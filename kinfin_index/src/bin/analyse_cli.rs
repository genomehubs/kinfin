use clap::Parser;
use std::path::PathBuf;
use anyhow::Result;
use kinfin_index::{Index, compute_cluster_stats};
use std::collections::{HashMap, HashSet};

#[derive(Parser, Debug)]
struct Args {
    /// Path to index bincode file
    #[arg(short, long, default_value = "../example/index.bincode")]
    index: PathBuf,

    /// Partition as comma-separated species indices or species names.
    /// Examples: "0,1" or "SpeciesA,SpeciesB" (names matched exactly against the index species list).
    #[arg(short, long, help = "Comma-separated species indices or names (e.g. '0,1' or 'SpA,SpB')")]
    partition: String,
}

fn main() -> Result<()> {
    let args = Args::parse();
    let idx = Index::load_bincode(&args.index)?;

    // build name -> index mapping from the index species list
    let mut name_to_idx: HashMap<String, usize> = HashMap::new();
    for (i, name) in idx.species.iter().enumerate() {
        name_to_idx.insert(name.clone(), i);
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
    for (ci, cluster) in idx.clusters.iter().enumerate() {
        let row = compute_cluster_stats(&idx, cluster, &partition_set);
        let out = serde_json::json!({
            "cluster_idx": ci,
            "cluster_id": row.cluster_id,
            "group_count": row.group_count,
            "other_count": row.other_count,
            "group_mean": row.group_mean,
            "other_mean": row.other_mean,
            "group_sd": row.group_sd,
            "other_sd": row.other_sd,
            "group_median": row.group_median,
            "other_median": row.other_median,
            "mann_whitney_u": row.mann_whitney_u,
            "mann_whitney_p": row.mann_whitney_p
        });
        println!("{}", out);
    }
    Ok(())
}
