import collections
import logging
import time

import core.log
import definitions
import tqdm

import core.utils

logger = logging.getLogger(__name__)


def parse_set(fn):
    strings = []
    if fn is not None:
        with open(fn) as fh:
            for line in fh:
                strings.append(line.rstrip("\n"))
    return set(strings)


def get_validator(include_fn, exclude_fn):
    is_valid = collections.defaultdict(lambda: True)
    if include_fn:
        is_valid = collections.defaultdict(lambda: False)
        is_valid.update({k: True for k in parse_set(include_fn)})
    if exclude_fn:
        is_valid = collections.defaultdict(lambda: True)
        is_valid.update({k: False for k in parse_set(exclude_fn)})
    return is_valid


def filter_orthogroups(
    orthogroups_fn,
    orthogroups_include_fn,
    orthogroups_exclude_fn,
    element_include_fn,
    element_exclude_fn,
):
    is_orthogroup_valid = get_validator(
        orthogroups_include_fn,
        orthogroups_exclude_fn,
    )
    is_element_valid = get_validator(
        element_include_fn,
        element_exclude_fn,
    )
    rows = []
    with open(orthogroups_fn) as orthogroup_fh:
        for line in orthogroup_fh:
            rows.append(line.rstrip("\n").split(" "))
    rows_valid = []

    counts = collections.Counter()
    with tqdm.tqdm(
        total=len(rows),
        desc=definitions.PROGRESS_DESC_ORTHOGROUPS_PARSE,
        ncols=definitions.PROGRESS_NCOLS,
    ) as pbar:
        for row in rows:
            element_ids_valid = []
            orthogroup_id, element_ids = row[0].replace(":", ""), row[1:]
            counts["orthogroups_total"] += 1
            counts["elements_total"] += len(element_ids)
            if is_orthogroup_valid[orthogroup_id]:
                for element_id in element_ids:
                    if is_element_valid[element_id]:
                        element_ids_valid.append(element_id)
                        counts["elements_included"] += 1
                    else:
                        counts["elements_excluded"] += 1
                if element_ids_valid:
                    rows_valid.append(f"{orthogroup_id}: {' '.join(element_ids_valid)}")
                    counts["orthogroups_included"] += 1
                else:
                    counts["orthogroups_excluded"] += 1
            else:
                counts["orthogroups_excluded"] += 1
                counts["elements_excluded"] += len(element_ids)

            pbar.update()
    out_fn = "orthogroups.preprocess.txt"
    with open(out_fn, "w") as out_fh:
        out_fh.write("\n".join(rows_valid))
        out_fh.write("\n")
    padding = len(core.utils.format_number(counts["elements_total"])) + 2
    logger.info(
        f"{core.utils.format_number(counts['orthogroups_total']):>{padding}} [orthogroups]"
    )
    logger.info(
        f"{core.utils.format_number(counts['orthogroups_included']):>{padding}}\t[included]"
    )
    logger.info(
        f"{core.utils.format_number(counts['orthogroups_excluded']):>{padding}}\t[excluded]"
    )
    logger.info(
        f"{core.utils.format_number(counts['elements_total']):>{padding}} [elements]"
    )
    logger.info(
        f"{core.utils.format_number(counts['elements_included']):>{padding}}\t[included]"
    )
    logger.info(
        f"{core.utils.format_number(counts['elements_excluded']):>{padding}}\t[excluded]"
    )


def run(args):
    t_0 = time.monotonic()
    args.d, args.v = "", True
    core.log.init_logger(args)
    for k, v in vars(args).items():
        logger.debug(f"[args] {f'{k}={v}'}")
    filter_orthogroups(
        orthogroups_fn=args.g,
        orthogroups_include_fn=args.i,
        orthogroups_exclude_fn=args.e,
        element_include_fn=args.I,
        element_exclude_fn=args.E,
    )
    logger.info(core.utils.format_elapsed(time.monotonic() - t_0))
