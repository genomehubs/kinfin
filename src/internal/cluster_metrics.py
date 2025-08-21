import logging
import warnings
from typing import Dict, List

import polars as pl
from scipy import stats

logger = logging.getLogger("kinfin_logger")


warnings.filterwarnings("ignore", message="Precision loss occurred*")


def add_status_and_TAXON_protein_count_columns(
    df: pl.DataFrame,
    label_to_taxons: Dict[str, Dict[str, set]],
) -> pl.DataFrame:
    expressions = []

    for attribute, label_dict in label_to_taxons.items():
        for label_group, valid_taxa in label_dict.items():
            in_valid = pl.col("taxons").list.eval(pl.element().is_in(valid_taxa))

            status_col_name = f"{attribute}_{label_group}_cluster_status"
            status_expr = (
                pl.when(in_valid.list.any())
                .then(pl.lit("present"))
                .otherwise(pl.lit("absent"))
                .alias(status_col_name)
            )

            count_col_name = f"{attribute}_{label_group}_TAXON_protein_count"
            count_expr = in_valid.list.sum().alias(count_col_name)

            expressions.extend([status_expr, count_expr])

    return df.with_columns(expressions)


def add_coverage_column(
    df: pl.DataFrame,
    attribute: str,
    level: str,
    label_to_taxons: dict,
) -> pl.DataFrame:
    expected_taxons = set(label_to_taxons[attribute][level])
    expected_taxons_len = len(expected_taxons)

    if expected_taxons_len == 0:
        return df.with_columns(pl.lit("N/A").alias("TAXON_coverage"))

    numerator = (
        pl.col("taxons").list.unique().list.set_intersection(expected_taxons).list.len()
    )

    coverage_numeric = numerator / expected_taxons_len

    coverage_str_padded = (
        (coverage_numeric * 100).round(0).cast(pl.Int64).cast(pl.Utf8).str.zfill(3)
    )

    coverage_expr = (
        coverage_str_padded.str.slice(0, length=coverage_str_padded.str.len_chars() - 2)
        + "."
        + coverage_str_padded.str.slice(-2)
    )

    return df.with_columns(coverage_expr.alias("TAXON_coverage"))


def add_taxon_split_columns(
    df: pl.DataFrame,
    attribute: str,
    level: str,
    label_to_taxons: dict,
    min_proteomes: int = 2,
    test: str = "mannwhitneyu",
) -> pl.DataFrame:
    """
    Calculates taxon statistics using a fully vectorized Polars-native approach.
    """
    valid_taxa = set(label_to_taxons[attribute][level])

    if "cluster_id" not in df.columns:
        df = df.with_row_count(name="cluster_id")

    partitioned_counts = (
        df.select(["cluster_id", "taxons"])
        .explode("taxons")
        .group_by("cluster_id", "taxons")
        .agg(pl.count().alias("count"))
        .with_columns(pl.col("taxons").is_in(valid_taxa).alias("is_inside"))
    )

    grouped_lists = partitioned_counts.group_by("cluster_id", maintain_order=True).agg(
        pl.col("count").filter(pl.col("is_inside")).alias("inside_counts"),
        pl.col("count").filter(~pl.col("is_inside")).alias("outside_counts"),
    )

    stats_results = (
        grouped_lists.with_columns(
            inside_len=pl.col("inside_counts").list.len(),
            outside_len=pl.col("outside_counts").list.len(),
        )
        .with_columns(
            is_valid=pl.when(
                (pl.col("inside_len") >= min_proteomes)
                & (pl.col("outside_len") >= min_proteomes)
            )
            .then(True)
            .otherwise(False),
            mean_inside=pl.col("inside_counts").list.mean(),
            mean_outside=pl.col("outside_counts").list.mean(),
        )
        .with_columns(
            log2_ratio=pl.when(pl.col("mean_outside") > 0)
            .then((pl.col("mean_inside") / pl.col("mean_outside")).log(base=2))
            .otherwise(None),
        )
        .with_columns(
            representation=pl.when(pl.col("log2_ratio") > 0)
            .then(pl.lit("enriched"))
            .otherwise(pl.lit("depleted")),
        )
    )

    def compute_p_value(struct: dict) -> str | None:
        """A small, focused function just for the p-value."""
        inside = struct.get("inside_counts")
        outside = struct.get("outside_counts")
        try:
            if not struct.get("is_valid"):
                return None
            p = stats.mannwhitneyu(inside, outside, alternative="two-sided").pvalue
            return f"{p:.16f}".rstrip("0").rstrip(".")
        except Exception:
            return None

    final_stats = stats_results.with_columns(
        p_value=pl.struct(["inside_counts", "outside_counts", "is_valid"]).map_elements(
            compute_p_value, return_dtype=pl.Utf8
        )
    ).select(
        pl.col("cluster_id"),
        pl.when(pl.col("is_valid"))
        .then(pl.col("mean_inside"))
        .otherwise(pl.lit("N/A"))
        .alias("TAXON_mean_count"),
        pl.when(pl.col("is_valid"))
        .then(pl.col("mean_outside"))
        .otherwise(pl.lit("N/A"))
        .alias("non_taxon_mean_count"),
        pl.when(pl.col("is_valid"))
        .then(pl.col("log2_ratio").cast(pl.Utf8))
        .otherwise(pl.lit("N/A"))
        .alias("log2_mean(TAXON/others)"),
        pl.col("p_value").fill_null(pl.lit("N/A")).alias("pvalue(TAXON vs. others)"),
        pl.when(pl.col("is_valid"))
        .then(pl.col("representation"))
        .otherwise(pl.lit("N/A"))
        .alias("representation"),
    )

    return df.join(final_stats, on="cluster_id", how="left")


def add_all_taxon_info_columns(
    df: pl.DataFrame,
    label_to_taxons: Dict[str, Dict[str, set]],
) -> pl.DataFrame:
    expressions = []

    for attribute, label_dict in label_to_taxons.items():
        for label_group, valid_taxa in label_dict.items():
            prefix = f"{attribute}_{label_group}"
            taxons_sorted_unique = pl.col("taxons").list.unique().list.sort()

            taxon_mask = taxons_sorted_unique.list.eval(pl.element().is_in(valid_taxa))
            non_taxon_mask = taxons_sorted_unique.list.eval(
                ~pl.element().is_in(valid_taxa)
            )

            taxon_list_str = taxons_sorted_unique.list.eval(
                pl.element().filter(pl.element().is_in(valid_taxa))
            )
            non_taxon_list_str = taxons_sorted_unique.list.eval(
                pl.element().filter(~pl.element().is_in(valid_taxa))
            )

            expressions.extend(
                [
                    taxon_mask.list.sum().alias(f"{prefix}_TAXON_count"),
                    non_taxon_mask.list.sum().alias(f"{prefix}_non_TAXON_count"),
                    pl.when(taxon_list_str.list.len() == 0)
                    .then(pl.lit("N/A"))
                    .otherwise(taxon_list_str.list.join(","))
                    .alias(f"{prefix}_TAXON_taxa"),
                    pl.when(non_taxon_list_str.list.len() == 0)
                    .then(pl.lit("N/A"))
                    .otherwise(non_taxon_list_str.list.join(","))
                    .alias(f"{prefix}_non_TAXON_taxa"),
                ]
            )

    return df.with_columns(expressions)


def get_cluster_metrics(
    attribute: str,
    label_group: str,
    label_to_taxons: Dict[str, Dict[str, set]],
    base_metrics_df: pl.DataFrame,
) -> pl.DataFrame:
    cols_for_loop = [
        "cluster_id",
        "cluster_protein_count",
        "cluster_proteome_count",
        "taxons",
        f"{attribute}_cluster_type",
        f"{attribute}_{label_group}_TAXON_protein_count",
        f"{attribute}_{label_group}_cluster_status",
        f"{attribute}_{label_group}_TAXON_count",
        f"{attribute}_{label_group}_non_TAXON_count",
        f"{attribute}_{label_group}_TAXON_taxa",
        f"{attribute}_{label_group}_non_TAXON_taxa",
    ]

    metrics_df = (
        base_metrics_df.select(cols_for_loop)
        .pipe(
            add_coverage_column,
            attribute=attribute,
            level=label_group,
            label_to_taxons=label_to_taxons,
        )
        .pipe(
            add_taxon_split_columns,
            attribute=attribute,
            level=label_group,
            label_to_taxons=label_to_taxons,
        )
    )

    final_order = [
        "#cluster_id",
        "cluster_status",
        "cluster_type",
        "cluster_protein_count",
        "cluster_proteome_count",
        "TAXON_protein_count",
        "TAXON_mean_count",
        "non_taxon_mean_count",
        "representation",
        "log2_mean(TAXON/others)",
        "pvalue(TAXON vs. others)",
        "TAXON_coverage",
        "TAXON_count",
        "non_TAXON_count",
        "TAXON_taxa",
        "non_TAXON_taxa",
    ]

    rename_map = {
        "cluster_id": "#cluster_id",
        f"{attribute}_cluster_type": "cluster_type",
        f"{attribute}_{label_group}_cluster_status": "cluster_status",
        f"{attribute}_{label_group}_TAXON_protein_count": "TAXON_protein_count",
        f"{attribute}_{label_group}_TAXON_count": "TAXON_count",
        f"{attribute}_{label_group}_non_TAXON_count": "non_TAXON_count",
        f"{attribute}_{label_group}_TAXON_taxa": "TAXON_taxa",
        f"{attribute}_{label_group}_non_TAXON_taxa": "non_TAXON_taxa",
    }

    final_df = metrics_df.rename(rename_map)
    final_df = final_df.select(final_order).sort("#cluster_id")
    return final_df


def get_all_cluster_metrics(
    attributes: List[str],
    unique_label_values: Dict[str, List[str]],
    cluster_df: pl.DataFrame,
    taxon_label_dict: Dict[str, Dict[str, str]],
    base_output_dir: str,
    min_proteomes=2,
) -> None:
    label_to_taxons: Dict[str, Dict[str, set]] = {
        attr: {
            label: {
                taxon
                for taxon, labels in taxon_label_dict.items()
                if labels.get(attr) == label
            }
            for label in unique_label_values[attr]
        }
        for attr in attributes
    }

    cluster_metrics = {}

    base_metrics_df = (
        cluster_df.pipe(
            add_status_and_TAXON_protein_count_columns,
            label_to_taxons,
        )
        .rename({"TAXON_count": "cluster_proteome_count"})
        .pipe(add_all_taxon_info_columns, label_to_taxons)
    )

    for attribute in attributes:
        cluster_metrics[attribute] = {}
        for label_group in unique_label_values[attribute]:
            metrics_df = get_cluster_metrics(
                attribute=attribute,
                label_group=label_group,
                label_to_taxons=label_to_taxons,
                base_metrics_df=base_metrics_df,
            )

            cluster_metrics[attribute][label_group] = metrics_df
            file_path = f"{base_output_dir}/{attribute}/{attribute}.{label_group}.cluster_metrics.txt"
            logger.info(f"[✓] Writing: {file_path}")
            metrics_df.write_csv(file_path, separator="\t")

    return cluster_metrics
