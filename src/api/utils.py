import asyncio
import json
import os
from typing import Any, Dict

import polars as pl

from internal import parsers


def read_status(status_file):
    status_info = {}
    with open(status_file, "r") as file:
        for line in file:
            key, value = line.strip().split("=", 1)
            status_info[key] = value

    return status_info


def write_status(
    status_file: str,
    status: str,
    exit_code: int = None,
    error: str = None,
):
    with open(status_file, "w") as file:
        file.write(f"status={status}\n")
        if exit_code is not None:
            file.write(f"exit_code={exit_code}\n")
        if error:
            file.write(f"error={error}\n")


def extract_error_message(stderr: str) -> str:
    lines = stderr.strip().splitlines()
    error_message_lines = []
    error_found = False

    for line in lines:
        if "[ERROR] -" in line:
            error_found = True
            error_message_lines.append(line.split("[ERROR] -")[1])
            continue
        if error_found:
            error_message_lines.append(line)

    return (
        " ".join(error_message_lines)
        if error_message_lines
        else "An unknown error occurred."
    )


async def run_cli_command(command: list, status_file: str):
    write_status(status_file, "running")

    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()
        stdout = stdout.decode().strip()
        stderr = stderr.decode().strip()

        if process.returncode == 0:
            write_status(status_file, "completed")
            return stdout
        else:
            error_message = extract_error_message(stderr)
            write_status(
                status_file,
                "error",
                exit_code=process.returncode,
                error=error_message,
            )
            return None

    except Exception as e:
        write_status(status_file, "error", error=str(e))
        return None


def extract_attributes_and_taxon_sets(session_dir: str):
    """
    Extract attributes and taxon sets directly from the session's config file,
    rather than relying on pre-generated *.cluster_metrics.txt files.
    """
    config_file = os.path.join(session_dir, "config.txt")
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Config file not found: {config_file}")

    nodesdb_f = os.environ.get("NODESDB_F")
    ndb_f = os.environ.get("NDB_F")
    if not nodesdb_f or not ndb_f:
        raise RuntimeError("NODESDB_F and NDB_F environment variables must be set")

    nodesdb = parsers.nodesdb(filepath=nodesdb_f, outpath=ndb_f)
    config_df, attributes = parsers.configfile(config_file, nodesdb)

    label_columns = [
        col for col in attributes if col not in ("#IDX", "TAXON", "TAXID", "OUT")
    ]

    result = {
        "attributes": label_columns,
        "taxon_set": {
            label: sorted(config_df[label].unique()) for label in label_columns
        },
    }
    return result


def sort_and_paginate_result(
    result: dict,
    sort_by: str,
    sort_order: str = "asc",
    page: int = 1,
    size: int = 20,
) -> tuple:
    if sort_by:
        sort_keys = sort_by.split(",")
        items = list(result.items())

        def safe_key(item):
            values = []
            for key in sort_keys:
                value = item[1].get(key)
                # Use lowercase for string comparison
                if isinstance(value, str):
                    values.append(value.lower())
                elif value is not None:
                    values.append(value)
                else:
                    values.append("")
            return tuple(values)

        items.sort(
            key=safe_key,
            reverse=(sort_order != "asc"),
        )
        result = dict(items)

    start_index = (page - 1) * size
    end_index = start_index + size
    paginated_result = dict(list(result.items())[start_index:end_index])
    total_pages = -(-len(result) // size)

    return paginated_result, total_pages


CLUSTERING_DATASETS: Dict[str, dict] = {}


def load_clustering_datasets(json_path: str):
    global CLUSTERING_DATASETS
    with open(json_path, "r") as f:
        datasets = json.load(f)
        CLUSTERING_DATASETS = {item["id"]: item for item in datasets}


def flatten_dict(d, parent_key="", sep="_"):
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            items.append((new_key, ",".join(map(str, v))))
        else:
            items.append((new_key, v))
    return dict(items)


def read_json_file(file_path: str) -> Any:
    with open(file_path, "r") as f:
        return json.load(f)
