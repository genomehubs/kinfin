use clap::Parser;
use std::path::{Path, PathBuf};
use anyhow::{Context, Result};
use std::collections::HashMap;
use std::io::BufRead;
use kinfin_index::{Cluster, Index};
use serde_json;

#[derive(Parser, Debug)]
#[command(author, version, about = "Index builder for kinfin")]
struct Args {
    /// Input directory containing SpeciesIDs.txt, SequenceIDs.txt, OrthologousGroups.txt, fasta/
    #[arg(short, long, default_value = "example")]
    input: PathBuf,

    /// Output bincode path (default: example/index.bincode)
    #[arg(short, long, default_value = "example/index.bincode")]
    output: PathBuf,

    /// Include sequence names in the index (larger file)
    #[arg(long, default_value_t = false)]
    include_names: bool,
}

fn parse_species(path: &Path) -> Result<Vec<String>> {
    let mut species = Vec::new();
    if !path.exists() {
        log::warn!("Species file {} not found", path.display());
        return Ok(species);
    }
    let s = std::fs::read_to_string(path)?;
    for line in s.lines() {
        let l = line.trim();
        if l.is_empty() {
            continue;
        }
        if let Some((idx_s, name)) = l.split_once(':') {
            let idx: usize = idx_s.trim().parse().with_context(|| format!("parse idx from '{}'", idx_s))?;
            let name = name.trim().to_string();
            let base = name.split('.').next().unwrap_or(&name).to_string();
            if idx >= species.len() {
                species.resize(idx + 1, String::new());
            }
            species[idx] = base;
        } else {
            log::warn!("Skipping malformed species line: {}", l);
        }
    }
    Ok(species)
}

fn parse_taxon_idx_mapping(path: &Path) -> Result<Vec<String>> {
    let mut species: Vec<String> = Vec::new();
    if !path.exists() {
        log::warn!("Taxon mapping file {} not found", path.display());
        return Ok(species);
    }
    let s = std::fs::read_to_string(path)?;
    let map: HashMap<String, serde_json::Value> = serde_json::from_str(&s)
        .with_context(|| format!("parse JSON from {}", path.display()))?;
    for (k, v) in map.into_iter() {
        let idx = if v.is_string() {
            v.as_str().unwrap().parse::<usize>().with_context(|| format!("parse index for {}", k))?
        } else if v.is_u64() {
            v.as_u64().unwrap() as usize
        } else {
            anyhow::bail!("unexpected value in taxon mapping for {}", k);
        };
        if idx >= species.len() {
            species.resize(idx + 1, String::new());
        }
        species[idx] = k;
    }
    Ok(species)
}

fn parse_sequence_ids(path: &Path, species_name_to_idx: Option<&HashMap<String, usize>>) -> Result<(Vec<String>, Vec<u32>, HashMap<String, u32>)> {
    if !path.exists() {
        return Err(std::io::Error::new(
            std::io::ErrorKind::NotFound,
            format!("SequenceIDs file {} not found", path.display()),
        )
        .into());
    }

    let s = std::fs::read_to_string(path)?;
    let mut seq_names = Vec::new();
    let mut seq_species = Vec::new();
    let mut name_to_idx = HashMap::new();
    for line in s.lines() {
        let l = line.trim();
        if l.is_empty() {
            continue;
        }
        if let Some((key, name)) = l.split_once(':') {
            let key = key.trim();
            let name = name.trim();
            // species prefix may be numeric or a species code; try numeric parse first, then lookup in mapping
            let prefix = key.split('_').next().unwrap_or("");
            let mut species_idx: usize = 0;
            if let Ok(i) = prefix.parse::<usize>() {
                species_idx = i;
            } else if let Some(map) = species_name_to_idx {
                if let Some(&i) = map.get(prefix) {
                    species_idx = i;
                } else {
                    log::warn!("Unknown species prefix '{}' in SequenceIDs; defaulting to 0", prefix);
                }
            }
            let idx = seq_names.len() as u32;
            seq_names.push(name.to_string());
            seq_species.push(species_idx as u32);
            name_to_idx.insert(name.to_string(), idx);
        } else {
            log::warn!("Skipping malformed seq id line: {}", l);
        }
    }
    Ok((seq_names, seq_species, name_to_idx))
}

fn parse_fasta_lengths(fasta_dir: &Path, name_to_idx: &HashMap<String, u32>, seq_len: &mut [Option<u32>]) -> Result<()> {
    if !fasta_dir.exists() {
        log::warn!("FASTA dir {} not found", fasta_dir.display());
        return Ok(());
    }
    for entry in std::fs::read_dir(fasta_dir)? {
        let entry = entry?;
        let p = entry.path();
        if !p.is_file() {
            continue;
        }
        let file_stem = p.file_stem().and_then(|s| s.to_str()).unwrap_or("");
        let file = std::fs::File::open(&p)?;
        let reader = std::io::BufReader::new(file);
        let mut cur_name: Option<String> = None;
        let mut cur_len: usize = 0;
        for line_res in reader.lines() {
            let line = line_res?;
            if line.starts_with('>') {
                if let Some(name) = cur_name.take() {
                    // try direct match, then try file-stem prefixed match (new datasets use species id as file prefix)
                    if let Some(&idx) = name_to_idx.get(&name) {
                        if (idx as usize) < seq_len.len() {
                            seq_len[idx as usize] = Some(cur_len as u32);
                        }
                    } else {
                        let combined = format!("{}.{}", file_stem, name);
                        if let Some(&idx) = name_to_idx.get(&combined) {
                            if (idx as usize) < seq_len.len() {
                                seq_len[idx as usize] = Some(cur_len as u32);
                            }
                        } else {
                            log::debug!("FASTA header {} not in SequenceIDs (tried combined={})", name, combined);
                        }
                    }
                }
                let header = line[1..].trim();
                let id = header.split_whitespace().next().unwrap_or("");
                cur_name = Some(id.to_string());
                cur_len = 0;
            } else {
                cur_len += line.trim().len();
            }
        }
        if let Some(name) = cur_name {
            if let Some(&idx) = name_to_idx.get(&name) {
                if (idx as usize) < seq_len.len() {
                    seq_len[idx as usize] = Some(cur_len as u32);
                }
            } else {
                let combined = format!("{}.{}", file_stem, name);
                if let Some(&idx) = name_to_idx.get(&combined) {
                    if (idx as usize) < seq_len.len() {
                        seq_len[idx as usize] = Some(cur_len as u32);
                    }
                }
            }
        }
    }
    Ok(())
}

/// Find a file in `input` by trying candidate names and a `kinfin.` prefix variant.
fn find_file_with_prefix(input: &Path, candidates: &[&str]) -> Option<std::path::PathBuf> {
    for &name in candidates {
        let p = input.join(name);
        if p.exists() {
            return Some(p);
        }
        let pref = input.join(format!("kinfin.{}", name));
        if pref.exists() {
            return Some(pref);
        }
    }
    None
}

fn parse_orthogroups(path: &Path, name_to_idx: &HashMap<String, u32>) -> Result<Vec<Cluster>> {
    if !path.exists() {
        return Err(std::io::Error::new(
            std::io::ErrorKind::NotFound,
            format!("OrthologousGroups file {} not found", path.display()),
        )
        .into());
    }

    let s = std::fs::read_to_string(path)?;
    let mut clusters = Vec::new();
    for line in s.lines() {
        let l = line.trim();
        if l.is_empty() {
            continue;
        }
        if let Some((id, members_str)) = l.split_once(':') {
            let id = id.trim().to_string();
            let mut members = Vec::new();
            for member in members_str.split_whitespace() {
                if let Some(&idx) = name_to_idx.get(member) {
                    members.push(idx);
                } else {
                    log::warn!("Member {} not found in SequenceIDs", member);
                }
            }
            clusters.push(Cluster { id, members });
        } else {
            log::warn!("Skipping malformed OG line: {}", l);
        }
    }
    Ok(clusters)
}

fn main() -> Result<()> {
    env_logger::init();
    let args = Args::parse();
    let input = args.input;
    let output = args.output;
    let species_path = find_file_with_prefix(&input, &["SpeciesIDs.txt"]).unwrap_or_else(|| input.join("SpeciesIDs.txt"));
    let seq_path = find_file_with_prefix(&input, &["SequenceIDs.txt"]).unwrap_or_else(|| input.join("SequenceIDs.txt"));
    let og_path = find_file_with_prefix(&input, &["OrthologousGroups.txt", "Orthogroups.txt"]).unwrap_or_else(|| input.join("OrthologousGroups.txt"));
    // accept either `fasta` or `fastas` directory names (some datasets use plural)
    let fasta_candidate = input.join("fasta");
    let fastas_candidate = input.join("fastas");
    let fasta_dir = if fasta_candidate.exists() {
        fasta_candidate
    } else if fastas_candidate.exists() {
        fastas_candidate
    } else {
        input.join("fasta")
    };

    log::info!("Using species file: {}", species_path.display());
    log::info!("Using sequence ids file: {}", seq_path.display());
    log::info!("Using orthogroups file: {}", og_path.display());

    log::info!("Parsing species...");
    // prefer taxon_idx_mapping.json when present (newer datasets)
    let taxon_json = find_file_with_prefix(&input, &["taxon_idx_mapping.json"]);
    let mut species: Vec<String> = Vec::new();
    if let Some(tj) = taxon_json {
        log::info!("Using taxon mapping file: {}", tj.display());
        species = parse_taxon_idx_mapping(&tj)?;
    } else {
        species = parse_species(&species_path)?;
    }

    log::info!("Parsing sequence ids...");
    // build species name -> idx map for parsing sequence id prefixes
    let mut species_name_to_idx: HashMap<String, usize> = HashMap::new();
    for (i, name) in species.iter().enumerate() {
        species_name_to_idx.insert(name.clone(), i);
    }

    let (seq_names, seq_species, name_to_idx) = parse_sequence_ids(&seq_path, Some(&species_name_to_idx))
        .with_context(|| format!("Failed to read SequenceIDs from {}", seq_path.display()))?;
    let mut seq_len: Vec<Option<u32>> = vec![None; seq_names.len()];
    log::info!("Parsing FASTA files (dir={})...", fasta_dir.display());
    parse_fasta_lengths(&fasta_dir, &name_to_idx, &mut seq_len)
        .with_context(|| format!("Failed to parse FASTA files in {}", fasta_dir.display()))?;
    log::info!("Parsing orthogroups...");
    let clusters = parse_orthogroups(&og_path, &name_to_idx)
        .with_context(|| format!("Failed to read OrthologousGroups from {}", og_path.display()))?;

    let index = Index {
        species,
        seq_names: if args.include_names { Some(seq_names) } else { None },
        seq_species,
        seq_len,
        clusters,
        meta: None,
    };

    let out_path = &output;
    // ensure parent directory exists for output files
    if let Some(parent) = out_path.parent() {
        log::info!("Ensuring output directory exists: {}", parent.display());
        std::fs::create_dir_all(parent)
            .with_context(|| format!("Failed to create output directory {}", parent.display()))?;
    }

    log::info!("Saving index to {}", out_path.display());
    index
        .save_bincode(out_path)
        .with_context(|| format!("Failed to save index bincode to {}", out_path.display()))?;
    // write memmap version as well
    let mmap_out = out_path.with_extension("mmap");
    log::info!("Saving memmap index to {}", mmap_out.display());
    kinfin_index::memmap::save_memmap(&index, &mmap_out)
        .with_context(|| format!("Failed to save memmap index to {}", mmap_out.display()))?;

    let meta = serde_json::json!({
        "species_count": index.species.len(),
        "seq_count": index.seq_species.len(),
        "cluster_count": index.clusters.len(),
    });
    let meta_path = out_path.with_extension("meta.json");
    std::fs::write(&meta_path, serde_json::to_string_pretty(&meta)?)
        .with_context(|| format!("Failed to write meta file to {}", meta_path.display()))?;
    log::info!("Done.");
    Ok(())
}
