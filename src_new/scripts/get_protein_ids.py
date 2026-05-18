#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
usage: get_sequence_ids.py    -g <FILE> [--protein_ids <FILE>]
                                            [-c <STRING>] [--cluster_ids <FILE>] [-s]
                                            [-o <STR>]
                                            [-h|--help]

    Options:
        -h --help                       show this
        -g, --groups <FILE>             OrthologousGroups.txt produced by OrthoFinder
        --protein_ids <FILE>            Filter based on sequence IDs in file
        -c, --cluster <STRING>          Filter based on cluster ID
        --cluster_ids <FILE>            Filter based on cluster IDs in file
        -o, --outprefix <STR>           Outprefix
        -s, --single_out_file           Write all proteins to a single file

"""

# LOGGING (only log to stderr, move somewhere)
import logging
import sys

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] [%(levelname)s] %(filename)s - %(message)s",
    stream=sys.stderr,
)

logger = logging.getLogger(__file__)


# ARGPARSE (move somewhere, use Rich's solution)

EPILOG = """hints:
[+]
[+]
[+]
"""


import argparse

"""
- add stats about where the proteins come from
    - taxon coverages 
    - cluster type: singleton, non-singleton

"""


def get_argparse():
    class CustomFormatter(
        argparse.ArgumentDefaultsHelpFormatter,
        argparse.RawDescriptionHelpFormatter,
    ):
        pass

    parser = argparse.ArgumentParser(
        description="get_sequence_ids.py script.",
        formatter_class=CustomFormatter,
        epilog="""Comments
        -> extracts sequence IDs of Orthogroups based on:
        -> 1.1 list of sequence IDs in file ('-p')
        -> 1.2 one sequence ID ('-P')
        -> 1.3 list of group IDs in file ('-c')
        -> 1.4 one group ID ('-C')
        -> and writes it to
        -> 2.1 a file for each group ('-G') (default)
        -> 2.2 one file for all sequence IDs ('-s')
        -> 2.3 stdout ('-w') (only available for options 1.2 and 1.4)
        """,
    )
    parser.add_argument(
        "-f",
        metavar="ORTHORGROUPS",
        required=True,
        type=str,
        help="Orthofinder Orthogroups file",
    )
    parser.add_argument(
        "-p",
        metavar="SEQ_ID_FILE",
        required=False,
        type=str,
        help="File of sequence IDs. One per line",
    )
    parser.add_argument(
        "-P",
        metavar="SEQ_ID",
        required=False,
        type=str,
        help="Sequence ID",
    )
    parser.add_argument(
        "-c",
        metavar="GROUP_ID_FILE",
        required=False,
        type=str,
        help="File of group IDs. One per line",
    )
    parser.add_argument(
        "-a",
        metavar="PREFIX",
        required=False,
        type=str,
        default="",
        help="Prefix to add to each FASTA header written to file. Requires '-w'",
    )
    parser.add_argument(
        "-i",
        required=False,
        action="store_true",
        help="Includes all sequences with filter status in second column of header. Requires '-w'",
    )
    parser.add_argument(
        "-w",
        required=False,
        action="store_true",
        help="Write FASTA sequences to STDOUT",
    )
    return parser.parse_args()


def parse_headers(header_f):
    headers = {}
    with open(header_f) as header_fh:
        for line in header_fh:
            header = line.rstrip("\n")
            if header in headers:
                sys.exit("[-] header %s repeated" % (header))
            else:
                headers[header] = None
    return headers


def parse_clusters(clusters):
    clusters = {}
    with open(cluster_f) as cluster_fh:
        for line in cluster_fh:
            cluster = line.rstrip("\n")
            if cluster in clusters:
                sys.exit("[-] cluster %s repeated" % (cluster))
            else:
                clusters[cluster] = None
    return clusters


def parse_groups(group_f):
    output = {}
    with open(groups_f) as group_fh:
        for line in group_fh:
            clusterID, protein_string = line.rstrip("\n").split(": ")
            proteins = protein_string.split(" ")
            if headers:
                for protein in proteins:
                    if protein in headers:
                        if headers[protein] is None:
                            headers[protein] = clusterID
                            output[clusterID] = proteins
                        else:
                            sys.exit("[-] protein %s found more than once" % protein)
            else:
                if clusterID in clusters:
                    if clusters[clusterID] is None:
                        clusters[clusterID] = clusterID
                        output[clusterID] = proteins
                    else:
                        sys.exit("[-] cluster %s found more than once" % clusterID)
    return output


def write_output(output, outprefix):
    headers_found = set([k for k, v in headers.items() if v])
    clusters_found = set([k for k, v in clusters.items() if v])
    if headers:
        print(
            "[+] Found %s of headers ..."
            % "{:.0%}".format(len(headers_found) / len(headers))
        )
    if clusters:
        print(
            "[+] Found %s of clusters ..."
            % "{:.0%}".format(len(clusters_found) / len(clusters))
        )
    stats_f = "%s.parse_stats.txt" % (splitext(basename(groups_f))[0])
    if outprefix:
        stats_f = "%s.%s" % (outprefix, stats_f)
    if headers_found or clusters_found:
        print("[+] Writing files ...")
        if not single_out_file:
            stats_lines = []
            for clusterID, proteins in output.items():
                protein_lines = []
                protein_lines += proteins
                proteins_total = len(proteins)
                proteins_target = len([x for x in proteins if x in headers_found])
                proteins_non_target = proteins_total - proteins_target
                out_f = "%s.%s.txt" % (splitext(basename(groups_f))[0], clusterID)
                if outprefix:
                    out_f = "%s.%s" % (outprefix, out_f)
                with open(out_f, "w") as out_fh:
                    out_fh.write("%s\n" % "\n".join(protein_lines))
                stats_lines.append(
                    "%s total=%s target=%s non-target=%s"
                    % (clusterID, proteins_total, proteins_target, proteins_non_target)
                )
            with open(stats_f, "w") as stats_fh:
                stats_fh.write("%s\n" % "\n".join(stats_lines))
        else:
            protein_lines = []
            out_f = "%s.protein_ids.txt" % (splitext(basename(cluster_f))[0])
            if outprefix:
                out_f = "%s.%s" % (outprefix, out_f)
            for clusterID, proteins in output.items():
                protein_lines += proteins
            with open(out_f, "w") as out_fh:
                out_fh.write("%s\n" % "\n".join(protein_lines))


if __name__ == "__main__":
    __version__ = 0.3
    args = docopt(__doc__)
    groups_f = args["--groups"]
    header_f = args["--protein_ids"]
    cluster_id = args["--cluster"]
    cluster_f = args["--cluster_ids"]
    single_out_file = args["--single_out_file"]
    outprefix = args["--outprefix"]

    headers = {}
    clusters = {}

    print("[+] Start ...")
    if header_f:
        print("[+] Parsing headers in %s ..." % header_f)
        parse_type = "header"
        headers = parse_headers(header_f)
    elif cluster_id:
        print("[+] Getting cluster %s ..." % cluster_id)
        clusters[cluster_id] = None
    elif cluster_f:
        print("[+] Parsing clusters in %s ..." % cluster_f)
        parse_type = "cluster"
        clusters = parse_clusters(cluster_f)
    else:
        sys.exit(__doc__.strip())
    print("[+] Parse groups %s ..." % groups_f)
    output = parse_groups(groups_f)
    write_output(output, outprefix)
