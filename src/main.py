#!/usr/bin/env python3

import argparse
import logging
import os
import sys
import time

from internal import analyse
from internal.utils import check_file

if "SCALENE_ALLOCATION_SAMPLING_WINDOW" in os.environ:

    def run_server(**kwargs):
        sys.exit("Server commented out for profiling.")

else:
    from api import run_server

logger = logging.getLogger("kinfin_logger")


def main():
    # ---- Initial Setup ----
    base_dir = os.getcwd()
    nodesdb_f = os.path.join(base_dir, "data/nodesdb.txt")
    ndb_f = os.path.join(base_dir, "db/ndb.parquet")

    # TODO: Handle pfam, ipr, go
    # pfam_mapping_f = os.path.join(base_dir, "data/Pfam-A.clans.tsv.gz")
    # ipr_mapping_f = os.path.join(base_dir, "data/entry.list")
    # go_mapping_f = os.path.join(base_dir, "data/interpro2go")

    try:
        check_file(nodesdb_f, install_kinfin=True)
    except FileNotFoundError as e:
        sys.exit(str(e))

    # ---- Parse Arguments ----
    parser = argparse.ArgumentParser(
        description="Kinfin proteome cluster analysis tool"
    )

    subparsers = parser.add_subparsers(title="command", required=True, dest="command")
    api_parser = subparsers.add_parser("serve", help="Start the server")
    api_parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8000,
        help="Port number for the server (default: 8000)",
    )

    cli_parser = subparsers.add_parser("analyse", help="Perform analysis")
    required_group = cli_parser.add_argument_group("Required Arguments")
    required_group.add_argument(
        "-g",
        "--cluster_file",
        help="OrthologousGroups.txt produced by OrthoFinder",
        required=True,
    )
    required_group.add_argument(
        "-c", "--config_file", help="Config file (in CSV format)", required=True
    )
    general_group = cli_parser.add_argument_group("General Options")
    general_group.add_argument("-o", "--output_path", help="Output prefix")

    args = parser.parse_args()
    if args.command == "serve":
        #  ---- RUN SERVER ----
        run_server(port=args.port, nodesdb_f=nodesdb_f, ndb_f=ndb_f, cluster_f="")
    elif args.command == "analyse":
        # ---- RUN POLARS ANALYSIS ----
        analyse(args, nodesdb_f=nodesdb_f, ndb_f=ndb_f)


if __name__ == "__main__":
    overall_start = time.time()
    main()
    overall_end = time.time()
    overall_elapsed = overall_end - overall_start
    logger.info(f"Took {overall_elapsed}s to run kinfin.")
