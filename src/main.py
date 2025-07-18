#!/usr/bin/env python3

import os
import sys

from api import run_server
from cli import run_cli
from cli.commands import parse_args
from core.input import InputData, ServeArgs
from core.utils import check_file

if __name__ == "__main__":
     # Without these files, application won't start
    base_dir = os.getcwd()
    nodesdb_f = os.path.join(base_dir, "data/nodesdb.txt")
    pfam_mapping_f = os.path.join(base_dir, "data/Pfam-A.clans.tsv.gz")
    ipr_mapping_f = os.path.join(base_dir, "data/entry.list")
    go_mapping_f = os.path.join(base_dir, "data/interpro2go")

    try:
        check_file(nodesdb_f, install_kinfin=True)
        check_file(pfam_mapping_f, install_kinfin=True)
        check_file(ipr_mapping_f, install_kinfin=True)
        check_file(go_mapping_f, install_kinfin=True)
    except FileNotFoundError as e:
        sys.exit(str(e))

    args = parse_args(nodesdb_f, pfam_mapping_f, ipr_mapping_f, go_mapping_f)

    if isinstance(args, ServeArgs):
        # cluster_f, sequence_ids_f, and taxon_idx_mapping_file will be set dynamically at runtime (from /init)
        run_server(
            args=args,
            nodesdb_f=nodesdb_f,
            go_mapping_f=go_mapping_f,
            ipr_mapping_f=ipr_mapping_f,
            pfam_mapping_f=pfam_mapping_f,
            cluster_f="",  # dummy
            sequence_ids_f="",  # dummy
            taxon_idx_mapping_file="",  # dummy
        )
    elif isinstance(args, InputData):
        run_cli(args)
    else:
        sys.exit("[ERROR] - Invalid input provided.")
