import logging
import os
from typing import List, Optional

import polars as pl

logger = logging.getLogger("kinfin_logger")


def precompute_cluster_info(
    cluster_df: pl.DataFrame, config_df: pl.DataFrame, attribute: str
) -> pl.DataFrame:
    taxon_to_label_df = config_df.select(
        pl.col("TAXON").alias("taxon"),
        pl.col(attribute).alias("taxon_set"),
    )

    cluster_info = (
        cluster_df.select(["cluster_id", "taxons", "protein_cluster"])
        .lazy()
        .explode("taxons")
        .rename({"taxons": "taxon"})
        .join(taxon_to_label_df.lazy(), on="taxon", how="left")
        .group_by("cluster_id")
        .agg(
            pl.col("taxon_set").drop_nulls().unique().alias("taxon_sets"),
            pl.col("protein_cluster").first().alias("protein_cluster"),
            pl.col("protein_cluster").first().list.len().alias("protein_cluster_len"),
        )
        .with_columns(
            pl.when(pl.col("protein_cluster_len") == 1)
            .then(pl.lit("singleton"))
            .when(pl.col("taxon_sets").list.len() == 1)
            .then(pl.lit("specific"))
            .otherwise(pl.lit("shared"))
            .alias("cluster_type")
        )
        .collect()
    )
    return cluster_info


def add_cluster_and_protein_counts(
    attribute_df: pl.DataFrame,
    cluster_info_df: pl.DataFrame,
    config_df: pl.DataFrame,
    attribute: str,
) -> pl.DataFrame:
    cluster_counts = (
        cluster_info_df.lazy()
        .explode("taxon_sets")
        .group_by("taxon_sets", "cluster_type")
        .agg(pl.count().alias("count"))
        .collect()
        .pivot(
            index="taxon_sets",
            columns="cluster_type",
            values="count",
            aggregate_function="sum",
        )
        .rename({"taxon_sets": "taxon_set"})
    )

    for col_name in ["singleton", "specific", "shared"]:
        if col_name not in cluster_counts.columns:
            cluster_counts = cluster_counts.with_columns(
                pl.lit(0, dtype=pl.UInt32).alias(col_name)
            )

    cluster_counts = cluster_counts.rename(
        {
            "singleton": "singleton_cluster_count",
            "specific": "specific_cluster_count",
            "shared": "shared_cluster_count",
        }
    ).with_columns(
        cluster_total_count=pl.col("singleton_cluster_count")
        + pl.col("specific_cluster_count")
        + pl.col("shared_cluster_count")
    )

    taxon_to_label_df = config_df.select(
        pl.col("TAXON").alias("taxon"),
        pl.col(attribute).alias("taxon_set"),
    ).filter(pl.col("taxon_set").is_not_null())

    protein_level_info = (
        cluster_info_df.lazy()
        .select(["cluster_id", "cluster_type", "protein_cluster"])
        .explode("protein_cluster")
        .with_columns(
            pl.col("protein_cluster").str.split(".").list.get(0).alias("taxon")
        )
        .join(taxon_to_label_df.lazy(), on="taxon", how="left")
    )

    protein_counts = (
        protein_level_info.group_by("taxon_set", "cluster_type")
        .agg(pl.count().alias("protein_count"))
        .collect()
        .pivot(
            index="taxon_set",
            columns="cluster_type",
            values="protein_count",
            aggregate_function="sum",
        )
    )
    for col_name in ["singleton", "specific", "shared"]:
        if col_name not in protein_counts.columns:
            protein_counts = protein_counts.with_columns(
                pl.lit(0, dtype=pl.UInt32).alias(col_name)
            )

    protein_counts = protein_counts.rename(
        {
            "singleton": "singleton_protein_count",
            "specific": "specific_protein_count",
            "shared": "shared_protein_count",
        }
    ).with_columns(
        protein_total_count=pl.col("singleton_protein_count")
        + pl.col("specific_protein_count")
        + pl.col("shared_protein_count")
    )

    attribute_df = attribute_df.join(cluster_counts, on="taxon_set", how="left")
    attribute_df = attribute_df.join(protein_counts, on="taxon_set", how="left")

    return attribute_df.fill_null(0)


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

    protein_spans = (
        cluster_info_df.lazy()
        .select(["cluster_id", "taxon_sets", "protein_cluster", "cluster_type"])
        .explode("protein_cluster")
        .join(
            protein_lengths_df.lazy(),
            left_on="protein_cluster",
            right_on="protein_id",
            how="left",
        )
        .with_columns(pl.col("length").fill_null(0))
        .explode("taxon_sets")
        .group_by("taxon_sets", "cluster_type")
        .agg(pl.col("length").sum().alias("span"))
        .collect()
        .pivot(
            index="taxon_sets",
            columns="cluster_type",
            values="span",
            aggregate_function="sum",
        )
        .rename({"taxon_sets": "taxon_set"})
    )

    for col_name in ["singleton", "specific", "shared"]:
        if col_name not in protein_spans.columns:
            protein_spans = protein_spans.with_columns(pl.lit(0).alias(col_name))

    protein_spans = protein_spans.rename(
        {
            "singleton": "singleton_protein_span",
            "specific": "specific_protein_span",
            "shared": "shared_protein_span",
        }
    ).with_columns(
        protein_total_span=pl.col("singleton_protein_span")
        + pl.col("specific_protein_span")
        + pl.col("shared_protein_span")
    )

    return attribute_df.join(protein_spans, on="taxon_set", how="left").fill_null(0)


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
    taxon_to_label_df = config_df.select(
        pl.col("TAXON").alias("taxon"),
        pl.col(attribute).alias("taxon_set"),
    ).filter(pl.col("taxon_set").is_not_null())

    present_taxa_long = (
        cluster_df.lazy()
        .explode("protein_cluster")
        .with_columns(
            pl.col("protein_cluster").str.split(".").list.get(0).alias("taxon")
        )
        .join(taxon_to_label_df.lazy(), on="taxon", how="left")
        .select(["cluster_id", "taxon_set", "taxon"])
        .filter(pl.col("taxon_set").is_not_null())
    )

    expected_taxa_long = taxon_to_label_df.select(["taxon_set", "taxon"]).rename(
        {"taxon": "expected_taxon"}
    )

    counts_df = (
        present_taxa_long.join(expected_taxa_long.lazy(), on="taxon_set")
        .with_columns(is_match=(pl.col("taxon") == pl.col("expected_taxon")))
        .group_by("cluster_id", "taxon_set", "expected_taxon")
        .agg(pl.col("is_match").sum().alias("count"))
        .group_by("cluster_id", "taxon_set")
        .agg(pl.col("count").alias("taxon_counts"))
    )

    counts_with_type = counts_df.join(
        cluster_info_df.lazy().select(["cluster_id", "cluster_type"]),
        on="cluster_id",
        how="left",
    )

    special_counts = (
        counts_with_type.with_columns(
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
        .group_by("taxon_set")
        .agg(
            pl.col("is_true_1to1")
            .filter(pl.col("cluster_type") == "specific")
            .sum()
            .alias("specific_cluster_true_1to1_count"),
            pl.col("is_true_1to1")
            .filter(pl.col("cluster_type") == "shared")
            .sum()
            .alias("shared_cluster_true_1to1_count"),
            pl.col("is_fuzzy")
            .filter(pl.col("cluster_type") == "specific")
            .sum()
            .alias("specific_cluster_fuzzy_count"),
            pl.col("is_fuzzy")
            .filter(pl.col("cluster_type") == "shared")
            .sum()
            .alias("shared_cluster_fuzzy_count"),
        )
        .collect()
    )

    return attribute_df.join(special_counts, on="taxon_set", how="left").fill_null(0)


def add_absent_cluster_counts(
    attribute_df: pl.DataFrame, cluster_info_df: pl.DataFrame
) -> pl.DataFrame:
    total_counts = cluster_info_df.group_by("cluster_type").agg(
        pl.count().alias("total_count")
    )

    total_singleton = total_counts.filter(pl.col("cluster_type") == "singleton")[
        "total_count"
    ].sum()
    total_specific = total_counts.filter(pl.col("cluster_type") == "specific")[
        "total_count"
    ].sum()
    total_shared = total_counts.filter(pl.col("cluster_type") == "shared")[
        "total_count"
    ].sum()

    present_counts_df = (
        cluster_info_df.lazy()
        .explode("taxon_sets")
        .group_by("taxon_sets", "cluster_type")
        .agg(pl.count().alias("present_count"))
        .collect()
        .pivot(
            index="taxon_sets",
            columns="cluster_type",
            values="present_count",
            aggregate_function="sum",
        )
        .rename({"taxon_sets": "taxon_set"})
    )

    for col_type in ["singleton", "specific", "shared"]:
        if col_type not in present_counts_df.columns:
            present_counts_df = present_counts_df.with_columns(
                pl.lit(0, dtype=pl.UInt32).alias(col_type)
            )

    result_df = (
        attribute_df.join(present_counts_df, on="taxon_set", how="left")
        .fill_null(0)
        .with_columns(
            absent_cluster_singleton_count=(total_singleton - pl.col("singleton")),
            absent_cluster_specific_count=(total_specific - pl.col("specific")),
            absent_cluster_shared_count=(total_shared - pl.col("shared")),
        )
        .with_columns(
            absent_cluster_total_count=pl.col("absent_cluster_singleton_count")
            + pl.col("absent_cluster_specific_count")
            + pl.col("absent_cluster_shared_count")
        )
        .drop(["singleton", "specific", "shared"])
    )
    return result_df


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

    cluster_info_df = precompute_cluster_info(cluster_df, config_df, attribute)

    final_df = (
        attribute_df.pipe(
            add_cluster_and_protein_counts,
            cluster_info_df=cluster_info_df,
            config_df=config_df,
            attribute=attribute,
        )
        .pipe(
            add_protein_spans,
            cluster_info_df=cluster_info_df,
            protein_lengths_df=protein_lengths_df,
        )
        .pipe(
            add_special_cluster_counts,
            cluster_df=cluster_df,
            config_df=config_df,
            attribute=attribute,
            cluster_info_df=cluster_info_df,
        )
        .pipe(add_absent_cluster_counts, cluster_info_df=cluster_info_df)
    )

    final_cols = [
        "#attribute",
        "taxon_set",
        "cluster_total_count",
        "protein_total_count",
        "protein_total_span",
        "singleton_cluster_count",
        "singleton_protein_count",
        "singleton_protein_span",
        "specific_cluster_count",
        "specific_protein_count",
        "specific_protein_span",
        "shared_cluster_count",
        "shared_protein_count",
        "shared_protein_span",
        "specific_cluster_true_1to1_count",
        "specific_cluster_fuzzy_count",
        "shared_cluster_true_1to1_count",
        "shared_cluster_fuzzy_count",
        "absent_cluster_total_count",
        "absent_cluster_singleton_count",
        "absent_cluster_specific_count",
        "absent_cluster_shared_count",
        "TAXON_count",
        "TAXON_taxa",
    ]

    for col in final_cols:
        if col not in final_df.columns:
            final_df = final_df.with_columns(pl.lit(0).alias(col))

    return final_df.select(final_cols)


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
        attribute_metrics[attribute] = attribute_df

        out_dir = os.path.join(base_output_dir, attribute)
        os.makedirs(out_dir, exist_ok=True)

        out_path = os.path.join(out_dir, f"{attribute}.attribute_metrics.txt")
        attribute_df.write_csv(out_path, separator="\t")
        logger.info(f"[✓] Writing: {out_path}")

    return attribute_metrics
