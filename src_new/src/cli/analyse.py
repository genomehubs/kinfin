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
            output_fmt=args.F,
        )
        sample_ids_source = "fasta"
    # [SEQUENCE/SPECIES IDs]
    elif args.s and args.S:
        core.analysis.get_ids(
            sequence_ids_fn=args.s,
            species_ids_fn=args.S,
            sample_ids=list(df_config.sample_id),
            output_fmt=args.F,
        )
        sample_ids_source = "sids"
    # [INFER IDs FROM OGs]
    elif args.P:
        sample_ids_source = "parse"
    else:
        sys.exit(1)
    # [ORTHOGRPUPS]
    df_orthogroups = core.analysis.get_orthogroups(
        args.g,
        sample_ids=list(df_config.sample_id),
        output_fmt=args.F,
        sample_ids_source=sample_ids_source,  # [ToDo] add
    )
    # [COUNTS]
    df_counts = core.analysis.get_counts(
        df_orthogroups,
        output_fmt=args.F,
    )
    # [TREE]
    # - [ToDo] bundle tree stuff into one function
    if args.t:
        tree = core.analysis.get_tree(
            fn=args.t,
            outgroup=args.o,
        )
        _ = core.analysis.get_df_nodes(
            df_counts,
            tree=tree,
            output_fmt=args.F,
        )
    # [ANNOTATION]
    # [ToDo] 
    # - bundle annotation stuff into one function
    # - 
    if args.i:
        df_interpro = core.analysis.get_df_interpro(
            fn=args.i,
            output_fmt=args.F,
        )
        _ = core.analysis.get_df_annotation(
            df_orthogroups=df_orthogroups,
            df_interpro=df_interpro,
            df_counts=df_counts,
            output_fmt=args.F,
        )
    tasks = core.analysis.get_comparison_tasks(
        df_config=df_config,
        df_counts=df_counts,
        count_target=args.n,
        count_min=args.m,
        count_max=args.M,
        count_fraction=args.x,
        output_fmt=args.F,
        ignore_sample_comparisons=args.X,
    )
    core.analysis.do_tasks(
        tasks,
        desc=f"calculating {len(tasks)} comparisons between taxon-groups using {args.p} process(es)",
        processes=args.p,
    )
    tasks = core.analysis.get_summary_tasks(
        df_config=df_config,
        output_fmt=args.F,
        ignore_sample_comparisons=args.X,
    )
    core.analysis.do_tasks(
        tasks,
        desc=f"calculating summary metrics for {len(tasks)} labels using {args.p} process(es)",
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
