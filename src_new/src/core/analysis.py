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

import core.log
import core.plot
import core.taxonomy
import definitions
import numpy as np
import pandas as pd
import scipy
import tqdm

import core.utils

logger = logging.getLogger(__name__)

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
        "plot_fmt",
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
        "plot_fmt",
        "lengths_parsed",
    ],
)

ParseTask = collections.namedtuple(
    "ParseTask",
    [
        "type",
        "sample_id",
        "fn",
        "params",
    ],
)

VolcanoTask = collections.namedtuple(
    "VolcanoTask",
    [
        "type",
        "fn",
        "label",
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
    params={},
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
                        params=params,
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
        .assign(**{"signature_id": np.nan, "analysis": np.nan})
        .reset_index()
    ).drop(columns=[sample_id])


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
    dump_signature_summary(
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


def dump_signature_summary(df, analyses=[], sample_id=None):
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


def do_parse_bed_task(task):
    use_cols = list(task.params["name_idxs"])
    if task.params["count_idx"] is not None:
        use_cols.append(task.params["count_idx"])

    success = False
    try:
        df_bed = pd.read_csv(
            task.fn,
            sep="\t",
            header=None,
            skiprows=(1 if task.params["has_header"] else 0),
            usecols=use_cols,
            dtype=str,
        )
        if task.params["count_idx"]:
            df_bed_counts = (
                pd.concat(
                    [
                        df_bed[task.params["name_idxs"]]
                        .apply(task.params["name_sep"].join, axis=1)
                        .to_frame("orthogroup_id"),
                        df_bed[[task.params["count_idx"]]].astype(int),
                    ],
                    axis=1,
                )
                .rename(columns={task.params["count_idx"]: "count"})
                .groupby("orthogroup_id")
                .sum()
            )
        else:
            df_bed_counts = (
                df_bed[task.params["name_idxs"]]
                .apply(task.params["name_sep"].join, axis=1)
                .value_counts()
                .to_frame("count")
            )
        df_bed_counts["sample_id"] = task.sample_id
        core.utils.dump(
            df_bed_counts.reset_index(),
            fn=core.utils.format_fn(
                fn=f"{task.sample_id}.{definitions.COUNTS_FN}",
                prefix=core.utils.get_dir("TMP") / task.sample_id,
            ),
            index=True,
        )
        success = True
    except Exception:
        pass
    return (task.fn, success)


def get_parse_bed_tasks(
    directory=None,
    sample_ids=[],
    count_idx=None,
    name_idxs=[3],
    name_sep=definitions.DEFAULT_BED_NAME_SEPARATOR,
    has_header=False,
):
    tasks = get_parse_tasks(
        directory=directory,
        type="bed",
        sample_ids=sample_ids,
        extensions=definitions.SUPPORTED_BED_EXTENSIONS,
        params={
            "count_idx": count_idx,
            "name_idxs": name_idxs,
            "name_sep": name_sep,
            "has_header": has_header,
        },
    )
    sample_ids_found = [task.sample_id for task in tasks]
    if len(sample_ids_found) == 0:
        logger.warning(
            f"no files with extension '{definitions.SUPPORTED_BED_EXTENSIONS}' could be found in directory '{directory}' for the sample IDs: {', '.join(sample_ids)}"
        )
        sys.exit(1)
    if len(sample_ids_found) < len(sample_ids):
        sample_ids_missing = set(sample_ids) - set(sample_ids_found)
        logger.warning(
            f"files for the following sample IDs could not be found: {', '.join(sorted(sample_ids_missing))}"
        )
    return tasks


def process_bed(
    directory="",
    sample_ids=[],
    count_idx=None,
    name_idxs=[3],
    name_sep=definitions.DEFAULT_BED_NAME_SEPARATOR,
    has_header=False,
    output_fmt=definitions.STD_FORMAT,
    plot_fmt=definitions.PLOT_FORMAT,
    do_plots=False,
    processes=1,
):
    parse_beds(
        directory=directory,
        sample_ids=sample_ids,
        count_idx=count_idx,
        name_idxs=name_idxs,
        name_sep=name_sep,
        has_header=has_header,
        processes=processes,
    )
    get_bed_counts(
        sample_ids=sample_ids,
        output_fmt=output_fmt,
        plot_fmt=plot_fmt,
        do_plots=do_plots,
    )


def parse_beds(
    directory=None,
    sample_ids=[],
    count_idx=None,
    name_idxs=[3],
    name_sep=definitions.DEFAULT_BED_NAME_SEPARATOR,
    has_header=False,
    processes=1,
):
    t_0 = time.monotonic()
    logger.info(f"parsing BED file(s) in {directory}")
    tasks = get_parse_bed_tasks(
        directory=directory,
        sample_ids=sample_ids,
        count_idx=count_idx,
        name_idxs=name_idxs,
        name_sep=name_sep,
        has_header=has_header,
    )
    processes = 1 if len(tasks) == 1 else processes
    logger.info(f"parsing {len(tasks)} file(s) using {processes} process(es)")
    results = do_tasks(
        tasks=tasks,
        desc=definitions.PROGRESS_DESC_BED,
        processes=processes,
        collect_results=True,
    )
    problematic_bed_string = "\n".join([fn for fn, success in results if not success])
    if problematic_bed_string:
        logger.error(
            f"The following BED files could not be parsed. Verify format and use of option (-B):\n{problematic_bed_string}"
        )
        sys.exit(1)
    logger.info(f"{core.utils.format_elapsed(time.monotonic() - t_0)}")


def get_bed_counts(
    sample_ids=[],
    output_fmt=definitions.STD_FORMAT,
    plot_fmt=definitions.PLOT_FORMAT,
    do_plots=True,
):
    t_0 = time.monotonic()
    logger.info("joining BED data ...")
    df_beds = []
    sample_ids_missing = []
    with tqdm.tqdm(
        total=len(sample_ids),
        desc=definitions.PROGRESS_DESC_ANNOTATION_TASK_RUN,
        ncols=definitions.PROGRESS_NCOLS,
    ) as pbar:
        for sample_id in sample_ids:
            df_bed = core.utils.get_bed_df(
                sample_id=sample_id,
            )
            if isinstance(df_bed, pd.DataFrame):
                df_beds.append(df_bed)
            else:
                sample_ids_missing.append(sample_id)
            pbar.update()
    df_counts = (
        pd.concat(df_beds, axis=0)
        .reset_index()
        .set_index(["orthogroup_id", "sample_id"])["count"]
        .unstack(fill_value=0)
    )
    for sample_id in sample_ids_missing:
        df_counts[sample_id] = 0
    # [DUMP COUNTS]
    core.utils.dump(
        df_counts,
        fn=core.utils.format_fn(
            fn=definitions.COUNTS_FN,
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
    if do_plots:
        tally_counts(
            output_fmt=output_fmt,
            plot_fmt=plot_fmt,
            do_plots=do_plots,
        )
    logger.info(
        core.utils.format_elapsed(time.monotonic() - t_0),
    )


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

    def get_EC_SC():
        df_counts = core.utils.get_counts_df()
        EC = df_counts.sum(axis=1).rename("EC")
        SC = df_counts.ge(1).sum(axis=1).rename("SC")
        return (EC, SC)

    t_0 = time.monotonic()
    logger.info("joining annotation data ...")
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
        pd.concat(
            df_annotations,
            axis=1,
        )
        .dropna(
            axis=0,
            how="all",
        )
        .replace(
            np.nan,
            0,
        )
    )
    logger.info("annotation data joined")
    for column in df_annotations.columns:
        df_annotations[column] = df_annotations[column].astype(int)
    df_annotations = downcast(df_annotations)
    columns = []
    EC_AC = df_annotations.sum(axis=1).rename("EC_AC")
    columns.append(EC_AC)
    SC_AC = df_annotations.ge(1).sum(axis=1).rename("SC_AC")
    columns.append(SC_AC)
    EC, SC = get_EC_SC()
    df_annotations = df_annotations.join(EC)
    df_annotations = df_annotations.join(SC)
    EC_AP = EC_AC.div(df_annotations["EC"]).rename("EC_AP")
    columns.append(EC_AP)
    SC_AP = SC_AC.div(df_annotations["SC"]).rename("SC_AP")
    columns.append(SC_AP)
    COLUMNS = [
        "signature_desc",
        "interpro_id",
        "interpro_desc",
        "go_annotation",
        "SC",
        "SC_AC",
        "SC_AP",
        "EC",
        "EC_AC",
        "EC_AP",
    ]
    df_annotations = df_annotations.join(
        core.utils.get_signatures_df()
        .reset_index()
        .set_index(["analysis", "signature_id"]),
    )
    df_annotation = core.utils.downcast(
        pd.concat(
            [
                df_annotations,
                pd.concat(columns, axis=1),
            ],
            axis=1,
        )
    )[COLUMNS + [col for col in df_annotations.columns if col not in COLUMNS]].astype(
        {
            "signature_desc": "category",
            "interpro_id": "category",
            "interpro_desc": "category",
            "go_annotation": "category",
        }
    )
    core.utils.dump(
        df_annotation,
        fn=core.utils.format_fn(
            f"{definitions.ANNOTATION_FN}",
            prefix=core.utils.get_dir("ANNOTATION"),
            suffix=f".{output_fmt}",
        ),
        index=True,
    )
    get_df_entropy(
        df_annotation=df_annotation.copy(deep=True),
        output_fmt=output_fmt,
    )
    logger.info(f"{core.utils.format_elapsed(time.monotonic() - t_0)}")


def analyse_signatures(
    sample_ids=[],
    output_fmt="tsv",
):
    df_signatures = None
    logger.info("collecting InterPro signatures ...")
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
    logger.info("tallying InterPro signatures ...")
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
        output_fmt=output_fmt,
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
        sample_ids_found = {}
        with open(species_ids_fn, "r") as fh:
            for line in fh:
                species_idx, sample_id = line.rstrip("\n").split(": ")
                if sample_id in sample_ids:
                    sample_ids_found[species_idx] = sample_id
        data = []
        with open(sequence_ids_fn, "r") as fh:
            for line in fh:
                sequence_idx, element_id = line.rstrip("\n").split(": ")
                species_idx, _ = sequence_idx.split("_")
                if species_idx in sample_ids_found:
                    data.append((element_id, sample_ids_found[species_idx]))
        df = pd.DataFrame().from_records(data, columns=["element_id", "sample_id"])
        if df.empty:
            logger.error(
                f"none of the following IDs was found in the file '{species_ids_fn}': {', '.join(sorted(sample_ids))}"
            )
            sys.exit(1)
        elif not len(sample_ids) == len(sample_ids_found):
            logger.error(
                f"the following IDs were not found in the file '{species_ids_fn}': {', '.join(sorted(sample_ids - set(sample_ids_found.values())))}"
            )
            sys.exit(1)
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
    output_fmt=definitions.STD_FORMAT,
    plot_fmt=definitions.PLOT_FORMAT,
    lengths_parsed=False,
    do_plots=True,
    ignore_duplicated_elements=False,
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
    if not ignore_duplicated_elements:
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
        logger.info(
            "inferring Sample IDs for orthogroups (this might take a moment)..."
        )
        df_elements = (
            core.utils.get_elements_df()
            .set_index("element_id")
            .astype({"sample_id": "category"})
        )
        df_orthogroups = df_elements.join(
            df_orthogroups.set_index("element_id"), how="outer"
        ).reset_index()
    orthogroups_count = df_orthogroups["orthogroup_id"].nunique()
    logger.info(f"{core.utils.format_number(orthogroups_count)} orthogroup(s) in file")
    elements_in_fasta_count = int(df_orthogroups["element_id"].count())
    elements_in_orthogroups_count = int(
        df_orthogroups[~df_orthogroups["orthogroup_id"].isna()]["element_id"].count()
    )
    logger.info(
        f"{core.utils.format_number(elements_in_fasta_count)} element(s) in FASTA file(s)"
    )
    msg = f"{core.utils.format_number(elements_in_orthogroups_count)} element(s) in orthogroups file ({elements_in_orthogroups_count / elements_in_fasta_count:.3%})"
    if elements_in_fasta_count == elements_in_orthogroups_count:
        logger.info(msg)
    else:
        logger.warning(msg)
        df_orphan_elements = df_orthogroups[df_orthogroups["orthogroup_id"].isna()]
        df_orphan_elements_fn = core.utils.dump(
            df_orphan_elements,
            fn=core.utils.format_fn(
                definitions.ELEMENTS_ORPHAN_FN,
                prefix=core.utils.get_dir("INPUT"),
                suffix=f".{output_fmt}",
            ),
            index=True,
        )
        logger.warning(f"wrote orphan elements(s) to {df_orphan_elements_fn}")
        df_orphan_elements_summary_fn = core.utils.dump(
            df_orphan_elements.groupby("sample_id").agg(
                missing_count=("sample_id", "count"),
                min_length=("length", "min"),
                max_length=("length", "max"),
                median_length=("length", "median"),
            )
            if lengths_parsed
            else df_orphan_elements.groupby("sample_id").agg(
                missing_count=("sample_id", "count"),
            ),
            fn=core.utils.format_fn(
                definitions.ELEMENTS_ORPHAN_SUMMARY_FN,
                prefix=core.utils.get_dir("INPUT"),
                suffix=f".{output_fmt}",
            ),
            index=True,
        )
        logger.warning(
            f"wrote orphan elements(s) summary to {df_orphan_elements_summary_fn}"
        )
        df_orthogroups = df_orthogroups[
            ~df_orthogroups["sample_id"].isna()
            & ~df_orthogroups["orthogroup_id"].isna()
        ].reset_index(drop=True)[["orthogroup_id", "element_id", "sample_id"]]
    if df_orthogroups.empty:
        logger.error(
            f"none of these sample IDs were found: {', '.join(sample_ids)}. Exiting."
        )
        sys.exit(1)
    if lengths_parsed:
        df_orthogroups["length"] = df_orthogroups["element_id"].map(
            df_elements["length"]
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
            fn=definitions.COUNTS_FN,
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
    if do_plots:
        tally_counts(
            output_fmt=output_fmt,
            plot_fmt=plot_fmt,
            do_plots=do_plots,
        )
    logger.info(
        core.utils.format_elapsed(time.monotonic() - t_0),
    )


def tally_counts(
    output_fmt=definitions.STD_FORMAT,
    plot_fmt=definitions.PLOT_FORMAT,
    do_plots=True,
):
    t_0 = time.monotonic()
    df_counts = core.utils.get_counts_df()
    df_EC = (
        df_counts.sum(axis=1)
        .value_counts(ascending=False)
        .reset_index()
        .rename(columns={"index": "EC"})
        .sort_values(by=["EC"])
    )
    df_SC = (
        df_counts.ge(1)
        .sum(axis=1)
        .value_counts(ascending=False)
        .reset_index()
        .rename(columns={"index": "SC"})
        .sort_values(by=["SC"])
    )
    if do_plots:
        core.plot.tally_plot(
            df_EC=df_EC,
            df_SC=df_SC,
            fn=core.utils.format_fn(
                fn="tally.plot",
                prefix=core.utils.get_dir("PLOTS") / "tally",
                suffix=f".{plot_fmt}",
            ),
        )
    core.utils.dump(
        df_EC,
        fn=core.utils.format_fn(
            fn=definitions.EC_TALLY_FN,
            prefix=core.utils.get_dir("PLOTS") / "tally",
            suffix=f".{output_fmt}",
        ),
        index=False,
    )
    core.utils.dump(
        df_SC,
        fn=core.utils.format_fn(
            fn=definitions.SC_TALLY_FN,
            prefix=core.utils.get_dir("PLOTS") / "tally",
            suffix=f".{output_fmt}",
        ),
        index=False,
    )
    logger.info(
        core.utils.format_elapsed(time.monotonic() - t_0),
    )


def partition_lengths(task=None):
    df_orthogroups = core.utils.get_orthogroups_df()
    dfs = [
        df_orthogroups.groupby("orthogroup_id").agg(
            EL_mean=("length", "mean"), EL_sd=("length", "std")
        )
    ]
    for idx, TNs in enumerate(task.taxon_groups):
        dfs.append(
            df_orthogroups.where(df_orthogroups["sample_id"].isin(TNs))
            .groupby("orthogroup_id")
            .agg(TG_EL_mean=("length", "mean"), TG_EL_sd=("length", "std"))
            .rename(
                columns={"TG_EL_mean": f"{idx}_EL_mean", "TG_EL_sd": f"{idx}_EL_sd"}
            )
        )
    df_lengths = pd.concat(dfs, axis=1).reindex(dfs[0].index)
    for label, tags in zip(task.labels, task.tags):
        for idx, tag in enumerate(tags):
            df_lengths = df_lengths.rename(
                columns={
                    f"{idx}_EL_mean": f"{tag}_EL_mean",
                    f"{idx}_EL_sd": f"{tag}_EL_sd",
                }
            )
        core.utils.dump(
            df_lengths,
            fn=core.utils.format_fn(
                fn=f"{label}.lengths.{task.output_fmt}",
                prefix=core.utils.get_dir("PARTITION") / label,
            ),
            index=True,
        )


def get_df_entropy(df_annotation, output_fmt="tsv"):
    """Entropy is correct. Previous KinFin implementation was off."""

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
    # print(df_annotation)
    df_annotation = df_annotation.reset_index()[
        [
            "orthogroup_id",
            "analysis",
            "signature_id",
            "interpro_id",
            "go_annotation",
            "SC",
            "SC_AP",
            "EC",
            "EC_AP",
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
                        f"{analysis}_SC": pd.NamedAgg(
                            column="SC",
                            aggfunc="max",
                        ),
                        f"{analysis}_SC_AP": pd.NamedAgg(
                            column="SC_AP",
                            aggfunc="max",
                        ),
                        f"{analysis}_EC": pd.NamedAgg(
                            column="EC",
                            aggfunc="max",
                        ),
                        f"{analysis}_EC_AP": pd.NamedAgg(
                            column="EC_AP",
                            aggfunc="max",
                        ),
                        "interpro_entropy": pd.NamedAgg(
                            column="interpro_id",
                            aggfunc=infer_entropy,
                        ),
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
            core.utils.dump(
                df_entropy[
                    [
                        f"{analysis}_SC",
                        f"{analysis}_SC_AP",
                        f"{analysis}_EC",
                        f"{analysis}_EC_AP",
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

    # def get_df_table(fn, df_orthogroups):
    #     # [ToDo]
    #     # - finish thinking about this
    #     # - decide how to expose to user. Args-config-json as mentioned by RC
    #     # - drop as table
    #     t_0 = time.monotonic()
    #     logger.info(f"parsing '{fn}'")
    #     df_table = core.utils.load(fn)
    #     try:
    #         annotations_valid = df_table["element_id"].isin(df_orthogroups["element_id"])
    #         annotations_valid_count = int(annotations_valid.value_counts().get(True, 0))
    #         annotations_orphan_count = int(annotations_valid.value_counts().get(False, 0))
    #         if annotations_orphan_count:
    #             logger.warning(
    #                 f"found {core.utils.format_number(annotations_orphan_count)} orphan annotation(s). Not part of any Orthogroup"
    #             )
    #             core.utils.dump(
    #                 df_table[~annotations_valid],
    #                 fn=core.utils.format_fn(fn, suffix=".orphans.tsv"),
    #                 index=False,
    #             )
    #         if annotations_valid_count:
    #             logger.info(
    #                 f"found {core.utils.format_number(annotations_valid_count)} annotation(s) of elements in Orthogroups"
    #             )
    #             core.utils.dump(
    #                 df_table[annotations_valid],
    #                 fn=core.utils.format_fn(fn, suffix=".filtered.tsv"),
    #                 index=False,
    #             )
    #     except NameError:
    #         logger.error("missing column 'element_id'")
    #     logger.info(
    #         core.utils.format_elapsed(time.monotonic() - t_0),
    #     )
    #     return df_table[annotations_valid]


def analyse_orthogroups(
    df_config=None,
    count_target=1,
    count_min=0,
    count_max=1,
    count_fraction=0.75,
    output_fmt="tsv",
    lengths_parsed=False,
    ignore_sample_comparisons=False,
    plot_fmt=definitions.PLOT_FORMAT,
    processes=1,
):
    tasks = get_comparison_tasks(
        df_config=df_config,
        count_target=count_target,
        count_min=count_min,
        count_max=count_max,
        count_fraction=count_fraction,
        output_fmt=output_fmt,
        ignore_sample_comparisons=ignore_sample_comparisons,
        plot_fmt=plot_fmt,
    )
    logger.info(
        f"calculating {len(tasks)} comparisons between taxon-groups using {processes} process(es)"
    )
    core.analysis.do_tasks(
        tasks,
        desc=definitions.PROGRESS_DESC_PARTITIONING,
        processes=processes,
    )
    tasks = get_summary_tasks(
        df_config=df_config,
        output_fmt=output_fmt,
        lengths_parsed=lengths_parsed,
        ignore_sample_comparisons=ignore_sample_comparisons,
        plot_fmt=plot_fmt,
    )
    logger.info(
        f"calculating summary metrics for {len(tasks)} labels using {processes} process(es)"
    )
    core.analysis.do_tasks(
        tasks,
        desc=definitions.PROGRESS_DESC_PARTITIONING,
        processes=processes,
    )


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
    if task.lengths_parsed:
        partition_lengths(task=task)
    for label, tags in zip(task.labels, task.tags):
        line_plot_data = []
        for idx, tag in enumerate(tags):
            df = core.utils.load(
                fn=(
                    core.utils.get_dir("PARTITION")
                    / label
                    / f"{label}.{tag}_vs_{definitions.REMAINDER_LABEL}.partition.{task.output_fmt}"
                ),
                columns=_COLUMNS,
            )
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
            df_sampling = downcast(
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
            )
            if task.plot_fmt is not None:
                if not df_sampling.empty:
                    line_plot_data.append([tag, SC_TG, df_sampling])
            core.utils.dump(
                df_sampling,
                fn=core.utils.format_fn(
                    fn=f"{label}.{tag}.{SC_TG}.curve.{task.output_fmt}",
                    prefix=core.utils.get_dir("PLOTS") / "curve" / label,
                ),
                index=False,
            )
            compare_row = {}
            compare_row["label"] = label
            compare_row["tag"] = tag
            compare_row["SC"] = SC_TG
            compare_row["OC"] = len(df[mask_present].index)
            compare_row["EC"] = EC_TG
            compare_row["OC_singleton"] = len(df[mask_present & mask_singleton].index)
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
        if line_plot_data:
            indices = np.argsort([_data[1] for _data in line_plot_data])[::-1]
            plot_tags = [line_plot_data[idx][0] for idx in indices]
            plot_SC = [line_plot_data[idx][1] for idx in indices]
            plot_dfs = [line_plot_data[idx][2] for idx in indices]
            plot_labels = [
                f"{tag} ({SC})" if int(SC) > 1 else f"{tag}"
                for tag, SC in zip(plot_tags, plot_SC)
            ]
            core.plot.lines(
                label,
                plot_dfs,
                plot_labels,
                x="EC",
                y="OCn",
                m="OT",
                max_lines=9,
                plot_fmt=task.plot_fmt,
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
        ).rename("l2m_TG1_TG2")
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
            "l2m_TG1_TG2",
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
            df_partition.reset_index(),
            fn=core.utils.format_fn(
                fn=(f"{fn}.partition.{task.output_fmt}"),
                prefix=core.utils.get_dir("PARTITION") / label,
            ),
            index=False,
        )
        # [VOLCANO]
        if task.plot_fmt is not None:
            df_volcano = df_partition[["l2m_TG1_TG2", "pvalue"]].dropna()
            if not df_volcano.empty:
                core.utils.dump(
                    df_volcano,
                    fn=core.utils.format_fn(
                        fn=(f"{fn}.volcano.{task.output_fmt}"),
                        prefix=core.utils.get_dir("PLOTS") / "volcano" / label,
                    ),
                    index=True,
                )
                core.plot.volcano(
                    x=df_volcano["l2m_TG1_TG2"],
                    y=df_volcano["pvalue"],
                    fn=core.utils.format_fn(
                        fn=(f"{fn}.volcano.{task.plot_fmt}"),
                        prefix=core.utils.get_dir("PLOTS") / "volcano" / label,
                    ),
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
    elif task.type == "repeatmasker":
        return do_parse_repeatmasker_task(task)
    elif task.type == "earlgrey":
        return do_parse_earlgrey_task(task)
    elif task.type == "bed":
        return do_parse_bed_task(task)
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
    lengths_parsed=False,
    ignore_sample_comparisons=False,
    plot_fmt=definitions.PLOT_FORMAT,
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
                plot_fmt=plot_fmt,
                lengths_parsed=lengths_parsed,
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
    plot_fmt=definitions.PLOT_FORMAT,
):
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
            plot_fmt=plot_fmt,
        )
        tasks.append(task)
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
