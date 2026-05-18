import collections
import contextlib
import glob
import itertools
import json
import math
import multiprocessing
import sys
import time
import traceback

import ete4
import numpy as np
import pandas as pd
import scipy
from tqdm import tqdm

# from dask.dataframe import from_pandas
# https://docs.dask.org/en/stable/dataframe-best-practices.html

INDEX_ANNOTATION = [
    "orthogroup_id",
    "analysis",
    "signature_id",
    "signature_desc",
    "interpro_id",
    "interpro_desc",
    "go_annotation",
    "pathway_annotations",
    "sample_id",
]

PROGRESS_DESC = "[partitioning] progress"
PROGRESS_NCOLS = 0
CONFIG_KEYWORD_MISSING = "NA"
CONFIG_MIN_SAMPLE_IDS = 2


"""
Based on config
 "CBRIG", "DMEDI", "LSIGM", "AVITE", "CELEG", "EELAP", "OOCHE2", "OFLEX", "LOA2", "SLABI", "BMALA", "DIMMI", "WBANC2", "TCALL", "OOCHE1", "BPAHA", "OVOLV", "WBANC1" "LOA1",

0) dict-of-dict to keep track of TaxonGroups (TGs)
- used for iteration
d = {
    "genus":
        {
            "genus_A": ("A",),
            "genus_B": ("B",),
            "genus_C": ("C",),
        },
    "all":
        {
        "all": ("A", "B", "C"),
        }
}

1) dict w/ taxon_names-tuple as key and partition data as value
- no unnecessary computation

d = {
    ("A", "B", "C") : ...,
    ("A",) : ...,
    ("B",) : ...,
    ("C",) : ...,
    ("A", "B"): ...,
}

DataPartition()

### TAXON_GROUP

TN = ("CBRIG", "CELEG")
TG_set = set(TG)
nTG = tuple([TN for TN in x.columns if TN not in TG])

df_TG = x.loc[:, TN]
df_nTG = x.loc[:, nTN]
df = pd.DataFrame()
df['PC'] = x.sum(axis=1)
df['TC_TG'] = df_TG.mask(df_TG > 1, 1).sum(axis=1)
df['PC_TG'] = df_TG.sum(axis=1)
df['PCm_TG'] = df_TG.mask(df_TG == 0, np.NAN).mean(axis=1).replace(np.NAN, 0.0)
df['COV_TG'] = df['TC_TG'] / len(TG)
df['TC_nTG'] = df_nTG.mask(df_nTG > 1, 1).sum(axis=1)
df['PC_nTG'] = df_nTG.sum(axis=1)
df['PCm_nTG'] = df_nTG.mask(df_nTG == 0, np.NAN).mean(axis=1).replace(np.NAN, 0.0)
with np.errstate(divide='ignore'):
    df['log2_mean(TG/nTG)'] = np.log2(mean_div).replace(-np.inf, np.NAN).replace(np.inf, np.NAN)

type_conditions = [
    (df['PC_TG'] == 0),
    (df['PC_TG'] == 1),
    (df['PC_TG'] >=1 ) & (df['PC_nTG'] == 0),
    (df['PC_TG'] >=1 ) & (df['PC_nTG'] >= 1)
]
type_labels = [
    "absent",
    "singleton",
    "specific",
    "shared"
]
df['type'] = np.select(type_conditions, type_labels)
df['TN_TG'] = df_TG.mask(df_TG.mask(df_TG==0, np.NAN).notnull(), df_TG.columns.to_series(), axis=1).replace(0, "").astype(str).apply(','.join, axis=1).replace(r",+", ",", regex=True).replace(r"^,", "", regex=True).replace(r",$", "", regex=True).replace("", np.NAN)
df['TN_nTG'] = df_nTG.mask(df_nTG.mask(df_nTG==0, np.NAN).notnull(), df_nTG.columns.to_series(), axis=1).replace(0, "").astype(str).apply(','.join, axis=1).replace(r",+", ",", regex=True).replace(r"^,", "", regex=True).replace(r",$", "", regex=True).replace("", np.NAN)
try:
            pvalue = scipy.stats.mannwhitneyu(
                implicit_count_1,
                implicit_count_2,
                alternative="two-sided",
            )[1]
        except ValueError:  # throws ValueError when all numbers are equal
            pvalue = 1.0

df['pvalue'] = scipy.stats.mannwhitneyu(df_TG.mask(df_TG==0, np.nan), df_nTG.mask(df_nTG==0, np.nan), alternative="two-sided", nan_policy="omit")

       
        very costly
        BUT consider: https://pandas.pydata.org/pandas-docs/stable/user_guide/text.html
     
        # df_partition["TN_TG"] = (
        #     df_TG.mask(
        #         df_TG.mask(df_TG == 0, np.nan).notnull(),
        #         df_TG.columns.to_series(),
        #         axis=1,
        #     )
        #     .replace(0, "")
        #     .astype(str)
        #     .apply(",".join, axis=1)
        #     .replace(r",+", ",", regex=True)
        #     .replace(r"^,", "", regex=True)
        #     .replace(r",$", "", regex=True)
        #     .replace("", np.nan)
        # )
     
        very costly
        BUT consider: https://pandas.pydata.org/pandas-docs/stable/user_guide/text.html
     
        # df_partition["TN_nTG"] = (
        #     df_nTG.mask(
        #         df_nTG.mask(df_nTG == 0, np.nan).notnull(),
        #         df_nTG.columns.to_series(),
        #         axis=1,
        #     )
        #     .replace(0, "")
        #     .astype(str)
        #     .apply(",".join, axis=1)
        #     .replace(r",+", ",", regex=True)
        #     .replace(r"^,", "", regex=True)
        #     .replace(r",$", "", regex=True)
        #     .replace("", np.nan)
        # )

"""

"""
>>> import playground; d = playground.parse_config_dicts(config_fn="/Users/dom/git/kinfin_.test_data/leps/lepidoptera_orthodb_input/config.DRL.json"); s = playground.get_sample_ids(config_dicts=d); t = playground.get_taxongroups(config_dicts=d); o = playground.parse_df_orthogroups("/Users/dom/git/kinfin_.test_data/leps/lepidoptera_orthodb_input/Orthogroups.txt", sample_ids=s); c = playground.get_df_counts(o); playground.do_partitions(t, c, cpus=10)
[parse_config_dicts] found 277 sample IDs
[get_taxongroups] - elapsed: 0.042544500436633825
[parse_df_orthogroups] parsing 277 samples from '/Users/dom/git/kinfin_.test_data/leps/lepidoptera_orthodb_input/Orthogroups.txt'
[parse_df_orthogroups] removing 114 sample id(s)
[parse_df_orthogroups] removed 1779990 element ids
[parse_df_orthogroups] elapsed: 2.3214567499235272
[get_df_counts] elapsed: 0.6666769157163799
[partitioning] progress: 100% 300/300 [03:14<00:00,  1.54it/s]
[do_partitions] - elapsed: 194.66630054125562
"""


def iter_seq_length(fn):
    with open(fn) as fh:
        header, seqs = "", []
        for line in fh:
            if line[0] == ">":
                if header:
                    header = (
                        header.replace(":", "_")
                        .replace(",", "_")
                        .replace("(", "_")
                        .replace(")", "_")
                    )  # orthofinder replaces chars
                    yield header, len("".join(seqs))
                header, seqs = (
                    line[1:-1].split()[0],
                    [],
                )  # Header is split at first whitespace
            else:
                seqs.append(line[:-1])
        header = (
            header.replace(":", "_")
            .replace(",", "_")
            .replace("(", "_")
            .replace(")", "_")
        )  # orthofinder replaces chars
        yield header, len("".join(seqs))


def get_lengths(path):
    t_0 = time.monotonic()
    data = {}
    for fn in glob.glob(f"{path}/*faa"):
        for header, length in iter_seq_length(fn):
            data[header] = length
    print(f"[get_df_lengths] elapsed: {time.monotonic() - t_0}")
    return data


def parse_df_orthogroups(orthogroup_fn, sample_ids=[]):
    t_0 = time.monotonic()
    # [TBD] how to establish element_id <-> sample_id?
    print(
        f"[parse_df_orthogroups] parsing {len(sample_ids)} samples from '{orthogroup_fn}'"
    )
    data = []
    with open(orthogroup_fn) as orthogroup_fh:
        for line in orthogroup_fh:
            temp = line.rstrip("\n").split(" ")
            # print(f"{temp=}")
            orthogroup_id, element_ids = temp[0].replace(":", ""), temp[1:]
            for element_id in element_ids:
                sample_id = element_id.split(".")[0]
                data.append((element_id, orthogroup_id, sample_id))
    df_orthogroups = pd.DataFrame.from_records(
        data,
        columns=[
            "element_id",
            "orthogroup_id",
            "sample_id",
        ],
    )
    sample_ids_to_remove = [
        s for s in list(df_orthogroups["sample_id"].unique()) if s not in sample_ids
    ]
    print(f"[parse_df_orthogroups] removing {len(sample_ids_to_remove)} sample id(s)")
    mask = df_orthogroups["sample_id"].isin(sample_ids)
    print(f"[parse_df_orthogroups] removed {mask.value_counts()[False]} element ids")
    df_orthogroups = df_orthogroups[mask]
    if df_orthogroups.empty:
        print(
            f"[parse_df_orthogroups] [Error] None of these sample IDs were found: {', '.join(sample_ids)}"
        )
        sys.exit(1)
    sample_ids_present = set(df_orthogroups["sample_id"].unique())
    sample_ids_missing = [
        sample_id for sample_id in sample_ids if sample_id not in sample_ids_present
    ]
    if sample_ids_missing:
        print(f"[parse_df_orthogroups] {sample_ids_missing=}")
        sys.exit(1)
    print(f"[parse_df_orthogroups] elapsed: {time.monotonic() - t_0}")
    return df_orthogroups


def get_df_counts(df_orthogroups):
    t_0 = time.monotonic()
    df_counts = (
        df_orthogroups.groupby(
            [
                "orthogroup_id",
                "sample_id",
            ],
            as_index=False,
        )
        .count()
        .set_index(["orthogroup_id", "sample_id"])["element_id"]
        .unstack(fill_value=0)
    )
    print(f"[get_df_counts] elapsed: {time.monotonic() - t_0}")
    return df_counts


# def get_df_scogs(
#     df_counts,
#     TG=[],
#     count_target=1,
#     count_min=0,
#     count_max=2,
#     count_fraction=0.75,
# ):
#     TG = TG if TG else df_counts.columns

#     def infer_scogs(row):
#         TNs = [k for k, v in row.to_dict().items() if v > 0]
#         node = tree.common_ancestor(TNs)
#         node_id = node.get_prop("node_id")
#         OG_type = "synapomorphy" if len(TNs) > 1 else "autapomorphy"
#         OG_NODE_COV = len(TNs) / len(list(node.leaf_names()))
#         return (
#             node_id,
#             OG_type,
#             OG_NODE_COV,
#         )

#     t_0 = time.monotonic()
#     df_scogs = df_counts.apply(place_orthogroup, axis=1, result_type="expand")
#     df_scogs.columns = ["node", "OG_type", "OG_N_COV"]
#     print(f"[get_df_nodes] elapsed: {time.monotonic() - t_0}")
#     return df_scogs


def partition_lengths(df_orthogroups, lengths, TGs={}):
    # [ToDo]
    # - probably should be based on interproscan file (removes requirement of FASTA parsing)
    # - expand to generate cluster_summary
    # - no need for cluster_type/attribute
    """
    # TG = "samples"
    import playground; x = playground.get_lengths("/Users/dom/git/kinfin_.test_data/advanced/input/fastas"); z = playground.parse_df_orthogroups("../input/Orthogroups.txt"); playground.partition_lengths(z, x, TGs={"CBRIG": ("CBRIG",), "DMEDI": ("DMEDI",), "LSIGM": ("LSIGM",), "AVITE": ("AVITE",), "CELEG": ("CELEG",), "EELAP": ("EELAP",), "OOCHE2": ("OOCHE2",), "OFLEX": ("OFLEX",), "LOA2": ("LOA2",), "SLABI": ("SLABI",), "BMALA": ("BMALA",), "DIMMI": ("DIMMI",), "WBANC2": ("WBANC2",), "TCALL": ("TCALL",), "OOCHE1": ("OOCHE1",), "BPAHA": ("BPAHA",), "OVOLV": ("OVOLV",), "WBANC1": ("WBANC1",),  "LOA1": ("LOA1",)})
    # TG = "host""
    import playground; x = playground.get_lengths("/Users/dom/git/kinfin_.test_data/advanced/input/fastas"); z = playground.parse_df_orthogroups("../input/Orthogroups.txt"); playground.partition_lengths(z, x, TGs={"outgroup": ("CBRIG","CELEG"), "human": ("DMEDI", "LOA2", "BMALA", "WBANC2", "OVOLV", "WBANC1", "LOA1"), "other": ("LSIGM", "AVITE", "EELAP", "OOCHE2", "OFLEX", "SLABI", "DIMMI", "TCALL", "OOCHE1", "BPAHA")})
    """
    t_0 = time.monotonic()
    df_orthogroups["length"] = df_orthogroups["element_id"].map(lengths)
    dfs = [
        df_orthogroups.groupby("orthogroup_id").agg(
            EL_mean=("length", "mean"), EL_sd=("length", "std")
        )
    ]
    for TG, TNs in TGs.items():
        # print(f"{TG=}", f"{TNs=}")
        dfs.append(
            df_orthogroups.where(df_orthogroups["sample_id"].isin(TNs))
            .groupby("orthogroup_id")
            .agg(TG_EL_mean=("length", "mean"), TG_EL_sd=("length", "std"))
            .rename(columns={"TG_EL_mean": f"{TG}_EL_mean", "TG_EL_sd": f"{TG}_EL_sd"})
        )
    df_lengths = pd.concat(dfs, axis=1).reindex(dfs[0].index)
    print(f"[partition_lengths] elapsed: {time.monotonic() - t_0}")
    return df_lengths


def get_tree(tree_fn, outgroup=[]):
    """
    >>> pip install ete4
    """
    t = ete4.Tree(tree_fn)
    if outgroup:
        try:
            t.set_outgroup(t.common_ancestor(outgroup))
        except ete4.core.tree.TreeError as exc:
            print(
                f"[get_tree] setting outgroup to {outgroup} - {exc}\n{traceback.format_exc()}"
            )
    for idx, node in enumerate(t.traverse("levelorder")):
        node.add_prop("node_id", node.name if node.name else f"n{idx}")
    return t


def get_df_nodes(df_counts, tree):
    """
    technically only needs to be done once for each tip-combo ... but don't worry unless it gets too slow
    """

    def place_orthogroup(row):
        TNs = [k for k, v in row.to_dict().items() if v > 0]
        node = tree.common_ancestor(TNs)
        node_id = node.get_prop("node_id")
        OG_type = "synapomorphy" if len(TNs) > 1 else "autapomorphy"
        OG_NODE_COV = len(TNs) / len(list(node.leaf_names()))
        return (
            node_id,
            OG_type,
            OG_NODE_COV,
        )

    t_0 = time.monotonic()
    df_nodes = df_counts.apply(place_orthogroup, axis=1, result_type="expand")
    df_nodes.columns = ["node", "OG_type", "OG_N_COV"]
    print(f"[get_df_nodes] elapsed: {time.monotonic() - t_0}")
    return df_nodes


def get_df_entropy(df_orthogroups, df_interpro, df_counts, analysis="Pfam"):

    def entropy(values):
        signature_counter = collections.Counter([v for k, v in values.items()])
        return -sum(
            [
                i / signature_counter.total() * math.log2(i / signature_counter.total())
                for i in list(signature_counter.values())
            ]
        )

    def glue(values):
        signature_counter = collections.Counter(
            [v for k, v in values.items() if isinstance(v, str)]
        )
        return (
            "|".join([f"{k}:{v}" for k, v in signature_counter.most_common()])
            if signature_counter
            else np.nan
        )

    t_0 = time.monotonic()
    df = (
        df_interpro.set_index("element_id")
        .join(df_orthogroups.set_index("element_id"))
        .reset_index()
    )[
        [
            "orthogroup_id",
            "analysis",
            "interpro_id",
            "go_annotation",
            "signature_id",
            "sample_id",
        ]
    ]
    df_entropy = (
        df[df["analysis"] == analysis]
        .groupby("orthogroup_id", as_index=False)
        .agg(
            **{
                f"{analysis}_entropy": pd.NamedAgg(
                    column="signature_id",
                    aggfunc=entropy,
                ),
                f"{analysis}_ids": pd.NamedAgg(
                    column="signature_id",
                    aggfunc=glue,
                ),
                f"{analysis}_TN_COV": pd.NamedAgg(
                    column="sample_id",
                    aggfunc="nunique",
                ),
                f"{analysis}_EC_COV": pd.NamedAgg(
                    column="signature_id",
                    aggfunc="count",
                ),
                "interpro_entropy": pd.NamedAgg(
                    column="signature_id",
                    aggfunc=entropy,
                ),
                "interpro_ids": pd.NamedAgg(
                    column="signature_id",
                    aggfunc=glue,
                ),
                "go_entropy": pd.NamedAgg(
                    column="go_annotation",
                    aggfunc=entropy,
                ),
                "go_ids": pd.NamedAgg(
                    column="go_annotation",
                    aggfunc=glue,
                ),
            }
        )
        .set_index("orthogroup_id")
    )
    df_entropy[f"{analysis}_TN_COV"] /= df_counts.ge(1).sum(axis=1)
    df_entropy[f"{analysis}_EC_COV"] /= df_counts.sum(axis=1)
    print(f"[get_df_entropy] elapsed: {time.monotonic() - t_0}")
    return df_entropy[
        [
            f"{analysis}_TN_COV",
            f"{analysis}_EC_COV",
            f"{analysis}_entropy",
            f"{analysis}_ids",
            "interpro_entropy",
            "interpro_ids",
            "go_entropy",
            "go_ids",
        ]
    ]


def get_df_interpro(fn, df_orthogroups):
    t_0 = time.monotonic()
    df_interpro = pd.read_csv(
        "/Users/dom/git/kinfin_.test_data/advanced/input/kinfin.interproscan.tsv",
        sep="\t",
        names=[
            "element_id",
            "sequence_md5",
            "sequence_length",
            "analysis",
            "signature_id",
            "signature_desc",
            "signature_start",
            "signature_stop",
            "signature_score",
            "signature_status",
            "date",
            "interpro_id",
            "interpro_desc",
            "go_annotation",
            "pathway_annotations",
        ],
    )
    annotations_valid = df_interpro["element_id"].isin(df_orthogroups["element_id"])
    annotations_orphan_count = int(annotations_valid.value_counts()[False])
    if annotations_orphan_count:
        print(
            f"[get_df_interpro] Found {annotations_orphan_count} annotation(s) of sequences which are not part of any Orthogroup. Will be ignored ..."
        )
        dump(df_interpro[~annotations_valid], f"{fn}.orphan")
        dump(df_interpro[annotations_valid], f"{fn}.filtered")
    print(f"[get_df_interpro] elapsed: {time.monotonic() - t_0}")
    return df_interpro[annotations_valid]


def get_df_annotation(
    df_orthogroups,
    df_interpro,
    df_counts,
    proportional=True,
):
    t_0 = time.monotonic()
    df_annotation = (
        df_interpro.set_index("element_id")
        .join(df_orthogroups.set_index("element_id"))
        .reset_index()
        .groupby(
            INDEX_ANNOTATION,
            as_index=False,
            dropna=False,
        )
        .agg(
            EC_AP_TN=("element_id", "nunique"),
        )
        .set_index(INDEX_ANNOTATION)
        .unstack(fill_value=0)
    )
    df_annotation["EC"] = df_counts.sum(axis=1)
    df_annotation["EC_AC"] = df_annotation["EC_AP_TN"].sum(axis=1)
    df_annotation["EC_AP"] = df_annotation["EC_AC"] / df_annotation["EC"]
    df_annotation["TN_AP"] = (
        df_annotation["EC_AP_TN"].ge(1).sum(axis=1).div(df_counts.ge(1).sum(axis=1))
    )
    if proportional is True:
        df_annotation["EC_AP_TN"] = (
            df_annotation["EC_AP_TN"]
            .div(
                df_counts,
            )
            .replace(np.nan, 0.0)
        )
    print(f"[get_df_annotation] elapsed: {time.monotonic() - t_0}")
    return df_annotation[
        [
            "EC",
            "EC_AC",
            "EC_AP",
            "TN_AP",
            "EC_AP_TN",
        ]
    ]


def get_cog_type(values, count_target, count_min, count_max, count_fraction):
    if np.all(values == count_target):
        return "true"  # [ToDo] better name?
    elif np.mean((values >= count_min) & (values <= count_max)) >= count_fraction:
        return "fuzzy"
    else:
        return "false"  # [ToDo] better name?


def get_df_partition(
    *args,
    **kwargs,
):
    # t_0 = time.monotonic()
    kwargs = kwargs if kwargs else args[0]
    TG_1 = kwargs.get("TG_1", [])
    TG_2 = kwargs.get("TG_2", [])
    labels = kwargs.get("labels", {})
    count_target = kwargs.get("count_target", 1)
    count_min = kwargs.get("count_min", 0)
    count_max = (kwargs.get("count_max", 2),)
    count_fraction = kwargs.get("count_fraction", 0.75)
    single_file = kwargs.get("single_file", False)
    df_counts = kwargs.get("df_counts_in", None)
    df_counts_TG1 = df_counts.loc[:, TG_1]
    df_counts_TG2 = df_counts.loc[:, TG_2]
    df_partition = pd.DataFrame(index=df_counts.index)
    # timing = {}  # [timing]
    # t_i = time.monotonic() [timing]
    df_partition["SC"] = df_counts.ge(1).sum(axis=1)  # .ge() >> .mask()
    # timing["SC"], t_i = time.monotonic() - t_i, time.monotonic()  # [timing]
    df_partition["SC_TG1"] = df_counts_TG1.ge(1).sum(axis=1)  # .ge() >> .mask()
    # timing["SC_TG1"], t_i = time.monotonic() - t_i, time.monotonic()  # [timing]
    df_partition["SP_TG1"] = df_partition["SC_TG1"] / len(TG_1)
    # timing["SP_TG1"], t_i = time.monotonic() - t_i, time.monotonic()  # [timing]
    df_partition["SC_TG2"] = df_counts_TG2.ge(1).sum(axis=1)  # .ge() >> .mask()
    # timing["SC_TG2"], t_i = time.monotonic() - t_i, time.monotonic()  # [timing]
    df_partition["SP_TG2"] = df_partition["SC_TG2"] / len(TG_2)
    # timing["SP_TG2"], t_i = time.monotonic() - t_i, time.monotonic()  # [timing]
    df_partition["EC"] = df_counts.sum(axis=1).astype(int)
    # timing["EC"], t_i = time.monotonic() - t_i, time.monotonic()  # [timing]
    df_partition["EC_TG1"] = df_counts_TG1.sum(axis=1).astype(int)
    # timing["EC_TG1"], t_i = time.monotonic() - t_i, time.monotonic()  # [timing]
    df_partition["EC_TG2"] = df_counts_TG2.sum(axis=1).astype(int)
    # timing["EC_TG2"], t_i = time.monotonic() - t_i, time.monotonic()  # [timing]
    df_partition["OG_type"] = np.select(
        condlist=[
            (df_partition["EC_TG1"] == 0),
            (df_partition["EC"] == 1),
            (df_partition["EC_TG1"] >= 1) & (df_partition["EC_TG2"] == 0),
            (df_partition["EC_TG1"] >= 1) & (df_partition["EC_TG2"] >= 1),
        ],
        choicelist=[
            "absent",
            "singleton",
            "specific",
            "shared",
        ],
        default="None",
    )
    # timing["OG_type"], t_i = time.monotonic() - t_i, time.monotonic()  # [timing]
    df_partition["COG_TP"] = df_counts.eq(count_target).sum(axis=1) / len(
        df_counts.columns
    )
    # timing["COG_TP"], t_i = time.monotonic() - t_i, time.monotonic()  # [timing]
    df_partition["COG_TP_TG1"] = df_counts_TG1.eq(count_target).sum(axis=1) / len(TG_1)
    # timing["COG_TP_TG1"], t_i = time.monotonic() - t_i, time.monotonic()  # [timing]
    df_partition["COG_type_TG1"] = df_counts_TG1.apply(
        get_cog_type,
        axis=1,
        raw=True,
        args=(
            count_target,
            count_min,
            count_max,
            count_fraction,
        ),
    )
    # timing["COG_type_TG1"], t_i = time.monotonic() - t_i, time.monotonic()  # [timing]
    df_partition["EC_mean"] = df_counts.mean(axis=1)
    # timing["EC_mean"], t_i = time.monotonic() - t_i, time.monotonic()  # [timing]
    df_partition["EC_mean_TG1"] = df_counts_TG1.mean(axis=1)
    # timing["EC_mean_TG1"], t_i = time.monotonic() - t_i, time.monotonic()  # [timing]
    df_partition["EC_mean_TG2"] = df_counts_TG2.mean(axis=1)
    # timing["EC_mean_TG2"], t_i = time.monotonic() - t_i, time.monotonic()  # [timing]
    df_partition["log2_mean(TG1/TG2)"] = np.log2(
        df_partition["EC_mean_TG1"] / df_partition["EC_mean_TG2"]
    )
    # timing["log2_mean(TG1/TG2)"], t_i = (time.monotonic() - t_i, time.monotonic())  # [timing]
    df_partition["pvalue"] = scipy.stats.mannwhitneyu(
        df_counts_TG1,
        df_counts_TG2,
        method="asymptotic",
        alternative="two-sided",
        nan_policy="omit",
        axis=1,
        keepdims=False,
    )[1]
    # timing["pvalue"], t_i = time.monotonic() - t_i, time.monotonic()  # [timing]
    df_partition["EC_median"] = df_counts.median(axis=1, skipna=True)
    # timing["EC_median"], t_i = time.monotonic() - t_i, time.monotonic()  # [timing]
    df_partition["EC_median_TG1"] = df_counts_TG1.median(axis=1, skipna=True)
    # timing["EC_median_TG1"], t_i = time.monotonic() - t_i, time.monotonic()  # [timing]
    df_partition["EC_median_TG2"] = df_counts_TG2.median(axis=1, skipna=True)
    # timing["EC_median_TG2"], t_i = time.monotonic() - t_i, time.monotonic()  # [timing]
    # print(f"[partition] elapsed: {time.monotonic() - t_0}")
    # pprint.pp(timing)  # [timing]
    for grouping, TG1_label, TG2_label in labels:
        fn = f"partition.{grouping}.{TG1_label}_vs_{TG2_label}"
        dump(df_partition, fn)
        if single_file:
            break

    return df_partition[
        [
            "OG_type",
            "SC",
            "SC_TG1",
            "SP_TG1",
            "SC_TG2",
            "SP_TG2",
            "EC",
            "EC_TG1",
            "EC_TG2",
            "EC_mean",
            "EC_mean_TG1",
            "EC_mean_TG2",
            "log2_mean(TG1/TG2)",
            "pvalue",
            "EC_median",
            "EC_median_TG1",
            "EC_median_TG2",
            "COG_type_TG1",
            "COG_TP",
            "COG_TP_TG1",
        ]
    ]


# def partition_before(
#     df_counts_in,
#     TG,
#     nTG=[],
#     metrics=True,
#     exclude=[],
#     count_target=1,
#     count_min=0,
#     count_max=2,
#     count_fraction=0.75,
# ):
#     """
#     NEEDS ALL LABELS AND DUMPS DIRECTLY FROM HERE!

#     >>> import playground; x = playground.parse_df_orthogroups("/Users/dom/git/kinfin_.test_data/leps/lepidoptera_orthodb_input/Orthogroups.txt"); y = playground.get_df_counts(x); zd = playground.partition(y, TG=['AbTri', 'AbTri1', 'AcAce', 'AcCri', 'AcEma', 'AcEph', 'AcFla', 'AcGri', 'AcLep', 'AcLit', 'AcPsi', 'AcSpa', 'AcSua', 'AgAur', 'AgCir', 'AgExc', 'AgGen', 'AgGen1', 'AgLeu', 'AgLit', 'AgLot', 'AgMac', 'AgMar', 'AgPut', 'AgStr', 'AgSub', 'AgTri', 'AlAes', 'AlOxy', 'AlRep', 'AmBer', 'AmJug', 'AmLuc', 'AmOcu', 'AmTra', 'AmTra1', 'AnCar', 'AnChi', 'AnCro', 'AnDer', 'AnInn', 'AnMun', 'ApBet', 'ApBis', 'ApCap', 'ApCra', 'ApCre', 'ApEff', 'ApEpo', 'ApHis', 'ApLim', 'ApLue', 'ApMon', 'ApNig', 'ApSor', 'ApSyr', 'ApTur', 'ArAge', 'ArAge1', 'ArArt', 'ArCra', 'ArGoe', 'ArPla', 'ArXyl', 'AtCen', 'AtMou', 'AuGam', 'AuPul', 'BeIch', 'BiAny', 'BiAny1', 'BiBet', 'BiStr', 'BlAdu', 'BlLac', 'BoMan', 'BoMan1', 'BoMor', 'BoSel', 'BrIno', 'BrVim', 'CaCla', 'CaFra', 'CaFug', 'CaKad', 'CaMar', 'CaPal', 'CaPal1', 'CaQue', 'CaSas', 'CeArg', 'CeRub', 'ChCul', 'ChFer', 'ChFum', 'ChInc', 'ChLeg', 'ChNem', 'ChSit', 'ChSup', 'ClCur', 'CnMed', 'CoCro', 'CoPyr', 'CoTra', 'CoVac', 'CrEli', 'CrLat', 'CrLig', 'CyAmp', 'CyMes', 'CyPun', 'CySem', 'CySpl', 'CyStr', 'DaChr', 'DaPle', 'DaPlePle', 'DeElp', 'DeKik', 'DePin', 'DePor', 'DePun', 'DiBru', 'DiChr', 'DiDah', 'DiMen', 'DiMen1', 'DiOo', 'DiRub', 'DiSac', 'DrEre', 'DrFal', 'DrIulMod', 'DrLab', 'EcGri', 'EcSil', 'EiCan', 'EiDep', 'EiSor', 'ElCor', 'ElSim', 'EmMon', 'EnFla', 'EnFus', 'EnQue', 'EpBil', 'EpDem', 'EpElu', 'EpNis', 'EpRam', 'ErAet', 'ErDef', 'ErLig', 'ErOch', 'ErTag', 'EsSul', 'EuAbb', 'EuCen', 'EuDod', 'EuEdi', 'EuExi', 'EuGla', 'EuIns', 'EuIsa', 'EuJap', 'EuLac', 'EuLuc', 'EuMi', 'EuPin', 'EuPro', 'EuPru', 'EuSim', 'EuSub', 'EuTes', 'EuTra', 'EuVul', 'FaAdi', 'FiYps', 'FuFur', 'GaMel', 'GaPyr', 'GlAle', 'GlSpa', 'GrApr', 'GrMol', 'GyRuf', 'HaPyr', 'HeAes', 'HeArm', 'HeArm1', 'HeAss', 'HeChr', 'HeCom', 'HeDys', 'HeFuc', 'HeSal', 'HeSar', 'HeTar', 'HeZea', 'HeZea1', 'HiSem', 'HoBla', 'HoPse', 'HyCos', 'HyEup', 'HyFas', 'HyFur', 'HyKah', 'HyMic', 'HyPro', 'HyPun', 'HyScr', 'HyVes', 'IdAve', 'IdDim', 'IpPod', 'LaCon', 'LaFle', 'LaMeg', 'LaPop', 'LaStr', 'LaSuf', 'LaWla', 'LeGly', 'LeGly1', 'LeSal', 'LeSin', 'LeSin1', 'LiAdu', 'LiCam', 'LiLea', 'LiOrn', 'LiSem', 'LiSoc', 'LoBim', 'LoHal', 'LuFer', 'LuTes', 'LyBel', 'LyCor', 'LyHir', 'LyMon', 'LyPhl', 'MaBra', 'MaExi', 'MaHyp', 'MaJur', 'MaLun', 'MaNot', 'MaSex', 'MaSex1', 'MeAlb', 'MeAth', 'MeCin', 'MeFla', 'MeFur', 'MeGal', 'MeMarRil', 'MeMenN', 'MePer', 'MiAru', 'MiMin', 'MiTil', 'MoLae', 'MuNit', 'MyAlb', 'MyFer', 'MyImp', 'MyLal', 'MyLor', 'MySep', 'MyVit', 'NoDro', 'NoFim', 'NoJan', 'NoPro', 'NoUdd', 'NoZic', 'NyIo', 'NyNit', 'NyPol', 'NyRev', 'NyUrt', 'OcDup', 'OcPle', 'OcSyl', 'OeQua', 'OlLat', 'OmLun', 'OpBru', 'OpLut', 'OrAnt', 'OrGot', 'OrGra', 'OrInc', 'OsFur', 'PaAeg', 'PaAegAeg', 'PaApo', 'PaAur', 'PaCin', 'PaCor', 'PaFas', 'PaMac', 'PaPol', 'PaStr', 'PaXut', 'PeGos', 'PeGos1', 'PeRho', 'PhBuc', 'PhFul', 'PhGno', 'PhMet', 'PhOpe', 'PhTre', 'PhVet', 'PiBra', 'PiMac', 'PiNap', 'PiRap', 'PlArg', 'PlFes', 'PlInt', 'PlXyl', 'PoFla', 'PoIca', 'PoLic', 'PrPyg', 'PtCap', 'PyMal', 'PyNig', 'SaPav', 'ScBip', 'ScCos', 'SeApi', 'SeBem', 'SeDen', 'ShVer', 'SpExi', 'SpFru', 'SpLit', 'SpLit1', 'SpLub', 'SpLut', 'SpPin', 'StBip', 'SyAnd', 'SyFor', 'SyMyo', 'SyTip', 'SyVes', 'TeFlu', 'TeLuc', 'ThAct', 'ThBat', 'ThBri', 'ThDec', 'ThMat', 'ThObe', 'ThSen', 'ThSyl', 'TiPel', 'TiSem', 'TiTri', 'ToAlt', 'TrEmo', 'TrNi', 'TuAbs', 'TyJac', 'UrSim', 'VaAta', 'VaCar', 'VaTam', 'VeCam', 'WaBin', 'XaIct', 'XaSpa', 'XeSex', 'XeXan', 'XyAre', 'YpCag', 'YpPlu', 'YpSca', 'YpSed', 'YpSeq', 'ZeCes', 'ZeHep', 'ZePyr', 'ZyFil'])
#     [parse_df_orthogroups] elapsed: 1.9772244999185205
#     [get_df_counts] elapsed: 0.9691542498767376
#     [partition] elapsed: 1.8879776657558978
#     {'SC': 0.027311624959111214,
#      'SC_TG': 0.0243927501142025,
#      'SP_TG': 0.00024054106324911118,
#      'SC_nTG': 0.002544958144426346,
#      'SP_nTG': 0.00015891622751951218,
#      'EC': 0.09090495808050036,
#      'EC_TG': 0.08114720787853003,
#      'EC_nTG': 0.0026344582438468933,
#      'OG_type': 0.005820500198751688,
#      'COG_TP': 0.026384124998003244,
#      'COG_TP_TG': 0.02643208298832178,
#      'COG_type_TG': 0.36072520911693573,
#      'EC_mean': 0.08084112498909235,
#      'EC_mean_TG': 0.07908158330246806,
#      'EC_mean_nTG': 0.0023332913406193256,
#      'log2_mean(TG/nTG)': 0.0003482499159872532,
#      'pvalue': 0.014906417112797499,
#      'EC_median': 0.42830095905810595,
#      'EC_median_TG': 0.4068118748255074,
#      'EC_median_nTG': 0.0023157079704105854}
#     """
#     t_0 = time.monotonic()
#     nTG = nTG if nTG else [TN for TN in df_counts_in.columns if TN not in TG]
#     df_counts = df_counts_in.replace(0, np.nan)
#     df_TG = df_counts.loc[:, TG]
#     df_nTG = df_counts.loc[:, nTG]
#     df_partition = pd.DataFrame(index=df_counts.index)
#     timing = {}
#     if metrics is True:
#         t_i = time.monotonic()
#         df_partition["SC"] = df_counts.ge(1).sum(axis=1)  # .ge() >> .mask()
#         timing["SC"], t_i = time.monotonic() - t_i, time.monotonic()
#         df_partition["SC_TG"] = df_TG.ge(1).sum(axis=1)  # .ge() >> .mask()
#         timing["SC_TG"], t_i = time.monotonic() - t_i, time.monotonic()
#         df_partition["SP_TG"] = df_partition["SC_TG"] / len(TG)
#         timing["SP_TG"], t_i = time.monotonic() - t_i, time.monotonic()
#         df_partition["SC_nTG"] = df_nTG.ge(1).sum(axis=1)  # .ge() >> .mask()
#         timing["SC_nTG"], t_i = time.monotonic() - t_i, time.monotonic()
#         df_partition["SP_nTG"] = df_partition["SC_nTG"] / len(nTG)
#         timing["SP_nTG"], t_i = time.monotonic() - t_i, time.monotonic()
#         df_partition["EC"] = df_counts.sum(axis=1).astype(int)
#         timing["EC"], t_i = time.monotonic() - t_i, time.monotonic()
#         df_partition["EC_TG"] = df_TG.sum(axis=1).astype(int)
#         timing["EC_TG"], t_i = time.monotonic() - t_i, time.monotonic()
#         df_partition["EC_nTG"] = df_nTG.sum(axis=1).astype(int)
#         timing["EC_nTG"], t_i = time.monotonic() - t_i, time.monotonic()
#         df_partition["OG_type"] = np.select(
#             condlist=[
#                 (df_partition["EC_TG"] == 0),
#                 (df_partition["EC"] == 1),
#                 (df_partition["EC_TG"] >= 1) & (df_partition["EC_nTG"] == 0),
#                 (df_partition["EC_TG"] >= 1) & (df_partition["EC_nTG"] >= 1),
#             ],
#             choicelist=[
#                 "absent",
#                 "singleton",
#                 "specific",
#                 "shared",
#             ],
#             default="None",
#         )
#         timing["OG_type"], t_i = time.monotonic() - t_i, time.monotonic()
#         df_partition["COG_TP"] = df_counts.eq(count_target).sum(axis=1) / len(
#             df_counts_in.columns
#         )
#         timing["COG_TP"], t_i = time.monotonic() - t_i, time.monotonic()
#         df_partition["COG_TP_TG"] = df_TG.eq(count_target).sum(axis=1) / len(TG)
#         timing["COG_TP_TG"], t_i = time.monotonic() - t_i, time.monotonic()
#         df_partition["COG_type_TG"] = df_TG.apply(
#             get_cog_type,
#             axis=1,
#             raw=True,
#             args=(
#                 count_target,
#                 count_min,
#                 count_max,
#                 count_fraction,
#             ),
#         )
#         timing["COG_type_TG"], t_i = time.monotonic() - t_i, time.monotonic()
#     t_i = time.monotonic()
#     df_partition["EC_mean"] = df_counts.mean(axis=1)
#     timing["EC_mean"], t_i = time.monotonic() - t_i, time.monotonic()
#     df_partition["EC_mean_TG"] = df_TG.mean(axis=1)
#     timing["EC_mean_TG"], t_i = time.monotonic() - t_i, time.monotonic()
#     df_partition["EC_mean_nTG"] = df_nTG.mean(axis=1)
#     timing["EC_mean_nTG"], t_i = time.monotonic() - t_i, time.monotonic()
#     df_partition["log2_mean(TG/nTG)"] = np.log2(
#         df_partition["EC_mean_TG"] / df_partition["EC_mean_nTG"]
#     )
#     timing["log2_mean(TG/nTG)"], t_i = time.monotonic() - t_i, time.monotonic()
#     df_partition["pvalue"] = scipy.stats.mannwhitneyu(
#         df_TG,
#         df_nTG,
#         method="asymptotic",
#         alternative="two-sided",
#         nan_policy="omit",
#         axis=1,
#         keepdims=False,
#     )[1]
#     timing["pvalue"], t_i = time.monotonic() - t_i, time.monotonic()
#     df_partition["EC_median"] = df_counts.median(axis=1, skipna=True)
#     timing["EC_median"], t_i = time.monotonic() - t_i, time.monotonic()
#     df_partition["EC_median_TG"] = df_TG.median(axis=1, skipna=True)
#     timing["EC_median_TG"], t_i = time.monotonic() - t_i, time.monotonic()
#     df_partition["EC_median_nTG"] = df_nTG.median(axis=1, skipna=True)
#     timing["EC_median_nTG"], t_i = time.monotonic() - t_i, time.monotonic()
#     # print(f"[partition] elapsed: {time.monotonic() - t_0}")
#     # pprint.pp(timing)
#     return df_partition[
#         [
#             "OG_type",
#             "SC",
#             "SC_TG",
#             "SP_TG",
#             "SC_nTG",
#             "SP_nTG",
#             "EC",
#             "EC_TG",
#             "EC_nTG",
#             "EC_mean",
#             "EC_mean_TG",
#             "EC_mean_nTG",
#             "log2_mean(TG/nTG)",
#             "pvalue",
#             "EC_median",
#             "EC_median_TG",
#             "EC_median_nTG",
#             "COG_type_TG",
#             "COG_TP",
#             "COG_TP_TG",
#         ]
#     ]


# def partition_old(df_counts, TG, nTG=[], metrics=True):
#     t_0 = time.monotonic()
#     nTG = tuple([TN for TN in df_counts.columns if TN not in TG]) if not nTG else nTG
#     df_TG = df_counts.loc[:, TG]
#     df_nTG = df_counts.loc[:, nTG]
#     df_partition = pd.DataFrame(index=df_counts.index)
#     timing = {}
#     if metrics is True:
#         t_i = time.monotonic()
#         # df_partition["SC"] = df_counts.mask(df_counts > 1, 1).sum(axis=1)
#         df_partition["SC"] = df_counts.mask(df_counts > 1, 1).sum(axis=1)
#         timing["SC"], t_i = time.monotonic() - t_i, time.monotonic()
#         df_partition["EC"] = df_counts.sum(axis=1)
#         timing["EC"], t_i = time.monotonic() - t_i, time.monotonic()
#         df_partition["SC_TG"] = df_TG.mask(df_TG > 1, 1).sum(axis=1)
#         timing["SC_TG"], t_i = time.monotonic() - t_i, time.monotonic()
#         df_partition["EC_TG"] = df_TG.sum(axis=1)
#         timing["EC_TG"], t_i = time.monotonic() - t_i, time.monotonic()
#         df_partition["SC_nTG"] = df_nTG.mask(df_nTG > 1, 1).sum(axis=1)
#         timing["SC_nTG"], t_i = time.monotonic() - t_i, time.monotonic()
#         df_partition["EC_nTG"] = df_nTG.sum(axis=1)
#         timing["EC_nTG"], t_i = time.monotonic() - t_i, time.monotonic()
#         df_partition["type"] = np.select(
#             condlist=[
#                 (df_partition["EC_TG"] == 0),
#                 (df_partition["EC"] == 1),
#                 (df_partition["EC_TG"] >= 1) & (df_partition["EC_nTG"] == 0),
#                 (df_partition["EC_TG"] >= 1) & (df_partition["EC_nTG"] >= 1),
#             ],
#             choicelist=[
#                 "absent",
#                 "singleton",
#                 "specific",
#                 "shared",
#             ],
#             default="None",
#         )
#         timing["type"], t_i = time.monotonic() - t_i, time.monotonic()
#         df_partition["COV_TG"] = df_partition["SC_TG"] / len(TG)
#         timing["COV_TG"], t_i = time.monotonic() - t_i, time.monotonic()
#         df_partition["COV_nTG"] = df_partition["SC_nTG"] / len(nTG)
#         timing["COV_nTG"], t_i = time.monotonic() - t_i, time.monotonic()

#         """
#         very costly
#         BUT consider: https://pandas.pydata.org/pandas-docs/stable/user_guide/text.html
#         """
#         # df_partition["TN_TG"] = (
#         #     df_TG.mask(
#         #         df_TG.mask(df_TG == 0, np.nan).notnull(),
#         #         df_TG.columns.to_series(),
#         #         axis=1,
#         #     )
#         #     .replace(0, "")
#         #     .astype(str)
#         #     .apply(",".join, axis=1)
#         #     .replace(r",+", ",", regex=True)
#         #     .replace(r"^,", "", regex=True)
#         #     .replace(r",$", "", regex=True)
#         #     .replace("", np.nan)
#         # )
#         """
#         very costly
#         BUT consider: https://pandas.pydata.org/pandas-docs/stable/user_guide/text.html
#         """
#         # df_partition["TN_nTG"] = (
#         #     df_nTG.mask(
#         #         df_nTG.mask(df_nTG == 0, np.nan).notnull(),
#         #         df_nTG.columns.to_series(),
#         #         axis=1,
#         #     )
#         #     .replace(0, "")
#         #     .astype(str)
#         #     .apply(",".join, axis=1)
#         #     .replace(r",+", ",", regex=True)
#         #     .replace(r"^,", "", regex=True)
#         #     .replace(r",$", "", regex=True)
#         #     .replace("", np.nan)
#         # )
#     df_partition["EC_mean"] = df_counts.replace(0, np.nan).mean(
#         skipna=True,  # dask does not like it
#         axis=1,
#     )
#     timing["EC_mean"], t_i = time.monotonic() - t_i, time.monotonic()
#     df_partition["EC_median"] = df_counts.replace(0, np.nan).median(
#         skipna=True,  # dask does not like it
#         axis=1,
#     )
#     timing["EC_median"], t_i = time.monotonic() - t_i, time.monotonic()
#     df_partition["EC_TG_mean"] = (
#         df_TG.mask(df_TG == 0, np.nan).mean(axis=1).replace(np.nan, 0.0)
#     )
#     timing["EC_TG_mean"], t_i = time.monotonic() - t_i, time.monotonic()
#     df_partition["EC_TG_median"] = df_TG.replace(0, np.nan).median(
#         skipna=True,  # dask does not like it
#         axis=1,
#     )
#     timing["EC_TG_median"], t_i = time.monotonic() - t_i, time.monotonic()
#     df_partition["EC_nTG_mean"] = (
#         df_nTG.mask(df_nTG == 0, np.nan).mean(axis=1).replace(np.nan, 0.0)
#     )
#     timing["EC_nTG_mean"], t_i = time.monotonic() - t_i, time.monotonic()
#     df_partition["EC_nTG_median"] = df_nTG.replace(0, np.nan).median(
#         skipna=True,  # dask does not like it
#         axis=1,
#     )
#     timing["EC_nTG_median"], t_i = time.monotonic() - t_i, time.monotonic()
#     with np.errstate(divide="ignore"):
#         mean_div = df_partition["EC_TG_mean"] / df_partition["EC_nTG_mean"]
#         df_partition["log2_mean(TG/nTG)"] = (
#             np.log2(mean_div).replace(-np.inf, np.nan).replace(np.inf, np.nan)
#         )
#     timing["log2_mean(TG/nTG)"], t_i = time.monotonic() - t_i, time.monotonic()
#     df_partition["pvalue"] = scipy.stats.mannwhitneyu(
#         df_TG.mask(df_TG == 0, np.nan),
#         df_nTG.mask(df_nTG == 0, np.nan),
#         alternative="two-sided",
#         nan_policy="omit",
#         axis=1,
#     )[1]
#     timing["pvalue"] = time.monotonic() - t_i
#     print(f"[partition] elapsed: {time.monotonic() - t_0}")
#     pprint.pp(timing)
#     return df_partition


# def partition_dask(df_counts_in, TG, nTG=[], metrics=True):
#     import dask.array.stats as dastats

#     t_0 = time.monotonic()
#     nTG = nTG if nTG else tuple([TN for TN in df_counts_in.columns if TN not in TG])
#     df_counts = df_counts_in.replace(0, np.nan)
#     df_counts = dd.from_pandas(df_counts, npartitions=10)
#     df_TG = df_counts.loc[:, TG]
#     df_nTG = df_counts.loc[:, nTG]
#     df_partition = dd.from_pandas(pd.DataFrame(index=df_counts.index), npartitions=10)
#     timing = {}
#     if metrics is True:
#         t_i = time.monotonic()
#         df_partition["SC"] = df_counts.count(axis=1)
#         timing["SC"], t_i = time.monotonic() - t_i, time.monotonic()
#         df_partition["SC_TG"] = df_TG.count(axis=1)
#         timing["SC_TG"], t_i = time.monotonic() - t_i, time.monotonic()
#         df_partition["SC_nTG"] = df_nTG.count(axis=1)
#         timing["SC_nTG"], t_i = time.monotonic() - t_i, time.monotonic()
#         df_partition["EC"] = df_counts.sum(axis=1).astype(int)
#         timing["EC"], t_i = time.monotonic() - t_i, time.monotonic()
#         df_partition["EC_TG"] = df_TG.sum(axis=1).astype(int)
#         timing["EC_TG"], t_i = time.monotonic() - t_i, time.monotonic()
#         df_partition["EC_nTG"] = df_nTG.sum(axis=1).astype(int)
#         timing["EC_nTG"], t_i = time.monotonic() - t_i, time.monotonic()
#         # df_partition["type"].apply(
#         #    func=np.select,
#         #    axis=1,
#         #    meta=df_partition,
#         #    args=(
#         #        [
#         #            (df_partition["EC_TG"] == 0),
#         #            (df_partition["EC"] == 1),
#         #            (df_partition["EC_TG"] >= 1) & (df_partition["EC_nTG"] == 0),
#         #            (df_partition["EC_TG"] >= 1) & (df_partition["EC_nTG"] >= 1),
#         #        ],
#         #        [
#         #            "absent",
#         #            "singleton",
#         #            "specific",
#         #            "shared",
#         #        ],
#         #        "None",
#         #    ),
#         # )
#         timing["type"], t_i = time.monotonic() - t_i, time.monotonic()
#         df_partition["COV_TG"] = df_partition["SC_TG"] / len(TG)
#         timing["COV_TG"], t_i = time.monotonic() - t_i, time.monotonic()
#         df_partition["COV_nTG"] = df_partition["SC_nTG"] / len(nTG)
#         timing["COV_nTG"], t_i = time.monotonic() - t_i, time.monotonic()
#     df_partition["EC_mean"] = df_counts.mean(axis=1)
#     timing["EC_mean"], t_i = time.monotonic() - t_i, time.monotonic()
#     df_partition["EC_median"] = df_counts.median(axis=1)
#     timing["EC_median"], t_i = time.monotonic() - t_i, time.monotonic()
#     df_partition["EC_TG_mean"] = df_TG.mean(axis=1)
#     timing["EC_TG_mean"], t_i = time.monotonic() - t_i, time.monotonic()
#     df_partition["EC_TG_median"] = df_TG.median(axis=1)
#     timing["EC_TG_median"], t_i = time.monotonic() - t_i, time.monotonic()
#     df_partition["EC_nTG_mean"] = df_nTG.mean(axis=1)
#     timing["EC_nTG_mean"], t_i = time.monotonic() - t_i, time.monotonic()
#     df_partition["EC_nTG_median"] = df_nTG.median(axis=1)
#     timing["EC_nTG_median"], t_i = time.monotonic() - t_i, time.monotonic()
#     df_partition["log2_mean(TG/nTG)"] = np.log2(
#         df_partition["EC_TG_mean"] / df_partition["EC_nTG_mean"]
#     )
#     timing["log2_mean(TG/nTG)"], t_i = time.monotonic() - t_i, time.monotonic()
#     # df_partition["pvalue"] = scipy.stats.mannwhitneyu(

#     pvalue = dastats.ttest_rel(
#         df_TG,
#         df_nTG,
#         # alternative="two-sided",
#         # nan_policy="omit",
#         axis=1,
#     )[1]
#     df_partition["pvalue"] = pvalue.compute()
#     timing["pvalue"] = time.monotonic() - t_i
#     df_partition.compute()
#     print(pvalue)
#     print(f"[partition] elapsed: {time.monotonic() - t_0}")
#     pprint.pprint(timing)
#     return df_partition


def dump(df, fn, fmt="tsv"):
    # t_0 = time.monotonic()
    if fmt == "parquet":
        fn = f"{fn}.{fmt}"
        # https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_parquet.html#pandas.DataFrame.to_parquet
        df.to_parquet(f"{fn}")
    elif fmt == "tsv":
        fn = f"{fn}.{fmt}"
        # https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_csv.html
        df.to_csv(fn, sep="\t", na_rep="NA")
    else:
        raise NotImplementedError
    # print(f"[dump] {fn} - elapsed: {time.monotonic() - t_0}")


class TaxonGroups:
    """
    shoud be able to yield analysis fodder
        partition()
        tuples of tuples are sortable (frozensets of frozensets are not)
        l = [
        (("A", "B", "C", "D"), ()),    name="all", vs="background" group="sample_ids", TG=["A", "B", "C", "D"], nTG=[] metrics=True
        (("A",), ("B", "C", "D")),     name="A", vs="background" group="sample_id", TG=["A"], nTG=[] metrics=True
        (("A",), ("B",)),              name="A", vs="B" group="sample_id", TG=["A"], nTG=["B"] metrics=False
        (("A",), ("C",)),              name="A", vs="C" group="sample_id", TG=["A"], nTG=["C"] metrics=False
        (("A",), ("D",)),              name="A", vs="D" group="sample_id", TG=["A"], nTG=["D"] metrics=False
        (("B",), ("A", "C", "D")),     name="B", vs="background" group="sample_id", TG=["B"], nTG=[] metrics=True
        (("B",), ("C",)),              name="B", vs="C" group="sample_id", TG=["B"], nTG=["C",] metrics=False
        (("B",), ("D",)),              name="B", vs="D" group="sample_id", TG=["B"], nTG=["D",] metrics=False
        (("C",), ("A", "B", "D")),     name="C", vs="background" group="sample_id", TG=["C"], nTG=[] metrics=True
        (("C",), ("D",)),              name="C", vs="D" group="sample_id", TG=["C"], nTG=["D"] metrics=False
        (("D",), ("A", "B", "C")),     name="D", vs="background" group="sample_id", TG=["D"], nTG=[] metrics=True
        #
        (("A", "D"), ("B", "C")),      name="group1", vs="background" group="hostplant_group", TG=["A", "D"] nTG=[] metrics=True
        (("A", "D"), ("B", "C")),      name="group1", vs="group2" group="hostplant_group", TG=["A", "D"] nTG=["B", "C"] metrics=False
        (("B", "C"), ("A", "D")),      name="group2", vs="background" group="hostplant_group", TG=["B", "C"] nTG=[] metrics=True
        #
        (("A", "D"), ("B", "C")),      name="class1", vs="background" group="hostplant_class", TG=["A", "D"] nTG=[] metrics=True
        (("A", "D"), ("B",)),          name="class1", vs="class2" group="hostplant_class", TG=["A", "D"] nTG=["B"] metrics=False
        (("A", "D"), ("C",)),          name="class1", vs="class3" group="hostplant_class", TG=["A", "D"] nTG=["C"] metrics=False
        (("B",), ("A", "C", "D")),     name="class2", vs="background" group="hostplant_class", TG=["B"] nTG=[] metrics=True
        (("B",), ("A", "C", "D")),     name="class2", vs="class3" group="hostplant_class", TG=["B"] nTG=["C"] metrics=False
        (("C",), ("A", "B", "D")),     name="class3", vs="background" group="hostplant_class", TG=["C"] nTG=[] metrics=True
        ]
        tuples of tuples are sortable (frozensets of frozensets are not)

        l = [(("A", "B", "C", "D"), ()),
            (("A",), ("B", "C", "D")),
            (("B",), ("A", "C", "D")),
            (("C",), ("A", "B", "D")),
            (("D",), ("A", "B", "C")),
            (("A", "D"), ("B", "C")),
            (("B", "C"), ("A", "D")),
            (("A", "D"), ("B", "C")),
            (("B",), ("A", "C", "D")),
            (("C",), ("A", "B", "D")),
        ]
        sorted(l)
        (('A',), ('B', 'C', 'D'))
        (('A', 'B', 'C', 'D'), ())
        (('A', 'D'), ('B', 'C'))
        (('A', 'D'), ('B', 'C')) *SKIP
        (('B',), ('A', 'C', 'D'))
        (('B',), ('A', 'C', 'D')) *SKIP
        (('B', 'C'), ('A', 'D'))
        (('C',), ('A', 'B', 'D'))
        (('C',), ('A', 'B', 'D')) *SKIP
        (('D',), ('A', 'B', 'C'))

            {"BoMor": frozenset(["BoMor"]), "BlaBla": frozenset(["BlaBla"]), "BooBoo": frozenset(["BooBoo"]), "BoMan": frozenset(["BoMan"]}

    """

    def __init__(self):
        pass


def get_taxon_plan(config_dicts):
    taxon_plan = collections.defaultdict(lambda: collections.defaultdict(list))
    taxon_plan["sample_ids"]["all"] = [
        record.get("sample_id", None) for record in config_dicts
    ]
    for record in config_dicts:
        sample_id = record.get("sample_id", None)
        for k, v in record.items():
            taxon_plan[k][v].append(sample_id)
    return taxon_plan


# def get_combinations1(taxon_plan, key):
#     b = [  # combinations between TGs (for pairwise-tests)
#         [*_] + [key, False]
#         for _ in sorted(itertools.combinations(taxon_plan[key].values(), 2))
#     ]
#     a = [
#         [_]
#         + [[__ for __ in taxon_plan["sample_ids"]["all"] if __ not in _]]
#         + [key, True]
#         for _ in taxon_plan[key].values()
#     ]
#     return sorted(a + b)


def get_combinations(taxon_plan, key):
    combinations = []
    for (label_1, TNs_1), (label_2, TNs_2) in sorted(
        itertools.combinations(taxon_plan[key].items(), 2)
    ):
        if not (label_1 == CONFIG_KEYWORD_MISSING) or not (
            label_2 == CONFIG_KEYWORD_MISSING
        ):
            if len(TNs_1) > CONFIG_MIN_SAMPLE_IDS or len(TNs_2) > CONFIG_MIN_SAMPLE_IDS:
                combinations.append(
                    (
                        tuple(sorted(TNs_1)),
                        tuple(sorted(TNs_2)),
                        tuple(
                            [
                                key,
                                label_1,
                                label_2,
                            ]
                        ),
                    )
                )
    for TNs_label, TNs in taxon_plan[key].items():
        TNs_remainder = [TN for TN in taxon_plan["sample_ids"]["all"] if TN not in TNs]
        combinations.append(
            (
                tuple(sorted(TNs)),
                tuple(sorted(TNs_remainder)),
                tuple(
                    [
                        key,
                        TNs_label,
                        "remainder",
                    ]
                ),
            )
        )
    return sorted(combinations)


@contextlib.contextmanager
def poolcontext(*args, **kwargs):
    pool = multiprocessing.Pool(*args, **kwargs)
    yield pool
    pool.terminate()


def do_partitions(
    taxon_groups,
    df_counts,
    count_target=1,
    count_min=0,
    count_max=2,
    count_fraction=0.75,
    single_file=False,
    cpus=1,
):
    t_0 = time.monotonic()
    if cpus > 1:
        with tqdm(
            total=len(taxon_groups), desc=PROGRESS_DESC, ncols=PROGRESS_NCOLS
        ) as t:
            args = [
                {"df_counts_in": df_counts.replace(0, np.nan), **taxon_group_instance}
                for taxon_group_instance in taxon_groups
            ]
            with poolcontext(processes=cpus) as pool:
                for _ in pool.imap_unordered(get_df_partition, args):
                    t.update()
    else:
        for taxon_group_instance in tqdm(
            taxon_groups,
            total=len(taxon_groups),
            desc=PROGRESS_DESC,
            ncols=PROGRESS_NCOLS,
        ):
            kwargs = {
                "df_counts_in": df_counts.replace(0, np.nan),
                **taxon_group_instance,
            }
            _ = get_df_partition(**kwargs)
    print(f"[do_partitions] - elapsed: {time.monotonic() - t_0}")


def get_sample_ids(
    config_dicts=[
        {"sample_id": "D", "hostplant_group": "group3", "hostplant_class": "class3"},
        {"sample_id": "E", "hostplant_group": "group3", "hostplant_class": "class1"},
        {"sample_id": "A", "hostplant_group": "group1", "hostplant_class": "class1"},
        {"sample_id": "B", "hostplant_group": "group2", "hostplant_class": "class2"},
        {"sample_id": "C", "hostplant_group": "group2", "hostplant_class": "class3"},
        {"sample_id": "F", "hostplant_group": "group1", "hostplant_class": "class1"},
        {"sample_id": "G", "hostplant_group": "group2", "hostplant_class": "class1"},
        {"sample_id": "H", "hostplant_group": "group4", "hostplant_class": "class4"},
    ],
):
    return sorted([d["sample_id"] for d in config_dicts])


def parse_config_dicts(config_fn):
    if config_fn.endswith(".json"):
        with open(config_fn, "r") as config_fh:
            config_data = json.load(config_fh)
            if config_data and "sample_id" in config_data[0]:
                print(f"[parse_config_dicts] found {len(config_data)} sample IDs")
            else:
                print(f"[parse_config_dicts] found {len(config_data)} sample IDs")
            return config_data


def get_taxongroups(
    config_dicts=[
        {"sample_id": "D", "hostplant_group": "group3", "hostplant_class": "class3"},
        {"sample_id": "E", "hostplant_group": "group3", "hostplant_class": "class1"},
        {"sample_id": "A", "hostplant_group": "group1", "hostplant_class": "class1"},
        {"sample_id": "B", "hostplant_group": "group2", "hostplant_class": "class2"},
        {"sample_id": "C", "hostplant_group": "group2", "hostplant_class": "class3"},
        {"sample_id": "F", "hostplant_group": "group1", "hostplant_class": "class1"},
        {"sample_id": "G", "hostplant_group": "group2", "hostplant_class": "class1"},
        {"sample_id": "H", "hostplant_group": "group4", "hostplant_class": "class4"},
    ],
):
    t_0 = time.monotonic()
    taxon_plan = get_taxon_plan(config_dicts)
    combinations = []
    for k in taxon_plan:
        combinations += get_combinations(taxon_plan, k)
    temp = collections.defaultdict(list)
    for combination in sorted(combinations):
        temp[(combination[0], combination[1])].append(combination[2])
    print(f"[get_taxongroups] - elapsed: {time.monotonic() - t_0}")
    return [
        {"TG_1": TG_1, "TG_2": TG_2, "labels": labels}
        for (TG_1, TG_2), labels in temp.items()
    ]


#
#
#
#    if config_f.endswith(".json"):
#        if not taxon_idx_mapping_file:
#            raise ValueError("[ERROR] - taxon_idx_mapping not present")
#
#        with (
#            open(taxon_idx_mapping_file, "r") as f_mapping,
#            open(config_f, "r") as f_config,
#        ):
#            taxon_idx_mapping = json.load(f_mapping)
#            config_data = json.load(f_config)
#            headers = ["IDX"] + list(config_data[0].keys())
#            yield "#" + ",".join(headers)
#
#            for item in config_data:
#                idx = taxon_idx_mapping[item.get("taxon") or item.get("TAXON")]
#                row = [idx] + [item[key] for key in headers[1:]]
#                yield ",".join(row)
#    else:
#        yield from yield_file_lines(config_f)
#
#    return
#
#
#        logger.info("[STATUS] - Parsing config data ...")
#        attributes: List[str] = []
#        level_by_attribute_by_proteome_id: Dict[str, Dict[str, str]] = {}
#        proteomes: Set[str] = set()
#        proteome_id_by_species_id: Dict[str, str] = {}
#
#        taxon_idx = None
#        for line in yield_config_lines(config_f, taxon_idx_mapping_file):
#            if line.startswith("#"):
#                if not attributes:
#                    attributes = [x.strip() for x in line.lstrip("#").split(",")]
#                    if attributes[0].upper() != "IDX" or "TAXON" not in [
#                        a.upper() for a in attributes
#                    ]:
#                        error_msg = f"[ERROR] - Header must contain IDX and TAXON.\n\t{attributes}"
#                        logger.info(error_msg)
#                        raise ValueError(error_msg)
#                    taxon_idx = [a.upper() for a in attributes].index("TAXON")
#            elif line.strip():
#                temp = line.split(",")
#
#                if len(temp) != len(attributes):
#                    error_msg = f"[ERROR] - number of columns in line differs from header\n\t{attributes}\n\t{temp}"
#                    logger.info(error_msg)
#                    raise ValueError(error_msg)
#
#                proteome_id = temp[taxon_idx]
#                species_id = temp[0]
#
#                if proteome_id in proteomes:
#                    error_msg = f"[ERROR] - 'TAXON' should be unique. {species_id} was encountered multiple times"
#                    logger.info(error_msg)
#                    raise ValueError(error_msg)
#
#                proteomes.add(proteome_id)
#                proteome_id_by_species_id[species_id] = proteome_id
#
#                level_by_attribute_by_proteome_id[proteome_id] = dict(
#                    zip(attributes, temp)
#                )
#                level_by_attribute_by_proteome_id[proteome_id]["all"] = "all"
#        attributes.insert(0, "all")  # append to front
#        return (
#            proteomes,
#            proteome_id_by_species_id,
#            attributes,
#            level_by_attribute_by_proteome_id,
#        )
#    except Exception as e:
#        logger.error(f"[ERROR] - {e}")


"""
>>> import playground; x = playground.parse_df_orthogroups("../input/Orthogroups.txt"); y = playground.get_df_counts(x); z = playground.partition(y, TG=("BMALA","DMEDI","LOA1","LOA2","OVOLV","WBANC1","WBANC2"), nTG=("CELEG", "CBRIG")); playground.dump(df=z, prefix="test.nematodes")
[parse_df_orthogroups] elapsed: 0.09144604206085205
[get_df_counts] elapsed: 0.03920049965381622
[partition] elapsed: 1.1045369999483228
[dump] elapsed: 0.12420045863837004

>>> import playground; x = playground.parse_df_orthogroups("/Users/dom/git/kinfin_.test_data/leps/lepidoptera_orthodb_input/Orthogroups.txt"); y = playground.get_df_counts(x); z1 = playground.partition(y, TG=["AbTri", "AbTri1", "XeXan", "YpPlu", "ZeHep", "ArAge1"]); z2 = playground.partition_alt(y, TG=["AbTri", "AbTri1", "XeXan", "YpPlu", "ZeHep", "ArAge1"]) 
[parse_df_orthogroups] elapsed: 1.924696832895279
[get_df_counts] elapsed: 0.9458670830354095
[partition] elapsed: 2.455597166903317
[dump] elapsed: 0.16683591669425368



# length
# TG = "samples"
import playground; x = playground.get_lengths("/Users/dom/git/kinfin_.test_data/advanced/input/fastas"); z = playground.parse_df_orthogroups("../input/Orthogroups.txt"); playground.partition_lengths(z, x, TGs={"CBRIG": ("CBRIG",), "DMEDI": ("DMEDI",), "LSIGM": ("LSIGM",), "AVITE": ("AVITE",), "CELEG": ("CELEG",), "EELAP": ("EELAP",), "OOCHE2": ("OOCHE2",), "OFLEX": ("OFLEX",), "LOA2": ("LOA2",), "SLABI": ("SLABI",), "BMALA": ("BMALA",), "DIMMI": ("DIMMI",), "WBANC2": ("WBANC2",), "TCALL": ("TCALL",), "OOCHE1": ("OOCHE1",), "BPAHA": ("BPAHA",), "OVOLV": ("OVOLV",), "WBANC1": ("WBANC1",),  "LOA1": ("LOA1",)})
# TG = "host""
import playground; x = playground.get_lengths("/Users/dom/git/kinfin_.test_data/advanced/input/fastas"); z = playground.parse_df_orthogroups("../input/Orthogroups.txt"); playground.partition_lengths(z, x, TGs={"outgroup": ("CBRIG","CELEG"), "human": ("DMEDI", "LOA2", "BMALA", "WBANC2", "OVOLV", "WBANC1", "LOA1"), "other": ("LSIGM", "AVITE", "EELAP", "OOCHE2", "OFLEX", "SLABI", "DIMMI", "TCALL", "OOCHE1", "BPAHA")})

"""
