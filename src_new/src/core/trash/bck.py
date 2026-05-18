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
