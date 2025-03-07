import gzip
import json
import logging
import os
import sys
from math import log, sqrt
from typing import Any, Generator, List, Optional, Tuple, Union

import scipy

logger = logging.getLogger("kinfin_logger")


def progress(iteration: int, steps: Union[int, float], max_value: int) -> None:
    """
    Print progress in percentage based on the current iteration, steps, and maximum value.

    Parameters:
    - iteration (int): Current iteration or step number.
    - steps (int | float): Number of steps or intervals after which progress is updated.
    - max_value (int): Maximum value or total number of iterations.

    Returns:
    - None

    Example:
    >>> progress(5, 2, 10)
    [PROGRESS]     - 50%
    """
    if iteration == max_value:
        sys.stdout.write("\r")
        print("[PROGRESS]\t- %d%%" % (100))
    elif iteration % int(steps + 1) == 0:
        sys.stdout.write("\r")
        print("[PROGRESS]\t- %d%%" % (float(iteration / max_value) * 100), end=" ")
        sys.stdout.flush()


def check_file(filepath: Optional[str], install_kinfin: bool = False) -> None:
    """
    Check if a file exists.

    Args:
        filepath (str): Path to the file to be checked.

    Raises:
        FileNotFoundError: If the file does not exist.
    """

    if filepath is not None and not os.path.isfile(filepath):
        error_msg = f"[ERROR] - file {filepath} not found."
        if install_kinfin:
            error_msg += " Please run the install script to download kinfin."
        raise FileNotFoundError(error_msg)


def yield_file_lines(filepath: str) -> Generator[str, Any, None]:
    """
    Args:
        filepath (str): Path to the file.

    Yields:
        str: Each line from the file.
    """
    check_file(filepath)
    if filepath.endswith(".gz"):
        with gzip.open(filepath, "rb") as fh:
            for line in fh:
                line = line.decode("utf-8")
                if line.startswith("nodesDB.txt"):
                    line = f'#{line.split("#")[1]}'
                yield line.rstrip("\n")
    else:
        with open(filepath) as fh:
            for line in fh:
                yield line.rstrip("\n")


def yield_config_lines(
    config_f: str,
    taxon_idx_mapping_file: Optional[str],
):
    if config_f.endswith(".json"):
        if not taxon_idx_mapping_file:
            raise ValueError("[ERROR] - taxon_idx_mapping not present")

        with (
            open(taxon_idx_mapping_file, "r") as f_mapping,
            open(config_f, "r") as f_config,
        ):
            taxon_idx_mapping = json.load(f_mapping)
            config_data = json.load(f_config)
            headers = ["IDX"] + list(config_data[0].keys())
            yield "#" + ",".join(headers)

            for item in config_data:
                idx = taxon_idx_mapping[item.get("taxon") or item.get("TAXON")]
                row = [idx] + [item[key] for key in headers[1:]]
                yield ",".join(row)
    else:
        yield from yield_file_lines(config_f)

    return


def read_fasta_len(fasta_file: str) -> Generator[Tuple[str, int], Any, None]:
    """
    Generator function to parse a FASTA file and yield tuples of header and sequence length.

    Args:
    - fasta_file (str): Path to the FASTA file to be parsed.

    Yields:
    Tuple[str, int]: A tuple containing the header and the length of the sequence.

    Raises:
    FileNotFoundError: If the specified FASTA file does not exist.
    """
    check_file(fasta_file)
    with open(fasta_file) as fh:
        logger.info(f"[STATUS]\t - Parsing FASTA {fasta_file}")
        header: str = ""
        seqs: List[str] = []
        for line in fh:
            if line[0] == ">":
                if header:
                    header = (
                        header.replace(":", "_")
                        .replace(",", "_")
                        .replace("(", "_")
                        .replace(")", "_")
                    )  # orthofinder replaces chars
                    yield header, len("".join(seqs))
                header, seqs = (
                    line[1:-1].split()[0],
                    [],
                )  # Header is split at first whitespace
            else:
                seqs.append(line[:-1])
        header = (
            header.replace(":", "_")
            .replace(",", "_")
            .replace("(", "_")
            .replace(")", "_")
        )  # orthofinder replaces chars
        yield header, len("".join(seqs))


def median(lst) -> float:
    """
    Calculate the median of a list of numbers.

    Args:
    - lst (list): List of numerical values.

    Returns:
    - float: Median of the list.
    """
    list_sorted = sorted(lst)
    list_length = len(lst)
    index = (list_length - 1) // 2
    if list_length % 2:
        return list_sorted[index] / 1.0
    else:
        return (list_sorted[index] + list_sorted[index + 1]) / 2.0


def mean(lst) -> float:
    """
    Calculate the mean (average) of a list of numbers.

    Args:
    - lst (list): List of numerical values.

    Returns:
    - float: Mean of the list.
    """
    return float(sum(lst)) / len(lst) if lst else 0.0


def sd(lst, population=True) -> float:
    """
    Calculate the standard deviation of a list of numbers.

    Args:
    - lst (list): List of numerical values.
    - population (bool, optional): If True, calculates population standard deviation,
      otherwise calculates sample standard deviation. Default is True.

    Returns:
    - float: Standard deviation of the list.
    """
    n = len(lst)
    differences = [x_ - mean(lst) for x_ in lst]
    sq_differences = [d**2 for d in differences]
    ssd = sum(sq_differences)
    variance = ssd / n if population is True else ssd / (n - 1)
    return sqrt(variance)


def statistic(
    count_1: List[int],
    count_2: List[int],
    test: str,
    min_proteomes: int,
) -> Tuple[
    Optional[float],
    Optional[float],
    Optional[float],
    Optional[float],
]:
    """
    Perform statistical tests and calculate relevant statistics between two lists of counts.

    Args:
    - count_1 (list): List of counts (integers).
    - count_2 (list): Another list of counts (integers).
    - test (str): Type of statistical test to perform, one of "welch", "mannwhitneyu", "ttest", "ks", "kruskal".
    - min_proteomes (int): Minimum number of proteomes required for valid analysis.

    Returns:
    - Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
      Tuple containing:
      - pvalue: p-value of the statistical test (or None if test is not applicable).
      - log2_mean: Logarithm base 2 of the mean of count_1 divided by count_2.
      - mean_count_1: Mean of count_1.
      - mean_count_2: Mean of count_2.
    """
    pvalue: Optional[float] = None
    log2_mean: Optional[float] = None
    mean_count_1: Optional[float] = None
    mean_count_2: Optional[float] = None

    implicit_count_1: List[float] = [count for count in count_1 if count > 0]
    implicit_count_2: List[float] = [count for count in count_2 if count > 0]

    if len(implicit_count_1) < min_proteomes or len(implicit_count_2) < min_proteomes:
        return None, None, None, None

    mean_count_1 = mean(implicit_count_1)
    mean_count_2 = mean(implicit_count_2)
    log2_mean = log(mean_count_1 / mean_count_2, 2)

    if (
        len(set(implicit_count_1)) == 1
        and len(set(implicit_count_2)) == 1
        and set(implicit_count_1) == set(implicit_count_2)
    ):  # equal
        pvalue = 1.0
    elif test == "welch":
        # try:
        # Welch's t-test
        pvalue = scipy.stats.ttest_ind(
            implicit_count_1,
            implicit_count_2,
            equal_var=False,
        )[1]

        if pvalue != pvalue:  # testing for "nan"
            pvalue = 1.0
    elif test == "mannwhitneyu":
        try:
            pvalue = scipy.stats.mannwhitneyu(
                implicit_count_1,
                implicit_count_2,
                alternative="two-sided",
            )[1]
        except ValueError:  # throws ValueError when all numbers are equal
            pvalue = 1.0
    elif test == "ttest":
        # try:
        pvalue = scipy.stats.ttest_ind(implicit_count_1, implicit_count_2)[1]  # t-test
        if pvalue != pvalue:  # testing for "nan"
            pvalue = 1.0
    elif test == "ks":
        # H0 that they are drawn from the same distribution
        pvalue = scipy.stats.ks_2samp(implicit_count_1, implicit_count_2)[1]
        if pvalue != pvalue:  # testing for "nan"
            pvalue = 1.0
    elif test == "kruskal":
        # H0 is that population median is equal
        pvalue = scipy.stats.kruskal(implicit_count_1, implicit_count_2)[1]
        if pvalue != pvalue:  # testing for "nan"
            pvalue = 1.0
    return pvalue, log2_mean, mean_count_1, mean_count_2
