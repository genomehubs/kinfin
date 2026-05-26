import core.analysis
import core.log
import matplotlib as mat
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

mat.use("agg")

COLOR_HISTOGRAM = "orange"
COLORS = ["deeppink", "dodgerblue"]
COLOR_AXES = "grey"
LEGEND_FONTSIZE = 10
AXES_TICKS_FONTSIZE = 8
AXES_LABELS_FONTSIZE = 8

MAX_LINES = 9
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
):
    df_chunks, label_chunks = [], []
    for i in range(0, len(dfs), MAX_LINES):
        j = i + MAX_LINES
        df_chunks.append(dfs[i:j])
        label_chunks.append(labels[i:j])
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
                    alpha=0.5,
                    color=f"C{idx}",
                    label=label,
                    lw=1.5,
                    linestyle=line_style[name],
                )
        ax.set_ylabel("OCn")
        ax.set_xlabel("ECn")
        ax.set_xlim([-0.05, 1.05])
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
        legend_2 = ax.legend(title="OG type", handles=handles, loc="lower right")
        ax.add_artist(legend_1)
        ax.add_artist(legend_2)
        plt.tight_layout()
        if len(df_chunks) > 1:
            zeros = len(str(len(df_chunks)))
            out_f = f"{out_prefix}.{str(idx_chunk + 1).zfill(zeros)}.sampling.ECn_vs_OCn.png"
        else:
            out_f = f"{out_prefix}.sampling.ECn_vs_OCn.png"
        fig.savefig(out_f)
        print("[+] Created %s" % out_f)
        plt.close(fig)


def run(args):
    tags = [f"{fn.split('.')[-4]}" for fn in args.f]
    SC = [f"{fn.split('.')[-3]}" for fn in args.f]
    labels = [f"{tag} ({SC})" if int(SC) > 1 else f"{tag}" for tag, SC in zip(tags, SC)]
    dfs = [core.utils.load(fn) for fn in args.f]
    plot_line(dfs, labels, x="ECn", y="OCn", m="OG_OT", out_prefix=args.p)
