#[cfg(feature = "python")]
use pyo3::prelude::*;
#[cfg(feature = "python")]
use pyo3::types::PyModule;
use statrs::distribution::{ContinuousCDF, Normal};

/// Calculate the rank of values in a combined sorted array
/// Returns the sum of ranks for the first group
fn mannwhitneyu_statistic(x: &[f64], y: &[f64]) -> (f64, usize, usize) {
    let n1 = x.len();
    let n2 = y.len();

    // Combine values with their group indicator
    let mut combined: Vec<(f64, usize)> = Vec::with_capacity(n1 + n2);

    for &val in x {
        combined.push((val, 0)); // 0 = group x
    }
    for &val in y {
        combined.push((val, 1)); // 1 = group y
    }

    // Sort by value
    combined.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(std::cmp::Ordering::Equal));

    // Assign ranks and handle ties
    let mut ranks: Vec<f64> = vec![0.0; n1 + n2];
    let mut i = 0;

    while i < combined.len() {
        // Find range of equal values
        let mut j = i;
        while j < combined.len() && (combined[j].0 - combined[i].0).abs() < 1e-15 {
            j += 1;
        }

        // Assign average rank to all tied values
        let avg_rank = ((i + j) as f64 + 1.0) / 2.0;
        for idx in i..j {
            ranks[idx] = avg_rank;
        }

        i = j;
    }

    // Sum ranks for group x
    let mut rank_sum_x = 0.0;
    for (idx, (_, group)) in combined.iter().enumerate() {
        if *group == 0 {
            rank_sum_x += ranks[idx];
        }
    }

    // Calculate U statistic
    let u1 = rank_sum_x - (n1 as f64) * (n1 as f64 + 1.0) / 2.0;

    (u1, n1, n2)
}

/// Normal CDF via statrs (matches scipy ndtr to floating-point precision)
fn normal_cdf(x: f64) -> f64 {
    Normal::new(0.0, 1.0).unwrap().cdf(x)
}

/// Exact two-sided p-value for Mann-Whitney U via DP over rank sequences.
///
/// Matches scipy.stats.mannwhitneyu method='exact' (no ties assumed).
/// m = min(n1, n2), n = max(n1, n2), u_obs_min = min(U1, U2).
///
/// Recurrence: f(k, i, j) = f(k, i-1, j) + f(k-i, i, j-1)
///   where f(k, i, j) = number of interleavings of i X's and j Y's with U_X = k.
/// Time: O(m^2 * n^2), Space: O(m * m*n).
fn mannwhitneyu_exact_pvalue(u_obs_min: usize, m: usize, n: usize) -> f64 {
    let max_u = m * n;
    let width = max_u + 1;

    // prev[i * width + k] = f(k, i, j-1),  cur[i * width + k] = f(k, i, j)
    let mut prev = vec![0.0f64; (m + 1) * width];
    let mut cur = vec![0.0f64; (m + 1) * width];

    // Base case j=0: f(0, i, 0) = 1 for all i (only U=0 is possible with no Y's)
    for i in 0..=m {
        prev[i * width] = 1.0;
    }

    for _j in 1..=n {
        for v in cur.iter_mut() {
            *v = 0.0;
        }
        cur[0] = 1.0; // f(0, 0, j) = 1
        for i in 1..=m {
            let base = i * width;
            let base_im1 = (i - 1) * width;
            for k in 0..=max_u {
                let from_x = cur[base_im1 + k]; // f(k, i-1, j)
                let from_y = if k >= i { prev[base + k - i] } else { 0.0 }; // f(k-i, i, j-1)
                cur[base + k] = from_x + from_y;
            }
        }
        std::mem::swap(&mut prev, &mut cur);
    }

    // prev now holds f(k, *, n)
    let base_m = m * width;
    let total: f64 = prev[base_m..base_m + width].iter().sum();
    if total == 0.0 {
        return 1.0;
    }
    let p_le: f64 = prev[base_m..base_m + u_obs_min + 1].iter().sum::<f64>() / total;
    (2.0 * p_le).min(1.0)
}

/// Calculate Mann-Whitney U test p-value
///
/// Args:
///     x: First sample (list/array of numbers)
///     y: Second sample (list/array of numbers)
///     alternative: "two-sided", "less", or "greater" (default: "two-sided")
///
/// Returns:
///     Tuple of (statistic, p-value)
#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(signature = (x, y, alternative = "two-sided"))]
fn mannwhitneyu(x: Vec<f64>, y: Vec<f64>, alternative: &str) -> PyResult<(f64, f64)> {
    let n1 = x.len();
    let n2 = y.len();

    // Handle edge cases
    if n1 == 0 || n2 == 0 {
        return Ok((f64::NAN, 1.0));
    }

    // Calculate U statistic
    let (u1, _, _) = mannwhitneyu_statistic(&x, &y);
    let u2 = (n1 * n2) as f64 - u1;
    let u_min = u1.min(u2);

    // Check for ties (exact method requires no ties)
    let has_ties = {
        let mut all: Vec<u64> = x.iter().chain(y.iter()).map(|v| v.to_bits()).collect();
        all.sort_unstable();
        all.windows(2).any(|w| w[0] == w[1])
    };

    // Use exact method when min(n1, n2) <= 8 and no ties (matches scipy 'auto')
    if !has_ties && n1 <= 8 || !has_ties && n2 <= 8 {
        let m = n1.min(n2);
        let n = n1.max(n2);
        let u_obs_min = u_min as usize;
        let p = mann_exact_for_alternative(u_obs_min, u_min as usize, m, n, alternative)?;
        return Ok((u_min, p));
    }

    // Asymptotic path with tie-corrected variance (matches scipy _get_mwu_z)
    let n1_f = n1 as f64;
    let n2_f = n2 as f64;
    let n_total = (n1 + n2) as f64;
    let mean_u = (n1_f * n2_f) / 2.0;

    // Build combined sorted sequence to compute tie runs (needed for variance correction)
    // We reuse the sorted order from mannwhitneyu_statistic indirectly via the rank computation;
    // here we just need the tie run lengths.
    let tie_term: f64 = {
        let mut all: Vec<f64> = x.iter().chain(y.iter()).copied().collect();
        all.sort_unstable_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        let mut sum = 0.0f64;
        let mut i = 0;
        while i < all.len() {
            let mut j = i + 1;
            while j < all.len() && (all[j] - all[i]).abs() < 1e-15 {
                j += 1;
            }
            let t = (j - i) as f64;
            sum += t * t * t - t;
            i = j;
        }
        sum
    };
    let var_u = n1_f * n2_f / 12.0 * ((n_total + 1.0) - tie_term / (n_total * (n_total - 1.0)));

    if var_u <= 0.0 {
        return Ok((u_min, 1.0));
    }

    // scipy: z = (U_max - 0.5 - mean_u) / s, p = 2*sf(z).
    // Equivalent with u_min: z = (u_min + 0.5 - mean_u) / s, p = 2*CDF(z).
    let p_value = match alternative {
        "two-sided" => {
            let z = (u_min + 0.5 - mean_u) / var_u.sqrt();
            (2.0 * normal_cdf(z)).clamp(0.0, 1.0)
        }
        "less" => {
            let z = (u1 + 0.5 - mean_u) / var_u.sqrt();
            normal_cdf(z).clamp(0.0, 1.0)
        }
        "greater" => {
            let z = (u1 - 0.5 - mean_u) / var_u.sqrt();
            1.0 - normal_cdf(z)
        }
        _ => {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Unknown alternative: {}",
                alternative
            )))
        }
    };

    Ok((u_min, p_value.clamp(0.0, 1.0)))
}

/// Public Rust API wrapper for Mann-Whitney U (returns (u, p)).
/// Uses the same logic as the pyo3-exposed `mannwhitneyu`.
pub fn mannwhitney_rust(x: &[f64], y: &[f64], alternative: &str) -> (f64, f64) {
    let n1 = x.len();
    let n2 = y.len();
    if n1 == 0 || n2 == 0 {
        return (f64::NAN, 1.0);
    }

    let (u1, _, _) = mannwhitneyu_statistic(x, y);
    let u2 = (n1 * n2) as f64 - u1;
    let u_min = u1.min(u2);

    // Check for ties
    let has_ties = {
        let mut all: Vec<u64> = x.iter().chain(y.iter()).map(|v| v.to_bits()).collect();
        all.sort_unstable();
        all.windows(2).any(|w| w[0] == w[1])
    };

    // Exact when small and no ties
    if (!has_ties && n1 <= 8) || (!has_ties && n2 <= 8) {
        let m = n1.min(n2);
        let n = n1.max(n2);
        let u_obs_min = u_min as usize;
        if let Ok(p) = mann_exact_for_alternative_rust(u_obs_min, u_min as usize, m, n, alternative)
        {
            return (u_min, p);
        } else {
            return (u_min, 1.0);
        }
    }

    // Asymptotic with tie correction
    let n1_f = n1 as f64;
    let n2_f = n2 as f64;
    let n_total = (n1 + n2) as f64;
    let mean_u = (n1_f * n2_f) / 2.0;

    let tie_term: f64 = {
        let mut all: Vec<f64> = x.iter().chain(y.iter()).copied().collect();
        all.sort_unstable_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        let mut sum = 0.0f64;
        let mut i = 0;
        while i < all.len() {
            let mut j = i + 1;
            while j < all.len() && (all[j] - all[i]).abs() < 1e-15 {
                j += 1;
            }
            let t = (j - i) as f64;
            sum += t * t * t - t;
            i = j;
        }
        sum
    };
    let var_u = n1_f * n2_f / 12.0 * ((n_total + 1.0) - tie_term / (n_total * (n_total - 1.0)));
    if var_u <= 0.0 {
        return (u_min, 1.0);
    }

    let p_value = match alternative {
        "two-sided" => {
            let z = (u_min + 0.5 - mean_u) / var_u.sqrt();
            (2.0 * normal_cdf(z)).clamp(0.0, 1.0)
        }
        "less" => {
            let z = (u1 + 0.5 - mean_u) / var_u.sqrt();
            normal_cdf(z).clamp(0.0, 1.0)
        }
        "greater" => {
            let z = (u1 - 0.5 - mean_u) / var_u.sqrt();
            1.0 - normal_cdf(z)
        }
        _ => 1.0,
    };

    (u_min, p_value.clamp(0.0, 1.0))
}

/// Pure-Rust exact p-value helper (no pyo3 types). Returns Err for unknown alternative.
fn mann_exact_for_alternative_rust(
    u_obs_min: usize,
    u1_usize: usize,
    m: usize,
    n: usize,
    alternative: &str,
) -> Result<f64, &'static str> {
    match alternative {
        "two-sided" => Ok(mannwhitneyu_exact_pvalue(u_obs_min, m, n)),
        "less" => Ok(mannwhitneyu_exact_pvalue(u1_usize.min(m * n), m, n) / 2.0),
        "greater" => Ok(mannwhitneyu_exact_pvalue((m * n).saturating_sub(u1_usize), m, n) / 2.0),
        _ => Err("Unknown alternative"),
    }
}

// pyo3 wrapper for the exact helper, compiled only when the python feature is enabled.
#[cfg(feature = "python")]
fn mann_exact_for_alternative(
    u_obs_min: usize,
    u1_usize: usize,
    m: usize,
    n: usize,
    alternative: &str,
) -> PyResult<f64> {
    match mann_exact_for_alternative_rust(u_obs_min, u1_usize, m, n, alternative) {
        Ok(v) => Ok(v),
        Err(e) => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
            "{}",
            e
        ))),
    }
}

/// Fast t-test implementation
///
/// Args:
///     x: First sample
///     y: Second sample
///
/// Returns:
///     Tuple of (t_statistic, p_value)
#[cfg(feature = "python")]
#[pyfunction]
fn ttest_ind(x: Vec<f64>, y: Vec<f64>) -> PyResult<(f64, f64)> {
    if x.is_empty() || y.is_empty() {
        return Ok((f64::NAN, 1.0));
    }

    // Calculate means
    let mean_x: f64 = x.iter().sum::<f64>() / x.len() as f64;
    let mean_y: f64 = y.iter().sum::<f64>() / y.len() as f64;

    // Calculate variances
    let n1 = x.len();
    let n2 = y.len();

    if n1 < 2 || n2 < 2 {
        return Ok((f64::NAN, 1.0));
    }

    let var_x: f64 = x.iter().map(|v| (v - mean_x).powi(2)).sum::<f64>() / (n1 - 1) as f64;
    let var_y: f64 = y.iter().map(|v| (v - mean_y).powi(2)).sum::<f64>() / (n2 - 1) as f64;

    if var_x == 0.0 && var_y == 0.0 {
        return Ok((0.0, 1.0));
    }

    // Welch's t-test (doesn't assume equal variances)
    let se = (var_x / n1 as f64 + var_y / n2 as f64).sqrt();
    if se == 0.0 {
        return Ok((f64::NAN, 1.0));
    }

    let t = (mean_x - mean_y) / se;

    // Approximate p-value using normal distribution
    let p_value = 2.0 * (1.0 - normal_cdf(t.abs()));

    Ok((t, p_value.clamp(0.0, 1.0)))
}

/// Kolmogorov-Smirnov test for two samples
#[cfg(feature = "python")]
#[pyfunction]
fn ks_2samp(x: Vec<f64>, y: Vec<f64>) -> PyResult<(f64, f64)> {
    if x.is_empty() || y.is_empty() {
        return Ok((f64::NAN, 1.0));
    }

    let mut x_sorted = x.clone();
    let mut y_sorted = y.clone();
    x_sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    y_sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));

    // Compute empirical CDFs and find max difference
    let mut max_diff: f64 = 0.0;
    let mut i = 0;
    let mut j = 0;
    let n1 = x_sorted.len() as f64;
    let n2 = y_sorted.len() as f64;

    while i < x_sorted.len() && j < y_sorted.len() {
        let cdf_x = (i as f64 + 1.0) / n1;
        let cdf_y = (j as f64 + 1.0) / n2;

        if x_sorted[i] < y_sorted[j] {
            max_diff = max_diff.max((cdf_x - j as f64 / n2).abs());
            i += 1;
        } else if x_sorted[i] > y_sorted[j] {
            max_diff = max_diff.max((i as f64 / n1 - cdf_y).abs());
            j += 1;
        } else {
            max_diff = max_diff.max((cdf_x - cdf_y).abs());
            i += 1;
            j += 1;
        }
    }

    // Remaining points
    while i < x_sorted.len() {
        max_diff = max_diff.max((1.0 - j as f64 / n2).abs());
        i += 1;
    }
    while j < y_sorted.len() {
        max_diff = max_diff.max((1.0 - i as f64 / n1).abs());
        j += 1;
    }

    // Approximate p-value
    let en = (n1 * n2 / (n1 + n2)).sqrt();
    let p_value = (-2.0 * (en * max_diff).powi(2)).exp().clamp(0.0, 1.0);

    Ok((max_diff, p_value))
}

/// Kruskal-Wallis H-test for two samples
#[cfg(feature = "python")]
#[pyfunction]
fn kruskal(x: Vec<f64>, y: Vec<f64>) -> PyResult<(f64, f64)> {
    if x.is_empty() || y.is_empty() {
        return Ok((f64::NAN, 1.0));
    }

    // Combine and rank
    let mut combined: Vec<(f64, usize)> = Vec::new();
    for &val in &x {
        combined.push((val, 0));
    }
    for &val in &y {
        combined.push((val, 1));
    }

    combined.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(std::cmp::Ordering::Equal));

    let mut ranks: Vec<f64> = vec![0.0; combined.len()];
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

    // Sum ranks by group
    let mut rank_sum_x = 0.0;
    let mut rank_sum_y = 0.0;
    for (idx, (_, group)) in combined.iter().enumerate() {
        if *group == 0 {
            rank_sum_x += ranks[idx];
        } else {
            rank_sum_y += ranks[idx];
        }
    }

    let n = combined.len() as f64;
    let n1 = x.len() as f64;
    let n2 = y.len() as f64;

    // H statistic
    let h = 12.0 / (n * (n + 1.0)) * (rank_sum_x.powi(2) / n1 + rank_sum_y.powi(2) / n2)
        - 3.0 * (n + 1.0);

    // Approximate p-value using chi-squared distribution with 1 df
    let p_value = (-h / 2.0).exp().clamp(0.0, 1.0);

    Ok((h, p_value))
}

/// Batch Mann-Whitney U test - reduced FFI overhead for multiple test pairs
///
/// Args:
///     test_pairs: List of (x, y) sample pairs as Vec<(Vec<f64>, Vec<f64>)>
///     alternative: One of "two-sided", "less", "greater"
///
/// Returns:
///     List of (u_statistic, p_value) tuples
#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(signature = (test_pairs, alternative = "two-sided"))]
fn batch_mannwhitneyu(
    test_pairs: Vec<(Vec<f64>, Vec<f64>)>,
    alternative: &str,
) -> PyResult<Vec<(f64, f64)>> {
    Ok(test_pairs
        .into_iter()
        .map(|(x, y)| mannwhitneyu(x, y, alternative).unwrap_or((f64::NAN, 1.0)))
        .collect())
}

/// Batch t-test implementation - reduced FFI overhead for multiple test pairs
///
/// Args:
///     test_pairs: List of (x, y) sample pairs
///
/// Returns:
///     List of (t_statistic, p_value) tuples
#[cfg(feature = "python")]
#[pyfunction]
fn batch_ttest_ind(test_pairs: Vec<(Vec<f64>, Vec<f64>)>) -> PyResult<Vec<(f64, f64)>> {
    Ok(test_pairs
        .into_iter()
        .map(|(x, y)| ttest_ind(x, y).unwrap_or((f64::NAN, 1.0)))
        .collect())
}

/// Batch Kolmogorov-Smirnov test - reduced FFI overhead for multiple test pairs
///
/// Args:
///     test_pairs: List of (x, y) sample pairs
///
/// Returns:
///     List of (ks_statistic, p_value) tuples
#[cfg(feature = "python")]
#[pyfunction]
fn batch_ks_2samp(test_pairs: Vec<(Vec<f64>, Vec<f64>)>) -> PyResult<Vec<(f64, f64)>> {
    Ok(test_pairs
        .into_iter()
        .map(|(x, y)| ks_2samp(x, y).unwrap_or((f64::NAN, 1.0)))
        .collect())
}

/// Batch Kruskal-Wallis test - reduced FFI overhead for multiple test pairs
///
/// Args:
///     test_pairs: List of (x, y) sample pairs
///
/// Returns:
///     List of (h_statistic, p_value) tuples
#[cfg(feature = "python")]
#[pyfunction]
fn batch_kruskal(test_pairs: Vec<(Vec<f64>, Vec<f64>)>) -> PyResult<Vec<(f64, f64)>> {
    Ok(test_pairs
        .into_iter()
        .map(|(x, y)| kruskal(x, y).unwrap_or((f64::NAN, 1.0)))
        .collect())
}

/// Python module definition
#[cfg(feature = "python")]
#[pymodule]
fn kinfin_stats(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(mannwhitneyu, m)?)?;
    m.add_function(wrap_pyfunction!(ttest_ind, m)?)?;
    m.add_function(wrap_pyfunction!(ks_2samp, m)?)?;
    m.add_function(wrap_pyfunction!(kruskal, m)?)?;
    m.add_function(wrap_pyfunction!(batch_mannwhitneyu, m)?)?;
    m.add_function(wrap_pyfunction!(batch_ttest_ind, m)?)?;
    m.add_function(wrap_pyfunction!(batch_ks_2samp, m)?)?;
    m.add_function(wrap_pyfunction!(batch_kruskal, m)?)?;
    Ok(())
}
