import collections
import logging
import math
import sys
import time
import traceback

import core.log
import definitions
import numpy as np
import pandas as pd
import tqdm

import core.utils

logger = logging.getLogger(__name__)


def get_parse_interpro_tasks(
    directory=None,
    sample_ids=[],
):
    tasks = core.analysis.get_parse_tasks(
        directory=directory,
        func=do_parse_interpro,
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
                core.analysis.ParseTask(
                    type=do_parse_interpro,
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


def do_parse_interpro(task):
    # fn, sample_id
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
            df_annotation = core.utils.downcast(
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
        logger.error(f"{exc}\n{traceback.format_exc()}")
        sys.exit(1)
    get_signature_summary(
        df=df_annotation,
        analyses=analyses,
        sample_id=task.sample_id,
    )
    df_annotation = (
        core.utils.downcast(df_annotation)
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


def get_signature_summary(df, analyses=[], sample_id=None):
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


def parse_interpro(
    directory=None,
    sample_ids=[],
    output_fmt="tsv",
    processes=1,
):
    t_0 = time.monotonic()
    tasks = get_parse_interpro_tasks(
        directory=directory,
        sample_ids=sample_ids,
    )
    processes = 1 if len(tasks) == 1 else processes
    logger.info(f"parsing {len(tasks)} file(s) using {processes} process(es)")
    core.analysis.do_tasks(
        tasks=tasks,
        desc=definitions.PROGRESS_DESC_INTERPRO,
        processes=processes,
        collect_results=True,
    )
    logger.info(f"{core.utils.format_elapsed(time.monotonic() - t_0)}")


def analyse_interpro(
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
    logger.info("joining interpro data ...")
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
    df_annotations = core.utils.downcast(df_annotations)
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
    analyse_domain_entropy(
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


def analyse_domain_entropy(df_annotation, output_fmt="tsv"):
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


def process_interpro(
    directory=None,
    sample_ids=[],
    output_fmt="tsv",
    processes=1,
):
    t_0 = time.monotonic()
    logger.info(f"processing interpro data in {directory}")
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
    analyse_interpro(
        sample_ids=sample_ids,
        processes=processes,
        output_fmt=output_fmt,
    )
    logger.info(f"[elapsed: {time.monotonic() - t_0}")
