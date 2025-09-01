import logging
import warnings
from typing import Dict, List, Set

import matplotlib as mat
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from matplotlib.ticker import NullFormatter
from scipy import stats

logger = logging.getLogger("kinfin_logger")


warnings.filterwarnings("ignore", message="Precision loss occurred*")

mat.use("agg")

plt.style.use("ggplot")

mat.rc("ytick", labelsize=20)
mat.rc("xtick", labelsize=20)
mat.rcParams.update({"font.size": 22})


def generate_background_plots(
    results_df: pl.DataFrame, attribute: str, output_dir: str, plot_format: str = "png"
):
    if results_df.height == 0:
        return

    for taxon_key, data in results_df.group_by("TAXON_1"):
        taxon_1 = taxon_key[0]
        log2fc_values = (
            data.get_column("log2_mean(TAXON_1/background)")
            .drop_nulls()
            .to_numpy()
            .copy()
        )
        p_values = (
            data.get_column("mwu_pvalue(TAXON_1 vs. background)")
            .drop_nulls()
            .to_numpy()
            .copy()
        )

        if len(p_values) == 0:
            continue

        p_values[p_values == 0] = 0.01 / (len(p_values) + 1)

        plt.figure(1, figsize=(24, 12))
        left, width = 0.1, 0.65
        bottom, height = 0.1, 0.65
        rect_scatter = [left, bottom, width, height]
        axScatter = plt.axes(rect_scatter)
        axScatter.set_facecolor("white")

        ooFive = 0.05
        ooOne = 0.01
        log2fc_percentile = np.percentile(np.abs(log2fc_values), 95)

        axScatter.axhline(y=ooFive, linewidth=2, color="orange", linestyle="--")
        ooFive_artist = plt.Line2D((0, 1), (0, 0), color="orange", linestyle="--")
        axScatter.axhline(y=ooOne, linewidth=2, color="red", linestyle="--")
        ooOne_artist = plt.Line2D((0, 1), (0, 0), color="red", linestyle="--")

        axScatter.axvline(x=1.0, linewidth=2, color="purple", linestyle="--")
        axScatter.axvline(x=-1.0, linewidth=2, color="purple", linestyle="--")
        v1_artist = plt.Line2D((0, 1), (0, 0), color="purple", linestyle="--")
        axScatter.axvline(
            x=log2fc_percentile, linewidth=2, color="blue", linestyle="--"
        )
        axScatter.axvline(
            x=-log2fc_percentile, linewidth=2, color="blue", linestyle="--"
        )
        nine_five_percentile_artist = plt.Line2D(
            (0, 1), (0, 0), color="blue", linestyle="--"
        )

        axScatter.scatter(
            log2fc_values, p_values, alpha=0.8, edgecolors="none", s=25, c="grey"
        )

        legend = axScatter.legend(
            [ooFive_artist, ooOne_artist, v1_artist, nine_five_percentile_artist],
            [
                f"p-value = {ooFive}",
                f"p-value = {ooOne}",
                "|log2FC| = 1",
                f"|log2FC-95%ile| = {log2fc_percentile:.2f}",
            ],
            fontsize=18,
            frameon=True,
        )
        legend.get_frame().set_facecolor("white")

        x_max_abs = np.max(np.abs(log2fc_values)) if len(log2fc_values) > 0 else 1.0
        axScatter.set_xlim(-x_max_abs - 1, x_max_abs + 1)
        axScatter.set_ylim(1.1, np.min(p_values) * 0.1)
        axScatter.set_yscale("log")
        axScatter.set_xlabel(f"log2(mean({taxon_1})/mean(background))", fontsize=18)
        axScatter.set_ylabel("p-value", fontsize=18)

        axScatter.grid(True, linewidth=1, which="major", color="lightgrey")
        axScatter.grid(True, linewidth=0.5, which="minor", color="lightgrey")

        plot_file = f"{output_dir}/{attribute}/{attribute}.pairwise_representation_test.{taxon_1}_background.{plot_format}"
        print(f"[✓] Plotting: {plot_file}")
        plt.savefig(plot_file, format=plot_format)
        plt.close()


def generate_background_representation_test(
    cluster_df: pl.DataFrame,
    attribute: str,
    label_to_taxons: Dict[str, Dict[str, Set[str]]],
    output_dir: str,
    min_proteomes: int = 2,
):
    """
    Performs a statistical test for each label against all other labels (background).
    """
    all_results = []
    taxon_map_df = pl.DataFrame(
        [
            (taxon, label)
            for label, taxons in label_to_taxons[attribute].items()
            for taxon in taxons
        ],
        schema=["taxons", "label"],
        orient="row",
    )

    protein_counts_per_taxon = (
        cluster_df.explode("taxons")
        .group_by("cluster_id", "taxons")
        .agg(pl.count().alias("count"))
        .join(taxon_map_df, on="taxons")
    )

    for current_label in label_to_taxons[attribute]:
        label_counts = (
            protein_counts_per_taxon.group_by("cluster_id")
            .agg(
                pl.col("count")
                .filter(pl.col("label") == current_label)
                .alias("inside_counts"),
                pl.col("count")
                .filter(pl.col("label") != current_label)
                .alias("outside_counts"),
            )
            .filter(
                (pl.col("inside_counts").list.len() >= min_proteomes)
                & (pl.col("outside_counts").list.len() >= min_proteomes)
            )
        )

        if label_counts.height == 0:
            continue

        stats_df = label_counts.with_columns(
            TAXON_1_mean=pl.col("inside_counts").list.mean(),
            background_mean=pl.col("outside_counts").list.mean(),
        ).with_columns(
            log2_mean=pl.when(
                (pl.col("TAXON_1_mean") > 0) & (pl.col("background_mean") > 0)
            )
            .then((pl.col("TAXON_1_mean") / pl.col("background_mean")).log(base=2))
            .when(pl.col("TAXON_1_mean") == pl.col("background_mean"))
            .then(0.0)
            .otherwise(None)
        )

        p_values = []
        for row in stats_df.iter_rows(named=True):
            c1, c2 = row["inside_counts"], row["outside_counts"]
            if len(set(c1)) == 1 and len(set(c2)) == 1 and c1[0] == c2[0]:
                p_values.append(1.0)
                continue
            try:
                pvalue = stats.mannwhitneyu(c1, c2, alternative="two-sided").pvalue
                p_values.append(pvalue)
            except ValueError:
                p_values.append(1.0)

        final_df = stats_df.with_columns(pl.Series("p_value", p_values)).select(
            pl.col("cluster_id").alias("#cluster_id"),
            pl.lit(current_label).alias("TAXON_1"),
            pl.col("TAXON_1_mean"),
            pl.lit("background").alias("TAXON_2"),
            pl.col("background_mean").alias("TAXON_2_mean"),
            pl.col("log2_mean").alias("log2_mean(TAXON_1/background)"),
            pl.col("p_value").alias("mwu_pvalue(TAXON_1 vs. background)"),
        )
        all_results.append(final_df)

    if not all_results:
        return

    full_results_df = pl.concat(all_results)
    generate_background_plots(full_results_df, attribute, output_dir)


def generate_pairwise_plots(
    pairwise_df: pl.DataFrame,
    attribute: str,
    output_dir: str,
    plot_format: str = "png",
):

    if pairwise_df.height == 0:
        return

    pair_groups = pairwise_df.group_by("TAXON_1", "TAXON_2")

    for (taxon_1, taxon_2), data in pair_groups:
        log2fc_values = (
            data.get_column("log2_mean(TAXON_1/TAXON_2)").drop_nulls().to_numpy().copy()
        )
        p_values = (
            data.get_column("mwu_pvalue(TAXON_1 vs. TAXON_2)")
            .drop_nulls()
            .to_numpy()
            .copy()
        )

        if len(p_values) == 0:
            continue

        p_values[p_values == 0] = 0.01 / (len(p_values) + 1)

        plt.figure(1, figsize=(24, 12))

        left, width = 0.1, 0.65
        bottom, height = 0.1, 0.65
        bottom_h = left + width + 0.02
        rect_scatter = [left, bottom, width, height]
        rect_histx = [left, bottom_h, width, 0.2]

        axScatter = plt.axes(rect_scatter)
        axScatter.set_facecolor("white")
        axHistx = plt.axes(rect_histx)
        axHistx.set_facecolor("white")

        nullfmt = NullFormatter()
        axHistx.xaxis.set_major_formatter(nullfmt)
        axHistx.yaxis.set_major_formatter(nullfmt)

        binwidth = 0.05
        xymax = np.max([np.max(np.fabs(log2fc_values)), np.max(np.fabs(p_values))])
        lim = (int(xymax / binwidth) + 1) * binwidth
        bins = np.arange(-lim, lim + binwidth, binwidth)
        axHistx.hist(
            log2fc_values, bins=bins, histtype="stepfilled", color="grey", align="mid"
        )

        ooFive = 0.05
        ooOne = 0.01
        log2fc_percentile = np.percentile(np.abs(log2fc_values), 95)

        axScatter.axhline(y=ooFive, linewidth=2, color="orange", linestyle="--")
        ooFive_artist = plt.Line2D((0, 1), (0, 0), color="orange", linestyle="--")
        axScatter.axhline(y=ooOne, linewidth=2, color="red", linestyle="--")
        ooOne_artist = plt.Line2D((0, 1), (0, 0), color="red", linestyle="--")

        axScatter.axvline(x=1.0, linewidth=2, color="purple", linestyle="--")
        axScatter.axvline(x=-1.0, linewidth=2, color="purple", linestyle="--")
        v1_artist = plt.Line2D((0, 1), (0, 0), color="purple", linestyle="--")
        axScatter.axvline(
            x=log2fc_percentile, linewidth=2, color="blue", linestyle="--"
        )
        axScatter.axvline(
            x=-log2fc_percentile, linewidth=2, color="blue", linestyle="--"
        )
        nine_five_percentile_artist = plt.Line2D(
            (0, 1), (0, 0), color="blue", linestyle="--"
        )

        axScatter.scatter(
            log2fc_values, p_values, alpha=0.8, edgecolors="none", s=25, c="grey"
        )

        legend = axScatter.legend(
            [ooFive_artist, ooOne_artist, v1_artist, nine_five_percentile_artist],
            [
                f"p-value = {ooFive}",
                f"p-value = {ooOne}",
                "|log2FC| = 1",
                f"|log2FC-95%ile| = {log2fc_percentile:.2f}",
            ],
            fontsize=18,
            frameon=True,
        )
        legend.get_frame().set_facecolor("white")

        x_max_abs = np.max(np.abs(log2fc_values))
        axScatter.set_xlim(-x_max_abs - 1, x_max_abs + 1)
        axScatter.set_ylim(1.1, np.min(p_values) * 0.1)
        axScatter.set_yscale("log")
        axScatter.set_xlabel(f"log2(mean({taxon_1})/mean({taxon_2}))", fontsize=18)
        axScatter.set_ylabel("p-value", fontsize=18)

        axScatter.grid(True, linewidth=1, which="major", color="lightgrey")
        axScatter.grid(True, linewidth=0.5, which="minor", color="lightgrey")

        axHistx.set_xlim(axScatter.get_xlim())

        plot_file = f"{output_dir}/{attribute}/{attribute}.pairwise_representation_test.{taxon_1}_{taxon_2}.{plot_format}"
        print(f"[✓] Plotting: {plot_file}")
        plt.savefig(plot_file, format=plot_format)
        plt.close()


def generate_pairwise_representation_test(
    cluster_df: pl.DataFrame,
    attribute: str,
    label_to_taxons: Dict[str, Dict[str, Set[str]]],
    output_dir: str,
    min_proteomes: int = 2,
):
    taxon_to_label_mapping = [
        (taxon, label)
        for label, taxons in label_to_taxons[attribute].items()
        for taxon in taxons
    ]
    taxon_map_df = pl.DataFrame(
        taxon_to_label_mapping, schema=["taxons", "label"], orient="row"
    )

    protein_counts_per_taxon = (
        cluster_df.explode("taxons")
        .group_by("cluster_id", "taxons")
        .agg(pl.count().alias("count"))
    )

    counts_by_label = (
        protein_counts_per_taxon.join(taxon_map_df, on="taxons")
        .group_by("cluster_id", "label")
        .agg(pl.col("count").alias("counts_list"))
    )

    counts_by_label_filtered = counts_by_label.filter(
        pl.col("counts_list").list.len() >= min_proteomes
    )

    pairwise_df = counts_by_label_filtered.join(
        counts_by_label_filtered, on="cluster_id", suffix="_2"
    ).filter(pl.col("label") < pl.col("label_2"))

    if pairwise_df.height == 0:
        print(
            f"[!] No valid pairs for pairwise test in attribute '{attribute}'. Skipping."
        )
        return

    stats_df = pairwise_df.with_columns(
        TAXON_1_mean=pl.col("counts_list").list.mean(),
        TAXON_2_mean=pl.col("counts_list_2").list.mean(),
    ).with_columns(
        pl.when((pl.col("TAXON_1_mean") > 0) & (pl.col("TAXON_2_mean") > 0))
        .then((pl.col("TAXON_1_mean") / pl.col("TAXON_2_mean")).log(base=2))
        .when(pl.col("TAXON_1_mean") == pl.col("TAXON_2_mean"))
        .then(0.0)
        .otherwise(None)
        .alias("log2_mean(TAXON_1/TAXON_2)"),
    )

    p_values = []
    counts1_series = stats_df["counts_list"]
    counts2_series = stats_df["counts_list_2"]

    for i in range(stats_df.height):
        c1 = counts1_series[i]
        c2 = counts2_series[i]

        if len(c1.unique()) == 1 and len(c2.unique()) == 1 and c1[0] == c2[0]:
            p_values.append(1.0)
            continue
        try:
            pvalue = stats.mannwhitneyu(c1, c2, alternative="two-sided").pvalue
            p_values.append(pvalue)
        except ValueError:
            p_values.append(1.0)

    final_df = stats_df.with_columns(
        pl.Series("mwu_pvalue(TAXON_1 vs. TAXON_2)", p_values)
    ).drop("counts_list", "counts_list_2")

    output_df = final_df.select(
        pl.col("cluster_id").alias("#cluster_id"),
        pl.col("label").alias("TAXON_1"),
        pl.col("TAXON_1_mean"),
        pl.col("label_2").alias("TAXON_2"),
        pl.col("TAXON_2_mean"),
        pl.col("log2_mean(TAXON_1/TAXON_2)"),
        pl.col("mwu_pvalue(TAXON_1 vs. TAXON_2)"),
    ).sort("#cluster_id", "TAXON_1", "TAXON_2")

    file_path = f"{output_dir}/{attribute}/{attribute}.pairwise_representation_test.txt"
    print(f"[✓] Writing: {file_path}")
    output_df.write_csv(file_path, separator="\t")

    generate_pairwise_plots(
        pairwise_df=output_df,
        attribute=attribute,
        output_dir=output_dir,
    )


def add_status_and_TAXON_protein_count_columns(
    df: pl.DataFrame,
    label_to_taxons: Dict[str, Dict[str, set]],
) -> pl.DataFrame:
    expressions = []

    for attribute, label_dict in label_to_taxons.items():
        for label_group, valid_taxa in label_dict.items():
            in_valid = pl.col("taxons").list.eval(pl.element().is_in(valid_taxa))

            status_col_name = f"{attribute}_{label_group}_cluster_status"
            status_expr = (
                pl.when(in_valid.list.any())
                .then(pl.lit("present"))
                .otherwise(pl.lit("absent"))
                .alias(status_col_name)
            )

            count_col_name = f"{attribute}_{label_group}_TAXON_protein_count"
            count_expr = in_valid.list.sum().alias(count_col_name)

            expressions.extend([status_expr, count_expr])

    return df.with_columns(expressions)


def add_coverage_column(
    df: pl.DataFrame,
    attribute: str,
    level: str,
    label_to_taxons: dict,
) -> pl.DataFrame:
    expected_taxons = set(label_to_taxons[attribute][level])
    expected_taxons_len = len(expected_taxons)

    if expected_taxons_len == 0:
        return df.with_columns(pl.lit("N/A").alias("TAXON_coverage"))

    numerator = (
        pl.col("taxons").list.unique().list.set_intersection(expected_taxons).list.len()
    )

    coverage_numeric = numerator / expected_taxons_len

    coverage_str_padded = (
        (coverage_numeric * 100).round(0).cast(pl.Int64).cast(pl.Utf8).str.zfill(3)
    )

    coverage_expr = (
        coverage_str_padded.str.slice(0, length=coverage_str_padded.str.len_chars() - 2)
        + "."
        + coverage_str_padded.str.slice(-2)
    )

    return df.with_columns(coverage_expr.alias("TAXON_coverage"))


def add_taxon_split_columns(
    df: pl.DataFrame,
    attribute: str,
    level: str,
    label_to_taxons: dict,
    min_proteomes: int = 2,
    test: str = "mannwhitneyu",
) -> pl.DataFrame:
    """
    Calculates taxon statistics using a fully vectorized Polars-native approach.
    """
    valid_taxa = set(label_to_taxons[attribute][level])

    if "cluster_id" not in df.columns:
        df = df.with_row_count(name="cluster_id")

    partitioned_counts = (
        df.select(["cluster_id", "taxons"])
        .explode("taxons")
        .group_by("cluster_id", "taxons")
        .agg(pl.count().alias("count"))
        .with_columns(pl.col("taxons").is_in(valid_taxa).alias("is_inside"))
    )

    grouped_lists = partitioned_counts.group_by("cluster_id", maintain_order=True).agg(
        pl.col("count").filter(pl.col("is_inside")).alias("inside_counts"),
        pl.col("count").filter(~pl.col("is_inside")).alias("outside_counts"),
    )

    stats_results = (
        grouped_lists.with_columns(
            inside_len=pl.col("inside_counts").list.len(),
            outside_len=pl.col("outside_counts").list.len(),
        )
        .with_columns(
            is_valid=pl.when(
                (pl.col("inside_len") >= min_proteomes)
                & (pl.col("outside_len") >= min_proteomes)
            )
            .then(True)
            .otherwise(False),
            mean_inside=pl.col("inside_counts").list.mean(),
            mean_outside=pl.col("outside_counts").list.mean(),
        )
        .with_columns(
            log2_ratio=pl.when(pl.col("mean_outside") > 0)
            .then((pl.col("mean_inside") / pl.col("mean_outside")).log(base=2))
            .otherwise(None),
        )
        .with_columns(
            representation=pl.when(pl.col("log2_ratio") > 0)
            .then(pl.lit("enriched"))
            .otherwise(pl.lit("depleted")),
        )
    )

    def compute_p_value(struct: dict) -> str | None:
        """A small, focused function just for the p-value."""
        inside = struct.get("inside_counts")
        outside = struct.get("outside_counts")
        try:
            if not struct.get("is_valid"):
                return None
            p = stats.mannwhitneyu(inside, outside, alternative="two-sided").pvalue
            return f"{p:.16f}".rstrip("0").rstrip(".")
        except Exception:
            return None

    final_stats = stats_results.with_columns(
        p_value=pl.struct(["inside_counts", "outside_counts", "is_valid"]).map_elements(
            compute_p_value, return_dtype=pl.Utf8
        )
    ).select(
        pl.col("cluster_id"),
        pl.when(pl.col("is_valid"))
        .then(pl.col("mean_inside"))
        .otherwise(pl.lit("N/A"))
        .alias("TAXON_mean_count"),
        pl.when(pl.col("is_valid"))
        .then(pl.col("mean_outside"))
        .otherwise(pl.lit("N/A"))
        .alias("non_taxon_mean_count"),
        pl.when(pl.col("is_valid"))
        .then(pl.col("log2_ratio").cast(pl.Utf8))
        .otherwise(pl.lit("N/A"))
        .alias("log2_mean(TAXON/others)"),
        pl.col("p_value").fill_null(pl.lit("N/A")).alias("pvalue(TAXON vs. others)"),
        pl.when(pl.col("is_valid"))
        .then(pl.col("representation"))
        .otherwise(pl.lit("N/A"))
        .alias("representation"),
    )

    return df.join(final_stats, on="cluster_id", how="left")


def add_all_taxon_info_columns(
    df: pl.DataFrame,
    label_to_taxons: Dict[str, Dict[str, set]],
) -> pl.DataFrame:
    expressions = []

    for attribute, label_dict in label_to_taxons.items():
        for label_group, valid_taxa in label_dict.items():
            prefix = f"{attribute}_{label_group}"
            taxons_sorted_unique = pl.col("taxons").list.unique().list.sort()

            taxon_mask = taxons_sorted_unique.list.eval(pl.element().is_in(valid_taxa))
            non_taxon_mask = taxons_sorted_unique.list.eval(
                ~pl.element().is_in(valid_taxa)
            )

            taxon_list_str = taxons_sorted_unique.list.eval(
                pl.element().filter(pl.element().is_in(valid_taxa))
            )
            non_taxon_list_str = taxons_sorted_unique.list.eval(
                pl.element().filter(~pl.element().is_in(valid_taxa))
            )

            expressions.extend(
                [
                    taxon_mask.list.sum().alias(f"{prefix}_TAXON_count"),
                    non_taxon_mask.list.sum().alias(f"{prefix}_non_TAXON_count"),
                    pl.when(taxon_list_str.list.len() == 0)
                    .then(pl.lit("N/A"))
                    .otherwise(taxon_list_str.list.join(","))
                    .alias(f"{prefix}_TAXON_taxa"),
                    pl.when(non_taxon_list_str.list.len() == 0)
                    .then(pl.lit("N/A"))
                    .otherwise(non_taxon_list_str.list.join(","))
                    .alias(f"{prefix}_non_TAXON_taxa"),
                ]
            )

    return df.with_columns(expressions)


def get_cluster_metrics(
    attribute: str,
    label_group: str,
    label_to_taxons: Dict[str, Dict[str, set]],
    base_metrics_df: pl.DataFrame,
) -> pl.DataFrame:
    cols_for_loop = [
        "cluster_id",
        "cluster_protein_count",
        "cluster_proteome_count",
        "taxons",
        f"{attribute}_cluster_type",
        f"{attribute}_{label_group}_TAXON_protein_count",
        f"{attribute}_{label_group}_cluster_status",
        f"{attribute}_{label_group}_TAXON_count",
        f"{attribute}_{label_group}_non_TAXON_count",
        f"{attribute}_{label_group}_TAXON_taxa",
        f"{attribute}_{label_group}_non_TAXON_taxa",
    ]

    metrics_df = (
        base_metrics_df.select(cols_for_loop)
        .pipe(
            add_coverage_column,
            attribute=attribute,
            level=label_group,
            label_to_taxons=label_to_taxons,
        )
        .pipe(
            add_taxon_split_columns,
            attribute=attribute,
            level=label_group,
            label_to_taxons=label_to_taxons,
        )
    )

    final_order = [
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

    rename_map = {
        "cluster_id": "#cluster_id",
        f"{attribute}_cluster_type": "cluster_type",
        f"{attribute}_{label_group}_cluster_status": "cluster_status",
        f"{attribute}_{label_group}_TAXON_protein_count": "TAXON_protein_count",
        f"{attribute}_{label_group}_TAXON_count": "TAXON_count",
        f"{attribute}_{label_group}_non_TAXON_count": "non_TAXON_count",
        f"{attribute}_{label_group}_TAXON_taxa": "TAXON_taxa",
        f"{attribute}_{label_group}_non_TAXON_taxa": "non_TAXON_taxa",
    }

    final_df = metrics_df.rename(rename_map)
    final_df = final_df.select(final_order).sort("#cluster_id")
    return final_df


def get_all_cluster_metrics(
    attributes: List[str],
    unique_label_values: Dict[str, List[str]],
    cluster_df: pl.DataFrame,
    taxon_label_dict: Dict[str, Dict[str, str]],
    base_output_dir: str,
    min_proteomes=2,
) -> None:
    label_to_taxons: Dict[str, Dict[str, set]] = {
        attr: {
            label: {
                taxon
                for taxon, labels in taxon_label_dict.items()
                if labels.get(attr) == label
            }
            for label in unique_label_values[attr]
        }
        for attr in attributes
    }

    cluster_metrics = {}

    base_metrics_df = (
        cluster_df.pipe(
            add_status_and_TAXON_protein_count_columns,
            label_to_taxons,
        )
        .rename({"TAXON_count": "cluster_proteome_count"})
        .pipe(add_all_taxon_info_columns, label_to_taxons)
    )

    for attribute in attributes:
        cluster_metrics[attribute] = {}
        for label_group in unique_label_values[attribute]:
            metrics_df = get_cluster_metrics(
                attribute=attribute,
                label_group=label_group,
                label_to_taxons=label_to_taxons,
                base_metrics_df=base_metrics_df,
            )

            cluster_metrics[attribute][label_group] = metrics_df
            file_path = f"{base_output_dir}/{attribute}/{attribute}.{label_group}.cluster_metrics.txt"
            logger.info(f"[✓] Writing: {file_path}")
            metrics_df.write_csv(file_path, separator="\t")

        generate_pairwise_representation_test(
            cluster_df=cluster_df,
            attribute=attribute,
            label_to_taxons=label_to_taxons,
            output_dir=base_output_dir,
        )
        generate_background_representation_test(
            cluster_df=cluster_df,
            attribute=attribute,
            label_to_taxons=label_to_taxons,
            output_dir=base_output_dir,
        )

    return cluster_metrics
