use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::path::Path;
use std::collections::HashSet;

use crate::{Index, StatsRow, compute_cluster_stats};
use crate::memmap::MemmapIndex;
use kinfin_stats;
// (no extra imports)

#[pyfunction]
#[pyo3(signature = (index_path, partitions, callback=None, batch_size=256))]
fn analyse_clusters(py: Python, index_path: &str, partitions: Vec<Vec<usize>>, callback: Option<PyObject>, batch_size: usize) -> PyResult<()> {
    let path = Path::new(index_path);
    let index = Index::load_bincode(path).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("failed to load index: {}", e)))?;
    let clusters_len = index.clusters.len();

    for (p_idx, partition) in partitions.into_iter().enumerate() {
        let partition_set: HashSet<usize> = partition.into_iter().collect();
        let mut cluster_idx = 0usize;
        while cluster_idx < clusters_len {
            let end = std::cmp::min(cluster_idx + batch_size, clusters_len);
            let mut rust_batch: Vec<StatsRow> = Vec::with_capacity(end - cluster_idx);

            // compute without holding GIL
            py.allow_threads(|| {
                for ci in cluster_idx..end {
                    let cluster = &index.clusters[ci];
                    let row = compute_cluster_stats(&index, cluster, &partition_set);
                    rust_batch.push(row);
                }
            });

            // call Python callback with batch
            if let Some(cb) = &callback {
                Python::with_gil(|py| -> PyResult<()> {
                    let cb_ref = cb.as_ref(py);
                    let py_list = PyList::empty(py);
                    for row in &rust_batch {
                        let dict = PyDict::new(py);
                        dict.set_item("cluster_id", row.cluster_id.clone())?;
                        dict.set_item("partition_idx", p_idx)?;
                        dict.set_item("group_count", row.group_count)?;
                        dict.set_item("other_count", row.other_count)?;
                        dict.set_item("group_mean", row.group_mean)?;
                        dict.set_item("other_mean", row.other_mean)?;
                        dict.set_item("group_sd", row.group_sd)?;
                        dict.set_item("other_sd", row.other_sd)?;
                        dict.set_item("group_median", row.group_median)?;
                        dict.set_item("other_median", row.other_median)?;
                        dict.set_item("mann_whitney_u", row.mann_whitney_u)?;
                        dict.set_item("mann_whitney_p", row.mann_whitney_p)?;
                        dict.set_item("group_length", row.group_length)?;
                        dict.set_item("group_length_mean", row.group_length_mean)?;
                        dict.set_item("group_length_median", row.group_length_median)?;
                        dict.set_item("other_length", row.other_length)?;
                        dict.set_item("other_length_mean", row.other_length_mean)?;
                        dict.set_item("other_length_median", row.other_length_median)?;
                        dict.set_item("group_taxa_count", row.group_taxa_count)?;
                        dict.set_item("other_taxa_count", row.other_taxa_count)?;
                        dict.set_item("lg2_mean_count_over_other", row.lg2_mean_count_over_other)?;
                        py_list.append(dict)?;
                    }
                    cb_ref.call1((py_list,))?;
                    Ok(())
                })?;
            }

            cluster_idx = end;
        }
    }

    Ok(())
}

#[pyclass]
struct MemmapBatchIter {
    mi: MemmapIndex,
    partitions: Vec<Vec<usize>>,
    batch_size: usize,
    p_idx: usize,
    cluster_idx: usize,
}

#[pymethods]
impl MemmapBatchIter {
    #[new]
    fn new(index_path: &str, partitions: Vec<Vec<usize>>, batch_size: usize) -> PyResult<Self> {
        let path = std::path::Path::new(index_path);
        let mi = MemmapIndex::open(path).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("failed to open memmap index: {}", e)))?;
        Ok(MemmapBatchIter { mi, partitions, batch_size, p_idx: 0usize, cluster_idx: 0usize })
    }

    fn __iter__(slf: PyRef<Self>) -> PyRef<Self> { slf }

    fn __next__(&mut self, py: Python) -> PyResult<Option<PyObject>> {
        let clusters_len = self.mi.cluster_count();

        while self.p_idx < self.partitions.len() {
            // if we've finished this partition, advance
            if self.cluster_idx >= clusters_len {
                self.p_idx += 1;
                self.cluster_idx = 0;
                continue;
            }

            let partition_set: HashSet<usize> = self.partitions[self.p_idx].iter().copied().collect();
            let start = self.cluster_idx;
            let end = std::cmp::min(self.cluster_idx + self.batch_size, clusters_len);

            // output arrays
            let mut cluster_idxs: Vec<u32> = Vec::with_capacity(end - start);
            let mut group_counts: Vec<u32> = Vec::with_capacity(end - start);
            let mut other_counts: Vec<u32> = Vec::with_capacity(end - start);
            let mut group_means: Vec<f64> = Vec::with_capacity(end - start);
            let mut other_means: Vec<f64> = Vec::with_capacity(end - start);
            let mut group_sds: Vec<f64> = Vec::with_capacity(end - start);
            let mut other_sds: Vec<f64> = Vec::with_capacity(end - start);
            let mut group_medians: Vec<f64> = Vec::with_capacity(end - start);
            let mut other_medians: Vec<f64> = Vec::with_capacity(end - start);
            let mut group_lengths: Vec<f64> = Vec::with_capacity(end - start);
            let mut group_length_means: Vec<f64> = Vec::with_capacity(end - start);
            let mut group_length_medians: Vec<f64> = Vec::with_capacity(end - start);
            let mut other_lengths: Vec<f64> = Vec::with_capacity(end - start);
            let mut other_length_means: Vec<f64> = Vec::with_capacity(end - start);
            let mut other_length_medians: Vec<f64> = Vec::with_capacity(end - start);
            let mut group_taxa_counts: Vec<u32> = Vec::with_capacity(end - start);
            let mut other_taxa_counts: Vec<u32> = Vec::with_capacity(end - start);
            let mut lg2_mean_count_over_others: Vec<f64> = Vec::with_capacity(end - start);
            let mut mann_whitney_us: Vec<f64> = Vec::with_capacity(end - start);
            let mut mann_whitney_ps: Vec<f64> = Vec::with_capacity(end - start);

            // compute the numeric arrays without holding GIL
            {
                let mi_ref = &self.mi;
                py.allow_threads(|| {
                    let seq_len = mi_ref.seq_len_raw_slice().unwrap();
                    for ci in start..end {
                        let members = mi_ref.cluster_members_for(ci).unwrap();
                        let entries_bytes = mi_ref.cluster_species_entries_bytes_for(ci).unwrap();

                        let mut group_count: u32 = 0;
                        let mut other_count: u32 = 0;
                        let mut group_sum: u64 = 0;
                        let mut other_sum: u64 = 0;
                        let mut group_sumsq: u64 = 0;
                        let mut other_sumsq: u64 = 0;
                        let mut group_n_with_len: u32 = 0;
                        let mut other_n_with_len: u32 = 0;
                        let mut group_vals: Vec<u32> = Vec::new();
                        let mut other_vals: Vec<u32> = Vec::new();

                        let entry_size = 32usize;
                        let mut off = 0usize;
                        // per-species counts for this cluster
                        let mut counts_by_species: Vec<u32> = vec![0u32; mi_ref.species_count()];
                        while off + entry_size <= entries_bytes.len() {
                            let species_idx = u32::from_le_bytes(entries_bytes[off..off+4].try_into().unwrap()) as usize;
                            let rel_off = u32::from_le_bytes(entries_bytes[off+4..off+8].try_into().unwrap()) as usize;
                            let count = u32::from_le_bytes(entries_bytes[off+8..off+12].try_into().unwrap()) as usize;
                            let count_with_len = u32::from_le_bytes(entries_bytes[off+12..off+16].try_into().unwrap()) as usize;
                            let sum = u64::from_le_bytes(entries_bytes[off+16..off+24].try_into().unwrap());
                            let sumsq = u64::from_le_bytes(entries_bytes[off+24..off+32].try_into().unwrap());

                            if species_idx < counts_by_species.len() {
                                counts_by_species[species_idx] = count as u32;
                            }

                            if partition_set.contains(&species_idx) {
                                group_count += count as u32;
                                group_sum += sum;
                                group_sumsq = group_sumsq.saturating_add(sumsq);
                                group_n_with_len += count_with_len as u32;

                                let start_idx = rel_off;
                                for i in 0..count {
                                    let seq_idx = members[start_idx + i] as usize;
                                    let len = seq_len[seq_idx];
                                    if len != u32::MAX { group_vals.push(len); }
                                }
                            } else {
                                other_count += count as u32;
                                other_sum += sum;
                                other_sumsq = other_sumsq.saturating_add(sumsq);
                                other_n_with_len += count_with_len as u32;
                                let start_idx = rel_off;
                                for i in 0..count {
                                    let seq_idx = members[start_idx + i] as usize;
                                    let len = seq_len[seq_idx];
                                    if len != u32::MAX { other_vals.push(len); }
                                }
                            }

                            off += entry_size;
                        }

                        // build per-species count vectors for MWU
                        let mut group_counts_per_species: Vec<f64> = Vec::with_capacity(mi_ref.species_count());
                        let mut other_counts_per_species: Vec<f64> = Vec::with_capacity(mi_ref.species_count());
                        for i in 0..mi_ref.species_count() {
                            if partition_set.contains(&i) {
                                group_counts_per_species.push(counts_by_species[i] as f64);
                            } else {
                                other_counts_per_species.push(counts_by_species[i] as f64);
                            }
                        }

                        let group_mean = if group_n_with_len > 0 { (group_sum as f64) / (group_n_with_len as f64) } else { f64::NAN };
                        let other_mean = if other_n_with_len > 0 { (other_sum as f64) / (other_n_with_len as f64) } else { f64::NAN };

                        let group_sd = if group_n_with_len > 1 {
                            let n = group_n_with_len as f64;
                            let var = (group_sumsq as f64 - (group_sum as f64 * group_sum as f64 / n)) / (n - 1.0);
                            var.max(0.0).sqrt()
                        } else { f64::NAN };

                        let other_sd = if other_n_with_len > 1 {
                            let n = other_n_with_len as f64;
                            let var = (other_sumsq as f64 - (other_sum as f64 * other_sum as f64 / n)) / (n - 1.0);
                            var.max(0.0).sqrt()
                        } else { f64::NAN };

                        let group_median = if !group_vals.is_empty() {
                            group_vals.sort_unstable();
                            let m = group_vals.len();
                            if m % 2 == 1 { group_vals[m/2] as f64 } else { ((group_vals[m/2 - 1] as f64) + (group_vals[m/2] as f64)) / 2.0 }
                        } else { f64::NAN };

                        let other_median = if !other_vals.is_empty() {
                            other_vals.sort_unstable();
                            let m = other_vals.len();
                            if m % 2 == 1 { other_vals[m/2] as f64 } else { ((other_vals[m/2 - 1] as f64) + (other_vals[m/2] as f64)) / 2.0 }
                        } else { f64::NAN };

                        // Mann-Whitney per-cluster on per-species counts
                        let (mw_u, mw_p) = if group_counts_per_species.is_empty() || other_counts_per_species.is_empty() {
                            (f64::NAN, f64::NAN)
                        } else {
                            let (u, p) = kinfin_stats::mannwhitney_rust(&group_counts_per_species, &other_counts_per_species, "two-sided");
                            (u, p)
                        };

                        cluster_idxs.push(ci as u32);
                        group_counts.push(group_count);
                        other_counts.push(other_count);
                        group_means.push(group_mean);
                        other_means.push(other_mean);
                        group_sds.push(group_sd);
                        other_sds.push(other_sd);
                        group_medians.push(group_median);
                        other_medians.push(other_median);
                        // length totals/means/medians (use NaN for missing)
                        let group_length_total = if group_n_with_len > 0 { group_sum as f64 } else { f64::NAN };
                        let other_length_total = if other_n_with_len > 0 { other_sum as f64 } else { f64::NAN };
                        group_lengths.push(group_length_total);
                        group_length_means.push(group_mean);
                        group_length_medians.push(group_median);
                        other_lengths.push(other_length_total);
                        other_length_means.push(other_mean);
                        other_length_medians.push(other_median);

                        // taxa counts
                        let mut g_taxa: u32 = 0;
                        let mut o_taxa: u32 = 0;
                        for i in 0..mi_ref.species_count() {
                            if partition_set.contains(&i) {
                                if counts_by_species[i] > 0 { g_taxa += 1; }
                            } else {
                                if counts_by_species[i] > 0 { o_taxa += 1; }
                            }
                        }
                        group_taxa_counts.push(g_taxa);
                        other_taxa_counts.push(o_taxa);

                        // mean counts per species and lg2 ratio (NaN if undefined)
                        let group_mean_count = if !group_counts_per_species.is_empty() { group_counts_per_species.iter().sum::<f64>() / (group_counts_per_species.len() as f64) } else { f64::NAN };
                        let other_mean_count = if !other_counts_per_species.is_empty() { other_counts_per_species.iter().sum::<f64>() / (other_counts_per_species.len() as f64) } else { f64::NAN };
                        let lg2v = if other_mean_count > 0.0 { (group_mean_count / other_mean_count).log2() } else { f64::NAN };
                        lg2_mean_count_over_others.push(lg2v);
                        mann_whitney_us.push(mw_u);
                        mann_whitney_ps.push(mw_p);
                    }
                });
            }

            // convert arrays into a Python dict-of-lists (one allocation per array)
            let py_batch = Python::with_gil(|py| -> PyResult<PyObject> {
                let dict = PyDict::new(py);
                dict.set_item("cluster_idx", PyList::new(py, &cluster_idxs))?;
                dict.set_item("group_count", PyList::new(py, &group_counts))?;
                dict.set_item("other_count", PyList::new(py, &other_counts))?;
                dict.set_item("group_mean", PyList::new(py, &group_means))?;
                dict.set_item("other_mean", PyList::new(py, &other_means))?;
                dict.set_item("group_sd", PyList::new(py, &group_sds))?;
                dict.set_item("other_sd", PyList::new(py, &other_sds))?;
                dict.set_item("group_median", PyList::new(py, &group_medians))?;
                dict.set_item("other_median", PyList::new(py, &other_medians))?;
                dict.set_item("group_length", PyList::new(py, &group_lengths))?;
                dict.set_item("group_length_mean", PyList::new(py, &group_length_means))?;
                dict.set_item("group_length_median", PyList::new(py, &group_length_medians))?;
                dict.set_item("other_length", PyList::new(py, &other_lengths))?;
                dict.set_item("other_length_mean", PyList::new(py, &other_length_means))?;
                dict.set_item("other_length_median", PyList::new(py, &other_length_medians))?;
                dict.set_item("group_taxa_count", PyList::new(py, &group_taxa_counts))?;
                dict.set_item("other_taxa_count", PyList::new(py, &other_taxa_counts))?;
                dict.set_item("lg2_mean_count_over_other", PyList::new(py, &lg2_mean_count_over_others))?;
                dict.set_item("mann_whitney_u", PyList::new(py, &mann_whitney_us))?;
                dict.set_item("mann_whitney_p", PyList::new(py, &mann_whitney_ps))?;

                // return the dict object
                Ok(dict.into())
            })?;

            self.cluster_idx = end;
            return Ok(Some(py_batch));
        }

        Ok(None)
    }
}

#[pymodule]
fn kinfin_index_py(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(analyse_clusters, m)?)?;
    m.add_function(wrap_pyfunction!(analyse_clusters_memmap, m)?)?;
    m.add_class::<MemmapBatchIter>()?;
    Ok(())
}

#[pyfunction]
#[pyo3(signature = (index_path, partitions, callback=None, batch_size=256))]
fn analyse_clusters_memmap(py: Python, index_path: &str, partitions: Vec<Vec<usize>>, callback: Option<PyObject>, batch_size: usize) -> PyResult<()> {
    let path = std::path::Path::new(index_path);
    let mi = MemmapIndex::open(path).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("failed to open memmap index: {}", e)))?;
    let seq_len = mi.seq_len_raw_slice().map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("failed to read seq_len: {}", e)))?;
    let clusters_len = mi.cluster_count();

    for (p_idx, partition) in partitions.into_iter().enumerate() {
        let partition_set: std::collections::HashSet<usize> = partition.into_iter().collect();
        let mut cluster_idx = 0usize;
        while cluster_idx < clusters_len {
            let end = std::cmp::min(cluster_idx + batch_size, clusters_len);
            let mut rust_batch: Vec<StatsRow> = Vec::with_capacity(end - cluster_idx);

            py.allow_threads(|| {
                for ci in cluster_idx..end {
                    // aggregate using species entries
                    let members = mi.cluster_members_for(ci).unwrap();
                    let entries_bytes = mi.cluster_species_entries_bytes_for(ci).unwrap();
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

                    // parse entries: each entry is 32 bytes
                    let entry_size = 32usize;
                    let mut off = 0usize;
                    let mut counts_by_species: Vec<u32> = vec![0u32; mi.species_count()];
                    while off + entry_size <= entries_bytes.len() {
                        let species_idx = u32::from_le_bytes(entries_bytes[off..off+4].try_into().unwrap()) as usize;
                        let rel_off = u32::from_le_bytes(entries_bytes[off+4..off+8].try_into().unwrap()) as usize;
                        let count = u32::from_le_bytes(entries_bytes[off+8..off+12].try_into().unwrap()) as usize;
                        let count_with_len = u32::from_le_bytes(entries_bytes[off+12..off+16].try_into().unwrap()) as usize;
                        let sum = u64::from_le_bytes(entries_bytes[off+16..off+24].try_into().unwrap());
                        let sumsq = u64::from_le_bytes(entries_bytes[off+24..off+32].try_into().unwrap());

                        if species_idx < counts_by_species.len() {
                            counts_by_species[species_idx] = count as u32;
                        }

                        if partition_set.contains(&species_idx) {
                            group_count += count as u32;
                            group_sum += sum;
                            group_sumsq = group_sumsq.saturating_add(sumsq);
                            group_n_with_len += count_with_len as u32;

                            // collect individual lengths for median
                            let start_idx = rel_off;
                            for i in 0..count {
                                let seq_idx = members[start_idx + i] as usize;
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
                            let start_idx = rel_off;
                            for i in 0..count {
                                let seq_idx = members[start_idx + i] as usize;
                                let len = seq_len[seq_idx];
                                if len != u32::MAX {
                                    other_vals.push(len);
                                }
                            }
                        }
                        off += entry_size;
                    }

                    // build per-species count vectors for MWU
                    let mut group_counts_per_species: Vec<f64> = Vec::with_capacity(mi.species_count());
                    let mut other_counts_per_species: Vec<f64> = Vec::with_capacity(mi.species_count());
                    for i in 0..mi.species_count() {
                        if partition_set.contains(&i) {
                            group_counts_per_species.push(counts_by_species[i] as f64);
                        } else {
                            other_counts_per_species.push(counts_by_species[i] as f64);
                        }
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

                    // compute Mann-Whitney for this cluster on per-species counts
                    let (mw_u, mw_p) = if group_counts_per_species.is_empty() || other_counts_per_species.is_empty() {
                        (None, None)
                    } else {
                        let (u, p) = kinfin_stats::mannwhitney_rust(&group_counts_per_species, &other_counts_per_species, "two-sided");
                        (Some(u), Some(p))
                    };

                    // taxa counts
                    let mut g_taxa: u32 = 0;
                    let mut o_taxa: u32 = 0;
                    for i in 0..mi.species_count() {
                        if partition_set.contains(&i) {
                            if counts_by_species[i] > 0 { g_taxa += 1; }
                        } else {
                            if counts_by_species[i] > 0 { o_taxa += 1; }
                        }
                    }

                    // mean counts per species and lg2 ratio
                    let group_mean_count = if !group_counts_per_species.is_empty() { Some(group_counts_per_species.iter().sum::<f64>() / (group_counts_per_species.len() as f64)) } else { None };
                    let other_mean_count = if !other_counts_per_species.is_empty() { Some(other_counts_per_species.iter().sum::<f64>() / (other_counts_per_species.len() as f64)) } else { None };
                    let lg2 = match (group_mean_count, other_mean_count) {
                        (Some(g), Some(o)) if o > 0.0 => Some((g / o).log2()),
                        _ => None,
                    };

                    let group_length = if group_n_with_len > 0 { Some(group_sum as f64) } else { None };
                    let other_length = if other_n_with_len > 0 { Some(other_sum as f64) } else { None };

                    rust_batch.push(StatsRow{
                        cluster_id: String::new(),
                        group_count,
                        other_count,
                        group_mean,
                        other_mean,
                        group_sd,
                        other_sd,
                        group_median,
                        other_median,
                        mann_whitney_u: mw_u,
                        mann_whitney_p: mw_p,
                        group_length,
                        group_length_mean: group_mean,
                        group_length_median: group_median,
                        other_length,
                        other_length_mean: other_mean,
                        other_length_median: other_median,
                        group_taxa_count: g_taxa,
                        other_taxa_count: o_taxa,
                        lg2_mean_count_over_other: lg2,
                    });
                }
            });

            // call Python callback with batch
            if let Some(cb) = &callback {
                Python::with_gil(|py| -> PyResult<()> {
                    let cb_ref = cb.as_ref(py);
                    let py_list = PyList::empty(py);
                    for row in &rust_batch {
                        let dict = PyDict::new(py);
                        dict.set_item("cluster_id", row.cluster_id.clone())?;
                        dict.set_item("partition_idx", p_idx)?;
                        dict.set_item("group_count", row.group_count)?;
                        dict.set_item("other_count", row.other_count)?;
                        dict.set_item("group_mean", row.group_mean)?;
                        dict.set_item("other_mean", row.other_mean)?;
                        dict.set_item("group_sd", row.group_sd)?;
                        dict.set_item("other_sd", row.other_sd)?;
                        dict.set_item("group_median", row.group_median)?;
                        dict.set_item("other_median", row.other_median)?;
                        dict.set_item("mann_whitney_u", row.mann_whitney_u)?;
                        dict.set_item("mann_whitney_p", row.mann_whitney_p)?;
                        dict.set_item("group_length", row.group_length)?;
                        dict.set_item("group_length_mean", row.group_length_mean)?;
                        dict.set_item("group_length_median", row.group_length_median)?;
                        dict.set_item("other_length", row.other_length)?;
                        dict.set_item("other_length_mean", row.other_length_mean)?;
                        dict.set_item("other_length_median", row.other_length_median)?;
                        dict.set_item("group_taxa_count", row.group_taxa_count)?;
                        dict.set_item("other_taxa_count", row.other_taxa_count)?;
                        dict.set_item("lg2_mean_count_over_other", row.lg2_mean_count_over_other)?;
                        py_list.append(dict)?;
                    }
                    cb_ref.call1((py_list,))?;
                    Ok(())
                })?;
            }

            cluster_idx = end;
        }
    }

    Ok(())
}
