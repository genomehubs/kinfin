#!/usr/bin/env python3
"""
Prepare serialised input for cluster analysis benchmarking.

Runs the kinfin pipeline up to (but not including) analyse_clusters(),
then writes a compact JSON file containing everything needed for the
cluster analysis loop:
  - clusters: id, singleton, protein_ids_by_proteome_id
  - alo_collection: attributes → levels → {proteomes_list, proteome_count}
  - protein_lengths: protein_id → length (0 when lengths unavailable)
  - params: test, min_proteomes, fuzzy_count, fuzzy_fraction, fuzzy_range

Usage (from repo root, in kinfin conda env):
    python prepare_cluster_data.py \
        -g <cluster_file> -c <config_file> -s <sequence_ids_file> \
        [-f <functional_annotation>] [-o <output.json>]
"""
import argparse
import json
import logging
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from core.build import build_AloCollection, build_ClusterCollection, build_ProteinCollection
from core.input import InputData

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("prepare")


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("-g", "--cluster_file", required=True)
    p.add_argument("-c", "--config_file", required=True)
    p.add_argument("-s", "--sequence_ids_file", required=True)
    p.add_argument("-f", "--functional_annotation", default=None)
    p.add_argument("-p", "--species_ids_file", default=None)
    p.add_argument("-m", "--taxon_idx_mapping", default=None)
    p.add_argument("-t", "--tree_file", default=None)
    p.add_argument("--min_proteomes", type=int, default=3)
    p.add_argument("--test", default="mannwhitneyu",
                   choices=["mannwhitneyu", "kruskal", "ks", "ttest", "welch"])
    p.add_argument("--fuzzy_count", type=int, default=1)
    p.add_argument("--fuzzy_fraction", type=float, default=0.75)
    p.add_argument("-o", "--output", default="cluster_data.json")
    return p.parse_args()


def main():
    args = parse_args()
    base_dir = os.path.dirname(os.path.abspath(__file__))

    nodesdb_f = os.path.join(base_dir, "data/nodesdb.txt")
    go_mapping_f = os.path.join(base_dir, "data/interpro2go")
    ipr_mapping_f = os.path.join(base_dir, "data/entry.list")
    pfam_mapping_f = os.path.join(base_dir, "data/Pfam-A.clans.tsv.gz")

    fuzzy_range = {x for x in range(20 + 1) if x != 1}

    # Build a minimal InputData by constructing it directly
    input_data = InputData(
        nodesdb_f=nodesdb_f,
        pfam_mapping_f=pfam_mapping_f,
        ipr_mapping_f=ipr_mapping_f,
        go_mapping_f=go_mapping_f,
        cluster_file=os.path.abspath(args.cluster_file),
        config_f=os.path.abspath(args.config_file),
        sequence_ids_file=os.path.abspath(args.sequence_ids_file),
        species_ids_file=os.path.abspath(args.species_ids_file) if args.species_ids_file else None,
        functional_annotation_f=os.path.abspath(args.functional_annotation) if args.functional_annotation else None,
        taxon_idx_mapping_file=os.path.abspath(args.taxon_idx_mapping) if args.taxon_idx_mapping else None,
        tree_file=os.path.abspath(args.tree_file) if args.tree_file else None,
        fasta_dir=None,
        output_path="/tmp/prepare_tmp",
        infer_singletons=False,
        min_proteomes=args.min_proteomes,
        test=args.test,
        fuzzy_count=args.fuzzy_count,
        fuzzy_fraction=args.fuzzy_fraction,
        fuzzy_range=fuzzy_range,
    )

    t0 = time.time()
    logger.info("Building AloCollection ...")

    os.makedirs("/tmp/prepare_tmp", exist_ok=True)
    alo_collection = build_AloCollection(
        config_f=input_data.config_f,
        nodesdb_f=input_data.nodesdb_f,
        tree_f=input_data.tree_f,
        taxranks=input_data.taxranks,
        taxon_idx_mapping_file=input_data.taxon_idx_mapping_file,
    )

    logger.info("Building ProteinCollection ...")
    protein_collection = build_ProteinCollection(
        aloCollection=alo_collection,
        fasta_dir=input_data.fasta_dir,
        go_mapping_f=input_data.go_mapping_f,
        functional_annotation_f=input_data.functional_annotation_f,
        ipr_mapping=input_data.ipr_mapping,
        ipr_mapping_f=input_data.ipr_mapping_f,
        pfam_mapping=input_data.pfam_mapping,
        pfam_mapping_f=input_data.pfam_mapping_f,
        sequence_ids_f=input_data.sequence_ids_f,
        species_ids_f=input_data.species_ids_f,
    )

    logger.info("Building ClusterCollection ...")
    cluster_collection = build_ClusterCollection(
        cluster_f=input_data.cluster_f,
        output_dir=input_data.output_path,
        proteinCollection=protein_collection,
        infer_singletons=input_data.infer_singletons,
        available_proteomes=alo_collection.proteomes,
    )
    logger.info(f"Collections built in {time.time()-t0:.1f}s")

    # --- Serialise ---
    logger.info("Serialising ...")
    t1 = time.time()

    # ALO collection: attributes → levels → proteomes_list + proteome_count
    alo_data = {}
    for attribute in alo_collection.attributes:
        alo_data[attribute] = {}
        for level, alo in alo_collection.ALO_by_level_by_attribute[attribute].items():
            if alo is None:
                alo_data[attribute][level] = None
            else:
                alo_data[attribute][level] = {
                    "proteomes_list": alo.proteomes_list,
                    "proteome_count": alo.proteome_count,
                }

    # Clusters: only what the analysis loop needs
    clusters = []
    for cluster in cluster_collection.cluster_list:
        clusters.append({
            "cluster_id": cluster.cluster_id,
            "singleton": cluster.singleton,
            # protein_ids_by_proteome_id: proteome_id → list of protein_ids
            "protein_ids_by_proteome_id": {
                proteome_id: list(protein_ids)
                for proteome_id, protein_ids in cluster.protein_ids_by_proteome_id.items()
            },
        })

    # Protein lengths (0 when no fasta was parsed — benchmark uses sum/mean/median/sd)
    protein_lengths = {}
    for pid, protein in protein_collection.proteins_by_protein_id.items():
        protein_lengths[pid] = protein.length if protein.length is not None else 0

    # fuzzy_range is a set — serialise as sorted list
    payload = {
        "params": {
            "test": args.test,
            "min_proteomes": args.min_proteomes,
            "fuzzy_count": input_data.fuzzy_count,
            "fuzzy_fraction": input_data.fuzzy_fraction,
            "fuzzy_range": sorted(input_data.fuzzy_range),
            "fastas_parsed": protein_collection.fastas_parsed,
        },
        "alo_collection": alo_data,
        "clusters": clusters,
        "protein_lengths": protein_lengths,
    }

    out_path = os.path.abspath(args.output)
    logger.info(f"Writing {out_path} ...")
    with open(out_path, "w") as fh:
        json.dump(payload, fh, separators=(",", ":"))

    size_mb = os.path.getsize(out_path) / 1024 / 1024
    logger.info(
        f"Done. {len(clusters)} clusters, {len(protein_lengths)} proteins, "
        f"{size_mb:.1f} MB in {time.time()-t1:.1f}s"
    )


if __name__ == "__main__":
    main()
