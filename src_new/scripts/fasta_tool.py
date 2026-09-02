#!/usr/bin/env python3

import argparse
import collections
import contextlib
import datetime
import glob
import hashlib
import logging
import multiprocessing
import pathlib
import re
import sys
import time

import tqdm

# LOGGING (only log to stderr, move somewhere)

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] [%(levelname)s] %(filename)s - %(message)s",
    stream=sys.stderr,
)

logger = logging.getLogger(__name__)


EPILOG = """hints:
[+] Counts sequences in FASTA file given parameters
[+] Writes stats to STDERR, a CSV ('-J'), and JSON ('-j') file
[+] if '-w' is specified, writes single-line FASTA sequences STDOUT
"""

AMINOACIDS = [
    "A",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "I",
    "K",
    "L",
    "M",
    "N",
    "P",
    "Q",
    "R",
    "S",
    "T",
    "V",
    "W",
    "Y",
    "*",
    "X",
    "O",
    "U",
]

HEADER_JOIN_DELIM = "."
MIN_LEN = 0
MAX_LEN = 1e12
MAX_STOP = 1e5


def str_or_none(value):
    msg = f"must be a string or None (not '{value}')"
    try:
        if value is None or value == "None":
            return None
        else:
            return str(value)
    except ValueError:
        raise argparse.ArgumentTypeError(msg)
    raise argparse.ArgumentTypeError(msg)


def int_zero_or_positive_or_none(value):
    msg = f"must be zero or positive integer or None (not '{value}')"
    try:
        if value is None:
            return value
        elif value == "None":
            return None
        else:
            number = int(value)
            if number >= 0:
                return number
    except ValueError:
        raise argparse.ArgumentTypeError(msg)
    raise argparse.ArgumentTypeError(msg)


def existing_dir(directory):
    path = pathlib.Path(directory)
    if not pathlib.Path.is_dir(path):
        raise argparse.ArgumentTypeError(f"directory '{directory}' does not exist")
    return path


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
        "-f",
        metavar="FASTADIR",
        required=True,
        type=existing_dir,
        help="FASTA directory",
    )
    parser_headers = parser.add_argument_group("[Sequence headers]")
    parser_headers.add_argument(
        "-d",
        metavar="HEADER_DELIM",
        required=False,
        type=str,
        default=" ",
        help="Delimiter on which to split FASTA header string (default: '%(default)s')",
    )
    parser_headers.add_argument(
        "-D",
        metavar="HEADER_FIELDS",
        required=False,
        nargs="*",
        type=int,
        default=[0],
        help="Field(s) to keep after splitting FASTA header (default: '%(default)s')",
    )
    parser_headers.add_argument(
        "-b",
        metavar="FN_DELIM",
        required=False,
        type=str_or_none,
        default=None,
        help="Delimiter on which to split FASTA FILENAME string. 'None' to ignore. (default: '%(default)s')",
    )
    parser_headers.add_argument(
        "-B",
        metavar="FN_FIELD",
        required=False,
        nargs="*",
        type=int,
        default=[0],
        help="Field(s) from FASTA filename (after splitting with 'b') to prepend to FASTA header (default: '%(default)s')",
    )
    parser_filters = parser.add_argument_group("[Sequence filters]")
    parser_filters.add_argument(
        "-m",
        metavar="MINLEN",
        required=False,
        type=int_zero_or_positive_or_none,
        default=MIN_LEN,
        help="Only include sequences which have at least this length (default: '%(default)s')",
    )
    parser_filters.add_argument(
        "-M",
        metavar="MAXLEN",
        required=False,
        type=int_zero_or_positive_or_none,
        default=MAX_LEN,
        help="Only include sequences which do not exceed this length (default: '%(default)s')",
    )
    parser_filters.add_argument(
        "-s",
        metavar="MAXSTOPS",
        required=False,
        type=int,
        default=MAX_STOP,
        help="Only include sequences which do not exceed this number of non-terminal stops (default: '%(default)s')",
    )
    parser_output = parser.add_argument_group("[Output]")
    parser_output.add_argument(
        "-l",
        action="store_true",
        help="Write TSV of sequence IDs and lengths",
    )
    parser_options = parser.add_argument_group("[Options]")
    parser_options.add_argument(
        "-p",
        metavar="PROCESSES",
        required=False,
        type=int,
        default=1,
        help="Processes for FASTA parsing (default: '%(default)s')",
    )
    return parser.parse_args()


def sanitize_name(header, prefix=""):
    if prefix == "":
        return re.sub(r"[\W_]+", "_", header)
    return ".".join([prefix, re.sub(r"[\W_]+", "_", header)])


def yield_fasta(task):
    with open(task.fn) as fh:
        header, seqs = "", []
        for line in fh:
            if line[0] == ">":
                if header:
                    yield header, "".join(seqs)
                header, seqs = line[1:-1], []
            else:
                seqs.append(line[:-1])
        yield header, "".join(seqs)


def get_header(
    header,
    header_delim,
    header_fields,
    prefix,
):
    # print(f"{header=}")
    # print(f"{header_delim=}")
    # print(f"{header_fields=}")
    # print(f"{prefix=}")
    if header_delim:
        header_new = HEADER_JOIN_DELIM.join(
            [header.split(header_delim)[field] for field in header_fields]
        )
    if prefix:
        header_new = f"{prefix}{HEADER_JOIN_DELIM}{header_new}"
    # print(f"{header_new=}")
    return header_new


@contextlib.contextmanager
def poolcontext(*args, **kwargs):
    pool = multiprocessing.Pool(*args, **kwargs)
    yield pool
    pool.terminate()


Task = collections.namedtuple(
    "Task",
    [
        "fn",
        "minlen",
        "maxlen",
        "maxstops",
        "header_delim",
        "header_fields",
        "fn_prefix",
        "write_length",
    ],
)


def get_tasks(
    args,
    extensions=(".fa", ".fas", ".fasta"),
):
    tasks = []
    for extension in extensions:
        for fn_str in glob.glob(f"{args.f}/*{extension}"):
            fn = pathlib.Path(fn_str)
            tasks.append(
                Task(
                    fn=fn,
                    minlen=args.m,
                    maxlen=args.M,
                    maxstops=args.s,
                    header_delim=args.d,
                    header_fields=args.D,
                    fn_prefix=(
                        ""
                        if args.b is None
                        else args.b.join(
                            [fn.stem.split(args.b)[field] for field in args.B],
                        )
                    ),
                    write_length=args.l,
                )
            )
    return tasks


def format_elapsed(seconds):
    td = datetime.timedelta(seconds=seconds)
    return f"elapsed: {td}"


def do_tasks(
    tasks,
    desc="",
    processes=1,
    collect_results=False,
):
    _TOTAL = len(tasks)
    _DESC = desc
    _NCOLS = 0
    results = [] if collect_results else None
    if processes > 1:
        with (
            tqdm.tqdm(total=_TOTAL, desc=_DESC, ncols=_NCOLS) as t,
            poolcontext(processes=processes) as pool,
        ):
            for _ in pool.imap_unordered(process_fasta, tasks):
                if collect_results:
                    results.append(_)
                t.update()
    else:
        for task in tqdm.tqdm(tasks, total=_TOTAL, desc=_DESC, ncols=_NCOLS):
            _ = process_fasta(task)
            if collect_results:
                results.append(_)
    return results


def parse_sequence_ids(sequence_ids_fn):
    with open(sequence_ids_fn) as fh:
        return [sequence_id[:-1] for sequence_id in fh]


def process_tasks(
    tasks,
    processes=1,
):

    t_0 = time.monotonic()
    logger.info(f"parsing {len(tasks)} FASTA files using {processes} process(es)")
    results = do_tasks(
        tasks=tasks,
        desc="[PROCESSING]",
        processes=processes,
        collect_results=True,
    )
    logger.info(f"finished processing FASTAs: {format_elapsed(time.monotonic() - t_0)}")
    return results


def process_fasta(task):
    result = {
        "fn_out": None,
        "headers_old": [],
        "headers_new": [],
        "sequences": [],
        "lengths": [],
        "aminoacid_counter": collections.Counter(),
        "md5_before": None,
        "md5_after": None,
    }
    for header, sequence in yield_fasta(task):
        result["headers_old"].append(header)
        length = len(sequence)
        if (
            task.minlen <= length <= task.maxlen
            and sequence.rstrip("*").count("*") <= task.maxstops
        ):
            result["aminoacid_counter"] += collections.Counter(sequence)
            header_new = get_header(
                header,
                header_delim=task.header_delim,
                header_fields=task.header_fields,
                prefix=task.fn_prefix,
            )
            # print(header_new)
        else:
            header_new, sequence = None, None
            length = 0
        result["headers_new"].append(header_new)
        result["sequences"].append(sequence)
        result["lengths"].append(length)
    result["md5_before"] = get_md5sum(task.fn)
    result = write_result(task, result)
    return result


def write_data(fn, data=None):
    with open(fn, "w") as fh:
        fh.write(data)


def write_result(task, result):
    result["fn_out"] = task.fn_prefix or task.fn.stem
    fn_fasta = f"{result['fn_out']}.faa"
    if len(result["headers_new"]) != len(set(result["headers_new"])):
        logger.error(
            f"This would result in non-unique headers based on file '{task.fn}' !"
        )
        sys.exit(1)
    write_data(
        fn_fasta,
        data="\n".join(
            [
                f">{header}\n{seq}"
                for header, seq in zip(result["headers_new"], result["sequences"])
            ]
        ),
    )
    result["md5_after"] = get_md5sum(fn_fasta)
    fn_lengths = f"{result['fn_out']}.lengths.txt"
    write_data(
        fn_lengths,
        data="\n".join(
            [
                f"{header}\t{length}"
                for header, length in zip(result["headers_new"], result["lengths"])
            ]
        ),
    )
    fn_mapping = f"{result['fn_out']}.mapping.txt"
    write_data(
        fn_mapping,
        data="\n".join(
            [
                f"{header_old}\t{header_new}"
                for header_old, header_new in zip(
                    result["headers_new"], result["headers_old"]
                )
            ]
        ),
    )
    result = {
        k: v
        for k, v in result.items()
        if k
        not in [
            "headers_old",
            "headers_new",
            "sequences",
            "lengths",
        ]
    }
    return result


def write_results(results):
    md5_lines = ["fn_out\tmd5_before\tmd5_after"]
    aa_header = "\t".join(AMINOACIDS)
    aa_lines = [f"fn_out\ttotal\t{aa_header}"]
    for result in sorted(results, key=lambda x: x["fn_out"]):
        md5_lines.append(
            f"{result['fn_out']}\t{result['md5_before']}\t{result['md5_after']}"
        )
        aminoacid_string = "\t".join(
            [str(result["aminoacid_counter"][aa]) for aa in AMINOACIDS]
        )
        aa_lines.append(
            f"{result['fn_out']}\t{result['aminoacid_counter'].total()}\t{aminoacid_string}"
        )
    write_data("checksums.tsv", data="\n".join(md5_lines))
    write_data("aminoacids.tsv", data="\n".join(aa_lines))


def get_md5sum(fn):
    with open(fn, "rb") as fh:
        md5sum = hashlib.file_digest(fh, "md5").hexdigest()
    return md5sum


def main():
    args = get_argparse()
    tasks = get_tasks(args)
    results = process_tasks(tasks, processes=args.p)
    write_results(results)


if __name__ == "__main__":
    main()
