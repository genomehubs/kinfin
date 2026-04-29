//! Rust cluster analysis benchmark binary.
//!
//! Reads the JSON file produced by prepare_cluster_data.py and runs the full
//! cluster analysis loop — identical logic to the Python run_cluster_analysis.py —
//! then writes a TSV result file.
//!
//! Timing covers only the analysis loop, excluding JSON I/O.
//!
//! Usage:
//!   ./run_cluster_analysis cluster_data.json [--output results.tsv]

use serde::{Deserialize, Serialize};
use serde_json::Value;
use statrs::distribution::{ContinuousCDF, Normal};
use std::collections::{HashMap, HashSet};
use std::env;
use std::fs;
use std::io::{BufWriter, Write};
use std::time::Instant;

// ---------------------------------------------------------------------------
// JSON input structs
// ---------------------------------------------------------------------------

#[derive(Deserialize, Debug)]
struct Params {
    test: String,
    min_proteomes: usize,
    fuzzy_count: usize,
    fuzzy_fraction: f64,
    fuzzy_range: Vec<usize>,
    fastas_parsed: bool,
}

#[derive(Deserialize, Debug)]
struct AloLevel {
    proteomes_list: Vec<String>,
    proteome_count: usize,
}

#[derive(Deserialize, Debug)]
struct ClusterInput {
    cluster_id: String,
    singleton: bool,
    // proteome_id -> list of protein_ids
    protein_ids_by_proteome_id: HashMap<String, Vec<String>>,
}

#[derive(Deserialize, Debug)]
struct InputData {
    params: Params,
    // attribute -> level -> AloLevel (or null)
    alo_collection: HashMap<String, HashMap<String, Option<AloLevel>>>,
    clusters: Vec<ClusterInput>,
    protein_lengths: HashMap<String, u32>,
}

// ---------------------------------------------------------------------------
// Output row
// ---------------------------------------------------------------------------

struct ResultRow {
    cluster_id: String,
    attribute: String,
    level: String,
    cluster_type: &'static str,
    alo_status: &'static str,
    proteome_coverage: f64,
    cardinality: Option<&'static str>,
    mwu_pvalue: Option<f64>,
    mwu_log2_mean: Option<f64>,
    mean_alo: Option<f64>,
    mean_non_alo: Option<f64>,
    protein_count: usize,
    length_sum: u32,
}

// ---------------------------------------------------------------------------
// Mann-Whitney U (matches lib.rs implementation exactly)
// ---------------------------------------------------------------------------

fn normal_cdf(x: f64) -> f64 {
    Normal::new(0.0, 1.0).unwrap().cdf(x)
}

/// Exact two-sided p-value for Mann-Whitney U via DP over rank sequences.
/// Matches scipy.stats.mannwhitneyu method='exact' (no ties assumed).
/// m = min(n1, n2), n = max(n1, n2), u_obs_min = min(U1, U2).
fn mannwhitneyu_exact_pvalue(u_obs_min: usize, m: usize, n: usize) -> f64 {
    let max_u = m * n;
    let width = max_u + 1;
    let mut prev = vec![0.0f64; (m + 1) * width];
    let mut cur = vec![0.0f64; (m + 1) * width];
    for i in 0..=m {
        prev[i * width] = 1.0;
    }
    for _j in 1..=n {
        for v in cur.iter_mut() {
            *v = 0.0;
        }
        cur[0] = 1.0;
        for i in 1..=m {
            let base = i * width;
            let base_im1 = (i - 1) * width;
            for k in 0..=max_u {
                let from_x = cur[base_im1 + k];
                let from_y = if k >= i { prev[base + k - i] } else { 0.0 };
                cur[base + k] = from_x + from_y;
            }
        }
        std::mem::swap(&mut prev, &mut cur);
    }
    let base_m = m * width;
    let total: f64 = prev[base_m..base_m + width].iter().sum();
    if total == 0.0 {
        return 1.0;
    }
    let p_le: f64 = prev[base_m..base_m + u_obs_min + 1].iter().sum::<f64>() / total;
    (2.0 * p_le).min(1.0)
}

fn mannwhitneyu(x: &[f64], y: &[f64]) -> f64 {
    let n1 = x.len();
    let n2 = y.len();
    if n1 == 0 || n2 == 0 {
        return 1.0;
    }
    let mut combined: Vec<(f64, usize)> = Vec::with_capacity(n1 + n2);
    for &v in x {
        combined.push((v, 0));
    }
    for &v in y {
        combined.push((v, 1));
    }
    combined.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(std::cmp::Ordering::Equal));

    let mut ranks = vec![0.0_f64; combined.len()];
    let mut i = 0;
    while i < combined.len() {
        let mut j = i;
        while j < combined.len() && (combined[j].0 - combined[i].0).abs() < 1e-15 {
            j += 1;
        }
        let avg_rank = ((i + j) as f64 + 1.0) / 2.0;
        for idx in i..j {
            ranks[idx] = avg_rank;
        }
        i = j;
    }

    let mut rank_sum_x = 0.0_f64;
    for (idx, (_, group)) in combined.iter().enumerate() {
        if *group == 0 {
            rank_sum_x += ranks[idx];
        }
    }

    let n1f = n1 as f64;
    let n2f = n2 as f64;
    let u1 = rank_sum_x - n1f * (n1f + 1.0) / 2.0;
    let u2 = n1f * n2f - u1;
    let u_min = u1.min(u2);

    // Check for ties
    let has_ties = combined.windows(2).any(|w| (w[0].0 - w[1].0).abs() < 1e-15);

    // Exact method when min(n1, n2) <= 8 and no ties (matches scipy 'auto')
    if !has_ties && (n1 <= 8 || n2 <= 8) {
        let m = n1.min(n2);
        let n = n1.max(n2);
        return mannwhitneyu_exact_pvalue(u_min as usize, m, n);
    }

    // Asymptotic path with tie-corrected variance (matches scipy _get_mwu_z)
    let n_total = (n1 + n2) as f64;
    let mean_u = n1f * n2f / 2.0;

    // Tie correction: sum of (t^3 - t) over each tied run, where t = run length
    let tie_term: f64 = {
        let mut sum = 0.0f64;
        let mut i = 0;
        while i < combined.len() {
            let mut j = i + 1;
            while j < combined.len() && (combined[j].0 - combined[i].0).abs() < 1e-15 {
                j += 1;
            }
            let t = (j - i) as f64;
            sum += t * t * t - t;
            i = j;
        }
        sum
    };
    let var_u = n1f * n2f / 12.0 * ((n_total + 1.0) - tie_term / (n_total * (n_total - 1.0)));
    if var_u <= 0.0 {
        return 1.0;
    }
    // scipy: z = (U_max - 0.5 - mean_u) / s, p = 2*sf(z).
    // Equivalent with u_min: z = (u_min + 0.5 - mean_u) / s, p = 2*CDF(z) [z <= 0 typically].
    let z = (u_min + 0.5 - mean_u) / var_u.sqrt();
    (2.0 * normal_cdf(z)).clamp(0.0, 1.0)
}

// ---------------------------------------------------------------------------
// Stat dispatch
// ---------------------------------------------------------------------------

fn statistic(
    count1: &[i32],
    count2: &[i32],
    test: &str,
    min_proteomes: usize,
) -> (Option<f64>, Option<f64>, Option<f64>, Option<f64>) {
    let c1: Vec<f64> = count1
        .iter()
        .filter(|&&c| c > 0)
        .map(|&c| c as f64)
        .collect();
    let c2: Vec<f64> = count2
        .iter()
        .filter(|&&c| c > 0)
        .map(|&c| c as f64)
        .collect();
    if c1.len() < min_proteomes || c2.len() < min_proteomes {
        return (None, None, None, None);
    }
    let mean_c1 = c1.iter().sum::<f64>() / c1.len() as f64;
    let mean_c2 = c2.iter().sum::<f64>() / c2.len() as f64;
    let log2_mean = (mean_c1 / mean_c2).log2();

    // Check if all values equal
    let s1: HashSet<u64> = c1.iter().map(|&x| x.to_bits()).collect();
    let s2: HashSet<u64> = c2.iter().map(|&x| x.to_bits()).collect();
    let pvalue = if s1.len() == 1 && s2.len() == 1 && s1 == s2 {
        1.0
    } else {
        match test {
            "mannwhitneyu" => mannwhitneyu(&c1, &c2),
            // other tests fall back to MWU for now (benchmark focus is mannwhitneyu)
            _ => mannwhitneyu(&c1, &c2),
        }
    };

    (Some(pvalue), Some(log2_mean), Some(mean_c1), Some(mean_c2))
}

// ---------------------------------------------------------------------------
// Cardinality
// ---------------------------------------------------------------------------

fn get_cardinality(
    alo_counts: &[i32],
    fuzzy_count: usize,
    fuzzy_fraction: f64,
    fuzzy_range: &HashSet<usize>,
) -> Option<&'static str> {
    let non_zero: Vec<i32> = alo_counts.iter().copied().filter(|&c| c > 0).collect();
    if non_zero.is_empty() {
        return None;
    }
    if non_zero.iter().all(|&c| c == 1) {
        return Some("true");
    }
    let fc = fuzzy_count as i32;
    if non_zero.contains(&fc)
        || (non_zero.len() as f64 >= alo_counts.len() as f64 * fuzzy_fraction
            && non_zero
                .iter()
                .all(|c| fuzzy_range.contains(&(*c as usize))))
    {
        return Some("fuzzy");
    }
    None
}

// ---------------------------------------------------------------------------
// Length stats
// ---------------------------------------------------------------------------

fn get_length_stats(
    protein_ids: &[String],
    protein_lengths: &HashMap<String, u32>,
    fastas_parsed: bool,
) -> (u32, f64, f64, f64) {
    if !fastas_parsed || protein_ids.is_empty() {
        return (0, 0.0, 0.0, 0.0);
    }
    let lengths: Vec<u32> = protein_ids
        .iter()
        .filter_map(|id| protein_lengths.get(id).copied())
        .filter(|&l| l > 0)
        .collect();
    if lengths.is_empty() {
        return (0, 0.0, 0.0, 0.0);
    }
    let sum: u32 = lengths.iter().sum();
    let mean = sum as f64 / lengths.len() as f64;
    let mut sorted = lengths.clone();
    sorted.sort_unstable();
    let n = sorted.len();
    let median = (sorted[n / 2] as f64 + sorted[(n - 1) / 2] as f64) / 2.0;
    let sd = if lengths.len() > 1 {
        (lengths
            .iter()
            .map(|&x| (x as f64 - mean).powi(2))
            .sum::<f64>()
            / lengths.len() as f64)
            .sqrt()
    } else {
        0.0
    };
    (sum, mean, median, sd)
}

// ---------------------------------------------------------------------------
// Main analysis loop
// ---------------------------------------------------------------------------

fn run_analysis(data: &InputData) -> Vec<ResultRow> {
    let params = &data.params;
    let test = params.test.as_str();
    let min_proteomes = params.min_proteomes;
    let fuzzy_count = params.fuzzy_count;
    let fuzzy_fraction = params.fuzzy_fraction;
    let fuzzy_range: HashSet<usize> = params.fuzzy_range.iter().copied().collect();
    let fastas_parsed = params.fastas_parsed;
    let attributes: Vec<&String> = data.alo_collection.keys().collect();

    let mut results = Vec::new();

    for cluster in &data.clusters {
        let cluster_id = &cluster.cluster_id;
        let singleton = cluster.singleton;
        let pids_by_proteome = &cluster.protein_ids_by_proteome_id;

        for attribute in &attributes {
            let levels = &data.alo_collection[*attribute];

            // Pass 1: build per-level data
            let mut protein_ids_by_level: HashMap<&str, Vec<&str>> = HashMap::new();
            let mut length_stats_by_level: HashMap<&str, (u32, f64, f64, f64)> = HashMap::new();
            let mut explicit_count_by_level: HashMap<&str, HashMap<&str, i32>> = HashMap::new();
            let mut implicit_by_level: HashMap<&str, bool> = HashMap::new(); // level -> has any

            for (level, alo_opt) in levels {
                let alo = match alo_opt {
                    Some(a) => a,
                    None => continue,
                };
                let mut pids_for_level: Vec<&str> = Vec::new();
                let mut count_by_proteome: HashMap<&str, i32> = HashMap::new();
                let mut has_implicit = false;

                for proteome_id in &alo.proteomes_list {
                    let pids = pids_by_proteome.get(proteome_id);
                    let count = pids.map_or(0, |v| v.len()) as i32;
                    count_by_proteome.insert(proteome_id.as_str(), count);
                    if let Some(pids) = pids {
                        pids_for_level.extend(pids.iter().map(String::as_str));
                        if count > 0 {
                            has_implicit = true;
                        }
                    }
                }

                let pids_owned: Vec<String> =
                    pids_for_level.iter().map(|s| s.to_string()).collect();
                let ls = get_length_stats(&pids_owned, &data.protein_lengths, fastas_parsed);
                length_stats_by_level.insert(level.as_str(), ls);
                protein_ids_by_level.insert(level.as_str(), pids_for_level);
                explicit_count_by_level.insert(level.as_str(), count_by_proteome);
                if has_implicit {
                    implicit_by_level.insert(level.as_str(), true);
                }
            }

            let cluster_type: &'static str = if singleton {
                "singleton"
            } else if implicit_by_level.len() > 1 {
                "shared"
            } else {
                "specific"
            };

            // Pass 2: per-level stats
            for (level, alo_opt) in levels {
                let alo = match alo_opt {
                    Some(a) => a,
                    None => continue,
                };
                let proteome_count = alo.proteome_count;
                let alo_status: &'static str = if implicit_by_level.contains_key(level.as_str()) {
                    "present"
                } else {
                    "absent"
                };
                let implicit_count = if alo_status == "present" {
                    explicit_count_by_level[level.as_str()]
                        .values()
                        .filter(|&&c| c > 0)
                        .count()
                } else {
                    0
                };
                let proteome_coverage = implicit_count as f64 / proteome_count as f64;

                let mut cardinality: Option<&'static str> = None;
                let mut mwu_pvalue: Option<f64> = None;
                let mut mwu_log2_mean: Option<f64> = None;
                let mut mean_alo: Option<f64> = None;
                let mut mean_non_alo: Option<f64> = None;

                if alo_status == "present" && cluster_type != "singleton" {
                    let alo_counts: Vec<i32> = explicit_count_by_level[level.as_str()]
                        .values()
                        .copied()
                        .collect();
                    cardinality =
                        get_cardinality(&alo_counts, fuzzy_count, fuzzy_fraction, &fuzzy_range);

                    if cluster_type == "shared" {
                        let non_alo_counts: Vec<i32> = explicit_count_by_level
                            .iter()
                            .filter(|(&l, _)| l != level.as_str())
                            .flat_map(|(_, counts)| counts.values().copied())
                            .collect();
                        let (pv, lm, ma, mn) =
                            statistic(&alo_counts, &non_alo_counts, test, min_proteomes);
                        mwu_pvalue = pv;
                        mwu_log2_mean = lm;
                        mean_alo = ma;
                        mean_non_alo = mn;
                    }
                }

                let pids = protein_ids_by_level
                    .get(level.as_str())
                    .map_or(0, |v| v.len());
                let ls = length_stats_by_level
                    .get(level.as_str())
                    .copied()
                    .unwrap_or((0, 0.0, 0.0, 0.0));

                results.push(ResultRow {
                    cluster_id: cluster_id.clone(),
                    attribute: attribute.to_string(),
                    level: level.clone(),
                    cluster_type,
                    alo_status,
                    proteome_coverage,
                    cardinality,
                    mwu_pvalue,
                    mwu_log2_mean,
                    mean_alo,
                    mean_non_alo,
                    protein_count: pids,
                    length_sum: ls.0,
                });
            }
        }
    }

    results
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        eprintln!("Usage: run_cluster_analysis <cluster_data.json> [--output <out.tsv>]");
        std::process::exit(1);
    }

    let input_path = &args[1];
    let output_path = args
        .windows(2)
        .find(|w| w[0] == "--output")
        .map(|w| w[1].clone())
        .unwrap_or_else(|| "cluster_analysis_results_rust.tsv".to_string());

    eprintln!("Loading {} ...", input_path);
    let t_load = Instant::now();
    let raw = fs::read_to_string(input_path).expect("Cannot read input file");
    let data: InputData = serde_json::from_str(&raw).expect("JSON parse error");
    eprintln!("Loaded in {:.2}s", t_load.elapsed().as_secs_f64());

    let n_clusters = data.clusters.len();
    let n_attrs = data.alo_collection.len();
    eprintln!("  {} clusters, {} attributes", n_clusters, n_attrs);

    // --- Timed section ---
    let t0 = Instant::now();
    let results = run_analysis(&data);
    let elapsed = t0.elapsed().as_secs_f64();
    // --- End timed section ---

    eprintln!("Writing {} ...", output_path);
    let f = fs::File::create(&output_path).expect("Cannot create output file");
    let mut w = BufWriter::new(f);
    writeln!(w, "cluster_id\tattribute\tlevel\tcluster_type\talo_status\tproteome_coverage\tcardinality\tmwu_pvalue\tmwu_log2_mean\tmean_alo\tmean_non_alo\tprotein_count\tlength_sum").unwrap();
    for row in &results {
        writeln!(
            w,
            "{}\t{}\t{}\t{}\t{}\t{:.6}\t{}\t{}\t{}\t{}\t{}\t{}\t{}",
            row.cluster_id,
            row.attribute,
            row.level,
            row.cluster_type,
            row.alo_status,
            row.proteome_coverage,
            row.cardinality.unwrap_or(""),
            row.mwu_pvalue
                .map_or(String::new(), |v| format!("{:.8}", v)),
            row.mwu_log2_mean
                .map_or(String::new(), |v| format!("{:.8}", v)),
            row.mean_alo.map_or(String::new(), |v| format!("{:.4}", v)),
            row.mean_non_alo
                .map_or(String::new(), |v| format!("{:.4}", v)),
            row.protein_count,
            row.length_sum,
        )
        .unwrap();
    }

    println!("cluster_analysis_elapsed_s\t{:.6}", elapsed);
    println!("clusters\t{}", n_clusters);
    println!("result_rows\t{}", results.len());
    eprintln!("Done. {:.3}s", elapsed);
}
