use anyhow::Result;
use kinfin_index::memmap::MemmapIndex;
use kinfin_stats;
use std::collections::{HashMap, HashSet};
use std::path::PathBuf;
use clap::Parser;

#[derive(Parser, Debug)]
struct Args {
    #[arg(short, long, default_value = "../example/index.mmap")]
    index: PathBuf,

    #[arg(short, long, help = "Comma-separated species indices or names (e.g. '0,1' or 'SpA,SpB'). Names are matched exactly against the index species list.")]
    partition: String,
}

fn main() -> Result<()> {
    let args = Args::parse();
    let mi = MemmapIndex::open(&args.index)?;

    // build name -> index mapping from the memmap species table
    let mut name_to_idx: HashMap<String, usize> = HashMap::new();
    for i in 0..mi.species_count() {
        let name = mi.species_name(i)?;
        name_to_idx.insert(name, i);
    }

    // accept comma-separated indices or species names
    let mut partition_set: HashSet<usize> = HashSet::new();
    for tok in args.partition.split(',').map(|s| s.trim()).filter(|s| !s.is_empty()) {
        if let Ok(i) = tok.parse::<usize>() {
            partition_set.insert(i);
        } else if let Some(&i) = name_to_idx.get(tok) {
            partition_set.insert(i);
        } else {
            eprintln!("warning: unknown partition token '{}' - ignoring", tok);
        }
    }
    let seq_len = mi.seq_len_raw_slice()?;
    let clusters = mi.cluster_count();
    for ci in 0..clusters {
        let members = mi.cluster_members_for(ci)?;
        let entries = mi.cluster_species_entries_bytes_for(ci)?;
        let mut off = 0usize;
        let entry_size = 32usize;
        let mut group_count: u32 = 0;
        let mut other_count: u32 = 0;
        let mut group_sum: u64 = 0;
        let mut group_sumsq: u64 = 0;
        let mut group_n_with_len: u32 = 0;
        let mut other_sum: u64 = 0;
        let mut other_sumsq: u64 = 0;
        let mut other_n_with_len: u32 = 0;
        let mut group_vals: Vec<u32> = Vec::new();
        let mut other_vals: Vec<u32> = Vec::new();
        let mut counts_by_species: Vec<u32> = vec![0u32; mi.species_count()];
        while off + entry_size <= entries.len() {
            let species_idx = u32::from_le_bytes(entries[off..off+4].try_into().unwrap()) as usize;
            let rel_off = u32::from_le_bytes(entries[off+4..off+8].try_into().unwrap()) as usize;
            let count = u32::from_le_bytes(entries[off+8..off+12].try_into().unwrap()) as usize;
            let count_with_len = u32::from_le_bytes(entries[off+12..off+16].try_into().unwrap()) as usize;
            let sum = u64::from_le_bytes(entries[off+16..off+24].try_into().unwrap());
            let sumsq = u64::from_le_bytes(entries[off+24..off+32].try_into().unwrap());
            if partition_set.contains(&species_idx) {
                group_count += count as u32;
                group_sum += sum;
                group_sumsq = group_sumsq.saturating_add(sumsq);
                group_n_with_len += count_with_len as u32;
                if species_idx < counts_by_species.len() { counts_by_species[species_idx] = count as u32; }
                for i in 0..count {
                    let seq_idx = members[rel_off + i] as usize;
                    let len = seq_len[seq_idx];
                    if len != u32::MAX {
                        group_vals.push(len);
                    }
                }
            } else {
                other_count += count as u32;
                other_sum += sum;
                other_sumsq = other_sumsq.saturating_add(sumsq);
                other_n_with_len += count_with_len as u32;
                if species_idx < counts_by_species.len() { counts_by_species[species_idx] = count as u32; }
                for i in 0..count {
                    let seq_idx = members[rel_off + i] as usize;
                    let len = seq_len[seq_idx];
                    if len != u32::MAX {
                        other_vals.push(len);
                    }
                }
            }
            off += entry_size;
        }
        let group_mean = if group_n_with_len > 0 { Some(group_sum as f64 / group_n_with_len as f64) } else { None };
        let other_mean = if other_n_with_len > 0 { Some(other_sum as f64 / other_n_with_len as f64) } else { None };
        let group_sd = if group_n_with_len > 1 {
            let n = group_n_with_len as f64;
            let var = (group_sumsq as f64 - (group_sum as f64 * group_sum as f64 / n)) / (n - 1.0);
            Some(var.max(0.0).sqrt())
        } else { None };
        let other_sd = if other_n_with_len > 1 {
            let n = other_n_with_len as f64;
            let var = (other_sumsq as f64 - (other_sum as f64 * other_sum as f64 / n)) / (n - 1.0);
            Some(var.max(0.0).sqrt())
        } else { None };
        let group_median = if !group_vals.is_empty() {
            group_vals.sort_unstable();
            let m = group_vals.len();
            if m % 2 == 1 { Some(group_vals[m/2] as f64) } else { Some(((group_vals[m/2 - 1] as f64)+(group_vals[m/2] as f64))/2.0) }
        } else { None };
        let other_median = if !other_vals.is_empty() {
            other_vals.sort_unstable();
            let m = other_vals.len();
            if m % 2 == 1 { Some(other_vals[m/2] as f64) } else { Some(((other_vals[m/2 - 1] as f64)+(other_vals[m/2] as f64))/2.0) }
        } else { None };

        // compute Mann-Whitney U and p-value when both groups have lengths
        // compute Mann-Whitney on per-species counts (include zeros across species)
        let mut group_counts_per_species: Vec<f64> = Vec::with_capacity(mi.species_count());
        let mut other_counts_per_species: Vec<f64> = Vec::with_capacity(mi.species_count());
        for i in 0..mi.species_count() {
            if partition_set.contains(&i) {
                group_counts_per_species.push(counts_by_species[i] as f64);
            } else {
                other_counts_per_species.push(counts_by_species[i] as f64);
            }
        }

        let (mann_whitney_u, mann_whitney_p) = if group_counts_per_species.is_empty() || other_counts_per_species.is_empty() {
            (None, None)
        } else {
            let (u, p) = kinfin_stats::mannwhitney_rust(&group_counts_per_species, &other_counts_per_species, "two-sided");
            (Some(u), Some(p))
        };

        // taxa counts
        let mut group_taxa_count: u32 = 0;
        let mut other_taxa_count: u32 = 0;
        for i in 0..mi.species_count() {
            if counts_by_species[i] > 0 {
                if partition_set.contains(&i) { group_taxa_count += 1; } else { other_taxa_count += 1; }
            }
        }

        // mean counts per species and lg2 ratio
        let group_mean_count = if !group_counts_per_species.is_empty() { Some(group_counts_per_species.iter().sum::<f64>() / (group_counts_per_species.len() as f64)) } else { None };
        let other_mean_count = if !other_counts_per_species.is_empty() { Some(other_counts_per_species.iter().sum::<f64>() / (other_counts_per_species.len() as f64)) } else { None };
        let lg2 = match (group_mean_count, other_mean_count) {
            (Some(g), Some(o)) if o > 0.0 => Some((g / o).log2()),
            _ => None,
        };

        let row = serde_json::json!({
            "cluster_idx": ci,
            "group_count": group_count,
            "other_count": other_count,
            "group_mean": group_mean,
            "other_mean": other_mean,
            "group_sd": group_sd,
            "other_sd": other_sd,
            "group_median": group_median,
            "other_median": other_median,
            "mann_whitney_u": mann_whitney_u,
            "mann_whitney_p": mann_whitney_p,
            "group_length": if group_n_with_len > 0 { Some(group_sum as f64) } else { None },
            "group_length_mean": group_mean,
            "group_length_median": group_median,
            "other_length": if other_n_with_len > 0 { Some(other_sum as f64) } else { None },
            "other_length_mean": other_mean,
            "other_length_median": other_median,
            "group_taxa_count": group_taxa_count,
            "other_taxa_count": other_taxa_count,
            "lg2_mean_count_over_other": lg2
        });
        println!("{}", row);
    }
    Ok(())
}
