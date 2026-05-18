#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import collections
import csv
import logging
import pathlib
import sys
import traceback

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


def validate_file(f):
    if f is not None:
        f_path = pathlib.Path(f)
        if not f_path.is_file():
            logging.error(f"{f} is not a file")
            sys.exit(1)
    return f


def validate_float(f, f_min=0.0, f_max=1.0):
    if f is not None:
        if not (f_min < f < f_max):
            logging.error(f"{f} must be between {f_min} and {f_max}")
            sys.exit(1)
    return f


def get_argparse():
    class CustomFormatter(
        argparse.ArgumentDefaultsHelpFormatter,
        argparse.RawDescriptionHelpFormatter,
    ):
        pass

    parser = argparse.ArgumentParser(
        description="cluster_annotation.py script.",
        formatter_class=CustomFormatter,
        epilog=EPILOG,
    )
    parser.add_argument(
        "-i",
        "--cluster_ids",
        metavar="FILE",
        required=False,
        type=str,
        help="only these will be parsed from other files (if not supplied, all those in cluster_counts_by_taxon are parsed)",
    )
    parser.add_argument(
        "-c",
        "--cluster_counts_by_taxon",
        metavar="FILE",
        required=True,
        type=str,
        help="cluster_counts_by_taxon",
    )
    parser.add_argument(
        "-d",
        "--cluster_domain_annotation",
        metavar="FILE",
        required=True,
        type=str,
        help="cluster_domain_annotation.*.txt file (* = IPR/Pfam/GO/SignalP_Euk)",
    )
    parser.add_argument(
        "-p",
        "--annotation_protein_cov",
        metavar="FLOAT",
        required=False,
        type=float,
        default=0.75,
        help="Minimum protein coverage of domain in cluster",
    )
    parser.add_argument(
        "-x",
        "--annotation_taxon_cov",
        metavar="FLOAT",
        required=False,
        type=float,
        default=0.75,
        help="Minimum taxon coverage by proteins with domain in cluster",
    )
    parser.add_argument(
        "-t",
        "--tree_cluster_metrics",
        metavar="FILE",
        required=False,
        help="tree.cluster_metrics.txt file",
    )
    parser.add_argument(
        "-n",
        "--node_taxon_cov",
        metavar="FLOAT",
        required=False,
        type=float,
        default=0.75,
        help="Minimum taxon coverage of cluster in tree.cluster_metrics.txt",
    )
    return parser.parse_args()


class Cluster:
    def __init__(self, cluster_id, counter):
        self.cluster_id = cluster_id
        self.counter = counter
        self.node_taxon_cov = 0.0
        self.annotations = []
        self.annotation_ids = "None"
        self.annotation_descriptions = "None"
        self.synapomorphy = False

    def add_annotation(self, annotation):
        self.annotations.append(annotation)

    def infer_annotation_strings(self):
        ids, desc = [], []
        for annotation in sorted(
            self.annotations,
            key=lambda x: x.annotation_proteome_cov,
            reverse=True,
        ):
            ids.append(annotation.annotation_id)
            desc.append(annotation.annotation_description)
        if ids:
            self.annotation_ids = ";".join(ids)
            self.annotation_descriptions = ";".join(desc)

    def get_annotation_line(self):
        cluster_annotation_data = [
            self.cluster_id,
            str(self.counter["proteins"]),
            str(self.counter["taxa"]),
            self.annotation_ids,
            self.annotation_descriptions,
        ]
        return "\t".join(cluster_annotation_data)

    def get_annotation(self, node_id=None):
        if node_id is None:
            return {
                "cluster_id": self.cluster_id,
                "protein_count": str(self.counter["proteins"]),
                "taxon_count": str(self.counter["taxa"]),
                "node_taxon_coverage": str(self.node_taxon_cov),
                "annotation_ids": self.annotation_ids,
                "annotation_description": self.annotation_descriptions,
            }
        else:
            return {
                "cluster_id": self.cluster_id,
                "node_id": node_id,
                "protein_count": str(self.counter["proteins"]),
                "taxon_count": str(self.counter["taxa"]),
                "node_taxon_coverage": str(self.node_taxon_cov),
                "annotation_ids": self.annotation_ids,
                "annotation_description": self.annotation_descriptions,
            }


class Annotation:
    def __init__(
        self,
        annotation_id,
        annotation_description,
        annotation_proteome_cov,
        annotation_protein_cov,
    ):
        self.annotation_id = annotation_id
        self.annotation_description = annotation_description
        self.annotation_proteome_cov = annotation_proteome_cov
        self.annotation_protein_cov = annotation_protein_cov


class ClusterAnnotationParser:
    def __init__(self, args):
        self.cluster_ids_f = validate_file(args.cluster_ids)
        self.cluster_counts_by_taxon_f = validate_file(args.cluster_counts_by_taxon)
        self.cluster_domain_annotation_f = validate_file(args.cluster_domain_annotation)
        self.tree_cluster_metrics_f = validate_file(args.tree_cluster_metrics)
        self.annotation_protein_cov = validate_float(args.annotation_protein_cov)
        self.annotation_taxon_cov = validate_float(args.annotation_taxon_cov)
        self.node_taxon_cov = validate_float(args.node_taxon_cov)

        self.cluster_ids = []
        self.clusters = {}
        self.cluster_ids_by_node = collections.defaultdict(list)

        self.annotation_all_f = self.get_annotation_all_fn()
        self.annotation_synapomorphies_f = self.get_annotation_synapo_fn()

    def get_annotation_all_fn(self):
        p = f"{self.annotation_protein_cov * 100:0.0f}"
        x = f"{self.annotation_taxon_cov * 100:.0.0f}"
        return f"cluster_functional_annotation.all.p{p}.x{x}.tsv"

    def get_annotation_synapo_fn(self):
        p = f"{self.annotation_protein_cov * 100:0.0f}"
        x = f"{self.annotation_taxon_cov * 100:.0.0f}"
        n = f"{self.node_taxon_cov * 100:.0.0f}"
        return f"cluster_functional_annotation.synapomorphies.p{p}.x{x}.n{n}.tsv"

    def add_cluster_to_node(self, cluster_id, node_id):
        self.cluster_ids_by_node[node_id].append(cluster_id)

    def parse(self):
        self._parse_cluster_ids()
        self._parse_cluster_counts()
        self._parse_cluster_annotation()
        self._parse_cluster_tree_metrics()

    def _parse_cluster_tree_metrics(self):
        if self.tree_cluster_metrics_f is not None:
            filter_set = set(self.cluster_ids)
            try:
                logger.info(f"parsing {self.tree_cluster_metrics_f}")
                with open(self.tree_cluster_metrics_f) as fh:
                    reader = csv.reader(fh, delimiter="\t")
                    next(reader, None)  # skip header
                    for row in reader:
                        cluster_id = row[0]
                        if cluster_id in filter_set:
                            node_id = row[1]
                            node_taxon_cov = float(row[3])
                            if node_taxon_cov >= self.node_taxon_cov:
                                self.clusters[cluster_id].synapomorphy = True
                                self.clusters[
                                    cluster_id
                                ].node_taxon_coverage = node_taxon_cov
                                self.add_cluster_to_node(cluster_id, node_id)
            except Exception as exc:
                logger.error(
                    f"failed to parse {self.tree_cluster_metrics_f} - {exc}\n{traceback.format_exc()}"
                )
                sys.exit(1)

    def _parse_cluster_counts(self):
        filter_flag = False
        if self.cluster_ids:
            filter_flag = True
            filter_set = set(self.cluster_ids)
        try:
            logger.info(f"parsing {self.cluster_counts_by_taxon_f}")
            with open(self.cluster_counts_by_taxon_f) as fh:
                reader = csv.reader(fh, delimiter="\t")
                next(reader, None)  # skip header
                for row in reader:
                    cluster_id = row[0]
                    if filter_flag is False or cluster_id in filter_set:
                        counter = collections.Counter()
                        for count in row[1:]:
                            counter["proteins"] += int(count)
                            counter["taxa"] += bool(int(count))
                        self.clusters[cluster_id] = Cluster(
                            cluster_id=cluster_id,
                            counter=counter,
                        )
                        self.cluster_ids.append(cluster_id)
        except Exception as exc:
            logger.error(
                f"failed to parse {self.cluster_counts_by_taxon_f} - {exc}\n{traceback.format_exc()}"
            )
            sys.exit(1)

    def _parse_cluster_ids(self):
        if self.cluster_ids_f is not None:
            try:
                with open(self.cluster_ids_f) as fh:
                    for line in fh:
                        self.cluster_ids.append(line.rstrip("\n"))
            except Exception as exc:
                logger.error(
                    f"failed to parse {self.cluster_ids_f} - {exc}\n{traceback.format_exc()}"
                )
                sys.exit(1)

    def _parse_cluster_annotation(self):
        filter_set = set(self.cluster_ids)
        try:
            logger.info(f"parsing {self.cluster_domain_annotation_f}")
            with open(self.cluster_domain_annotation_f) as fh:
                reader = csv.reader(fh, delimiter="\t")
                # next(reader, None)  # has no header ... [ToDo] add header
                for row in reader:
                    cluster_id = row[0]
                    if cluster_id in filter_set:
                        annotation_id = row[2]
                        annotation_description = row[3]
                        annotation_protein_cov = int(row[5]) / int(row[4])
                        annotation_taxon_cov = float(row[6])
                        if (
                            annotation_protein_cov >= self.annotation_protein_cov
                            and annotation_taxon_cov >= self.annotation_taxon_cov
                        ):
                            self.clusters[cluster_id].add_annotation(
                                Annotation(
                                    (
                                        annotation_id,
                                        annotation_description,
                                        annotation_protein_cov,
                                        annotation_taxon_cov,
                                    )
                                )
                            )
        except Exception as exc:
            logger.error(
                f"failed to parse {self.cluster_domain_annotation_f} - {exc}\n{traceback.format_exc()}"
            )
            sys.exit(1)

    def write(self):
        annotation_all_writer = 
        if self.tree_cluster_metrics_f is not None:

        annotation_all_lines = []
        annotation_synapomorphies_lines = []

        for cluster_id in self.cluster_ids:
            clusterObj = self.clusterObjs_by_cluster_id[cluster_id]
            line = clusterObj.get_domain_line_all()
            output.append(line)

        output = []
        header = []
        out_f = ""
        if self.all_flag:
            out_f = "cluster_functional_annotation.all.p%s.x%s.tsv" % (
                "{0:.0f}".format(self.annotation_protein_cov * 100),
                "{0:.0f}".format(self.annotation_taxon_cov * 100),
            )
            header = "\t".join(
                [
                    "cluster_id",
                    "PC",
                    "TC",
                    "domain_id",
                    "domain_desc",
                ]
            )
            for cluster_id in self.cluster_ids:
                clusterObj = self.clusterObjs_by_cluster_id[cluster_id]
                line = clusterObj.get_domain_line_all()
                output.append(line)
            write_file(out_f, self.outprefix, header, output)
        if self.synapo_flag:
            out_f = "cluster_functional_annotation.synapo.p%s.x%s.n%s.tsv" % (
                "{0:.0f}".format(self.annotation_protein_cov * 100),
                "{0:.0f}".format(self.annotation_taxon_cov * 100),
                "{0:.0f}".format(self.NODE_TAXON_COV * 100),
            )
            header = "\t".join(
                [
                    "cluster_id",
                    "node_id",
                    "node_desc",
                    "PC",
                    "TC",
                    "node_cov",
                    "domain_ids",
                    "domain_desc",
                ]
            )
            for node_id in self.node_ids:
                node_description = self.node_description_by_node_id.get(
                    node_id, node_id
                )
                clusterObjs = [
                    self.clusterObjs_by_cluster_id[cluster_id]
                    for cluster_id in self.cluster_ids_by_node_id[node_id]
                ]
                for clusterObj in sorted(
                    clusterObjs, key=lambda x: x.node_taxon_cov, reverse=True
                ):
                    line = clusterObj.get_domain_line_synapo(node_id, node_description)
                    output.append(line)
            write_file(out_f, self.outprefix, header, output)


if __name__ == "__main__":
    __version__ = 0.1
    parser = ClusterAnnotationParser(args=get_argparse())
    parser.parse()
    # parser.write_annotation_tsv()
    # parser.write_stats()
