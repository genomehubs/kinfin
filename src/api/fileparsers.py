import csv
from typing import Optional, Set, Union


def read_tsv_file(filepath: str, delimiter: str = "\t"):
    try:
        with open(filepath, "r", newline="") as file:
            yield from csv.DictReader(file, delimiter=delimiter)
    except csv.Error as e:
        raise ValueError(f"Error reading CSV file: {e}") from e


def split_to_set(value: Optional[str]) -> Optional[Set[str]]:
    return set(value.split(",")) if value else None


def filter_include_exclude(
    item: str,
    include_set: Optional[Set[str]] = None,
    exclude_set: Optional[Set[str]] = None,
) -> bool:
    if include_set and item not in include_set:
        return False
    return not exclude_set or item not in exclude_set


def filter_min_max(
    value: Union[int, float],
    min_value: Optional[Union[int, float]] = None,
    max_value: Optional[Union[int, float]] = None,
) -> bool:
    if min_value is not None:
        min_value = float(min_value)
    if max_value is not None:
        max_value = float(max_value)

    return (min_value is None or value >= min_value) and (
        max_value is None or value <= max_value
    )


def parse_taxon_counts_file(
    filepath: str,
    include_clusters: Optional[str],
    exclude_clusters: Optional[str],
    include_taxons: Optional[str],
    exclude_taxons: Optional[str],
    min_count: Optional[int],
    max_count: Optional[int],
):
    included_clusters = split_to_set(include_clusters)
    excluded_clusters = split_to_set(exclude_clusters)
    included_taxons = split_to_set(include_taxons)
    excluded_taxons = split_to_set(exclude_taxons)

    result = {}

    for row in read_tsv_file(filepath):
        cluster_id = row["#ID"]

        if not filter_include_exclude(cluster_id, included_clusters, excluded_clusters):
            continue

        if filtered_values := {
            taxon: int(count)
            for taxon, count in row.items()
            if taxon != "#ID"
            and filter_min_max(int(count), min_count, max_count)
            and filter_include_exclude(taxon, included_taxons, excluded_taxons)
        }:
            result[cluster_id] = filtered_values

    return result


def parse_cluster_summary_file(
    filepath: str,
    include_clusters: Optional[str],
    exclude_clusters: Optional[str],
    include_properties: Optional[str],
    exclude_properties: Optional[str],
    min_cluster_protein_count: Optional[int],
    max_cluster_protein_count: Optional[int],
    min_protein_median_count: Optional[float],
    max_protein_median_count: Optional[float],
):
    included_clusters = split_to_set(include_clusters)
    excluded_clusters = split_to_set(exclude_clusters)
    included_properties = split_to_set(include_properties)
    excluded_properties = split_to_set(exclude_properties)

    rows = read_tsv_file(filepath)
    result = {}
    for row in rows:
        cluster_id = row["#cluster_id"]
        if not filter_include_exclude(cluster_id, included_clusters, excluded_clusters):
            continue

        summary = {
            "cluster_id": cluster_id,
            "cluster_protein_count": int(row["cluster_protein_count"]),
            "protein_median_count": float(row["protein_median_count"]),
            "TAXON_count": int(row["TAXON_count"]),
            "attribute": row["attribute"],
            "attribute_cluster_type": row["attribute_cluster_type"],
            "protein_span_mean": (
                None
                if row["protein_span_mean"] == "N/A"
                else float(row["protein_span_mean"])
            ),
            "protein_span_sd": (
                None
                if row["protein_span_sd"] == "N/A"
                else float(row["protein_span_sd"])
            ),
        }

        if not filter_min_max(
            summary["cluster_protein_count"],
            min_cluster_protein_count,
            max_cluster_protein_count,
        ) or not filter_min_max(
            summary["protein_median_count"],
            min_protein_median_count,
            max_protein_median_count,
        ):
            continue
        protein_counts = {
            k: v
            for k, v in row.items()
            if k not in summary
            and filter_include_exclude(k, included_properties, excluded_properties)
        }

        result[cluster_id] = {**summary, "protein_counts": protein_counts}
    return result


def parse_attribute_summary_file(filepath: str):
    result = {}

    for row in read_tsv_file(filepath):
        taxon_set = row["taxon_set"]
        result[taxon_set] = {
            "taxon_set": taxon_set,
            "cluster_total_count": row["cluster_total_count"],
            "protein_total_count": row["protein_total_count"],
            "protein_total_span": row["protein_total_span"],
            "singleton": {
                "cluster_count": row["singleton_cluster_count"],
                "protein_count": row["singleton_protein_count"],
                "protein_span": row["singleton_protein_span"],
            },
            "specific": {
                "cluster_count": row["specific_cluster_count"],
                "protein_count": row["specific_protein_count"],
                "protein_span": row["specific_protein_span"],
                "cluster_true_1to1_count": row["specific_cluster_true_1to1_count"],
                "cluster_fuzzy_count": row["specific_cluster_fuzzy_count"],
            },
            "shared": {
                "cluster_count": row["shared_cluster_count"],
                "protein_count": row["shared_protein_count"],
                "protein_span": row["shared_protein_span"],
                "cluster_true_1to1_count": row["shared_cluster_true_1to1_count"],
                "cluster_fuzzy_count": row["shared_cluster_fuzzy_count"],
            },
            "absent": {
                "cluster_total_count": row["absent_cluster_total_count"],
                "cluster_singleton_count": row["absent_cluster_singleton_count"],
                "cluster_specific_count": row["absent_cluster_specific_count"],
                "cluster_shared_count": row["absent_cluster_shared_count"],
            },
            "TAXON_count": row["TAXON_count"],
            "TAXON_taxa": row["TAXON_taxa"].split(", "),
        }
    return result


def parse_cluster_metrics_file(
    filepath: str,
    cluster_status: Optional[str],
    cluster_type: Optional[str],
):
    result = {}
    valid_status = split_to_set(cluster_status)
    valid_types = split_to_set(cluster_type)
    rows = read_tsv_file(filepath)

    for row in rows:
        cluster_id = row["#cluster_id"]
        if valid_types and row["cluster_type"] not in valid_types:
            continue

        if not filter_include_exclude(row["cluster_status"], valid_status):
            continue

        if not filter_include_exclude(row["cluster_type"], valid_types):
            continue

        result[cluster_id] = {
            "cluster_id": cluster_id,
            "cluster_status": row["cluster_status"],
            "cluster_type": row["cluster_type"],
            "present_in_cluster": row["cluster_status"] == "present",
            "is_singleton": row["cluster_type"] == "singleton",
            "is_specific": row["cluster_type"] == "specific",
            "counts": {
                "cluster_protein_count": row["cluster_protein_count"],
                "cluster_proteome_count": row["cluster_proteome_count"],
                "TAXON_protein_count": row["TAXON_protein_count"],
                "TAXON_mean_count": row["TAXON_mean_count"],
                "non_taxon_mean_count": row["non_taxon_mean_count"],
            },
            "representation": row["representation"],
            "log2_mean(TAXON/others)": row["log2_mean(TAXON/others)"],
            "pvalue(TAXON vs. others)": row["pvalue(TAXON vs. others)"],
            "coverage": {
                "taxon_coverage": row["TAXON_coverage"],
                "TAXON_count": row["TAXON_count"],
                "non_TAXON_count": row["non_TAXON_count"],
            },
            "TAXON_taxa": (
                row["TAXON_taxa"].split(",") if row["TAXON_taxa"] != "N/A" else "N/A"
            ),
            "non_TAXON_taxa": (
                row["non_TAXON_taxa"].split(",")
                if row["non_TAXON_taxa"] != "N/A"
                else "N/A"
            ),
        }

    return result


def parse_pairwise_file(filepath: str, taxon_1: Optional[str], taxon_2: Optional[str]):
    result = []
    for row in read_tsv_file(filepath):
        if taxon_1 and row["TAXON_1"] != taxon_1 and row["TAXON_2"] != taxon_1:
            continue

        if taxon_2 and row["TAXON_1"] != taxon_2 and row["TAXON_2"] != taxon_2:
            continue

        result.append(row)

    return result
