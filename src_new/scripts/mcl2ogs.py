#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import itertools
import logging
import math
import pathlib
import sys
import warnings

import pandas as pd

# LOGGING (only log to stderr, move somewhere)


logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] [%(levelname)s] - %(message)s",
    stream=sys.stderr,
)

logger = logging.getLogger(__file__)

EPILOG = """"""

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def str_or_none(value):
    msg = f"must be a string or None (not '{value}')"
    try:
        if value is None or value == "None":
            return None
        else:
            return str(value)
    except Exception:
        raise argparse.ArgumentTypeError(msg)
    raise argparse.ArgumentTypeError(msg)


def int_zero_or_positive(value):
    msg = f"must be zero or positive integer (not '{value}')"
    try:
        number = int(value)
        if number >= 0:
            return number
        else:
            raise argparse.ArgumentTypeError(msg)
    except Exception:
        raise argparse.ArgumentTypeError(msg)
    raise argparse.ArgumentTypeError(msg)


def float_or_empty_list(value):
    msg = f"must be empty list or list of numbers (not '{value}')"
    try:
        if value is None:
            return value
        else:
            return float(value)
    except Exception:
        raise argparse.ArgumentTypeError(msg)
    return value


def existing_dir(directory):
    directory = pathlib.Path(directory)
    if not pathlib.Path.is_dir(directory):
        raise argparse.ArgumentTypeError(f"directory '{directory}' does not exist")
    return directory


def existing_file(infile):
    infile = pathlib.Path(infile)
    if not pathlib.Path.is_file(infile):
        raise argparse.ArgumentTypeError(f"file '{infile}' does not exist")
    return infile


def get_argparse():
    class CustomFormatter(
        argparse.ArgumentDefaultsHelpFormatter,
        argparse.RawDescriptionHelpFormatter,
    ):
        pass

    parser = argparse.ArgumentParser(
        formatter_class=CustomFormatter,
        epilog=EPILOG,
    )
    parser.add_argument(
        "-p",
        metavar="PAIRS",
        required=True,
        type=existing_file,
        help="clusters_OrthoFinder.txt_id_pairs.txt",
    )
    parser.add_argument(
        "-b",
        required=False,
        nargs="*",
        type=float_or_empty_list,
        default=[],
        help="""Bin edges (in absolute values) between which values in column will be binned.
        E.g.: '-b 0.5 20 90 120' will cause values in column to be placed into the following bins:
        (MIN, 0.5], (0.5, 20], (20, 90] (90, 120], (120, MAX]  (default: '%(default)s')""",
    )
    parser.add_argument(
        "-B",
        required=False,
        nargs="*",
        type=float_or_empty_list,
        default=[],
        help="""Bin edges (in proportional values) between which values in column will be binned.
        If not specified, bin edges 0.0 and 1.0 are inferred.
        E.g.: '-b 0.2 0.5 0.75 1.0' will cause values in column to be placed into the following bins:
        (0.0, 0.2], (0.2, 0.5], (0.75, 1.0] (default: '%(default)s')""",
    )
    parser.add_argument(
        "-x",
        required=False,
        type=float,
        default=1e-6,
        help="""Value by which bins are extended on each side to include the minimum and maximum values of x.
        Only applies to '-B' and '-b' (default: '%(default)s')""",
    )
    parser.add_argument(
        "-e",
        required=False,
        type=int,
        default=0,
        help="Number of equal-width bins into which values in columns will be binned. (default: '%(default)s')",
    )
    parser.add_argument(
        "-E",
        required=False,
        type=int,
        default=0,
        help="Number of equal-size bins (quantiles) into which values in columns will be binned. (default: '%(default)s')",
    )
    parser.add_argument(
        "-l",
        required=False,
        nargs="*",
        type=str,
        help="Custom labels of bins. Must match number of bins. (default: '%(default)s', i.e. string of interval is used)",
    )
    parser.add_argument(
        "-a",
        action="store_true",
        help="Use letters as labels of bins (default: '%(default)s', i.e. string of interval is used)",
    )
    parser.add_argument(
        "-n",
        action="store_true",
        help="Use integers as labels of bins (default: '%(default)s', i.e. string of interval is used)",
    )
    parser.add_argument(
        "-c",
        metavar="COLUMN_IN",
        required=True,
        type=int_zero_or_positive,
        default=None,
        help="Index of column (0-based) to bin. (default: '%(default)s')",
    )
    parser.add_argument(
        "-C",
        metavar="COLUMN_NAME",
        required=True,
        type=str,
        help="Name of column into which to the results are inserted",
    )
    args = parser.parse_args()
    if not any([args.b, args.B, args.e, args.E]):
        parser.error("must specify either '-b' or '-B' or '-e' or '-E'")
    if args.B:
        invalid_values = []
        for value in args.B:
            if not 0.0 <= value <= 1.0:
                invalid_values.append(value)
        if invalid_values:
            parser.error(
                f"values for '-B' myst be between 0.0 and 1.0. The following values are invalid: {invalid_values}"
            )
    return args


def label_results(
    result=None,
    intervals=None,
    labels=False,
    bins=[],
    n=False,
    a=False,
):
    if not result.dtype == "category":
        result = result.astype("category")
    interval_count = intervals if isinstance(intervals, int) else len(intervals)
    if n:
        labels = list(range(interval_count))
    elif a:
        labels = [
            "".join(x)
            for i in range(1, math.ceil(interval_count / len(LETTERS)) + 1)
            for x in itertools.combinations_with_replacement(LETTERS, i)
        ][:interval_count]
    elif labels:
        if not interval_count == len(labels):
            logger.error(
                f"{interval_count} labels are needed. You provided {len(labels)} label(s)!"
            )
            sys.exit(1)
    else:
        labels = [str(interval).replace(" ", "") for interval in intervals]
    result = result.cat.rename_categories(labels)
    return (result, labels)


def process_file(args):
    sep = "," if args.f.suffix[1:] == "csv" else "\t"
    warnings.simplefilter("error", pd.errors.DtypeWarning)
    try:
        df = pd.read_csv(args.f, sep=sep, header=None)
    except pd.errors.DtypeWarning:
        # skip first column if header
        df = pd.read_csv(args.f, sep=sep, header=0)
    if not pd.api.types.is_numeric_dtype(df.iloc[:, args.c].dtype):
        # error if column is not numeric
        logger.error(
            f"Column {args.c} must be numeric but is '{df.iloc[:, args.c].dtype}' ..."
        )
        header = "[FILE] "
        lines = [line for line in df.__repr__().split("\n")]
        logger.error(f"{header}" + "#" * (len(lines[0]) - len(header)))
        for line in lines:
            logger.error(f"{line}")
        logger.error("#" * len(lines[0]))
        sys.exit(1)
    values = df.iloc[:, args.c]
    _min = float(values.min() - args.x)
    _max = float(values.max())
    if args.b or args.B:
        breaks = sorted(
            set(
                (args.b if args.b else [value * _max for value in args.B])
                + [_min, _max]
            )
        )
        intervals = pd.IntervalIndex.from_breaks(breaks)
    else:
        intervals = args.e or args.E
    labels = args.l or False
    if args.E:
        result, bins = pd.qcut(
            x=values,
            q=args.E,
            labels=labels,
            retbins=True,
            precision=3,
        )
    else:
        result, bins = pd.cut(
            x=values,
            bins=intervals,
            labels=labels,
            retbins=True,
            precision=3,
            include_lowest=True,
            duplicates="raise",
            ordered=True,
        )
    if args.E or args.e:
        intervals = pd.IntervalIndex.from_breaks(
            [float(_bin) for _bin in bins.tolist()]
        )
    result, labels = label_results(
        result=result,
        intervals=intervals,
        labels=args.l,
        bins=bins,
        n=args.n,
        a=args.a,
    )
    df.insert(
        loc=args.c,
        column=args.C,
        value=result,
        allow_duplicates=True,
    )
    summary = []
    for k, v in vars(args).items():
        summary.append(f"[args] {f'{k}={v}'}")
    for label, interval in zip(labels, intervals):
        summary.append(f"{label} := {interval} => {result[result == label].count()}")
    for line in summary:
        logger.info(line)
    fn = f"{args.f.stem}.binned{args.f.suffix}"
    print(df)
    df.to_csv(fn, sep=sep)
    logger.info(f"wrote '{fn}'")


if __name__ == "__main__":
    args = get_argparse()
    process_file(args)
