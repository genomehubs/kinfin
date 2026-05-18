use kinfin_stats::mannwhitney_rust;

#[test]
fn mann_whitney_basic() {
    // fully separated samples: group small, other large
    let a = vec![1.0f64, 2.0f64, 3.0f64];
    let b = vec![4.0f64, 5.0f64, 6.0f64];

    let (u, p) = mannwhitney_rust(&a, &b, "two-sided");
    // for these samples U should be 0 (or the minimum) and p should be <= 0.06 (approx)
    assert!(u <= 0.5);
    assert!(p >= 0.0 && p <= 0.1);
}

#[test]
fn mann_whitney_ties() {
    let a = vec![1.0f64, 1.0f64, 2.0f64];
    let b = vec![1.0f64, 2.0f64, 3.0f64];
    let (_u, p) = mannwhitney_rust(&a, &b, "two-sided");
    assert!(p >= 0.0 && p <= 1.0);
}
