import logging
import sys
import time

import core.analysis
import core.log

logger = logging.getLogger(__name__)


def run(args):
    t_0 = time.monotonic()
    core.log.init_logger(args)
    logger.info(f"{args=}")
    df = core.utils.load(args.TABLE_FN)
    core.utils.dump(df, fn=sys.stdout, fmt=args.f, index=args.i)
    logger.info(core.utils.format_elapsed(time.monotonic() - t_0))
