import os

from core.input import InputData
from core.logger import setup_logger
from core.results import analyse


def run_cli(args: InputData) -> None:
    """
    Run the command-line interface to perform analysis based on the provided input data.

    Args:
        args (InputData): An instance of InputData containing input parameters and data.

    Returns:
        None
    """
    log_path = os.path.join(args.output_path, "kinfin.log")
    setup_logger(log_path)
    analyse(args)
