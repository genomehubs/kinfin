import collections
import contextlib
import datetime
import itertools
import json
import math
import multiprocessing
import os
import sys
import time
import traceback
import uuid

import ete4
import numpy as np
import pandas as pd
import scipy
from tqdm import tqdm

import log
from utils import dump, load

"""
[ToDo]
- parse multicolumn TABLE_FN
- load taxonomy db
- expand config data with taxonomy
"""

UUID = uuid.uuid4()

TIMESTAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

LOG_DIR = "log"
[get_tree][get_tree]
ode=0o775, exist_ok=True)

logger = log.init_logger(f"{LOG_DIR}/kinfin")
# logging.basicConfig(
#     filename=f"{LOG_DIR}/kinfin.log",
#     level=logging.DEBUG,
#     format="[%(asctime)s] [%(levelname)-7s] [%(funcName)s] - %(message)s",
#     stream=sys.stdout,
# )


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


@contextlib.contextmanager
def poolcontext(*args, **kwargs):
    pool = multiprocessing.Pool(*args, **kwargs)
    yield pool
    pool.terminate()


"""

[ToDo]
- parse multicolumn TABLE_FN
- think about whether to support other ways of linking element_id <-> sample_id (beside name-prefix)?
[###] filenames vs pathlib-objects
- use pathlib only for intial CLI args to get absolute paths easily
- filename-strings are better for being passed to processes

[###] Parquet/Feather:
- just needs a script for converting to TSV on demand for CLI ninjas
- storage_options: data can be accessed via storeage connection (host, port, username, password, etc)
- parquet smaller files, feather faster read/write (both smaller/faster than CSV)

[###] CONFIG_MISSING_KEYWORD
- sample IDs are NOT included in between-label comparisons
- sample IDs are NOT included in label-remainder comparisons

## 5) cpu=10, dumping feather (twice the filesize of parquet)
>>> import playground; d = playground.parse_config_dicts(config_fn="/Users/dom/git/kinfin_.test_data/leps/lepidoptera_orthodb_input/config.DRL.json"); s = playground.get_sample_ids(config_dicts=d); t = playground.get_tasks(config_dicts=d); o = playground.parse_df_orthogroups("/Users/dom/git/kinfin_.test_data/leps/lepidoptera_orthodb_input/Orthogroups.txt", sample_ids=s); c = playground.get_df_counts(o); playground.do_partitions(t, c, cpus=10)
[parse_config_dicts] found 277 sample IDs
[get_tasks] - elapsed: 0.04131950018927455
[parse_df_orthogroups] parsing 277 samples from '/Users/dom/git/kinfin_.test_data/leps/lepidoptera_orthodb_input/Orthogroups.txt'
[parse_df_orthogroups] removing 114 sample id(s)
[parse_df_orthogroups] removed 1779990 element ids
[parse_df_orthogroups] elapsed: 2.2576219998300076
[get_df_counts] elapsed: 0.6623496250249445
[partitioning] progress: 100% 300/300 [01:33<00:00,  3.22it/s]
[do_partitions] - elapsed: 93.39043124997988

## 4) cpu=10, dumping parquet
>>> import playground; d = playground.parse_config_dicts(config_fn="/Users/dom/git/kinfin_.test_data/leps/lepidoptera_orthodb_input/config.DRL.json"); s = playground.get_sample_ids(config_dicts=d); t = playground.get_tasks(config_dicts=d); o = playground.parse_df_orthogroups("/Users/dom/git/kinfin_.test_data/leps/lepidoptera_orthodb_input/Orthogroups.txt", sample_ids=s); c = playground.get_df_counts(o); playground.do_partitions(t, c, cpus=10)
[parse_config_dicts] found 277 sample IDs
[get_tasks] - elapsed: 0.03889633296057582
[parse_df_orthogroups] parsing 277 samples from '/Users/dom/git/kinfin_.test_data/leps/lepidoptera_orthodb_input/Orthogroups.txt'
[parse_df_orthogroups] removing 114 sample id(s)
[parse_df_orthogroups] removed 1779990 element ids
[parse_df_orthogroups] elapsed: 2.3385556247085333
[get_df_counts] elapsed: 0.6820082077756524
[partitioning] progress: 100% 300/300 [01:42<00:00,  2.93it/s]
[do_partitions] - elapsed: 102.70711329113692

## 3) cpu=10, only loading needed parquet columns
>>> import playground; d = playground.parse_config_dicts(config_fn="/Users/dom/git/kinfin_.test_data/leps/lepidoptera_orthodb_input/config.DRL.json"); s = playground.get_sample_ids(config_dicts=d); t = playground.get_tasks(config_dicts=d); o = playground.parse_df_orthogroups("/Users/dom/git/kinfin_.test_data/leps/lepidoptera_orthodb_input/Orthogroups.txt", sample_ids=s); c = playground.get_df_counts(o); playground.do_partitions(t, c, cpus=10)
[parse_config_dicts] found 277 sample IDs
[get_tasks] - elapsed: 0.0388367916457355
[parse_df_orthogroups] parsing 277 samples from '/Users/dom/git/kinfin_.test_data/leps/lepidoptera_orthodb_input/Orthogroups.txt'
[parse_df_orthogroups] removing 114 sample id(s)
[parse_df_orthogroups] removed 1779990 element ids
[parse_df_orthogroups] elapsed: 2.257474333047867
[get_df_counts] elapsed: 0.6834029997698963
[partitioning] progress: 100% 300/300 [01:54<00:00,  2.63it/s]
[do_partitions] - elapsed: 114.41555749997497

## 2) cpu=10, passing parquet fn (~600Mb memory per process)
[ToDo] parquets should be stored in tmp folder (needs management)
>>> import playground; d = playground.parse_config_dicts(config_fn="/Users/dom/git/kinfin_.test_data/leps/lepidoptera_orthodb_input/config.DRL.json"); s = playground.get_sample_ids(config_dicts=d); t = playground.get_tasks(config_dicts=d); o = playground.parse_df_orthogroups("/Users/dom/git/kinfin_.test_data/leps/lepidoptera_orthodb_input/Orthogroups.txt", sample_ids=s); c = playground.get_df_counts(o); playground.do_partitions(t, c, cpus=10)
[parse_config_dicts] found 277 sample IDs
[get_tasks] - elapsed: 0.028689791914075613
[parse_df_orthogroups] parsing 277 samples from '/Users/dom/git/kinfin_.test_data/leps/lepidoptera_orthodb_input/Orthogroups.txt'
[parse_df_orthogroups] removing 114 sample id(s)
[parse_df_orthogroups] removed 1779990 element ids
[parse_df_orthogroups] elapsed: 2.4066978748887777
[get_df_counts] elapsed: 0.701802917290479
[partitioning] progress: 100% 300/300 [01:58<00:00,  2.53it/s]
[do_partitions] - elapsed: 119.09221495781094

## 1) cpu=10, passing df_counts directly (30Gb memory)
>>> import playground; d = playground.parse_config_dicts(config_fn="/Users/dom/git/kinfin_.test_data/leps/lepidoptera_orthodb_input/config.DRL.json"); s = playground.get_sample_ids(config_dicts=d); t = playground.get_tasks(config_dicts=d); o = playground.parse_df_orthogroups("/Users/dom/git/kinfin_.test_data/leps/lepidoptera_orthodb_input/Orthogroups.txt", sample_ids=s); c = playground.get_df_counts(o); playground.do_partitions(t, c, cpus=10)
[parse_config_dicts] found 277 sample IDs
[get_tasks] - elapsed: 0.042544500436633825
[parse_df_orthogroups] parsing 277 samples from '/Users/dom/git/kinfin_.test_data/leps/lepidoptera_orthodb_input/Orthogroups.txt'
[parse_df_orthogroups] removing 114 sample id(s)
[parse_df_orthogroups] removed 1779990 element ids
[parse_df_orthogroups] elapsed: 2.3214567499235272
[get_df_counts] elapsed: 0.6666769157163799
[partitioning] progress: 100% 300/300 [03:14<00:00,  1.54it/s]
[do_partitions] - elapsed: 194.66630054125562
"""


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
    logger.info(f"elapsed: {time.monotonic() - t_0}")
    return df_nodes


def parse_df_orthogroups(orthogroup_fn, sample_ids=[]):
    t_0 = time.monotonic()
    # [TBD] how to establish element_id <-> sample_id?
    logger.info(f"parsing {len(sample_ids)} samples from '{orthogroup_fn}'")
    data = []
    with open(orthogroup_fn) as orthogroup_fh:
        for line in orthogroup_fh:
            temp = line.rstrip("\n").split(" ")
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
    logger.warning(f"removing {len(sample_ids_to_remove)} sample id(s)")
    mask = df_orthogroups["sample_id"].isin(sample_ids)
    logger.warning(f"removed {mask.value_counts()[False]} element ids")
    df_orthogroups = df_orthogroups[mask]
    if df_orthogroups.empty:
        logger.error(f"none of these sample IDs were found: {', '.join(sample_ids)}")
        sys.exit(1)
    sample_ids_present = set(df_orthogroups["sample_id"].unique())
    sample_ids_missing = [
        sample_id for sample_id in sample_ids if sample_id not in sample_ids_present
    ]
    if sample_ids_missing:
        logger.error(f"[parse_df_orthogroups] {sample_ids_missing=}")
        sys.exit(1)
    logger.info(f"[parse_df_orthogroups] elapsed: {time.monotonic() - t_0}")
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
    logger.info(f"elapsed: {time.monotonic() - t_0}")
    return df_counts


def partition_lengths(df_orthogroups, lengths, TGs={}):
    # [ToDo]
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
        dfs.append(
            df_orthogroups.where(df_orthogroups["sample_id"].isin(TNs))
            .groupby("orthogroup_id")
            .agg(TG_EL_mean=("length", "mean"), TG_EL_sd=("length", "std"))
            .rename(columns={"TG_EL_mean": f"{TG}_EL_mean", "TG_EL_sd": f"{TG}_EL_sd"})
        )
    df_lengths = pd.concat(dfs, axis=1).reindex(dfs[0].index)
    logger.info(f"elapsed: {time.monotonic() - t_0}")
    return df_lengths


def get_df_entropy(df_orthogroups, df_interpro, df_counts, analysis="Pfam"):

    def infer_entropy(values):
        signature_counter = collections.Counter([v for k, v in values.items()])
        return -sum(
            [
                i / signature_counter.total() * math.log2(i / signature_counter.total())
                for i in list(signature_counter.values())
            ]
        )

    def glue_strings(values):
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
                    aggfunc=infer_entropy,
                ),
                f"{analysis}_ids": pd.NamedAgg(
                    column="signature_id",
                    aggfunc=glue_strings,
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
                    aggfunc=infer_entropy,
                ),
                "interpro_ids": pd.NamedAgg(
                    column="signature_id",
                    aggfunc=glue_strings,
                ),
                "go_entropy": pd.NamedAgg(
                    column="go_annotation",
                    aggfunc=infer_entropy,
                ),
                "go_ids": pd.NamedAgg(
                    column="go_annotation",
                    aggfunc=glue_strings,
                ),
            }
        )
        .set_index("orthogroup_id")
    )
    df_entropy[f"{analysis}_TN_COV"] /= df_counts.ge(1).sum(axis=1)
    df_entropy[f"{analysis}_EC_COV"] /= df_counts.sum(axis=1)
    logger.info(f"elapsed: {time.monotonic() - t_0}")
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
    df_interpro = load(
        "/Users/dom/git/kinfin_.test_data/advanced/input/kinfin.interproscan.tsv",
        sep="\t",
        columns=[
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
        logger.warning(
            f"Found {annotations_orphan_count} annotation(s) of sequences which are not part of any Orthogroup. Will be ignored ..."
        )
        dump(df_interpro[~annotations_valid], f"{fn}.orphan")
        dump(df_interpro[annotations_valid], f"{fn}.filtered")
    logger.info(f"elapsed: {time.monotonic() - t_0}")
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
    logger.info(f"[elapsed: {time.monotonic() - t_0}")
    return df_annotation[
        [
            "EC",
            "EC_AC",
            "EC_AP",
            "TN_AP",
            "EC_AP_TN",
        ]
    ]


def infer_cog_type(values, count_target, count_min, count_max, count_fraction):
    if np.all(values == count_target):
        return "true"  # [ToDo] better name?
    elif np.mean((values >= count_min) & (values <= count_max)) >= count_fraction:
        return "fuzzy"
    else:
        return "false"  # [ToDo] better name?


def make_df_partition(
    *args,
    **kwargs,
):
    kwargs = kwargs if kwargs else args[0]
    TG_1 = kwargs.get("TG_1", [])
    TG_2 = kwargs.get("TG_2", [])
    labels = kwargs.get("labels", {})
    count_target = kwargs.get("count_target", 1)
    count_min = kwargs.get("count_min", 0)
    count_max = (kwargs.get("count_max", 2),)
    count_fraction = kwargs.get("count_fraction", 0.75)
    no_redundancy = kwargs.get("no_redundancy", False)
    output_fmt = kwargs.get("output_fmt", "parquet")
    df_counts = load(
        fn=kwargs.get("df_counts_fn", None),
        columns=sum([TG_1, TG_2], ()),
    )
    df_counts_TG1 = df_counts.loc[:, TG_1]
    df_counts_TG2 = df_counts.loc[:, TG_2]
    df_partition = pd.DataFrame(index=df_counts.index)
    df_partition["SC"] = df_counts.ge(1).sum(axis=1)  # .ge() >> .mask()
    df_partition["SC_TG1"] = df_counts_TG1.ge(1).sum(axis=1)  # .ge() >> .mask()
    df_partition["SP_TG1"] = df_partition["SC_TG1"] / len(TG_1)
    df_partition["SC_TG2"] = df_counts_TG2.ge(1).sum(axis=1)  # .ge() >> .mask()
    df_partition["SP_TG2"] = df_partition["SC_TG2"] / len(TG_2)
    df_partition["EC"] = df_counts.sum(axis=1).astype(int)
    df_partition["EC_TG1"] = df_counts_TG1.sum(axis=1).astype(int)
    df_partition["EC_TG2"] = df_counts_TG2.sum(axis=1).astype(int)
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
    df_partition["COG_TP"] = df_counts.eq(count_target).sum(axis=1) / len(
        df_counts.columns
    )
    df_partition["COG_TP_TG1"] = df_counts_TG1.eq(count_target).sum(axis=1) / len(TG_1)
    df_partition["COG_type_TG1"] = df_counts_TG1.apply(
        infer_cog_type,
        axis=1,
        raw=True,
        args=(
            count_target,
            count_min,
            count_max,
            count_fraction,
        ),
    )
    df_partition["EC_mean"] = df_counts.mean(axis=1)
    df_partition["EC_mean_TG1"] = df_counts_TG1.mean(axis=1)
    df_partition["EC_mean_TG2"] = df_counts_TG2.mean(axis=1)
    df_partition["log2_mean(TG1/TG2)"] = np.log2(
        df_partition["EC_mean_TG1"] / df_partition["EC_mean_TG2"]
    )
    df_partition["pvalue"] = scipy.stats.mannwhitneyu(
        df_counts_TG1,
        df_counts_TG2,
        method="asymptotic",
        alternative="two-sided",
        nan_policy="omit",
        axis=1,
        keepdims=False,
    )[1]
    df_partition["EC_median"] = df_counts.median(axis=1, skipna=True)
    df_partition["EC_median_TG1"] = df_counts_TG1.median(axis=1, skipna=True)
    df_partition["EC_median_TG2"] = df_counts_TG2.median(axis=1, skipna=True)
    for grouping, TG1_label, TG2_label in labels:
        dump(
            df_partition,
            prefix=f"partition.{grouping}.{TG1_label}_vs_{TG2_label}",
            fmt=output_fmt,
        )
        if no_redundancy:
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


def do_partitions(
    taxon_groups,
    df_counts,
    count_target=1,
    count_min=0,
    count_max=2,
    count_fraction=0.75,
    no_redundancy=False,
    output_fmt="feather",
    cpus=1,
    threads=1,
):
    t_0 = time.monotonic()
    df_counts_fn = dump(
        df_counts.replace(0, np.nan),
        prefix="df_counts_in",
        fmt=output_fmt,  #
    )
    payloads = [
        {
            "df_counts_fn": df_counts_fn,
            "count_target": count_target,
            "count_min": count_min,
            "count_max": count_max,
            "count_fraction": count_fraction,
            "no_redundancy": False,
            "output_fmt": output_fmt,
            **taxon_group_instance,
        }
        for taxon_group_instance in taxon_groups
    ]
    if cpus > 1:
        with tqdm(
            total=len(taxon_groups), desc=PROGRESS_DESC, ncols=PROGRESS_NCOLS
        ) as t:
            args = payloads
            with poolcontext(processes=cpus) as pool:
                for _ in pool.imap_unordered(make_df_partition, args):
                    t.update()
    else:
        for payload in tqdm(
            payloads,
            total=len(payloads),
            desc=PROGRESS_DESC,
            ncols=PROGRESS_NCOLS,
        ):
            _ = make_df_partition(**payload)
    logger.info(f"elapsed: {time.monotonic() - t_0}")


################### [INPUT] ###################


def parse_config_dicts(config_fn):
    if config_fn.endswith(".json"):
        with open(config_fn, "r") as config_fh:
            config_data = json.load(config_fh)
    elif config_fn.endswith(".csv"):
        config_data = (
            load(config_fn).to_dict(orient="records")
            # .drop(labels=["#IDX"], axis=1)  # [LEGACY-SUPPORT]
            # .rename(
            #     columns={
            #         "taxon": "sample_id",  # [LEGACY-SUPPORT]
            #         "TAXON": "sample_id",  # [LEGACY-SUPPORT]
            #     }
            # )
            # .to_dict(orient="records")
        )
    else:
        extension = config_fn.split(".")[-1]
        logger.error(f"unknown file format extension: {extension}")
        sys.exit(1)
    if not config_data or "sample_id" not in config_data[0]:
        logger.error("error reading config")
        sys.exit(1)
    if "taxid" in config_data[0]:
        pass
    logger.info(f"found {len(config_data)} sample IDs")
    return config_data


def get_taxongroups(config_dicts):
    t_0 = time.monotonic()
    taxon_plan = get_taxon_plan(config_dicts)
    combinations = []
    for k in taxon_plan:
        combinations += get_combinations(taxon_plan, k)
    temp = collections.defaultdict(list)
    for combination in sorted(combinations):
        temp[(combination[0], combination[1])].append(combination[2])
    logger.info(f"elapsed: {time.monotonic() - t_0}")
    return [
        {
            "TG_1": TG_1,
            "TG_2": TG_2,
            "labels": labels,
        }
        for (TG_1, TG_2), labels in temp.items()
    ]


def get_sample_ids(config_dicts):
    try:
        return sorted([d["sample_id"] for d in config_dicts])
    except Exception:
        logger.error("not a valid config file.")
        sys.exit(1)


def get_groupings(config_dicts):
    group_labels = collections.defaultdict(list)
    group_labels["sample_ids"].append("all")
    for group_category in list(config_dicts[0].keys()):
        for config_dict in config_dicts:
            group_labels[group_category].append(config_dict[group_category])
        group_labels[group_category] = sorted(set(group_labels[group_category]))
    return group_labels


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


def get_tree(tree_fn, outgroup=[]):
    t = ete4.Tree(tree_fn)
    if outgroup:
        try:
            t.set_outgroup(t.common_ancestor(outgroup))
        except ete4.core.tree.TreeError as exc:
            logger.error(
                f"setting outgroup to {outgroup} - {exc}\n{traceback.format_exc()}"
            )
    for idx, node in enumerate(t.traverse("levelorder")):
        node.add_prop("node_id", node.name if node.name else f"n{idx}")
    return t


if __name__ == "__main__":
    parse_config_dicts(config_fn="/Users/dom/git/kinfin2/test/config.leps.json")

# def partition_bck(
#     *args,
#     **kwargs,
# ):
#     kwargs = kwargs if kwargs else args[0]
#     if kwargs["labels"][0][0] == "compare":
#         return False
#     TG_1, TG_2 = kwargs["TGs"]
#     labels = kwargs["labels"]
#     count_target = kwargs["count_target"]
#     count_min = kwargs["count_min"]
#     count_max = kwargs["count_max"]
#     count_fraction = kwargs["count_fraction"]
#     output_fmt = kwargs["output_fmt"]
#     output_dir = kwargs["output_dir"]
#     df_counts = core.utils.load(
#         fn=kwargs["df_counts_fn"],
#         columns=sum([("orthogroup_id",), TG_1, TG_2], ()),
#     ).set_index("orthogroup_id")
#     df_counts_TG1 = df_counts.loc[:, TG_1]
#     df_counts_TG2 = df_counts.loc[:, TG_2]
#     df_partition = pd.DataFrame()
#     df_partition["SC"] = df_counts.ge(1).sum(axis=1)  # .ge() >> .mask()
#     df_partition["SC_TG1"] = df_counts_TG1.ge(1).sum(axis=1)  # .ge() >> .mask()
#     df_partition["SP_TG1"] = df_partition["SC_TG1"] / len(TG_1)
#     df_partition["SC_TG2"] = df_counts_TG2.ge(1).sum(axis=1)  # .ge() >> .mask()
#     df_partition["SP_TG2"] = df_partition["SC_TG2"] / len(TG_2)
#     df_partition["EC"] = df_counts.sum(axis=1).astype(int)
#     df_partition["EC_TG1"] = df_counts_TG1.sum(axis=1).astype(int)
#     df_partition["EC_TG2"] = df_counts_TG2.sum(axis=1).astype(int)
#     df_partition["OG_type"] = np.select(
#         condlist=[
#             (df_partition["EC_TG1"] == 0),
#             (df_partition["EC"] == 1),
#             (df_partition["EC_TG1"] >= 1) & (df_partition["EC_TG2"] == 0),
#             (df_partition["EC_TG1"] >= 1) & (df_partition["EC_TG2"] >= 1),
#         ],
#         choicelist=[
#             "absent",
#             "singleton",
#             "specific",
#             "shared",
#         ],
#         default="None",
#     )
#     df_partition["COG_TP"] = df_counts.eq(count_target).sum(axis=1) / len(
#         df_counts.columns
#     )
#     df_partition["COG_TP_TG1"] = df_counts_TG1.eq(count_target).sum(axis=1) / len(TG_1)
#     df_partition["COG_type_TG1"] = df_counts_TG1.apply(
#         infer_cog_type,
#         axis=1,
#         raw=True,
#         args=(
#             count_target,
#             count_min,
#             count_max,
#             count_fraction,
#         ),
#     )
#     df_partition["EC_mean"] = df_counts.mean(axis=1)
#     df_partition["EC_mean_TG1"] = df_counts_TG1.mean(axis=1)
#     df_partition["EC_mean_TG2"] = df_counts_TG2.mean(axis=1)
#     df_partition["log2_mean(TG1/TG2)"] = np.log2(
#         df_partition["EC_mean_TG1"] / df_partition["EC_mean_TG2"]
#     )
#     df_partition["pvalue"] = scipy.stats.mannwhitneyu(
#         df_counts_TG1,
#         df_counts_TG2,
#         method="asymptotic",
#         alternative="two-sided",
#         nan_policy="omit",
#         axis=1,
#         keepdims=False,
#     )[1]
#     df_partition["EC_median"] = df_counts.median(axis=1, skipna=True)
#     df_partition["EC_median_TG1"] = df_counts_TG1.median(axis=1, skipna=True)
#     df_partition["EC_median_TG2"] = df_counts_TG2.median(axis=1, skipna=True)
#     df_partition = df_partition[
#         [
#             "OG_type",
#             "SC",
#             "SC_TG1",
#             "SP_TG1",
#             "SC_TG2",
#             "SP_TG2",
#             "EC",
#             "EC_TG1",
#             "EC_TG2",
#             "EC_mean",
#             "EC_mean_TG1",
#             "EC_mean_TG2",
#             "log2_mean(TG1/TG2)",
#             "pvalue",
#             "EC_median",
#             "EC_median_TG1",
#             "EC_median_TG2",
#             "COG_type_TG1",
#             "COG_TP",
#             "COG_TP_TG1",
#         ]
#     ]
#     for _, grouping, TG1_label, TG2_label in labels:
#         fn = f"partition.{grouping}.{TG1_label}_vs_{TG2_label}"
#         # sample_ids file
#         core.utils.dump(
#             pd.DataFrame.from_records(
#                 [{"TG": "1", "sample_id": TN, "label": TG1_label} for TN in TG_1]
#                 + [{"TG": "2", "sample_id": TN, "label": TG2_label} for TN in TG_2]
#             ),
#             fn=core.utils.format_fn(
#                 fn=(f"{fn}.sample_ids.tsv"),
#                 prefix=output_dir / grouping,
#             ),
#             verbose=False,
#             index=False,
#         )
#         # comparisons file
#         core.utils.dump(
#             df_partition.reset_index(),
#             fn=core.utils.format_fn(
#                 fn=(f"{fn}.comparisons.{output_fmt}"),
#                 prefix=output_dir / grouping,
#             ),
#             verbose=False,
#             index=False,
#         )

#     return True

# def partition_dict(
#     *args,
#     **kwargs,
# ):
#     kwargs = kwargs if kwargs else args[0]
#     if kwargs["labels"][0][0] == "compare":
#         return False
#     TG_1, TG_2 = kwargs["TGs"]
#     labels = kwargs["labels"]
#     count_target = kwargs["count_target"]
#     count_min = kwargs["count_min"]
#     count_max = kwargs["count_max"]
#     count_fraction = kwargs["count_fraction"]
#     output_fmt = kwargs["output_fmt"]
#     output_dir = kwargs["output_dir"]
#     df_counts = core.utils.load(
#         fn=kwargs["df_counts_fn"],
#         columns=sum([("orthogroup_id",), TG_1, TG_2], ()),
#     ).set_index("orthogroup_id")
#     df_counts_TG1 = df_counts.loc[:, TG_1]
#     df_counts_TG2 = df_counts.loc[:, TG_2]
#     df_partition = pd.DataFrame(
#         {
#             "SC": df_counts.ge(1).sum(axis=1),  # .ge() >> .mask()
#             "SC_TG1": df_counts_TG1.ge(1).sum(axis=1),  # .ge() >> .mask()
#             "SC_TG2": df_counts_TG2.ge(1).sum(axis=1),  # .ge() >> .mask()
#             "SP_TG1": df_counts_TG1.ge(1).sum(axis=1) / len(TG_1),
#             "SP_TG2": df_counts_TG2.ge(1).sum(axis=1) / len(TG_2),
#             "EC": df_counts.sum(axis=1).astype(int),
#             "EC_TG1": df_counts_TG1.sum(axis=1).astype(int),
#             "EC_TG2": df_counts_TG2.sum(axis=1).astype(int),
#             "COG_TP": df_counts.eq(count_target).sum(axis=1) / len(df_counts.columns),
#             "COG_TP_TG1": df_counts_TG1.eq(count_target).sum(axis=1) / len(TG_1),
#             "COG_type_TG1": df_counts_TG1.apply(
#                 infer_cog_type,
#                 axis=1,
#                 raw=True,
#                 args=(
#                     count_target,
#                     count_min,
#                     count_max,
#                     count_fraction,
#                 ),
#             ),
#             "EC_mean": df_counts.mean(axis=1),
#             "EC_mean_TG1": df_counts_TG1.mean(axis=1),
#             "EC_mean_TG2": df_counts_TG2.mean(axis=1),
#             "pvalue": scipy.stats.mannwhitneyu(
#                 df_counts_TG1,
#                 df_counts_TG2,
#                 method="asymptotic",
#                 alternative="two-sided",
#                 nan_policy="omit",
#                 axis=1,
#                 keepdims=False,
#             )[1],
#             "EC_median": df_counts.median(axis=1, skipna=True),
#             "EC_median_TG1": df_counts_TG1.median(axis=1, skipna=True),
#             "EC_median_TG2": df_counts_TG2.median(axis=1, skipna=True),
#             "OG_type": np.select(
#                 condlist=[
#                     (df_counts_TG1.sum(axis=1).astype(int) == 0),
#                     (df_counts.sum(axis=1).astype(int) == 1),
#                     (df_counts_TG1.sum(axis=1).astype(int) >= 1)
#                     & (df_counts_TG2.sum(axis=1).astype(int) == 0),
#                     (df_counts_TG1.sum(axis=1).astype(int) >= 1)
#                     & (df_counts_TG2.sum(axis=1).astype(int) >= 1),
#                 ],
#                 choicelist=[
#                     "absent",
#                     "singleton",
#                     "specific",
#                     "shared",
#                 ],
#                 default="None",
#             ),
#             "log2_mean(TG1/TG2)": np.log2(
#                 df_counts_TG1.mean(axis=1) / df_counts_TG2.mean(axis=1)
#             ),
#         }
#     )
#     print()
#     df_partition = df_partition[
#         [
#             "OG_type",
#             "SC",
#             "SC_TG1",
#             "SP_TG1",
#             "SC_TG2",
#             "SP_TG2",
#             "EC",
#             "EC_TG1",
#             "EC_TG2",
#             "EC_mean",
#             "EC_mean_TG1",
#             "EC_mean_TG2",
#             "log2_mean(TG1/TG2)",
#             "pvalue",
#             "EC_median",
#             "EC_median_TG1",
#             "EC_median_TG2",
#             "COG_type_TG1",
#             "COG_TP",
#             "COG_TP_TG1",
#         ]
#     ]
#     for _, grouping, TG1_label, TG2_label in labels:
#         fn = f"partition.{grouping}.{TG1_label}_vs_{TG2_label}"
#         # sample_ids file
#         core.utils.dump(
#             pd.DataFrame.from_records(
#                 [{"TG": "1", "sample_id": TN, "label": TG1_label} for TN in TG_1]
#                 + [{"TG": "2", "sample_id": TN, "label": TG2_label} for TN in TG_2]
#             ),
#             fn=core.utils.format_fn(
#                 fn=(f"{fn}.sample_ids.tsv"),
#                 prefix=output_dir / grouping,
#             ),
#             verbose=False,
#             index=False,
#         )
#         # comparisons file
#         core.utils.dump(
#             df_partition.reset_index(),
#             fn=core.utils.format_fn(
#                 fn=(f"{fn}.comparisons.{output_fmt}"),
#                 prefix=output_dir / grouping,
#             ),
#             verbose=False,
#             index=False,
#         )

#     return True


# [Progressbar takes too long]
# tqdm.tqdm.pandas(
#     desc=definitions.PROGRESS_DESC_ORTHOGROUPS_ADD_SAMPLE,
#     ncols=definitions.PROGRESS_NCOLS,
# )
# df_orthogroups["sample_id"] = df_orthogroups["element_id"].map(
#     lambda x: df_elements["sample_id"].loc[x], na_action="ignore"
# )  # 100% 20194305/20194305 [04:26<00:00, 75694.57it/s]

# def do_tasks_old(
#     tasks,
#     df_counts,
#     count_target=1,
#     count_min=0,
#     count_max=2,
#     count_fraction=0.75,
#     output_fmt="parquet",
#     output_dir="",
#     processes=1,
# ):
#     t_0 = time.monotonic()
#     df_counts_tmp_fn = core.utils.dump(
#         # df_counts.replace(0, np.nan),  # DON'T CHANGE!
#         df_counts.apply(pd.to_numeric, downcast="float").replace(0, np.nan),  # BEST?
#         # df_counts.astype(pd.Int16Dtype()).replace(0, pd.NA), # SCIPY DOES NOT LIKE pd.NA
#         fn=core.utils.format_fn(
#             fn=tempfile.NamedTemporaryFile().name,
#             prefix=output_dir / definitions.TMP_DIR,
#             suffix=".parquet",
#         ),
#         index=True,
#     )
#     payloads = [
#         {
#             "df_counts_fn": df_counts_tmp_fn,
#             "count_target": count_target,
#             "count_min": count_min,
#             "count_max": count_max,
#             "count_fraction": count_fraction,
#             "output_fmt": output_fmt,
#             "output_dir": output_dir,
#             **task,
#         }
#         for task in tasks
#     ]
#     logger.info(
#         f"partitioning {len(payloads)} batches of taxon-groups using {processes} process(es)"
#     )
#     if processes > 1:
#         with tqdm.tqdm(
#             total=len(tasks),
#             desc=PROGRESS_DESC_PARTITIONING,
#             ncols=PROGRESS_NCOLS,
#         ) as t:
#             args = payloads
#             with poolcontext(processes=processes) as pool:
#                 for _ in pool.imap_unordered(partition, args):
#                     t.update()
#     else:
#         for payload in tqdm.tqdm(
#             payloads,
#             total=len(payloads),
#             desc=PROGRESS_DESC_PARTITIONING,
#             ncols=PROGRESS_NCOLS,
#         ):
#             _ = partition(**payload)
#     df_counts_tmp_fn.unlink()
#     logger.info(
#         core.utils.format_elapsed(time.monotonic() - t_0),
#     )

# def get_orthogroups_bck(
#     orthogroup_fn,
#     sample_ids=[],
#     output_dir="",
#     output_fmt="feather",
#     sample_ids_source="parse",
# ):
#     # [ORTHOGROUPS]:  99% 20194305/20389463 [06:05<00:03, 55254.32it/s] of 8Gb mem
#     #
#     data = []
#     t_0 = time.monotonic()
#     logger.info(f"parsing {len(sample_ids)} samples from '{orthogroup_fn}'")
#     if not sample_ids_source == "parse":
#         elements_dir = (
#             output_dir / definitions.INPUT_DIR if output_dir else definitions.INPUT_DIR
#         )
#         df_elements = core.utils.load(
#             fn=elements_dir / f"elements.{output_fmt}"
#         ).set_index("element_id")
#     rows = []
#     with open(orthogroup_fn) as orthogroup_fh:
#         for line in orthogroup_fh:
#             rows.append(line.rstrip("\n").split(" "))
#     with tqdm.tqdm(
#         total=len(rows),
#         desc=definitions.PROGRESS_DESC_ORTHOGROUPS_PARSE,
#         ncols=definitions.PROGRESS_NCOLS,
#     ) as t:
#         for row in rows:
#             orthogroup_id, element_ids = row[0].replace(":", ""), row[1:]
#             for element_id in element_ids:
#                 if sample_ids_source == "parse":
#                     sample_id = element_id.split(".")[0]
#                     data.append((element_id, orthogroup_id, sample_id))
#                 else:
#                     data.append((element_id, orthogroup_id))
#             t.update()
#     if sample_ids_source == "parse":
#         df_orthogroups = pd.DataFrame.from_records(
#             data,
#             columns=[
#                 "element_id",
#                 "orthogroup_id",
#                 "sample_id",
#             ],
#         )
#     else:
#         df_orthogroups = pd.DataFrame.from_records(
#             data,
#             columns=[
#                 "element_id",
#                 "orthogroup_id",
#             ],
#         )
#         logger.info("inferring sample_ids for orthogroups...")
#         tqdm.tqdm.pandas(
#             desc=definitions.PROGRESS_DESC_ORTHOGROUPS_ADD_SAMPLE,
#             ncols=definitions.PROGRESS_NCOLS,
#         )
#         df_orthogroups["sample_id"] = df_orthogroups["element_id"].progress_map(
#             lambda x: df_elements["sample_id"].loc[x], na_action="ignore"
#         )
#     logger.info(
#         f"{core.utils.format_number(len(df_orthogroups['orthogroup_id'].unique()))} orthogroup(s) in file"
#     )
#     logger.info(
#         f"{core.utils.format_number(len(df_orthogroups.index))} element(s) in file"
#     )
#     sample_ids_present = list(df_orthogroups["sample_id"].unique())
#     logger.info(
#         f"{core.utils.format_number(len(sample_ids_present))} sample ID(s) in file"
#     )
#     if sample_ids:
#         sample_ids_to_remove = [s for s in sample_ids_present if s not in sample_ids]
#         if sample_ids_to_remove:
#             logger.warning(
#                 f"excluding {core.utils.format_number(len(sample_ids_to_remove))} sample ID(s) from data: {', '.join(sample_ids_to_remove)}"
#             )
#             # mask = df_orthogroups["sample_id"].isin(sample_ids)  # elapsed: 0:04:15.656517
#             mask = df_orthogroups["sample_id"].apply(
#                 lambda x: x in set(sample_ids)
#             )  # elapsed: 0:04:15.363990
#             df_orthogroups_orphans = df_orthogroups[~mask]
#             if not df_orthogroups_orphans.empty:
#                 logger.warning(
#                     f"excluded {core.utils.format_number(len(df_orthogroups_orphans['orthogroup_id'].unique()))} orthogroup(s) from data"
#                 )
#                 logger.warning(
#                     f"excluded {core.utils.format_number(len(df_orthogroups_orphans.index))} element(s) from data"
#                 )
#                 core.utils.dump(
#                     df_orthogroups_orphans,
#                     fn=core.utils.format_fn(
#                         f"orthogroups.orphans.{output_fmt}",
#                         prefix=(output_dir / definitions.INPUT_DIR),
#                     ),
#                     verbose=True,
#                     index=False,
#                 )
#             df_orthogroups = df_orthogroups[mask]
#         sample_ids_missing = [
#             sample_id
#             for sample_id in sample_ids
#             if sample_id not in set(df_orthogroups["sample_id"].unique())
#         ]
#         if sample_ids_missing:
#             logger.error(
#                 f"{len(sample_ids_missing)} sample ID(s) from config file are missing: {', '.join(sample_ids_missing)}"
#             )
#             sys.exit(1)
#         if df_orthogroups.empty:
#             logger.error(
#                 f"none of these sample IDs were found: {', '.join(sample_ids)}"
#             )
#             sys.exit(1)
#         logger.info(
#             f"{core.utils.format_number(len(df_orthogroups['orthogroup_id'].unique()))} orthogroup(s) parsed"
#         )
#         logger.info(
#             f"{core.utils.format_number(len(df_orthogroups.index))} element(s) parsed",
#         )
#         logger.info(
#             f"4 {core.utils.format_elapsed(time.monotonic() - t_0)}",
#         )
#         core.utils.dump(
#             df_orthogroups,
#             fn=core.utils.format_fn(
#                 f"orthogroups.{output_fmt}",
#                 prefix=(output_dir / definitions.INPUT_DIR),
#             ),
#             verbose=True,
#             index=False,
#         )
#     logger.info(
#         core.utils.format_elapsed(time.monotonic() - t_0),
#     )
#     return df_orthogroups


# def get_config(
#    config_fn,
#    taxonomic_ranks=[
#        "genus",
#        "species",
#    ],
#    verbose=True,
# ):
#    config_fn = pathlib.Path(config_fn)
#    )
#    if config_fn.suffix == ".csv":
#        config_data = core.utils.load(config_fn).to_dict(orient="records")
#    else:
#        config_data = core.utils.load(config_fn)
#    if not config_data:
#        logger.error("config is empty")
#        sys.exit(1)
#    if "sample_id" not in config_data[0]:
#        logger.error("column 'sample_id' not found")
#        sys.exit(1)
#
#    df_config = pd.DataFrame().from_dict(config_data).convert_dtypes()
#    parsed_rows = len(df_config.index)
#    parsed_cols = len(df_config.columns)
#    logger.info(f"found {core.utils.format_number(parsed_rows)} sample ID(s)")
#    logger.info(f"found {core.utils.format_number(parsed_cols)} grouping(s)")
#    if "taxid" in df_config.columns:
#        df_config = get_taxonomy(df_config, taxonomic_ranks=taxonomic_ranks)
#    elif taxonomic_ranks:
#        logger.warning(
#            f"no taxids provided in config. Can't lookup taxonomic ranks: {taxonomic_ranks}"
#        )
#    if verbose:
#        print(df_config)
#    assert len(df_config.index) == parsed_rows, (
#        f"{len(df_config.index)=} != {parsed_rows=}"
#    )
#    input_dir = (
#        output_dir / definitions.INPUT_DIR if output_dir else definitions.INPUT_DIR
#    )
#    # output directory
#    core.utils.mkdir(
#        name=output_dir,
#        subdirs=[
#            "sample_ids",
#        ]
#        + list(df_config.columns),
#        do_replace=False,
#    )
#    # table
#    core.utils.dump(
#        df_config,
#        fn=core.utils.format_fn(
#            config_fn,
#            prefix=input_dir,
#            suffix=f".{output_fmt}",
#        ),
#        verbose=True,
#        index=False,
#    )
#    # new json
#    config_data = df_config.to_dict(orient="records")
#    core.utils.dump(
#        config_data,
#        fn=core.utils.format_fn(
#            config_fn,
#            prefix=input_dir,
#            suffix=".parsed.json",
#        ),
#        verbose=True,
#        index=False,
#    )
#
#    return config_data


# def get_tasks_old(
#     df_config=None,
#     df_counts=None,
#     count_target=1,
#     count_min=0,
#     count_max=2,
#     count_fraction=0.75,
#     output_fmt="tsv",
#     verbose=False,
# ):
#     t_0 = time.monotonic()
#     collector = collections.defaultdict(list)
#     taxon_groups = get_taxon_groups(df_config.to_dict(orient="records"))
#     combinations = []
#     task_type = "compare"
#     for key in taxon_groups:
#         collector_key = tuple(
#             [task_type] + [tuple(TG) for TG in sorted(taxon_groups[key].values())]
#         )
#         collector_value = tuple(
#             [key] + [TG_label for TG_label in taxon_groups[key].keys()]
#         )
#         collector[collector_key].append(collector_value)
#         combinations += get_combinations(taxon_groups, key)
#     task_type = "contrast"
#     for TG_1, TG_2, (grouping, label_1, label_2) in sorted(combinations):
#         collector_key = (task_type, TG_1, TG_2)
#         collector_value = (grouping, label_1, label_2)
#         collector[collector_key].append(collector_value)
#     tasks = []
#     df_counts_fn = core.utils.dump(
#         # df_counts.replace(0, np.nan),  # DON'T CHANGE!
#         df_counts.apply(pd.to_numeric, downcast="float").replace(0, np.nan),  # BEST?
#         fn=core.utils.format_fn(
#             fn="orthogroups.counts.nan.feather",
#             prefix=core.utils.get_dir("TMP"),
#         ),
#         index=True,
#         verbose=verbose,
#     )
#     for k, v in collector.items():
#         task_type = k[0]
#         taxon_groups = k[1:]
#         labels = [label[0] for label in v]
#         tags = [label[1:] for label in v]
#         task = Task(
#             type=task_type,
#             taxon_groups=taxon_groups,
#             labels=labels,
#             tags=tags,
#             df_counts_fn=df_counts_fn if task_type == "contrast" else None,
#             count_target=count_target,
#             count_min=count_min,
#             count_max=count_max,
#             count_fraction=count_fraction,
#             output_fmt=output_fmt,
#         )
#         tasks.append(task)
#     logger.info(
#         core.utils.format_elapsed(time.monotonic() - t_0),
#     )
#     return sorted(tasks, key=lambda x: x.priority)


#

# def process_interpro(
#     fn=None,
#     directory=None,
#     sample_ids=[],
#     output_fmt="tsv",
#     processes=1,
# ):
#     t_0 = time.monotonic()
#     write_temp_files(
#         directory=directory,
#         sample_ids=sample_ids,
#         output_fmt=output_fmt,
#         processes=processes,
#     )
#     df_annotation = (
#         core.utils.get_interpro_df()
#         .reset_index()
#         .groupby(
#             definitions.ANNOTATION_INDEX,
#             as_index=False,
#             dropna=False,
#         )
#         .agg(
#             TG_AC=("element_id", "nunique"),
#         )
#         .set_index(definitions.ANNOTATION_INDEX)
#         .unstack(fill_value=0)
#     )
#     df_counts = core.utils.get_counts_df()
#     df_annotation["EC"] = df_counts.sum(axis=1)
#     df_annotation["EC_AC"] = df_annotation["TG_AC"].sum(axis=1)
#     df_annotation["EC_AP"] = df_annotation["EC_AC"] / df_annotation["EC"]
#     df_annotation["SN_AP"] = (
#         df_annotation["TG_AC"].ge(1).sum(axis=1).div(df_counts.ge(1).sum(axis=1))
#     )
#     # df_annotation["TG_AP"] = (
#     #     df_annotation["TG_AP"]
#     #     .div(
#     #         df_counts,
#     #     )
#     #     .replace(np.nan, 0.0)
#     # )
#     df_annotation.columns = [
#         (f"{x}_{y}" if y else f"{x}") for x, y in df_annotation.columns.to_flat_index()
#     ]
#     front_cols = [
#         "orthogroup_id",
#         "EC",
#         "EC_AC",
#         "EC_AP",
#         "SN_AP",
#     ]
#     df_annotation = df_annotation.reset_index()
#     column_order = front_cols + [
#         col for col in df_annotation.columns if col not in front_cols
#     ]
#     core.utils.dump(
#         df_annotation[column_order],
#         fn=core.utils.format_fn(
#             definitions.ANNOTATION_FN,
#             prefix=core.utils.get_dir("ANNOTATION"),
#             suffix=f".{output_fmt}",
#         ),
#         index=False,
#     )
#     logger.info(f"[elapsed: {time.monotonic() - t_0}")

def contrast(task):
    """
    - np.nanmedian is not faster
    - .ge() is faster than .mask()
    - dtype="category" does not help in OG_type
    - medians are 42.1% of time
    - pvalue is 20.2% of time
    """
    TG_1, TG_2 = task.taxon_groups
    # df_counts = core.utils.load(
    #     fn=task.df_counts_fn,
    #     columns=sum([("orthogroup_id",), TG_1, TG_2], ()),
    # )
    df_counts = core.utils.get_counts_df(
        columns=sum([("orthogroup_id",), TG_1, TG_2], ()),
        nan=True,
    )
    df_counts_TG1 = df_counts.loc[:, TG_1]
    df_counts_TG2 = df_counts.loc[:, TG_2]
    df_partition_list = []
    # timing, t_i = {}, time.monotonic()
    df_partition_list.append(df_counts.ge(1).sum(axis=1).rename("SC"))
    # timing["SC"], t_i = time.monotonic() - t_i, time.monotonic()
    df_partition_list.append(df_counts_TG1.ge(1).sum(axis=1).rename("SC_TG1"))
    # timing["SC_TG1"], t_i = time.monotonic() - t_i, time.monotonic()
    df_partition_list.append((df_partition_list[1] / len(TG_1)).rename("SP_TG1"))
    # timing["SP_TG1"], t_i = time.monotonic() - t_i, time.monotonic()
    df_partition_list.append(df_counts_TG2.ge(1).sum(axis=1).rename("SC_TG2"))
    # timing["SC_TG2"], t_i = time.monotonic() - t_i, time.monotonic()
    df_partition_list.append((df_partition_list[3] / len(TG_2)).rename("SP_TG2"))
    # timing["SP_TG2"], t_i = time.monotonic() - t_i, time.monotonic()
    df_partition_list.append(df_counts.sum(axis=1).astype(int).rename("EC"))
    # timing["EC"], t_i = time.monotonic() - t_i, time.monotonic()
    df_partition_list.append(df_counts_TG1.sum(axis=1).astype(int).rename("EC_TG1"))
    # timing["EC_TG1"], t_i = time.monotonic() - t_i, time.monotonic()
    df_partition_list.append(df_counts_TG2.sum(axis=1).astype(int).rename("EC_TG2"))
    # timing["EC_TG2"], t_i = time.monotonic() - t_i, time.monotonic()
    df_partition_list.append(
        pd.Series(
            np.select(
                condlist=[
                    (df_partition_list[6] == 0),
                    (df_partition_list[5] == 1),
                    (df_partition_list[7] == 0),  # sufficient!
                    # (df_partition_list[7] == 0) & (df_partition_list[6] >= 1),
                    # (df_partition_list[6] >= 1) & (df_partition_list[7] >= 1),
                ],
                choicelist=[
                    "absent",
                    "singleton",
                    "specific",
                    # "shared",
                ],
                default="shared",
            ),
            index=df_counts.index,
        ).rename("OT")
    )
    # timing["OG_type"], t_i = time.monotonic() - t_i, time.monotonic()
    df_partition_list.append(
        (df_counts.eq(task.count_target).sum(axis=1) / len(df_counts.columns)).rename(
            "CSP"
        )
    )
    # timing["CSP"], t_i = time.monotonic() - t_i, time.monotonic()
    df_partition_list.append(
        (df_counts_TG1.eq(task.count_target).sum(axis=1) / len(TG_1)).rename("CSP_TG1")
    )
    # timing["CSP_TG1"], t_i = time.monotonic() - t_i, time.monotonic()
    # FASTER NPSELECT
    df_partition_list.append(
        pd.Series(
            np.select(
                condlist=[
                    np.all(df_counts_TG1.eq(task.count_target), axis=1),
                    np.mean(
                        (df_counts_TG1 >= task.count_min)
                        & (df_counts_TG1 <= task.count_max),
                        axis=1,
                    )
                    >= task.count_fraction,
                ],
                choicelist=[
                    "true_cog",
                    "fuzzy_cog",
                ],
                default="no_cog",
            ),
            index=df_counts.index,
        ).rename("CT")
    )
    ## SLOWER apply
    # df_partition_list.append(
    #     df_counts_TG1.apply(
    #         infer_cog_type,
    #         axis=1,
    #         raw=True,
    #         args=(
    #             task.count_target,
    #             task.count_min,
    #             task.count_max,
    #             task.count_fraction,
    #         ),
    #     ).rename("CT")
    # )
    # timing["CT"], t_i = time.monotonic() - t_i, time.monotonic()
    df_partition_list.append(df_counts.mean(axis=1).rename("EC_mean"))
    # timing["EC_mean"], t_i = time.monotonic() - t_i, time.monotonic()
    df_partition_list.append(df_counts_TG1.mean(axis=1).rename("EC_mean_TG1"))
    # timing["EC_mean_TG1"], t_i = time.monotonic() - t_i, time.monotonic()
    df_partition_list.append(df_counts_TG2.mean(axis=1).rename("EC_mean_TG2"))
    # timing["EC_mean_TG2"], t_i = time.monotonic() - t_i, time.monotonic()
    df_partition_list.append(
        pd.Series(
            np.log2(df_partition_list[13] / df_partition_list[14]),
            index=df_counts.index,
        ).rename("l2m(TG1/TG2)")
    )
    # timing["l2m(TG1/TG2)"], t_i = (
    #    time.monotonic() - t_i,
    #    time.monotonic(),
    # )
    df_partition_list.append(
        pd.Series(
            scipy.stats.mannwhitneyu(
                df_counts_TG1,
                df_counts_TG2,
                method="asymptotic",
                alternative="two-sided",
                nan_policy="omit",
                axis=1,
                keepdims=False,
            )[1],
            index=df_counts.index,
        ).rename("pvalue")
    )
    # timing["pvalue"], t_i = time.monotonic() - t_i, time.monotonic()
    df_partition_list.append(df_counts.median(axis=1, skipna=True).rename("EC_median"))
    # timing["EC_median"], t_i = time.monotonic() - t_i, time.monotonic()
    df_partition_list.append(
        df_counts_TG1.median(axis=1, skipna=True).rename("EC_median_TG1")
    )
    # timing["EC_median_TG1"], t_i = time.monotonic() - t_i, time.monotonic()
    df_partition_list.append(
        df_counts_TG2.median(axis=1, skipna=True).rename("EC_median_TG2")
    )
    # timing["EC_median_TG2"], t_i = time.monotonic() - t_i, time.monotonic()
    # concat
    df_partition = pd.concat(df_partition_list, axis=1)
    # timing["concat"], t_i = time.monotonic() - t_i, time.monotonic()
    df_partition = df_partition[
        [
            "OT",
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
            "l2m(TG1/TG2)",
            "pvalue",
            "EC_median",
            "EC_median_TG1",
            "EC_median_TG2",
            "CT",
            "CSP",
            "CSP_TG1",
        ]
    ]
    for idx, label in enumerate(task.labels):
        TG1_tag, TG2_tag = task.tags[idx]
        fn = f"{label}.{TG1_tag}_vs_{TG2_tag}"
        # [SAMPLE IDS]
        core.utils.dump(
            pd.DataFrame.from_records(
                [{"TG": "1", "sample_id": SN, "label": TG1_tag} for SN in TG_1]
                + [{"TG": "2", "sample_id": SN, "label": TG2_tag} for SN in TG_2]
            ),
            fn=core.utils.format_fn(
                fn=(f"{fn}.sample_ids.tsv"),
                prefix=core.utils.get_dir("PARTITION") / label,
            ),
            index=False,
        )
        # [CONTRAST]
        core.utils.dump(
            downcast(df_partition.reset_index(), categorical=["CT"]),
            fn=core.utils.format_fn(
                fn=(f"{fn}.partition.{task.output_fmt}"),
                prefix=core.utils.get_dir("PARTITION") / label,
            ),
            index=False,
        )
    # timing["dumping"] = time.monotonic() - t_i
    # import pprint
    # pprint.pp(timing)
    return True


import collections
import contextlib
import glob
import itertools
import logging
import math
import multiprocessing
import pathlib
import sys
import time
import traceback
import warnings

import core.log
import core.taxonomy
import definitions
import numpy as np
import pandas as pd
import scipy
import tqdm

import core.utils

logger = logging.getLogger(__name__)

DOWNCAST = False
# pd.options.display.max_colwidth = None
# pd.options.display.max_rows = None


ComparisonTask = collections.namedtuple(
    "ComparisonTask",
    [
        "type",
        "labels",
        "tags",
        "taxon_groups",
        "count_target",
        "count_min",
        "count_max",
        "count_fraction",
        "output_fmt",
    ],
)

SummaryTask = collections.namedtuple(
    "SummaryTask",
    [
        "type",
        "labels",
        "tags",
        "taxon_groups",
        "output_fmt",
    ],
)

ParseTask = collections.namedtuple(
    "ParseTask",
    [
        "type",
        "sample_id",
        "fn",
    ],
)

InterproChunkTask = collections.namedtuple(
    "InterproChunkTask",
    [
        "type",
        "sample_id",
        "size",
    ],
)

AnnotationTask = collections.namedtuple(
    "AnnotationTask",
    [
        "type",
        "sample_ids",
        "chunk",
    ],
)


@contextlib.contextmanager
def poolcontext(*args, **kwargs):
    pool = multiprocessing.Pool(*args, **kwargs)
    yield pool
    pool.terminate()


"""

[ToDo]
- parse multicolumn TABLE_FN
- think about whether to support other ways of linking element_id <-> sample_id (beside name-prefix)?
[###] filenames vs pathlib-objects
- use pathlib only for intial CLI args to get absolute paths easily
- filename-strings are better for being passed to processes

[###] Parquet/Feather:
- storage_options: data can be accessed via storeage connection (host, port, username, password, etc)
- parquet smaller files, feather faster read/write (both smaller/faster than CSV)
"""


# [DONE]
def get_parse_tasks(
    directory=None,
    type="",
    sample_ids=[],
    extensions=[],
):
    _SAMPLE_IDS = set(sample_ids)
    tasks = []
    for extension in extensions:
        for fn in glob.glob(f"{directory}/*{extension}"):
            sample_id = pathlib.Path(fn).stem.split(".")[0]
            if sample_id in _SAMPLE_IDS:
                tasks.append(
                    ParseTask(
                        type=type,
                        sample_id=sample_id,
                        fn=fn,
                    )
                )
    return tasks


# [DONE]
def do_parse_fasta_task(task):
    try:
        data = []
        for header, length in core.utils.iter_seq_length(task.fn):
            data.append((header, task.sample_id, length))
        df_fasta = pd.DataFrame().from_records(
            data, columns=["element_id", "sample_id", "length"]
        )
        if df_fasta.empty:
            logger.warning(f"no sequences found in {task.fn}")
        else:
            df_fasta = downcast(
                df_fasta,
                categorical=["sample_id"],
            )
            return core.utils.dump(
                df_fasta,
                fn=core.utils.format_fn(
                    f"{task.sample_id}.elements.{definitions.STD_FORMAT}",
                    prefix=core.utils.get_dir("TMP") / task.sample_id,
                ),
                index=False,
            )
    except Exception as exc:
        logger.error(f"problem reading {task.fn} - {exc}")
    return None


# [DONE]
def get_parse_interpro_tasks(
    directory=None,
    sample_ids=[],
):
    tasks = get_parse_tasks(
        directory=directory,
        type="interpro",
        sample_ids=sample_ids,
        extensions=definitions.SUPPORTED_INTERPRO_EXTENSIONS,
    )
    sample_ids_found = [task.sample_id for task in tasks]
    if len(sample_ids_found) < len(sample_ids):
        sample_ids_missing = set(sample_ids) - set(sample_ids_found)
        logger.warning(
            f"files for the following sample IDs could not be found: {', '.join(sorted(sample_ids_missing))}"
        )
        for sample_id in sample_ids_missing:
            tasks.append(
                ParseTask(
                    type="interpro",
                    sample_id=sample_id,
                    fn=None,
                )
            )
    return tasks


def get_interpro_df_empty(sample_id):
    return (
        core.utils.get_orthogroups_df(filters=[("sample_id", "==", sample_id)])
        .set_index("orthogroup_id")
        .join(
            core.utils.get_counts_df(
                columns=[sample_id],
            ),
            how="right",
        )
        # .assign(**{"signature_id": "nan", "analysis": "nan"})
        .assign(**{"signature_id": np.nan, "analysis": np.nan})
        .reset_index()
    ).drop(columns=[sample_id])


# def do_parse_interpro_task_old(task):
#     try:
#         if task.fn is None:
#             # fake df_annotation for sample_ids without interpro file
#             df_annotation = get_interpro_df_empty(task.sample_id)
#         else:
#             df_interpro = core.utils.load(
#                 task.fn,
#                 names=definitions.INTERPRO_TSV_COLUMNS,
#             )[definitions.INTERPRO_TSV_COLUMNS_VALID].set_index("element_id")
#             # add orthorgoups information
#             df_annotation = df_interpro.join(
#                 core.utils.get_orthogroups_df(
#                     filters=[("sample_id", "==", task.sample_id)],
#                 ).set_index("element_id"),
#                 how="outer",
#             )
#             # remove annotations of E's not in OG's
#             df_annotation = df_annotation[~df_annotation["orthogroup_id"].isnull()]
#             if df_annotation.empty:
#                 df_annotation = get_interpro_df_empty(task.sample_id)
#             else:
#                 # [signatures]
#                 df_signatures = (
#                     df_annotation[definitions.SIGNATURE_COLUMNS]
#                     .set_index("signature_id")
#                     .drop_duplicates()
#                     .dropna(subset=["analysis"])
#                 )
#                 _ = core.utils.dump(
#                     df_signatures,
#                     fn=core.utils.format_fn(
#                         f"{task.sample_id}.{definitions.SIGNATURES_FN}",
#                         prefix=core.utils.get_dir("TMP") / task.sample_id,
#                     ),
#                     index=True,
#                 )
#                 # [annotations]
#                 df_annotation = (
#                     core.utils.get_counts_df(
#                         columns=[task.sample_id],
#                     )
#                     .join(
#                         (
#                             df_annotation[definitions.ANNOTATION_COLUMNS]
#                             .reset_index()
#                             .set_index("orthogroup_id")
#                         ),
#                         how="left",
#                     )
#                     .reset_index()
#                     .drop(columns=[task.sample_id])
#                     # .set_index(definitions.ANNOTATION_COLUMNS)
#                 )
#     except Exception as exc:
#         logger.error(f"{exc}")
#         logger.error(f"{traceback.format_exc()}")
#         sys.exit(1)
#     df_annotation = downcast(
#         df_annotation,
#         categorical=[
#             "analysis",
#             "signature_id",
#             "sample_id",
#         ],
#     )
#     core.utils.dump(
#         df_annotation,
#         fn=core.utils.format_fn(
#             f"{task.sample_id}.{definitions.ANNOTATION_FN}",
#             prefix=core.utils.get_dir("TMP") / task.sample_id,
#         ),
#         index=True,
#     )


def do_parse_interpro_task(task):
    analyses = []
    try:
        if task.fn is None:
            # fake df_annotation for sample_ids without interpro file
            df_annotation = get_interpro_df_empty(task.sample_id)
        else:
            df_interpro = core.utils.load(
                task.fn,
                names=definitions.INTERPRO_TSV_COLUMNS,
            )[definitions.INTERPRO_TSV_COLUMNS_VALID].set_index("element_id")
            # add orthorgoups information
            df_annotation = downcast(
                df_interpro.join(
                    core.utils.get_orthogroups_df(
                        filters=[("sample_id", "==", task.sample_id)],
                    ).set_index("element_id"),
                    how="outer",
                )
            )
            # remove annotations of E's not in OG's
            df_annotation = df_annotation[~df_annotation["orthogroup_id"].isnull()]
            if df_annotation.empty:
                df_annotation = get_interpro_df_empty(task.sample_id)
            else:
                df_signatures = (
                    df_annotation[
                        [
                            "signature_id",
                            "analysis",
                            "signature_desc",
                            "interpro_id",
                            "interpro_desc",
                            "go_annotation",
                        ]
                    ]
                    .set_index("signature_id")
                    .drop_duplicates()
                    .dropna(subset=["analysis"])
                )
                analyses = df_signatures["analysis"].unique()
                _ = core.utils.dump(
                    df_signatures,
                    fn=core.utils.format_fn(
                        f"{task.sample_id}.{definitions.SIGNATURES_FN}",
                        prefix=core.utils.get_dir("TMP") / task.sample_id,
                    ),
                    index=True,
                )
                df_annotation = df_annotation[
                    [
                        "orthogroup_id",
                        "signature_id",
                        "analysis",
                    ]
                ].reset_index()
    except Exception as exc:
        logger.error(f"{exc}")
        logger.error(f"{traceback.format_exc()}")
        sys.exit(1)
    _ = write_signature_summary(
        df=df_annotation,
        analyses=analyses,
        sample_id=task.sample_id,
    )
    df_annotation = (
        downcast(df_annotation)
        .groupby(
            ["orthogroup_id", "analysis", "signature_id"],
            dropna=False,
        )
        .agg(sample=("element_id", "nunique"))
        .rename(columns={"sample": task.sample_id})
    )
    df_annotation = df_annotation.loc[(df_annotation != 0).any(axis=1)]
    core.utils.dump(
        df_annotation,
        fn=core.utils.format_fn(
            f"{task.sample_id}.{definitions.ANNOTATION_FN}",
            prefix=core.utils.get_dir("TMP") / task.sample_id,
        ),
        index=True,
    )


def write_signature_summary(df, analyses=[], sample_id=None):
    df_counts = core.utils.get_counts_df(
        columns=[sample_id],
    )
    EC = int(df_counts[sample_id].sum(axis=0))
    rows = []
    for analysis in analyses:
        EC_AC = int(df[df["analysis"] == analysis]["element_id"].nunique())
        rows.append((analysis, sample_id, EC, EC_AC, float(EC_AC / EC)))
    EC_AC = int(df[df["analysis"].isna()]["element_id"].nunique(dropna=True))
    rows.append(("not_annotated", sample_id, EC, EC_AC, float(EC_AC / EC)))
    core.utils.dump(
        pd.DataFrame().from_records(
            rows, columns=["analysis", "sample_id", "EC", "EC_AC", "EC_AP"]
        ),
        fn=core.utils.format_fn(
            f"{sample_id}.{definitions.SIGNATURES_SUMMARY_FN}",
            prefix=core.utils.get_dir("TMP") / sample_id,
        ),
        index=False,
    )


def downcast(df, categorical=[], info=False):
    ints = []
    floats = []
    if info:
        print("[+]\n")
        df.info()
    for column in df.columns:
        if column in categorical:
            df[column] = df[column].astype("category")
        elif df[column].dtype == "float64":
            floats.append(column)
        elif df[column].dtype == "int64":
            ints.append(column)
        elif df[column].dtype == "category" and not categorical:
            df[column] = df[column].astype(str)
        else:
            pass
    df[ints] = df[ints].apply(pd.to_numeric, downcast="unsigned")
    df[floats] = df[floats].apply(pd.to_numeric, downcast="float")
    if info:
        df.info()
        print("[*]")
    return df


# def make_interpro_chunks(task):
#     """
#     [ToDo]
#     - consumes 70Mb per species! too much
#     -either groupby here
#     """
#     chunks = []
#     df_annotation = core.utils.get_annotation_df(
#         sample_id=task.sample_id,
#     )
#     # print(df_annotation)
#     indices = [
#         [int(batch[0][1][0]), (int(batch[-1][1][0]) + 1)]
#         for batch in itertools.batched(
#             df_annotation.groupby(by="orthogroup_id").indices.items(),
#             task.size,
#         )
#     ]
#     for idx, (start, end) in enumerate(indices):
#         idx_string = str(idx).zfill(len(str(len(indices))))
#         chunks.append(idx_string)
#         core.utils.dump(
#             df_annotation.iloc[start:end],
#             fn=core.utils.format_fn(
#                 f"{task.sample_id}.{idx_string}.{definitions.ANNOTATION_FN}",
#                 prefix=core.utils.get_dir("TMP") / task.sample_id,
#             ),
#             index=True,
#         )
#     return (task.sample_id, chunks)


# def get_annotation_tasks(
#     sample_ids=[],
#     processes=1,
# ):
#     """
#     [ToDo]
#     do groupby on each sample, should be below 2Mb
#     - drop sample id (only needed for filtering)
#     - it coul be done directly in do_parse_interpro_task

#     """
#     df_counts = core.utils.get_counts_df()
#     df_annotation_denominator = pd.DataFrame(index=df_counts.index)
#     df_annotation_denominator["EC"] = df_counts.sum(axis=1)
#     df_annotation_denominator["SC"] = df_counts.ge(1).sum(axis=1)
#     df_annotation_denominator = downcast(df_annotation_denominator)
#     core.utils.dump(
#         df_annotation_denominator,
#         fn=core.utils.format_fn(
#             f"{definitions.ANNOTATION_DENOMINATOR_FN}",
#             prefix=core.utils.get_dir("TMP"),
#         ),
#         index=True,
#     )
#     ROWS_MAX = 400_000
#     size = max([processes, int((ROWS_MAX / len(sample_ids)))])
#     tasks = [
#         InterproChunkTask(
#             type="InterproChunkTask",
#             sample_id=sample_id,
#             size=size,
#         )
#         for sample_id in sample_ids
#     ]
#     logger.info(
#         f"chunking data of {len(sample_ids)} sample IDs using {processes} process(es)"
#     )
#     chunkings = do_tasks(
#         tasks=tasks,
#         desc=definitions.PROGRESS_DESC_INTERPRO,
#         processes=processes,
#         collect_results=True,
#     )
#     chunk_sizes = [len(chunking[1]) for chunking in chunkings]
#     if not chunk_sizes.count(chunk_sizes[0]) == len(chunk_sizes):
#         logger.error("chunk sizes are not equal:")
#         for sample_id, chunks in chunkings:
#             logger.error(f"{sample_id} = {len(chunks)}")
#         sys.exit(1)
#     tasks = [
#         AnnotationTask(
#             type="AnnotationTask",
#             sample_ids=sample_ids,
#             chunk=chunk,
#         )
#         for chunk in chunkings[0][1]
#     ]
#     return tasks


def do_annotation_task(task):
    df_annotations = []
    for sample_id in task.sample_ids:
        df_annotation = core.utils.get_annotation_df(
            sample_id=sample_id,
            chunk=task.chunk,
        )
        df_annotations.append(
            df_annotation.drop(
                # remove filler OG rows needed for chunking
                df_annotation[df_annotation["element_id"].isnull()].index
            )
        )
    df_annotation = pd.concat(df_annotations, axis=0)
    df_annotation = (
        (
            df_annotation  # check whether these empty rows are useful
            # df_annotation.drop(df_annotation[df_annotation["element_id"].isnull()].index)
            .groupby(
                definitions.ANNOTATION_COLUMNS,
                as_index=False,
                dropna=False,
            )
            .agg(
                SN_AC=("element_id", "nunique"),
            )
            .set_index(definitions.ANNOTATION_COLUMNS)
            .unstack(fill_value=0)
        )
        .reset_index()
        .set_index("orthogroup_id")
    )
    df_denominators = core.utils.load(
        fn=core.utils.get_dir("TMP") / definitions.ANNOTATION_DENOMINATOR_FN
    )
    # df_annotation["SN_AC"] = df_annotation["SN_AC"].replace(np.nan, 0)
    df_annotation["EC"] = df_denominators["EC"]
    df_annotation["SC"] = df_denominators["SC"]
    df_annotation.reset_index().set_index(
        [
            "orthogroup_id",
            "signature_id",
            "analysis",
        ]
    )
    df_annotation["EC_AC"] = df_annotation["SN_AC"].sum(axis=1)
    df_annotation["EC_AP"] = df_annotation["EC_AC"] / df_annotation["EC"]
    df_annotation["SC_AC"] = df_annotation["SN_AC"].ge(1).sum(axis=1)
    df_annotation["SC_AP"] = df_annotation["SC_AC"] / df_annotation["SC"]
    df_annotation = downcast(df_annotation)
    core.utils.dump(
        downcast(df_annotation, categorical=["signature_id", "analysis"]),
        fn=core.utils.format_fn(
            f"{task.chunk}.{definitions.ANNOTATION_FN}",
            prefix=core.utils.get_dir("TMP"),
        ),
        index=False,
    )


# def analyse_signatures(
#     sample_ids=[],
#     output_fmt="tsv",
# ):
#     df_signatures = None
#     logger.info("collecting INTEPRO signatures ...")
#     with tqdm.tqdm(
#         total=len(sample_ids),
#         desc=definitions.PROGRESS_DESC_SIGNATURES,
#         ncols=definitions.PROGRESS_NCOLS,
#     ) as pbar:
#         for sample_id in sample_ids:
#             df_signatures_instance = core.utils.get_signatures_df(
#                 sample_id=sample_id,
#             )
#             # print(df_signatures_instance)
#             if df_signatures_instance is not None:
#                 df_signatures = (
#                     df_signatures_instance
#                     if df_signatures is None
#                     else pd.concat(
#                         [
#                             df_signatures,
#                             df_signatures_instance,
#                         ],
#                         axis=0,
#                     ).drop_duplicates()
#                 )
#             pbar.update()
#     analyses = list(df_signatures["analysis"].unique())
#     if df_signatures is not None:
#         if not df_signatures.empty:
#             core.utils.dump(
#                 df_signatures,
#                 fn=core.utils.format_fn(
#                     f"{definitions.SIGNATURES_FN}",
#                     prefix=core.utils.get_dir("TMP"),
#                 ),
#                 index=True,
#             )
#     signatures = collections.defaultdict(lambda: collections.defaultdict(dict))
#     logger.info("tallying INTEPRO signatures ...")
#     with tqdm.tqdm(
#         total=len(sample_ids),
#         desc=definitions.PROGRESS_DESC_SIGNATURES_COUNTING,
#         ncols=definitions.PROGRESS_NCOLS,
#     ) as pbar:
#         # would benefit from EC accessibility
#         for sample_id in sample_ids:
#             df_annotation = core.utils.get_annotation_df(
#                 sample_id=sample_id,
#             ).reset_index()
#             df_counts = core.utils.get_counts_df()
#             EC = int(df_counts[sample_id].sum(axis=0))
#             for analysis in analyses:
#                 signatures[analysis][sample_id]["EC"] = EC
#                 signatures[analysis][sample_id]["EC_AC"] = int(
#                     df_annotation[df_annotation["analysis"] == analysis][sample_id].sum(
#                         axis=0
#                     )
#                 )
#                 signatures[analysis][sample_id]["EC_AP"] = float(
#                     signatures[analysis][sample_id]["EC_AC"] / EC
#                 )
#             signatures["not_annotated"][sample_id]["EC"] = EC
#             signatures["not_annotated"][sample_id]["EC_AC"] = int(
#                 df_annotation[df_annotation["analysis"].isna()][sample_id].sum(axis=0)
#             )
#             signatures["not_annotated"][sample_id]["EC_AP"] = float(
#                 signatures["not_annotated"][sample_id]["EC_AC"] / EC
#             )
#             pbar.update()
#     for analysis in signatures.keys():
#         analysis_string = analysis if isinstance(analysis, str) else "not_annotated"
#         rows = []
#         for sample_id in sample_ids:
#             rows.append(
#                 {
#                     "sample_id": sample_id,
#                     **signatures[analysis][sample_id],
#                 }
#             )
#         core.utils.dump(
#             pd.DataFrame().from_records(rows),
#             fn=core.utils.format_fn(
#                 f"interpro_signatures.{analysis_string}.summary.{output_fmt}",
#                 prefix=core.utils.get_dir("ANNOTATION"),
#             ),
#             index=False,
#         )

# def analyse_annotation_old(
#     sample_ids=[],
#     output_fmt="tsv",
#     processes=1,
# ):
#     t_0 = time.monotonic()
#     logger.info("preparing tasks ...")
#     tasks = get_annotation_tasks(
#         sample_ids=sample_ids,
#         processes=processes,
#     )
#     logger.info(f"processing {len(tasks)} chunk(s) using {processes} process(es)")
#     do_tasks(
#         tasks=tasks,
#         desc=definitions.PROGRESS_DESC_ANNOTATION_TASK_RUN,
#         processes=processes,
#     )
#     dfs = []
#     for fn in sorted(
#         glob.glob(str(core.utils.get_dir("TMP") / f"*.{definitions.ANNOTATION_FN}"))
#     ):
#         df = core.utils.load(fn=fn)
#         dfs.append(df)
#     logger.info(f"concatenating {len(dfs)} dataframes ...")
#     df = pd.concat(dfs)
#     logger.info("concatenating done")
#     _FRONT_COLS = [
#         "orthogroup_id",
#         "analysis",
#         "signature_id",
#         "EC",
#         "EC_AC",
#         "EC_AP",
#         "SC",
#         "SC_AC",
#         "SC_AP",
#     ]
#     df["SN_AC"] = df["SN_AC"].fillna(0).convert_dtypes()
#     df = downcast(df)
#     df.columns = [(f"{y}" if y else f"{x}") for x, y in df.columns.to_flat_index()]
#     df = df.reset_index()
#     column_order = _FRONT_COLS + [col for col in df.columns if col not in _FRONT_COLS]
#     df = df[column_order]
#     df = downcast(df)
#     core.utils.dump(
#         df,
#         fn=core.utils.format_fn(
#             f"{definitions.ANNOTATION_FN}",
#             prefix=core.utils.get_dir("ANNOTATION"),
#             suffix=f".{output_fmt}",
#         ),
#         index=False,
#     )
#     logger.info(f"{core.utils.format_elapsed(time.monotonic() - t_0)}")


# def analyse_signatures_old(
#     sample_ids=[],
#     output_fmt="tsv",
# ):
#     df_signatures = None
#     logger.info("collecting INTEPRO signatures ...")
#     with tqdm.tqdm(
#         total=len(sample_ids),
#         desc=definitions.PROGRESS_DESC_SIGNATURES,
#         ncols=definitions.PROGRESS_NCOLS,
#     ) as pbar:
#         for sample_id in sample_ids:
#             df_signatures_instance = core.utils.get_signatures_df(
#                 sample_id=sample_id,
#             )
#             # print(df_signatures_instance)
#             if df_signatures_instance is not None:
#                 df_signatures = (
#                     df_signatures_instance
#                     if df_signatures is None
#                     else pd.concat(
#                         [
#                             df_signatures,
#                             df_signatures_instance,
#                         ],
#                         axis=0,
#                     ).drop_duplicates()
#                 )
#             pbar.update()
#     analyses = list(df_signatures["analysis"].unique())
#     if df_signatures is not None:
#         if not df_signatures.empty:
#             core.utils.dump(
#                 df_signatures,
#                 fn=core.utils.format_fn(
#                     f"{definitions.SIGNATURES_FN}",
#                     prefix=core.utils.get_dir("TMP"),
#                 ),
#                 index=True,
#             )
#     signatures = collections.defaultdict(lambda: collections.defaultdict(dict))
#     logger.info("tallying INTEPRO signatures ...")
#     with tqdm.tqdm(
#         total=len(sample_ids),
#         desc=definitions.PROGRESS_DESC_SIGNATURES_COUNTING,
#         ncols=definitions.PROGRESS_NCOLS,
#     ) as pbar:
#         for sample_id in sample_ids:
#             df_annotation = core.utils.get_annotation_df(
#                 sample_id=sample_id,
#             )
#             EC = int(df_annotation["element_id"].nunique())
#             for analysis in analyses:
#                 signatures[analysis][sample_id]["EC"] = EC
#                 signatures[analysis][sample_id]["EC_AC"] = int(
#                     df_annotation[df_annotation["analysis"] == analysis][
#                         "element_id"
#                     ].nunique()
#                 )
#                 signatures[analysis][sample_id]["EC_AP"] = float(
#                     signatures[analysis][sample_id]["EC_AC"] / EC
#                 )
#             signatures["not_annotated"][sample_id]["EC"] = EC
#             signatures["not_annotated"][sample_id]["EC_AC"] = int(
#                 df_annotation[df_annotation["sample_id"] == sample_id]["analysis"]
#                 .isnull()
#                 .sum()
#             )
#             signatures["not_annotated"][sample_id]["EC_AP"] = float(
#                 signatures["not_annotated"][sample_id]["EC_AC"] / EC
#             )
#             pbar.update()
#     for analysis in signatures.keys():
#         analysis_string = analysis if isinstance(analysis, str) else "not_annotated"
#         rows = []
#         for sample_id in sample_ids:
#             rows.append(
#                 {
#                     "sample_id": sample_id,
#                     **signatures[analysis][sample_id],
#                 }
#             )
#         core.utils.dump(
#             pd.DataFrame().from_records(rows),
#             fn=core.utils.format_fn(
#                 f"interpro_signatures.{analysis_string}.summary.{output_fmt}",
#                 prefix=core.utils.get_dir("ANNOTATION"),
#             ),
#             index=False,
#         )


def parse_interpro(
    directory=None,
    sample_ids=[],
    output_fmt="tsv",
    processes=1,
):
    t_0 = time.monotonic()
    logger.info(f"parsing INTERPRO data in {directory}")
    tasks = get_parse_interpro_tasks(
        directory=directory,
        sample_ids=sample_ids,
    )
    processes = 1 if len(tasks) == 1 else processes
    logger.info(f"parsing {len(tasks)} file(s) using {processes} process(es)")
    do_tasks(
        tasks=tasks,
        desc=definitions.PROGRESS_DESC_INTERPRO,
        processes=processes,
        collect_results=True,
    )
    logger.info(f"{core.utils.format_elapsed(time.monotonic() - t_0)}")


def analyse_annotation(
    sample_ids=[],
    output_fmt="tsv",
    processes=1,
):
    """
    - acivate signatures
    - put signature data inside of df_annotation
    - change EC/SC/etc column generation to not trigger warning
    - check for categoricals ... might affect concatenation
    - run with downcasted(dfs) to see whether that improves memory
    - add downcasting upon loading, dumping
    """
    t_0 = time.monotonic()
    logger.info("joining INTERPRO results ...")
    df_annotations = []
    with tqdm.tqdm(
        total=len(sample_ids),
        desc=definitions.PROGRESS_DESC_ANNOTATION_TASK_RUN,
        ncols=definitions.PROGRESS_NCOLS,
    ) as pbar:
        for sample_id in sample_ids:
            df = core.utils.get_annotation_df(
                sample_id=sample_id,
                delete=False,
            )
            df_annotations.append(df)
            pbar.update()
    df_annotations = (
        pd.concat(df_annotations, axis=1).dropna(axis=0, how="all").replace(np.nan, 0)
    )
    for column in df_annotations.columns:
        df_annotations[column] = df_annotations[column].astype(int)
    df_annotations = downcast(df_annotations)
    df_counts = core.utils.get_counts_df()
    # additional_data = []
    # additional_data.append(df_counts.sum(axis=1).rename("EC"))
    # additional_data.append(df_annotations.sum(axis=1).rename("EC_AC"))
    # additional_data.append((additional_data[1] / additional_data[0]).rename("EC_AP"))
    # additional_data.append(df_counts.ge(1).sum(axis=1).rename("SC"))
    # additional_data.append(df_annotations.ge(1).sum(axis=1).rename("SC_AC"))
    # additional_data.append((additional_data[4] / additional_data[3]).rename("SC_AP"))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=pd.errors.PerformanceWarning)
        EC = df_counts.sum(axis=1)
        EC_AC = df_annotations.sum(axis=1)
        EC_AP = EC_AC / EC
        SC = df_counts.ge(1).sum(axis=1)
        SC_AC = df_annotations.ge(1).sum(axis=1)
        SC_AP = SC_AC / SC
        df_annotations["EC"] = EC
        df_annotations["EC_AC"] = EC_AC
        df_annotations["EC_AP"] = EC_AP
        df_annotations["SC"] = SC
        df_annotations["SC_AC"] = SC_AC
        df_annotations["SC_AP"] = SC_AP
    # print(additional_data)
    # df_annotations = pd.concat(
    #    [df_annotations, pd.concat(additional_data, axis=1)], axis=1
    # )
    # df_annotations.info()
    core.utils.dump(
        downcast(df_annotations),
        fn=core.utils.format_fn(
            f"{definitions.ANNOTATION_FN}",
            prefix=core.utils.get_dir("ANNOTATION"),
        ),
        index=False,
    )
    logger.info(f"{core.utils.format_elapsed(time.monotonic() - t_0)}")


def analyse_signatures(
    sample_ids=[],
    output_fmt="tsv",
):
    df_signatures = None
    logger.info("collecting INTEPRO signatures ...")
    with tqdm.tqdm(
        total=len(sample_ids),
        desc=definitions.PROGRESS_DESC_SIGNATURES,
        ncols=definitions.PROGRESS_NCOLS,
    ) as pbar:
        for sample_id in sample_ids:
            df_signatures_instance = core.utils.get_signatures_df(
                sample_id=sample_id,
            )
            df_signatures = (
                df_signatures_instance
                if df_signatures is None
                else pd.concat(
                    [
                        df_signatures,
                        df_signatures_instance,
                    ],
                    axis=0,
                ).drop_duplicates()
            )
            pbar.update()
    if df_signatures is not None and not df_signatures.empty:
        core.utils.dump(
            df_signatures,
            fn=core.utils.format_fn(
                f"{definitions.SIGNATURES_FN}",
                prefix=core.utils.get_dir("TMP"),
            ),
            index=True,
        )
    analyses = df_signatures["analysis"].unique()
    logger.info("tallying INTEPRO signature summary ...")
    df_signature_summary = []
    with tqdm.tqdm(
        total=len(sample_ids),
        desc=definitions.PROGRESS_DESC_SIGNATURES_COUNTING,
        ncols=definitions.PROGRESS_NCOLS,
    ) as pbar:
        for sample_id in sample_ids:
            df_signature_summary_instance = core.utils.get_signature_summary_df(
                sample_id=sample_id,
            )
            if len(df_signature_summary_instance) == 1:
                rows = []
                for analysis in analyses:
                    rows.append(
                        {
                            "sample_id": df_signature_summary_instance["sample_id"][0],
                            "analysis": analysis,
                            "EC": df_signature_summary_instance["EC"][0],
                            "EC_AC": 0,
                            "EC_AP": 0.0,
                        }
                    )
                df_signature_summary_instance = pd.concat(
                    [df_signature_summary_instance, pd.DataFrame.from_dict(rows)],
                    ignore_index=True,
                    axis=0,
                )
            df_signature_summary.append(df_signature_summary_instance)
            pbar.update()
        df_signature_summary = pd.concat(df_signature_summary, axis=0)[
            [
                "sample_id",
                "analysis",
                "EC",
                "EC_AC",
                "EC_AP",
            ]
        ]
    for analysis in df_signature_summary["analysis"].unique():
        core.utils.dump(
            df_signature_summary[df_signature_summary["analysis"] == analysis],
            fn=core.utils.format_fn(
                f"interpro_signatures.{analysis}.summary.{output_fmt}",
                prefix=core.utils.get_dir("ANNOTATION"),
            ),
            index=False,
        )


def analyse_interpro(
    directory=None,
    sample_ids=[],
    output_fmt="tsv",
    processes=1,
):
    t_0 = time.monotonic()
    parse_interpro(
        directory=directory,
        sample_ids=sample_ids,
        output_fmt=output_fmt,
        processes=processes,
    )
    analyse_signatures(
        sample_ids=sample_ids,
        output_fmt=output_fmt,
    )
    analyse_annotation(
        sample_ids=sample_ids,
        processes=processes,
    )
    # get_df_entropy(
    #     output_fmt=args.F,
    # )
    # data = x.groupby(by="orthogroup_id").indices
    # [len(chunk) for chunk in chunks(x.groupby(by="orthogroup_id").indices, SIZE=1000)]
    # chunk_size = max(args.p, len(data))
    # # collect
    # fns = []
    # idxs = []
    #
    # # for each idx, make task, run task, save as filename with padded-idx
    # idx = int
    """
    # concat axis=0 in sorted order (using padded index)
    
    
    1. parse all the signatures and concat them
    2. parse all the annotations
        - for each sample_id save the indices-slices
        - give the n-th task the n-th index-slices from each sample
    3. in each task:
        - groupy
    """
    logger.info(f"[elapsed: {time.monotonic() - t_0}")


def get_ids(
    sequence_ids_fn=None,
    species_ids_fn=None,
    sample_ids=[],
):
    logger.info("parsing SpeciesIDs file")
    sample_ids = set(sample_ids)
    try:
        sample_ids = {}
        with open(species_ids_fn, "r") as fh:
            for line in fh:
                species_idx, sample_id = line.rstrip("\n").split(": ")
                if sample_id in sample_ids:
                    sample_ids[species_idx] = sample_id
        data = []
        with open(sequence_ids_fn, "r") as fh:
            for line in fh:
                sequence_idx, element_id = line.rstrip("\n").split(": ")
                species_idx, _ = sequence_idx.split("_")
                if species_idx in sample_ids:
                    data.append((element_id, sample_ids[species_idx]))
        df = pd.DataFrame().from_records(data, columns=["element_id", "sample_id"])
        if df.empty:
            logger.error("no IDs could be parsed")
        else:
            logger.info(
                f"{core.utils.format_number(df['sample_id'].nunique())} sample IDs parsed"
            )
            logger.info(f"{core.utils.format_number(len(df.index))} element IDs")
            return core.utils.dump(
                downcast(df, categorical=["sample_id"]),
                fn=core.utils.format_fn(
                    fn=definitions.ELEMENTS_FN,
                    prefix=core.utils.get_dir("INPUT"),
                ),
                index=False,
            )
    except Exception as exc:
        logger.error(f"unexpected error - {exc}")
    sys.exit(1)


def get_elements(
    directory=None,
    sample_ids=[],
    processes=1,
):
    t_0 = time.monotonic()
    tasks = get_parse_tasks(
        directory=directory,
        type="ParseTask",
        sample_ids=sample_ids,
        extensions=definitions.SUPPORTED_FASTA_EXTENSIONS,
    )
    if len(tasks) < len(sample_ids):
        sample_ids_missing = set(sample_ids) - set([task.sample_id for task in tasks])
        logger.error(
            f"files for the following sample IDs could not be found: {', '.join(sorted(sample_ids_missing))}"
        )
        sys.exit(1)
    logger.info(f"parsing {len(tasks)} FASTA files using {processes} process(es)")
    df_fns = do_tasks(
        tasks=tasks,
        desc=definitions.PROGRESS_DESC_FASTA,
        processes=processes,
        collect_results=True,
    )
    df_fns_valid = list(filter(None, df_fns))
    if len(df_fns_valid) == 0:
        logger.error(
            f"No FASTA files with extension {', '.join(definitions.SUPPORTED_FASTA_EXTENSIONS)} found. Exiting."
        )
        sys.exit(1)
    if len(df_fns_valid) < len(tasks):
        logger.error("Some Fasta files could not be parsed. Exiting.")
        sys.exit(1)
    core.utils.dump(
        downcast(
            pd.concat([core.utils.load(df_fn) for df_fn in df_fns]),
        ),
        fn=core.utils.format_fn(
            fn=definitions.ELEMENTS_FN,
            prefix=core.utils.get_dir("INPUT"),
        ),
        index=False,
    )
    logger.info(f"{core.utils.format_elapsed(time.monotonic() - t_0)}")
    return True


def get_orthogroups(
    orthogroup_fn,
    sample_ids=[],
    sample_ids_source="parse",
):
    # [ToDo]
    # - make -P work when length is ALSO parsed from -f. Decide what happens if disagreement.
    # data = []
    t_0 = time.monotonic()
    logger.info(f"parsing {len(sample_ids)} samples from '{orthogroup_fn}'")
    rows = []
    with open(orthogroup_fn) as orthogroup_fh:
        for line in orthogroup_fh:
            rows.append(line.rstrip("\n").split(" "))
    with tqdm.tqdm(
        total=len(rows),
        desc=definitions.PROGRESS_DESC_ORTHOGROUPS_PARSE,
        ncols=definitions.PROGRESS_NCOLS,
    ) as pbar:
        _element_ids = []
        _orthogroup_ids = []
        _sample_ids = []
        for row in rows:
            orthogroup_id, element_ids = row[0].replace(":", ""), row[1:]
            for element_id in element_ids:
                _element_ids.append(element_id)
                _orthogroup_ids.append(orthogroup_id)
                if sample_ids_source == "parse":
                    _sample_ids.append(element_id.split(".")[0])
            pbar.update()
    data = {
        "orthogroup_id": _orthogroup_ids,
        "element_id": _element_ids,
    }
    dtypes = {
        "orthogroup_id": "category",
        "element_id": str,
    }
    if sample_ids_source == "parse":
        data["sample_id"] = _sample_ids
        dtypes["sample_id"] = "category"
    df_orthogroups = pd.DataFrame.from_dict(data=data).astype(dtypes)
    logger.info("orthogroups parsed")
    duplicated_elements_count = int(
        (df_orthogroups["element_id"].value_counts() > 1).value_counts().get(True, 0)
    )
    if duplicated_elements_count > 0:
        duplicated_element_ids = (
            df_orthogroups["element_id"]
            .value_counts()
            .reset_index()
            .query("count > 1")["element_id"]
            .to_list()
        )
        logger.error(
            f"{core.utils.format_number(duplicated_elements_count)} duplicated element(s) encountered in {orthogroup_fn}: {' '.join(duplicated_element_ids)}"
        )
        sys.exit(1)
    if not sample_ids_source == "parse":
        logger.info("inferring sample_ids for orthogroups (this might take a while)...")
        df_elements = (
            core.utils.get_elements_df()
            .set_index("element_id")
            .astype({"sample_id": "category"})
        )
        df_orthogroups["sample_id"] = df_orthogroups["element_id"].map(
            df_elements["sample_id"],
            na_action="ignore",
        )
        df_orthogroups = df_orthogroups[
            ~df_orthogroups["sample_id"].isna()
        ].reset_index(drop=True)
    logger.info(
        f"{core.utils.format_number(len(df_orthogroups['orthogroup_id'].unique()))} orthogroup(s) in file"
    )
    logger.info(
        f"{core.utils.format_number(len(df_orthogroups.index))} element(s) in file"
    )
    logger.info(
        f"{core.utils.format_number(len(list(df_orthogroups['sample_id'].unique())))} sample ID(s) in file"
    )
    if df_orthogroups.empty:
        logger.error(
            f"none of these sample IDs were found: {', '.join(sample_ids)}. Exiting."
        )
        sys.exit(1)
    # [DUMP OGS]
    core.utils.dump(
        df_orthogroups,
        fn=core.utils.format_fn(
            definitions.ORTHOGROUPS_FN,
            prefix=core.utils.get_dir("INPUT"),
        ),
        index=False,
    )
    # [GET COUNTS]
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
    # [DUMP COUNTS]
    core.utils.dump(
        df_counts,
        fn=core.utils.format_fn(
            fn=f"{definitions.COUNTS_FN}",
            prefix=core.utils.get_dir("INPUT"),
        ),
        index=True,
    )
    core.utils.dump(
        df_counts.replace(0, np.nan),
        fn=core.utils.format_fn(
            fn=definitions.COUNTS_NAN_FN,
            prefix=core.utils.get_dir("TMP"),
        ),
        index=True,
    )
    logger.info(
        core.utils.format_elapsed(time.monotonic() - t_0),
    )

def do_parse_earlgrey_task(task):
    """
    ["family", "class", "subclass", "span", "count"]
    # Earlgrey
    ## TE Family   Coverage (bp)   Copy Number
    ## {name}#{superfamily}/{family}
    A-RICH#Low_complexity   27522   592
    => ["A-RICH", "Other", "Low_complexity"]
    RND-1_FAMILY-11#RC/Helitron 6212    29
    => ["RND-1_FAMILY-11", "RC", "Helitron"]
    RND-2_FAMILY-54#LINE/RTE-RTE    4389    19
    => ["RND-2_FAMILY-54", "LINE", "RTE-RTE"]
    (AAT)N#Simple_repeat    2530    59
    => ["(AAT)N", "Other", "Simple_repeat"]
    RND-1_FAMILY-6#Unknown  2488    7
    => ["RND-1_FAMILY-6", "Other", "Unknown"]
    RND-1_FAMILY-24#DNA/TcMar-Tc1   44617   42
    => ["RND-1_FAMILY-24", "DNA", "TcMar-Tc1"]
    """
    try:
        HEADER = [
            "te_family",
            "coverage",
            "copies",
        ]
        HEADER_VALID = set(HEADER)
        rows = []
        with open(task.fn) as fh:
            header = None
            for line in fh:
                if header is None:
                    header = HEADER
                else:
                    row = {
                        h: r for h, r in zip(header, line.split()) if h in HEADER_VALID
                    }
                    repeat_family, repeat_class_subclass = row["te_family"].split("#")
                    repeat_class_subclass = repeat_class_subclass.split("/")
                    rows.append(
                        {
                            "span": int(row["coverage"]),
                            "count": int(row["copies"]),
                            "repeat_family": repeat_family,
                            "repeat_class": "Other"
                            if len(repeat_class_subclass) == 1
                            else repeat_class_subclass[0],
                            "repeat_subclass": repeat_class_subclass[0]
                            if len(repeat_class_subclass) == 1
                            else repeat_class_subclass[1],
                        }
                    )
        df_repeats = pd.DataFrame().from_dict(rows)
        groups = ["repeat_class", "repeat_subclass", "repeat_family"]
        for group in groups:
            df_group = df_repeats.groupby(group).agg(
                span=("span", "sum"),
                count=("repeat_family", "sum"),
            )
            df_group["sample_id"] = task.sample_id
            core.utils.dump(
                df_group,
                fn=core.utils.format_fn(
                    f"{task.sample_id}.{group},{definitions.REPEATS_FN}",
                    prefix=core.utils.get_dir("TMP") / task.sample_id,
                ),
                index=False,
            )
        core.utils.dump(
            df_group,
            fn=core.utils.format_fn(
                f"{task.sample_id}.{definitions.REPEATS_FN}",
                prefix=core.utils.get_dir("TMP") / task.sample_id,
            ),
            index=False,
        )
    except Exception as exc:
        logger.error(f"problem reading {task.fn} - {exc}")


def do_parse_repeatmasker_task(task):
    """
    # RM
    ["family", "class", "subclass", "span", "count"]
    431  19.4  0.0  2.0  CM057379    10748   10847 (207354771) +  aSto-6.9027    LTR/ERV                897  994 (6786)     29
    => ["aSto-6.9027", "LTR", "ERV", (10847-10748-1), 1]
    401  38.6  8.0  0.5  CM057379    13000   13374 (207352244) C  LTR78B         LTR/ERV1             (576)  720    318     35
    => ["LTR78B", "LTR", "ERV1", (13374-13000-1), 1]
     21  15.2  1.4  9.2  CM057379    14076   14145 (207351473) +  (CCCGC)n       Simple_repeat            1   65    (0)     37
    => ["(CCCGC)n", "Other", "Simple_repeat", (13374-13000-1), 1]
    976   5.1  0.0  4.4  CM057379    14957   15099 (207350519) C  5S-Sauria      SINE/5S-Sauria-RTE   (211)  137      1     38
    => ["5S-Sauria", "SINE", "5S-Sauria-RTE", (15099-14957-1), 1]
     17  22.6  4.5  4.5  CM057379    15821   15887 (207349731) +  GA-rich        Low_complexity           1   67    (0)     40
    => ["GA-rich", "Other", "Low_complexity", (15099-14957-1), 1]
     14   4.9  0.0  0.0  CM057379    16566   16586 (207349032) +  (GCGG)n        Simple_repeat            1   21    (0)     43
    => ["(GCGG)n", "Other", "Simple_repeat", (16586-16566-1), 1]
    951   2.5  0.0  0.0  CM057379    16718   16838 (207348780) C  5S             rRNA/rRNA              (0)  121      1     45
    => ["5S", "rRNA", "rRNA", (16838-16718-1), 1]
    """
    HEADER = [
        "score",
        "div",
        "del",
        "ins",
        "sequence",
        "qstart",
        "qend",
        "qleft",
        "C",
        "repeat",
        "family",
        "mstart",
        "mend",
        "mleft",
        "ID",
        "last",
    ]
    HEADER_VALID = set(
        [
            "div",
            "qstart",
            "qend",
            "repeat",
            "family",
        ]
    )
    rows = []
    if task.fn is not None:
        with open(task.fn) as fh:
            header = None
            for line in fh:
                if header is None:
                    header = HEADER
                else:
                    row = {
                        h: r for h, r in zip(header, line.split()) if h in HEADER_VALID
                    }
                    if (
                        task.params.get("min_div", 0.0)
                        <= float(row["div"])
                        <= task.params.get("max_div", 100.0)
                    ):
                        repeat_class_subclass = row["family"].split("/")
                        rows.append(
                            {
                                # "span": int(row["qend"]) - int(row["qstart"]) + 1,
                                "repeat_family": row["repeat"],
                                "repeat_class": "Other"
                                if len(repeat_class_subclass) == 1
                                else repeat_class_subclass[0],
                                "repeat_subclass": repeat_class_subclass[0]
                                if len(repeat_class_subclass) == 1
                                else repeat_class_subclass[1],
                            }
                        )
        df_repeats = pd.DataFrame().from_dict(rows)
        groups = ["repeat_class", "repeat_subclass", "repeat_family"]
        for group in groups:
            df_group = df_repeats.groupby(group).agg(
                # span=("span", "sum"),
                count=("repeat_family", "count"),
            )
            df_group["sample_id"] = task.sample_id
            core.utils.dump(
                df_group,
                fn=core.utils.format_fn(
                    f"{task.sample_id}.{group}.{definitions.REPEATS_FN}",
                    prefix=core.utils.get_dir("TMP") / task.sample_id,
                ),
                index=False,
            )
        core.utils.dump(
            df_group,
            fn=core.utils.format_fn(
                f"{task.sample_id}.{definitions.REPEATS_FN}",
                prefix=core.utils.get_dir("TMP") / task.sample_id,
            ),
            index=False,
        )
        
def partition_lengths(df_orthogroups, lengths, TGs={}):
    """
    [ToDo]
    - finish
    """
    t_0 = time.monotonic()
    df_orthogroups["length"] = df_orthogroups["element_id"].map(lengths)
    dfs = [
        df_orthogroups.groupby("orthogroup_id").agg(
            EL_mean=("length", "mean"), EL_sd=("length", "std")
        )
    ]
    for TG, TNs in TGs.items():
        dfs.append(
            df_orthogroups.where(df_orthogroups["sample_id"].isin(TNs))
            .groupby("orthogroup_id")
            .agg(TG_EL_mean=("length", "mean"), TG_EL_sd=("length", "std"))
            .rename(columns={"TG_EL_mean": f"{TG}_EL_mean", "TG_EL_sd": f"{TG}_EL_sd"})
        )
    df_lengths = pd.concat(dfs, axis=1).reindex(dfs[0].index)
    logger.info(
        core.utils.format_elapsed(time.monotonic() - t_0),
    )
    return df_lengths


def get_df_entropy(output_fmt="tsv"):
    """
    Entropy is correct. Previous KinFin implementation was off.
    """

    # def entropy2(values, base=2):
    #    return True  # 3.08
    #    values = [str(v) for v in values]
    #    n_labels = len(values)

    #    if n_labels <= 1:
    #        return 0
    #    value, counts = np.unique(values, return_counts=True)
    #    probs = counts / n_labels
    #    n_classes = np.count_nonzero(probs)

    #    if n_classes <= 1:
    #        return 0

    #    ent = 0.0

    #    # Compute entropy
    #    base = math.e if base is None else base
    #    for i in probs:
    #        ent -= i * math.log(i, base)
    #    return ent

    def infer_entropy(values):
        signature_counter = collections.Counter([v for k, v in values.items()])
        return -sum(
            [
                i / signature_counter.total() * math.log2(i / signature_counter.total())
                for i in list(signature_counter.values())
            ]
        )

    def glue_strings(values):
        signature_counter = collections.Counter(
            [v for k, v in values.items() if isinstance(v, str)]
        )
        return (
            "|".join([f"{k}:{v}" for k, v in signature_counter.most_common()])
            if signature_counter
            else np.nan
        )

    t_0 = time.monotonic()
    df_annotation = core.utils.get_interpro_df()[
        [
            "orthogroup_id",
            "analysis",
            "interpro_id",
            "go_annotation",
            "signature_id",
            "sample_id",
        ]
    ]
    for analysis in df_annotation["analysis"].unique():
        if isinstance(analysis, str):
            logger.info(f"calculating entropy for {analysis} annotations")
            df_entropy = (
                df_annotation[df_annotation["analysis"] == analysis]
                .groupby("orthogroup_id", as_index=False)
                .agg(
                    **{
                        f"{analysis}_entropy": pd.NamedAgg(
                            column="signature_id",
                            aggfunc=infer_entropy,
                        ),
                        f"{analysis}_ids": pd.NamedAgg(
                            column="signature_id",
                            aggfunc=glue_strings,
                        ),
                        f"{analysis}_SN_COV": pd.NamedAgg(
                            column="sample_id",
                            aggfunc="nunique",
                        ),
                        f"{analysis}_EC_COV": pd.NamedAgg(
                            column="signature_id",
                            aggfunc="count",
                        ),
                        "interpro_entropy": pd.NamedAgg(
                            column="interpro_id",
                            aggfunc=infer_entropy,
                        ),
                        # "interpro_entropy2": pd.NamedAgg(
                        #     column="interpro_id",
                        #     aggfunc=entropy2,
                        # ),
                        "interpro_ids": pd.NamedAgg(
                            column="interpro_id",
                            aggfunc=glue_strings,
                        ),
                        "go_entropy": pd.NamedAgg(
                            column="go_annotation",
                            aggfunc=infer_entropy,
                        ),
                        "go_ids": pd.NamedAgg(
                            column="go_annotation",
                            aggfunc=glue_strings,
                        ),
                    }
                )
                .set_index("orthogroup_id")
            )
            df_counts = core.utils.get_counts_df()
            df_entropy[f"{analysis}_SN_COV"] /= df_counts.ge(1).sum(axis=1)
            df_entropy[f"{analysis}_EC_COV"] /= df_counts.sum(axis=1)
            core.utils.dump(
                df_entropy[
                    [
                        f"{analysis}_SN_COV",
                        f"{analysis}_EC_COV",
                        f"{analysis}_entropy",
                        f"{analysis}_ids",
                        "interpro_entropy",
                        # "interpro_entropy2",
                        "interpro_ids",
                        "go_entropy",
                        "go_ids",
                    ]
                ],
                fn=core.utils.format_fn(
                    fn=f"{definitions.ENTROPY_FN}.{analysis}.{output_fmt}",
                    prefix=core.utils.get_dir("ANNOTATION"),
                ),
                index=True,
            )
    logger.info(
        core.utils.format_elapsed(time.monotonic() - t_0),
    )


def get_df_table(fn, df_orthogroups):
    # [ToDo]
    # - finish thinking about this
    # - decide how to expose to user. Args-config-json as mentioned by RC
    # - drop as table
    t_0 = time.monotonic()
    logger.info(f"parsing '{fn}'")
    df_table = core.utils.load(fn)
    try:
        annotations_valid = df_table["element_id"].isin(df_orthogroups["element_id"])
        annotations_valid_count = int(annotations_valid.value_counts().get(True, 0))
        annotations_orphan_count = int(annotations_valid.value_counts().get(False, 0))
        if annotations_orphan_count:
            logger.warning(
                f"found {core.utils.format_number(annotations_orphan_count)} orphan annotation(s). Not part of any Orthogroup"
            )
            core.utils.dump(
                df_table[~annotations_valid],
                fn=core.utils.format_fn(fn, suffix=".orphans.tsv"),
                index=False,
            )
        if annotations_valid_count:
            logger.info(
                f"found {core.utils.format_number(annotations_valid_count)} annotation(s) of elements in Orthogroups"
            )
            core.utils.dump(
                df_table[annotations_valid],
                fn=core.utils.format_fn(fn, suffix=".filtered.tsv"),
                index=False,
            )
    except NameError:
        logger.error("missing column 'element_id'")
    logger.info(
        core.utils.format_elapsed(time.monotonic() - t_0),
    )
    return df_table[annotations_valid]


def infer_cog_type(values, count_target, count_min, count_max, count_fraction):
    if np.all(values == count_target):
        return "true_cog"
    elif np.mean((values >= count_min) & (values <= count_max)) >= count_fraction:
        return "fuzzy_cog"
    else:
        return "no_cog"


def compare(task):
    _COLUMNS = ["EC_TG1", "OT", "CT"]
    compare_rows = []
    df_sampling = None
    for label, tags in zip(task.labels, task.tags):
        directory = core.utils.get_dir("PARTITION") / label
        if not compare_rows:
            for idx, tag in enumerate(tags):
                fn = (
                    directory
                    / f"{label}.{tag}_vs_{definitions.REMAINDER_LABEL}.partition.{task.output_fmt}"
                )
                if task.output_fmt == "tsv":
                    df = core.utils.load(fn)
                else:
                    df = core.utils.load(fn, columns=_COLUMNS)
                OC = len(df.index)
                mask_absent = df["OT"] == "absent"
                mask_present = df["OT"] != "absent"
                mask_singleton = df["OT"] == "singleton"
                mask_specific = df["OT"] == "specific"
                mask_shared = df["OT"] == "shared"
                mask_cog_true = df["CT"] == "true_cog"
                mask_cog_fuzzy = df["CT"] == "fuzzy_cog"
                EC_TG = int(df[mask_present]["EC_TG1"].sum())
                SC_TG = len(task.taxon_groups[idx])
                df_sampling = (
                    df[mask_present][
                        [
                            "OT",
                            "EC_TG1",
                        ]
                    ]
                    .reset_index(drop=True)
                    .rename(
                        columns={
                            "EC_TG1": "EC",
                            "OT": "OT",
                        }
                    )
                    .replace(
                        {
                            "specific": "2_specific",
                            "shared": "1_shared",
                            "singleton": "3_singleton",
                        }
                    )
                    .sort_values(
                        ["OT", "EC"],
                        ascending=[True, True],
                        ignore_index=True,
                    )
                    .reset_index(names="OC")
                    .replace(
                        {
                            "2_specific": "specific",
                            "1_shared": "shared",
                            "3_singleton": "singleton",
                        }
                    )
                )
                df_sampling["OC"] += 1
                df_sampling["EC"] = df_sampling["EC"].cumsum()
                df_sampling["ECn"] = df_sampling["EC"].div(EC_TG)
                df_sampling["OCn"] = df_sampling["OC"].div(OC)
                core.utils.dump(
                    downcast(
                        df_sampling[
                            [
                                "OT",
                                "EC",
                                "OC",
                                "ECn",
                                "OCn",
                            ]
                        ],
                        categorical=["OT"],
                    ),
                    fn=core.utils.format_fn(
                        fn=f"{label}.{tag}.{SC_TG}.curve.{task.output_fmt}",
                        prefix=core.utils.get_dir("PARTITION") / label,
                    ),
                    index=False,
                )
                compare_row = {}
                compare_row["label"] = label
                compare_row["tag"] = tag
                compare_row["SC"] = SC_TG
                compare_row["OC"] = len(df[mask_present].index)
                compare_row["EC"] = EC_TG
                compare_row["OC_singleton"] = len(
                    df[mask_present & mask_singleton].index
                )
                compare_row["EC_singleton"] = int(
                    df[mask_present & mask_singleton]["EC_TG1"].sum()
                )
                compare_row["OC_specific"] = len(df[mask_present & mask_specific].index)
                compare_row["EC_specific"] = int(
                    df[mask_present & mask_specific]["EC_TG1"].sum()
                )
                compare_row["OC_shared"] = len(df[mask_present & mask_shared].index)
                compare_row["EC_shared"] = int(
                    df[mask_present & mask_shared]["EC_TG1"].sum()
                )
                compare_row["OC_absent"] = len(df[mask_absent].index)
                compare_row["OC_specific_COG_true"] = len(
                    df[mask_present & mask_specific & mask_cog_true].index
                )
                compare_row["OC_specific_COG_fuzzy"] = len(
                    df[mask_present & mask_specific & mask_cog_fuzzy].index
                )
                compare_row["OC_shared_COG_true"] = len(
                    df[mask_present & mask_shared & mask_cog_true].index
                )
                compare_row["OC_shared_COG_fuzzy"] = len(
                    df[mask_present & mask_shared & mask_cog_fuzzy].index
                )
                compare_rows.append(compare_row)
        else:
            compare_rows[idx]["label"] = label
            compare_rows[idx]["tag"] = tag
            core.utils.dump(
                downcast(
                    df_sampling[
                        [
                            "OT",
                            "EC",
                            "OC",
                            "ECn",
                            "OCn",
                        ]
                    ],
                    categorical=["OT"],
                ),
                fn=core.utils.format_fn(
                    fn=f"{label}.{tag}.{SC_TG}.curve.{task.output_fmt}",
                    prefix=core.utils.get_dir("PARTITION") / label,
                ),
                index=False,
            )
        core.utils.dump(
            downcast(pd.DataFrame.from_dict(compare_rows)),
            fn=core.utils.format_fn(
                fn=f"{label}.summary.{task.output_fmt}",
                prefix=core.utils.get_dir("PARTITION") / label,
            ),
            index=False,
        )
    return True


def contrast(task):
    TG_1, TG_2 = task.taxon_groups
    df_counts = core.utils.get_counts_df(
        columns=sum([("orthogroup_id",), TG_1, TG_2], ()),
        nan=True,
    )
    df_counts_TG1 = df_counts.loc[:, TG_1]
    df_counts_TG2 = df_counts.loc[:, TG_2]
    df_partition_list = []
    df_partition_list.append(df_counts.ge(1).sum(axis=1).rename("SC"))
    df_partition_list.append(df_counts_TG1.ge(1).sum(axis=1).rename("SC_TG1"))
    df_partition_list.append((df_partition_list[1] / len(TG_1)).rename("SP_TG1"))
    df_partition_list.append(df_counts_TG2.ge(1).sum(axis=1).rename("SC_TG2"))
    df_partition_list.append((df_partition_list[3] / len(TG_2)).rename("SP_TG2"))
    df_partition_list.append(df_counts.sum(axis=1).astype(int).rename("EC"))
    df_partition_list.append(df_counts_TG1.sum(axis=1).astype(int).rename("EC_TG1"))
    df_partition_list.append(df_counts_TG2.sum(axis=1).astype(int).rename("EC_TG2"))
    df_partition_list.append(
        pd.Series(
            np.select(
                condlist=[
                    (df_partition_list[6] == 0),
                    (df_partition_list[5] == 1),
                    (df_partition_list[7] == 0),
                ],
                choicelist=[
                    "absent",
                    "singleton",
                    "specific",
                ],
                default="shared",
            ),
            index=df_counts.index,
        ).rename("OT")
    )
    df_partition_list.append(
        (df_counts.eq(task.count_target).sum(axis=1) / len(df_counts.columns)).rename(
            "CSP"
        )
    )
    df_partition_list.append(
        (df_counts_TG1.eq(task.count_target).sum(axis=1) / len(TG_1)).rename("CSP_TG1")
    )
    df_partition_list.append(
        pd.Series(
            np.select(
                condlist=[
                    np.all(df_counts_TG1.eq(task.count_target), axis=1),
                    np.mean(
                        (df_counts_TG1 >= task.count_min)
                        & (df_counts_TG1 <= task.count_max),
                        axis=1,
                    )
                    >= task.count_fraction,
                ],
                choicelist=[
                    "true_cog",
                    "fuzzy_cog",
                ],
                default="no_cog",
            ),
            index=df_counts.index,
        ).rename("CT")
    )
    df_partition_list.append(df_counts.mean(axis=1).rename("EC_mean"))
    df_partition_list.append(df_counts_TG1.mean(axis=1).rename("EC_mean_TG1"))
    df_partition_list.append(df_counts_TG2.mean(axis=1).rename("EC_mean_TG2"))
    df_partition_list.append(
        pd.Series(
            np.log2(df_partition_list[13] / df_partition_list[14]),
            index=df_counts.index,
        ).rename("l2m(TG1/TG2)")
    )
    df_partition_list.append(
        pd.Series(
            scipy.stats.mannwhitneyu(
                df_counts_TG1,
                df_counts_TG2,
                method="asymptotic",
                alternative="two-sided",
                nan_policy="omit",
                axis=1,
                keepdims=False,
            )[1],
            index=df_counts.index,
        ).rename("pvalue")
    )
    df_partition_list.append(df_counts.median(axis=1, skipna=True).rename("EC_median"))
    df_partition_list.append(
        df_counts_TG1.median(axis=1, skipna=True).rename("EC_median_TG1")
    )
    df_partition_list.append(
        df_counts_TG2.median(axis=1, skipna=True).rename("EC_median_TG2")
    )
    df_partition = pd.concat(df_partition_list, axis=1)
    df_partition = df_partition[
        [
            "OT",
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
            "l2m(TG1/TG2)",
            "pvalue",
            "EC_median",
            "EC_median_TG1",
            "EC_median_TG2",
            "CT",
            "CSP",
            "CSP_TG1",
        ]
    ]
    for idx, label in enumerate(task.labels):
        TG1_tag, TG2_tag = task.tags[idx]
        fn = f"{label}.{TG1_tag}_vs_{TG2_tag}"
        # [SAMPLE IDS]
        core.utils.dump(
            pd.DataFrame.from_records(
                [{"TG": "1", "sample_id": SN, "label": TG1_tag} for SN in TG_1]
                + [{"TG": "2", "sample_id": SN, "label": TG2_tag} for SN in TG_2]
            ),
            fn=core.utils.format_fn(
                fn=(f"{fn}.sample_ids.tsv"),
                prefix=core.utils.get_dir("PARTITION") / label,
            ),
            index=False,
        )
        # [CONTRAST]
        core.utils.dump(
            downcast(df_partition.reset_index(), categorical=["CT"]),
            fn=core.utils.format_fn(
                fn=(f"{fn}.partition.{task.output_fmt}"),
                prefix=core.utils.get_dir("PARTITION") / label,
            ),
            index=False,
        )
    return True


def do_task(task):
    if task.type == "SummaryTask":
        return compare(task)
    elif task.type == "ComparisonTask":
        return contrast(task)
    elif task.type == "ParseTask":
        return do_parse_fasta_task(task)
    elif task.type == "interpro":
        return do_parse_interpro_task(task)
    elif task.type == "AnnotationTask":
        return do_annotation_task(task)
    else:
        raise ValueError(f"unknown task type: {task}")


def do_tasks(
    tasks=[],
    desc="",
    processes=1,
    collect_results=False,
):
    t_0 = time.monotonic()
    _TOTAL = len(tasks)
    _DESC = desc
    _NCOLS = definitions.PROGRESS_NCOLS
    results = [] if collect_results else None
    if processes > 1:
        with tqdm.tqdm(total=_TOTAL, desc=_DESC, ncols=_NCOLS) as t:
            with poolcontext(processes=processes) as pool:
                for _ in pool.imap_unordered(do_task, tasks):
                    if collect_results:
                        results.append(_)
                    t.update()
    else:
        for task in tqdm.tqdm(tasks, total=_TOTAL, desc=_DESC, ncols=_NCOLS):
            _ = do_task(task)
            if collect_results:
                results.append(_)
    logger.info(
        core.utils.format_elapsed(time.monotonic() - t_0),
    )
    return results


def get_summary_tasks(
    df_config=None,
    output_fmt="tsv",
    ignore_sample_comparisons=False,
):
    t_0 = time.monotonic()
    collector = collections.defaultdict(list)
    taxon_groups = get_taxon_groups(
        df_config.to_dict(orient="records"),
        ignore_sample_comparisons=ignore_sample_comparisons,
    )
    for key in taxon_groups:
        collector_key = tuple([tuple(TG) for TG in taxon_groups[key].values()])
        collector_value = tuple(
            [key] + [TG_label for TG_label in taxon_groups[key].keys()]
        )
        collector[collector_key].append(collector_value)
    tasks = []
    for taxon_groups, v in collector.items():
        labels = [label[0] for label in v]
        tags = [label[1:] for label in v]
        tasks.append(
            SummaryTask(
                type="SummaryTask",
                taxon_groups=taxon_groups,
                labels=labels,
                tags=tags,
                output_fmt=output_fmt,
            )
        )
    logger.info(
        core.utils.format_elapsed(time.monotonic() - t_0),
    )
    return tasks


def get_comparison_tasks(
    df_config=None,
    count_target=1,
    count_min=0,
    count_max=2,
    count_fraction=0.75,
    output_fmt="tsv",
    ignore_sample_comparisons=False,
):
    t_0 = time.monotonic()
    collector = collections.defaultdict(list)
    taxon_groups = get_taxon_groups(
        df_config.to_dict(orient="records"),
        ignore_sample_comparisons=ignore_sample_comparisons,
    )
    combinations = []
    for key in taxon_groups:
        combinations += get_combinations(taxon_groups, key)
    for TG_1, TG_2, (grouping, label_1, label_2) in sorted(combinations):
        collector_key = (TG_1, TG_2)
        collector_value = (grouping, label_1, label_2)
        collector[collector_key].append(collector_value)
    tasks = []
    for taxon_groups, v in collector.items():
        labels = [label[0] for label in v]
        tags = [label[1:] for label in v]
        task = ComparisonTask(
            type="ComparisonTask",
            taxon_groups=taxon_groups,
            labels=labels,
            tags=tags,
            count_target=count_target,
            count_min=count_min,
            count_max=count_max,
            count_fraction=count_fraction,
            output_fmt=output_fmt,
        )
        tasks.append(task)
    logger.info(
        core.utils.format_elapsed(time.monotonic() - t_0),
    )
    return tasks


def get_taxids(
    df_config,
    output_dir=definitions.CWD,
    output_fmt="csv",
    update_taxdump=False,
    update_taxonomy=False,
):
    t_0 = time.monotonic()
    df_taxonomy = core.taxonomy.load_taxonomy_df(
        update_taxdump=update_taxdump,
        update_taxonomy=update_taxonomy,
        index="name",
    )
    # remove duplicated names!
    df_taxonomy = df_taxonomy[~df_taxonomy.index.duplicated(keep=False)]

    def infer_taxonomy(value):
        taxid_dict = core.taxonomy.get_taxid(
            value,
            df_taxonomy,
        )
        return pd.Series(taxid_dict)

    logger.info(
        f"querying NCBI TaxDump (created: {df_taxonomy.attrs['created']}) for TaxIDs based on sample IDs"
    )
    df_config = pd.concat(
        (df_config, df_config["sample_id"].apply(infer_taxonomy)), axis=1
    )
    df_config_missing = df_config[
        df_config["taxid"] == definitions.CONFIG_KEYWORD_MISSING
    ]
    if len(df_config.index) == len(df_config_missing.index):
        logger.error(
            f"no TaxIDs could be assigned. Make sure sample IDs are in NCBI Taxonomy ({definitions.TAXONOMY_USER_URL})"
        )
        return False
    elif len(df_config_missing.index) > 0:
        logger.warning(
            f"{core.utils.format_number(len(df_config_missing.index))} TaxIDs could not be assigned. Reasons may include changes in taxonomy (by NCBI), typos (by you), or edge cases such as complex and/or duplicated entries. Please consult NCBI Taxonomy ({definitions.TAXONOMY_USER_URL}) to manually curate your config file!"
        )
        core.utils.dump(
            df_config_missing,
            fn=core.utils.format_fn(
                "kinfin.config.taxids.missing.csv",
                prefix=output_dir,
            ),
            index=False,
        )
    else:
        pass
    core.utils.dump(
        df_config,
        fn=core.utils.format_fn(
            "kinfin.config.taxids.csv",
            prefix=output_dir,
        ),
        index=False,
    )
    logger.info(
        core.utils.format_elapsed(time.monotonic() - t_0),
    )
    return df_config


def get_taxonomy(
    df_config,
    taxonomic_ranks,
):
    t_0 = time.monotonic()
    df_taxonomy = core.taxonomy.load_taxonomy_df(index="node")

    def infer_taxonomy(value):
        try:
            value = str(int(value))
            taxonomy_dict = core.taxonomy.get_lineage(
                str(value),
                df_taxonomy,
                taxonomic_ranks=taxonomic_ranks,
            )
            return pd.Series(taxonomy_dict)
        except ValueError:
            return pd.Series({rank: value for rank in taxonomic_ranks})  # value = None

    logger.info(
        f"adding taxonomic information for the following ranks: {', '.join(taxonomic_ranks)}"
    )
    df_config = pd.concat(
        (df_config, df_config["taxid"].apply(infer_taxonomy)), axis=1
    ).convert_dtypes()
    logger.info(
        core.utils.format_elapsed(time.monotonic() - t_0),
    )
    return df_config.drop(["taxid"], axis=1)


def get_config(
    config_fn,
    taxonomic_ranks=[
        "genus",
        "species",
    ],
):
    df_config = core.utils.load(config_fn).convert_dtypes()
    if df_config.empty:
        logger.error("config is empty")
        sys.exit(1)
    if "sample_id" not in df_config.columns:
        logger.error("column 'sample_id' not found")
        sys.exit(1)
    parsed_rows = len(df_config.index)
    parsed_cols = len(df_config.columns)
    logger.info(f"found {core.utils.format_number(parsed_rows)} sample ID(s)")
    taxids_comment = "(including 'taxid')" if "taxid" in df_config.columns else ""
    logger.info(
        f"found {core.utils.format_number(parsed_cols)} grouping(s) {taxids_comment}"
    )
    if "taxid" not in df_config.columns:
        if taxonomic_ranks:
            logger.warning(
                f"no taxids provided in config. Can't lookup taxonomic ranks: {taxonomic_ranks}"
            )
    else:
        df_config = get_taxonomy(df_config, taxonomic_ranks=taxonomic_ranks)
    header = "[Config] "
    lines = [line for line in df_config.__repr__().split("\n")]
    logger.debug(f"{header}" + "#" * (len(lines[0]) - len(header)))
    for line in lines:
        logger.debug(f"{line}")
    logger.debug("#" * len(lines[0]))
    assert len(df_config.index) == parsed_rows, (
        f"{len(df_config.index)=} != {parsed_rows=}"
    )
    core.utils.dump(
        df_config,
        fn=core.utils.format_fn(
            config_fn,
            prefix=core.utils.get_dir("INPUT"),
            suffix=".csv",
        ),
        index=False,
    )
    core.utils.dump(
        df_config.to_dict(orient="records"),
        fn=core.utils.format_fn(
            config_fn,
            prefix=core.utils.get_dir("INPUT"),
            suffix=".parsed.json",
        ),
        index=False,
    )
    return df_config


def get_taxon_groups(config_dicts, ignore_sample_comparisons=False):
    taxon_groups = collections.defaultdict(lambda: collections.defaultdict(list))
    taxon_groups["sample_ids"]["all"] = [
        record.get("sample_id", None) for record in config_dicts
    ]
    for record in config_dicts:
        sample_id = record.get("sample_id", None)
        for k, v in record.items():
            if v is not None:
                taxon_groups[k][v].append(sample_id)
    if ignore_sample_comparisons:
        del taxon_groups["sample_id"]
    return taxon_groups


def get_combinations(taxon_groups, key):
    combinations = []
    for (label_1, TNs_1), (label_2, TNs_2) in sorted(
        itertools.combinations({k: v for k, v in taxon_groups[key].items()}.items(), 2)
    ):
        if (
            len(TNs_1) > definitions.CONFIG_MIN_SAMPLE_IDS
            or len(TNs_2) > definitions.CONFIG_MIN_SAMPLE_IDS
        ):
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
    for TNs_label, TNs in taxon_groups[key].items():
        TNs_set = set(TNs)
        TNs_remainder = [
            TN for TN in taxon_groups["sample_ids"]["all"] if TN not in TNs_set
        ]
        combinations.append(
            (
                tuple(sorted(TNs)),
                tuple(sorted(TNs_remainder)),
                tuple(
                    [
                        key,
                        TNs_label,
                        definitions.REMAINDER_LABEL,
                    ]
                ),
            )
        )
    return sorted(combinations)


if __name__ == "__main__":
    pass
