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

import ete4
import numpy as np
import pandas as pd
import scipy
import tqdm

import core.log
import core.taxonomy
import core.utils
import definitions

logger = logging.getLogger(__name__)

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

ComparisonTask = collections.namedtuple(
    "ComparisonTask",
    [
        "type",
        "labels",
        "tags",
        "taxon_groups",
        "df_counts_fn",
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
"""


def get_fasta_df(payload):
    sample_id, fn = payload
    try:
        data = []
        for header, length in core.utils.iter_seq_length(fn):
            data.append((header, sample_id, length))
        df_fasta = pd.DataFrame().from_records(
            data, columns=["element_id", "sample_id", "length"]
        )
        if not df_fasta.empty:
            return core.utils.dump(
                df_fasta,
                fn=core.utils.format_fn(
                    f"{sample_id}.elements.{definitions.STD_FORMAT}",
                    prefix=core.utils.get_dir("TMP"),
                ),
                index=False,
            )
        else:
            logger.warning(f"no sequences found in {fn}")
    except Exception as exc:
        logger.error(f"problem reading {fn} - {exc}")
        return False


def get_ids(
    sequence_ids_fn=None,
    species_ids_fn=None,
    sample_ids=[],
    output_fmt="tsv",
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
        if not df.empty:
            core.utils.dump(
                df,
                fn=core.utils.format_fn(
                    fn=definitions.ELEMENTS_FN,
                    prefix=core.utils.get_dir("INPUT"),
                ),
                index=False,
            )
            logger.info(
                f"{core.utils.format_number(df['sample_id'].nunique())} sample IDs parsed"
            )
            logger.info(f"{core.utils.format_number(len(df.index))} element IDs")
            return True
        else:
            logger.warning("no IDs could be parsed")
    except Exception as exc:
        logger.error(f"unexpected error - {exc}")
    sys.exit(1)


def get_elements(
    directory=None,
    sample_ids=[],
    processes=1,
    output_fmt="feather",
):
    t_0 = time.monotonic()
    payloads = []
    sample_ids_found = []
    for fasta_extension in definitions.SUPPORTED_FASTA_EXTENSIONS:
        for fn in glob.glob(f"{directory}/*{fasta_extension}"):
            sample_id = pathlib.Path(fn).stem.split(".")[0]
            if sample_id in sample_ids:
                sample_ids_found.append(sample_id)
                payloads.append(
                    (
                        sample_id,
                        fn,
                    )
                )
    if len(payloads) < len(sample_ids):
        logger.error(
            f"FASTA files for the following sample IDs could not be found: {', '.join([set(sample_ids) - set(sample_ids_found)])}"
        )
        sys.exit(1)
    logger.info(f"parsing {len(payloads)} FASTA files using {processes} process(es)")
    df_fns = []
    if processes > 1:
        with tqdm.tqdm(
            total=len(payloads),
            desc=definitions.PROGRESS_DESC_FASTA,
            ncols=definitions.PROGRESS_NCOLS,
        ) as t:
            with poolcontext(processes=processes) as pool:
                for df_fn in pool.imap_unordered(get_fasta_df, payloads):
                    df_fns.append(df_fn)
                    t.update()
    else:
        for payload in tqdm.tqdm(
            payloads,
            total=len(payloads),
            desc=definitions.PROGRESS_DESC_FASTA,
            ncols=definitions.PROGRESS_NCOLS,
        ):
            df_fn = get_fasta_df(payload)
            df_fns.append(df_fn)
    core.utils.dump(
        pd.concat([core.utils.load(df_fn) for df_fn in df_fns]),
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
    output_fmt="feather",
    sample_ids_source="parse",
):
    # [ToDo]
    # - fastOMA parsing:
    #   - maybe do some sort of agnostic iter_orthogroups
    #   - maybe even easier to load
    # - make -P work when length is ALSO parsed from -f. Decide what happens if disagreement.
    data = []
    t_0 = time.monotonic()
    logger.info(f"parsing {len(sample_ids)} samples from '{orthogroup_fn}'")
    if not sample_ids_source == "parse":
        df_elements = core.utils.load(
            fn=(core.utils.get_dir("INPUT") / definitions.ELEMENTS_FN)
        ).set_index("element_id")
    rows = []
    with open(orthogroup_fn) as orthogroup_fh:
        for line in orthogroup_fh:
            rows.append(line.rstrip("\n").split(" "))
    with tqdm.tqdm(
        total=len(rows),
        desc=definitions.PROGRESS_DESC_ORTHOGROUPS_PARSE,
        ncols=definitions.PROGRESS_NCOLS,
    ) as t:
        for row in rows:
            orthogroup_id, element_ids = row[0].replace(":", ""), row[1:]
            for element_id in element_ids:
                if sample_ids_source == "parse":
                    sample_id = element_id.split(".")[0]
                    data.append((element_id, orthogroup_id, sample_id))
                else:
                    data.append((element_id, orthogroup_id))
            t.update()
    if sample_ids_source == "parse":
        df_orthogroups = pd.DataFrame.from_records(
            data,
            columns=[
                "element_id",
                "orthogroup_id",
                "sample_id",
            ],
        )
    else:
        df_orthogroups = pd.DataFrame.from_records(
            data,
            columns=[
                "element_id",
                "orthogroup_id",
            ],
        )
        logger.info(
            "inferring sample_ids for orthogroups (this might take a moment)..."
        )
        df_orthogroups["sample_id"] = df_orthogroups["element_id"].map(
            df_elements["sample_id"],
            na_action="ignore",  # 14s !!
        )
        logger.info("sample IDs inferred!")
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
        logger.error(f"none of these sample IDs were found: {', '.join(sample_ids)}")
        sys.exit(1)
    core.utils.dump(
        df_orthogroups,
        fn=core.utils.format_fn(
            definitions.ORTHOGROUPS_FN,
            prefix=core.utils.get_dir("INPUT"),
        ),
        index=False,
    )
    logger.info(
        core.utils.format_elapsed(time.monotonic() - t_0),
    )
    return df_orthogroups


def get_counts(
    df_orthogroups,
    output_fmt="tsv",
):
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
    core.utils.dump(
        df_counts,
        fn=core.utils.format_fn(
            fn=f"{definitions.COUNTS_FN}.{output_fmt}",
            prefix=core.utils.get_dir("INPUT"),
        ),
        index=True,
    )
    logger.info(
        core.utils.format_elapsed(time.monotonic() - t_0),
    )
    return df_counts


def partition_lengths(df_orthogroups, lengths, TGs={}):
    """
    [ToDo]
    - part of summary or a separate table?

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
    logger.info(
        core.utils.format_elapsed(time.monotonic() - t_0),
    )
    return df_lengths


def get_df_entropy(df_orthogroups, df_interpro, df_counts, analysis="Pfam"):
    # [ToDo]
    # - drop as table
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
    logger.info(
        core.utils.format_elapsed(time.monotonic() - t_0),
    )
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


def get_df_table(fn, df_orthogroups):
    # [ToDo]
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


def get_df_interpro(
    fn,
    df_orthogroups=None,
    output_fmt="tsv",
):
    t_0 = time.monotonic()
    logger.info(f"parsing '{fn}'")
    df_interpro = core.utils.load(
        fn,
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
    annotations_valid_count = annotations_valid.value_counts().get(True, 0)
    annotations_orphan_count = annotations_valid.value_counts().get(False, 0)
    if annotations_valid_count == 0:
        logger.error(
            f"{core.utils.format_number(annotations_valid_count)} valid annotation(s) found"
        )
        logger.error(
            f"{core.utils.format_number(annotations_orphan_count)} orphan annotation(s) found"
        )
        sys.exit(1)
    else:
        logger.info(
            f"{core.utils.format_number(annotations_valid_count)} valid annotation(s) found"
        )
        core.utils.dump(
            df_interpro[annotations_valid],
            fn=core.utils.format_fn(
                fn,
                prefix=core.utils.get_dir("INPUT"),
                suffix=".filtered.tsv",
            ),
            index=False,
        )
        if annotations_orphan_count:
            logger.warning(
                f"{core.utils.format_number(annotations_orphan_count)} orphan annotation(s) found"
            )
            core.utils.dump(
                df_interpro.loc[~annotations_valid],
                fn=core.utils.format_fn(
                    fn,
                    prefix=core.utils.get_dir("INPUT"),
                    suffix=".orphan.tsv",
                ),
                index=False,
            )
        annotated_EP = (
            df_interpro["element_id"].nunique() / df_orthogroups["element_id"].nunique()
        )
        logger.info(f"{annotated_EP:.2%} of elements in orthogroups have annotations")
        df_interpro = df_interpro[annotations_valid]
    logger.info(
        core.utils.format_elapsed(time.monotonic() - t_0),
    )
    return df_interpro


def get_df_annotation(
    df_orthogroups=None,
    df_interpro=None,
    df_counts=None,
    output_fmt="tsv",
):
    _PROPORTIONAL = True
    if df_interpro is None:
        return None
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
            TG_AC=("element_id", "nunique"),
        )
        .set_index(INDEX_ANNOTATION)
        .unstack(fill_value=0)
    )
    df_annotation["EC"] = df_counts.sum(axis=1)
    df_annotation["EC_AC"] = df_annotation["TG_AC"].sum(axis=1)
    df_annotation["EC_AP"] = df_annotation["EC_AC"] / df_annotation["EC"]
    df_annotation["TN_AP"] = (
        df_annotation["TG_AC"].ge(1).sum(axis=1).div(df_counts.ge(1).sum(axis=1))
    )
    df_annotation[
        [
            "EC",
            "EC_AC",
            "EC_AP",
            "TN_AP",
            "TG_AC",
        ]
    ]
    if _PROPORTIONAL is True:
        df_annotation["TG_AC"] = (
            df_annotation["TG_AC"]
            .div(
                df_counts,
            )
            .replace(np.nan, 0.0)
        ).rename(columns={"TG_AC": "TG_AP"})
    df_annotation.columns = [
        (f"{x}_{y}" if y else f"{x}") for x, y in df_annotation.columns.to_flat_index()
    ]
    core.utils.dump(
        df_annotation.reset_index(),
        fn=core.utils.format_fn(
            f"orthogroups.annotated.{output_fmt}",
            prefix=core.utils.get_dir("ANNOTATION"),
        ),
        index=False,
    )
    logger.info(f"[elapsed: {time.monotonic() - t_0}")
    return df_annotation


def infer_cog_type(values, count_target, count_min, count_max, count_fraction):
    if np.all(values == count_target):
        return "true_cog"
    elif np.mean((values >= count_min) & (values <= count_max)) >= count_fraction:
        return "fuzzy_cog"
    else:
        return "no_cog"


def compare(task):
    _COLUMNS = ["EC_TG1", "OG_type_TG1", "COG_type_TG1"]
    rows = []
    for label, tags in zip(task.labels, task.tags):
        directory = core.utils.get_dir("PARTITION") / label
        if not rows:
            for idx, tag in enumerate(tags):
                fn = (
                    directory
                    / f"partition.{label}.{tag}_vs_{definitions.REMAINDER_LABEL}.contrast.{task.output_fmt}"
                )
                if task.output_fmt == "tsv":
                    df = core.utils.load(fn)
                else:
                    df = core.utils.load(fn, columns=_COLUMNS)
                mask_absent = df["OG_type_TG1"] == "absent"
                mask_present = df["OG_type_TG1"] != "absent"
                mask_singleton = df["OG_type_TG1"] == "singleton"
                mask_specific = df["OG_type_TG1"] == "specific"
                mask_shared = df["OG_type_TG1"] == "shared"
                mask_cog_true = df["COG_type_TG1"] == "true_cog"
                mask_cog_fuzzy = df["COG_type_TG1"] == "fuzzy_cog"
                row = {}
                row["label"] = label
                row["tag"] = tag
                row["SC"] = len(task.taxon_groups[idx])
                row["OC"] = len(df[mask_present].index)
                row["EC"] = int(df[mask_present]["EC_TG1"].sum())
                row["OC_singleton"] = len(df[mask_present & mask_singleton].index)
                row["EC_singleton"] = int(
                    df[mask_present & mask_singleton]["EC_TG1"].sum()
                )
                row["OC_specific"] = len(df[mask_present & mask_specific].index)
                row["EC_specific"] = int(
                    df[mask_present & mask_specific]["EC_TG1"].sum()
                )
                row["OC_shared"] = len(df[mask_present & mask_shared].index)
                row["EC_shared"] = int(df[mask_present & mask_shared]["EC_TG1"].sum())
                row["OC_absent"] = len(df[mask_absent].index)
                row["OC_specific_COG_true"] = len(
                    df[mask_present & mask_specific & mask_cog_true].index
                )
                row["OC_specific_COG_fuzzy"] = len(
                    df[mask_present & mask_specific & mask_cog_fuzzy].index
                )
                row["OC_shared_COG_true"] = len(
                    df[mask_present & mask_shared & mask_cog_true].index
                )
                row["OC_shared_COG_fuzzy"] = len(
                    df[mask_present & mask_shared & mask_cog_fuzzy].index
                )
                rows.append(row)
        else:
            rows[idx]["label"] = label
            rows[idx]["tag"] = tag
        core.utils.dump(
            pd.DataFrame.from_dict(rows),
            fn=core.utils.format_fn(
                fn=f"{label}.{task.type}.{task.output_fmt}",
                prefix=core.utils.get_dir("PARTITION") / label,
            ),
            index=False,
        )
    return True


def contrast(task):
    """
    - np.nanmedian is not faster
    - .ge() is faster than .mask()
    - dtype="category" does not help in OG_type
    - medians are 42.1% of time
    - pvalue is 20.2% of time
    """
    TG_1, TG_2 = task.taxon_groups
    df_counts = core.utils.load(
        fn=task.df_counts_fn,
        columns=sum([("orthogroup_id",), TG_1, TG_2], ()),
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
                    (df_partition_list[6] >= 1) & (df_partition_list[7] == 0),
                    (df_partition_list[6] >= 1) & (df_partition_list[7] >= 1),
                ],
                choicelist=[
                    "absent",
                    "singleton",
                    "specific",
                    "shared",
                ],
                default="None",
            ),
            index=df_counts.index,
        ).rename("OG_type_TG1")
    )
    # timing["OG_type"], t_i = time.monotonic() - t_i, time.monotonic()
    df_partition_list.append(
        (df_counts.eq(task.count_target).sum(axis=1) / len(df_counts.columns)).rename(
            "COG_TP"
        )
    )
    # timing["COG_TP"], t_i = time.monotonic() - t_i, time.monotonic()
    df_partition_list.append(
        (df_counts_TG1.eq(task.count_target).sum(axis=1) / len(TG_1)).rename(
            "COG_TP_TG1"
        )
    )
    # timing["COG_TP_TG1"], t_i = time.monotonic() - t_i, time.monotonic()
    df_partition_list.append(
        df_counts_TG1.apply(
            infer_cog_type,
            axis=1,
            raw=True,
            args=(
                task.count_target,
                task.count_min,
                task.count_max,
                task.count_fraction,
            ),
        ).rename("COG_type_TG1")
    )
    # timing["COG_type_TG1"], t_i = time.monotonic() - t_i, time.monotonic()
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
        ).rename("log2_mean(TG1/TG2)")
    )
    # timing["log2_mean(TG1/TG2)"], t_i = (
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
    # df_partition_list.append(df_counts.median(axis=1, skipna=True).rename("EC_median"))
    # timing["EC_median"], t_i = time.monotonic() - t_i, time.monotonic()
    # df_partition_list.append(
    #     df_counts_TG1.median(axis=1, skipna=True).rename("EC_median_TG1")
    # )
    # timing["EC_median_TG1"], t_i = time.monotonic() - t_i, time.monotonic()
    # df_partition_list.append(
    #     df_counts_TG2.median(axis=1, skipna=True).rename("EC_median_TG2")
    # )
    # timing["EC_median_TG2"], t_i = time.monotonic() - t_i, time.monotonic()
    # concat
    df_partition = pd.concat(df_partition_list, axis=1)
    # timing["concat"], t_i = time.monotonic() - t_i, time.monotonic()
    df_partition = df_partition[
        [
            "OG_type_TG1",
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
            # "EC_median",
            # "EC_median_TG1",
            # "EC_median_TG2",
            "COG_type_TG1",
            "COG_TP",
            "COG_TP_TG1",
        ]
    ]
    for idx, label in enumerate(task.labels):
        TG1_tag, TG2_tag = task.tags[idx]
        fn = f"partition.{label}.{TG1_tag}_vs_{TG2_tag}"
        # [SAMPLE IDS]
        core.utils.dump(
            pd.DataFrame.from_records(
                [{"TG": "1", "sample_id": TN, "label": TG1_tag} for TN in TG_1]
                + [{"TG": "2", "sample_id": TN, "label": TG2_tag} for TN in TG_2]
            ),
            fn=core.utils.format_fn(
                fn=(f"{fn}.sample_ids.tsv"),
                prefix=core.utils.get_dir("PARTITION") / label,
            ),
            index=False,
        )
        # [CONTRAST]
        core.utils.dump(
            df_partition.reset_index(),
            fn=core.utils.format_fn(
                fn=(f"{fn}.contrast.{task.output_fmt}"),
                prefix=core.utils.get_dir("PARTITION") / label,
            ),
            index=False,
        )
    # timing["dumping"] = time.monotonic() - t_i
    # pprint.pp(timing)
    return True


def do_task(task):
    if task.type == "summary":
        compare(task)
    elif task.type == "comparison":
        contrast(task)
    else:
        raise ValueError(f"unknown task type: {task}")


def do_tasks(
    tasks=[],
    desc="",
    processes=1,
):
    t_0 = time.monotonic()
    logger.info(desc)
    _TOTAL = len(tasks)
    _DESC = definitions.PROGRESS_DESC_PARTITIONING
    _NCOLS = definitions.PROGRESS_NCOLS
    if processes > 1:
        with tqdm.tqdm(total=_TOTAL, desc=_DESC, ncols=_NCOLS) as t:
            with poolcontext(processes=processes) as pool:
                for _ in pool.imap_unordered(do_task, tasks):
                    t.update()
    else:
        for task in tqdm.tqdm(tasks, total=_TOTAL, desc=_DESC, ncols=_NCOLS):
            _ = do_task(task)
    logger.info(
        core.utils.format_elapsed(time.monotonic() - t_0),
    )


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
        task = SummaryTask(
            type="summary",
            taxon_groups=taxon_groups,
            labels=labels,
            tags=tags,
            output_fmt=output_fmt,
        )
        tasks.append(task)
    logger.info(
        core.utils.format_elapsed(time.monotonic() - t_0),
    )
    return tasks


def get_comparison_tasks(
    df_config=None,
    df_counts=None,
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
    df_counts_fn = core.utils.dump(
        # df_counts.replace(0, np.nan)
        df_counts.apply(
            pd.to_numeric,
            downcast="float",  # float32
        ).replace(
            0,
            np.nan,
        ),
        fn=core.utils.format_fn(
            fn="orthogroups.counts.nan.feather",
            prefix=core.utils.get_dir("TMP"),
        ),
        index=True,
    )
    tasks = []
    for taxon_groups, v in collector.items():
        labels = [label[0] for label in v]
        tags = [label[1:] for label in v]
        task = ComparisonTask(
            type="comparison",
            taxon_groups=taxon_groups,
            labels=labels,
            tags=tags,
            df_counts_fn=df_counts_fn,
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


def get_tree(
    fn,
    outgroup=[],
):
    """
    - technically only checks for outgroups. A tree with additional tips should work. 
    """
    if fn is None:
        logger.info("no tree provided")
        tree = None
    else:
        tree = ete4.Tree(fn)
        if outgroup:
            logger.info(f"setting outgroup to {outgroup}")
            try:
                tree.set_outgroup(tree.common_ancestor(outgroup))
            except KeyError as exc:
                logger.error(
                    f"setting outgroup to {outgroup} failed - {exc} not in tree"
                )
                sys.exit(1)
        else:
            logger.warning(
                "no outgroup provided. No outgroup will be set. Verify tree topology"
            )
        zeros = len(str(len(list(tree.traverse()))))
        for idx, node in enumerate(tree.traverse("levelorder")):  # rename nodes
            node.add_prop("name", node.name if node.name else f"{str(idx).zfill(zeros)}")
        tree.write(
            outfile=core.utils.format_fn(
                fn=("tree.with_node_names.nwk"),
                prefix=core.utils.get_dir("TREE"),
            ),
            props=None,
            parser=1,
        )
        tree_strings = tree.to_str(compact=True, props=["name"]).split("\n")
        if len(tree[str(0).zfill(zeros)]) <= definitions.TREE_NODES_MAX_FOR_LOG:
            logger.debug("[Tree]")
            for tree_string in tree_strings:
                logger.debug(tree_string)
        core.utils.dump(
            tree_strings,
            fn=core.utils.format_fn(
                fn=("tree.with_node_names.txt"),
                prefix=core.utils.get_dir("TREE"),
            ),
        )
    return tree


def get_df_nodes(
    df_counts,
    tree,
    output_fmt="tsv",
):
    """
    - agnostic about additional leafs
    - OG_AT: ApomorphyType
    - OG_NP: NodeProportion (based only on leaf_names in df_counts)
    - EC: ElementCount
    """
    if df_counts.empty or tree is None:
        return None

    def place_orthogroup(row):
        row_dict = row.to_dict()
        TNs = [k for k, v in row_dict.items() if v > 0]
        node = tree.common_ancestor(TNs)
        node_id = node.get_prop("name")
        OG_AT = "synapomorphy" if len(TNs) > 1 else "autapomorphy"
        OG_NP = len(TNs) / len([leaf_name for leaf_name in node.leaf_names() if leaf_name in row_dict])
        return (
            node_id,
            OG_AT,
            OG_NP,
        )

    t_0 = time.monotonic()
    logger.info(
        f"placing orthogroups along {core.utils.format_number(len(list(tree.root.edges())))} branches on tree"
    )
    df_nodes = df_counts.apply(place_orthogroup, axis=1, result_type="expand")
    df_nodes.columns = ["node_id", "OG_TT", "OG_NP"]
    df_nodes["EC"] = df_counts.sum(axis=1)
    OG_TT = df_nodes["OG_TT"].value_counts()
    logger.info(
        f"{core.utils.format_number(OG_TT.get('synapomorphy', 0))} synapomorphic orthogroups"
    )
    logger.info(
        f"{core.utils.format_number(OG_TT.get('autapomorphy', 0))} autapomorphic orthogroups"
    )
    core.utils.dump(
        df_nodes.reset_index(),
        fn=core.utils.format_fn(
            fn=f"tree.node_metrics.{output_fmt}",
            prefix=core.utils.get_dir("TREE"),
        ),
        index=False,
    )
    logger.info(
        core.utils.format_elapsed(time.monotonic() - t_0),
    )
    return df_nodes


if __name__ == "__main__":
    pass
