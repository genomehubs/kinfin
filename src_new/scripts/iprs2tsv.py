#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import collections
import csv
import hashlib
import logging
import pathlib
import statistics
import sys
import traceback

INTERPROSCAN_FIELDNAMES = [
    "sequence_id",
    "sequence_md5",
    "length",
    "analysis",
    "signature_accession",
    "signature_description",
    "start",
    "stop",
    "score",
    "status",
    "date",
    "interpro_accession",
    "interpro_description",
    "go_annotation",
]

INTERPRO2GO_PATH = pathlib.Path(f"{__file__}/../../data/interpro2go").resolve()

# LOGGING (only log to stderr, move somewhere)

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

# interproscan output format: https://interproscan-docs.readthedocs.io/en/v5/OutputFormats.html#tab-separated-values-format-tsv


def get_argparse():
    class CustomFormatter(
        argparse.ArgumentDefaultsHelpFormatter,
        argparse.RawDescriptionHelpFormatter,
    ):
        pass

    parser = argparse.ArgumentParser(
        description="iprs2tsv.py script.",
        formatter_class=CustomFormatter,
        epilog=EPILOG,
    )
    parser.add_argument(
        "-f",
        metavar="FILE",
        required=True,
        type=str,
        help="Interproscan file",
    )
    parser.add_argument(
        "-o",
        metavar="OUTPREFIX",
        required=False,
        type=str,
        default="",
        help="Prefix for output file",
    )
    parser.add_argument(
        "-a",
        metavar="ANALYSES",
        required=False,
        type=str,
        default="SignalP_EUK,Pfam",
        help="Analysis types to parse, comma-separated (4th column in interproscan TSV)",
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


class Protein:
    def __init__(self, sequence_id=None, sequence=None, sequence_md5=None, length=None):
        self.id = sequence_id
        self.sequence = sequence
        self.sequence_md5 = sequence_md5
        self.length = length
        self.annotations = collections.defaultdict(list)
        self.counts = collections.defaultdict(collections.Counter)
        self.validate()

    def validate(self):
        if self.sequence_md5 is None:
            try:
                self.sequence_md5 = hashlib.md5(self.sequence)
            except Exception:
                logger.warning(
                    f"protein_id={self.id}: failed to calculate MD5 from '{self.sequence}'"
                )
                self.sequence_md5 = None
        if self.length is None:
            try:
                self.length = len(self.sequence)
            except Exception:
                logger.warning(
                    f"protein_id={self.id}: failed to calculate length from '{self.sequence}'"
                )
                self.length = None

    def add_annotation(self, d):
        annotation = Annotation(d)
        self.annotations[annotation.analysis].append(annotation)
        self.counts[annotation.analysis][annotation.signature_accession] += 1
        if annotation.interpro_accession:
            self.counts["IPR"][annotation.interpro_accession] += 1
        if annotation.go_annotation:
            for go_annotation in annotation.go_annotation:
                if go_annotation:
                    self.counts["GO"][go_annotation] += 1

    def get_functional_annotation(self, analyses):
        line = [self.id]
        for analysis in analyses:
            field = []
            if analysis in self.counts:
                for accession, count in self.counts[analysis].items():
                    string = (
                        f"{accession}" if analysis == "GO" else f"{accession}:{count}"
                    )
                    field.append(string)
            else:
                field.append("None")
            line.append(f"{';'.join(sorted(field))}")

        return "\t".join(line)


class Annotation:
    def __init__(self, d):
        self.analysis = d["analysis"]
        self.signature_accession = d["signature_accession"]
        self.signature_description = d["signature_description"]
        self.start = d["start"]
        self.stop = d["stop"]
        self.score = d["score"]
        self.status = d["status"]
        self.date = d["date"]
        self.interpro_accession = d["interpro_accession"]
        self.interpro_description = d["interpro_accession"]
        self.go_annotation = d["go_annotation"]


class InterproscanParser:
    def __init__(self, args):
        self.interproscan_fn = args.f
        self.outprefix = args.o
        self.analysis_types = args.a.split(",")
        self.interpro2go_fn = INTERPRO2GO_PATH
        self.analyses = ["GO", "IPR"] + self.analysis_types
        self.write_csv = args.J
        self.write_json = args.j
        self.out_fn = None
        self.stats_csv_fn = None
        self.stats_json_fn = None
        self.proteins = {}
        self.validate_args()

    def validate_args(self):
        interproscan_path = pathlib.Path(self.interproscan_fn)
        if not interproscan_path.is_file():
            logging.error(f"{self.interproscan_fn} is not a file")
            sys.exit(1)
        self.stats_csv_fn = str(interproscan_path.with_suffix(".stats.csv"))
        self.stats_json_fn = str(interproscan_path.with_suffix(".stats.json"))
        self.out_fn = str(interproscan_path.with_suffix(".functional_annotation.tsv"))
        interpro2go_path = pathlib.Path(self.interpro2go_fn)
        if not interpro2go_path.is_file():
            logger.error(f"{self.interpro2go_fn} not found")
            sys.exit(1)

    def parse(self):
        logger.info(f"parsing {self.interproscan_fn}")
        try:
            with open(self.interproscan_fn) as fh:
                reader = csv.DictReader(
                    fh,
                    delimiter="\t",
                    fieldnames=INTERPROSCAN_FIELDNAMES,
                    restkey="others",
                )
                for row in reader:
                    # remove GO pipes
                    if row["go_annotation"] is not None:
                        row["go_annotation"] = row["go_annotation"].split("|")
                    # create Protein
                    if row["sequence_id"] not in self.proteins:
                        self.proteins[row["sequence_id"]] = Protein(
                            sequence_id=row["sequence_id"],
                            sequence=None,
                            sequence_md5=row["sequence_md5"],
                            length=row["length"],
                        )
                    # add annotation
                    self.proteins[row["sequence_id"]].add_annotation(row)
        except Exception as exc:
            logger.error(
                f"failed to parse {self.interproscan_fn} - {exc}\n{traceback.format_exc()}"
            )
            sys.exit(1)

    def write_stats(self):
        # stats_analysis := count unique IDs per analysis
        stats_analysis = collections.defaultdict(collections.Counter)
        # stats_proteins := mean/stdev IDs per protein per analysis
        stats_proteins = collections.defaultdict(list)
        for _id, protein in sorted(self.proteins.items()):
            for analysis in self.analyses:
                stats_analysis[analysis] += protein.counts[analysis]
                stats_proteins[analysis].append(sum(protein.counts[analysis].values()))
        output = []
        for analysis in self.analyses:
            annotation_count = len(stats_analysis[analysis])
            proteins_count = len(stats_proteins[analysis])
            proteins_mean = statistics.mean(stats_proteins[analysis])
            proteins_stdev = statistics.stdev(stats_proteins[analysis])
            log_string = f"{analysis}: {annotation_count} unique IDs in {proteins_count} proteins (per protein mean={proteins_mean}, stdev={proteins_stdev})"
            output.append(log_string)
        print("\n".join(output))

    def write_annotation_tsv(self):
        logger.info(f"writing output to {self.out_fn} ...")
        output = ["\t".join(["#protein_id"] + self.analyses)]
        for _id, protein in sorted(self.proteins.items()):
            line = protein.get_functional_annotation(analyses=self.analyses)
            output.append(line)
        with open(self.out_fn, "w") as fh:
            fh.write("\n".join(output) + "\n")


if __name__ == "__main__":
    parser = InterproscanParser(args=get_argparse())
    parser.parse()
    parser.write_annotation_tsv()
    parser.write_stats()
