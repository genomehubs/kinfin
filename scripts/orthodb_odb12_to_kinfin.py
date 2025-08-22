#!/usr/bin/env python3

"""
This script converts OrthoDB data to Kinfin format.

It parses the OrthoDB cluster files and
- reports on available clustering sets
- generates orthogroups, sequence_ids and config files based on a provided root taxon
"""

# format of the OrthoDB files is described at https://data.orthodb.org/current/download/README.txt
#
# odb12v1_species.tab
# 1.	NCBI tax id
# 2.	Ortho DB individual organism id, based on NCBI tax id
# 3.	scientific name inherited from the most relevant NCBI tax id
# 4.	genome asssembly id, when available
# 5.	total count of clustered genes in this species
# 6.	total count of the OGs it participates
# 7.	mapping type, clustered(C) or mapped(M)

# odb12v1_levels.tab:
# 1.	level NCBI tax id
# 2.	scientific name
# 3.	total non-redundant count of genes in all underneath clustered species
# 4.	total count of OGs built on it
# 5.	total non-redundant count of species underneath

# odb12v1_level2species.tab
# 1.	top-most level NCBI tax id, one of {2, 2157, 2759, 10239}
# 2.	Ortho DB organism id
# 3.	number of hops between the top-most level id and the NCBI tax id assiciated with the organism
# 4.	ordered list of Ortho DB selected intermediate levels from the top-most level to the bottom one

# odb12v1_genes.tab
# 1.	Ortho DB unique gene id (not stable between releases)
# 2.	Ortho DB individual organism id, composed of NCBI tax id and suffix
# 3.	protein original sequence id, as downloaded along with the sequence
# 4.	semicolon-separated list of synonyms, evaluated by mapping
# 5.	Uniprot id, evaluated by mapping
# 6.	semicolon-separated list of ids from Ensembl, evaluated by mapping
# 7.	NCBI gid or gene name, evaluated by mapping
# 8.	description, evaluated by mapping
# 9.	genomic coordinates relative to genomic DNA, from the source GBFF data
# 10.	genomic DNA id
# 11. chromosome

# odb12v1_gene_xrefs.tab
# 1.	Ortho DB gene id
# 2.	external gene identifier, either mapped or the original sequence id from Genes table
# 3.	external DB name, one of {GOterm, InterPro, NCBIproteinGI, UniProt, ENSEMBL, NCBIgid, NCBIgenename}

# odb12v1_OGs.tab
# 1.	OG unique id (not stable and re-used between releases)
# 2.	level tax_id on which the group was built
# 3.	OG name (the most common gene name within the group)

# odb12v1_OG2genes.tab
# 1.	OG unique id
# 2.	Ortho DB gene id

# odb12v1_OG_pairs.tab
# 1. descendant OG id
# 2. antecedent OG id

# odb12v1_OG_xrefs.tab
# 1.	OG unique id
# 2.	external DB or DB section
# 3.	external identifier
# 4.	number of genes in the OG associated with the identifier

# Functions in the file parse these tab delimited files to generate KinFin-compatible input files
# the 3 outputs should lookm like this:
# - orthogroups.tsv
#   OG0000000: A.seq1 B.seq1 C.seq1 D.seq1 E.seq1 F.seq8 A.seq2 B.seq2 C.seq2 D.seq2 E.seq2
#   OG0000001: A.seq3 B.seq3 B.seq4 D.seq3 D.seq4
#   OG0000002: E.seq3 C.seq4 E.seq4 F.seq8 F.seq9 F.seq10
# - sequence_ids.tsv
#   0_0: A.seq1
#   0_1: A.seq2
#   0_2: A.seq3
# - config.json

import argparse
import json
import os
import sys
from collections import defaultdict


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert OrthoDB data to Kinfin format."
    )
    parser.add_argument(
        "--taxid",
        required=True,
        type=str,
        help="NCBI taxid for the root level to filter OrthoDB clusters.",
    )
    parser.add_argument(
        "--ortho_dir",
        required=True,
        type=str,
        help="Root directory containing OrthoDB files.",
    )
    parser.add_argument(
        "--out_dir", required=True, type=str, help="Output directory for Kinfin files."
    )
    return parser.parse_args()


def uc_first(s):
    return s[0].upper() + s[1:] if s else s


def shorten_name(name, existing_short_names):
    # Create a short name by taking the first 2 letters of the first word in the name
    # and the first 3 letters of all other words
    parts = name.split()
    short_name = uc_first(parts[0][:2].lower()) + "".join(
        uc_first(part[:3]) for part in parts[1:]
    )

    # Ensure the short name is unique by appending numbers if necessary
    original_short_name = short_name
    counter = 1
    while short_name in existing_short_names:
        short_name = f"{original_short_name}{counter}"
        counter += 1

    existing_short_names.add(short_name)
    return short_name


def species_at_level(taxid, levels_path, level2species_path, species_path):
    # Verify the taxid exists in levels and map to name
    valid_taxids = {}
    with open(levels_path) as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 1:
                valid_taxids[parts[0]] = parts
    if taxid not in valid_taxids:
        print(f"Taxid {taxid} not found in levels file.", file=sys.stderr)
        sys.exit(1)
    print(f"Taxid {taxid} found: {valid_taxids[taxid][1]}")
    level_taxid = taxid
    metadata = {
        "level_taxid": level_taxid,
        "level_name": valid_taxids[taxid][1],
        "total_genes": valid_taxids[taxid][2],
        "total_OGs": valid_taxids[taxid][3],
        "total_species": valid_taxids[taxid][4],
    }
    print("Level metadata:", metadata)

    # Get all species under the specified level
    relevant_species_ids = set()
    with open(level2species_path) as f:
        for line in f:
            parts = line.strip().split("\t")
            levels = (
                parts[3].replace("{", "").replace("}", "").split(",")
                if len(parts) >= 4
                else []
            )
            if level_taxid in levels:
                relevant_species_ids.add(parts[1])

    print(f"Found {len(relevant_species_ids)} species under taxid {taxid}.")

    if not relevant_species_ids:
        print(f"No species found under taxid {taxid}.", file=sys.stderr)
        sys.exit(1)

    # Map species ids to NCBI taxids and names
    species_info = {}
    index = 0
    short_names = set()
    with open(species_path) as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 3 and parts[1] in relevant_species_ids:
                species_info[parts[1]] = {
                    "taxid": parts[0],
                    "name": parts[2],
                    "short_name": shorten_name(parts[2], short_names),
                    "index": index,
                }
                index += 1
    metadata["species"] = species_info

    return metadata


def filter_orthogroups_by_level(og2genes_path, genes_path, species_metadata):
    level_taxid = species_metadata["level_taxid"]
    sequence_ids = set(species_metadata["species"].keys())
    og2genes = defaultdict(list)
    geneid_to_seqid = {}
    og_suffix = f"at{level_taxid}"
    with open(og2genes_path, "r") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 2 and parts[0].endswith(og_suffix):
                og2genes[parts[0]].append(parts[1])
                sequence_ids.add(parts[1])

    print(f"Found {len(og2genes)} orthogroups at level {level_taxid}.")

    with open(genes_path, "r") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 2 and parts[0] in sequence_ids:
                species_short_name = species_metadata["species"][parts[1]]["short_name"]
                geneid_to_seqid[parts[0]] = f"{species_short_name}.{parts[2]}"

    print(f"Found {len(geneid_to_seqid)} genes at level {level_taxid}.")

    return og2genes, geneid_to_seqid


def write_orthogroups(genes_by_og, geneid_to_seqid, output_path):
    with open(output_path, "w") as f:
        for og, genes in genes_by_og.items():
            if seq_ids := [geneid_to_seqid[g] for g in genes if g in geneid_to_seqid]:
                f.write(f"{og}: {' '.join(seq_ids)}\n")
    print(f"Wrote orthogroups to {output_path}")


def write_sequence_ids(geneid_to_seqid, species_metadata, output_path):
    gene_indices = defaultdict(int)
    with open(output_path, "w") as f:
        for gene_id, seq_id in geneid_to_seqid.items():
            species_id = gene_id.split(":")[0]
            if species_id in species_metadata["species"]:
                species_index = species_metadata["species"][species_id]["index"]
                gene_index = gene_indices[species_id]
                gene_indices[species_id] += 1
                f.write(f"{species_index}_{gene_index}: {seq_id}\n")
    print(f"Wrote sequence IDs to {output_path}")


def write_config(species_metadata, output_path):
    config = []
    config.extend(
        {
            "taxon": info["short_name"],
            "index": info["index"],
            "taxid": info["taxid"],
            "name": info["name"],
        }
        for _, info in sorted(
            species_metadata["species"].items(),
            key=lambda x: x[1]["index"],
        )
    )
    with open(output_path, "w") as f:
        json.dump(config, f, indent=4)
    print(f"Wrote config to {output_path}")


def main():
    args = parse_args()
    taxid = args.taxid
    ortho_dir = args.ortho_dir
    out_dir = args.out_dir

    levels_path = os.path.join(ortho_dir, "odb12v1_levels.tab")
    level2species_path = os.path.join(ortho_dir, "odb12v1_level2species.tab")
    species_path = os.path.join(ortho_dir, "odb12v1_species.tab")
    # gene_xrefs_path = os.path.join(ortho_dir, "odb12v1_gene_xrefs.tab")
    # og_pairs_path = os.path.join(ortho_dir, "odb12v1_OG_pairs.tab")
    # og_xrefs_path = os.path.join(ortho_dir, "odb12v1_OG_xrefs.tab")
    og2genes_path = os.path.join(ortho_dir, "odb12v1_OG2genes_7088.tab")
    ogs_path = os.path.join(ortho_dir, "odb12v1_OGs.tab")
    genes_path = os.path.join(ortho_dir, "odb12v1_genes.tab")

    if not all(
        os.path.exists(p)
        for p in [
            levels_path,
            level2species_path,
            species_path,
            og2genes_path,
            ogs_path,
            genes_path,
        ]
    ):
        print(
            "Missing required OrthoDB files in the provided directory.", file=sys.stderr
        )
        sys.exit(1)

    os.makedirs(out_dir, exist_ok=True)

    species_metadata = species_at_level(
        taxid, levels_path, level2species_path, species_path
    )

    genes_by_og, geneid_to_seqid = filter_orthogroups_by_level(
        og2genes_path, genes_path, species_metadata
    )

    write_orthogroups(
        genes_by_og, geneid_to_seqid, os.path.join(out_dir, "orthogroups.tsv")
    )

    write_sequence_ids(
        geneid_to_seqid, species_metadata, os.path.join(out_dir, "sequence_ids.tsv")
    )

    write_config(species_metadata, os.path.join(out_dir, "config.json"))


if __name__ == "__main__":
    main()
