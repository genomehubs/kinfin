import asyncio
import glob
import json
from collections import defaultdict
from typing import Dict


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


def extract_attributes_and_taxon_sets(filepath: str):
    files = glob.glob(f"{filepath}/**/*.cluster_metrics.txt")
    files = [file.split(filepath)[1] for file in files]
    attributes = set()
    result = {"attributes": [], "taxon_set": defaultdict(list)}
    for file in files:
        filename = file.split("/")[-1]
        attribute = filename.split(".")[0]
        taxon_set = filename.split(".")[1]
        attributes.add(attribute)
        result["taxon_set"][attribute].append(taxon_set)
    result["attributes"] = sorted(attributes)
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
        items.sort(
            key=lambda item: tuple(item[1].get(key, float("inf")) for key in sort_keys),
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
