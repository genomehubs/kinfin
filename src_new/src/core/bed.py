import logging
import sys
import time

import core.analysis
import core.log
import definitions
import numpy as np
import pandas as pd
import tqdm

import core.utils

logger = logging.getLogger(__name__)


def do_parse_earlgrey_task(task):
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


def do_parse_bed(task):
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
    tasks = core.analysis.get_parse_tasks(
        directory=directory,
        func=do_parse_bed,
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
    results = core.analysis.do_tasks(
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
    try:
        df_counts = (
            pd.concat(df_beds, axis=0)
            .reset_index()
            .set_index(["orthogroup_id", "sample_id"])["count"]
            .unstack(fill_value=0)
        )
    except ValueError:
        logger.error("BED counts could not be joined. Verify input files.")
        sys.exit(1)
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
        core.utils.get_tally(
            output_fmt=output_fmt,
            plot_fmt=plot_fmt,
            do_plots=do_plots,
        )
    logger.info(
        core.utils.format_elapsed(time.monotonic() - t_0),
    )


# def do_parse_earlgrey_task(task):
#     try:
#         HEADER = [
#             "te_family",
#             "coverage",
#             "copies",
#         ]
#         HEADER_VALID = set(HEADER)
#         rows = []
#         with open(task.fn) as fh:
#             header = None
#             for line in fh:
#                 if header is None:
#                     header = HEADER
#                 else:
#                     row = {
#                         h: r for h, r in zip(header, line.split()) if h in HEADER_VALID
#                     }
#                     repeat_family, repeat_class_subclass = row["te_family"].split("#")
#                     repeat_class_subclass = repeat_class_subclass.split("/")
#                     rows.append(
#                         {
#                             "span": int(row["coverage"]),
#                             "count": int(row["copies"]),
#                             "repeat_family": repeat_family,
#                             "repeat_class": "Other"
#                             if len(repeat_class_subclass) == 1
#                             else repeat_class_subclass[0],
#                             "repeat_subclass": repeat_class_subclass[0]
#                             if len(repeat_class_subclass) == 1
#                             else repeat_class_subclass[1],
#                         }
#                     )
#         df_repeats = pd.DataFrame().from_dict(rows)
#         groups = ["repeat_class", "repeat_subclass", "repeat_family"]
#         for group in groups:
#             df_group = df_repeats.groupby(group).agg(
#                 span=("span", "sum"),
#                 count=("repeat_family", "sum"),
#             )
#             df_group["sample_id"] = task.sample_id
#             core.utils.dump(
#                 df_group,
#                 fn=core.utils.format_fn(
#                     f"{task.sample_id}.{group},{definitions.REPEATS_FN}",
#                     prefix=core.utils.get_dir("TMP") / task.sample_id,
#                 ),
#                 index=False,
#             )
#         core.utils.dump(
#             df_group,
#             fn=core.utils.format_fn(
#                 f"{task.sample_id}.{definitions.REPEATS_FN}",
#                 prefix=core.utils.get_dir("TMP") / task.sample_id,
#             ),
#             index=False,
#         )
#     except Exception as exc:
#         logger.error(f"problem reading {task.fn} - {exc}")


# def do_parse_repeatmasker_task(task):
#     HEADER = [
#         "score",
#         "div",
#         "del",
#         "ins",
#         "sequence",
#         "qstart",
#         "qend",
#         "qleft",
#         "C",
#         "repeat",
#         "family",
#         "mstart",
#         "mend",
#         "mleft",
#         "ID",
#         "last",
#     ]
#     HEADER_VALID = set(
#         [
#             "div",
#             "qstart",
#             "qend",
#             "repeat",
#             "family",
#         ]
#     )
#     rows = []
#     if task.fn is not None:
#         with open(task.fn) as fh:
#             header = None
#             for line in fh:
#                 if header is None:
#                     header = HEADER
#                 else:
#                     row = {
#                         h: r for h, r in zip(header, line.split()) if h in HEADER_VALID
#                     }
#                     if (
#                         task.params.get("min_div", 0.0)
#                         <= float(row["div"])
#                         <= task.params.get("max_div", 100.0)
#                     ):
#                         repeat_class_subclass = row["family"].split("/")
#                         rows.append(
#                             {
#                                 # "span": int(row["qend"]) - int(row["qstart"]) + 1,
#                                 "repeat_family": row["repeat"],
#                                 "repeat_class": "Other"
#                                 if len(repeat_class_subclass) == 1
#                                 else repeat_class_subclass[0],
#                                 "repeat_subclass": repeat_class_subclass[0]
#                                 if len(repeat_class_subclass) == 1
#                                 else repeat_class_subclass[1],
#                             }
#                         )
#         df_repeats = pd.DataFrame().from_dict(rows)
#         groups = ["repeat_class", "repeat_subclass", "repeat_family"]
#         for group in groups:
#             df_group = df_repeats.groupby(group).agg(
#                 # span=("span", "sum"),
#                 count=("repeat_family", "count"),
#             )
#             df_group["sample_id"] = task.sample_id
#             core.utils.dump(
#                 df_group,
#                 fn=core.utils.format_fn(
#                     f"{task.sample_id}.{group}.{definitions.REPEATS_FN}",
#                     prefix=core.utils.get_dir("TMP") / task.sample_id,
#                 ),
#                 index=False,
#             )
#         core.utils.dump(
#             df_group,
#             fn=core.utils.format_fn(
#                 f"{task.sample_id}.{definitions.REPEATS_FN}",
#                 prefix=core.utils.get_dir("TMP") / task.sample_id,
#             ),
#             index=False,
#         )
