import argparse
import collections
import random
import sys
import time
import traceback

import numpy as np
import os


def parse_args():
    parser = argparse.ArgumentParser(
        prog="simfin.py",
        description="Simulate KinFin input",
        epilog="Author: DRL (2025)",
    )
    parser.add_argument(
        "-n",
        "--sim_clusters",
        required=False,
        default=1_000_000,
        type=int,
    )
    parser.add_argument(
        "-m",
        "--taxon_counts",
        required=False,
        default=20,
        type=int,
    )
    parser.add_argument(
        "-r",
        "--random_seed",
        required=False,
        default=19,
        type=int,
    )
    parser.add_argument(
        "-f",
        "--fasta_sim",
        action="store_true",
        required=False,
        default=False,
    )
    parser.add_argument(
        "-g",
        "--groups_raw",
        required=True,
    )

    parser.add_argument(
        "-wt",
        "--with_taxid",
        action="store_true",
        required=False,
    )
    parser.add_argument(
        "-wo",
        "--with_outgroup",
        action="store_true",
        required=False,
    )
    parser.add_argument(
        "-lc",
        "--label_counts",
        type=int,
        nargs="+",
        required=False,
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        required=False,
        default=".",
        help="Directory to write output files",
    )

    return parser.parse_args()


def get_count_matrix(orthogroups_f):
    taxon_ids = set()
    taxon_counters = []
    with open(orthogroups_f) as fh:
        for i, line in enumerate(fh):
            cluster_id, protein_string = line.rstrip("\n").split(": ")
            taxon_counter = collections.Counter(
                [
                    protein_name.split(".")[0]
                    for protein_name in protein_string.split(" ")
                ]
            )
            taxon_ids.update(taxon_counter.keys())
            taxon_counters.append(taxon_counter)
    taxon_ids = sorted(taxon_ids)
    matrix = np.zeros(shape=(len(taxon_counters), len(taxon_ids)), dtype=int)
    for j, taxon_counter in enumerate(taxon_counters):
        for i, taxon_id in enumerate(taxon_ids):
            matrix[j][i] = taxon_counter[taxon_id]
    return taxon_ids, matrix


def get_simulated_counts(
    matrix,
    sim_clusters,
    seed,
):
    rng = np.random.default_rng(seed)
    simulated_counts = rng.choice(
        matrix, size=sim_clusters, replace=True, axis=0, shuffle=True
    )
    simulated_counts_sorted = simulated_counts[
        np.argsort(simulated_counts.sum(axis=1))[::-1], :
    ]
    return simulated_counts_sorted


def write_sequence_ids(
    taxon_ids,
    protein_ids_by_taxon_id,
    seed,
    sim_clusters,
    output_dir,
):
    lines = []
    for taxon_index, taxon_id in enumerate(taxon_ids):
        protein_list = protein_ids_by_taxon_id.get(taxon_id, [])
        for protein_index, protein_id in enumerate(protein_list):
            lines.append(f"{taxon_index}_{protein_index}: {protein_id}")

    sequence_ids_f = os.path.join(
        output_dir, f"sequence_ids.sim_{sim_clusters}.seed_{seed}.txt"
    )

    with open(sequence_ids_f, "w") as fh:
        fh.write("\n".join(lines) + "\n")
        print(f"[+] wrote {sequence_ids_f}")


def write_clusters(taxon_ids, simulated_counts, seed, output_dir):
    rows = []
    padding = len(str(simulated_counts.shape[0]))
    max_count_by_taxon = collections.Counter()
    protein_ids_by_taxon_id = collections.defaultdict(list)
    for n, cluster in enumerate(simulated_counts):
        proteins_in_cluster = []
        for taxon_i, count in enumerate(cluster):
            for _ in range(count):
                taxon_id = taxon_ids[taxon_i]
                max_count_by_taxon[taxon_id] += 1
                protein_id = f"{taxon_id}.seq{max_count_by_taxon[taxon_id]}"
                protein_ids_by_taxon_id[taxon_id].append(protein_id)
                proteins_in_cluster.append(protein_id)
        proteins_in_cluster.sort()
        row = [f"OG0{n:0{padding}}:"]
        row.extend(proteins_in_cluster)
        rows.append(" ".join(row))

    cluster_f = os.path.join(output_dir, f"orthogroups.sim_{len(rows)}.seed_{seed}.txt")
    with open(cluster_f, "w") as fh:
        fh.write("\n".join(rows) + "\n")
        print(f"[+] wrote {cluster_f}")
    return protein_ids_by_taxon_id


def write_config_file(
    taxon_ids,
    sim_clusters,
    seed,
    with_taxid,
    with_outgroup,
    label_counts,
    output_dir,
):
    print("[+] Generating flexible config file...")
    rng = np.random.default_rng(seed)
    header = ["#IDX", "TAXON"]
    if with_taxid:
        header.append("TAXID")
    if with_outgroup:
        header.append("OUT")

    all_label_pools = []
    if label_counts:
        num_attributes = len(label_counts)
        attribute_names = [f"attr{i+1}" for i in range(num_attributes)]
        header.extend(attribute_names)
        for i, num_labels in enumerate(label_counts):
            pool = [f"attr{i+1}_label{j+1}" for j in range(num_labels)]
            all_label_pools.append(pool)

    rows = [",".join(header)]
    taxid_pool = [
        6238,
        318479,
        42156,
        6277,
        6239,
        1147741,
        42157,
        387005,
        7209,
        108094,
        6279,
        6287,
        6293,
        103827,
        42157,
        6280,
        6282,
        6293,
        7209,
    ]
    outgroup_idx = rng.choice(np.arange(len(taxon_ids))) if with_outgroup else -1

    for idx, taxon_id in enumerate(taxon_ids):
        row_data = [str(idx), taxon_id]

        if with_taxid:
            row_data.append(str(rng.choice(taxid_pool)))
        if with_outgroup:
            row_data.append("1" if idx == outgroup_idx else "0")
        if label_counts:
            for i in range(len(label_counts)):
                label_to_add = rng.choice(all_label_pools[i])
                row_data.append(label_to_add)

        rows.append(",".join(row_data))

    config_f = os.path.join(output_dir, f"config.sim_{sim_clusters}.seed_{seed}.txt")
    with open(config_f, "w") as fh:
        fh.write("\n".join(rows) + "\n")
        print(f"[+] wrote {config_f}")


def write_proteins(
    protein_ids_by_taxon_id,
    seed,
    output_dir,
    sim_clusters,
    length_max=200,
    length_min=10,
):
    rng = np.random.default_rng(seed)  # length rng
    random.seed(seed)  # aminoacid rng
    alphabet = [
        "A",
        "C",
        "D",
        "E",
        "F",
        "G",
        "H",
        "I",
        "K",
        "L",
        "M",
        "N",
        "P",
        "Q",
        "R",
        "S",
        "T",
        "V",
        "W",
        "Y",
    ]
    for taxon_id, protein_ids in protein_ids_by_taxon_id.items():
        lines = []
        fasta_f = os.path.join(
            output_dir, f"{taxon_id}.sim_{sim_clusters}.seed_{seed}.fasta"
        )

        protein_lengths = rng.integers(
            size=len(protein_ids), low=length_min, high=length_max
        )
        # print(f"{taxon_id=} {protein_ids=} {protein_lengths=}")
        for protein_id, protein_length in zip(protein_ids, protein_lengths):
            lines.append(
                f">{protein_id}\nM{''.join(random.choices(alphabet, k=(protein_length - 1)))}\n"
            )
        with open(fasta_f, "w") as fh:
            fh.write("".join(lines))
            print(f"[+] wrote {fasta_f}")


def adjust_matrix_dimensions(taxon_ids, matrix, desired_taxon_count, seed):
    num_original_taxa = matrix.shape[1]
    rng = np.random.default_rng(seed)

    if desired_taxon_count <= 0 or desired_taxon_count == num_original_taxa:
        print(f"[+] Using all {num_original_taxa} available taxa.")
        return taxon_ids, matrix

    if desired_taxon_count < num_original_taxa:
        print(
            f"[+] Subsampling from {num_original_taxa} down to {desired_taxon_count} taxa."
        )
        all_indices = np.arange(num_original_taxa)
        selected_indices = rng.choice(
            all_indices, size=desired_taxon_count, replace=False
        )
        selected_indices.sort()
        new_taxon_ids = [taxon_ids[i] for i in selected_indices]
        new_matrix = matrix[:, selected_indices]
        return new_taxon_ids, new_matrix

    if desired_taxon_count > num_original_taxa:
        num_to_add = desired_taxon_count - num_original_taxa
        print(
            f"[+] Extrapolating from {num_original_taxa} to {desired_taxon_count} by adding {num_to_add} synthetic taxa."
        )
        template_indices = rng.choice(
            np.arange(num_original_taxa), size=num_to_add, replace=True
        )
        new_columns = matrix[:, template_indices]
        new_matrix = np.hstack((matrix, new_columns))
        new_taxon_ids = list(taxon_ids)
        for i in range(num_to_add):
            new_taxon_ids.append(f"SimFin_{i+1}")

        return new_taxon_ids, new_matrix


"""
 Feature request:
 - simulate data with arg --taxon_ids M
 - uses real counts to spit out clusters for more or fewer taxon_ids
 
(n,m) matrix of counts
- n = number of clusters
- m = number of taxons

[
[1 1 1 1]
[2 2 2 2]
[1 0 1 0]
]

- cluster counts: 10_000 advanced 100_000 1_000_000
- taxon counts: 10 19 50 100
- config: 
    attributes 2 5 10
    labels 2 5 half-of-taxon-count 
"""
if __name__ == "__main__":
    __version__ = 0.1
    t_0 = time.monotonic()
    args = parse_args()
    try:
        os.makedirs(args.output_dir, exist_ok=True)
        if args.label_counts:
            for count in args.label_counts:
                if count < 2:
                    print(
                        f"\n[X] FATAL ERROR: All values for --label_counts (-lc) must be 2 or greater. You provided: {count}"
                    )
                    sys.exit(1)

        print(f"[+] For {args.output_dir} ...")

        print(
            f"[+] Simulating based on {args.sim_clusters=} {args.random_seed=} {args.groups_raw=} ..."
        )
        taxon_ids, matrix = get_count_matrix(args.groups_raw)
        taxon_ids, matrix = adjust_matrix_dimensions(
            taxon_ids,
            matrix,
            args.taxon_counts,
            args.random_seed,
        )

        non_empty_matrix = matrix[matrix.sum(axis=1) > 0]

        if non_empty_matrix.shape[0] == 0:
            print(
                "\n[X] FATAL ERROR: No non-empty orthogroups exist for the selected taxa."
            )
            print(
                "[X] Cannot proceed with simulation. Try a different or larger taxon set."
            )
            sys.exit()

        print(
            f"[+] Found {non_empty_matrix.shape[0]} non-empty cluster patterns to use for simulation."
        )

        simulated_counts = get_simulated_counts(
            non_empty_matrix,
            args.sim_clusters,
            args.random_seed,
        )
        print(f"[+] Simulated counts into {simulated_counts.shape=}")
        protein_ids_by_taxon_id = write_clusters(
            taxon_ids,
            simulated_counts,
            args.random_seed,
            args.output_dir,
        )
        write_sequence_ids(
            taxon_ids,
            protein_ids_by_taxon_id,
            args.random_seed,
            args.sim_clusters,
            args.output_dir,
        )
        write_config_file(
            taxon_ids,
            args.sim_clusters,
            args.random_seed,
            args.with_taxid,
            args.with_outgroup,
            args.label_counts,
            args.output_dir,
        )
        if args.fasta_sim:
            write_proteins(
                protein_ids_by_taxon_id,
                args.random_seed,
                args.output_dir,
                args.sim_clusters,
            )
        print(f"[+] Done {args.output_dir} ...\n")

    except Exception as exc:
        print(f"[X] Error {exc}\n{traceback.format_exc()}")
    finally:
        pass
