import json
import os
from collections import OrderedDict
from typing import List, Tuple

import polars as pl

from internal.config import ATTRIBUTE_RESERVED


def nodesdb(filepath: str, outpath: str) -> pl.DataFrame:
    if os.path.exists(outpath):
        return pl.read_parquet(outpath)

    db = pl.read_csv(
        filepath,
        has_header=False,
        separator="\t",
        comment_prefix="#",
        new_columns=["node", "rank", "name", "parent"],
    )
    os.makedirs("db", exist_ok=True)
    db.write_parquet(outpath)
    return db


def clusterfile(
    cluster_path: str,
    config_df: pl.DataFrame,
    output_dir: str,
) -> pl.DataFrame:
    with open(cluster_path, "r") as file:
        content = file.read().strip().split("\n")

    cluster_ids = []
    protein_clusters = []

    for line in content:
        cluster_id, proteins = line.split(": ")
        prots = proteins.split()
        cluster_ids.extend([cluster_id] * len(prots))
        protein_clusters.extend(prots)

    exploded = pl.DataFrame(
        {"cluster_id": cluster_ids, "protein_cluster": protein_clusters}
    )
    exploded = exploded.with_columns(
        pl.col("protein_cluster")
        .str.split_exact(".", 1)
        .struct.field("field_0")
        .alias("taxon")
    )

    available_proteomes = set(config_df["TAXON"].to_list())
    total_proteins = len(exploded)
    total_clusters = exploded["cluster_id"].n_unique()
    total_proteomes = len(available_proteomes)

    included_df = exploded.filter(pl.col("taxon").is_in(available_proteomes))
    excluded_df = exploded.filter(~pl.col("taxon").is_in(available_proteomes))

    filtered_proteins = len(included_df)
    filtered_clusters = included_df["cluster_id"].n_unique()
    included_proteins_count = included_df["protein_cluster"].n_unique()
    excluded_proteins_count = excluded_df["protein_cluster"].n_unique()

    included_proteomes = (
        included_df.group_by("taxon")
        .agg(pl.len())
        .rename({"len": "count"})
        .to_dict(as_series=False)
    )
    included_proteomes_dict = dict(
        sorted(zip(included_proteomes["taxon"], included_proteomes["count"]))
    )

    excluded_proteomes = (
        excluded_df.group_by("taxon")
        .agg(pl.len())
        .rename({"len": "count"})
        .to_dict(as_series=False)
    )
    excluded_proteomes_dict = dict(
        sorted(zip(excluded_proteomes["taxon"], excluded_proteomes["count"]))
    )

    stats = OrderedDict(
        [
            ("total_clusters", total_clusters),
            ("total_proteins", total_proteins),
            ("total_proteomes", total_proteomes),
            ("filtered_clusters", filtered_clusters),
            ("filtered_proteins", filtered_proteins),
            ("included_proteins_count", included_proteins_count),
            ("excluded_proteins_count", excluded_proteins_count),
            ("included_proteomes", included_proteomes_dict),
            ("excluded_proteomes", excluded_proteomes_dict),
            ("included_proteins", included_df["protein_cluster"].sort().to_list()),
            ("excluded_proteins", excluded_df["protein_cluster"].sort().to_list()),
        ]
    )

    with open(f"{output_dir}/summary.json", "w") as mf:
        json.dump(stats, mf, separators=(", ", ": "), indent=4)

    agg_df = included_df.group_by("cluster_id").agg(
        [
            pl.col("taxon").sort().alias("taxons"),
            pl.col("protein_cluster")
            .str.split_exact(".", 1)
            .struct.field("field_1")
            .sort()
            .alias("sequences"),
            pl.col("protein_cluster").sort().alias("protein_cluster"),
            pl.len().alias("cluster_protein_count"),
            pl.col("taxon").n_unique().alias("TAXON_count"),
        ]
    )

    median_counts = (
        included_df.group_by(["cluster_id", "taxon"])
        .len()
        .group_by("cluster_id")
        .agg(pl.median("len").alias("protein_median_count"))
    )
    df = agg_df.join(median_counts, on="cluster_id", how="left")

    return df


def add_taxid_attributes(
    config_df: pl.DataFrame,
    nodesdb: pl.DataFrame,
    taxranks: List[str] = ["phylum", "order", "genus"],
) -> pl.DataFrame:
    if "TAXID" in config_df.columns:
        nodes_lookup = {
            row["node"]: {
                "rank": row["rank"],
                "name": row["name"],
                "parent": row["parent"],
            }
            for row in nodesdb.iter_rows(named=True)
        }

        def get_lineage(taxid: int) -> dict:
            lineage = {}
            current = taxid
            while current in nodes_lookup:
                entry = nodes_lookup[current]
                rank = entry["rank"]
                if rank in taxranks and rank not in lineage:
                    lineage[rank] = entry["name"]
                    if len(lineage) == len(taxranks):
                        break
                current = entry["parent"]
            return lineage

        taxid_series = config_df.get_column("TAXID")
        taxid_lineages = [get_lineage(tid) for tid in taxid_series.to_list()]

        new_columns = {}
        for rank in taxranks:
            new_columns[rank] = [
                lineage.get(rank, "not_available") for lineage in taxid_lineages
            ]

        for rank in taxranks:
            config_df = config_df.with_columns(pl.Series(rank, new_columns[rank]))

    return config_df


def configfile(filepath: str, nodesdb: pl.DataFrame) -> Tuple[pl.DataFrame, List[str]]:
    config_df = (
        pl.read_csv(filepath, has_header=True, separator=",")
        .with_columns(pl.lit("all").alias("all"))
        .pipe(add_taxid_attributes, nodesdb=nodesdb)
    )
    attributes = config_df.columns
    attributes = [
        attribute
        for attribute in attributes
        if attribute.strip("#") not in ATTRIBUTE_RESERVED
    ]
    return config_df, attributes


# def entrylist(filepath: str = "data/entry.list") -> pl.DataFrame:
#     return pl.read_csv(
#         filepath,
#         has_header=True,
#         separator="\t",
#     )


# def interpro2go(filepath: str = "data/interpro2go") -> pl.DataFrame:
#     go_mapping_dict: Dict[str, str] = {}

#     with open(filepath) as go_mapping_f:
#         for line in go_mapping_f:
#             if not line.startswith("!"):
#                 temp: List[str] = line.replace(" > ", "|").split("|")
#                 go_string: List[str] = temp[1].split(";")
#                 go_desc: str = go_string[0].replace("GO:", "").strip()
#                 go_id: str = go_string[1].strip()

#                 if go_id not in go_mapping_dict:
#                     go_mapping_dict[go_id] = go_desc
#                 elif go_desc != go_mapping_dict[go_id]:
#                     error_msg: str = f"[ERROR] : Conflicting descriptions for {go_id}"
#                     raise ValueError(error_msg)

#     go_ids: List[str] = list(go_mapping_dict.keys())
#     go_descriptions: List[str] = list(go_mapping_dict.values())

#     return pl.DataFrame({"GO_ID": go_ids, "GO_Description": go_descriptions})


# def cluster_file(filepath: str) -> pl.DataFrame:
#     with open(filepath, "r") as file:
#         content = file.read()

#     data: List[Tuple[str, List[str], List[str], List[str]]] = []
#     for line in content.strip().split("\n"):
#         cluster_id, proteins = line.strip().split(": ")
#         protein_list = proteins.split()
#         taxons = [p.split(".")[0] for p in protein_list]
#         sequences = [p.split(".")[1] for p in protein_list]
#         data.append((cluster_id, taxons, sequences, protein_list))

#     df = pl.DataFrame(
#         data,
#         schema=["cluster_id", "taxons", "sequences", "protein_cluster"],
#         schema_overrides={
#             "taxons": pl.List(pl.Utf8),
#             "sequences": pl.List(pl.Utf8),
#         },
#         orient="row",
#     )
#     df = df.with_columns(
#         [pl.col("taxons").list.sort(), pl.col("sequences").list.sort()]
#     )
#     return df


# def clusterfile_basic() -> pl.DataFrame:
#     with open(CLUSTER_PATH, "r") as file:
#         content = file.read()

#     data: List[Tuple[str, List[str]]] = []
#     for line in content.strip().split("\n"):
#         cluster_id, proteins = line.strip().split(": ")
#         protein_list = proteins.split()
#         data.append((cluster_id, protein_list))


#     df = pl.DataFrame(
#         data,
#         schema=["cluster_id", "protein_cluster"],
#         schema_overrides={
#             "taxons": pl.List(pl.Utf8),
#             "sequences": pl.List(pl.Utf8),
#         },
#         orient="row",
#     )

#     return df


# def sequence_ids(filepath: str) -> pl.DataFrame:
#     with open(filepath, "r") as sequence_id_f:
#         lines = sequence_id_f.readlines()

#     data: List[Dict[str, str]] = []
#     for line in lines:
#         col = line.strip().split(": ")
#         sequence_id = col[0].split("_")[0]
#         species_id = sequence_id.split("_")[0]
#         protein_id = (
#             col[1]
#             .replace(":", "_")
#             .replace(",", "_")
#             .replace("(", "_")
#             .replace(")", "_")
#         )
#         proteome_id = protein_id.split(".")[0]
#         data.append(
#             {
#                 "sequence_id": sequence_id,
#                 "proteome_id": proteome_id,
#                 "protein_id": protein_id,
#                 "species_id": species_id,
#             }
#         )

#     df = pl.DataFrame(data)
#     df.write_parquet("db/sequenceids.parquet")
#     return df
