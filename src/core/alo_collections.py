import os
import random
from typing import Any, Dict, List, Optional, Set

import ete3
import matplotlib as mat
import matplotlib.pyplot as plt
import numpy as np
from ete3 import Tree

from core.alo import AttributeLevel
from core.config import ATTRIBUTE_RESERVED
from core.utils import logger

mat.use("agg")


plt.style.use("ggplot")
mat.rc("ytick", labelsize=20)
mat.rc("xtick", labelsize=20)
axis_font = {"size": "20"}
mat.rcParams.update({"font.size": 22})


class AloCollection:
    def __init__(
        self,
        proteomes: Set[str],
        attributes: List[str],
        proteome_id_by_species_id: Dict[str, str],
        level_by_attribute_by_proteome_id: Dict[str, Dict[str, str]],
        node_idx_by_proteome_ids: Optional[Dict[Any, Any]],
        tree_ete: Optional[Tree],
    ) -> None:
        self.proteomes = proteomes
        self.attributes_verbose = attributes
        self.attributes = [
            # list of attributes
            attribute
            for attribute in attributes
            if attribute not in ATTRIBUTE_RESERVED
        ]
        self.proteome_id_by_species_id = proteome_id_by_species_id
        self.level_by_attribute_by_proteome_id = level_by_attribute_by_proteome_id
        self.node_idx_by_proteome_ids = node_idx_by_proteome_ids
        self.tree_ete = tree_ete
        self.proteome_ids_by_level_by_attribute = (
            self.compute_proteomes_by_level_by_attribute()
        )
        self.fastas_parsed: bool = False
        self.ALO_by_level_by_attribute = self.create_ALOs()

    def compute_proteomes_by_level_by_attribute(
        self,
    ) -> Dict[str, Dict[str, Set[str]]]:
        """
        Compute proteomes grouped by levels for each attribute.

        Args:
            attributes (List[str]): A list of strings representing attributes.
            level_by_attribute_by_proteome_id (Dict[str, Dict[str, str]]): A dictionary where keys
                are proteome IDs (strings), and values are dictionaries with keys representing
                attributes (strings) and values representing levels (strings).

        Returns:
            Dict[str, Dict[str, Set[str]]]: A dictionary where keys are attributes (strings),
                and values are dictionaries. The inner dictionaries have keys representing
                levels (strings) and values representing sets of proteome IDs (strings).
        """
        proteomes_by_level_by_attribute: Dict[str, Dict[str, Set[str]]] = {
            attribute: {} for attribute in self.attributes
        }
        for proteome_id in self.level_by_attribute_by_proteome_id:
            for attribute in self.attributes:
                level = self.level_by_attribute_by_proteome_id[proteome_id][
                    attribute
                ]
                if level not in proteomes_by_level_by_attribute[attribute]:
                    proteomes_by_level_by_attribute[attribute][level] = set()
                proteomes_by_level_by_attribute[attribute][level].add(proteome_id)
        return proteomes_by_level_by_attribute

    def create_ALOs(self) -> Dict[str, Dict[str, Optional[AttributeLevel]]]:
        """
        Creates Attribute Level Objects (ALOs) for each attribute and level based on
        proteome IDs.

        Returns:
            Dict[str, Dict[str, Optional[AttributeLevel]]]:
                A dictionary where each key is an attribute name (str),
                and the corresponding value is a dictionary mapping level (str)
                to an AttributeLevel instance or None.
        """
        ALO_by_level_by_attribute: Dict[str, Dict[str, Optional[AttributeLevel]]] = {
            attribute: {} for attribute in self.attributes
        }
        for attribute in self.proteome_ids_by_level_by_attribute:
            for level in self.proteome_ids_by_level_by_attribute[attribute]:
                proteome_ids = self.proteome_ids_by_level_by_attribute[attribute][
                    level
                ]
                ALO = AttributeLevel(
                    #
                    attribute=attribute,
                    level=level,
                    proteomes=proteome_ids,
                )
                if level not in ALO_by_level_by_attribute[attribute]:
                    ALO_by_level_by_attribute[attribute][level] = None
                ALO_by_level_by_attribute[attribute][level] = ALO
        return ALO_by_level_by_attribute

    def generate_header_for_node(self, node: ete3.TreeNode, dirs: Dict[str, str]):
        """
        Generates a header image for a given node of a tree with specified statistics.

        Args:
            node (ete3.TreeNode): The TreeNode object representing the node for which the header is generated.
            dirs (Dict[str, str]): A dictionary containing directory paths, including 'tree_headers' where the header image will be saved.

        Returns:
            str: File path to the generated header image.

        Notes:
            - The method generates a header image in PNG format displaying various statistics (apomorphies and synapomorphies) for the given tree node.
            - The statistics include counts of singletons, non-singletons, complete presence synapomorphies, and partial absence synapomorphies.
            - The generated image is saved in the specified directory under 'tree_headers' with the node's name as the filename.

        Raises:
            Any exceptions that might occur during file saving or table rendering.
        """

        node_header_f = os.path.join(dirs["tree_headers"], f"{node.name}.header.png")
        data = [
            (
                "Apomorphies (size=1)",
                "{:,}".format(
                    node.apomorphic_cluster_counts["singletons"]  # type:ignore
                ),
            ),
            (
                "Apomorphies (size>1)",
                "{:,}".format(
                    node.apomorphic_cluster_counts["non_singletons"]  # type:ignore
                ),
            ),
            (
                "Synapomorphies (all)",
                "{:,}".format(
                    node.synapomorphic_cluster_counts[  # type:ignore
                        "complete_presence"
                    ]
                    + node.synapomorphic_cluster_counts[  # type:ignore
                        "partial_absence"
                    ]
                ),
            ),
            (
                "Synapomorphies (cov=100%)",
                "{:,}".format(
                    node.synapomorphic_cluster_counts[  # type:ignore
                        "complete_presence"
                    ]
                ),
            ),
            (
                "Synapomorphies (cov<100%)",
                "{:,}".format(
                    node.synapomorphic_cluster_counts[  # type: ignore
                        "partial_absence"
                    ]  # type:ignore
                ),
            ),
        ]
        col_labels = ("Type", "Count")
        fig, ax = plt.subplots(figsize=(2, 0.5))
        ax.set_facecolor("white")
        table = ax.table(
            cellText=data,
            colLabels=col_labels,
            loc="bottom",
            fontsize=24,
            colLoc="center",
            rowLoc="right",
            edges="",
        )
        table.set_fontsize(24)
        table.scale(2, 1)
        for key, cell in list(table.get_celld().items()):
            row, col = key
            cell._text.set_color("grey")
            cell.set_edgecolor("darkgrey")
            cell.visible_edges = "T" if row > 0 else "B"
            if row == len(data) - 2:
                cell.set_edgecolor("darkgrey")
                cell.visible_edges = "T"
        ax.axis("tight")
        ax.axis("off")
        logger.info(f"[STATUS]\t- Plotting {node_header_f}")
        fig.savefig(node_header_f, pad=0, bbox_inches="tight", format="png")
        plt.close()
        return node_header_f

    def generate_chart_for_node(
        self,
        node,
        dirs: Dict[str, str],
        plot_format: str,
        fontsize: int,
    ) -> Optional[str]:
        """
        Generate and save a histogram chart for a given node's synapomorphies.

        Args:
        - node: The node object containing synapomorphic cluster strings.
        - dirs: A dictionary containing directory paths, specifically 'tree_charts' for saving charts.
        - plot_format: The format in which to save the chart ('png' or 'pdf').
        - fontsize: Font size for axis labels and ticks.

        Returns:
        - Optional[str]: Path to the saved chart file if successful, None otherwise.
        """

        if proteome_coverages := [
            float(synapomorphic_cluster_string[3])
            for synapomorphic_cluster_string in node.synapomorphic_cluster_strings
        ]:
            chart_f = os.path.join(dirs["tree_charts"], f"{node.name}.barchart.png")
            f, ax = plt.subplots(figsize=(3.0, 3.0))
            ax.set_facecolor("white")
            x_values = np.array(proteome_coverages)
            ax.hist(
                x_values,
                histtype="stepfilled",
                align="mid",
                bins=np.arange(0.0, 1.0 + 0.1, 0.1),
            )
            ax.set_xlim(-0.1, 1.1)
            for tick in ax.xaxis.get_majorticklabels():
                tick.set_fontsize(fontsize - 2)
                tick.set_rotation("vertical")
            for tick in ax.yaxis.get_majorticklabels():
                tick.set_fontsize(fontsize - 2)
            ax.set_frame_on(False)
            ax.xaxis.grid(True, linewidth=1, which="major", color="lightgrey")
            ax.yaxis.grid(True, linewidth=1, which="major", color="lightgrey")
            f.suptitle("Synapomorphies", y=1.1)
            ax.set_ylabel("Count", fontsize=fontsize)
            ax.set_xlabel("Proteome coverage", fontsize=fontsize)
            logger.info(f"[STATUS]\t- Plotting {chart_f}")
            f.savefig(chart_f, bbox_inches="tight", format="png")
            if plot_format == "pdf":
                pdf_chart_f = os.path.join(
                    dirs["tree_charts"],
                    f"{
                        node.name}.barchart.pdf",
                )
                logger.info(f"[STATUS]\t- Plotting {pdf_chart_f}")
                f.savefig(pdf_chart_f, bbox_inches="tight", format="pdf")
            plt.close()
            return chart_f

    def plot_text_tree(self, dirs: Dict[str, str]) -> None:
        """
        Plot and save the textual representation of the tree.

        This method uses the `tree_ete` attribute of the class to generate and save
        both a Newick format (.nwk) and a text format (.txt) representation of the tree.

        Args:
        - dirs: A dictionary containing directory paths, specifically 'tree' for saving tree files.

        Returns:
        - None
        """
        if self.tree_ete:
            tree_nwk_f = os.path.join(dirs["tree"], "tree.nwk")
            self.tree_ete.write(format=1, outfile=tree_nwk_f)
            tree_txt_f = os.path.join(dirs["tree"], "tree.txt")
            with open(tree_txt_f, "w") as tree_txt_fh:
                tree_txt_fh.write(
                    f"{self.tree_ete.get_ascii(show_internal=True, compact=False)}\n"
                )

    def plot_tree(
        self,
        header_f_by_node_name,
        charts_f_by_node_name,
        dirs: Dict[str, str],
    ) -> None:
        """
        Plot and save a tree visualization with custom header and chart images for nodes.

        This method uses the `self.tree_ete` attribute of the class to visualize the tree
        in a hierarchical manner, with customized header and chart images for each node.

        Args:
        - header_f_by_node_name: Dictionary mapping node names to header image file paths (must be PNG).
        - charts_f_by_node_name: Dictionary mapping node names to chart image file paths (must be PNG).
        - dirs: A dictionary containing directory paths, specifically 'tree' for saving the tree PDF.

        Returns:
        - None
        """
        tree_f = os.path.join(
            dirs["tree"], "tree.pdf"
        )  # must be PDF! (otherwise it breaks)
        style = ete3.NodeStyle()
        style["vt_line_width"] = 5
        style["hz_line_width"] = 5
        style["fgcolor"] = "darkgrey"
        for node in self.tree_ete.traverse("levelorder"):  # type: ignore
            node.set_style(style)
            if header_f_by_node_name[node.name]:
                # must be PNG! (ETE can't do PDF Faces)
                node_header_face = ete3.faces.ImgFace(
                    header_f_by_node_name[node.name]
                )
                node.add_face(node_header_face, column=0, position="branch-top")
            if charts_f_by_node_name[node.name]:
                # must be PNG! (ETE can't do PDF Faces)
                node_chart_face = ete3.faces.ImgFace(
                    charts_f_by_node_name[node.name]
                )
                node.add_face(node_chart_face, column=0, position="branch-bottom")
            node_name_face = ete3.TextFace(node.name, fsize=64)
            node.img_style["size"] = 10
            node.img_style["shape"] = "sphere"
            node.img_style["fgcolor"] = "black"
            if not node.is_leaf():
                node.add_face(node_name_face, column=0, position="branch-right")
            node.add_face(node_name_face, column=0, position="aligned")
        ts = ete3.TreeStyle()
        ts.draw_guiding_lines = True
        ts.show_scale = False
        ts.show_leaf_name = False
        ts.allow_face_overlap = True
        ts.guiding_lines_color = "lightgrey"
        logger.info(f"[STATUS] - Writing tree {tree_f}... ")
        self.tree_ete.render(  # type: ignore
            tree_f, dpi=600, h=1189, units="mm", tree_style=ts
        )

    def write_tree(
        self,
        dirs: Dict[str, str],
        render_tree: bool,
        plot_format: str,
        fontsize: int,
    ) -> None:
        """
        Write tree data to files and optionally render a graphical tree representation.

        This method generates and saves various metrics and data related to the tree structure,
        including node statistics and cluster metrics. It can also render a graphical tree
        representation if specified.

        Args:
        - dirs: A dictionary containing directory paths, including 'tree' for saving tree-related files.
        - render_tree: Boolean flag indicating whether to render a graphical tree representation.
        - plot_format: Format for saving plots ('png', 'pdf', etc.).
        - fontsize: Font size used for plotting.

        Returns:
        - None
        """
        if not self.tree_ete:
            return
        logger.info("[STATUS] - Writing data for tree ... ")
        # Node stats
        node_stats_f = os.path.join(dirs["tree"], "tree.node_metrics.txt")
        node_stats_header: List[str] = [
            "#nodeID",
            "taxon_specific_apomorphies_singletons",
            "taxon_specific_apomorphies_non_singletons",
            "node_specific_synapomorphies_total",
            "node_specific_synapomorphies_complete_presence",
            "node_specific_synapomorphies_partial_absence",
            "proteome_count",
        ]
        node_stats: List[str] = ["\t".join(node_stats_header)]
        # Cluster node stats
        node_clusters_f = os.path.join(dirs["tree"], "tree.cluster_metrics.txt")
        node_clusters_header = [
            "#clusterID",
            "nodeID",
            "synapomorphy_type",
            "node_taxon_coverage",
            "children_coverage",
            "node_taxa_present",
        ]
        node_clusters = ["\t".join(node_clusters_header)]
        # header_f_by_node_name
        header_f_by_node_name = {}
        charts_f_by_node_name = {}
        for node in self.tree_ete.traverse("levelorder"):  # type: ignore
            for synapomorphic_cluster_string in node.synapomorphic_cluster_strings:  # type: ignore
                node_clusters.append(
                    "\t".join(
                        [
                            str(string)
                            for string in list(synapomorphic_cluster_string)
                        ]
                    )
                )
            node_stats_line = [
                node.name,
                node.apomorphic_cluster_counts["singletons"],  # type: ignore
                node.apomorphic_cluster_counts["non_singletons"],  # type: ignore
                (
                    # type: ignore
                    node.synapomorphic_cluster_counts["complete_presence"]  # type: ignore
                    # type: ignore
                    + node.synapomorphic_cluster_counts["partial_absence"]  # type: ignore
                ),
                # type: ignore
                node.synapomorphic_cluster_counts["complete_presence"],  # type: ignore
                node.synapomorphic_cluster_counts["partial_absence"],  # type: ignore
                len(node.proteome_ids),  # type: ignore
            ]
            node_stats.append("\t".join([str(string) for string in node_stats_line]))
            if render_tree:
                header_f_by_node_name[node.name] = self.generate_header_for_node(
                    node, dirs
                )
            charts_f_by_node_name[node.name] = self.generate_chart_for_node(
                node, dirs, plot_format, fontsize
            )
        logger.info(f"[STATUS] - Writing {node_stats_f} ... ")
        with open(node_stats_f, "w") as node_stats_fh:
            node_stats_fh.write("\n".join(node_stats) + "\n")
        logger.info(f"[STATUS] - Writing {node_clusters_f} ... ")
        with open(node_clusters_f, "w") as node_clusters_fh:
            node_clusters_fh.write("\n".join(node_clusters) + "\n")
        if render_tree:
            self.plot_tree(header_f_by_node_name, charts_f_by_node_name, dirs)
        else:
            self.plot_text_tree(dirs)

    def compute_repetition_for_rarefaction_curve(
        self,
        ALO: AttributeLevel,
        attribute: str,
        level: str,
        rarefaction_by_samplesize_by_level_by_attribute: Dict[
            str, Dict[str, Dict[int, List[int]]]
        ],
    ):
        seen_cluster_ids = set()
        random_list_of_proteome_ids = list(ALO.proteomes)
        random.shuffle(random_list_of_proteome_ids)
        for idx, proteome_id in enumerate(random_list_of_proteome_ids):
            if proteome_ALO := self.ALO_by_level_by_attribute["TAXON"][proteome_id]:
                seen_cluster_ids.update(
                    proteome_ALO.cluster_ids_by_cluster_type_by_cluster_status[
                        "present"
                    ]["specific"]
                )
                seen_cluster_ids.update(
                    proteome_ALO.cluster_ids_by_cluster_type_by_cluster_status[
                        "present"
                    ]["shared"]
                )
                sample_size = idx + 1
                if (
                    sample_size
                    not in rarefaction_by_samplesize_by_level_by_attribute[
                        attribute
                    ][level]
                ):
                    rarefaction_by_samplesize_by_level_by_attribute[attribute][
                        level
                    ][sample_size] = []
                rarefaction_by_samplesize_by_level_by_attribute[attribute][level][
                    sample_size
                ].append(len(seen_cluster_ids))

    def compute_rarefaction_data(
        self, repetitions: int
    ) -> Dict[str, Dict[str, Dict[int, List[int]]]]:
        """
        Compute rarefaction data and generate rarefaction curves for proteome clusters.

        This method computes rarefaction curves to analyze the accumulation of non-singleton
        clusters as proteome samples increase. It generates plots for each attribute based on
        the specified parameters.

        Args:
        - repetitions: Number of repetitions to shuffle proteome lists for random sampling.

        Returns:
        - Dict[str, Dict[str, Dict[int, List[int]]]]
        """
        rarefaction_by_samplesize_by_level_by_attribute: Dict[
            str, Dict[str, Dict[int, List[int]]]
        ] = {}
        logger.info("[STATUS] - Generating rarefaction data ...")
        for attribute in self.attributes:
            for level in self.proteome_ids_by_level_by_attribute[attribute]:
                proteome_ids = self.proteome_ids_by_level_by_attribute[attribute][
                    level
                ]
                if len(proteome_ids) == 1:
                    continue

                if attribute not in rarefaction_by_samplesize_by_level_by_attribute:
                    rarefaction_by_samplesize_by_level_by_attribute[attribute] = {}
                if (
                    level
                    not in rarefaction_by_samplesize_by_level_by_attribute[attribute]
                ):
                    rarefaction_by_samplesize_by_level_by_attribute[attribute][
                        level
                    ] = {}
                ALO = self.ALO_by_level_by_attribute[attribute][level]
                if ALO is None:
                    continue
                for _ in range(repetitions):
                    self.compute_repetition_for_rarefaction_curve(
                        ALO=ALO,
                        attribute=attribute,
                        level=level,
                        rarefaction_by_samplesize_by_level_by_attribute=rarefaction_by_samplesize_by_level_by_attribute,
                    )
        return rarefaction_by_samplesize_by_level_by_attribute
