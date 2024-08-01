import time

from core.datastore import DataFactory
from core.input import InputData
import logging

logger = logging.getLogger("kinfin_logger")


def analyse(input_data: InputData) -> None:
    """
    Performs KinFin analysis based on the provided input data using DataFactory.

    Args:
        input_data (InputData): An instance of InputData containing input parameters and data.

    Returns:
        None

    Raises:
        Any exceptions raised by DataFactory methods.
    """
    overall_start = time.time()
    dataFactory = DataFactory(input_data)
    dataFactory.setup_dirs()
    dataFactory.analyse_clusters()
    dataFactory.aloCollection.write_tree(
        dataFactory.dirs,
        dataFactory.inputData.plot_tree,
        dataFactory.inputData.plot_format,
        dataFactory.inputData.fontsize,
    )
    rarefaction_data = dataFactory.aloCollection.compute_rarefaction_data(
        repetitions=dataFactory.inputData.repetitions
    )
    dataFactory.plot_rarefaction_data(
        dirs=dataFactory.dirs,
        plotsize=dataFactory.inputData.plotsize,
        plot_format=dataFactory.inputData.plot_format,
        fontsize=dataFactory.inputData.fontsize,
        rarefaction_by_samplesize_by_level_by_attribute=rarefaction_data,
    )
    dataFactory.write_output()
    overall_end = time.time()
    overall_elapsed = overall_end - overall_start
    logger.info(f"[STATUS] - Took {overall_elapsed}s to run kinfin.")
