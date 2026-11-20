#!/usr/bin/env python3

import argparse
import collections
import logging
import os
import pathlib
import sys

import tqdm

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] [%(levelname)s] %(filename)s - %(message)s",
    stream=sys.stderr,
)


def existing_file(infile):
    if not os.path.isfile(infile):
        raise argparse.ArgumentTypeError(f"file '{infile}' does not exist")
    return infile


def read_file(infile):
    if not os.path.exists(infile):
        sys.exit("[X] File %s does not exist." % (infile))
    else:
        with open(infile) as fh:
            for line in fh:
                yield line


def parse_ids_f(id_f):
    ids = []
    for line in read_file(id_f):
        ids.append(line.rstrip("\n"))
    ids_set = set(ids)
    if len(ids_set) < len(ids):
        logger.warning(f"file '{id_f}' contains duplicated IDs.")
    return sorted(ids_set)


def get_argparse():
    class CustomFormatter(
        argparse.RawDescriptionHelpFormatter,
        argparse.ArgumentDefaultsHelpFormatter,
    ):
        pass

    parser = argparse.ArgumentParser(
        prog="filter_orthogroups",
        description="filter orthogroups.txt based on list of protein IDs",
        formatter_class=CustomFormatter,
        epilog="""""",
    )
    parser.add_argument(
        "-g",
        metavar="ORTHOGROUPS_F",
        required=True,
        type=existing_file,
        help="orthogroups file",
    )
    parser.add_argument(
        "-i",
        metavar="INCLUDE",
        type=existing_file,
        help="List of sequence IDs to include",
    )
    parser.add_argument(
        "-e",
        metavar="EXCLUDE",
        type=existing_file,
        help="List of sequence IDs to exclude",
    )
    return parser.parse_args()


def get_filter_dict(include_f=None, exclude_f=None):
    if include_f and exclude_f:
        logger.error("supply either '-i' OR '-e'. Can't be both.")
        sys.exit(1)
    default_bool = True
    id_list = []
    if include_f:
        default_bool = False
        id_list = parse_ids_f(include_f)
    if exclude_f:
        id_list = parse_ids_f(exclude_f)
    filter_dict = collections.defaultdict(lambda: default_bool)
    for _id in id_list:
        filter_dict[_id] = not default_bool
    return filter_dict


def process_orthogroups(orthogroups_f=None, filter_dict=None):
    counts = collections.Counter()
    rows_in = [line.rstrip("\n").split(" ") for line in read_file(orthogroups_f)]
    rows_out = []
    with tqdm.tqdm(
        total=len(rows_in),
        desc=f"[{'ORTHOGROUPS'.center(23, '.')}]",
        ncols=0,
    ) as pbar:
        counts["orthogroups"] = len(rows_in)
        for row in rows_in:
            row_out = []
            orthogroup_id, element_ids = row[0], row[1:]
            orthogroup_type = "singleton" if len(element_ids) == 1 else "non_singletons"
            for element_id in element_ids:
                counts["proteins"] += 1
                if filter_dict[element_id] is True:
                    row_out.append(element_id)
                    counts["proteins_included"] += 1
                else:
                    counts["proteins_excluded"] += 1
            if row_out:
                rows_out.append(f"{orthogroup_id} {' '.join(row_out)}")
                counts[f"orthogroups_included_{orthogroup_type}"] += 1
            else:
                counts[f"orthogroups_excluded_{orthogroup_type}"] += 1
            pbar.update()
    for label in sorted(counts):
        logger.info(f"{label}: {counts[label]}")
    if counts["proteins_excluded"] > 0:
        out_fn = orthogroups_f.parent / (
            orthogroups_f.stem + ".filtered" + orthogroups_f.suffix
        )
        with open(out_fn, "w") as out_fh:
            out_fh.write("\n".join(rows_out))


if __name__ == "__main__":
    args = get_argparse()
    filter_dict = get_filter_dict(
        include_f=args.i,
        exclude_f=args.e,
    )
    process_orthogroups(orthogroups_f=pathlib.Path(args.g), filter_dict=filter_dict)
