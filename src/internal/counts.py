import os

import polars as pl


def get_cluster_counts_by_taxon(
    config_df: pl.DataFrame,
    cluster_df: pl.DataFrame,
    base_output_dir: str,
) -> None:
    taxa = config_df["TAXON"].unique().sort()
    exploded = cluster_df.select(["cluster_id", "taxons"]).explode("taxons")

    counts = (
        exploded.group_by(["cluster_id", "taxons"])
        .count()
        .rename({"count": "taxon_count"})
    )

    result_df = counts.pivot(
        values="taxon_count",
        index="cluster_id",
        columns="taxons",
        aggregate_function=None,
    ).fill_null(0)

    result_df = result_df.rename({"cluster_id": "#ID"})
    result_df = result_df.select(["#ID"] + taxa.to_list())

    result_df = result_df.sort("#ID")

    output_path = f"{base_output_dir}/cluster_counts_by_taxon.txt"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    result_df.write_csv(output_path, separator="\t")
    return result_df
