import logging
import shutil
import sys
import time

import core.analysis
import core.bed
import core.log
import core.tree
import definitions

logger = logging.getLogger(__name__)


def cleanup(keep_dir=False, verbose=False):
    logger.info("deleting temporary files ...")
    if not keep_dir:
        tmp_dir = core.utils.get_dir("TMP")
        logger.debug(f"\tdeleting directory {tmp_dir}")
        shutil.rmtree(
            tmp_dir,
            ignore_errors=True,
        )
    logger.debug(f"\tdeleting file {definitions.TMP_PATHS_FILE}")
    definitions.TMP_PATHS_FILE.unlink()
    logger.info("done")


def run(args):
    t_0 = time.monotonic()
    # [ToDo] put everything 'setup' into one function
    # create basic DIRs (before core.log.init_logger!)
    core.utils.mkdir(
        name=args.d,
        subdirs="initbed",
        do_replace=True,
    )
    core.log.init_logger(args)
    if args.v:
        for k, v in vars(args).items():
            logger.debug(f"[args] {f'{k}={v}'}")
    # testament
    core.utils.testament(
        cleanup,
        keep_dir=args.N,
    )
    # get config
    df_config = core.analysis.process_config(
        config_fn=args.c,
        taxonomic_ranks=args.r,
    )
    # create sample TMP dirs
    core.utils.mkdir(
        name=core.utils.get_dir("TMP"),
        subdirs=list(df_config.sample_id),
        do_replace=False,
    )
    # create partition DIRs
    core.utils.mkdir(
        name=core.utils.get_dir("PARTITION"),
        subdirs=["sample_ids"] + list(df_config.columns),
        do_replace=False,
    )
    if not args.L:
        core.utils.mkdir(
            name=core.utils.get_dir("PLOTS"),
            subdirs=[
                "/".join([d1, d2])
                for d1 in ["curve", "volcano"]
                for d2 in ["sample_ids"] + list(df_config.columns)
            ]
            + [
                "tally",
            ],
            do_replace=False,
        )
    core.bed.process_bed(
        directory=args.b,
        sample_ids=list(df_config.sample_id),
        count_idx=args.C,
        name_idxs=args.e,
        name_sep=args.s,
        has_header=args.B,
        output_fmt=args.F,
        plot_fmt=args.l,
        do_plots=(not args.L),
        processes=args.p,
    )
    # [TREE]
    if args.t:
        core.tree.process_tree(
            tree_fn=args.t,
            outgroup=args.o,
            sample_ids=list(df_config.sample_id),
            output_fmt=args.F,
        )
    tasks = core.analysis.get_comparison_tasks(
        df_config=df_config,
        count_target=args.n,
        count_min=args.m,
        count_max=args.M,
        count_fraction=args.x,
        output_fmt=args.F,
        ignore_sample_comparisons=args.X,
    )
    logger.info(
        f"calculating {len(tasks)} comparisons between taxon-groups using {args.p} process(es)"
    )
    core.analysis.do_tasks(
        tasks,
        desc=definitions.PROGRESS_DESC_PARTITIONING,
        processes=args.p,
    )
    tasks = core.analysis.get_summary_tasks(
        df_config=df_config,
        output_fmt=args.F,
        ignore_sample_comparisons=args.X,
        plot_fmt=args.l if not args.L else None,
    )
    logger.info(
        f"calculating summary metrics for {len(tasks)} labels using {args.p} process(es)"
    )
    core.analysis.do_tasks(
        tasks,
        desc=definitions.PROGRESS_DESC_PARTITIONING,
        processes=args.p,
    )
    logger.info("SUCCESS.")
    logger.info(core.utils.format_elapsed(time.monotonic() - t_0))
    sys.exit(0)
