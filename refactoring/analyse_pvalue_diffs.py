#!/usr/bin/env python3
"""
Analyse p-value differences between Python (scipy) and Rust MWU implementations,
bucketed by cluster size (total proteins, ALO side count, non-ALO side count).

Usage:
    python analyse_pvalue_diffs.py \
        --py   /tmp/nem_py_results.tsv \
        --rust /tmp/nem_rust_results.tsv \
        --prefix nem \
        --title "Nematodes"

    python analyse_pvalue_diffs.py \
        --py   /tmp/lep_py_results.tsv \
        --rust /tmp/lep_rust_results.tsv \
        --prefix lep \
        --title "Lepidoptera"
"""
import argparse
import csv
import math
import os
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


# ---------------------------------------------------------------------------
# Loading — streaming for large files
# ---------------------------------------------------------------------------

def load_results(path: str) -> dict:
    """Load TSV results. Returns dict keyed by (cluster_id, attribute, level)."""
    rows = {}
    with open(path) as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for row in reader:
            key = (row["cluster_id"], row["attribute"], row["level"])
            rows[key] = row
    return rows


def stream_comparison(py_path: str, rust_path: str):
    """
    Generator that yields one comparison record at a time.
    Streams both files simultaneously keyed by (cluster_id, attribute, level),
    so only one row per file is in memory at a time on the hot path.
    Requires both files to have the same row order (they do — same cluster loop).
    """
    with open(py_path) as py_fh, open(rust_path) as rust_fh:
        py_reader = csv.DictReader(py_fh, delimiter="\t")
        rust_reader = csv.DictReader(rust_fh, delimiter="\t")
        for p, r in zip(py_reader, rust_reader):
            pv_py_s = p["mwu_pvalue"]
            pv_rust_s = r["mwu_pvalue"]
            if not pv_py_s or not pv_rust_s:
                continue
            pv_py = float(pv_py_s)
            pv_rust = float(pv_rust_s)
            if pv_py == 0 and pv_rust == 0:
                continue
            abs_diff = abs(pv_py - pv_rust)
            rel_diff = abs_diff / max(abs(pv_py), 1e-300)
            alo_prot = int(p["protein_count"])
            yield {
                "cluster_id": p["cluster_id"],
                "attribute": p["attribute"],
                "level": p["level"],
                "pv_py": pv_py,
                "pv_rust": pv_rust,
                "abs_diff": abs_diff,
                "rel_diff": rel_diff,
                "alo_prot": alo_prot,
                "alo_bin": bin_label(alo_prot),
            }


# ---------------------------------------------------------------------------
# Binning helpers
# ---------------------------------------------------------------------------

SIZE_BINS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 30, 50, 100, 200, 500, float("inf")]
SIZE_LABELS = [
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
    "11-15", "16-20", "21-30", "31-50", "51-100", "101-200", "201-500", ">500",
]

def bin_label(n: int) -> str:
    for i in range(len(SIZE_BINS) - 1):
        if SIZE_BINS[i] <= n < SIZE_BINS[i + 1]:
            return SIZE_LABELS[i]
    return SIZE_LABELS[-1]


# ---------------------------------------------------------------------------
# Build comparison table — streaming, accumulates only per-bin data
# ---------------------------------------------------------------------------

def build_comparison(py_rows: dict, rust_rows: dict) -> list:
    """Return list of dicts for every row with a non-null p-value in both.
    Used for small datasets (nematodes). For large datasets use stream_comparison."""
    records = []
    for key in py_rows:
        if key not in rust_rows:
            continue
        p = py_rows[key]
        r = rust_rows[key]
        pv_py_s = p["mwu_pvalue"]
        pv_rust_s = r["mwu_pvalue"]
        if not pv_py_s or not pv_rust_s:
            continue
        pv_py = float(pv_py_s)
        pv_rust = float(pv_rust_s)
        if pv_py == 0 and pv_rust == 0:
            continue
        abs_diff = abs(pv_py - pv_rust)
        rel_diff = abs_diff / max(abs(pv_py), 1e-300)
        alo_prot = int(p["protein_count"])
        records.append({
            "cluster_id": key[0],
            "attribute": key[1],
            "level": key[2],
            "pv_py": pv_py,
            "pv_rust": pv_rust,
            "abs_diff": abs_diff,
            "rel_diff": rel_diff,
            "alo_prot": alo_prot,
            "alo_bin": bin_label(alo_prot),
        })
    return records


def accumulate_streaming(py_path: str, rust_path: str):
    """
    Stream both result files together and accumulate only per-bin stats and
    a random sample of records for scatter plots. Memory-efficient for large datasets.
    Returns (bin_data, sample, summary_counts).
    """
    SAMPLE_LIMIT = 50000
    bin_data = defaultdict(lambda: {"rel": [], "abs": [], "pv_py": [], "pv_rust": []})
    sample = []
    total = agree = flips = 0
    import random
    rng = random.Random(42)

    with open(py_path) as py_fh, open(rust_path) as rust_fh:
        py_reader = csv.DictReader(py_fh, delimiter="\t")
        rust_reader = csv.DictReader(rust_fh, delimiter="\t")
        for p, r in zip(py_reader, rust_reader):
            pv_py_s = p["mwu_pvalue"]
            pv_rust_s = r["mwu_pvalue"]
            if not pv_py_s or not pv_rust_s:
                continue
            pv_py = float(pv_py_s)
            pv_rust = float(pv_rust_s)
            if pv_py == 0 and pv_rust == 0:
                continue

            abs_diff = abs(pv_py - pv_rust)
            rel_diff = abs_diff / max(abs(pv_py), 1e-300)
            alo_prot = int(p["protein_count"])
            lb = bin_label(alo_prot)

            bin_data[lb]["rel"].append(rel_diff)
            bin_data[lb]["abs"].append(abs_diff)
            bin_data[lb]["pv_py"].append(pv_py)
            bin_data[lb]["pv_rust"].append(pv_rust)

            sig_py = pv_py < 0.05
            sig_rust = pv_rust < 0.05
            total += 1
            if sig_py == sig_rust:
                agree += 1
            else:
                flips += 1

            # Reservoir sampling for scatter plot
            if len(sample) < SAMPLE_LIMIT:
                sample.append((pv_py, pv_rust))
            else:
                j = rng.randint(0, total)
                if j < SAMPLE_LIMIT:
                    sample[j] = (pv_py, pv_rust)

    return bin_data, sample, {"total": total, "agree": agree, "flips": flips}


# ---------------------------------------------------------------------------
# Per-bin stats — works from either records list or bin_data dict
# ---------------------------------------------------------------------------

def bin_stats_from_records(records: list, bin_col: str = "alo_bin") -> list:
    """Compute per-bin summary stats from a list of records (small datasets)."""
    bins = defaultdict(list)
    for rec in records:
        bins[rec[bin_col]].append(rec)

    rows = []
    for label in SIZE_LABELS:
        bucket = bins.get(label, [])
        if not bucket:
            continue
        rel = [r["rel_diff"] for r in bucket]
        absd = [r["abs_diff"] for r in bucket]
        pv_py = [r["pv_py"] for r in bucket]
        pv_rust = [r["pv_rust"] for r in bucket]
        rows.append(_make_bin_row(label, len(bucket), rel, absd, pv_py, pv_rust))
    return rows


def bin_stats_from_dict(bin_data: dict) -> list:
    """Compute per-bin summary stats from streaming accumulator dict."""
    rows = []
    for label in SIZE_LABELS:
        d = bin_data.get(label)
        if not d or not d["rel"]:
            continue
        rows.append(_make_bin_row(
            label, len(d["rel"]), d["rel"], d["abs"], d["pv_py"], d["pv_rust"]
        ))
    return rows


def _make_bin_row(label, n, rel, absd, pv_py, pv_rust):
    pct_sig_py = 100 * sum(1 for v in pv_py if v < 0.05) / len(pv_py) if pv_py else 0
    pct_sig_rust = 100 * sum(1 for v in pv_rust if v < 0.05) / len(pv_rust) if pv_rust else 0
    agree = sum(1 for p, r in zip(pv_py, pv_rust) if (p < 0.05) == (r < 0.05))
    return {
        "bin": label,
        "n": n,
        "rel_diff_mean": np.mean(rel),
        "rel_diff_median": np.median(rel),
        "rel_diff_p95": np.percentile(rel, 95),
        "abs_diff_mean": np.mean(absd),
        "abs_diff_median": np.median(absd),
        "pct_sig_py": pct_sig_py,
        "pct_sig_rust": pct_sig_rust,
        "sig_agreement_pct": 100 * agree / n,
    }


# ---------------------------------------------------------------------------
# Writing tables
# ---------------------------------------------------------------------------

def write_table(rows: list, path: str) -> None:
    if not rows:
        return
    with open(path, "w") as fh:
        fh.write("\t".join(rows[0].keys()) + "\n")
        for row in rows:
            fh.write("\t".join(f"{v:.4f}" if isinstance(v, float) else str(v) for v in row.values()) + "\n")
    print(f"  Table: {path}")


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def _bin_order(rows: list) -> list:
    """Return rows sorted by SIZE_LABELS order."""
    order = {l: i for i, l in enumerate(SIZE_LABELS)}
    return sorted(rows, key=lambda r: order.get(r["bin"], 999))


def plot_rel_diff(rows: list, out_path: str, title: str) -> None:
    rows = _bin_order(rows)
    labels = [r["bin"] for r in rows]
    medians = [r["rel_diff_median"] * 100 for r in rows]
    p95 = [r["rel_diff_p95"] * 100 for r in rows]
    ns = [r["n"] for r in rows]

    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.bar(x, medians, 0.5, label="Median", color="#f0903a", alpha=0.85)
    ax.plot(x, p95, "k--o", markersize=4, label="95th pct", linewidth=1.2)

    ax2 = ax.twinx()
    ax2.plot(x, ns, "g:^", markersize=5, label="Count (right axis)", linewidth=1)
    ax2.set_ylabel("Test count", color="green")
    ax2.tick_params(axis="y", labelcolor="green")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_xlabel("ALO protein count (bin)")
    ax.set_ylabel("Relative p-value difference (%) — mean excluded (heavily skewed by outliers)")
    ax.set_title(f"{title}: Rust vs scipy p-value relative difference by ALO size")
    # Cap y-axis just above highest p95 to keep scale readable
    finite_p95 = [v for v in p95 if np.isfinite(v)]
    if finite_p95:
        ax.set_ylim(0, max(finite_p95) * 1.15)
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc="upper right")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"  Chart: {out_path}")


def plot_sig_agreement(rows: list, out_path: str, title: str) -> None:
    rows = _bin_order(rows)
    labels = [r["bin"] for r in rows]
    agree = [r["sig_agreement_pct"] for r in rows]
    sig_py = [r["pct_sig_py"] for r in rows]
    sig_rust = [r["pct_sig_rust"] for r in rows]

    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.bar(x, agree, 0.6, label="Significance agreement % (p<0.05)", color="#5cba7c", alpha=0.85)
    ax.plot(x, sig_py, "b-o", markersize=4, label="% significant (scipy)", linewidth=1.5)
    ax.plot(x, sig_rust, "r--s", markersize=4, label="% significant (Rust)", linewidth=1.5)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_xlabel("ALO protein count (bin)")
    ax.set_ylabel("Percentage (%)")
    ax.set_ylim(0, 105)
    ax.set_title(f"{title}: Significance agreement by ALO size")
    ax.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"  Chart: {out_path}")


def plot_scatter_pvalues(sample, out_path: str, title: str) -> None:
    """Scatter plot scipy vs Rust p-values.
    sample: list of (pv_py, pv_rust) tuples (already limited to ≤50k)."""
    if not sample:
        print(f"  Skipping scatter (no data): {out_path}")
        return
    py_vals = [s[0] for s in sample]
    rust_vals = [s[1] for s in sample]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Linear scale
    ax = axes[0]
    ax.scatter(py_vals, rust_vals, s=1, alpha=0.15, color="#4c8cbf")
    ax.plot([0, 1], [0, 1], "r-", linewidth=1, label="y=x")
    ax.axvline(0.05, color="gray", linestyle="--", linewidth=0.8, label="p=0.05")
    ax.axhline(0.05, color="gray", linestyle="--", linewidth=0.8)
    ax.set_xlabel("scipy p-value")
    ax.set_ylabel("Rust p-value")
    ax.set_title(f"{title}: scipy vs Rust (linear)")
    ax.legend(loc="upper left", markerscale=5)

    # Log scale
    ax = axes[1]
    log_py = [-math.log10(max(v, 1e-300)) for v in py_vals]
    log_rust = [-math.log10(max(v, 1e-300)) for v in rust_vals]
    ax.scatter(log_py, log_rust, s=1, alpha=0.15, color="#f0903a")
    mn, mx = 0, max(max(log_py), max(log_rust)) * 1.05
    ax.plot([mn, mx], [mn, mx], "r-", linewidth=1, label="y=x")
    ax.set_xlabel("-log10(scipy p-value)")
    ax.set_ylabel("-log10(Rust p-value)")
    ax.set_title(f"{title}: scipy vs Rust (log scale)")
    ax.legend(loc="upper left", markerscale=5)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"  Chart: {out_path}")


def plot_rel_diff_by_side(bin_data_or_records, out_path: str, title: str) -> None:
    """Boxplot of relative diff distribution per bin.
    Accepts either a list of records (small) or a bin_data dict (streaming)."""
    if isinstance(bin_data_or_records, dict):
        bins_data = {lb: [v * 100 for v in d["rel"]] for lb, d in bin_data_or_records.items()}
    else:
        bins_data = defaultdict(list)
        for rec in bin_data_or_records:
            bins_data[rec["alo_bin"]].append(rec["rel_diff"] * 100)

    ordered = _bin_order([{"bin": b} for b in bins_data])
    labels = [r["bin"] for r in ordered if r["bin"] in bins_data]
    data = [bins_data[lb] for lb in labels]

    fig, ax = plt.subplots(figsize=(14, 6))
    bp = ax.boxplot(data, patch_artist=True, notch=False,
                    medianprops={"color": "red", "linewidth": 1.5},
                    boxprops={"facecolor": "#4c8cbf", "alpha": 0.6},
                    flierprops={"marker": ".", "markersize": 1, "alpha": 0.3},
                    whiskerprops={"linewidth": 0.8})
    # Cap y-axis at 95th percentile across all bins so boxes/whiskers are visible
    all_vals = [v for d in data for v in d]
    if all_vals:
        cap = np.percentile(all_vals, 95)
        ax.set_ylim(0, cap * 1.1)
    ax.set_xticks(range(1, len(labels) + 1))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_xlabel("ALO protein count (bin)")
    ax.set_ylabel("Relative p-value difference (%) — capped at 95th pct")
    ax.set_title(f"{title}: Distribution of Rust vs scipy p-value difference by ALO size")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"  Chart: {out_path}")


# ---------------------------------------------------------------------------
# Summary stats
# ---------------------------------------------------------------------------

def print_summary_from_counts(counts: dict, rel_all: list, title: str) -> None:
    total = counts["total"]
    if total == 0:
        print(f"{title}: no rows with p-values on both sides")
        return
    agree = counts["agree"]
    flips = counts["flips"]
    print(f"\n{'='*60}")
    print(f"  {title} — p-value comparison summary")
    print(f"{'='*60}")
    print(f"  Test pairs with p-values: {total:,}")
    print(f"  Relative diff: mean={np.mean(rel_all)*100:.2f}%  median={np.median(rel_all)*100:.2f}%  p95={np.percentile(rel_all,95)*100:.2f}%")
    print(f"  Significance agreement (p<0.05): {agree/total*100:.2f}% ({agree:,}/{total:,})")
    print(f"  Significance flips: {flips:,} ({flips/total*100:.2f}%)")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--py", required=True, help="Python results TSV")
    p.add_argument("--rust", required=True, help="Rust results TSV")
    p.add_argument("--prefix", default="out", help="Output file prefix")
    p.add_argument("--title", default="Dataset", help="Title for charts")
    p.add_argument("--outdir", default=".", help="Output directory")
    args = p.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    pfx = os.path.join(args.outdir, args.prefix)

    # Stream both files in one pass — memory efficient for large datasets
    print(f"Streaming {args.py} vs {args.rust} ...")
    bin_data, sample, counts = accumulate_streaming(args.py, args.rust)

    # Flatten all rel_diff values for summary stats
    all_rel = [v for d in bin_data.values() for v in d["rel"]]
    print_summary_from_counts(counts, all_rel, args.title)

    print("\nComputing bin stats ...")
    stats = bin_stats_from_dict(bin_data)
    write_table(stats, f"{pfx}_bin_stats.tsv")

    print("\nGenerating charts ...")
    plot_rel_diff(stats, f"{pfx}_rel_diff_by_size.png", args.title)
    plot_sig_agreement(stats, f"{pfx}_sig_agreement_by_size.png", args.title)
    plot_scatter_pvalues(sample, f"{pfx}_scatter_pvalues.png", args.title)
    plot_rel_diff_by_side(bin_data, f"{pfx}_boxplot_by_size.png", args.title)

    print("\nDone.")


if __name__ == "__main__":
    main()
