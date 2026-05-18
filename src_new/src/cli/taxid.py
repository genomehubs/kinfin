import logging
import time

import core.analysis
import core.log

logger = logging.getLogger(__name__)


def run(args):
    t_0 = time.monotonic()
    core.log.init_logger(args)
    logger.info(f"{args=}")
    for k, v in vars(args).items():
        logger.info(f"[args] {f'{k}={v}'}")
    df_config = core.utils.load(args.c)
    _ = core.analysis.get_taxids(
        df_config,
        output_dir=args.d,
        output_fmt=args.F,
        update_taxdump=args.u,
        update_taxonomy=args.u,
    )
    logger.info(core.utils.format_elapsed(time.monotonic() - t_0))
