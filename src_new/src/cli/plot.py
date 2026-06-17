import matplotlib as mat

mat.use("agg")

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

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
- make -d an argument so user can point it to dir of interest and it does all the plots
"""


def plot_line(
    dfs,
    labels,
    x=None,
    y=None,
    m=None,
    out_prefix=None,
    max_lines=9,
):
    df_chunks, label_chunks = [], []
    for i in range(0, len(dfs), max_lines):
        j = i + max_lines
        df_chunks.append(dfs[i:j])
        label_chunks.append(labels[i:j])
    prop_cycle = plt.rcParams["axes.prop_cycle"]
    default_colors = prop_cycle.by_key()["color"]
    for idx_chunk, (label_chunk, df_chunk) in enumerate(zip(label_chunks, df_chunks)):
        lines = []
        fig = plt.figure(figsize=(6, 8), dpi=200, frameon=True)
        ax = fig.add_subplot(111)
        for idx, (label, df) in enumerate(zip(label_chunk, df_chunk)):
            for name in sorted(df[m].unique()):
                _df = df[df["OG_OT"] == name]
                lines += ax.plot(
                    _df[x],
                    _df[y],
                    alpha=0.9,
                    color=(
                        plt.cm.gnuplot2(idx / max_lines)
                        if len(dfs) >= 20
                        else plt.cm.tab20(idx / 20)
                        if len(dfs) > 10
                        else default_colors[idx]
                    ),
                    label=label,
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
        if len(handles_1) > 3:
            handles_1 = [
                handle_1 for handle_1 in handles_1 if handle_1._linestyle == "-"
            ]
        else:
            handles_1 = [
                handle_1 for handle_1 in handles_1 if handle_1._linestyle == "--"
            ]
        legend_1 = ax.legend(
            handles=handles_1,
            labels=label_chunk,
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
        if len(df_chunks) > 1:
            zeros = len(str(len(df_chunks)))
            out_f = f"{out_prefix}.{str(idx_chunk + 1).zfill(zeros)}.sampling.{x}_vs_{y}.png"
        else:
            out_f = f"{out_prefix}.sampling.{x}_vs_{y}.png"
        fig.savefig(out_f)
        print("[+] Created %s" % out_f)
        plt.close(fig)


def plot_3d(n=4):
    import matplotlib.pyplot as plt
    import pandas as pd

    e = pd.read_parquet(
        "/Users/dom/data/testing/psyche_all/input/orthogroups.counts.parquet"
    )
    EC = e.sum(axis=1)
    SC = e.ge(1).sum(axis=1)
    SC_max = SC.max()
    EC_max = EC.max()
    # df = (
    #     pd.concat([EC, SC], axis=1)
    #     .value_counts()
    #     .reset_index()
    #     .sort_values(by=["EC", "SC"])
    # )
    df_SC = SC.rename("SC").value_counts().reset_index().sort_values(by=["SC"])
    df_EC = EC.rename("EC").value_counts().reset_index().sort_values(by=["EC"])
    count_max = df_EC["count"].max()
    fig = plt.figure(figsize=(8, 10), dpi=200, frameon=True)
    ax = fig.subplot_mosaic([["top"], ["bottom"]])
    # df = df.sort_values(["SC", "EC"])
    # for threshold in thresholds[::-1]:
    #    ax.plot(
    #        df_EC["EC"],
    #        df_EC["count"],
    #        c="darkgrey",
    #        # df[df["SC"] <= threshold]["EC"],
    # df[df["SC"] <= threshold]["count"],
    # label=f"<= {round(threshold, 0)}",
    # alpha=0.5,
    # )
    ax["top"].vlines(
        SC_max,
        ymin=1,
        ymax=df_EC["count"].max(),
        colors="darkgrey",
        linestyles="dashed",
        alpha=0.5,
    )
    ax["top"].scatter(
        df_EC["EC"],
        df_EC["count"],
        c="mediumslateblue",
        s=1,
        # df[df["SC"] <= threshold]["EC"],
        # df[df["SC"] <= threshold]["count"],
        alpha=1,
    )
    ax["top"].plot(
        df_EC["EC"],
        df_EC["count"],
        c="hotpink",
        # df[df["SC"] <= threshold]["EC"],
        # df[df["SC"] <= threshold]["count"],
        # label=f"<= {round(threshold, 0)}",
        lw=0.25,
        alpha=0.5,
    )
    ax["bottom"].vlines(
        SC_max,
        ymin=1,
        ymax=df_SC["count"].max(),
        colors="darkgrey",
        alpha=0.5,
        linestyles="dashed",
    )
    ax["bottom"].scatter(
        df_SC["SC"],
        df_SC["count"],
        c="mediumslateblue",
        s=1,
        # df[df["SC"] <= threshold]["EC"],
        # df[df["SC"] <= threshold]["count"],
        alpha=1,
    )
    ax["bottom"].plot(
        df_SC["SC"],
        df_SC["count"],
        c="hotpink",
        # df[df["SC"] <= threshold]["EC"],
        # df[df["SC"] <= threshold]["count"],
        # label=f"<= {round(threshold, 0)}",
        lw=0.25,
        alpha=0.5,
    )
    # z = np.polyfit(df_EC["EC"], df_EC["count"], 5)
    # p = np.poly1d(z)
    # ax.plot(df_EC["EC"], p(df_EC["EC"]), "r--")
    ax["top"].set_xscale("log", base=10)
    ax["top"].set_ylim(0.5, count_max * 1.5)
    ax["top"].set_xlim(0.8, EC_max * 1.5)
    ax["top"].set_yscale("log", base=10)
    ax["top"].set_ylabel("Counts")
    ax["top"].set_xlabel("Orthogroup size (EC)")
    ax["bottom"].set_xscale("log", base=10)
    ax["bottom"].set_yscale("log", base=10)
    ax["bottom"].set_ylabel("Counts")
    ax["bottom"].set_xlabel("SC")
    ax["bottom"].set_ylim(0.5, df_SC["count"].max() * 1.5)
    ax["bottom"].set_xlim(0.8, SC_max * 1.5)
    out_f = "test.png"
    fig.savefig(out_f)
    print("[+] Created %s" % out_f)
    plt.close(fig)
    # ax.set_xlim(1, x.max())
    # ax.set_xscale("log", base=10)
    # ax.set_ylim(1, y.max())
    # ax.set_yscale("log", base=10)


# def plot_tally(
#     dfs,
#     labels,
#     x=None,
#     y=None,
#     m=None,
#     out_prefix=None,
#     max_lines=9,
# ):
#     prop_cycle = plt.rcParams["axes.prop_cycle"]
#     default_colors = prop_cycle.by_key()["color"]
#     df_tally = core.utils.get_tally_df()

#     for idx_chunk, (label_chunk, df_chunk) in enumerate(zip(label_chunks, df_chunks)):
#         lines = []
#         fig = plt.figure(figsize=(6, 8), dpi=200, frameon=True)
#         ax = fig.add_subplot(111)
#         for idx, (label, df) in enumerate(zip(label_chunk, df_chunk)):
#             for name in sorted(df[m].unique()):
#                 _df = df[df["OG_OT"] == name]
#                 lines += ax.plot(
#                     _df[x],
#                     _df[y],
#                     alpha=0.9,
#                     color=(
#                         plt.cm.gnuplot2(idx / max_lines)
#                         if len(dfs) >= 20
#                         else plt.cm.tab20(idx / 20)
#                         if len(dfs) > 10
#                         else default_colors[idx]
#                     ),
#                     label=label,
#                     lw=1.5,
#                     linestyle=line_style[name],
#                 )
#         ax.set_ylabel(y)
#         ax.set_xlabel(x)
#         if x.endswith("n"):
#             ax.set_xlim([-0.05, 1.05])
#         if y.endswith("n"):
#             ax.set_ylim([-0.05, 1.05])
#         handles_1, labels_1 = plt.gca().get_legend_handles_labels()
#         if len(handles_1) > 3:
#             handles_1 = [
#                 handle_1 for handle_1 in handles_1 if handle_1._linestyle == "-"
#             ]
#         else:
#             handles_1 = [
#                 handle_1 for handle_1 in handles_1 if handle_1._linestyle == "--"
#             ]
#         legend_1 = ax.legend(
#             handles=handles_1,
#             labels=label_chunk,
#             title="Taxongroup",
#             frameon=False,
#             loc="upper left",
#         )
#         handles = [
#             Line2D([0], [0], label="shared", color="grey", linestyle="-"),
#             Line2D([0], [0], label="specific", color="grey", linestyle=":"),
#             Line2D([0], [0], label="singleton", color="grey", linestyle="--"),
#         ]
#         legend_2 = ax.legend(
#             title="OG type",
#             handles=handles,
#             frameon=False,
#             loc="upper center",
#         )
#         ax.add_artist(legend_1)
#         ax.add_artist(legend_2)
#         plt.tight_layout()
#         if len(df_chunks) > 1:
#             zeros = len(str(len(df_chunks)))
#             out_f = f"{out_prefix}.{str(idx_chunk + 1).zfill(zeros)}.sampling.{x}_vs_{y}.png"
#         else:
#             out_f = f"{out_prefix}.sampling.{x}_vs_{y}.png"
#         fig.savefig(out_f)
#         print("[+] Created %s" % out_f)
#         plt.close(fig)


def run(args):
    plot_3d()
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
