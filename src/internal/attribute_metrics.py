import logging
import os
from typing import List, Optional

import polars as pl

logger = logging.getLogger("kinfin_logger")


def precompute_cluster_info(
    cluster_df: pl.DataFrame, config_df: pl.DataFrame, attribute: str
) -> pl.DataFrame:
    taxon_to_label_df = config_df.lazy().select(
        [
            pl.col("TAXON").alias("taxon"),
            pl.col(attribute).alias("taxon_set"),
        ]
    )

    return (
        cluster_df.lazy()
        .select(["cluster_id", "taxons", "protein_cluster"])
        .explode("taxons")
        .rename({"taxons": "taxon"})
        .join(taxon_to_label_df, on="taxon", how="left")
        .group_by("cluster_id")
        .agg(
            [
                pl.col("taxon_set").drop_nulls().unique().alias("taxon_sets"),
                pl.col("protein_cluster").first().alias("protein_cluster"),
                pl.col("protein_cluster")
                .first()
                .list.len()
                .alias("protein_cluster_len"),
            ]
        )
        .with_columns(
            [
                pl.when(pl.col("protein_cluster_len") == 1)
                .then(pl.lit("singleton"))
                .when(pl.col("taxon_sets").list.len() == 1)
                .then(pl.lit("specific"))
                .otherwise(pl.lit("shared"))
                .alias("cluster_type")
            ]
        )
    )


def add_cluster_and_protein_counts(
    attribute_df: pl.DataFrame,
    cluster_info_df: pl.DataFrame,
    config_df: pl.DataFrame,
    attribute: str,
) -> pl.DataFrame:
    # Use lazy for all operations, collect only at the end

    # Long format: group and aggregate, no pivot
    cluster_counts_lf = (
        cluster_info_df.explode("taxon_sets")
        .group_by(["taxon_sets", "cluster_type"])
        .agg(pl.count().alias("cluster_count"))
        .rename({"taxon_sets": "taxon_set"})
    )

    taxon_to_label_df_lf = (
        config_df.lazy()
        .select([pl.col("TAXON").alias("taxon"), pl.col(attribute).alias("taxon_set")])
        .filter(pl.col("taxon_set").is_not_null())
    )

    protein_counts_lf = (
        cluster_info_df.select(["cluster_id", "cluster_type", "protein_cluster"])
        .explode("protein_cluster")
        .with_columns(
            pl.col("protein_cluster").str.split(".").list.get(0).alias("taxon")
        )
        .join(taxon_to_label_df_lf, on="taxon", how="left")
        .group_by(["taxon_set", "cluster_type"])
        .agg(pl.count().alias("protein_count"))
    )

    result_lf = attribute_df.lazy().join(cluster_counts_lf, on="taxon_set", how="left")
    result_lf = result_lf.join(
        protein_counts_lf, on=["taxon_set", "cluster_type"], how="left"
    )
    result_lf = result_lf.fill_null(0)
    return result_lf


def add_protein_spans(
    attribute_df: pl.DataFrame,
    cluster_info_df: pl.DataFrame,
    protein_lengths_df: Optional[pl.DataFrame] = None,
) -> pl.DataFrame:
    span_columns = [
        "protein_total_span",
        "singleton_protein_span",
        "specific_protein_span",
        "shared_protein_span",
    ]
    if protein_lengths_df is None or protein_lengths_df.is_empty():
        return attribute_df.with_columns([pl.lit(0).alias(col) for col in span_columns])

    protein_spans_lf = (
        cluster_info_df.select(
            ["cluster_id", "taxon_sets", "protein_cluster", "cluster_type"]
        )
        .explode("protein_cluster")
        .join(
            protein_lengths_df.lazy(),
            left_on="protein_cluster",
            right_on="protein_id",
            how="left",
        )
        .with_columns(pl.col("length").fill_null(0))
        .explode("taxon_sets")
        .group_by(["taxon_sets", "cluster_type"])
        .agg(pl.col("length").sum().alias("protein_span"))
        .rename({"taxon_sets": "taxon_set"})
    )
    result_lf = attribute_df.lazy().join(
        protein_spans_lf, on=["taxon_set", "cluster_type"], how="left"
    )
    result_lf = result_lf.fill_null(0)
    return result_lf


def add_special_cluster_counts(
    attribute_df: pl.DataFrame,
    cluster_df: pl.DataFrame,
    config_df: pl.DataFrame,
    cluster_info_df: pl.DataFrame,
    attribute: str,
    fuzzy_count: int = 1,
    fuzzy_min: int = 0,
    fuzzy_max: int = 20,
    fuzzy_fraction: float = 0.75,
) -> pl.DataFrame:
    taxon_to_label_df_lazy = (
        config_df.lazy()
        .select([pl.col("TAXON").alias("taxon"), pl.col(attribute).alias("taxon_set")])
        .filter(pl.col("taxon_set").is_not_null())
    )

    present_taxa_long_lazy = (
        cluster_df.lazy()
        .explode("protein_cluster")
        .with_columns(
            pl.col("protein_cluster").str.split(".").list.get(0).alias("taxon")
        )
        .join(taxon_to_label_df_lazy, on="taxon", how="left")
        .select(["cluster_id", "taxon_set", "taxon"])
        .filter(pl.col("taxon_set").is_not_null())
    )

    expected_taxa_long_lazy = taxon_to_label_df_lazy.select(
        ["taxon_set", "taxon"]
    ).rename({"taxon": "expected_taxon"})

    # Pre-aggregate is_match by cluster_id and expected_taxon
    preagg_df = (
        present_taxa_long_lazy.join(expected_taxa_long_lazy, on="taxon_set")
        .with_columns(is_match=(pl.col("taxon") == pl.col("expected_taxon")))
        .group_by(["cluster_id", "expected_taxon"])
        .agg(pl.col("is_match").sum().alias("count"))
    )

    # Join back to taxon_set for final aggregation
    counts_df_lazy = (
        preagg_df.join(expected_taxa_long_lazy, on="expected_taxon", how="left")
        .group_by(["cluster_id", "taxon_set"])
        .agg(pl.col("count").alias("taxon_counts"))
    )

    counts_with_type_lazy = counts_df_lazy.join(
        cluster_info_df.lazy().select(["cluster_id", "cluster_type"]),
        on="cluster_id",
        how="left",
    )

    special_counts_lf = (
        counts_with_type_lazy.with_columns(
            num_expected=pl.col("taxon_counts").list.len(),
            is_true_1to1=(pl.col("taxon_counts").list.len() > 2)
            & (pl.col("taxon_counts").list.eval(pl.element() == 1).list.all()),
            fraction_at_fuzzy=(
                pl.col("taxon_counts").list.count_matches(fuzzy_count)
                / pl.col("taxon_counts").list.len()
            ),
            all_in_range=pl.col("taxon_counts")
            .list.eval((pl.element() >= fuzzy_min) & (pl.element() <= fuzzy_max))
            .list.all(),
        )
        .with_columns(
            is_fuzzy=(pl.col("num_expected") > 2)
            & (pl.col("fraction_at_fuzzy") >= fuzzy_fraction)
            & pl.col("all_in_range")
            & ~(pl.col("is_true_1to1"))
        )
        .group_by(["taxon_set", "cluster_type"])
        .agg(
            pl.col("is_true_1to1").sum().alias("true_1to1_count"),
            pl.col("is_fuzzy").sum().alias("fuzzy_count"),
        )
    )
    result_lf = attribute_df.lazy().join(
        special_counts_lf, on=["taxon_set", "cluster_type"], how="left"
    )
    result_lf = result_lf.fill_null(0)
    return result_lf


def add_absent_cluster_counts(
    attribute_df: pl.DataFrame, cluster_info_df: pl.DataFrame
) -> pl.DataFrame:
    present_counts_lf = (
        cluster_info_df.explode("taxon_sets")
        .group_by(["taxon_sets", "cluster_type"])
        .agg(pl.count().alias("present_count"))
        .rename({"taxon_sets": "taxon_set"})
    )
    result_lf = attribute_df.lazy().join(
        present_counts_lf, on=["taxon_set", "cluster_type"], how="left"
    )
    result_lf = result_lf.fill_null(0)
    return result_lf


def get_attribute_metrics(
    config_df: pl.DataFrame,
    attribute: str,
    cluster_df,
    protein_lengths_df: Optional[pl.DataFrame] = None,
) -> pl.DataFrame:
    attribute_df = (
        config_df.group_by(pl.col(attribute).alias("taxon_set"))
        .agg(
            pl.col("TAXON").unique().sort().alias("TAXON_taxa_list"),
            pl.col("TAXON").n_unique().alias("TAXON_count"),
        )
        .with_columns(
            pl.lit(attribute).alias("#attribute"),
            pl.col("TAXON_taxa_list").list.join(", ").alias("TAXON_taxa"),
        )
        .select(["#attribute", "taxon_set", "TAXON_count", "TAXON_taxa"])
        .sort("taxon_set")
    )

    cluster_info_lf = precompute_cluster_info(cluster_df, config_df, attribute)
    # Compose all metrics in long format, passing LazyFrame
    # Compose all metrics in long format, passing LazyFrame
    lazy_long_df = (
        attribute_df.pipe(
            add_cluster_and_protein_counts,
            cluster_info_df=cluster_info_lf,
            config_df=config_df,
            attribute=attribute,
        )
        .pipe(
            add_protein_spans,
            cluster_info_df=cluster_info_lf,
            protein_lengths_df=protein_lengths_df,
        )
        .pipe(
            add_special_cluster_counts,
            cluster_df=cluster_df,
            config_df=config_df,
            attribute=attribute,
            cluster_info_df=cluster_info_lf,
        )
        .pipe(add_absent_cluster_counts, cluster_info_df=cluster_info_lf)
    )

    # # Profile Polars RAM/compute usage
    # profile = lazy_long_df.profile()
    # logger.info(f"[Polars profile] Attribute: {attribute}\n{profile}")

    # # Save full profile node table to CSV for inspection (no abbreviation)
    # profile_dir = "polars_profiles"
    # os.makedirs(profile_dir, exist_ok=True)
    # profile_csv_path = os.path.join(profile_dir, f"{attribute}.profile_nodes.csv")
    # # Polars profile returns a dict with 'nodes' key containing a DataFrame
    # # Expect Polars .profile() to return a tuple, with the profile DataFrame as the second item
    # nodes_df = None
    # if (
    #     isinstance(profile, tuple)
    #     and len(profile) > 1
    #     and isinstance(profile[1], pl.DataFrame)
    # ):
    #     nodes_df = profile[1]
    #     nodes_df.write_csv(profile_csv_path)
    #     logger.info(f"[✓] Polars profile nodes saved: {profile_csv_path}")

    long_df = lazy_long_df.collect()

    # Ensure all metric columns exist before pivot
    metric_cols = [
        "cluster_count",
        "protein_count",
        "protein_span",
        "true_1to1_count",
        "fuzzy_count",
        "present_count",
    ]
    for col in metric_cols:
        if col not in long_df.columns:
            long_df = long_df.with_columns(pl.lit(0).alias(col))

    # Pivot to wide format at the end
    wide_df = long_df.pivot(
        index=["#attribute", "taxon_set", "TAXON_count", "TAXON_taxa"],
        columns="cluster_type",
        values=metric_cols,
        aggregate_function="first",
    )

    logger.debug(f"Config df shape for attribute {attribute}: {config_df.shape}")
    logger.debug(f"Cluster df shape for attribute {attribute}: {wide_df.shape}")

    return wide_df


def get_all_attribute_metrics(
    config_df: pl.DataFrame,
    cluster_df: pl.DataFrame,
    attributes: List[str],
    base_output_dir: str,
    protein_lengths_df: Optional[pl.DataFrame] = None,
) -> None:
    config_df = config_df.with_columns(pl.lit("all").alias("all"))

    attribute_metrics = {}
    for attribute in attributes:
        attribute_df = get_attribute_metrics(
            cluster_df=cluster_df,
            config_df=config_df,
            protein_lengths_df=protein_lengths_df,
            attribute=attribute,
        )
        # attribute_metrics[attribute] = attribute_df

        out_dir = os.path.join(base_output_dir, attribute)
        os.makedirs(out_dir, exist_ok=True)

        out_path = os.path.join(out_dir, f"{attribute}.attribute_metrics.txt")
        attribute_df.write_csv(out_path, separator="\t")
        logger.info(f"[✓] Writing: {out_path}")

    return attribute_metrics
