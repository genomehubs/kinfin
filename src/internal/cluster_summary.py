import logging
from typing import List

import polars as pl

logger = logging.getLogger("kinfin_logger")


def add_attribute_count_median_cov(
    cluster_df: pl.DataFrame,
    config_df: pl.DataFrame,
    attribute: str,
) -> pl.DataFrame:
    if attribute == "TAXON":
        non_empty_clusters = cluster_df.filter(pl.col("taxons").list.len() > 0)
        if non_empty_clusters.is_empty():
            return cluster_df

        count_wide = (
            non_empty_clusters.select(["cluster_id", "taxons"])
            .explode("taxons")
            .pivot(
                values="taxons",
                index="cluster_id",
                columns="taxons",
                aggregate_function="count",
            )
            .fill_null(0)
        )

        sorted_cols = ["cluster_id"] + sorted(
            [c for c in count_wide.columns if c != "cluster_id"]
        )
        count_wide = count_wide.select(sorted_cols)

        rename_dict = {
            col: f"{col}_count" for col in count_wide.columns if col != "cluster_id"
        }
        count_wide = count_wide.rename(rename_dict)

        result = cluster_df.join(count_wide, on="cluster_id", how="left")

        count_cols_to_fill = [c for c in rename_dict.values() if c in result.columns]
        fill_expressions = [pl.col(c).fill_null(0) for c in count_cols_to_fill]

        if not fill_expressions:
            return result
        return result.with_columns(fill_expressions)

    labels_df = config_df.select(
        pl.col("TAXON").alias("taxon"),
        pl.col(attribute).alias("label"),
    ).drop_nulls()

    taxon_counts = (
        cluster_df.select(["cluster_id", "taxons"])
        .explode("taxons")
        .group_by(["cluster_id", "taxons"])
        .agg(pl.count().alias("count_taxon"))
    )

    scaffold = cluster_df.select("cluster_id").unique().join(labels_df, how="cross")

    data_for_agg = scaffold.join(
        taxon_counts,
        left_on=["cluster_id", "taxon"],
        right_on=["cluster_id", "taxons"],
        how="left",
    ).with_columns(pl.col("count_taxon").fill_null(0))

    total_taxons_per_label = labels_df.group_by("label").agg(
        pl.count("taxon").alias("total_taxons_in_label")
    )

    agg = data_for_agg.group_by(["cluster_id", "label"]).agg(
        pl.sum("count_taxon").alias("count"),
        pl.median("count_taxon").alias("median"),
        pl.col("count_taxon")
        .filter(pl.col("count_taxon") > 0)
        .count()
        .alias("present_taxons_count"),
    )

    agg_with_cov = agg.join(total_taxons_per_label, on="label", how="left")

    agg_with_cov = (
        agg_with_cov.with_columns(
            pl.when(pl.col("total_taxons_in_label") > 0)
            .then(pl.col("present_taxons_count") / pl.col("total_taxons_in_label"))
            .otherwise(0.0)
            .alias("coverage_numeric")
        )
        .with_columns(
            (pl.col("coverage_numeric") * 100)
            .round(0)
            .cast(pl.Int64)
            .cast(pl.Utf8)
            .str.zfill(3)
            .alias("coverage_str")
        )
        .with_columns(
            (
                pl.col("coverage_str").str.slice(
                    0, length=pl.col("coverage_str").str.len_chars() - 2
                )
                + "."
                + pl.col("coverage_str").str.slice(-2)
            ).alias("coverage")
        )
        .drop(["coverage_numeric", "coverage_str"])
    )

    def pivot_and_prepare(df, value_col, suffix, fill_value):
        pivoted = df.pivot(
            values=value_col, index="cluster_id", columns="label"
        ).fill_null(fill_value)

        sorted_cols = ["cluster_id"] + sorted(
            [c for c in pivoted.columns if c != "cluster_id"]
        )
        pivoted = pivoted.select(sorted_cols)

        rename_dict = {
            col: f"{col}{suffix}" for col in pivoted.columns if col != "cluster_id"
        }
        return pivoted.rename(rename_dict)

    count_wide = pivot_and_prepare(agg_with_cov, "count", "_count", 0)
    median_wide = pivot_and_prepare(agg_with_cov, "median", "_median", 0.0)
    coverage_wide = pivot_and_prepare(agg_with_cov, "coverage", "_cov", "0.00")

    result = (
        cluster_df.join(count_wide, on="cluster_id", how="left")
        .join(median_wide, on="cluster_id", how="left")
        .join(coverage_wide, on="cluster_id", how="left")
    )

    fill_expressions = []
    all_labels = labels_df.get_column("label").unique().to_list()
    for label in all_labels:
        count_col, median_col, cov_col = (
            f"{label}_count",
            f"{label}_median",
            f"{label}_cov",
        )
        if count_col in result.columns:
            fill_expressions.append(pl.col(count_col).fill_null(0))
        if median_col in result.columns:
            fill_expressions.append(pl.col(median_col).fill_null(0.0))
        if cov_col in result.columns:
            fill_expressions.append(pl.col(cov_col).fill_null("0.00"))

    if not fill_expressions:
        return result

    return result.with_columns(fill_expressions)


def get_cluster_summary(
    attribute: str,
    config_df: pl.DataFrame,
    cluster_df: pl.DataFrame,
):
    summary_df = cluster_df.select(
        [
            "cluster_id",
            "cluster_protein_count",
            "protein_median_count",
            "TAXON_count",
            "taxons",
            f"{attribute}_cluster_type",
        ]
    )
    summary_df = summary_df.with_columns(pl.lit(attribute).alias("attribute"))
    summary_df = summary_df.select(
        [
            "cluster_id",
            "cluster_protein_count",
            "protein_median_count",
            "TAXON_count",
            "taxons",
            "attribute",
            f"{attribute}_cluster_type",
        ]
    )
    summary_df = (
        summary_df.with_columns(pl.lit("N/A").alias("protein_span_mean"))
        .with_columns(pl.lit("N/A").alias("protein_span_sd"))
        .pipe(
            add_attribute_count_median_cov,
            config_df=config_df,
            attribute=attribute,
        )
        .drop("taxons")
        .rename(
            {
                "cluster_id": "#cluster_id",
                f"{attribute}_cluster_type": "attribute_cluster_type",
            }
        )
        .sort("#cluster_id")
    )

    return summary_df


def get_all_cluster_summaries(
    attributes: List[str],
    cluster_df: pl.DataFrame,
    config_df: pl.DataFrame,
    base_output_dir: str,
) -> None:

    cluster_summaries = {}
    for attribute in attributes:
        summary_df = get_cluster_summary(
            cluster_df=cluster_df,
            attribute=attribute,
            config_df=config_df,
        )
        cluster_summaries[attribute] = summary_df
        file_path = f"{base_output_dir}/{attribute}/{attribute}.cluster_summary.txt"
        logger.info(f"[✓] Writing: {file_path}")
        summary_df.write_csv(file_path, separator="\t")

    return cluster_summaries
