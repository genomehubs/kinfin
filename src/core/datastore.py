import os
import shutil
import time
from collections import Counter, defaultdict
from typing import Any, Dict, FrozenSet, Generator, List, Optional, Set, Tuple

import matplotlib as mat
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.ticker import FormatStrFormatter, NullFormatter

from core.alo import AttributeLevel
from core.alo_collections import AloCollection
from core.build import (
    build_AloCollection,
    build_AloCollection_from_json,
    build_ClusterCollection,
    build_ProteinCollection,
)
from core.clusters import Cluster, ClusterCollection
from core.input import InputData
from core.logic import get_ALO_cluster_cardinality, get_attribute_cluster_type
from core.proteins import ProteinCollection
from core.utils import logger, median, progress, statistic

mat.use("agg")

plt.style.use("ggplot")
mat.rc("ytick", labelsize=20)
mat.rc("xtick", labelsize=20)
axis_font = {"size": "20"}
mat.rcParams.update({"font.size": 22})


class DataFactory:
    def __init__(self, inputData: InputData) -> None:
        self.dirs = {}
        self.inputData: InputData = inputData
        if isinstance(self.inputData.config_data, str):
            self.aloCollection: AloCollection = build_AloCollection(
                config_f=self.inputData.config_data,
                nodesdb_f=self.inputData.nodesdb_f,
                tree_f=self.inputData.tree_f,
                taxranks=self.inputData.taxranks,
            )
        elif self.inputData.taxon_idx_mapping_file is not None:
            self.aloCollection: AloCollection = build_AloCollection_from_json(
                nodesdb_f=self.inputData.nodesdb_f,
                tree_f=self.inputData.tree_f,
                taxranks=self.inputData.taxranks,
                json_list=self.inputData.config_data,
                taxon_idx_mapping_file=self.inputData.taxon_idx_mapping_file,
            )
        else:
            raise ValueError("[ERROR] - Either provide config file or json")

        self.proteinCollection: ProteinCollection = build_ProteinCollection(
            aloCollection=self.aloCollection,
            fasta_dir=self.inputData.fasta_dir,
            go_mapping_f=self.inputData.go_mapping_f,
            functional_annotation_f=self.inputData.functional_annotation_f,
            ipr_mapping=self.inputData.ipr_mapping,
            ipr_mapping_f=self.inputData.ipr_mapping_f,
            pfam_mapping=self.inputData.pfam_mapping,
            pfam_mapping_f=self.inputData.pfam_mapping_f,
            sequence_ids_f=self.inputData.sequence_ids_f,
            species_ids_f=self.inputData.species_ids_f,
        )
        self.clusterCollection: ClusterCollection = build_ClusterCollection(
            cluster_f=self.inputData.cluster_f,
            proteinCollection=self.proteinCollection,
            infer_singletons=self.inputData.infer_singletons,
        )

    def setup_dirs(self) -> None:
        """
        Set up output directories for storing results and attributes.
        """
        output_path: Optional[str] = self.inputData.output_path

        if output_path:
            if not os.path.isabs(output_path):
                output_path = os.path.abspath(output_path)
        else:
            output_path = os.path.join(os.getcwd(), "kinfin_results")

        self.dirs["main"] = output_path
        logger.info("[STATUS] - Output directories in")
        logger.info(f"\t{output_path}")
        if os.path.exists(output_path):
            logger.info("[STATUS] - Directory exists. Deleting directory ...")
            shutil.rmtree(output_path)

        logger.info("[STATUS] - Creating directories ...")
        os.mkdir(output_path)
        for attribute in self.aloCollection.attributes:
            attribute_path = os.path.join(output_path, attribute)
            self.dirs[attribute] = attribute_path
            if not os.path.exists(attribute_path):
                logger.info(f"\t{attribute_path}")
                os.mkdir(attribute_path)

        if self.aloCollection.tree_ete is not None:
            tree_path = os.path.join(output_path, "tree")
            node_chart_path = os.path.join(tree_path, "charts")
            node_header_path = os.path.join(tree_path, "headers")

            if not os.path.exists(tree_path):
                logger.info(f"\t{tree_path}")
                os.mkdir(tree_path)
                self.dirs["tree"] = tree_path

                logger.info(f"\t{node_chart_path}")
                os.mkdir(node_chart_path)
                self.dirs["tree_charts"] = node_chart_path

                if self.inputData.plot_tree:
                    logger.info(f"\t{node_header_path}")
                    os.mkdir(node_header_path)
                    self.dirs["tree_headers"] = node_header_path

    def analyse_clusters(self) -> None:
        if self.clusterCollection.inferred_singletons_count:
            logger.info(
                f"[STATUS]\t - Clusters found = {
                    self.clusterCollection.cluster_count} (of which {
                    self.clusterCollection.inferred_singletons_count} were inferred singletons)"
            )

        else:
            logger.info(
                f"[STATUS]\t - Clusters found = {self.clusterCollection.cluster_count}"
            )

        parse_steps = self.clusterCollection.cluster_count / 100

        logger.info("[STATUS] - Analysing clusters ...")
        analyse_clusters_start = time.time()
        for idx, cluster in enumerate(self.clusterCollection.cluster_list):
            self.__analyse_cluster(cluster)
            progress(idx + 1, parse_steps, self.clusterCollection.cluster_count)
        analyse_clusters_end = time.time()
        analyse_clusters_elapsed = analyse_clusters_end - analyse_clusters_start
        logger.info(f"[STATUS] - Took {analyse_clusters_elapsed}s to analyse clusters")

    def plot_rarefaction_data(
        self,
        rarefaction_by_samplesize_by_level_by_attribute: Dict[
            str, Dict[str, Dict[int, List[int]]]
        ],
        dirs: Dict[str, str],
        plotsize: Tuple[float, float],
        plot_format: str,
        fontsize: int,
    ) -> None:
        for (
            attribute,
            rarefaction_by_samplesize_by_level,
        ) in rarefaction_by_samplesize_by_level_by_attribute.items():
            rarefaction_plot_f = os.path.join(
                dirs[attribute], f"{attribute}.rarefaction_curve.{plot_format}"
            )
            f, ax = plt.subplots(figsize=plotsize)
            ax.set_facecolor("white")
            max_number_of_samples = 0
            for idx, level in enumerate(rarefaction_by_samplesize_by_level):
                number_of_samples = len(rarefaction_by_samplesize_by_level[level])
                if number_of_samples > max_number_of_samples:
                    max_number_of_samples = number_of_samples
                colour = plt.cm.Paired(  # type: ignore
                    idx / len(rarefaction_by_samplesize_by_level)
                )  # type: ignore
                x_values = []
                y_mins = []
                y_maxs = []
                median_y_values = []
                median_x_values = []
                for x, y_reps in list(
                    rarefaction_by_samplesize_by_level[level].items()
                ):
                    x_values.append(x)
                    y_mins.append(min(y_reps))
                    y_maxs.append(max(y_reps))
                    median_y_values.append(median(y_reps))
                    median_x_values.append(x)
                x_array = np.array(x_values)
                y_mins_array = np.array(y_mins)
                y_maxs_array = np.array(y_maxs)
                ax.plot(
                    median_x_values, median_y_values, "-", color=colour, label=level
                )
                ax.fill_between(
                    x_array, y_mins_array, y_maxs_array, color=colour, alpha=0.5
                )
            ax.set_xlim([0, max_number_of_samples + 1])
            ax.set_ylabel("Count of non-singleton clusters", fontsize=fontsize)
            ax.set_xlabel("Sampled proteomes", fontsize=fontsize)

            ax.grid(True, linewidth=1, which="major", color="lightgrey")
            legend = ax.legend(
                ncol=1,
                numpoints=1,
                loc="lower right",
                frameon=True,
                fontsize=fontsize,
            )
            legend.get_frame().set_facecolor("white")
            logger.info(f"[STATUS]\t- Plotting {rarefaction_plot_f}")
            f.savefig(rarefaction_plot_f, format=plot_format)
            plt.close()

    def write_output(self) -> None:
        self.__plot_cluster_sizes()
        self.__write_cluster_counts_by_taxon()
        self.__write_cluster_metrics_domains()
        self.__write_cluster_metrics_domains_detailed()
        self.__write_attribute_metrics()
        self.__write_cluster_summary()
        self.__write_cluster_metrics_ALO()
        self.__write_cluster_1to1_ALO()
        self.__write_pairwise_representation()

    # analyse cluster
    def __analyse_ete_for_specific_cluster(
        self,
        cluster: Cluster,
        intersection: FrozenSet[str],
        node,
    ) -> None:
        node.counts["specific"] += 1  # type: ignore
        if cluster.proteome_count == 1:
            # But it only belongs to one proteome
            node.apomorphic_cluster_counts["non_singletons"] += 1  # type: ignore
        else:
            # It has more than one proteome
            child_nodes_covered = []
            child_node_proteome_coverage_strings = []
            child_node_proteome_ids_covered_count = 0
            for child_node in node.get_children():
                if child_node.proteome_ids.isdisjoint(cluster.proteome_ids):
                    # No child node proteomes are not in cluster
                    child_nodes_covered.append(False)
                else:
                    # At least on child node proteome in cluster
                    child_nodes_covered.append(True)
                    child_node_proteome_ids_covered_count = len(
                        cluster.proteome_ids.intersection(child_node.proteome_ids)
                    )
                    child_node_proteome_coverage_strings.append(
                        f"{child_node.name}=({child_node_proteome_ids_covered_count}/{len(child_node.proteome_ids)})"
                    )
            if all(child_nodes_covered):
                # At least one proteome of each child node in cluster
                # => SYNAPOMORPHY
                node_proteome_coverage = len(intersection) / len(
                    node.proteome_ids
                )  # type: ignore
                node_cluster_type = ""
                node_cluster_type = (
                    "complete_presence"
                    if node_proteome_coverage == 1.0
                    else "partial_absence"
                )
                # type: ignore
                node.synapomorphic_cluster_counts[node_cluster_type] += 1

                node.synapomorphic_cluster_strings.append(  # type: ignore
                    (
                        cluster.cluster_id,
                        node.name,
                        node_cluster_type,
                        "{0:.3}".format(node_proteome_coverage),
                        ";".join(child_node_proteome_coverage_strings),
                        ",".join(sorted(intersection)),
                    )
                )

    def __analyse_tree_ete(self, cluster: Cluster) -> None:
        if not self.aloCollection.tree_ete:
            return

        for node in self.aloCollection.tree_ete.traverse("levelorder"):  # type: ignore
            intersection = cluster.proteome_ids.intersection(
                node.proteome_ids  # type: ignore
            )  # type: ignore
            difference = cluster.proteome_ids.difference(
                node.proteome_ids  # type: ignore
            )  # type: ignore

            if len(intersection) == 0:
                # Nothing to see here ...
                node.counts["absent"] += 1  # type: ignore

            elif cluster.singleton is True:
                # This is a singleton
                node.counts["singleton"] += 1  # type: ignore
                node.apomorphic_cluster_counts["singletons"] += 1  # type: ignore

            elif len(difference) > 0:
                # This is a 'shared' cluster
                node.counts["shared"] += 1  # type: ignore

            elif len(difference) == 0:
                # This is a node 'specific' cluster
                self.__analyse_ete_for_specific_cluster(
                    cluster=cluster,
                    intersection=intersection,
                    node=node,
                )

    def __process_level(
        self,
        cluster: Cluster,
        attribute: str,
        level: str,
        protein_ids_by_level: Dict[str, List[str]],
        protein_length_stats_by_level: Dict[str, Dict[str, int | float]],
        explicit_protein_count_by_proteome_id_by_level: Dict[str, Dict[str, int]],
    ) -> None:
        ALO = self.aloCollection.ALO_by_level_by_attribute[attribute][level]
        if ALO is None:
            return

        protein_ids_by_proteome_id = {}
        protein_count_by_proteome_id = {}
        protein_ids_by_level[level] = []

        for proteome_id in ALO.proteomes_list:
            protein_ids = list(cluster.protein_ids_by_proteome_id.get(proteome_id, []))
            protein_ids_by_level[level].extend(protein_ids)
            protein_count_by_proteome_id[proteome_id] = len(protein_ids)
            if protein_count_by_proteome_id[proteome_id] != 0:
                protein_ids_by_proteome_id[proteome_id] = protein_ids

        if protein_ids_by_proteome_id:
            cluster.implicit_protein_ids_by_proteome_id_by_level_by_attribute[
                attribute
            ][level] = protein_ids_by_proteome_id

        explicit_protein_count_by_proteome_id_by_level[level] = (
            protein_count_by_proteome_id
        )

        protein_length_stats_by_level[level] = (
            self.proteinCollection.get_protein_length_stats(protein_ids_by_level[level])
        )

        cluster.protein_counts_of_proteomes_by_level_by_attribute[attribute][level] = (
            list(protein_count_by_proteome_id.values())
        )

    def __update_ALO_data(
        self,
        cluster: Cluster,
        attribute: str,
        protein_ids_by_level: Dict[str, List[str]],
        protein_length_stats_by_level: Dict[str, Dict[str, int | float]],
        explicit_protein_count_by_proteome_id_by_level: Dict[str, Dict[str, int]],
    ) -> None:
        for level in self.aloCollection.ALO_by_level_by_attribute[attribute]:
            ALO = self.aloCollection.ALO_by_level_by_attribute[attribute][level]
            if ALO is None:
                continue

            cluster.proteome_coverage_by_level_by_attribute[attribute][level] = (
                len(
                    cluster.implicit_protein_ids_by_proteome_id_by_level_by_attribute[
                        attribute
                    ].get(level, [])
                )
                / ALO.proteome_count
            )

            ALO_cluster_status = (
                "present"
                if level
                in cluster.implicit_protein_ids_by_proteome_id_by_level_by_attribute[
                    attribute
                ]
                else "absent"
            )

            ALO_cluster_cardinality = None
            mwu_pvalue = None
            mwu_log2_mean = None
            mean_ALO_count = None
            mean_non_ALO_count = None

            if (
                ALO_cluster_status == "present"
                and cluster.cluster_type_by_attribute[attribute] != "singleton"
            ):
                ALO_proteome_counts_in_cluster = list(
                    explicit_protein_count_by_proteome_id_by_level[level].values()
                )
                ALO_cluster_cardinality = get_ALO_cluster_cardinality(
                    ALO_proteome_counts_in_cluster=ALO_proteome_counts_in_cluster,
                    fuzzy_count=self.inputData.fuzzy_count,
                    fuzzy_fraction=self.inputData.fuzzy_fraction,
                    fuzzy_range=self.inputData.fuzzy_range,
                )

                if cluster.cluster_type_by_attribute[attribute] == "shared":
                    non_ALO_proteome_counts_in_cluster = [
                        count
                        for non_ALO_level in explicit_protein_count_by_proteome_id_by_level
                        if non_ALO_level != level
                        for count in explicit_protein_count_by_proteome_id_by_level[
                            non_ALO_level
                        ].values()
                    ]
                    mwu_pvalue, mwu_log2_mean, mean_ALO_count, mean_non_ALO_count = (
                        statistic(
                            count_1=ALO_proteome_counts_in_cluster,
                            count_2=non_ALO_proteome_counts_in_cluster,
                            test=self.inputData.test,
                            min_proteomes=self.inputData.min_proteomes,
                        )
                    )

            ALO.add_cluster(
                cluster=cluster,
                attribute_cluster_type=cluster.cluster_type_by_attribute[attribute],
                ALO_cluster_status=ALO_cluster_status,
                ALO_protein_length_stats=protein_length_stats_by_level[level],
                ALO_protein_ids_in_cluster=protein_ids_by_level[level],
                ALO_cluster_cardinality=ALO_cluster_cardinality,
                mwu_pvalue=mwu_pvalue,
                mwu_log2_mean=mwu_log2_mean,
                mean_ALO_count=mean_ALO_count,
                mean_non_ALO_count=mean_non_ALO_count,
            )

    def __process_single_attribute(self, cluster: Cluster, attribute: str) -> None:
        protein_ids_by_level: Dict[str, List[str]] = {}
        protein_length_stats_by_level: Dict[str, Dict[str, int | float]] = {}
        explicit_protein_count_by_proteome_id_by_level: Dict[str, Dict[str, int]] = {}

        cluster.protein_counts_of_proteomes_by_level_by_attribute[attribute] = {}
        cluster.proteome_coverage_by_level_by_attribute[attribute] = {}
        cluster.implicit_protein_ids_by_proteome_id_by_level_by_attribute[attribute] = (
            {}
        )

        for level in self.aloCollection.ALO_by_level_by_attribute[attribute]:
            self.__process_level(
                cluster,
                attribute,
                level,
                protein_ids_by_level,
                protein_length_stats_by_level,
                explicit_protein_count_by_proteome_id_by_level,
            )

        cluster.cluster_type_by_attribute[attribute] = get_attribute_cluster_type(
            cluster.singleton,
            cluster.implicit_protein_ids_by_proteome_id_by_level_by_attribute[
                attribute
            ],
        )

        self.__update_ALO_data(
            cluster,
            attribute,
            protein_ids_by_level,
            protein_length_stats_by_level,
            explicit_protein_count_by_proteome_id_by_level,
        )

    def __process_attributes(self, cluster: Cluster) -> None:
        for attribute in self.aloCollection.attributes:
            self.__process_single_attribute(cluster, attribute)

    def __finalize_cluster_analysis(self, cluster: Cluster) -> None:
        cluster.protein_median = median(
            [
                count
                for count in cluster.protein_counts_of_proteomes_by_level_by_attribute[
                    "all"
                ]["all"]
                if count != 0
            ]
        )

    def __analyse_cluster(self, cluster: Cluster) -> None:
        if self.aloCollection.tree_ete:
            self.__analyse_tree_ete(cluster=cluster)

        self.__process_attributes(cluster)
        self.__finalize_cluster_analysis(cluster)

    # write output
    # 0. __get_header_line
    def __get_header_line(self, filetype: str, attribute: str) -> str:
        if filetype == "attribute_metrics":
            attribute_metrics_header = [
                "#attribute",
                "taxon_set",
                "cluster_total_count",
                "protein_total_count",
                "protein_total_span",
                "singleton_cluster_count",
                "singleton_protein_count",
                "singleton_protein_span",
                "specific_cluster_count",
                "specific_protein_count",
                "specific_protein_span",
                "shared_cluster_count",
                "shared_protein_count",
                "shared_protein_span",
                "specific_cluster_true_1to1_count",
                "specific_cluster_fuzzy_count",
                "shared_cluster_true_1to1_count",
                "shared_cluster_fuzzy_count",
                "absent_cluster_total_count",
                "absent_cluster_singleton_count",
                "absent_cluster_specific_count",
                "absent_cluster_shared_count",
                "TAXON_count",
                "TAXON_taxa",
            ]
            return "\t".join(attribute_metrics_header)
        elif filetype == "cafe":
            cafe_header = ["#ID"]
            cafe_header.extend(
                iter(sorted(self.aloCollection.ALO_by_level_by_attribute["TAXON"]))
            )
            return "\t".join(cafe_header)
        elif filetype == "cluster_1to1s_ALO":
            cluster_1to1s_ALO_header = [
                "#cluster_id",
                "cluster_type",
                "1to1_type",
                "proteome_count",
                "percentage_at_target_count",
            ]
            return "\t".join(cluster_1to1s_ALO_header)
        elif filetype == "cluster_metrics":
            cluster_metrics_header = [
                "#cluster_id",
                "cluster_protein_count",
                "protein_median_count",
                "TAXON_count",
                "attribute",
                "attribute_cluster_type",
                "protein_span_mean",
                "protein_span_sd",
            ]
            cluster_metrics_header += [
                f"{level}_count"
                for level in sorted(
                    self.aloCollection.ALO_by_level_by_attribute[attribute]
                )
            ]
            if attribute != "TAXON":
                cluster_metrics_header += [
                    f"{level}_median"
                    for level in sorted(
                        self.aloCollection.ALO_by_level_by_attribute[attribute]
                    )
                ]
                cluster_metrics_header += [
                    f"{level}_cov"
                    for level in sorted(
                        self.aloCollection.ALO_by_level_by_attribute[attribute]
                    )
                ]
            return "\t".join(cluster_metrics_header)
        elif filetype == "cluster_metrics_ALO":
            cluster_metrics_ALO_header = [
                "#cluster_id",
                "cluster_status",
                "cluster_type",
                "cluster_protein_count",
                "cluster_proteome_count",
                "TAXON_protein_count",
                "TAXON_mean_count",
                "non_taxon_mean_count",
                "representation",
                "log2_mean(TAXON/others)",
                "pvalue(TAXON vs. others)",
                "TAXON_coverage",
                "TAXON_count",
                "non_TAXON_count",
                "TAXON_taxa",
                "non_TAXON_taxa",
            ]
            # for domain_source in clusterCollection.domain_sources:
            #    cluster_metrics_ALO_header.append(domain_source)
            return "\t".join(cluster_metrics_ALO_header)
        elif filetype == "cluster_metrics_domains":
            cluster_metrics_domains_header = [
                "#cluster_id",
                "cluster_protein_count",
                "TAXON_count",
                "protein_span_mean",
                "protein_span_sd",
                "fraction_secreted",
            ]
            for domain_source in self.clusterCollection.domain_sources:
                cluster_metrics_domains_header.extend(
                    (domain_source, f"{domain_source}_entropy")
                )
            return "\t".join(cluster_metrics_domains_header)
        elif filetype == "cluster_metrics_domains_detailed":
            cluster_metrics_domains_detailed_header = [
                "#cluster_id",
                "domain_source",
                "domain_id",
                "domain_description",
                "protein_count",
                "protein_count_with_domain",
                "TAXA_with_domain_fraction",
                "TAXA_with_domain",
                "TAXA_without_domain",
            ]
            return "\t".join(cluster_metrics_domains_detailed_header)
        elif filetype == "pairwise_representation_test":
            pairwise_representation_test_header = [
                "#cluster_id",
                "TAXON_1",
                "TAXON_1_mean",
                "TAXON_2",
                "TAXON_2_mean",
                "log2_mean(TAXON_1/TAXON_2)",
                "mwu_pvalue(TAXON_1 vs. TAXON_2)",
            ]
            # pairwise_representation_test_header.append("go_terms")
            # for domain_source in clusterCollection.domain_sources:
            #    pairwise_representation_test_header.append(domain_source)
            return "\t".join(pairwise_representation_test_header)
        else:
            error_msg = f"[ERROR] {filetype} is not a valid header 'filetype'"
            raise ValueError(error_msg)

    # 1. plot_cluster_sizes
    def __plot_cluster_sizes(self) -> None:
        cluster_protein_count = [
            cluster.protein_count for cluster in self.clusterCollection.cluster_list
        ]
        cluster_protein_counter = Counter(cluster_protein_count)
        count_plot_f = os.path.join(
            self.dirs["main"],
            f"cluster_size_distribution.{
                self.inputData.plot_format}",
        )
        f, ax = plt.subplots(figsize=self.inputData.plotsize)
        ax.set_facecolor("white")
        x_values = []
        y_values = []
        for value, count in list(cluster_protein_counter.items()):
            x_values.append(value)
            y_values.append(count)
        x_array = np.array(x_values)  # type: ignore
        y_array = np.array(y_values)
        ax.scatter(x_array, y_array, marker="o", alpha=0.8, s=100)
        ax.set_xlabel("Cluster size", fontsize=self.inputData.fontsize)
        ax.set_ylabel("Count", fontsize=self.inputData.fontsize)
        ax.set_yscale("log")
        ax.set_xscale("log")
        plt.margins(0.8)
        plt.gca().set_ylim(bottom=0.8)
        plt.gca().set_xlim(left=0.8)
        ax.xaxis.set_major_formatter(FormatStrFormatter("%.0f"))
        ax.yaxis.set_major_formatter(FormatStrFormatter("%.0f"))
        f.tight_layout()

        ax.grid(True, linewidth=1, which="major", color="lightgrey")
        ax.grid(True, linewidth=0.5, which="minor", color="lightgrey")
        logger.info(f"[STATUS] - Plotting {count_plot_f}")
        f.savefig(count_plot_f, format=self.inputData.plot_format)
        plt.close()

    # 2. write_cluster_counts_by_taxon
    def __write_cluster_counts_by_taxon(self) -> None:
        cafe_f = os.path.join(self.dirs["main"], "cluster_counts_by_taxon.txt")
        for attribute in self.aloCollection.attributes:
            levels = sorted(
                list(self.aloCollection.ALO_by_level_by_attribute[attribute])
            )
            cafe_output = [self.__get_header_line("cafe", "TAXON")]
            for cluster in self.clusterCollection.cluster_list:
                if attribute == "TAXON":
                    cafe_line = f"{cluster.cluster_id}"
                    # cafe_line.append("None")
                    for _level in levels:
                        total_proteins = sum(
                            cluster.protein_counts_of_proteomes_by_level_by_attribute[
                                attribute
                            ][_level]
                        )
                        cafe_line += f"\t{total_proteins}"
                    cafe_output.append(cafe_line)
            if len(cafe_output) > 1:
                with open(cafe_f, "w") as cafe_fh:
                    logger.info(f"[STATUS] - Writing {cafe_f}")
                    cafe_fh.write("\n".join(cafe_output) + "\n")
                cafe_output = []

    # 3. write_cluster_metrics_domains
    def __write_cluster_metrics_domains(self) -> None:
        cluster_metrics_domains_f = os.path.join(
            self.dirs["main"], "cluster_metrics_domains.txt"
        )
        header = self.__get_header_line("cluster_metrics_domains", "TAXON").split("\t")
        cluster_metrics_domains_output = ["\t".join(header)]

        if self.clusterCollection.functional_annotation_parsed:
            for cluster in self.clusterCollection.cluster_list:
                line_parts = {
                    "#cluster_id": cluster.cluster_id,
                    "cluster_protein_count": str(cluster.protein_count),
                    "TAXON_count": str(cluster.proteome_count),
                    "protein_span_mean": "N/A",
                    "protein_span_sd": "N/A",
                    "fraction_secreted": "N/A",
                }

                if (
                    self.clusterCollection.fastas_parsed
                    and cluster.protein_length_stats
                ):
                    line_parts["protein_span_mean"] = str(
                        cluster.protein_length_stats["mean"]
                    )
                    line_parts["protein_span_sd"] = str(
                        cluster.protein_length_stats["sd"]
                    )

                if "SignalP_EUK" in self.clusterCollection.domain_sources:
                    line_parts["fraction_secreted"] = "{0:.2f}".format(
                        cluster.secreted_cluster_coverage
                    )

                for domain_source in self.clusterCollection.domain_sources:
                    if domain_source in cluster.domain_counter_by_domain_source:
                        sorted_counts = sorted(
                            [
                                f"{domain_id}:{count}"
                                for domain_id, count in cluster.domain_counter_by_domain_source[
                                    domain_source
                                ].most_common()
                            ],
                            key=lambda x: (x.split(":")[-1], x.split(":")[-2]),
                        )
                        line_parts[domain_source] = ";".join(sorted_counts)
                        line_parts[f"{domain_source}_entropy"] = "{0:.3f}".format(
                            cluster.domain_entropy_by_domain_source[domain_source]
                        )
                    else:
                        line_parts[domain_source] = "N/A"
                        line_parts[f"{domain_source}_entropy"] = "N/A"

                # Ensure we're following the correct order from the header
                ordered_line = [line_parts.get(col, "N/A") for col in header]
                cluster_metrics_domains_output.append("\t".join(ordered_line))

        if len(cluster_metrics_domains_output) > 1:
            with open(cluster_metrics_domains_f, "w") as cluster_metrics_domains_fh:
                logger.info(f"[STATUS] - Writing {cluster_metrics_domains_f}")
                cluster_metrics_domains_fh.write(
                    "\n".join(cluster_metrics_domains_output) + "\n"
                )

    # 4. write_cluster_metrics_domains_detailed
    def __count_proteins_with_domain(
        self, cluster: Cluster, domain_source: str, domain_id: str
    ) -> Tuple[Dict[str, int], Dict[str, int]]:
        with_domain = defaultdict(int)
        without_domain = defaultdict(int)

        for proteome_id, protein_ids in cluster.protein_ids_by_proteome_id.items():
            for protein_id in protein_ids:
                protein = self.proteinCollection.proteins_by_protein_id[protein_id]
                if (
                    domain_source in protein.domain_counter_by_domain_source
                    and domain_id
                    in protein.domain_counter_by_domain_source[domain_source]
                ):
                    with_domain[proteome_id] += 1
                else:
                    without_domain[proteome_id] += 1

        return with_domain, without_domain

    def __format_proteome_counts(
        self, count_dict: Dict[str, int], cluster: Cluster
    ) -> str:
        return (
            ",".join(
                f"{proteome_id}:{count}/{len(cluster.protein_ids_by_proteome_id[proteome_id])}"
                for proteome_id, count in sorted(count_dict.items())
            )
            or "N/A"
        )

    def __get_domain_description(self, domain_source: str, domain_id: str) -> str:
        if domain_source == "SignalP_EUK":
            return domain_id
        return self.proteinCollection.domain_desc_by_id_by_source.get(
            domain_source, {}
        ).get(domain_id, "N/A")

    def __process_cluster_domains(
        self, cluster: Cluster, output_by_domain_source: Dict[str, List[str]]
    ) -> None:
        for (
            domain_source,
            domain_counter,
        ) in cluster.domain_counter_by_domain_source.items():
            for domain_id, count in domain_counter.most_common():
                with_domain, without_domain = self.__count_proteins_with_domain(
                    cluster, domain_source, domain_id
                )
                proteome_count_with_domain = sum(
                    count > 0 for count in with_domain.values()
                )

                with_domain_str = self.__format_proteome_counts(with_domain, cluster)
                without_domain_str = self.__format_proteome_counts(
                    without_domain, cluster
                )

                domain_description = self.__get_domain_description(
                    domain_source, domain_id
                )

                output_line = (
                    f"{cluster.cluster_id}\t{domain_source}\t{domain_id}\t"
                    f"{domain_description}\t{cluster.protein_count}\t"
                    f"{sum(with_domain.values())}\t"
                    f"{proteome_count_with_domain / cluster.proteome_count:.3f}\t"
                    f"{with_domain_str}\t{without_domain_str}"
                )

                output_by_domain_source[domain_source].append(output_line)

    def __write_domain_outputs(
        self,
        output_by_domain_source: Dict[str, List[str]],
        output_files: Dict[str, str],
    ) -> None:
        for domain_source, output_lines in output_by_domain_source.items():
            if len(output_lines) > 1:
                output_file = output_files[domain_source]
                logger.info(f"[STATUS] - Writing {output_file}")
                with open(output_file, "w") as fh:
                    fh.write("\n".join(output_lines) + "\n")

    def __write_cluster_metrics_domains_detailed(self) -> None:
        output_by_domain_source: Dict[str, List[str]] = {
            source: [
                self.__get_header_line("cluster_metrics_domains_detailed", "TAXON")
            ]
            for source in self.clusterCollection.domain_sources
        }

        output_files: Dict[str, str] = {
            source: os.path.join(
                self.dirs["main"], f"cluster_domain_annotation.{source}.txt"
            )
            for source in self.clusterCollection.domain_sources
        }

        if self.clusterCollection.functional_annotation_parsed:
            for cluster in self.clusterCollection.cluster_list:
                self.__process_cluster_domains(cluster, output_by_domain_source)

        self.__write_domain_outputs(output_by_domain_source, output_files)

    # 5. write attribute metrics
    def __get_attribute_metrics(self, ALO: AttributeLevel) -> str:
        attribute_metrics = [
            ALO.attribute,
            ALO.level,
            ALO.get_cluster_count_by_cluster_status_by_cluster_type("present", "total"),
        ]
        attribute_metrics.append(ALO.get_protein_count_by_cluster_type("total"))
        attribute_metrics.append(ALO.get_protein_span_by_cluster_type("total"))
        attribute_metrics.append(
            ALO.get_cluster_count_by_cluster_status_by_cluster_type(
                "present", "singleton"
            )
        )
        attribute_metrics.append(ALO.get_protein_count_by_cluster_type("singleton"))
        attribute_metrics.append(ALO.get_protein_span_by_cluster_type("singleton"))
        attribute_metrics.append(
            ALO.get_cluster_count_by_cluster_status_by_cluster_type(
                "present", "specific"
            )
        )
        attribute_metrics.append(ALO.get_protein_count_by_cluster_type("specific"))
        attribute_metrics.append(ALO.get_protein_span_by_cluster_type("specific"))
        attribute_metrics.append(
            ALO.get_cluster_count_by_cluster_status_by_cluster_type("present", "shared")
        )
        attribute_metrics.append(ALO.get_protein_count_by_cluster_type("shared"))
        attribute_metrics.append(ALO.get_protein_span_by_cluster_type("shared"))
        attribute_metrics.append(
            ALO.get_cluster_count_by_cluster_cardinality_by_cluster_type(
                "specific", "true"
            )
        )
        attribute_metrics.append(
            ALO.get_cluster_count_by_cluster_cardinality_by_cluster_type(
                "specific", "fuzzy"
            )
        )
        attribute_metrics.append(
            ALO.get_cluster_count_by_cluster_cardinality_by_cluster_type(
                "shared", "true"
            )
        )
        attribute_metrics.append(
            ALO.get_cluster_count_by_cluster_cardinality_by_cluster_type(
                "shared", "fuzzy"
            )
        )
        attribute_metrics.append(
            ALO.get_cluster_count_by_cluster_status_by_cluster_type("absent", "total")
        )
        attribute_metrics.append(
            ALO.get_cluster_count_by_cluster_status_by_cluster_type(
                "absent", "singleton"
            )
        )
        attribute_metrics.append(
            ALO.get_cluster_count_by_cluster_status_by_cluster_type(
                "absent", "specific"
            )
        )
        attribute_metrics.extend(
            (
                ALO.get_cluster_count_by_cluster_status_by_cluster_type(
                    "absent", "shared"
                ),
                ALO.proteome_count,
            )
        )
        attribute_metrics.append(ALO.get_proteomes())
        return "\t".join([str(field) for field in attribute_metrics])

    def __write_attribute_metrics(self) -> None:
        for attribute in self.aloCollection.attributes:
            attribute_metrics_f = os.path.join(
                self.dirs[attribute], f"{attribute}.attribute_metrics.txt"
            )
            attribute_metrics_output = [
                self.__get_header_line("attribute_metrics", attribute)
            ]
            levels = sorted(
                list(self.aloCollection.ALO_by_level_by_attribute[attribute])
            )
            for level in levels:
                if ALO := self.aloCollection.ALO_by_level_by_attribute[attribute][
                    level
                ]:
                    attribute_metrics_output.append(self.__get_attribute_metrics(ALO))

            if len(attribute_metrics_output) > 1:
                with open(attribute_metrics_f, "w") as attribute_metrics_fh:
                    logger.info(f"[STATUS] - Writing {attribute_metrics_f}")
                    attribute_metrics_fh.write(
                        "\n".join(attribute_metrics_output) + "\n"
                    )

    # 6. write cluster summary
    def __write_cluster_summary(self) -> None:
        for attribute in self.aloCollection.attributes:
            cluster_metrics_f = os.path.join(
                self.dirs[attribute], f"{attribute}.cluster_summary.txt"
            )

            levels = sorted(
                list(self.aloCollection.ALO_by_level_by_attribute[attribute])
            )
            cluster_metrics_output = [
                self.__get_header_line("cluster_metrics", attribute)
            ]
            for cluster in self.clusterCollection.cluster_list:
                cluster_metrics_line = f"{cluster.cluster_id}"
                cluster_metrics_line += f"\t{cluster.protein_count}"
                cluster_metrics_line += f"\t{cluster.protein_median}"
                cluster_metrics_line += f"\t{cluster.proteome_count}"
                cluster_metrics_line += f"\t{attribute}"
                cluster_metrics_line += f"\t{
                    cluster.cluster_type_by_attribute[attribute]}"
                if (
                    self.clusterCollection.fastas_parsed
                    and cluster.protein_length_stats
                ):
                    cluster_metrics_line += f"\t{
                        cluster.protein_length_stats["mean"]}"
                    cluster_metrics_line += f"\t{
                        cluster.protein_length_stats["sd"]}"
                else:
                    cluster_metrics_line += "\tN/A"
                    cluster_metrics_line += "\tN/A"
                for _level in levels:
                    cluster_metrics_line += f"\t{
                        sum(
                            cluster.protein_counts_of_proteomes_by_level_by_attribute[attribute][_level])}"
                if not attribute == "TAXON":
                    for _level in levels:
                        cluster_metrics_line += f"\t{median(
                            cluster.protein_counts_of_proteomes_by_level_by_attribute[attribute][_level])}"
                    for _level in levels:
                        cluster_metrics_line += "\t{0:.2f}".format(
                            cluster.proteome_coverage_by_level_by_attribute[attribute][
                                _level
                            ]
                        )

                cluster_metrics_output.append(cluster_metrics_line)

            if len(cluster_metrics_output) > 1:
                with open(cluster_metrics_f, "w") as cluster_metrics_fh:
                    logger.info(f"[STATUS] - Writing {cluster_metrics_f}")
                    cluster_metrics_fh.write("\n".join(cluster_metrics_output) + "\n")
                cluster_metrics_output = []

    # 7. Write cluster ALO metrics
    def __get_enrichment_data(self, ALO: AttributeLevel, cluster: Cluster) -> List[str]:
        if (
            ALO
            and ALO.cluster_type_by_cluster_id[cluster.cluster_id] == "shared"
            and ALO.cluster_mwu_log2_mean_by_cluster_id[cluster.cluster_id]
        ):
            log2_mean = ALO.cluster_mwu_log2_mean_by_cluster_id[cluster.cluster_id]
            enrichment = (
                "enriched"
                if log2_mean > 0
                else "depleted" if log2_mean < 0 else "equal"
            )
            return [
                enrichment,
                f"{log2_mean}",
                f"{ALO.cluster_mwu_pvalue_by_cluster_id[cluster.cluster_id]}",
            ]
        return ["N/A", "N/A", "N/A"]

    def __get_proteome_data(self, ALO: AttributeLevel, cluster: Cluster) -> List[str]:
        ALO_proteomes_present = cluster.proteome_ids.intersection(
            ALO.proteomes if ALO else set()
        )
        non_ALO_proteomes_present = cluster.proteome_ids.difference(
            ALO.proteomes if ALO else set()
        )
        return [
            f"{len(ALO_proteomes_present)}",
            f"{len(non_ALO_proteomes_present)}",
            (
                f"{','.join(sorted(list(ALO_proteomes_present)))}"
                if ALO_proteomes_present
                else "N/A"
            ),
            (
                f"{','.join(sorted(list(non_ALO_proteomes_present)))}"
                if non_ALO_proteomes_present
                else "N/A"
            ),
        ]

    def __write_cluster_metrics_ALO(self) -> None:
        for attribute in self.aloCollection.attributes:
            levels = sorted(
                list(self.aloCollection.ALO_by_level_by_attribute[attribute])
            )

            for level in levels:
                ALO = self.aloCollection.ALO_by_level_by_attribute[attribute][level]
                cluster_metrics_ALO_f = os.path.join(
                    self.dirs[attribute], f"{attribute}.{level}.cluster_metrics.txt"
                )
                cluster_metrics_ALO_output = [
                    self.__get_header_line("cluster_metrics_ALO", attribute)
                ]
                if ALO is None:
                    continue
                cluster_metrics_ALO_output.extend(
                    [
                        "\t".join(
                            [
                                f"{cluster.cluster_id}",
                                (
                                    f"{ALO.cluster_status_by_cluster_id[cluster.cluster_id]}"
                                    if ALO
                                    else "N/A"
                                ),
                                (
                                    f"{ALO.cluster_type_by_cluster_id[cluster.cluster_id]}"
                                    if ALO
                                    else "N/A"
                                ),
                                f"{cluster.protein_count}",
                                f"{cluster.proteome_count}",
                                f"{sum(cluster.protein_counts_of_proteomes_by_level_by_attribute[attribute][level])}",
                                (
                                    f"{ALO.cluster_mean_ALO_count_by_cluster_id[cluster.cluster_id]}"
                                    if ALO
                                    and ALO.cluster_mean_ALO_count_by_cluster_id[
                                        cluster.cluster_id
                                    ]
                                    else "N/A"
                                ),
                                (
                                    f"{ALO.cluster_mean_non_ALO_count_by_cluster_id[cluster.cluster_id]}"
                                    if ALO
                                    and ALO.cluster_mean_non_ALO_count_by_cluster_id[
                                        cluster.cluster_id
                                    ]
                                    else "N/A"
                                ),
                                *self.__get_enrichment_data(ALO, cluster),
                                "{0:.2f}".format(
                                    cluster.proteome_coverage_by_level_by_attribute[
                                        attribute
                                    ][level]
                                ),
                                *self.__get_proteome_data(ALO, cluster),
                            ]
                        )
                        for cluster in self.clusterCollection.cluster_list
                    ]
                )

                if len(cluster_metrics_ALO_output) > 1:
                    with open(cluster_metrics_ALO_f, "w") as cluster_metrics_ALO_fh:
                        logger.info(f"[STATUS] - Writing {cluster_metrics_ALO_f}")
                        cluster_metrics_ALO_fh.write(
                            "\n".join(cluster_metrics_ALO_output) + "\n"
                        )

    # 8. write cluster 1to1 ALO
    def __write_cluster_1to1_ALO(self) -> None:
        for attribute in self.aloCollection.attributes:
            levels = sorted(
                list(self.aloCollection.ALO_by_level_by_attribute[attribute])
            )
            for level in levels:
                cluster_1to1_ALO_f = os.path.join(
                    self.dirs[attribute], f"{attribute}.{level}.cluster_1to1s.txt"
                )
                cluster_1to1_ALO_output = [
                    self.__get_header_line("cluster_1to1s_ALO", attribute)
                ]

                ALO = self.aloCollection.ALO_by_level_by_attribute[attribute][level]

                if attribute != "TAXON" and ALO:
                    for (
                        cluster_type
                    ) in ALO.clusters_by_cluster_cardinality_by_cluster_type:
                        for (
                            cluster_cardinality
                        ) in ALO.clusters_by_cluster_cardinality_by_cluster_type[
                            cluster_type
                        ]:
                            for (
                                cluster_id
                            ) in ALO.clusters_by_cluster_cardinality_by_cluster_type[
                                cluster_type
                            ][
                                cluster_cardinality
                            ]:
                                cluster_1to1_ALO_line = f"{cluster_id}"
                                cluster_1to1_ALO_line += f"\t{cluster_type}"
                                cluster_1to1_ALO_line += f"\t{cluster_cardinality}"
                                cluster_1to1_ALO_line += f"\t{self.clusterCollection.cluster_list_by_cluster_id[
                                    cluster_id
                                ].proteome_count}"
                                cluster_1to1_ALO_line += "\t{0:.2f}".format(
                                    len(
                                        [
                                            protein_count
                                            for proteome_id, protein_count in list(
                                                self.clusterCollection.cluster_list_by_cluster_id[
                                                    cluster_id
                                                ].protein_count_by_proteome_id.items()
                                            )
                                            if protein_count
                                            == self.inputData.fuzzy_count
                                        ]
                                    )
                                    / self.clusterCollection.cluster_list_by_cluster_id[
                                        cluster_id
                                    ].proteome_count
                                )
                                cluster_1to1_ALO_output.append(cluster_1to1_ALO_line)

                if len(cluster_1to1_ALO_output) > 1:
                    with open(cluster_1to1_ALO_f, "w") as cluster_1to1_ALO_fh:
                        logger.info(f"[STATUS] - Writing {cluster_1to1_ALO_f}")
                        cluster_1to1_ALO_fh.write(
                            "\n".join(cluster_1to1_ALO_output) + "\n"
                        )
                    cluster_1to1_ALO_output = []

    # 9. write_pairwise_representation
    def __process_background_representation(
        self,
        attribute: str,
        level: str,
        ALO: AttributeLevel,
        cluster: Cluster,
        background_representation_test_by_pair_by_attribute,
    ) -> None:
        background_pair = (level, "background")
        if attribute not in background_representation_test_by_pair_by_attribute:
            background_representation_test_by_pair_by_attribute[attribute] = {}
        if (
            background_pair
            not in background_representation_test_by_pair_by_attribute[attribute]
        ):
            background_representation_test_by_pair_by_attribute[attribute][
                background_pair
            ] = []

        background_representation_test = [
            cluster.cluster_id,
            level,
            "background",
            ALO.cluster_mean_ALO_count_by_cluster_id[cluster.cluster_id],
            ALO.cluster_mean_non_ALO_count_by_cluster_id[cluster.cluster_id],
            ALO.cluster_mwu_log2_mean_by_cluster_id[cluster.cluster_id],
            ALO.cluster_mwu_pvalue_by_cluster_id[cluster.cluster_id],
        ]
        background_representation_test_by_pair_by_attribute[attribute][
            background_pair
        ].append(background_representation_test)

    def __get_pairwise_representation_test(
        self,
        cluster: Cluster,
        attribute: str,
        level: str,
        levels_seen: Set[str],
        levels: List[str],
    ) -> Generator[Any, Any, Any]:
        for other_level in set(levels).difference(levels_seen):
            if other_level != level:
                other_ALO = self.aloCollection.ALO_by_level_by_attribute[attribute][
                    other_level
                ]
                if (
                    other_ALO
                    and len(cluster.proteome_ids.intersection(other_ALO.proteomes)) >= 2
                ):
                    protein_counts_level = [
                        count
                        for count in cluster.protein_counts_of_proteomes_by_level_by_attribute[
                            attribute
                        ][
                            level
                        ]
                        if count > 0
                    ]
                    protein_counts_other_level = [
                        count
                        for count in cluster.protein_counts_of_proteomes_by_level_by_attribute[
                            attribute
                        ][
                            other_level
                        ]
                        if count > 0
                    ]
                    if protein_counts_level and protein_counts_other_level:
                        (
                            mwu_pvalue,
                            mwu_log2_mean,
                            mean_ALO_count,
                            mean_non_ALO_count,
                        ) = statistic(
                            protein_counts_level,
                            protein_counts_other_level,
                            self.inputData.test,
                            self.inputData.min_proteomes,
                        )
                        yield [
                            cluster.cluster_id,
                            level,
                            other_level,
                            mean_ALO_count,
                            mean_non_ALO_count,
                            mwu_log2_mean,
                            mwu_pvalue,
                        ]
                        # pvalue = None
                        # try:
                        #     pvalue = scipy.stats.mannwhitneyu(protein_counts_level, protein_counts_other_level, alternative="two-sided")[1]
                        # except:
                        #     pvalue = 1.0
                        # mean_level = mean(protein_counts_level)
                        # mean_other_level = mean(protein_counts_other_level)
                        # log2fc_mean = log((mean_level/mean_other_level), 2)
                        # yield [cluster.cluster_id, level, other_level, mean_level,
                        # mean_other_level, log2fc_mean, pvalue]

    def __process_pairwise_representation(
        self,
        attribute: str,
        level: str,
        levels_seen: Set[str],
        levels: List[str],
        cluster: Cluster,
        pairwise_representation_test_by_pair_by_attribute,
        pairwise_representation_test_output: List[str],
    ) -> None:
        for result in self.__get_pairwise_representation_test(
            cluster, attribute, level, levels_seen, levels
        ):
            if attribute not in pairwise_representation_test_by_pair_by_attribute:
                pairwise_representation_test_by_pair_by_attribute[attribute] = {}
            pair = (result[1], result[2])
            if pair not in pairwise_representation_test_by_pair_by_attribute[attribute]:
                pairwise_representation_test_by_pair_by_attribute[attribute][pair] = []
            pairwise_representation_test_by_pair_by_attribute[attribute][pair].append(
                result
            )

            pairwise_representation_test_output.append(
                f"{result[0]}\t{result[1]}\t{result[3]}\t{result[2]}\t{result[4]}\t{result[5]}\t{result[6]}"
            )

    # 9.5 __plot_count_comparisons_volcano
    def __prepare_data(self, pair_data: List[str]) -> Tuple[List[float], List[float]]:
        pair_data_count = len(pair_data)
        p_values: List[float] = []
        log2fc_values: List[float] = []

        for data in pair_data:
            log2fc_values.append(float(data[5]))
            pvalue = data[6] if data[6] != 0.0 else 0.01 / (pair_data_count + 1)
            p_values.append(float(pvalue))

        return p_values, log2fc_values

    def __get_output_filename(self, attribute: str, pair_list: List[str]) -> str:
        return os.path.join(
            self.dirs[attribute],
            f"{attribute}.pairwise_representation_test.{
                "_".join(pair_list)}.{
                self.inputData.plot_format}",
        )

    def __create_volcano_plot(
        self,
        p_values: List[float],
        log2fc_values: List[float],
        pair_list: List[str],
        output_file: str,
    ) -> None:
        plt.figure(1, figsize=self.inputData.plotsize)

        axScatter, axHistx = self.__setup_plot_axes()

        p_array = np.array(p_values)
        log2fc_array = np.array(log2fc_values)

        log2fc_percentile = self.__plot_data(axScatter, axHistx, log2fc_array, p_array)
        self.__set_plot_properties(
            axScatter, axHistx, log2fc_array, p_array, pair_list, log2fc_percentile
        )

        logger.info(f"[STATUS] - Plotting {output_file}")
        plt.savefig(output_file, format=self.inputData.plot_format)
        plt.close()

    def __setup_plot_axes(self) -> Tuple[Any, Any]:
        left, width = 0.1, 0.65
        bottom, height = 0.1, 0.65
        bottom_h = left + width + 0.02
        rect_scatter = (left, bottom, width, height)
        rect_histx = (left, bottom_h, width, 0.2)

        axScatter = plt.axes(rect_scatter)
        axScatter.set_facecolor("white")
        axHistx = plt.axes(rect_histx)
        axHistx.set_facecolor("white")
        axHistx.xaxis.set_major_formatter(NullFormatter())
        axHistx.yaxis.set_major_formatter(NullFormatter())

        return axScatter, axHistx

    def __plot_data(
        self,
        axScatter: Any,
        axHistx: Any,
        log2fc_array: np.ndarray,
        p_array: np.ndarray,
    ) -> Any:
        # Plot histogram
        binwidth = 0.05
        xymax = np.max(np.fabs(log2fc_array))
        lim = (int(xymax / binwidth) + 1) * binwidth
        bins = np.arange(-lim, lim + binwidth, binwidth)
        axHistx.hist(
            log2fc_array, bins=bins, histtype="stepfilled", color="grey", align="mid"
        )

        # Plot scatter
        axScatter.scatter(
            log2fc_array, p_array, alpha=0.8, edgecolors="none", s=25, c="grey"
        )

        # Add reference lines
        ooFive, ooOne = 0.05, 0.01
        log2fc_percentile = np.percentile(log2fc_array, 95)

        axScatter.axhline(y=ooFive, linewidth=2, color="orange", linestyle="--")
        axScatter.axhline(y=ooOne, linewidth=2, color="red", linestyle="--")
        axScatter.axvline(x=1.0, linewidth=2, color="purple", linestyle="--")
        axScatter.axvline(
            x=log2fc_percentile, linewidth=2, color="blue", linestyle="--"
        )
        axScatter.axvline(x=-1.0, linewidth=2, color="purple", linestyle="--")
        axScatter.axvline(
            x=-log2fc_percentile, linewidth=2, color="blue", linestyle="--"
        )

        return log2fc_percentile

    def __set_plot_properties(
        self,
        axScatter: Any,
        axHistx: Any,
        log2fc_array: np.ndarray,
        p_array: np.ndarray,
        pair_list: List[str],
        log2fc_percentile: Any,
    ) -> None:
        # Set axis limits and properties
        x_min = -max(abs(np.min(log2fc_array)), abs(np.max(log2fc_array)))
        x_max = -x_min
        axScatter.set_xlim(x_min - 1, x_max + 1)
        axScatter.grid(True, linewidth=1, which="major", color="lightgrey")
        axScatter.grid(True, linewidth=0.5, which="minor", color="lightgrey")
        axScatter.set_ylim(1.1, np.min(p_array) * 0.1)
        axScatter.set_xlabel(
            f"log2(mean({pair_list[0]})/mean({pair_list[1]}))",
            fontsize=self.inputData.fontsize,
        )
        axScatter.set_ylabel("p-value", fontsize=self.inputData.fontsize)
        axScatter.set_yscale("log")
        axHistx.set_xlim(axScatter.get_xlim())

        # Add legend
        legend_elements = [
            Line2D([0], [0], color="orange", linestyle="--", label="p-value = 0.05"),
            Line2D([0], [0], color="red", linestyle="--", label="p-value = 0.01"),
            Line2D([0], [0], color="purple", linestyle="--", label="|log2FC| = 1"),
            Line2D(
                [0],
                [0],
                color="blue",
                linestyle="--",
                label=f"|log2FC-95%ile| = {log2fc_percentile:.2f}",
            ),
        ]
        legend = axScatter.legend(
            handles=legend_elements, fontsize=self.inputData.fontsize, frameon=True
        )
        legend.get_frame().set_facecolor("white")

    def __plot_count_comparisons_volcano(
        self,
        pairwise_representation_test_by_pair_by_attribute,
    ) -> None:
        for attribute in pairwise_representation_test_by_pair_by_attribute:
            for pair in pairwise_representation_test_by_pair_by_attribute[attribute]:
                pair_list = list(pair)
                pair_data = pairwise_representation_test_by_pair_by_attribute[
                    attribute
                ][pair]

                p_values, log2fc_values = self.__prepare_data(pair_data)

                if p_values:
                    output_file = self.__get_output_filename(attribute, pair_list)
                    self.__create_volcano_plot(
                        p_values, log2fc_values, pair_list, output_file
                    )

    def __write_pairwise_representation(self) -> None:
        for attribute in self.aloCollection.attributes:
            pairwise_representation_test_by_pair_by_attribute: Dict[
                str, Dict[str, str]
            ] = {}
            background_representation_test_by_pair_by_attribute = {}
            pairwise_representation_test_output = [
                self.__get_header_line("pairwise_representation_test", attribute)
            ]
            pairwise_representation_test_f = os.path.join(
                self.dirs[attribute], f"{attribute}.pairwise_representation_test.txt"
            )
            levels = sorted(
                list(self.aloCollection.ALO_by_level_by_attribute[attribute])
            )
            levels_seen: Set[str] = set()

            for level in levels:
                ALO = self.aloCollection.ALO_by_level_by_attribute[attribute][level]

                for cluster in self.clusterCollection.cluster_list:
                    if (
                        ALO
                        and ALO.cluster_type_by_cluster_id[cluster.cluster_id]
                        == "shared"
                        and ALO.cluster_mwu_log2_mean_by_cluster_id[cluster.cluster_id]
                    ):
                        self.__process_background_representation(
                            attribute,
                            level,
                            ALO,
                            cluster,
                            background_representation_test_by_pair_by_attribute,
                        )

                    ALO_proteomes_present = cluster.proteome_ids.intersection(
                        ALO.proteomes if ALO else set("")
                    )

                    if (
                        len(levels) > 1
                        and len(ALO_proteomes_present) >= self.inputData.min_proteomes
                    ):
                        self.__process_pairwise_representation(
                            attribute,
                            level,
                            levels_seen,
                            levels,
                            cluster,
                            pairwise_representation_test_by_pair_by_attribute,
                            pairwise_representation_test_output,
                        )

                levels_seen.add(level)

                if background_representation_test_by_pair_by_attribute:
                    self.__plot_count_comparisons_volcano(
                        background_representation_test_by_pair_by_attribute
                    )

            if len(pairwise_representation_test_output) > 1:
                with open(
                    pairwise_representation_test_f, "w"
                ) as pairwise_representation_test_fh:
                    logger.info(f"[STATUS] - Writing {pairwise_representation_test_f}")
                    pairwise_representation_test_fh.write(
                        "\n".join(pairwise_representation_test_output) + "\n"
                    )

            if pairwise_representation_test_by_pair_by_attribute:
                self.__plot_count_comparisons_volcano(
                    pairwise_representation_test_by_pair_by_attribute
                )
