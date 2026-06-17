#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os

import definitions


def existing_file(infile):
    if not os.path.isfile(infile):
        raise argparse.ArgumentTypeError(f"file '{infile}' does not exist")
    return infile


def existing_files(infiles):
    for infile in infiles:
        existing_file(infile)
    return infiles


def existing_dir(directory):
    if not os.path.isdir(directory):
        raise argparse.ArgumentTypeError(f"directory '{directory}' does not exist")
    return directory


def int_positive(value):
    msg = f"must be a positive integer (not '{value}')"
    try:
        number = int(value)
        if number > 0:
            return number
    except Exception:
        raise argparse.ArgumentTypeError(msg)
    raise argparse.ArgumentTypeError(msg)


def int_zero_or_positive(value):
    msg = f"must be zero or positive integer (not '{value}')"
    try:
        number = int(value)
        if number >= 0:
            return number
    except Exception:
        raise argparse.ArgumentTypeError(msg)
    raise argparse.ArgumentTypeError(msg)


def float_proportion(value):
    msg = f"must be a value between 0.0 and 1.0 (not '{value}')"
    try:
        number = float(value)
        if 0.0 < number < 1.0:
            return number
    except Exception:
        raise argparse.ArgumentTypeError(msg)
    raise argparse.ArgumentTypeError(msg)


def add_reps_parser(subparsers):
    subparser = subparsers.add_parser(
        "reps",
        help="start KinFin analysis of repeat/TE data",
    )
    subparser._optionals.title = "[optional]"
    subparser_required = subparser.add_argument_group("[essential]")
    subparser_parameters = subparser.add_argument_group("[parameters]")
    subparser_required.add_argument(
        "-c",
        metavar="CONFIG_FN",
        required=True,
        type=existing_file,
        help="Config file in CSV or JSON",
    )
    subparser_required.add_argument(
        "-e",
        metavar="REPEATMASKER_DIR",
        required=False,
        type=existing_dir,
        help="Directory containing Repeatmasker (*.out) files to parse",
    )
    subparser_required.add_argument(
        "-m",
        metavar="MIN_DIV",
        required=False,
        type=float,
        default=0.0,
        help="Minimum divergence when filtering Repeatmasker (*.out) files (default: %(default)s)",
    )
    subparser_required.add_argument(
        "-M",
        metavar="MAX_DIV",
        required=False,
        type=float,
        default=100.0,
        help="Maximum divergence when filtering Repeatmasker (*.out) files (default: %(default)s)",
    )
    subparser_required.add_argument(
        "-E",
        metavar="EARLGREY_DIR",
        required=False,
        type=existing_dir,
        help="Directory containing Earlgrey (*.familyLevelCount.txt) files to parse",
    )
    subparser_parameters.add_argument(
        "-t",
        metavar="TREE_FN",
        required=False,
        type=existing_file,
        help="Tree file in Newick format. Sample IDs must be the same as 'sample_ids' in CONFIG_FN",
    )
    subparser_parameters.add_argument(
        "-o",
        metavar="OUTGROUP",
        required=False,
        type=str,
        nargs="*",
        default=[],
        help="Sample-ID(s) (space-separated) that will be used as outgroup when parsing TREE_FN. Must be monophyletic.",
    )
    subparser_parameters.add_argument(
        "-r",
        metavar="TAXRANKS",
        required=False,
        choices=definitions.ARGS_TAXONOMY_RANKS_SUPPORTED,
        nargs="*",
        default=definitions.ARGS_TAXONOMY_RANKS_DEFAULT,
        help=f"Taxonomic ranks to be inferred from NCBI 'taxids' column in config file (or None to ignore) (default: {' '.join(definitions.ARGS_TAXONOMY_RANKS_DEFAULT)})",
    )
    subparser_parameters.add_argument(
        "-d",
        metavar="OUTDIR",
        type=str,
        default="kinfin_analysis/",
        help="Output directory (default: %(default)s)",
    )
    subparser_parameters.add_argument(
        "-F",
        choices=definitions.ARGS_SUPPORTED_OUTPUT_FORMATS,
        metavar="FMT",
        default="parquet",
        help="Output table format (default: %(default)s)",
    )
    subparser_parameters.add_argument(
        "-p",
        metavar="PROCESSES",
        required=False,
        type=int_positive,
        default=1,
        help="Number of processes to use for the analysis (default: %(default)s)",
    )
    subparser_parameters.add_argument(
        "-v",
        action="store_true",
        help="Verbose log",
    )
    subparser_parameters.add_argument(
        "-X",
        action="store_true",
        help="Ignore 'sample_id' column for comparisons",
    )
    subparser_parameters.add_argument(
        "-L",
        action="store_true",
        help="No plots",
    )
    subparser_parameters.add_argument(
        "-l",
        metavar="PLOT_FMT",
        choices=definitions.ARGS_SUPPORTED_PLOT_FORMATS,
        default=definitions.PLOT_FORMAT,
        help="Format for plots (default: %(default)s)",
    )
    subparser_parameters.add_argument(
        "-N",
        action="store_true",
        help="No cleanup of temporary directory",
    )


def add_analysis_parser(subparsers):
    subparser = subparsers.add_parser(
        "analysis",
        help="start KinFin analysis",
    )
    subparser._optionals.title = "[optional]"
    subparser_required = subparser.add_argument_group("[essential]")
    subparser_parameters = subparser.add_argument_group("[parameters]")
    subparser_required.add_argument(
        "-g",
        metavar="ORTHOGROUPS_FN",
        required=True,
        type=existing_file,
        help="Orthogroups.txt, as produced by OrthoFinder",
    )
    subparser_required.add_argument(
        "-c",
        metavar="CONFIG_FN",
        required=True,
        type=existing_file,
        help="Config file in CSV or JSON",
    )
    subparser_parameters.add_argument(
        "-P",
        action="store_true",
        help="parse sample IDs from prefix of names in orthogroups",
    )
    subparser_parameters.add_argument(
        "-f",
        metavar="FASTA_DIR",
        required=False,
        type=existing_dir,
        help="Directory containing all FASTA files of samples to be parsed from ORTHOGROUPS_FN. Caution: Prefix of files will be used as sample IDs",
    )
    subparser_parameters.add_argument(
        "-s",
        metavar="SEQUENCEIDS_FN",
        required=False,
        type=existing_file,
        help="SequenceIDs.txt used in OrthoFinder",
    )
    subparser_parameters.add_argument(
        "-S",
        metavar="SPECIESIDS_FN",
        required=False,
        type=existing_file,
        help="SpeciesIDs.txt used in OrthoFinder",
    )
    subparser_parameters.add_argument(
        "-i",
        metavar="INTERPRO_FN",
        required=False,
        type=existing_file,
        help="Interproscan output in a single file in TSV format",
    )
    subparser_parameters.add_argument(
        "-I",
        metavar="INTERPRO_DIR",
        required=False,
        type=existing_dir,
        help="Directory of Interproscan output in TSV format. Needs Sample-ID as filename prefix.",
    )
    subparser_parameters.add_argument(
        "-a",
        metavar="TABLE_FN",
        required=False,
        type=existing_file,
        help=f"Table mapping numerical values to members in ORTHOGROUPS_FN, in {'/'.join(definitions.ARGS_SUPPORTED_OUTPUT_FORMATS)} format",
    )
    subparser_parameters.add_argument(
        "-t",
        metavar="TREE_FN",
        required=False,
        type=existing_file,
        help="Tree file in Newick format. Sample IDs must be the same as 'sample_ids' in CONFIG_FN",
    )
    subparser_parameters.add_argument(
        "-o",
        metavar="OUTGROUP",
        required=False,
        type=str,
        nargs="*",
        default=[],
        help="Sample-ID(s) (space-separated) that will be used as outgroup when parsing TREE_FN. Must be monophyletic.",
    )
    subparser_parameters.add_argument(
        "-r",
        metavar="TAXRANKS",
        required=False,
        choices=definitions.ARGS_TAXONOMY_RANKS_SUPPORTED,
        nargs="*",
        default=definitions.ARGS_TAXONOMY_RANKS_DEFAULT,
        help=f"Taxonomic ranks to be inferred from NCBI 'taxids' column in config file (or None to ignore) (default: {' '.join(definitions.ARGS_TAXONOMY_RANKS_DEFAULT)})",
    )
    subparser_parameters.add_argument(
        "-n",
        metavar="COG_COUNT_T",
        required=False,
        type=int_positive,
        default=1,
        help="Target count of COGs (Copy-OrthoGroups) (default: %(default)s)",
    )
    subparser_parameters.add_argument(
        "-x",
        metavar="COG_COUNT_P",
        required=False,
        type=float_proportion,
        default=0.75,
        help="Minimum proportion of Sample IDs at COG_COUNT_TARGET (default: %(default)s)",
    )
    subparser_parameters.add_argument(
        "-m",
        metavar="COG_COUNT_MIN",
        required=False,
        type=int_zero_or_positive,
        default=0,
        help="Minimum count per Sample IDs outside (!) of COG_COUNT_FRACTION (default: %(default)s)",
    )
    subparser_parameters.add_argument(
        "-M",
        metavar="COG_COUNT_MAX",
        required=False,
        type=int_positive,
        default=1,
        help="Maximum count per Sample IDs outside (!) of COG_COUNT_FRACTION (default: %(default)s)",
    )
    subparser_parameters.add_argument(
        "-d",
        metavar="OUTDIR",
        type=str,
        default="kinfin_analysis/",
        help="Output directory (default: %(default)s)",
    )
    subparser_parameters.add_argument(
        "-F",
        choices=definitions.ARGS_SUPPORTED_OUTPUT_FORMATS,
        metavar="FMT",
        default="parquet",
        help="Output table format (default: %(default)s)",
    )
    subparser_parameters.add_argument(
        "-p",
        metavar="PROCESSES",
        required=False,
        type=int_positive,
        default=1,
        help="Number of processes to use for the analysis (default: %(default)s)",
    )
    subparser_parameters.add_argument(
        "-v",
        action="store_true",
        help="Verbose log",
    )
    subparser_parameters.add_argument(
        "-X",
        action="store_true",
        help="Ignore 'sample_id' column for comparisons",
    )
    subparser_parameters.add_argument(
        "-L",
        action="store_true",
        help="No plots",
    )
    subparser_parameters.add_argument(
        "-l",
        metavar="PLOT_FMT",
        choices=definitions.ARGS_SUPPORTED_PLOT_FORMATS,
        default=definitions.PLOT_FORMAT,
        help="Format for plots (default: %(default)s)",
    )
    subparser_parameters.add_argument(
        "-N",
        action="store_true",
        help="No cleanup of temporary directory",
    )


def add_api_parser(subparsers):
    subparser = subparsers.add_parser(
        "serve",
        help="start KinFin API server",
    )
    subparser.add_argument(
        "-p",
        "--port",
        type=int_positive,
        default=8000,
        help="Port number for the server (default: %(default)s)",
    )


def add_plot_parser(subparsers):
    subparser = subparsers.add_parser(
        "plot",
        help="make plots based on output tables ",
    )
    subparser.add_argument(
        "-f",
        metavar="FILE",
        type=existing_files,
        nargs="*",
        help="files to plot",
    )
    subparser.add_argument(
        "-p",
        metavar="PREFIX",
        required=True,
        type=str,
        default="plot",
        help="prefix for output file.",
    )
    subparser.add_argument(
        "-d",
        metavar="DIR",
        required=False,
        type=existing_dir,
        help="Directory in which to look for plottable files",
    )
    subparser.add_argument(
        "-X",
        action="store_true",
        help="Do not normalize X-axis in line plots",
    )
    subparser.add_argument(
        "-Y",
        action="store_true",
        help="Do not normalize Y-axis in line plots",
    )
    subparser.add_argument(
        "-M",
        type=int_positive,
        default=9,
        help="Maximum number of taxon groups per plot (default: %(default)s)",
    )


def add_preprocess_parser(subparsers):
    subparser = subparsers.add_parser(
        "preprocess",
        help="preprocess files before kinfin analysis",
    )
    subparser.add_argument(
        "-g",
        metavar="ORTHOGROUPS_FN",
        required=True,
        type=existing_file,
        help="Orthogroups.txt, as produced by OrthoFinder",
    )
    subparser.add_argument(
        "-e",
        metavar="FILE",
        type=existing_file,
        help="Orthogroups to exclude (one per line). All others are included. Incompatible with (-i)",
    )
    subparser.add_argument(
        "-i",
        metavar="FILE",
        type=existing_file,
        help="Orthogroups to include (one per line). All others are excluded. Incompatible with (-e)",
    )
    subparser.add_argument(
        "-E",
        metavar="FILE",
        type=existing_file,
        help="Elements to exclude (one per line). All others are included. Incompatible with (-I)",
    )
    subparser.add_argument(
        "-I",
        metavar="FILE",
        type=existing_file,
        help="Elements to include (one per line). All others are excluded. Incompatible with (-E)",
    )


def add_convert_parser(subparsers):
    subparser = subparsers.add_parser(
        "convert",
        help="convert KinFin output table into other formats",
    )
    subparser.add_argument(
        "-t",
        metavar="TABLE_FN",
        required=True,
        type=existing_file,
        help="Table to convert",
    )
    subparser.add_argument(
        "-F",
        metavar="FMT",
        choices=definitions.ARGS_SUPPORTED_OUTPUT_FORMATS,
        default="tsv",
        help="Output format (default: %(default)s)",
    )
    subparser.add_argument(
        "-i",
        action="store_true",
        help="Include index",
    )


def add_view_parser(subparsers):
    subparser = subparsers.add_parser(
        "view",
        help="write KinFin output table to stdout",
    )
    subparser.add_argument(
        "-t",
        metavar="TABLE_FN",
        required=True,
        type=existing_file,
        help="Table to convert",
    )
    subparser.add_argument(
        "-i",
        action="store_true",
        help="include index column",
    )
    subparser.add_argument(
        "-F",
        metavar="FMT",
        choices=definitions.ARGS_SUPPORTED_OUTPUT_FORMATS,
        default="tsv",
        help="Output format (default: %(default)s)",
    )


def add_head_parser(subparsers):
    subparser = subparsers.add_parser(
        "head",
        help="display first rows of a KinFin output table",
    )
    subparser.add_argument(
        "-t",
        metavar="TABLE_FN",
        required=True,
        type=existing_file,
        help="Table to display",
    )
    subparser.add_argument(
        "-n",
        metavar="COUNT",
        required=False,
        default=10,
        type=int_positive,
        help="print COUNT lines of each of the specified file (default: %(default)s)",
    )


def add_tail_parser(subparsers):
    subparser = subparsers.add_parser(
        "tail",
        help="display last rows of a KinFin output table",
    )
    subparser.add_argument(
        "-t",
        metavar="TABLE_FN",
        required=True,
        type=existing_file,
        help="Table to display",
    )
    subparser.add_argument(
        "-n",
        metavar="COUNT",
        required=False,
        default=10,
        type=int_positive,
        help="print COUNT lines of each of the specified file (default: %(default)s)",
    )


def add_taxid_parser(subparsers):
    subparser = subparsers.add_parser(
        "taxid",
        help="adds taxid to config file, based on sample_id field. Returns 'None' if string could not be found in NCBI Taxonomy",
    )
    subparser.add_argument(
        "-c",
        metavar="CONFIG_FN",
        required=True,
        type=existing_file,
        help="Config file in CSV or JSON",
    )
    subparser.add_argument(
        "-u",
        action="store_true",
        help="update NCBI TaxDump",
    )
    subparser.add_argument(
        "-F",
        metavar="FMT",
        choices=definitions.ARGS_SUPPORTED_OUTPUT_FORMATS_CONFIG,
        default="csv",
        help="Output format (default: %(default)s)",
    )
    subparser.add_argument(
        "-d",
        metavar="OUTDIR",
        type=str,
        default="",
        help="Output directory (default: %(default)s)",
    )


def get_argparse():
    class CustomFormatter(
        argparse.RawDescriptionHelpFormatter,
        argparse.ArgumentDefaultsHelpFormatter,
    ):
        pass

    EPILOG = """"""

    parser = argparse.ArgumentParser(
        prog="kinfin",
        description="KinFin analysis tool",
        formatter_class=CustomFormatter,
        epilog=EPILOG,
    )
    subparsers = parser.add_subparsers(
        title="[commands]",
        metavar="",
        required=True,
        dest="command",
    )
    add_analysis_parser(subparsers)
    add_reps_parser(subparsers)
    add_api_parser(subparsers)
    add_plot_parser(subparsers)
    add_view_parser(subparsers)
    add_head_parser(subparsers)
    add_tail_parser(subparsers)
    add_convert_parser(subparsers)
    add_taxid_parser(subparsers)
    add_preprocess_parser(subparsers)
    args = parser.parse_args()
    if args.command == "analysis":
        subparser = subparsers.choices[args.command]
        if args.m >= args.M:
            subparser.error(
                f"value for '-m' must be smaller than '-M' (not {args.m} > {args.M}) !",
            )
        if sum([bool(args.s), bool(args.S)]) == 1:
            subparser.error("must specify both -s and -S")
        if not sum(bool(_) for _ in [args.f, args.P, bool(args.s and args.S)]) == 1:
            subparser.error(
                "must specify options (-f) or (-P) or (-s/-S) depending on your data"
            )
    if args.command == "reps":
        subparser = subparsers.choices[args.command]
        if (args.E and args.e) or not (args.E or args.e):
            subparser.error("must specify either (-e) or (-E)")
        if args.m >= args.M:
            subparser.error(
                f"value for '-m' must be smaller than '-M' (not {args.m} >= {args.M}) !",
            )
    if args.command == "preprocess":
        subparser = subparsers.choices[args.command]
        if args.i and args.e:
            subparser.error(
                "can't specify both '-i' and '-e'!",
            )
        if args.I and args.E:
            subparser.error(
                "can't specify both '-I' and '-E'!",
            )
    return parser.parse_args()
