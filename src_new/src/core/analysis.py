import collections
import contextlib
import glob
import itertools
import logging
import multiprocessing
import pathlib
import sys
import time

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
        "func",
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
        "func",
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
        "func",
        "sample_id",
        "fn",
        "params",
    ],
)


@contextlib.contextmanager
def poolcontext(*args, **kwargs):
    pool = multiprocessing.Pool(*args, **kwargs)
    yield pool
    pool.terminate()


"""

[ToDo]
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
    func=None,
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
                        func=func,
                        sample_id=sample_id,
                        fn=fn,
                        params=params,
                    )
                )
    return tasks


# [DONE]
def do_parse_fasta(task):
    # fn, sample_id
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
            df_fasta = core.utils.downcast(
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
                core.utils.downcast(df, categorical=["sample_id"]),
                fn=core.utils.format_fn(
                    fn=definitions.ELEMENTS_FN,
                    prefix=core.utils.get_dir("INPUT"),
                ),
                index=False,
            )
    except Exception as exc:
        logger.error(f"unexpected error - {exc}")
    sys.exit(1)


def process_elements(
    directory=None,
    sample_ids=[],
    processes=1,
):
    t_0 = time.monotonic()
    tasks = get_parse_tasks(
        directory=directory,
        func=do_parse_fasta,
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
        core.utils.downcast(
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


def process_orthogroups(
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
    logger.info(
        f"{core.utils.format_number(df_orthogroups['orthogroup_id'].nunique())} orthogroup(s) in file"
    )
    duplicated_elements_count = int(
        (df_orthogroups["element_id"].value_counts() > 1).value_counts().get(True, 0)
    )
    if duplicated_elements_count > 0:
        logger.warning(
            f"{core.utils.format_number(duplicated_elements_count)} duplicated element(s) found"
        )
        df_orthogroups["OG_EC"] = df_orthogroups["orthogroup_id"].map(
            df_orthogroups["orthogroup_id"].value_counts().to_dict()
        )
        df_dupes = df_orthogroups[
            df_orthogroups.duplicated("element_id", keep=False)
        ].sort_values(by=["element_id", "OG_EC"], ascending=False)
        logger.warning(
            f"writing duplicated element(s) to '{core.utils.get_dir('INPUT') / definitions.ORTHOGROUPS_DUPES_FN}'"
        )
        core.utils.dump(
            df_dupes,
            fn=core.utils.format_fn(
                definitions.ORTHOGROUPS_DUPES_FN,
                prefix=core.utils.get_dir("INPUT"),
            ),
            index=False,
        )
        if ignore_duplicated_elements:
            # remove dupes with lower OG_EC (should be singletons)
            logger.warning("removing duplicated element(s)")
            df_orthogroups = (
                df_orthogroups.loc[
                    df_orthogroups.groupby(["element_id"])["OG_EC"].idxmax()
                ]
                .sort_index(ignore_index=True)
                .drop(["OG_EC"], axis=1)
            )
            logger.warning(
                f"{core.utils.format_number(df_orthogroups['orthogroup_id'].nunique())} orthogroup(s) remaining"
            )
        else:
            logger.warning(
                "can't proceed with duplicated elements. Either provide a different file or rerun with (-U)"
            )
            core.utils.dump(
                df_orthogroups,
                fn=core.utils.format_fn(
                    definitions.ORTHOGROUPS_FN,
                    prefix=core.utils.get_dir("INPUT"),
                ),
                index=False,
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
    logger.info(f"{core.utils.format_number(orthogroups_count)} orthogroup(s) parsed")
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
        core.utils.get_tally(
            output_fmt=output_fmt,
            plot_fmt=plot_fmt,
            do_plots=do_plots,
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


def summary_function(task):
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
            df_sampling = core.utils.downcast(
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
            core.utils.downcast(pd.DataFrame.from_dict(compare_rows)),
            fn=core.utils.format_fn(
                fn=f"{label}.summary.{task.output_fmt}",
                prefix=core.utils.get_dir("PARTITION") / label,
            ),
            index=False,
        )
    return True


def comparison_function(task):
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
                prefix = core.utils.get_dir("PLOTS") / "volcano" / label
                core.utils.dump(
                    df_volcano,
                    fn=core.utils.format_fn(
                        fn=(f"{fn}.volcano.{task.output_fmt}"),
                        prefix=prefix,
                    ),
                    index=True,
                )
                core.plot.volcano(
                    x=df_volcano["l2m_TG1_TG2"],
                    y=df_volcano["pvalue"],
                    fn=core.utils.format_fn(
                        fn=(f"{fn}.volcano.{task.plot_fmt}"),
                        prefix=prefix,
                    ),
                )

    return True


def do_task(task):
    return task.func(task)


def do_tasks(
    tasks=[],
    desc="",
    processes=1,
    collect_results=False,
):
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
                func=summary_function,
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
            func=comparison_function,
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


def process_config(
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
