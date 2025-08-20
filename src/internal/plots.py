import logging
import os
import random
import warnings
from collections import Counter, defaultdict
from typing import Tuple

import matplotlib as mat
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from matplotlib.ticker import FormatStrFormatter

logger = logging.getLogger("kinfin_logger")

warnings.filterwarnings(
    "ignore", message="No artists with labels found to put in legend.*"
)


mat.use("agg")

plt.style.use("ggplot")

mat.rc("ytick", labelsize=20)
mat.rc("xtick", labelsize=20)
mat.rcParams.update({"font.size": 22})


def plot_cluster_sizes(
    cluster_df: pl.DataFrame,
    base_output_dir: str,
    plot_format: str = "png",
    plotsize: Tuple[int, int] = (24, 12),
    fontsize: int = 18,
) -> None:
    counts = cluster_df.get_column("cluster_protein_count").to_list()
    cluster_size_counter = Counter(counts)
    x_values = np.array(list(cluster_size_counter.keys()))
    y_values = np.array(list(cluster_size_counter.values()))

    output_path = os.path.join(base_output_dir, "cluster_size_distribution.tsv")
    with open(output_path, "w") as f:
        f.write("cluster_size\tcount\n")
        for size, count in sorted(cluster_size_counter.items()):
            f.write(f"{size}\t{count}\n")
    logger.info(f"[✓] Writing: {output_path}")

    fig, ax = plt.subplots(figsize=plotsize)
    ax.set_facecolor("white")

    ax.scatter(x_values, y_values, marker="o", alpha=0.8, s=100)

    ax.set_xlabel("Cluster size", fontsize=fontsize)
    ax.set_ylabel("Count", fontsize=fontsize)
    ax.set_yscale("log")
    ax.set_xscale("log")

    plt.margins(0.8)
    plt.gca().set_ylim(bottom=0.8)
    plt.gca().set_xlim(left=0.8)

    ax.xaxis.set_major_formatter(FormatStrFormatter("%.0f"))
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.0f"))

    fig.tight_layout()

    ax.grid(True, which="major", color="lightgrey", linewidth=1)
    ax.grid(True, which="minor", color="lightgrey", linewidth=0.5)

    plot_out_path = os.path.join(
        base_output_dir, f"cluster_size_distribution.{plot_format}"
    )
    logger.info(f"[✓] Plotting: {plot_out_path}")

    fig.savefig(plot_out_path, format=plot_format)
    plt.close()


def generate_kinfin_rarefaction_plots(
    cluster_df: pl.DataFrame,
    config_df: pl.DataFrame,
    attributes: list[str],
    base_output_dir: str,
    repetitions: int = 30,
    plot_size: tuple = (24, 12),
    font_size: int = 18,
    plot_format: str = "png",
):
    os.makedirs(base_output_dir, exist_ok=True)

    non_singleton_clusters = cluster_df.filter(pl.col("TAXON_count") > 1)
    clusters_by_taxon = defaultdict(set)
    for taxon, cid in (
        non_singleton_clusters.select(["taxons", "cluster_id"])
        .explode("taxons")
        .iter_rows()
    ):
        clusters_by_taxon[taxon].add(cid)

    for attribute in attributes:
        attribute_output_path = os.path.join(base_output_dir, attribute)
        os.makedirs(attribute_output_path, exist_ok=True)

        fig, ax = plt.subplots(figsize=plot_size)
        ax.set_facecolor("white")

        color_map = plt.cm.Paired(np.linspace(0, 1, config_df[attribute].n_unique()))

        plot_data_by_level = {}
        max_samples_on_plot = 0

        # This list will store the raw data for the TSV file
        data_for_saving = [
            "level\tsample_size\tmedian_clusters\tmin_clusters\tmax_clusters"
        ]

        all_levels = config_df[attribute].unique().sort()
        for i, level in enumerate(all_levels):
            taxa_for_level = config_df.filter(pl.col(attribute) == level)[
                "TAXON"
            ].to_list()

            if len(taxa_for_level) <= 1:
                continue

            max_samples_on_plot = max(max_samples_on_plot, len(taxa_for_level))

            rarefaction_data = defaultdict(list)
            for _ in range(repetitions):
                random.shuffle(taxa_for_level)
                seen_clusters = set()
                for j, taxon in enumerate(taxa_for_level):
                    seen_clusters.update(clusters_by_taxon[taxon])
                    rarefaction_data[j + 1].append(len(seen_clusters))

            sample_sizes = sorted(rarefaction_data.keys())
            medians = [np.median(rarefaction_data[s]) for s in sample_sizes]
            mins = [np.min(rarefaction_data[s]) for s in sample_sizes]
            maxs = [np.max(rarefaction_data[s]) for s in sample_sizes]

            plot_data_by_level[level] = {
                "samples": sample_sizes,
                "medians": medians,
                "mins": mins,
                "maxs": maxs,
                "color": color_map[i],
            }

            # Populate the data for saving
            for k, sample_size in enumerate(sample_sizes):
                row = f"{level}\t{sample_size}\t{medians[k]}\t{mins[k]}\t{maxs[k]}"
                data_for_saving.append(row)

        # Plotting section
        for level, data in plot_data_by_level.items():
            ax.plot(
                data["samples"],
                data["medians"],
                color=data["color"],
                label=level,
                linewidth=2,
            )
            ax.fill_between(
                data["samples"],
                data["mins"],
                data["maxs"],
                color=data["color"],
                alpha=0.4,
            )

        ax.set_title(
            f"Rarefaction Curve by {attribute}",
            fontsize=font_size + 2,
            fontweight="bold",
        )
        ax.set_xlabel("Number of Proteomes Sampled", fontsize=font_size)
        ax.set_ylabel("Count of Non-Singleton Clusters", fontsize=font_size)
        ax.grid(True, which="both", linestyle="--", linewidth=1, color="lightgrey")
        ax.set_xlim(0, max_samples_on_plot + 1)
        legend = ax.legend(
            title=attribute.capitalize(),
            fontsize=font_size,
            loc="lower right",
            frameon=True,
        )
        legend.get_frame().set_facecolor("white")

        # Save the plot
        plot_filename = os.path.join(
            attribute_output_path, f"{attribute}.rarefaction_curve.{plot_format}"
        )
        try:
            fig.savefig(plot_filename, format=plot_format, bbox_inches="tight")
        except Exception as e:
            logger.info(f"[ERROR] Could not save plot. {e}")
        plt.close(fig)

        # *** NEW: Save the aggregated data to a TSV file ***
        data_filename = os.path.join(
            attribute_output_path, f"{attribute}.rarefaction_data.tsv"
        )
        try:
            with open(data_filename, "w") as f:
                f.write("\n".join(data_for_saving))
        except Exception as e:
            logger.info(f"[ERROR] Could not save data file. {e}")
