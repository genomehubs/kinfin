use anyhow::Result;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashSet;
use std::path::Path;

#[derive(Serialize, Deserialize, Debug)]
pub struct Cluster {
    pub id: String,
    pub members: Vec<u32>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct Index {
    pub species: Vec<String>,
    pub seq_names: Option<Vec<String>>,
    pub seq_species: Vec<u32>,
    pub seq_len: Vec<Option<u32>>,
    pub clusters: Vec<Cluster>,
    pub meta: Option<Value>,
}

impl Index {
    pub fn save_bincode(&self, path: &Path) -> Result<()> {
        let f = std::fs::File::create(path)?;
        bincode::serialize_into(f, self)?;
        Ok(())
    }

    pub fn load_bincode(path: &Path) -> Result<Index> {
        let f = std::fs::File::open(path)?;
        let idx: Index = bincode::deserialize_from(f)?;
        Ok(idx)
    }
}

pub mod memmap;
#[cfg(feature = "python")]
pub mod pyapi;

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct StatsRow {
    pub cluster_id: String,
    pub group_count: u32,
    pub other_count: u32,
    pub group_mean: Option<f64>,
    pub other_mean: Option<f64>,
    pub group_sd: Option<f64>,
    pub other_sd: Option<f64>,
    pub group_median: Option<f64>,
    pub other_median: Option<f64>,
    pub mann_whitney_u: Option<f64>,
    pub mann_whitney_p: Option<f64>,

    // sequence length summaries
    pub group_length: Option<f64>,
    pub group_length_mean: Option<f64>,
    pub group_length_median: Option<f64>,
    pub other_length: Option<f64>,
    pub other_length_mean: Option<f64>,
    pub other_length_median: Option<f64>,

    // taxa counts (number of species observed in/out of partition)
    pub group_taxa_count: u32,
    pub other_taxa_count: u32,

    // log2 of (mean count per-species in partition) / (mean count per-species in other)
    pub lg2_mean_count_over_other: Option<f64>,
}

pub fn compute_cluster_stats(
    index: &Index,
    cluster: &Cluster,
    partition_set: &HashSet<usize>,
) -> StatsRow {
    let mut group_count: u32 = 0;
    let mut other_count: u32 = 0;
    let mut group_sum: f64 = 0.0;
    let mut other_sum: f64 = 0.0;
    let mut group_sumsq: f64 = 0.0;
    let mut other_sumsq: f64 = 0.0;
    let mut group_vals: Vec<u32> = Vec::new();
    let mut other_vals: Vec<u32> = Vec::new();
    // per-species counts (length = number of species)
    let mut counts_by_species: Vec<u32> = vec![0u32; index.species.len()];

    for &mem in &cluster.members {
        let mem_usize = mem as usize;
        let species_idx = index.seq_species[mem_usize] as usize;
        // increment per-species count
        if species_idx < counts_by_species.len() {
            counts_by_species[species_idx] = counts_by_species[species_idx].saturating_add(1);
        }
        if partition_set.contains(&species_idx) {
            group_count += 1;
            if let Some(len) = index.seq_len[mem_usize] {
                group_sum += len as f64;
                group_sumsq += (len as f64) * (len as f64);
                group_vals.push(len);
            }
        } else {
            other_count += 1;
            if let Some(len) = index.seq_len[mem_usize] {
                other_sum += len as f64;
                other_sumsq += (len as f64) * (len as f64);
                other_vals.push(len);
            }
        }
    }

    let group_n = group_vals.len() as f64;
    let other_n = other_vals.len() as f64;
    let group_mean = if group_n > 0.0 {
        Some(group_sum / group_n)
    } else {
        None
    };
    let other_mean = if other_n > 0.0 {
        Some(other_sum / other_n)
    } else {
        None
    };
    let group_sd = if group_n > 1.0 {
        let var = (group_sumsq - (group_sum * group_sum / group_n)) / (group_n - 1.0);
        Some(var.max(0.0).sqrt())
    } else {
        None
    };
    let other_sd = if other_n > 1.0 {
        let var = (other_sumsq - (other_sum * other_sum / other_n)) / (other_n - 1.0);
        Some(var.max(0.0).sqrt())
    } else {
        None
    };

    let group_median = if !group_vals.is_empty() {
        group_vals.sort_unstable();
        let m = group_vals.len();
        if m % 2 == 1 {
            Some(group_vals[m / 2] as f64)
        } else {
            Some(((group_vals[m / 2 - 1] as f64) + (group_vals[m / 2] as f64)) / 2.0)
        }
    } else {
        None
    };

    let other_median = if !other_vals.is_empty() {
        other_vals.sort_unstable();
        let m = other_vals.len();
        if m % 2 == 1 {
            Some(other_vals[m / 2] as f64)
        } else {
            Some(((other_vals[m / 2 - 1] as f64) + (other_vals[m / 2] as f64)) / 2.0)
        }
    } else {
        None
    };

    // compute Mann-Whitney over per-species counts (compare counts per species in partition vs other)
    let mut group_counts_per_species: Vec<f64> = Vec::new();
    let mut other_counts_per_species: Vec<f64> = Vec::new();
    for (i, &c) in counts_by_species.iter().enumerate() {
        if partition_set.contains(&i) {
            group_counts_per_species.push(c as f64);
        } else {
            other_counts_per_species.push(c as f64);
        }
    }

    let mann = if group_counts_per_species.is_empty() || other_counts_per_species.is_empty() {
        (None, None)
    } else {
        let (u, p) = kinfin_stats::mannwhitney_rust(
            &group_counts_per_species,
            &other_counts_per_species,
            "two-sided",
        );
        (Some(u), Some(p))
    };

    // taxa counts (number of species with at least one member)
    let mut group_taxa_count: u32 = 0;
    let mut other_taxa_count: u32 = 0;
    for (i, &c) in counts_by_species.iter().enumerate() {
        if c > 0 {
            if partition_set.contains(&i) {
                group_taxa_count += 1;
            } else {
                other_taxa_count += 1;
            }
        }
    }

    // mean counts per-species (including zeros across species in each side)
    let group_mean_count = if !group_counts_per_species.is_empty() {
        Some(group_counts_per_species.iter().sum::<f64>() / (group_counts_per_species.len() as f64))
    } else {
        None
    };
    let other_mean_count = if !other_counts_per_species.is_empty() {
        Some(other_counts_per_species.iter().sum::<f64>() / (other_counts_per_species.len() as f64))
    } else {
        None
    };

    let lg2_mean_count_over_other = match (group_mean_count, other_mean_count) {
        (Some(g), Some(o)) if o > 0.0 => Some((g / o).log2()),
        _ => None,
    };

    // total lengths
    let group_length = if group_n > 0.0 { Some(group_sum) } else { None };
    let other_length = if other_n > 0.0 { Some(other_sum) } else { None };

    let group_length_mean = group_mean;
    let other_length_mean = other_mean;
    let group_length_median = group_median;
    let other_length_median = other_median;

    StatsRow {
        cluster_id: cluster.id.clone(),
        group_count,
        other_count,
        group_mean,
        other_mean,
        group_sd,
        other_sd,
        group_median,
        other_median,
        mann_whitney_u: mann.0,
        mann_whitney_p: mann.1,
        group_length,
        group_length_mean,
        group_length_median,
        other_length,
        other_length_mean,
        other_length_median,
        group_taxa_count,
        other_taxa_count,
        lg2_mean_count_over_other,
    }
}
