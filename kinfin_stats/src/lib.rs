use pyo3::prelude::*;
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

/// Calculate Mann-Whitney U test p-value
///
/// Args:
///     x: First sample (list/array of numbers)
///     y: Second sample (list/array of numbers)
///     alternative: "two-sided", "less", or "greater" (default: "two-sided")
///
/// Returns:
///     Tuple of (statistic, p-value)
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
    let u = u1.min(u2); // Use smaller U for two-sided test

    // Mean and variance of U distribution
    let n1_f = n1 as f64;
    let n2_f = n2 as f64;
    let mean_u = (n1_f * n2_f) / 2.0;
    let var_u = (n1_f * n2_f * (n1_f + n2_f + 1.0)) / 12.0;

    // Avoid division by zero
    if var_u == 0.0 {
        return Ok((u, 1.0)); // All values are equal
    }

    // Z-score with continuity correction
    let z = (u + 0.5 - mean_u) / var_u.sqrt();

    // Calculate p-value based on alternative
    let p_value = match alternative {
        "two-sided" => 2.0 * (1.0 - normal_cdf(z.abs())),
        "less" => normal_cdf(z),
        "greater" => 1.0 - normal_cdf(z),
        _ => {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Unknown alternative: {}",
                alternative
            )))
        }
    };

    Ok((u, p_value.clamp(0.0, 1.0)))
}

/// Fast t-test implementation
///
/// Args:
///     x: First sample
///     y: Second sample
///
/// Returns:
///     Tuple of (t_statistic, p_value)
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
#[pyfunction]
fn batch_kruskal(test_pairs: Vec<(Vec<f64>, Vec<f64>)>) -> PyResult<Vec<(f64, f64)>> {
    Ok(test_pairs
        .into_iter()
        .map(|(x, y)| kruskal(x, y).unwrap_or((f64::NAN, 1.0)))
        .collect())
}

/// Python module definition
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
