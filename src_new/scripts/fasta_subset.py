#!/usr/bin/env python3
import argparse
import collections
import contextlib
import datetime
import glob
import logging
import multiprocessing
import os
import pathlib
import time

import tqdm

logger = logging.getLogger(__name__)


def existing_dir(directory):
    if not os.path.isdir(directory):
        raise argparse.ArgumentTypeError(f"directory '{directory}' does not exist")
    return directory


def existing_file(infile):
    if not os.path.isfile(infile):
        raise argparse.ArgumentTypeError(f"file '{infile}' does not exist")
    return infile


@contextlib.contextmanager
def poolcontext(*args, **kwargs):
    pool = multiprocessing.Pool(*args, **kwargs)
    yield pool
    pool.terminate()


ParseTask = collections.namedtuple(
    "ParseTask",
    [
        "func",
        "sequence_ids",
        "fn",
    ],
)


def get_parse_tasks(
    directory=None,
    func=None,
    sequence_ids=[],
    extensions=[".fa", ".fas", ".fasta"],
):
    sequence_ids = set(sequence_ids)
    tasks = []
    for extension in extensions:
        for fn in glob.glob(f"{directory}/*{extension}"):
            tasks.append(
                ParseTask(
                    func=func,
                    sequence_ids=set(sequence_ids),
                    fn=fn,
                )
            )
    return tasks


def format_elapsed(seconds):
    td = datetime.timedelta(seconds=seconds)
    return f"elapsed: {td}"


def do_task(task):
    return task.func(task)


def do_tasks(
    tasks=[],
    desc="",
    processes=1,
    collect_results=False,
):
    _TOTAL = len(tasks)
    _DESC = desc
    _NCOLS = 0
    results = [] if collect_results else None
    if processes > 1:
        with tqdm.tqdm(total=_TOTAL, desc=_DESC, ncols=_NCOLS) as t:
            with poolcontext(processes=processes) as pool:
                for _ in pool.imap_unordered(do_task, tasks):
                    if collect_results:
                        results.append(_)
                    t.update()
    else:
        for task in tqdm.tqdm(tasks, total=_TOTAL, desc=_DESC, ncols=_NCOLS):
            _ = do_task(task)
            if collect_results:
                results.append(_)
    return results


def parse_sequence_ids(sequence_ids_fn):
    with open(sequence_ids_fn) as fh:
        return [sequence_id[:-1] for sequence_id in fh.readlines()]


def process_elements(
    directory=None,
    sequence_ids_fn=None,
    processes=1,
):

    t_0 = time.monotonic()
    sequence_ids = parse_sequence_ids(sequence_ids_fn)
    tasks = get_parse_tasks(
        directory=directory,
        func=do_parse_fasta,
        sequence_ids=sequence_ids,
    )
    logger.info(f"parsing {len(tasks)} FASTA files using {processes} process(es)")
    results = do_tasks(
        tasks=tasks,
        desc="[PARSING]",
        processes=processes,
        collect_results=True,
    )
    for result in results:
        for k, v in result.items():
            if v:
                with open(f"{k}.dupes.faa", "w") as fh:
                    fh.write("".join(v))
    logger.info(f"{format_elapsed(time.monotonic() - t_0)}")
    return True


def do_parse_fasta(task):
    # fn, sample_id
    sample_id = pathlib.Path(task.fn).stem.split(".")[0]
    try:
        data = collections.defaultdict(list)
        for header, sequence in iter_header_seq(task.fn):
            if header in task.sequence_ids:
                data[sample_id].append(f">{header}\n{sequence}\n")
        return data
    except Exception as exc:
        logger.error(f"problem reading {task.fn} - {exc}")
    return {sample_id: []}


def iter_header_seq(fn):
    with open(fn) as fh:
        header, seqs = "", []
        for line in fh:
            if line[0] == ">":
                if header:
                    header = (
                        header.replace(":", "_")
                        .replace(",", "_")
                        .replace("(", "_")
                        .replace(")", "_")
                    )  # orthofinder replaces chars
                    yield header, "".join(seqs)
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
        yield header, "".join(seqs)


def get_argparse():
    class CustomFormatter(
        argparse.RawDescriptionHelpFormatter,
        argparse.ArgumentDefaultsHelpFormatter,
    ):
        pass

    parser = argparse.ArgumentParser(
        prog="fasta_subset",
        description="subeset fasta based on list of sequence IDs",
        formatter_class=CustomFormatter,
        epilog="""""",
    )
    parser.add_argument(
        "-d",
        metavar="FASTA_DIR",
        required=True,
        type=existing_dir,
        help="Directory with FASTA files",
    )
    parser.add_argument(
        "-i",
        metavar="SEQIDS",
        required=True,
        type=existing_file,
        help="List of sequence IDs to subset",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = get_argparse()
    process_elements(
        directory=args.d,
        sequence_ids_fn=args.i,
    )
