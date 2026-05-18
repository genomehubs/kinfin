import logging
import time

import core.analysis
import core.log

logger = logging.getLogger(__name__)


def run(args):
    t_0 = time.monotonic()
    core.log.init_logger(args)
    logger.info(f"{args=}")
    df = core.utils.load(args.TABLE_FN)
    print(df)
    logger.info(core.utils.format_elapsed(time.monotonic() - t_0))
