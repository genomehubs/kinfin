import os

import polars as pl

from internal import (
    attribute_metrics,
    cluster_metrics,
    cluster_summary,
    counts,
    logger,
    parsers,
    plots,
    utils,
)


def classify_clusters(
    cluster_df: pl.DataFrame, config_df: pl.DataFrame, attributes: list[str]
) -> pl.DataFrame:
    exploded_df = cluster_df.select(["cluster_id", "taxons"]).explode("taxons").unique()

    config_subset = config_df.select(attributes)
    merged_df = exploded_df.join(config_subset, left_on="taxons", right_on="TAXON")

    aggs = [
        (pl.col("taxons") if attr == "TAXON" else pl.col(attr))
        .n_unique()
        .alias(f"{attr}_n_unique")
        for attr in attributes
    ]

    agg_df = merged_df.group_by("cluster_id").agg(aggs)

    result_df = cluster_df.join(agg_df, on="cluster_id", how="left")

    classification_exprs = []
    for attr in attributes:
        class_col = f"{attr}_cluster_type"

        expr = (
            pl.when(pl.col("cluster_protein_count") == 1)
            .then(pl.lit("singleton"))
            .when(pl.col(f"{attr}_n_unique") == 1)
            .then(pl.lit("specific"))
            .otherwise(pl.lit("shared"))
            .alias(class_col)
        )

        classification_exprs.append(expr)

    return result_df.with_columns(classification_exprs).drop(
        [f"{attr}_n_unique" for attr in attributes]
    )


def analyse(args, nodesdb_f, ndb_f):
    log_path = os.path.join(args.output_path, "kinfin.log")
    logger.setup_logger(log_path)
    cluster_file = args.cluster_file
    config_file = args.config_file
    output_dir = args.output_path

    nodesdb = parsers.nodesdb(filepath=nodesdb_f, outpath=ndb_f)
    config_df, attributes = parsers.configfile(config_file, nodesdb)

    utils.setup_dirs(output_dir, attributes)

    cluster_df = parsers.clusterfile(cluster_file, config_df, output_dir)
    cluster_df = classify_clusters(cluster_df, config_df, attributes)

    label_columns = [
        col for col in config_df.columns if col not in ("#IDX", "TAXON", "TAXID", "OUT")
    ]

    taxon_label_dict = {
        row["TAXON"]: {
            **{label: row[label] for label in label_columns},
            "TAXON": row["TAXON"],
            "all": "all",
        }
        for row in config_df.to_dicts()
    }

    unique_label_values = {
        col: config_df.select(pl.col(col)).unique().to_series().to_list()
        for col in config_df.columns
        if col not in ("#IDX", "TAXON", "TAXID", "OUT")
    }
    unique_label_values["all"] = ["all"]
    unique_label_values["TAXON"] = config_df["TAXON"].to_list()

    counts.get_cluster_counts_by_taxon(
        cluster_df=cluster_df,
        config_df=config_df,
        base_output_dir=output_dir,
    )
    cluster_summary.get_all_cluster_summaries(
        attributes=attributes,
        cluster_df=cluster_df,
        config_df=config_df,
        base_output_dir=output_dir,
    )
    cluster_metrics.get_all_cluster_metrics(
        cluster_df=cluster_df,
        taxon_label_dict=taxon_label_dict,
        attributes=attributes,
        unique_label_values=unique_label_values,
        base_output_dir=output_dir,
    )
    attribute_metrics.get_all_attribute_metrics(
        config_df=config_df,
        cluster_df=cluster_df,
        attributes=attributes,
        base_output_dir=output_dir,
    )
    plots.plot_cluster_sizes(cluster_df=cluster_df, base_output_dir=output_dir)
    plots.generate_kinfin_rarefaction_plots(
        cluster_df=cluster_df,
        config_df=config_df,
        attributes=attributes,
        base_output_dir=output_dir,
    )
