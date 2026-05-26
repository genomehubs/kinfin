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

import core.log
import core.taxonomy
import definitions
import ete4
import numpy as np
import pandas as pd
import scipy
import tqdm

import core.utils

logger = logging.getLogger(__name__)

# pd.options.display.max_colwidth = None
# pd.options.display.max_rows = None

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

ParseResult = collections.namedtuple(
    "ParseResult",
    [
        "type",
        "fn_in",
        "fn_out",
        "sample_id",
        "problem",
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
def do_fasta_task(task):
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
            return core.utils.dump(
                df_fasta,
                fn=core.utils.format_fn(
                    f"{task.sample_id}.elements.{definitions.STD_FORMAT}",
                    prefix=core.utils.get_dir("TMP"),
                ),
                index=False,
            )
    except Exception as exc:
        logger.error(f"problem reading {task.fn} - {exc}")
    return None


# [DONE]
def get_interpro_tasks(
    fn=None,
    directory=None,
    sample_ids=[],
):
    if fn is not None:
        tasks = [
            ParseTask(
                type="interpro",
                sample_id=sample_ids,
                fn=fn,
            )
        ]
    else:
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


# [DONE]
def do_interpro_task(task):
    problem = None
    fn_out = None
    sample_ids = [task.sample_id] if isinstance(task.sample_id, str) else task.sample_id
    try:
        if task.fn is not None:
            df_interpro = core.utils.load(
                task.fn,
                names=definitions.INTERPRO_TSV_COLUMNS,
            ).set_index("element_id")
            df_orthogroups = core.utils.get_orthogroups_df(
                filters=[
                    (
                        "sample_id",
                        "in",
                        sample_ids,
                    )
                ]
            ).set_index("element_id")
            df_annotation = df_interpro.join(df_orthogroups, how="outer")
            # remove annotations of E's not in OG's
            is_orphan = df_annotation["orthogroup_id"].isnull()
            df_annotation = df_annotation[~is_orphan]
            if not df_annotation.empty:
                fn_out = core.utils.dump(
                    df_annotation,
                    fn=core.utils.format_fn(
                        f"{'all' if len(sample_ids) > 1 else f'{task.sample_id}'}.interpro.{definitions.STD_FORMAT}",
                        prefix=core.utils.get_dir("TMP"),
                    ),
                    index=True,
                )
            else:
                if df_annotation["analysis"].isnull().values.any():
                    problem = f"inconsistent tabs in file {task.fn}"
        else:
            # fake df_annotation for sample_ids without interpro file
            df_annotation = (
                core.utils.get_orthogroups_df(
                    filters=[
                        (
                            "sample_id",
                            "in",
                            sample_ids,
                        )
                    ]
                )
                .assign(
                    **{
                        col: np.nan
                        for col in [
                            col
                            for col in definitions.INTERPRO_TSV_COLUMNS
                            if col != "element_id"
                        ]
                    }
                )
                .set_index("element_id")
            )
            fn_out = core.utils.dump(
                df_annotation,
                fn=core.utils.format_fn(
                    f"{task.sample_id}.interpro.{definitions.STD_FORMAT}",
                    prefix=core.utils.get_dir("TMP"),
                ),
                index=True,
            )
            print(df_orthogroups)
    except Exception as exc:
        problem = f"problem reading {task.fn} - {exc}"
    return ParseResult(
        type="interpro",
        fn_in=task.fn,
        sample_id=task.sample_id,
        fn_out=fn_out,
        problem=problem,
    )


def get_interpro_summary_table(
    interpro_results,
    sample_ids=[],
    output_fmt="tsv",
):
    interpro_summary = {}
    for interpro_result in interpro_results:
        interpro_sample_ids = (
            interpro_result.sample_id
            if isinstance(interpro_result.sample_id, list)
            else [interpro_result.sample_id]
        )
        df_annotation = core.utils.load(fn=interpro_result.fn_out)
        for interpro_sample_id in interpro_sample_ids:
            interpro_summary[interpro_sample_id] = {
                "EC": df_annotation[df_annotation["sample_id"] == interpro_sample_id][
                    "sample_id"
                ].count(),
                "EC_AC": df_annotation[
                    df_annotation["sample_id"] == interpro_sample_id
                ]["analysis"].count(),
            }
            interpro_summary[interpro_sample_id]["EC_AP"] = (
                interpro_summary[interpro_sample_id]["EC_AC"]
                / interpro_summary[interpro_sample_id]["EC"]
            )
    interpro_summary_rows = []
    for sample_id in sample_ids:
        interpro_summary_rows.append(
            {
                "sample_id": sample_id,
                **interpro_summary[sample_id],
            }
        )
    core.utils.dump(
        pd.DataFrame().from_records(interpro_summary_rows),
        fn=core.utils.format_fn(
            f"interpro.summary.{output_fmt}",
            prefix=core.utils.get_dir("ANNOTATION"),
        ),
        index=False,
    )


def get_interpro(
    fn=None,
    directory=None,
    sample_ids=[],
    output_fmt="tsv",
    processes=1,
):
    t_0 = time.monotonic()
    logger.info(f"parsing INTERPRO data in {fn or directory}")
    tasks = get_interpro_tasks(
        fn=fn,
        directory=directory,
        sample_ids=sample_ids,
    )
    if len(tasks) == 1:
        processes = 1
    logger.info(f"parsing {len(tasks)} file(s) using {processes} process(es)")
    interpro_results = do_tasks(
        tasks=tasks,
        desc=definitions.PROGRESS_DESC_INTERPRO,
        processes=processes,
        collect_results=True,
    )
    logger.info("generating summary table")
    get_interpro_summary_table(
        interpro_results,
        sample_ids=sample_ids,
        output_fmt=output_fmt,
    )
    core.utils.dump(
        pd.concat(
            [
                core.utils.load(interpro_result.fn_out)
                for interpro_result in interpro_results
            ]
        ),
        fn=core.utils.format_fn(
            fn=definitions.INTERPRO_FN,
            prefix=core.utils.get_dir("INPUT"),
        ),
        index=False,
    )
    logger.info(f"{core.utils.format_elapsed(time.monotonic() - t_0)}")
    return None


def process_interpro(
    fn=None,
    directory=None,
    sample_ids=[],
    output_fmt="tsv",
    processes=1,
):
    t_0 = time.monotonic()
    get_interpro(
        fn=fn,
        directory=directory,
        sample_ids=sample_ids,
        output_fmt=output_fmt,
        processes=processes,
    )
    df_annotation = (
        core.utils.get_interpro_df()
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
    df_counts = core.utils.get_counts_df()
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
    # df_annotation["TG_AP"] = (
    #     df_annotation["TG_AP"]
    #     .div(
    #         df_counts,
    #     )
    #     .replace(np.nan, 0.0)
    # )
    df_annotation.columns = [
        (f"{x}_{y}" if y else f"{x}") for x, y in df_annotation.columns.to_flat_index()
    ]
    core.utils.dump(
        df_annotation.reset_index(),
        fn=core.utils.format_fn(
            definitions.ANNOTATION_FN,
            prefix=core.utils.get_dir("ANNOTATION"),
        ),
        index=False,
    )
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
                df,
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
        type="fasta",
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
    sample_ids_source="parse",
):
    # [ToDo]
    # - make -P work when length is ALSO parsed from -f. Decide what happens if disagreement.
    data = []
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
        df_elements = core.utils.get_elements_df().set_index("element_id")
        df_orthogroups["sample_id"] = df_orthogroups["element_id"].map(
            df_elements["sample_id"],
            na_action="ignore",
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
        logger.error(
            f"none of these sample IDs were found: {', '.join(sample_ids)}. Exiting."
        )
        sys.exit(1)
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
        df_counts.apply(
            pd.to_numeric,
            downcast="float",  # float32
        ).replace(
            0,
            np.nan,
        ),
        fn=core.utils.format_fn(
            fn=definitions.COUNTS_NAN_FN,
            prefix=core.utils.get_dir("TMP"),
        ),
        index=True,
    )
    # [DUMP OGS]
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
    _COLUMNS = ["EC_TG1", "OG_type_TG1", "COG_type_TG1"]
    compare_rows = []
    df_sampling = None
    for label, tags in zip(task.labels, task.tags):
        directory = core.utils.get_dir("PARTITION") / label
        if not compare_rows:
            for idx, tag in enumerate(tags):
                fn = (
                    directory
                    / f"partition.{label}.{tag}_vs_{definitions.REMAINDER_LABEL}.contrast.{task.output_fmt}"
                )
                if task.output_fmt == "tsv":
                    df = core.utils.load(fn)
                else:
                    df = core.utils.load(fn, columns=_COLUMNS)
                OC = len(df.index)
                mask_absent = df["OG_type_TG1"] == "absent"
                mask_present = df["OG_type_TG1"] != "absent"
                mask_singleton = df["OG_type_TG1"] == "singleton"
                mask_specific = df["OG_type_TG1"] == "specific"
                mask_shared = df["OG_type_TG1"] == "shared"
                mask_cog_true = df["COG_type_TG1"] == "true_cog"
                mask_cog_fuzzy = df["COG_type_TG1"] == "fuzzy_cog"
                EC_TG = int(df[mask_present]["EC_TG1"].sum())
                SC_TG = len(task.taxon_groups[idx])
                df_sampling = (
                    df[mask_present][
                        [
                            "OG_type_TG1",
                            "EC_TG1",
                        ]
                    ]
                    .reset_index(drop=True)
                    .rename(
                        columns={
                            "EC_TG1": "EC",
                            "OG_type_TG1": "OG_OT",
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
                        ["OG_OT", "EC"],
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
                    df_sampling[
                        [
                            "OG_OT",
                            "EC",
                            "OC",
                            "ECn",
                            "OCn",
                        ]
                    ],
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
                df_sampling[
                    [
                        "OG_OT",
                        "EC",
                        "OC",
                        "ECn",
                        "OCn",
                    ]
                ],
                fn=core.utils.format_fn(
                    fn=f"{label}.{tag}.{SC_TG}.curve.{task.output_fmt}",
                    prefix=core.utils.get_dir("PARTITION") / label,
                ),
                index=False,
            )
        core.utils.dump(
            pd.DataFrame.from_dict(compare_rows),
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
    # FASTER NPSELECT
    df_partition_list.append(
        pd.Series(
            np.select(
                condlist=[
                    np.all(df_counts.eq(task.count_target), axis=1),
                    np.mean(
                        (df_counts >= task.count_min) & (df_counts <= task.count_max),
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
        ).rename("COG_type_TG1")
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
    #     ).rename("COG_type_TG1")
    # )
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
            "EC_median",
            "EC_median_TG1",
            "EC_median_TG2",
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
            df_partition.reset_index(),
            fn=core.utils.format_fn(
                fn=(f"{fn}.contrast.{task.output_fmt}"),
                prefix=core.utils.get_dir("PARTITION") / label,
            ),
            index=False,
        )
    # timing["dumping"] = time.monotonic() - t_i
    # import pprint
    # pprint.pp(timing)
    return True


def do_task(task):
    if task.type == "summary":
        return compare(task)
    # elif task.type == "plot":
    #     return plottify(task)
    elif task.type == "comparison":
        return contrast(task)
    elif task.type == "fasta":
        return do_fasta_task(task)
    elif task.type == "interpro":
        return do_interpro_task(task)
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
    type="summary",
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
                type=type,
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
            type="comparison",
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


def get_tree(
    fn,
    outgroup=[],
):
    """
    # [done]
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
        idx = 0
        for node in tree.traverse("levelorder"):  # rename nodes
            if not node.name:
                node.add_prop("name", f"{str(idx).zfill(zeros)}")
                idx += 1
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


def process_tree(
    tree_fn="",
    outgroup=[],
    output_fmt="tsv",
):
    """
    # [done]
    - agnostic about additional leafs
    - OG_AT: ApomorphyType
    - OG_OT: OrthogroupType
    - OG_NP: NodeProportion (based only on leaf_names in df_counts)
    - EC: ElementCount
    """
    t_0 = time.monotonic()
    tree = get_tree(
        fn=tree_fn,
        outgroup=outgroup,
    )

    def place_orthogroup(row):
        row_dict = row.to_dict()
        TNs = [k for k, v in row_dict.items() if v > 0]
        EC = sum(row_dict.values())
        node = tree.common_ancestor(TNs)
        node_id = node.get_prop("name")
        OG_AT = "synapomorphy" if len(TNs) > 1 else "autapomorphy"
        OG_OT = "specific" if EC > 1 else "singleton"
        OG_NP = len(TNs) / len(
            [leaf_name for leaf_name in node.leaf_names() if leaf_name in row_dict]
        )
        return (
            node_id,
            OG_AT,
            OG_OT,
            OG_NP,
            EC,
        )

    logger.info(
        f"placing orthogroups along {core.utils.format_number(len(list(tree.root.edges())))} branches on tree"
    )

    df_nodes = core.utils.get_counts_df().apply(
        place_orthogroup,
        axis=1,
        result_type="expand",
    )
    df_nodes.columns = ["node_id", "OG_AT", "OG_OT", "OG_NP", "EC"]
    OG_AT = df_nodes["OG_AT"].value_counts()
    logger.info(
        f"{core.utils.format_number(OG_AT.get('synapomorphy', 0))} synapomorphic orthogroups"
    )
    logger.info(
        f"{core.utils.format_number(OG_AT.get('autapomorphy', 0))} autapomorphic orthogroups"
    )
    df_nodes = df_nodes.reset_index()
    core.utils.dump(
        df_nodes,
        fn=core.utils.format_fn(
            fn=f"tree.node_metrics.{output_fmt}",
            prefix=core.utils.get_dir("TREE"),
        ),
        index=False,
    )
    df_nodes["OG_NT"] = "partial"
    df_nodes["OG_NT"] = df_nodes["OG_NT"].where(df_nodes["OG_NP"] == 1, "complete")
    df_summary = df_nodes.groupby(
        [
            "node_id",
            "OG_AT",
            "OG_OT",
            "OG_NT",
        ],
        as_index=False,
    ).agg(OC=("orthogroup_id", "count"))
    core.utils.dump(
        df_summary,
        fn=core.utils.format_fn(
            fn=f"tree.summary.{output_fmt}",
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
