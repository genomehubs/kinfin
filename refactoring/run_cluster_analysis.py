#!/usr/bin/env python3
"""
Pure-Python cluster analysis benchmark.

Reads prepared JSON from prepare_cluster_data.py and runs the full cluster
analysis loop (identical logic to src/core/datastore.py __process_single_attribute
+ __update_ALO_data), writing a compact result CSV.

Timing covers only the analysis loop, excluding file I/O.

Usage:
    python run_cluster_analysis.py cluster_data.json [--output results.csv]
"""
import argparse
import json
import sys
import time
from math import log, sqrt
from typing import Any, Dict, List, Optional, Set, Tuple

import scipy.stats


# ---------------------------------------------------------------------------
# Stat helpers (mirrors src/core/utils.py statistic())
# ---------------------------------------------------------------------------

def _mean(lst):
    return sum(lst) / len(lst)


def statistic(count_1, count_2, test, min_proteomes):
    pvalue = log2_mean = mean_c1 = mean_c2 = None
    c1 = [c for c in count_1 if c > 0]
    c2 = [c for c in count_2 if c > 0]
    if len(c1) < min_proteomes or len(c2) < min_proteomes:
        return None, None, None, None
    mean_c1 = _mean(c1)
    mean_c2 = _mean(c2)
    log2_mean = log(mean_c1 / mean_c2, 2)
    if len(set(c1)) == 1 and len(set(c2)) == 1 and set(c1) == set(c2):
        pvalue = 1.0
    elif test == "mannwhitneyu":
        try:
            pvalue = scipy.stats.mannwhitneyu(c1, c2, alternative="two-sided")[1]
        except ValueError:
            pvalue = 1.0
    elif test in ("welch", "ttest"):
        pvalue = scipy.stats.ttest_ind(c1, c2, equal_var=(test == "ttest"))[1]
        if pvalue != pvalue:
            pvalue = 1.0
    elif test == "ks":
        pvalue = scipy.stats.ks_2samp(c1, c2)[1]
        if pvalue != pvalue:
            pvalue = 1.0
    elif test == "kruskal":
        pvalue = scipy.stats.kruskal(c1, c2)[1]
        if pvalue != pvalue:
            pvalue = 1.0
    return pvalue, log2_mean, mean_c1, mean_c2


# ---------------------------------------------------------------------------
# Cardinality logic (mirrors src/core/logic.py get_ALO_cluster_cardinality)
# ---------------------------------------------------------------------------

def get_attribute_cluster_type(singleton, implicit_by_level):
    if singleton:
        return "singleton"
    return "shared" if len(implicit_by_level) > 1 else "specific"


def get_ALO_cluster_cardinality(alo_counts, fuzzy_count, fuzzy_fraction, fuzzy_range):
    if not alo_counts:
        return None
    non_zero = [c for c in alo_counts if c > 0]
    if not non_zero:
        return None
    if all(c == 1 for c in non_zero):
        return "true"
    if fuzzy_count in alo_counts or (
        len(non_zero) >= len(alo_counts) * fuzzy_fraction
        and all(c in fuzzy_range for c in non_zero)
    ):
        return "fuzzy"
    return None


# ---------------------------------------------------------------------------
# Length stats (mirrors ProteinCollection.get_protein_length_stats)
# ---------------------------------------------------------------------------

def get_protein_length_stats(protein_ids, protein_lengths, fastas_parsed):
    stats = {"sum": 0, "mean": 0.0, "median": 0, "sd": 0.0}
    if not protein_ids or not fastas_parsed:
        return stats
    lengths = [protein_lengths[pid] for pid in protein_ids if pid in protein_lengths and protein_lengths[pid] > 0]
    if not lengths:
        return stats
    stats["sum"] = sum(lengths)
    stats["mean"] = sum(lengths) / len(lengths)
    s = sorted(lengths)
    n = len(s)
    stats["median"] = (s[n // 2] + s[(n - 1) // 2]) / 2.0
    m = stats["mean"]
    stats["sd"] = sqrt(sum((x - m) ** 2 for x in lengths) / len(lengths)) if len(lengths) > 1 else 0.0
    return stats


# ---------------------------------------------------------------------------
# Main analysis loop
# ---------------------------------------------------------------------------

def run_analysis(data: dict) -> List[dict]:
    params = data["params"]
    test = params["test"]
    min_proteomes = params["min_proteomes"]
    fuzzy_count = params["fuzzy_count"]
    fuzzy_fraction = params["fuzzy_fraction"]
    fuzzy_range = set(params["fuzzy_range"])
    fastas_parsed = params["fastas_parsed"]

    alo_collection = data["alo_collection"]
    protein_lengths = data["protein_lengths"]
    attributes = list(alo_collection.keys())

    results = []

    for cluster in data["clusters"]:
        cluster_id = cluster["cluster_id"]
        singleton = cluster["singleton"]
        protein_ids_by_proteome_id = cluster["protein_ids_by_proteome_id"]

        for attribute in attributes:
            levels = alo_collection[attribute]

            # Pass 1: process each level — collect protein ids, counts, length stats
            protein_ids_by_level: Dict[str, List[str]] = {}
            protein_length_stats_by_level: Dict[str, dict] = {}
            explicit_count_by_proteome_by_level: Dict[str, Dict[str, int]] = {}
            implicit_by_level: Dict[str, dict] = {}  # level -> {proteome_id: [prot_ids]}

            for level, alo in levels.items():
                if alo is None:
                    continue
                proteomes_list = alo["proteomes_list"]

                pids_for_level = []
                count_by_proteome = {}
                implicit_for_level = {}

                for proteome_id in proteomes_list:
                    pids = protein_ids_by_proteome_id.get(proteome_id, [])
                    pids_for_level.extend(pids)
                    count_by_proteome[proteome_id] = len(pids)
                    if pids:
                        implicit_for_level[proteome_id] = pids

                protein_ids_by_level[level] = pids_for_level
                explicit_count_by_proteome_by_level[level] = count_by_proteome
                protein_length_stats_by_level[level] = get_protein_length_stats(
                    pids_for_level, protein_lengths, fastas_parsed
                )
                if implicit_for_level:
                    implicit_by_level[level] = implicit_for_level

            cluster_type = get_attribute_cluster_type(singleton, implicit_by_level)

            # Pass 2: per-level stats + result row
            for level, alo in levels.items():
                if alo is None:
                    continue
                proteome_count = alo["proteome_count"]

                alo_status = "present" if level in implicit_by_level else "absent"

                proteome_coverage = len(implicit_by_level.get(level, {})) / proteome_count

                cardinality = None
                mwu_pvalue = mwu_log2_mean = mean_alo = mean_non_alo = None

                if alo_status == "present" and cluster_type != "singleton":
                    alo_counts = list(explicit_count_by_proteome_by_level[level].values())
                    cardinality = get_ALO_cluster_cardinality(
                        alo_counts, fuzzy_count, fuzzy_fraction, fuzzy_range
                    )

                    if cluster_type == "shared":
                        non_alo_counts = [
                            c
                            for non_level, counts in explicit_count_by_proteome_by_level.items()
                            if non_level != level
                            for c in counts.values()
                        ]
                        mwu_pvalue, mwu_log2_mean, mean_alo, mean_non_alo = statistic(
                            alo_counts, non_alo_counts, test, min_proteomes
                        )

                results.append({
                    "cluster_id": cluster_id,
                    "attribute": attribute,
                    "level": level,
                    "cluster_type": cluster_type,
                    "alo_status": alo_status,
                    "proteome_coverage": proteome_coverage,
                    "cardinality": cardinality,
                    "mwu_pvalue": mwu_pvalue,
                    "mwu_log2_mean": mwu_log2_mean,
                    "mean_alo": mean_alo,
                    "mean_non_alo": mean_non_alo,
                    "protein_count": len(protein_ids_by_level.get(level, [])),
                    "length_sum": protein_length_stats_by_level.get(level, {}).get("sum", 0),
                })

    return results


def write_results(results, out_path):
    if not results:
        return
    keys = list(results[0].keys())
    with open(out_path, "w") as fh:
        fh.write("\t".join(keys) + "\n")
        for row in results:
            fh.write("\t".join("" if row[k] is None else str(row[k]) for k in keys) + "\n")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input", help="JSON file from prepare_cluster_data.py")
    p.add_argument("--output", default="cluster_analysis_results.tsv")
    args = p.parse_args()

    sys.stderr.write(f"Loading {args.input} ...\n")
    t_load = time.time()
    with open(args.input) as fh:
        data = json.load(fh)
    sys.stderr.write(f"Loaded in {time.time()-t_load:.2f}s\n")

    n_clusters = len(data["clusters"])
    n_attrs = len(data["alo_collection"])
    sys.stderr.write(f"  {n_clusters} clusters, {n_attrs} attributes\n")

    # --- Timed section ---
    t0 = time.time()
    results = run_analysis(data)
    elapsed = time.time() - t0
    # --- End timed section ---

    sys.stderr.write(f"Writing {args.output} ...\n")
    write_results(results, args.output)

    print(f"cluster_analysis_elapsed_s\t{elapsed:.6f}")
    print(f"clusters\t{n_clusters}")
    print(f"result_rows\t{len(results)}")
    sys.stderr.write(f"Done. {elapsed:.3f}s\n")


if __name__ == "__main__":
    main()
