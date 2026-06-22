import math

import definitions
import matplotlib as mat

# mat.use("agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

import core.utils

plt.set_loglevel("info")
COLOR_HISTOGRAM = "orange"
COLORS = ["deeppink", "dodgerblue"]
COLOR_AXES = "grey"
LEGEND_FONTSIZE = 10
AXES_TICKS_FONTSIZE = 8
AXES_LABELS_FONTSIZE = 8

# MATPLOTLIB PARAMS
mat.rcParams["text.color"] = COLOR_AXES
mat.rcParams["axes.edgecolor"] = COLOR_AXES
mat.rcParams["xtick.color"] = COLOR_AXES
mat.rcParams["ytick.color"] = COLOR_AXES
mat.rcParams["grid.color"] = COLOR_AXES
mat.rcParams["grid.alpha"] = 0.2
mat.rcParams["grid.linewidth"] = 0.5
mat.rcParams["font.family"] = "sans-serif"
mat.rcParams["xtick.labelsize"] = AXES_LABELS_FONTSIZE
mat.rcParams["ytick.labelsize"] = AXES_LABELS_FONTSIZE
mat.rcParams["figure.frameon"] = False
mat.rcParams["axes.grid"] = False

line_style = {
    "shared": "-",
    "specific": ":",
    "singleton": "--",
}

"""
[ToDo]
- export all plot parameters to config file in config/ so that they can be globally edited
"""

VOLCANO_LINEWIDTH = 2


def volcano(x, y, fn):
    # P_VALUES_MIN = 0.0001
    x_label = "log2FC"
    y_label = "p-value"
    # y = y.clip(lower=P_VALUES_MIN)
    fig, axs = plt.subplot_mosaic(
        [["top"], ["bottom"]],
        figsize=(12, 8),
        height_ratios=(1, 3),
        sharex=True,
        layout="constrained",
    )
    binwidth = 0.05
    xymax = max([x.abs().max(), y.abs().max()])
    lim = (int(xymax / binwidth) + 1) * binwidth
    bins = np.arange(-lim, lim + binwidth, binwidth)
    axs["top"].hist(
        x,
        bins=bins,
        histtype="stepfilled",
        color="dimgray",
        align="left",
    )
    axs["top"].tick_params(axis="x", which="both", labelbottom=False)
    axs["bottom"].scatter(
        x,
        y,
        alpha=0.8,
        edgecolors=None,
        s=5,
        c="dimgray",
    )
    axs["bottom"].axhline(
        y=0.05,
        linewidth=VOLCANO_LINEWIDTH,
        color="orange",
        linestyle="--",
        label=f"{y_label} = 0.05",
        alpha=0.5,
    )
    axs["bottom"].axhline(
        y=0.01,
        linewidth=VOLCANO_LINEWIDTH,
        color="red",
        linestyle="--",
        label=f"{y_label} = 0.01",
        alpha=0.5,
    )
    axs["bottom"].axvline(
        x=1.0,
        linewidth=VOLCANO_LINEWIDTH,
        color="purple",
        linestyle="--",
        label=f"|{x_label}| = 1",
        alpha=0.5,
    )
    axs["bottom"].axvline(
        x=-1.0,
        linewidth=VOLCANO_LINEWIDTH,
        color="purple",
        linestyle="--",
        alpha=0.5,
    )
    log2fc_percentile = np.percentile(x, 95)
    axs["bottom"].axvline(
        x=log2fc_percentile,
        linewidth=VOLCANO_LINEWIDTH,
        color="blue",
        linestyle="--",
        label=f"|log2FC-95%ile| = {log2fc_percentile:.3f}",
        alpha=0.5,
    )
    axs["bottom"].axvline(
        x=-log2fc_percentile,
        linewidth=VOLCANO_LINEWIDTH,
        color="blue",
        linestyle="--",
        alpha=0.5,
    )
    axs["bottom"].grid(
        True,
        linewidth=1,
        which="major",
        color="lightgrey",
    )
    axs["bottom"].grid(
        True,
        linewidth=0.5,
        which="minor",
        color="lightgrey",
    )
    axs["top"].grid(
        True,
        linewidth=1,
        which="major",
        color="lightgrey",
    )
    axs["top"].grid(
        True,
        linewidth=0.5,
        which="minor",
        color="lightgrey",
    )
    axs["bottom"].set_ylim(1.5, 10 ** (math.log(y.min(), 10) - 0.5))
    axs["bottom"].set_xlim(-x.abs().max() - 1, x.abs().max() + 1)
    axs["bottom"].set_yscale("log")
    axs["bottom"].set_ylabel(y_label)
    axs["bottom"].set_xlabel(x_label)
    axs["bottom"].legend(frameon=False, fontsize=10)
    # plt.tight_layout()
    fig.savefig(fn)
    plt.close(fig)


def lines(
    label,
    dfs,
    tags,
    x=None,
    y=None,
    m=None,
    out_prefix=None,
    max_lines=9,
    plot_fmt=definitions.PLOT_FORMAT,
):
    df_chunks, tags_chunks = [], []
    for i in range(0, len(dfs), max_lines):
        j = i + max_lines
        df_chunks.append(dfs[i:j])
        tags_chunks.append(tags[i:j])
    prop_cycle = plt.rcParams["axes.prop_cycle"]
    default_colors = prop_cycle.by_key()["color"]
    for idx_chunk, (tag_chunk, df_chunk) in enumerate(zip(tags_chunks, df_chunks)):
        lines = []
        fig = plt.figure(figsize=(6, 8), dpi=200, frameon=True)
        ax = fig.add_subplot(111)
        for idx, (tag, df) in enumerate(zip(tag_chunk, df_chunk)):
            for name in sorted(df[m].unique()):
                _df = df[df["OT"] == name]
                lines += ax.plot(
                    _df[x],
                    _df[y],
                    alpha=0.9,
                    color=(
                        # plt.cm.gnuplot2(idx / max_lines)
                        # if len(dfs) >= 20
                        # else plt.cm.tab20(idx / 20)
                        plt.cm.tab20(idx / 20) if len(dfs) > 10 else default_colors[idx]
                    ),
                    label=tag,
                    lw=1.5,
                    linestyle=line_style[name],
                )
        ax.set_ylabel(y)
        ax.set_xlabel(x)
        if x.endswith("n"):
            ax.set_xlim([-0.05, 1.05])
        if y.endswith("n"):
            ax.set_ylim([-0.05, 1.05])
        handles_1, labels_1 = plt.gca().get_legend_handles_labels()
        handles_1 = (
            [handle_1 for handle_1 in handles_1 if handle_1._linestyle == "-"]
            or [handle_1 for handle_1 in handles_1 if handle_1._linestyle == "--"]
            or [handle_1 for handle_1 in handles_1 if handle_1._linestyle == ":"]
        )
        legend_1 = ax.legend(
            handles=handles_1,
            labels=tag_chunk,
            title="Taxongroup",
            frameon=False,
            loc="upper left",
        )
        handles = [
            Line2D([0], [0], label="shared", color="grey", linestyle="-"),
            Line2D([0], [0], label="specific", color="grey", linestyle=":"),
            Line2D([0], [0], label="singleton", color="grey", linestyle="--"),
        ]
        legend_2 = ax.legend(
            title="OG type",
            handles=handles,
            frameon=False,
            loc="upper center",
        )
        ax.add_artist(legend_1)
        ax.add_artist(legend_2)
        plt.tight_layout()
        fn = (
            f"{label}.{str(idx_chunk + 1).zfill(len(str(len(df_chunks))))}.sampling.{x}_vs_{y}.{plot_fmt}"
            if len(df_chunks) > 1
            else f"{label}.sampling.{x}_vs_{y}.{plot_fmt}"
        )
        if out_prefix is None:
            out_fn = core.utils.get_dir("PLOTS") / "curve" / label / fn
        else:
            out_fn = f"{out_prefix}{fn}"
        fig.savefig(out_fn)
        plt.close(fig)


def tally_plot(
    df_EC=None,
    df_SC=None,
    fn=None,
):
    fig = plt.figure(figsize=(8, 10), dpi=200, frameon=True)
    ax = fig.subplot_mosaic([["top"], ["bottom"]])
    ax["top"].annotate(
        int(df_SC["SC"].max()),
        xy=(df_SC["SC"].max(), df_EC["count"].max()),
        xytext=(0, 0),
        textcoords="offset points",
        rotation=0,
        va="bottom",
        ha="center",
        annotation_clip=False,
    )
    ax["top"].vlines(
        df_SC["SC"].max(),
        ymin=df_EC["count"].min(),
        ymax=df_EC["count"].max(),
        colors="darkgrey",
        linestyles="dashed",
        alpha=0.5,
    )
    ax["top"].scatter(
        df_EC["EC"],
        df_EC["count"],
        c="dimgray",
        s=7.5,
        alpha=0.5,
    )
    ax["bottom"].annotate(
        int(df_SC["SC"].max()),
        xy=(df_SC["SC"].max(), df_SC["count"].max()),
        xytext=(0, 0),
        textcoords="offset points",
        rotation=0,
        va="bottom",
        ha="center",
        annotation_clip=False,
    )
    ax["bottom"].vlines(
        df_SC["SC"].max(),
        ymin=df_SC["count"].min(),
        ymax=df_SC["count"].max(),
        colors="darkgrey",
        alpha=0.5,
        linestyles="dashed",
    )
    ax["bottom"].scatter(
        df_SC["SC"],
        df_SC["count"],
        c="dimgray",
        s=7.5,
        alpha=0.5,
    )
    ax["top"].set_xscale("log", base=10)
    top_xmin = 10 ** (math.log(df_EC["EC"].min(), 10) - 0.5)
    top_xmax = 10 ** (math.log(df_EC["EC"].max(), 10) + 0.5)
    top_ymin = 10 ** (math.log(df_EC["count"].min(), 10) - 0.5)
    top_ymax = 10 ** (math.log(df_EC["count"].max(), 10) + 0.5)
    ax["top"].set_ylim(top_ymin, top_ymax)
    ax["top"].set_xlim(top_xmin, top_xmax)
    ax["top"].set_yscale("log", base=10)
    ax["top"].set_ylabel("Orthogroup Count (OC)")
    ax["top"].set_xlabel("Element Count (EC)")
    ax["top"].grid(visible=True, which="major", axis="both")
    ax["bottom"].set_xscale("log", base=10)
    ax["bottom"].set_yscale("log", base=10)
    ax["bottom"].set_ylabel("Orthogroup Count (OC)")
    ax["bottom"].set_xlabel("Sample Count (SC)")
    bottom_xmin = 10 ** (math.log(df_SC["SC"].min(), 10) - 0.5)
    bottom_xmax = 10 ** (math.log(df_SC["SC"].max(), 10) + 0.5)
    bottom_ymin = 10 ** (math.log(df_SC["count"].min(), 10) - 0.5)
    bottom_ymax = 10 ** (math.log(df_SC["count"].max(), 10) + 0.5)
    ax["bottom"].set_ylim(bottom_ymin, bottom_ymax)
    ax["bottom"].set_xlim(bottom_xmin, bottom_xmax)
    ax["bottom"].grid(visible=True, which="major", axis="both")
    fig.savefig(fn)
    plt.close(fig)


def run(args):
    pass
    # plot_3d()
    # fns = []
    # if args.d:
    #     fns += [fn for fn in glob.glob(f"{args.d}/*.curve.*")]
    # if args.f:
    #     fns += args.f
    # if fns:
    #     SC = [int(fn.split(".")[-3]) for fn in fns]
    #     indices = np.argsort(SC)
    #     tags = [f"{fn.split('.')[-4]}" for fn in fns]
    #     tags_sorted = [tags[idx] for idx in indices]


#
#     labels = [
#         f"{tag} ({SC})" if int(SC) > 1 else f"{tag}"
#         for tag, SC in zip(tags_sorted, sorted(SC))
#     ]
#     fns_sorted = [fns[idx] for idx in indices]
#     dfs = [core.utils.load(fn) for fn in fns_sorted]
#     plot_line(
#         dfs,
#         labels,
#         x="ECn" if not args.X else "EC",
#         y="OCn" if not args.Y else "OC",
#         m="OG_OT",
#         out_prefix=args.p,
#         max_lines=args.M,
#     )
# else:
#     print("[X] nothing to plot")

if __name__ == "__main__":
    run([])
