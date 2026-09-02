#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import collections
import csv
import json
import logging
import pathlib
import re
import sys

# LOGGING (only log to stderr, move somewhere)

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] [%(levelname)s] %(filename)s - %(message)s",
    stream=sys.stderr,
)

logger = logging.getLogger(__file__)


# ARGPARSE (move somewhere, use Rich's solution)

EPILOG = """hints:
[+] Counts sequences in FASTA file given parameters
[+] Writes stats to STDERR, a CSV ('-J'), and JSON ('-j') file
[+] if '-w' is specified, writes single-line FASTA sequences STDOUT
"""


def get_argparse():
    class CustomFormatter(
        argparse.ArgumentDefaultsHelpFormatter,
        argparse.RawDescriptionHelpFormatter,
    ):
        pass

    parser = argparse.ArgumentParser(
        formatter_class=CustomFormatter,
        epilog=EPILOG,
    )
    parser.add_argument(
        "-f",
        metavar="FILE",
        required=True,
        type=str,
        help="FASTA file",
    )
    parser.add_argument(
        "-m",
        metavar="MINLEN",
        required=False,
        type=int,
        default=30,
        help="Only include sequences which have at least this length",
    )
    parser.add_argument(
        "-M",
        metavar="MAXLEN",
        required=False,
        type=int,
        default=100_000,
        help="Only include sequences which do not exceed this length",
    )
    parser.add_argument(
        "-s",
        metavar="MAXSTOPS",
        required=False,
        type=int,
        default=0,
        help="Only include sequences which do not exceed the number of non-terminal stops",
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
        help="Includes ALL sequences. Adds filter status in second column of header. Requires '-w'",
    )
    parser.add_argument(
        "-w",
        required=False,
        action="store_true",
        help="Write FASTA sequences to STDOUT",
    )
    parser.add_argument(
        "-j",
        required=False,
        action="store_true",
        help="Stats in JSON file",
    )
    parser.add_argument(
        "-J",
        required=False,
        action="store_true",
        help="Stats in CSV file",
    )
    return parser.parse_args()


def sanitize_name(header, prefix=""):
    if prefix == "":
        return re.sub(r"[\W_]+", "_", header)
    return ".".join([prefix, re.sub(r"[\W_]+", "_", header)])


def yield_fasta(infile):
    with open(infile) as fh:
        header, seqs = "", []
        for line in fh:
            if line[0] == ">":
                if header:
                    yield header, "".join(seqs)
                # Header is split at first whitespace
                header, seqs = line[1:-1].split(" ")[0], []
            else:
                seqs.append(line[:-1])
        yield header, "".join(seqs)


class SeqObj:
    def __init__(self, header, sequence, prefix=""):
        self.header = sanitize_name(header, prefix)
        self.sequence = sequence
        self.length = len(sequence)
        self.non_terminal_stops = self.sequence.rstrip("*").count("*")
        self.fails = []

    def to_string(self, include_status=False):
        if include_status:
            return (
                f">{self.header}\t{self.length}\t{self.get_status()}\n{self.sequence}"
            )
        return f">{self.header}\n{self.sequence}"

    def add_fail(self, fail):
        self.fails.append(fail)

    def get_status(self, as_list=False):
        status = ["PASS"] if self.is_pass() else self.fails
        if as_list:
            return status
        return ",".join(sorted(status))

    def is_pass(self):
        return not len(self.fails)


class Parser:
    def __init__(self, args):
        self.fasta_in_fn = args.f
        self.stops_max = args.s
        self.write_fasta = args.w
        self.fasta_prefix = args.a
        self.length_min = args.m
        self.length_max = args.M
        self.include_all = args.i
        self.write_csv = args.J
        self.write_json = args.j
        self.stats_csv_fn = None
        self.stats_json_fn = None
        self.stats = collections.Counter()
        self.validate_args()

    def validate_args(self):
        if self.length_max < self.length_min:
            logging.error(
                f"invalid parameters: '-m {self.length_min}' must be smaller than '-M {self.length_max}'."
            )
            sys.exit(1)
        fasta_path = pathlib.Path(self.fasta_in_fn)
        if not fasta_path.is_file():
            logging.error(f"{self.fasta_in_fn} is not a file.")
            sys.exit(1)
        self.stats_csv_fn = str(fasta_path.with_suffix(".stats.csv"))
        self.stats_json_fn = str(fasta_path.with_suffix(".stats.json"))

    def parse(self):
        for header, sequence in yield_fasta(self.fasta_in_fn):
            self.stats["TOTAL"] += 1
            seq_obj = SeqObj(
                header=header,
                sequence=sequence,
                prefix=self.fasta_prefix,
            )
            if seq_obj.non_terminal_stops > self.stops_max:
                seq_obj.add_fail("STOP_FAIL")
            if seq_obj.length > self.length_max:
                seq_obj.add_fail("LENGTH_MAX_FAIL")
            if seq_obj.length < self.length_min:
                seq_obj.add_fail("LENGTH_MIN_FAIL")
            for status in seq_obj.get_status(as_list=True):
                self.stats[status] += 1
            if self.write_fasta is True:
                print(seq_obj.to_string(include_status=self.include_all))

    def get_stats(self):
        fieldnames = [
            "FILE",
            "TOTAL",
            "TOTAL_P",
            "PASS",
            "PASS_P",
            "STOP_FAIL",
            "STOP_FAIL_P",
            "LENGTH_MIN_FAIL",
            "LENGTH_MIN_FAIL_P",
            "LENGTH_MAX_FAIL",
            "LENGTH_MAX_FAIL_P",
        ]
        stats = {}
        for fieldname in fieldnames:
            if fieldname == "FILE":
                stats[fieldname] = self.fasta_in_fn
            elif not fieldname.endswith("_P"):
                stats[fieldname] = self.stats[fieldname]
                stats[f"{fieldname}_P"] = (
                    f"{self.stats[fieldname] / self.stats['TOTAL']:.3%}"
                )
            else:
                pass
        return stats

    def write_stats(self):
        stats = self.get_stats()
        stats_log = " ".join(
            f"{k}={v}"
            for k, v in stats.items()
            if k
            in [
                "FILE",
                "TOTAL",
                "PASS",
                "STOP_FAIL",
                "LENGTH_MIN_FAIL",
                "LENGTH_MAX_FAIL",
            ]
        )
        logger.info(f"{stats_log}")
        if self.write_csv:
            with open(self.stats_csv_fn, "w") as fh:
                writer = csv.DictWriter(fh, fieldnames=stats.keys())
                writer.writeheader()
                writer.writerow(stats)
        if self.write_json:
            stats_json = {
                stats["FILE"]: {k: v for k, v in stats.items() if not k == "FILE"}
            }
            with open(self.stats_json_fn, "w") as fh:
                json.dump(stats_json, fh, indent=4)


if __name__ == "__main__":
    parser = Parser(args=get_argparse())
    parser.parse()
    parser.write_stats()
