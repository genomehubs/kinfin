import json
import logging
import logging.config
import os
import pathlib

import core.utils
from definitions import LOG_CONFIG

FORMAT = "[%(asctime)s] [%(levelname)-7s] [%(name)-14s] [%(funcName)s] %(message)s"


def init_logger(
    args={},
    default_config=LOG_CONFIG,
    default_level=logging.INFO,
    env_key="LOG_CFG",
    append=False,
):
    if not args:
        logging.basicConfig(level=default_level, format=FORMAT)
        logger = logging.getLogger(__name__)
    else:
        # LOG_CFG=my_logging.json python my_server.py
        log_fn = pathlib.Path(args.d) / f"kinfin.{args.command}.log"
        level = logging.DEBUG if args.v else default_level
        if not append:
            log_fn.unlink(missing_ok=True)
        env_log = os.getenv(env_key, None)
        config_path = env_log if env_log else default_config
        if os.path.exists(config_path):
            with open(config_path, "rt") as f:
                config = json.load(f)
            config["handlers"]["logfile"]["level"] = level
            config["handlers"]["console"]["level"] = level
            config["handlers"]["logfile"]["filename"] = log_fn
            config["formatters"]["simple"]["format"] = FORMAT
            logging.config.dictConfig(config)
        logger = logging.getLogger(__name__)
        logger.info(
            f"{logger.level} logging enabled: file='{core.utils.format_fn(log_fn)}'"
        )
