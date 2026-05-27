import logging
import shutil
import sys
import time

import core.analysis
import core.log
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
        subdirs="init",
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
    df_config = core.analysis.get_config(
        config_fn=args.c,
        taxonomic_ranks=args.r,
    )
    # create partition DIRs
    core.utils.mkdir(
        name=core.utils.get_dir("PARTITION"),
        subdirs=["sample_ids"] + list(df_config.columns),
        do_replace=False,
    )
    # [FASTA IDs]
    if args.f:
        core.analysis.get_elements(
            directory=args.f,
            sample_ids=list(df_config.sample_id),
            processes=args.p,
        )
        sample_ids_source = "fasta"
    # [SEQUENCE/SPECIES IDs]
    elif args.s and args.S:
        core.analysis.get_ids(
            sequence_ids_fn=args.s,
            species_ids_fn=args.S,
            sample_ids=list(df_config.sample_id),
        )
        sample_ids_source = "sids"
    # [INFER IDs FROM OGs]
    elif args.P:
        sample_ids_source = "parse"
    else:
        sys.exit(1)

    # [ORTHOGRPUPS]
    core.analysis.get_orthogroups(
        args.g,
        sample_ids=list(df_config.sample_id),
        sample_ids_source=sample_ids_source,
    )

    # [TREE]
    if args.t:
        core.analysis.process_tree(
            tree_fn=args.t,
            outgroup=args.o,
            sample_ids=list(df_config.sample_id),
            output_fmt=args.F,
        )

    # [ANNOTATION]
    if args.i or args.I:
        core.analysis.process_interpro(
            fn=args.i,
            directory=args.I,
            sample_ids=list(df_config.sample_id),
            output_fmt=args.F,
            processes=args.p,
        )
        core.analysis.get_df_entropy(
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
    # tasks += core.analysis.get_summary_tasks(
    #     df_config=df_config,
    #     type="plot",
    #     output_fmt=args.F,
    #     ignore_sample_comparisons=args.X,
    # )
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
        type="summary",
        output_fmt=args.F,
        ignore_sample_comparisons=args.X,
    )
    logger.info(
        f"calculating summary metrics for {len(tasks)} labels using {args.p} process(es)"
    )
    core.analysis.do_tasks(
        tasks,
        desc=definitions.PROGRESS_DESC_PARTITIONING,
        processes=args.p,
    )
    # rarefaction_data = dataFactory.aloCollection.compute_rarefaction_data(
    #     repetitions=dataFactory.inputData.repetitions
    # )
    # dataFactory.plot_rarefaction_data(
    #     dirs=dataFactory.dirs,
    #     plotsize=dataFactory.inputData.plotsize,
    #     plot_format=dataFactory.inputData.plot_format,
    #     fontsize=dataFactory.inputData.fontsize,
    #     rarefaction_by_samplesize_by_level_by_attribute=rarefaction_data,
    # )
    logger.info("done")
    logger.info(core.utils.format_elapsed(time.monotonic() - t_0))
    sys.exit(0)
