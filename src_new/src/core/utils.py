import atexit
import datetime
import json
import logging
import pathlib
import pickle
import shutil
import signal
import sys
import traceback

import definitions
import pandas as pd
import requests
import tqdm

logger = logging.getLogger(__name__)


def killed(signum, frame):
    logger.error("process got killed via CTRL+C")
    sys.exit(1)


def murdered(signum, frame):
    logger.error("process got killed via SIGTERM")
    sys.exit(1)


def testament(f=None, keep_dir=False):
    if f is not None:
        atexit.register(
            f,
            keep_dir=keep_dir,
        )
        signal.signal(signal.SIGINT, killed)  # Interrupt from keyboard
        signal.signal(signal.SIGTERM, murdered)  # Interrupt from kills


def iter_seq_length(fn):
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


def download(url, dest_fn):
    response = requests.get(url, stream=True)
    try:
        with tqdm.tqdm(
            total=int(response.headers.get("content-length", 0)),
            unit="B",
            desc=f"[{dest_fn}]",
            unit_scale=True,
        ) as p:
            with open(str(dest_fn), "wb") as fh:
                for data in response.iter_content(1024):
                    p.update(len(data))
                    fh.write(data)
    except Exception:
        return False
    return True


def get_fn(fn, outdir=None, dir=None, suffix=""):
    # [ToDo] finish
    pass


def get_orthogroups_df(filters=None):
    return load(fn=get_dir("INPUT") / definitions.ORTHOGROUPS_FN, filters=filters)


def get_counts_df(columns=None, nan=False):
    if nan:
        return load(fn=get_dir("TMP") / definitions.COUNTS_NAN_FN, columns=columns)
    return load(fn=get_dir("INPUT") / definitions.COUNTS_FN, columns=columns)


def get_elements_df():
    return load(fn=get_dir("INPUT") / definitions.ELEMENTS_FN)


def get_interpro_df():
    return load(fn=get_dir("INPUT") / definitions.INTERPRO_FN)


def get_annotation_df():
    return load(fn=get_dir("ANNOTATION") / definitions.ANNOTATION_FN)


def set_dir(name, value):
    tmp_paths_dict = {}
    if not definitions.TMP_PATHS_FILE.exists():
        dump(tmp_paths_dict, definitions.TMP_PATHS_FILE)
    tmp_paths_dict = load(definitions.TMP_PATHS_FILE)
    tmp_paths_dict[name] = value
    dump(tmp_paths_dict, definitions.TMP_PATHS_FILE)


def get_dir(name):
    return load(definitions.TMP_PATHS_FILE).get(name, None)


def format_fn(fn, prefix="", suffix=""):
    fn = fn if isinstance(fn, pathlib.Path) else pathlib.Path(fn)
    fn = pathlib.Path(f"{prefix}/{fn.name}") if prefix else fn
    fn = fn.with_suffix(suffix) if suffix else fn
    return str(fn.absolute())


def format_elapsed(seconds):
    td = datetime.timedelta(seconds=seconds)
    return f"elapsed: {td}"


def format_number(number):
    return f"{number:,.12g}"


def mkdir(name, subdirs=[], do_replace=False):
    try:
        output_dir = pathlib.Path(name)
        if do_replace and output_dir.exists():
            shutil.rmtree(
                output_dir,
                ignore_errors=True,
            )
        if not output_dir.exists():
            logger.debug(f"creating directory: {name}")
            output_dir.mkdir(
                parents=True,
                exist_ok=True,
            )
        if not isinstance(subdirs, str):
            for subdir_name in subdirs:
                mkdir(
                    output_dir / subdir_name,
                    do_replace=False,
                )
        else:
            if subdirs == "init":
                set_dir("INPUT", output_dir / "input")
                set_dir("TMP", output_dir / ".tmp")
                set_dir("ANNOTATION", output_dir / "annotation")
                set_dir("TREE", output_dir / "tree")
                set_dir("PARTITION", output_dir / "partition")
                for subdir in [
                    get_dir("INPUT"),
                    get_dir("TMP"),
                    get_dir("ANNOTATION"),
                    get_dir("TREE"),
                    get_dir("PARTITION"),
                ]:
                    mkdir(subdir)
    except Exception:
        logger.exception("failed creating directory")
        return False
    return True


def load(fn, columns=None, names=None, filters=None):
    fn = fn if isinstance(fn, pathlib.Path) else pathlib.Path(fn)
    fmt = fn.suffix[1:]  # remove dot
    data = None
    try:
        if fmt == "tsv" or fmt == "csv":
            if names is not None:
                data = pd.read_csv(
                    fn,
                    sep=("\t" if fmt == "tsv" else ","),
                    names=names,
                )
            else:
                data = pd.read_csv(
                    fn,
                    sep=("\t" if fmt == "tsv" else ","),
                    header=0,
                )
        elif fmt == "parquet":
            # https://pandas.pydata.org/docs/reference/api/pandas.read_parquet.html
            data = pd.read_parquet(fn, columns=columns, engine="auto", filters=filters)
        elif fmt == "feather":
            # print(f"{fn=}, columns={columns=}, names={names=}")
            # https://pandas.pydata.org/docs/reference/api/pandas.read_feather.html
            data = pd.read_feather(fn, columns=columns, use_threads=True)
        elif fmt == "pickle":
            with open(fn, "rb") as fh:
                data = pickle.load(fh)
        elif fmt == "json":
            with open(fn, "r") as fh:
                data = json.load(fh)
        else:
            logger.error(f"unsupported extension '.{fmt}'' in file {fn}")
            sys.exit(1)
    except FileNotFoundError as exc:
        logger.error(f"reading {fn=} failed - {exc}")
        sys.exit(1)
    return data


def dump(data, fn, fmt="", index=True):
    if not (fn == sys.stdout or isinstance(fn, pathlib.Path)):
        fn = pathlib.Path(fn)
    fmt = fmt if fmt else fn.suffix[1:]  # remove dot
    try:
        # logger.debug(f"{fn}")
        if fmt == "tsv" or fmt == "csv":
            # https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_csv.html
            data.to_csv(
                fn,
                sep=("\t" if fmt == "tsv" else ","),
                na_rep="NA",
                index=index,
            )
        elif fmt == "parquet":
            # https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_parquet.html#pandas.DataFrame.to_parquet
            data.to_parquet(f"{fn}")
        elif fmt == "feather":
            # https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_feather.html#pandas.DataFrame.to_feather
            data.to_feather(fn)
        elif fmt == "pickle":
            # assumes data is dict
            with open(fn, "wb") as fh:
                pickle.dump(data, fh)
        elif fmt == "json":
            # assumes data is dict
            with open(fn, "w") as fh:
                json.dump(data, fh, indent=4)
        elif fmt == "txt":
            # assumes data is lines
            with open(fn, "w") as fh:
                fh.write("\n".join(data))
        else:
            logger.error(f"unknown format {fmt=}")
            raise NotImplementedError
    except Exception as exc:
        logger.error(f"dumping {fn=} failed - {exc}\n{traceback.format_exc()}")
    return fn
