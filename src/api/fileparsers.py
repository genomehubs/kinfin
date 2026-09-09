import json
from pathlib import Path
from typing import Optional, Set, Union

import pandas as pd

from api.utils import (
    apply_filters_to_frame,
    normalise_filter_specs,
    resolve_requested_columns,
)


def read_table_file(filepath: str, *, columns=None, **kwargs):
    path = Path(filepath)
    suffix = path.suffix.lower().lstrip(".")

    if suffix == "feather":
        return pd.read_feather(path, columns=columns, use_threads=True)

    if suffix == "parquet":
        return pd.read_parquet(path, columns=columns, use_threads=True)

    if suffix in {"tsv", "csv"}:
        sep = "\t" if suffix == "tsv" else ","
        return pd.read_csv(path, sep=sep, usecols=columns, **kwargs)

    raise ValueError(f"Unsupported table format: {suffix}")


def sort_and_paginate_table(
    df: pd.DataFrame,
    *,
    sort_by: str | None,
    sort_order: str = "asc",
    page: int = 1,
    size: int = 20,
) -> tuple[pd.DataFrame, int]:
    if sort_by:
        keys = [k.strip() for k in sort_by.split(",") if k.strip()]
        for key in reversed(keys):
            df = df.sort_values(
                by=key, ascending=(sort_order == "asc"), na_position="last"
            )
    total_pages = max(1, int((len(df) + size - 1) / size))
    start = (page - 1) * size
    end = start + size
    return df.iloc[start:end].copy(), total_pages


def read_table_payload(
    file_path: str,
    *,
    table_name: str,
    requested_fields: list[str] | None = None,
    filters: list[dict] | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    page: int = 1,
    size: int = 20,
) -> tuple[list[dict], int]:
    """
    Reads a table file, applies filters, sorts, and paginates the data.

    Parameters:
    - file_path [str]: Path to the table file.
    - table_name [str]: Name of the table (used for validation).
    - requested_fields [list[str] | None]: List of fields to include in the output.
    - filters [list[dict] | None]: List of filter specifications.
    - sort_by [str | None]: Field(s) to sort by.
    - sort_order [str]: Sort order ('asc' or 'desc').
    - page [int]: Page number for pagination.
    - size [int]: Number of records per page.

    Returns:
    - tuple[list[dict], int]: A tuple containing the list of records and total pages.
    """
    requested_columns = resolve_requested_columns(table_name, requested_fields)
    print(
        f"Reading table file: {file_path} with columns: {requested_columns}"
    )  # --- IGNORE ---
    df = read_table_file(file_path, columns=requested_columns)
    print(df.describe())  # --- IGNORE ---
    if filters:
        normalised_filters = normalise_filter_specs(table_name, filters)
        df = apply_filters_to_frame(
            df, table_name=table_name, filters=normalised_filters
        )
    df_paginated, total_pages = sort_and_paginate_table(
        df, sort_by=sort_by, sort_order=sort_order, page=page, size=size
    )
    # Convert pandas missing values to JSON-safe Python None.
    df_paginated = df_paginated.astype(object).where(pd.notna(df_paginated), None)
    return df_paginated.to_dict(orient="records"), total_pages


def read_tsv_file(filepath: str):
    data = read_table_file(filepath)
    yield from data.to_dict(orient="records")


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


def parse_clustering_summary_file(filepath: str):
    """
    Parses a clustering summary JSON file and returns a dictionary of clustering summary entries.

    Args:
        filepath (str): The path to the clustering summary JSON file.

    Returns:
        dict: A dictionary containing clustering summary entries.
    """
    table = read_table_file(filepath)
    return table.to_dict(orient="records")


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
            # Singleton
            "singleton_cluster_count": row["singleton_cluster_count"],
            "singleton_protein_count": row["singleton_protein_count"],
            "singleton_protein_span": row["singleton_protein_span"],
            # Specific
            "specific_cluster_count": row["specific_cluster_count"],
            "specific_protein_count": row["specific_protein_count"],
            "specific_protein_span": row["specific_protein_span"],
            "specific_cluster_true_1to1_count": row["specific_cluster_true_1to1_count"],
            "specific_cluster_fuzzy_count": row["specific_cluster_fuzzy_count"],
            # Shared
            "shared_cluster_count": row["shared_cluster_count"],
            "shared_protein_count": row["shared_protein_count"],
            "shared_protein_span": row["shared_protein_span"],
            "shared_cluster_true_1to1_count": row["shared_cluster_true_1to1_count"],
            "shared_cluster_fuzzy_count": row["shared_cluster_fuzzy_count"],
            # Absent
            "absent_cluster_total_count": row["absent_cluster_total_count"],
            "absent_cluster_singleton_count": row["absent_cluster_singleton_count"],
            "absent_cluster_specific_count": row["absent_cluster_specific_count"],
            "absent_cluster_shared_count": row["absent_cluster_shared_count"],
            # Taxon
            "TAXON_count": row["TAXON_count"],
            "TAXON_taxa": row["TAXON_taxa"],
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

    def safe_int(val):
        return int(val) if val.isdigit() else "-"

    def safe_float(val):
        try:
            return f"{float(val):.2f}"
        except (ValueError, TypeError):
            return "-"

    def yes_no(cond: bool) -> str:
        return "Yes" if cond else "No"

    for row in rows:
        cluster_id = row["#cluster_id"]

        # ---- filtering ----
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
            "present_in_cluster": yes_no(row["cluster_status"] == "present"),
            "is_singleton": yes_no(row["cluster_type"] == "singleton"),
            "is_specific": yes_no(row["cluster_type"] == "specific"),
            # counts
            "counts_cluster_protein_count": safe_int(row["cluster_protein_count"]),
            "counts_cluster_proteome_count": safe_int(row["cluster_proteome_count"]),
            "counts_TAXON_protein_count": safe_int(row["TAXON_protein_count"]),
            "counts_TAXON_mean_count": safe_float(row["TAXON_mean_count"]),
            "counts_non_taxon_mean_count": safe_float(row["non_taxon_mean_count"]),
            # representation
            "representation": safe_float(row["representation"]),
            # stats
            "log2_mean(TAXON/others)": safe_float(row["log2_mean(TAXON/others)"]),
            "pvalue(TAXON vs. others)": safe_float(row["pvalue(TAXON vs. others)"]),
            # coverage
            "coverage_TAXON_coverage": safe_float(row["TAXON_coverage"]),
            "coverage_TAXON_count": safe_int(row["TAXON_count"]),
            "coverage_non_TAXON_count": safe_int(row["non_TAXON_count"]),
            # taxa lists
            "TAXON_taxa": (
                row["TAXON_taxa"].split(",") if row["TAXON_taxa"] != "N/A" else ["-"]
            ),
            "non_TAXON_taxa": (
                row["non_TAXON_taxa"].split(",")
                if row["non_TAXON_taxa"] != "N/A"
                else ["-"]
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


def parse_valid_proteome_ids_file(filepath: str) -> dict:
    with open(filepath, "r") as f:
        return json.load(f)


def parse_clustering_file(filepath: str) -> list[dict]:
    """
    Parses a clustering JSON file and returns a list of clustering entries.

    Args:
        filepath (str): The path to the clustering JSON file.

    Returns:
        List[Dict]: Parsed list of clustering metadata entries.
    """
    with open(filepath, "r") as f:
        return json.load(f)
