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
import ete4
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
        elif df[column].dtype == "categorical":
            df[column] = df[column].cat.remove_unused_categories()
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
        logger.info("inferring sample_ids for orthogroups (this might take a while)...")
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
    df_counts = downcast(
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
    # [DUMP OGS]
    core.utils.dump(
        downcast(df_orthogroups, categorical=["sample_id"]),
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
                    / f"partition.{label}.{tag}_vs_{definitions.REMAINDER_LABEL}.contrast.{task.output_fmt}"
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
            downcast(df_partition.reset_index(), categorical=["CT"]),
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
    # elif task.type == "InterproChunkTask":
    #    return make_interpro_chunks(task)
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


def get_tree(
    fn,
    sample_ids=[],
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
        logger.info(f"parsing tree in {fn}")
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
        sample_ids_found = []
        for node in tree.traverse("levelorder"):  # rename nodes
            if not node.name:
                node.add_prop("name", f"{str(idx).zfill(zeros)}")
                idx += 1
            else:
                sample_ids_found.append(node.name)
        logger.info(f"tree has {core.utils.format_number(len(sample_ids_found))} taxa")
        sample_ids_missing = set(sample_ids) - set(sample_ids_found)
        if sample_ids_missing:
            logger.error(
                f"{core.utils.format_number(len(sample_ids_missing))} sample IDs not in tree: {' '.join(sample_ids_missing)}"
            )
            sys.exit(1)
        sample_ids_surplus = set(sample_ids_found) - set(sample_ids)
        if sample_ids_surplus:
            logger.warning(f"tree has additional taxa: {' '.join(sample_ids_surplus)}")
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
    sample_ids=[],
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
        sample_ids=sample_ids,
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
        f"placing orthogroups along {core.utils.format_number(len(list(tree.root.edges())))} branches on tree (this might take a while)"
    )
    tqdm.tqdm.pandas(
        desc=definitions.PROGRESS_DESC_TREE,
        ncols=definitions.PROGRESS_NCOLS,
    )
    df_counts = core.utils.get_counts_df()
    df_nodes = df_counts.progress_apply(
        place_orthogroup,
        axis=1,
        result_type="expand",
    )
    df_nodes.columns = ["node_id", "OG_AT", "OT", "OG_NP", "EC"]
    OG_AT = df_nodes["OG_AT"].value_counts()
    logger.info(
        f"{core.utils.format_number(OG_AT.get('synapomorphy', 0))} synapomorphic orthogroups"
    )
    logger.info(
        f"{core.utils.format_number(OG_AT.get('autapomorphy', 0))} autapomorphic orthogroups"
    )
    df_nodes = df_nodes.reset_index()
    core.utils.dump(
        downcast(
            df_nodes,
            categorical=[
                "node_id",
                "OG_AT",
                "OT",
            ],
        ),
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
            "OT",
            "OG_NT",
        ],
        as_index=False,
    ).agg(OC=("orthogroup_id", "count"))
    core.utils.dump(
        downcast(
            df_summary,
            categorical=[
                "node_id",
                "OG_AT",
                "OT",
                "OG_NT",
            ],
        ),
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
