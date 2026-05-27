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


def add_analysis_parser(subparsers):
    analysis_parser = subparsers.add_parser(
        "analysis",
        help="start KinFin analysis",
    )
    analysis_parser._optionals.title = "[optional]"
    analysis_parser_required = analysis_parser.add_argument_group("[essential]")
    analysis_parser_parameters = analysis_parser.add_argument_group("[parameters]")
    analysis_parser_required.add_argument(
        "-g",
        metavar="ORTHOGROUPS_FN",
        required=True,
        type=existing_file,
        help="Orthogroups.txt, as produced by OrthoFinder",
    )
    analysis_parser_required.add_argument(
        "-c",
        metavar="CONFIG_FN",
        required=True,
        type=existing_file,
        help="Config file in CSV or JSON",
    )
    analysis_parser_parameters.add_argument(
        "-P",
        action="store_true",
        help="parse sample IDs from prefix of names in orthogroups",
    )
    analysis_parser_parameters.add_argument(
        "-f",
        metavar="FASTA_DIR",
        required=False,
        type=existing_dir,
        help="Directory containing all FASTA files of samples to be parsed from ORTHOGROUPS_FN. Caution: Prefix of files will be used as sample IDs",
    )
    analysis_parser_parameters.add_argument(
        "-s",
        metavar="SEQUENCEIDS_FN",
        required=False,
        type=existing_file,
        help="SequenceIDs.txt used in OrthoFinder",
    )
    analysis_parser_parameters.add_argument(
        "-S",
        metavar="SPECIESIDS_FN",
        required=False,
        type=existing_file,
        help="SpeciesIDs.txt used in OrthoFinder",
    )
    analysis_parser_parameters.add_argument(
        "-i",
        metavar="INTERPRO_FN",
        required=False,
        type=existing_file,
        help="Interproscan output in a single file in TSV format",
    )
    analysis_parser_parameters.add_argument(
        "-I",
        metavar="INTERPRO_DIR",
        required=False,
        type=existing_dir,
        help="Directory of Interproscan output in TSV format. Needs Sample-ID as filename prefix.",
    )
    analysis_parser_parameters.add_argument(
        "-a",
        metavar="TABLE_FN",
        required=False,
        type=existing_file,
        help=f"Table mapping numerical values to members in ORTHOGROUPS_FN, in {'/'.join(definitions.ARGS_SUPPORTED_OUTPUT_FORMATS)} format",
    )
    analysis_parser_parameters.add_argument(
        "-t",
        metavar="TREE_FN",
        required=False,
        type=existing_file,
        help="Tree file in Newick format. Sample IDs must be the same as 'sample_ids' in CONFIG_FN",
    )
    analysis_parser_parameters.add_argument(
        "-o",
        metavar="OUTGROUP",
        required=False,
        type=str,
        nargs="*",
        default=[],
        help="Sample-ID(s) (space-separated) that will be used as outgroup when parsing TREE_FN. Must be monophyletic.",
    )
    analysis_parser_parameters.add_argument(
        "-r",
        metavar="TAXRANKS",
        required=False,
        choices=definitions.ARGS_TAXONOMY_RANKS_SUPPORTED,
        nargs="*",
        default=definitions.ARGS_TAXONOMY_RANKS_DEFAULT,
        help=f"Taxonomic ranks to be inferred from NCBI 'taxids' column in config file (or None to ignore) (default: {' '.join(definitions.ARGS_TAXONOMY_RANKS_DEFAULT)})",
    )
    analysis_parser_parameters.add_argument(
        "-n",
        metavar="COG_COUNT_T",
        required=False,
        type=int_positive,
        default=1,
        help="Target count of COGs (Copy-OrthoGroups) (default: %(default)s)",
    )
    analysis_parser_parameters.add_argument(
        "-x",
        metavar="COG_COUNT_P",
        required=False,
        type=float_proportion,
        default=0.75,
        help="Minimum proportion of Sample IDs at COG_COUNT_TARGET (default: %(default)s)",
    )
    analysis_parser_parameters.add_argument(
        "-m",
        metavar="COG_COUNT_MIN",
        required=False,
        type=int_zero_or_positive,
        default=0,
        help="Minimum count per Sample IDs outside (!) of COG_COUNT_FRACTION (default: %(default)s)",
    )
    analysis_parser_parameters.add_argument(
        "-M",
        metavar="COG_COUNT_MAX",
        required=False,
        type=int_positive,
        default=1,
        help="Maximum count per Sample IDs outside (!) of COG_COUNT_FRACTION (default: %(default)s)",
    )
    analysis_parser_parameters.add_argument(
        "-d",
        metavar="OUTDIR",
        type=str,
        default="kinfin_analysis/",
        help="Output directory (default: %(default)s)",
    )
    analysis_parser_parameters.add_argument(
        "-F",
        choices=definitions.ARGS_SUPPORTED_OUTPUT_FORMATS,
        metavar="FMT",
        default="feather",
        help="Output table format (default: %(default)s)",
    )
    analysis_parser_parameters.add_argument(
        "-p",
        metavar="PROCESSES",
        required=False,
        type=int_positive,
        default=1,
        help="Number of processes to use for the analysis (default: %(default)s)",
    )
    analysis_parser_parameters.add_argument(
        "-v",
        action="store_true",
        help="Verbose log",
    )
    analysis_parser_parameters.add_argument(
        "-X",
        action="store_true",
        help="Ignore 'sample_id' column for comparisons",
    )
    analysis_parser_parameters.add_argument(
        "-N",
        action="store_true",
        help="No cleanup of temporary directory",
    )


def add_api_parser(subparsers):
    api_parser = subparsers.add_parser(
        "serve",
        help="start KinFin API server",
    )
    api_parser.add_argument(
        "-p",
        "--port",
        type=int_positive,
        default=8000,
        help="Port number for the server (default: %(default)s)",
    )


def add_plot_parser(subparsers):
    plot_parser = subparsers.add_parser(
        "plot",
        help="make plots based on output tables ",
    )
    plot_parser.add_argument(
        "-f",
        metavar="FILE",
        type=existing_files,
        nargs="*",
        help="files to plot",
    )
    plot_parser.add_argument(
        "-p",
        metavar="PREFIX",
        required=True,
        type=str,
        default="plot",
        help="prefix for output file.",
    )
    plot_parser.add_argument(
        "-d",
        metavar="DIR",
        required=False,
        type=existing_dir,
        help="Directory in which to look for plottable files",
    )
    plot_parser.add_argument(
        "-X",
        action="store_true",
        help="Do not normalize X-axis in line plots",
    )
    plot_parser.add_argument(
        "-Y",
        action="store_true",
        help="Do not normalize Y-axis in line plots",
    )
    plot_parser.add_argument(
        "-M",
        type=int_positive,
        default=9,
        help="Maximum number of taxon groups per plot (default: %(default)s)",
    )


def add_convert_parser(subparsers):
    convert_parser = subparsers.add_parser(
        "convert",
        help="convert KinFin output table into other formats",
    )
    convert_parser.add_argument(
        "-t",
        metavar="TABLE_FN",
        required=True,
        type=existing_file,
        help="Table to convert",
    )
    convert_parser.add_argument(
        "-F",
        metavar="FMT",
        required=True,
        choices=definitions.ARGS_SUPPORTED_OUTPUT_FORMATS,
        default="tsv",
        help="Output format (default: %(default)s)",
    )
    convert_parser.add_argument(
        "-i",
        action="store_true",
        help="Include index",
    )


def add_view_parser(subparsers):
    view_parser = subparsers.add_parser(
        "view",
        help="write KinFin output table to stdout",
    )
    view_parser.add_argument(
        "-t",
        metavar="TABLE_FN",
        required=True,
        type=existing_file,
        help="Table to convert",
    )
    view_parser.add_argument(
        "-i",
        action="store_true",
        help="include index column",
    )
    view_parser.add_argument(
        "-F",
        metavar="FMT",
        choices=definitions.ARGS_SUPPORTED_OUTPUT_FORMATS,
        default="tsv",
        help="Output format (default: %(default)s)",
    )


def add_head_parser(subparsers):
    head_parser = subparsers.add_parser(
        "head",
        help="display first rows of a KinFin output table",
    )
    head_parser.add_argument(
        "-t",
        metavar="TABLE_FN",
        required=True,
        type=existing_file,
        help="Table to display",
    )
    head_parser.add_argument(
        "-n",
        metavar="COUNT",
        required=False,
        default=10,
        type=int_positive,
        help="print COUNT lines of each of the specified file (default: %(default)s)",
    )


def add_tail_parser(subparsers):
    tail_parser = subparsers.add_parser(
        "tail",
        help="display last rows of a KinFin output table",
    )
    tail_parser.add_argument(
        "-t",
        metavar="TABLE_FN",
        required=True,
        type=existing_file,
        help="Table to display",
    )
    tail_parser.add_argument(
        "-n",
        metavar="COUNT",
        required=False,
        default=10,
        type=int_positive,
        help="print COUNT lines of each of the specified file (default: %(default)s)",
    )


def add_taxid_parser(subparsers):
    taxid_parser = subparsers.add_parser(
        "taxid",
        help="adds taxid to config file, based on sample_id field. Returns 'None' if string could not be found in NCBI Taxonomy",
    )
    taxid_parser.add_argument(
        "-c",
        metavar="CONFIG_FN",
        required=True,
        type=existing_file,
        help="Config file in CSV or JSON",
    )
    taxid_parser.add_argument(
        "-u",
        action="store_true",
        help="update NCBI TaxDump",
    )
    taxid_parser.add_argument(
        "-F",
        metavar="FMT",
        choices=definitions.ARGS_SUPPORTED_OUTPUT_FORMATS_CONFIG,
        default="csv",
        help="Output format (default: %(default)s)",
    )
    taxid_parser.add_argument(
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
    add_api_parser(subparsers)
    add_plot_parser(subparsers)
    add_view_parser(subparsers)
    add_head_parser(subparsers)
    add_tail_parser(subparsers)
    add_convert_parser(subparsers)
    add_taxid_parser(subparsers)
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
    return parser.parse_args()
