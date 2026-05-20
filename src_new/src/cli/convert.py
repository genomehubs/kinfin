import logging
import time

import core.log
import core.utils

logger = logging.getLogger(__name__)


def run(args):
    t_0 = time.monotonic()
    args.d, args.v = "", True
    core.log.init_logger(args)
    core.utils.dump(
        core.utils.load(args.t),
        fn=core.utils.format_fn(
            args.t,
            prefix=".",
            suffix=f".{args.F}",
        ),
        index=args.i,
    )
    logger.info(core.utils.format_elapsed(time.monotonic() - t_0))
