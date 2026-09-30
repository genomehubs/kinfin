import asyncio
import glob
import json
import os
from collections import defaultdict
from hashlib import sha256
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd
import yaml


def read_status(status_file):
    status_info = {}
    with open(status_file, "r") as file:
        # read json from file
        status_info = json.load(file)

    return status_info


def write_status(
    status_file: str,
    status: str,
    exit_code: int | None = None,
    error: str | None = None,
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
    write_status(status_file, "initialising")

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
        if attribute not in result["taxon_set"]:
            result["taxon_set"][attribute] = ["all"]
        if taxon_set != "all":
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


COLUMN_DESCRIPTIONS: Dict[str, dict] = {}


def load_column_descriptions(yaml_path: str):
    global COLUMN_DESCRIPTIONS
    with open(yaml_path, "r") as f:
        COLUMN_DESCRIPTIONS = yaml.safe_load(f)


def load_column_registry(
    table_name: str,
) -> dict[str, dict]:
    """
    Load the column registry for a specific table from a cached file.

    Parameters:
    - table_name [str]: The name of the table for which to load the column registry.

    Returns:
    - dict[str, dict]: A dictionary containing the column registry for the specified table.
    """
    tables = COLUMN_DESCRIPTIONS.get("tables", {})
    if table_name not in tables:
        raise ValueError(f"Table '{table_name}' not found in the column registry.")
    return tables[table_name]


def canonicalise_column_names(
    table_name: str,
    column_names: str | list[str],
) -> str | list[str]:
    """
    Canonicalise a column name based on the column registry for a specific table.

    Parameters:
    - table_name [str]: The name of the table.
    - column_names [str | list[str]]: The column name(s) to canonicalise.

    Returns:
    - str | list[str]: The canonicalised column name(s).

    Raises:
    - ValueError: If the table or column is not found in the registry.
    """
    registry = load_column_registry(table_name)
    if isinstance(column_names, str):
        column_names = [col.strip() for col in column_names.split(",")]
    elif isinstance(column_names, list):
        expanded_columns = []
        for col in column_names:
            expanded_columns.extend([c.strip() for c in col.split(",")])
        column_names = expanded_columns
    canonicalised_columns = []
    for canonical_name, details in registry.get("columns", {}).items():
        lc_canonical_name = canonical_name.lower()
        for col in column_names:
            col_lower = col.lower()
            aliases_lower = [alias.lower() for alias in details.get("aliases", [])]
            if lc_canonical_name == col_lower or col_lower in aliases_lower:
                canonicalised_columns.append(canonical_name)
                column_names.remove(col)
                break
    if not canonicalised_columns:
        raise ValueError(
            f"Column '{column_names}' not found in the registry for table '{table_name}'."
        )
    return canonicalised_columns


def get_column_metadata(
    table_name: str,
    column_name: str,
) -> dict:
    """
    Get metadata for a specific column in a table.

    Parameters:
    - table_name [str]: The name of the table.
    - column_name [str]: The name of the column.

    Returns:
    - dict: A dictionary containing the metadata for the specified column.

    Raises:
    - ValueError: If the table or column is not found in the registry.
    """
    registry = load_column_registry(table_name)
    if column_name not in registry.get("columns", {}):
        raise ValueError(
            f"Column '{column_name}' not found in the registry for table '{table_name}'."
        )
    return registry["columns"][column_name]


def get_default_visible_columns(table_name: str) -> list[str]:
    """
    Get the default visible columns for a specific table.

    Parameters:
    - table_name [str]: The name of the table.

    Returns:
    - list[str]: A list of default visible column names for the specified table.
    """
    registry = load_column_registry(table_name)
    return [
        col_name
        for col_name, details in registry.get("columns", {}).items()
        if details.get("default_visible", False)
    ]


def get_always_visible_columns(table_name: str) -> list[str]:
    """
    Get the always visible columns for a specific table.

    Parameters:
    - table_name [str]: The name of the table.

    Returns:
    - list[str]: A list of always visible column names for the specified table.
    """
    registry = load_column_registry(table_name)
    return [
        col_name
        for col_name, details in registry.get("columns", {}).items()
        if details.get("always_visible", False)
    ]


def resolve_requested_columns(
    table_name: str,
    requested_columns: list[str] | None = None,
) -> list[str]:
    """
    Resolve the requested columns for a specific table, ensuring they are valid and canonicalised.

    Parameters:
    - table_name [str]: The name of the table.
    - requested_columns [list[str] | None]: A list of requested column names. If None, defaults to the default visible columns.

    Returns:
    - list[str]: A list of resolved and canonicalised column names for the specified table.
    """
    always_visible_columns = get_always_visible_columns(table_name)
    if requested_columns is None or requested_columns in ["default", ["default"]]:
        return get_default_visible_columns(table_name) + always_visible_columns
    if not requested_columns or requested_columns == [""]:
        return always_visible_columns or None
    if requested_columns in ["all", ["all"]]:
        return list(load_column_registry(table_name).get("columns", {}).keys())
    columns = canonicalise_column_names(table_name, requested_columns)
    if isinstance(columns, str):
        columns = [columns]
    # Ensure always visible columns are included
    for col in always_visible_columns:
        if col not in columns:
            columns.append(col)
    return columns


def build_filter_spec(
    table_name: str,
    field: str,
    op: str,
    value: Any,
) -> dict:
    """
    Build a filter specification for a specific table and field.

    Parameters:
    - table_name [str]: The name of the table.
    - field [str]: The field/column name to filter on.
    - op [str]: The operation to apply (e.g., "eq", "lt", "gt").
    - value [Any]: The value to compare against.

    Returns:
    - dict: A dictionary representing the filter specification.

    Raises:
    - ValueError: If the table or field is not found in the registry.
    """
    registry = load_column_registry(table_name)
    if field not in registry.get("columns", {}):
        raise ValueError(
            f"Field '{field}' not found in the registry for table '{table_name}'."
        )
    return {
        "field": field,
        "op": op,
        "value": value,
        "type": registry["columns"][field].get("type", "string"),
    }


def normalise_filter_specs(
    table_name: str,
    filters: list[dict] | None,
    legacy_params: dict | None = None,
) -> list[dict]:
    """
    Normalise filter specifications for a specific table, ensuring they are valid and canonicalised.

    Parameters:
    - table_name [str]: The name of the table.
    - filters [list[dict] | None]: A list of filter specifications. If None, defaults to an empty list.
    - legacy_params [dict | None]: A dictionary of legacy filter parameters. If provided, these will be converted to filter specifications.

    Returns:
    - list[dict]: A list of normalised filter specifications for the specified table.
    """
    if filters is None:
        filters = []
    if legacy_params:
        for field, value in legacy_params.items():
            filters.append(build_filter_spec(table_name, field, "eq", value))
    return filters


def check_operation_validity(
    table_name: str,
    field: str,
    op: str,
) -> bool:
    """
    Check if a specific operation is valid for a given field in a table.

    Parameters:
    - table_name [str]: The name of the table.
    - field [str]: The field/column name to check.
    - op [str]: The operation to check (e.g., "eq", "lt", "gt").

    Returns:
    - bool: True if the operation is valid for the field, False otherwise.

    Raises:
    - ValueError: If the table or field is not found in the registry.
    """
    registry = load_column_registry(table_name)
    if field not in registry.get("columns", {}):
        raise ValueError(
            f"Field '{field}' not found in the registry for table '{table_name}'."
        )
    # use field type to determine valid operations
    field_type = registry["columns"][field].get("type", "string")
    if field_type == "string":
        return op in {"eq", "ne", "in", "not_in", "contains", "not_contains"}
    elif field_type in ["integer", "float"]:
        return op in {"eq", "ne", "lt", "gt", "lte", "gte", "in", "not_in"}
    else:
        return op in {"eq", "ne", "in", "not_in"}


def apply_filters_to_frame(
    df: pd.DataFrame,
    table_name: str,
    filters: list[dict],
) -> pd.DataFrame:
    """
    Apply a list of filter specifications to a pandas DataFrame.

    Parameters:
    - df [pd.DataFrame]: The DataFrame to filter.
    - table_name [str]: The name of the table (used for validation).
    - filters [list[dict]]: A list of filter specifications to apply.

    Returns:
    - pd.DataFrame: The filtered DataFrame.
    """
    for f in filters:
        field = f["field"]
        normalised_field = canonicalise_column_names(table_name, field)
        if isinstance(normalised_field, list):
            normalised_field = normalised_field[0]
        op = f["op"]
        if not check_operation_validity(table_name, normalised_field, op):
            raise ValueError(
                f"Operation '{op}' is not valid for field '{field}' in table '{table_name}'."
            )
        value = f["value"]
        if op == "eq":
            df = df[df[normalised_field] == value]
        elif op == "lt":
            df = df[df[normalised_field] < value]
        elif op == "gt":
            df = df[df[normalised_field] > value]
        elif op == "ne":
            df = df[df[normalised_field] != value]
        elif op == "in":
            df = df[df[normalised_field].isin(value)]
        elif op == "not_in":
            df = df[~df[normalised_field].isin(value)]
        elif op == "contains":
            df = df[df[normalised_field].str.contains(value)]
        elif op == "not_contains":
            df = df[~df[normalised_field].str.contains(value)]
        elif op == "gte":
            df = df[df[normalised_field] >= value]
        elif op == "lte":
            df = df[df[normalised_field] <= value]
        elif op == "is_null":
            df = df[df[normalised_field].isnull()]
        elif op == "not_null":
            df = df[df[normalised_field].notnull()]

    return df


def normalise_field_list(raw_values: Optional[Iterable[str]]) -> List[str]:
    if raw_values is None:
        return []

    expanded: List[str] = []
    for value in raw_values:
        if value is None:
            continue
        if isinstance(value, str):
            expanded.extend(part.strip() for part in value.split(","))
        else:
            expanded.append(str(value).strip())

    cleaned = [item for item in expanded if item]
    return list(dict.fromkeys(cleaned))


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


def get_clustering_root() -> str:
    """
    Returns the root directory for clustering datasets.

    Checks the RESULTS_BASE_DIR environment variable first. If not set, defaults to the current working directory.
    """
    # convert to absolute path
    return os.path.abspath(os.getenv("RESULTS_BASE_DIR", os.getcwd()))


def get_clustering_artifact_root(clustering_id: str) -> str:
    """
    Returns the artifact root directory for a specific clustering dataset.

    Parameters:
    - clustering_id [str]: The ID of the clustering dataset.

    Returns:
    - str: The path to the artifact root directory for the specified clustering dataset.
    """
    if not (
        root_dir := CLUSTERING_DATASETS.get(clustering_id, {}).get("artifact_root")
    ):
        raise ValueError(
            f"No artifact root found for clustering dataset '{clustering_id}'."
        )
    if root_dir.startswith("~"):
        root_dir = os.path.expanduser(root_dir)
    if not os.path.isabs(root_dir):
        root_dir = os.path.join(get_clustering_root(), root_dir)
    return root_dir


def get_clustering_status_dir(clustering_id: str) -> str:
    """
    Returns the status directory for a specific clustering dataset.

    Parameters:
    - clustering_id [str]: The ID of the clustering dataset.

    Returns:
    - str: The path to the status directory for the specified clustering dataset.
    """
    # Determine the root directory for the clustering dataset's status
    # handle relative paths in status_root by joining with the clustering root directory
    # avoid encoving /./ or /../ in the path by using os.path.join and os.path.normpath
    root_dir = os.path.normpath(
        os.path.join(
            get_clustering_root(),
            CLUSTERING_DATASETS.get(clustering_id, {}).get("status_root", "."),
        )
    )
    return os.path.join(root_dir, clustering_id)


# def get_default_run_dir(clustering_id: str) -> str:
#     """
#     Returns the default run directory for a specific clustering dataset.

#     Parameters:
#     - clustering_id [str]: The ID of the clustering dataset.

#     Returns:
#     - str: The path to the default run directory for the specified clustering dataset.
#     """
#     output_dir = get_clustering_output_dir(clustering_id)
#     default_partition_id = derive_default_partition_id(clustering_id)
#     if default_partition_id:
#         return os.path.join(output_dir, "partitions", default_partition_id)
#     else:
#         raise ValueError(
#             f"No default partition ID found for clustering dataset '{clustering_id}'."
#         )


# def get_default_status_path(clustering_id: str) -> str:
#     """
#     Returns the path to the default status file for a specific clustering dataset.

#     Parameters:
#     - clustering_id [str]: The ID of the clustering dataset.

#     Returns:
#     - str: The path to the default status file for the specified clustering dataset.
#     """
#     run_dir = get_default_run_dir(clustering_id)
#     return os.path.join(run_dir, "status.json")


def get_clustering_artifact_dir(
    clustering_id: str, artifact_type: str | None = "partition"
) -> str:
    """
    Returns the artifact directory for a specific clustering dataset.

    Parameters:
    - clustering_id [str]: The ID of the clustering dataset.
    - artifact_type [str, optional]: The type of artifact directory to return. Defaults to "partition".

    Returns:
    - str: The path to the artifact directory for the specified clustering dataset.
    """
    root_dir = get_clustering_artifact_root(clustering_id)
    if artifact_path := (
        CLUSTERING_DATASETS.get(clustering_id, {})
        .get("artifacts", {})
        .get(artifact_type, "")
    ):
        return os.path.join(root_dir, artifact_path)
    else:
        raise ValueError(
            f"No artifact path found for clustering dataset '{clustering_id}' and artifact type '{artifact_type}'."
        )


def get_partition_artifact_dir(
    clustering_id: str,
    partition_name: str | None = None,
    artifact_type: str | None = "partition",
) -> str:
    """
    Returns the artifact directory for a specific partition of a clustering dataset.

    Parameters:
    - clustering_id [str]: The ID of the clustering dataset.
    - partition_name [str, optional]: The name of the partition. If not provided, uses the default partition.
    - artifact_type [str, optional]: The type of artifact directory to return. Defaults to "partition".

    Returns:
    - str: The path to the artifact directory for the specified partition.
    """
    artifact_dir = get_clustering_artifact_dir(clustering_id, artifact_type)
    if not partition_name:
        return artifact_dir
    status = read_run_status_file(clustering_id, partition_name)
    normalized_state = normalise_run_state(status.get("state", "unknown"))

    if normalized_state != "ready":
        raise ValueError(
            f"Partition '{partition_name}' for clustering dataset '{clustering_id}' is not ready. Current state: {normalized_state}"
        )
    if output_name := status.get("output_name"):
        return os.path.join(artifact_dir, output_name)
    else:
        raise ValueError(
            f"No output name found for partition '{partition_name}' of clustering dataset '{clustering_id}'."
        )


def preferred_suffix_order(kind: str | None = "table") -> list[str]:
    """
    Returns the preferred suffix order for a given kind of file.

    Parameters:
    - kind [str, optional]: The kind of file. Defaults to "table".

    Returns:
    - list[str]: A list of preferred suffixes in order of preference.
    """
    if kind == "table":
        return ["parquet", "feather", "tsv", "csv", "json"]
    elif kind == "plot":
        return ["png", "pdf", "svg"]
    else:
        return [
            kind or "tsv"
        ]  # Return the kind itself if it's not recognized, or fall back to "tsv" if kind is None


def get_partition_artifact_path(
    clustering_id: str,
    partition_name: str | None = None,
    artifact_type: str | None = "partition",
    artifact_file: str = "summary",
    kind: str | None = "table",
) -> str:
    artifact_dir = get_partition_artifact_dir(
        clustering_id, partition_name=partition_name, artifact_type=artifact_type
    )
    if partition_name:
        if output_name := read_run_status_file(clustering_id, partition_name).get(
            "output_name"
        ):
            artifact_file = f"{output_name}.{artifact_file}"
    suffix_order = preferred_suffix_order(kind=kind)
    for suffix in suffix_order:
        candidate = f"{artifact_file}.{suffix}"
        candidate_path = os.path.join(artifact_dir, candidate)
        if os.path.exists(candidate_path):
            return candidate_path
    raise FileNotFoundError(
        f"No artifact file found for '{artifact_file}' with preferred suffixes {suffix_order} in directory '{artifact_dir}'."
    )


def get_common_artifact_path(
    clustering_id: str,
    artifact_type: str | None = "tally",
    artifact_file: str = "tally",
    kind: str | None = "table",
) -> str:
    artifact_dir = get_partition_artifact_dir(
        clustering_id, partition_name=None, artifact_type=artifact_type
    )
    suffix_order = preferred_suffix_order(kind=kind)
    for suffix in suffix_order:
        candidate = f"{artifact_file}.{suffix}"
        candidate_path = os.path.join(artifact_dir, candidate)
        if os.path.exists(candidate_path):
            return candidate_path
    raise FileNotFoundError(
        f"No artifact file found for '{artifact_file}' with preferred suffixes {suffix_order} in directory '{artifact_dir}'."
    )


def list_partition_status_dirs(clustering_id: str) -> list:
    """
    Lists all partition status directories for a specific clustering dataset.

    Parameters:
    - clustering_id [str]: The ID of the clustering dataset.

    Returns:
    - list: A list of paths to partition status directories for the specified clustering dataset.
    """
    output_dir = get_clustering_status_dir(clustering_id)
    return glob.glob(os.path.join(output_dir, "partitions", "*"))


def get_partition_status_dir(clustering_id: str, partition_name: str) -> str:
    """
    Returns the directory for a specific partition of a clustering dataset.

    Parameters:
    - clustering_id [str]: The ID of the clustering dataset.
    - partition_name [str]: The name of the partition.

    Returns:
    - str: The path to the specified partition directory.
    """
    output_dir = get_clustering_status_dir(clustering_id)
    if partition_id := partition_name or derive_default_partition_id(clustering_id):
        return os.path.join(output_dir, "partitions", partition_id)
    raise ValueError(
        f"No partition ID found for clustering dataset '{clustering_id}' and partition '{partition_name}'."
    )


def get_partition_status_path(
    clustering_id: str, partition_name: str | None = None
) -> str:
    """
    Returns the path to the status file for a specific partition of a clustering dataset.

    Parameters:
    - clustering_id [str]: The ID of the clustering dataset.
    - partition_name [str, optional]: The name of the partition. If not provided, uses the default partition.

    Returns:
    - str: The path to the status file for the specified partition.
    """
    partition_id = partition_name or derive_default_partition_id(clustering_id)
    if not partition_id:
        raise ValueError(
            f"No partition ID found for clustering dataset '{clustering_id}' and partition '{partition_name}'."
        )
    partition_dir = get_partition_status_dir(clustering_id, partition_id)
    return os.path.join(partition_dir, "status.json")


def read_run_status_file(clustering_id: str, partition_name: str | None = None) -> dict:
    """
    Reads the status file for a specific clustering dataset or its partition.

    Parameters:
    - clustering_id [str]: The ID of the clustering dataset.
    - partition_name [str, optional]: The name of the partition. If not provided, reads the default run status.

    Returns:
    - dict: A dictionary containing the status information.
    """
    status_path = get_partition_status_path(clustering_id, partition_name)
    print(f"Reading run status from: {status_path}")

    if os.path.exists(status_path):
        return read_status(status_path)
    resolved_partition_name = partition_name or "default"
    return {
        "schema_version": 1,
        "run_name": resolved_partition_name,
        "state": "error",
        "message": f"Run status for {resolved_partition_name} not found.",
        "error": {
            "code": "not_found",
            "message": f"Run status for {resolved_partition_name} not found.",
        },
    }


def normalise_run_state(state: str) -> str:
    """
    Normalizes the run state to a standard set of states.

    Parameters:
    - state [str]: The original state string.

    Returns:
    - str: The normalized state string.
    """
    state_mapping = {
        "running": "initialising",
        "queued": "initialising",
        "initialising": "initialising",
        "completed": "ready",
        "complete": "ready",
        "success": "ready",
        "ready": "ready",
        "failed": "error",
        "error": "error",
        "not_found": "missing",
        "missing": "missing",
        "expired": "expired",
    }
    return state_mapping.get(state.lower(), "unknown")


def derive_run_status(clustering_id: str, partition_name: str | None = None) -> dict:
    """
    Derives the run status for a specific clustering dataset or its partition.

    Parameters:
    - clustering_id [str]: The ID of the clustering dataset.
    - partition_name [str, optional]: The name of the partition. If not provided, derives the default run status.

    Returns:
    - dict: A dictionary containing the derived run status information.
    """
    run_status = read_run_status_file(clustering_id, partition_name)
    normalized_state = normalise_run_state(run_status.get("state", "unknown"))
    run_status["state"] = normalized_state
    run_status["details"] = {
        "default_analysis_exists": os.path.exists(
            get_partition_status_path(clustering_id)
        ),
        "status_file_exists": os.path.exists(
            get_partition_status_path(clustering_id, partition_name)
        ),
        "artifacts_exist": os.path.exists(
            get_partition_artifact_dir(clustering_id, partition_name)
        ),
    }
    return run_status


# def derive_default_status(clustering_id: str) -> dict:
#     """
#     Derives a default status dictionary for a clustering dataset.

#     Parameters:
#     - clustering_id [str]: The ID of the clustering dataset.

#     Returns:
#     - dict: A dictionary containing the default status information.
#     """
#     default_partition_id = CLUSTERING_DATASETS.get(clustering_id, {}).get(
#         "default_partition_id"
#     )
#     if not default_partition_id:
#         return {
#             "schema_version": 1,
#             "run_name": "default",
#             "state": "missing",
#             "message": "Default partition ID not found for this clustering dataset.",
#             "error": {
#                 "code": "not_found",
#                 "message": "Default partition ID not found for this clustering dataset.",
#             },
#         }
#     run_status = derive_run_status(clustering_id, default_partition_id)
#     normalized_state = normalise_run_state(run_status.get("state", "unknown"))
#     run_status["state"] = normalized_state
#     return run_status


def count_partition_runs(clustering_id: str) -> int:
    """
    Counts the number of partition runs for a specific clustering dataset.

    Parameters:
    - clustering_id [str]: The ID of the clustering dataset.

    Returns:
    - int: The number of partition runs.
    """
    partition_dirs = list_partition_status_dirs(clustering_id)
    return len(partition_dirs)


def count_completed_partition_runs(clustering_id: str) -> int:
    """
    Counts the number of completed partition runs for a specific clustering dataset.

    Parameters:
    - clustering_id [str]: The ID of the clustering dataset.

    Returns:
    - int: The number of completed partition runs.
    """
    partition_dirs = list_partition_status_dirs(clustering_id)
    completed_count = 0
    for partition_dir in partition_dirs:
        partition_name = os.path.basename(partition_dir)
        run_status = derive_run_status(clustering_id, partition_name)
        if run_status.get("state") == "ready":
            completed_count += 1
    return completed_count


def derive_default_partition_id(clustering_id: str) -> str | None:
    """
    Retrieves the default partition ID for a specific clustering dataset.

    Parameters:
    - clustering_id [str]: The ID of the clustering dataset.

    Returns:
    - str | None: The default partition ID, or None if not found.
    """
    return CLUSTERING_DATASETS.get(clustering_id, {}).get("default_partition_id")


def get_clustering_readiness(clustering_id: str) -> bool:
    """
    Determines the readiness of a clustering dataset based on the default partition.

    Parameters:
    - clustering_id [str]: The ID of the clustering dataset.

    Returns:
    - dict: A dictionary containing readiness information.
    """
    default_partition_id = derive_default_partition_id(clustering_id)
    run_status = derive_run_status(clustering_id, default_partition_id)
    return run_status.get("state") == "ready"


def canonicalise_list(partition_list: list[str]) -> list[str]:
    """
    Canonicalises a list of entity names by converting to lowercase,removing duplicates and sorting them.

    Parameters:
    - partition_list [list[str]]: A list of entity names.

    Returns:
    - list[str]: A canonicalised list of unique, sorted entity names.
    """
    return sorted({entity.lower() for entity in partition_list})


def sort_keys_by_values(
    input_dict: dict[str, list[str]], reverse: bool = False
) -> list[str]:
    """
    Sorts the keys of a dictionary based on their corresponding values.
    Sorting is based on the first element of the canonicalised value list for each key.

    Parameters:
    - input_dict [dict[str, list[str]]]: A dictionary where keys are strings and values are lists of strings.
    - reverse [bool]: If True, sorts in descending order; otherwise, sorts in ascending order.

    Returns:
    - list[str]: A list of keys sorted based on their corresponding values.
    """
    return sorted(
        input_dict.keys(),
        key=lambda k: canonicalise_list(input_dict[k])[0] if input_dict[k] else "",
        reverse=reverse,
    )


def validate_partition_dict(
    cluster_id: str, partition_dict: dict[str, list[str]]
) -> Tuple[bool, str]:
    """
    Validates a dictionary of entity names to ensure that each key has a non-empty list of associated names.

    Parameters:
    - cluster_id [str]: The ID of the clustering dataset.
    - partition_dict [dict[str, list[str]]]: A dictionary where keys are entity names and values are lists of associated names.

    Returns:
    - bool: True if the dictionary is valid; False otherwise.
    - str: An error message if the dictionary is invalid; an empty string if valid.
    """
    valid_members = [
        name.lower()
        for name in CLUSTERING_DATASETS.get(cluster_id, {}).get("valid_members", [])
    ]
    seen_ids = set()
    for _, values in partition_dict.items():
        if not isinstance(values, list) or not values:
            return False, "Values must be a non-empty list."
        for value in values:
            if not isinstance(value, str) or not value:
                return False, "Values must be non-empty strings."
            lc_value = value.lower()
            if lc_value not in valid_members:
                return False, f"Value '{value}' is not a valid ID."
            if lc_value in seen_ids:
                return False, f"Duplicate value '{value}' found."
            seen_ids.add(lc_value)
    return True, ""


def canonicalise_partition_dict(
    partition_dict: dict[str, list[str]],
) -> tuple[dict[int, list[str]], dict[str, int]]:
    """
    Canonicalises a dictionary of entity names by converting to lowercase, removing duplicates and sorting them.
    Converts the keys to standardised integer keys (e.g., 0, 1, 2) and returns the canonicalised dictionary.
    Also returns a mapping of the original keys to the new canonical keys.

    Parameters:
    - partition_dict [dict[str, list[str]]]: A dictionary where keys are entity names and values are lists of associated names.

    Returns:
    - dict[int, list[str]]: A canonicalised dictionary with unique, sorted entity names.
    - dict[str, int]: A mapping of original keys to canonical keys.
    """
    canonical_dict = {}
    key_mapping = {}
    sorted_keys = sort_keys_by_values(partition_dict)
    for i, key in enumerate(sorted_keys):
        canonical_key = i
        canonical_dict[canonical_key] = sorted(
            {entity.lower() for entity in partition_dict[key]}
        )
        key_mapping[key] = canonical_key
    return canonical_dict, key_mapping


def partition_selection_to_id(
    partition_dict: dict[str, list[str]],
) -> Tuple[str, dict[str, int]]:
    """
    Generates a unique hashed partition ID based on the canonicalised partition dictionary.
    The partition ID is a string representation of the canonicalised dictionary.

    Parameters:
    - partition_dict [dict[str, list[str]]]: A dictionary where keys are entity names and values are lists of associated names.

    Returns:
    - str: A unique partition ID.
    - dict[str, int]: A mapping of original keys to canonical keys.
    """
    canonical_dict, key_mapping = canonicalise_partition_dict(partition_dict)
    raw = json.dumps(canonical_dict, sort_keys=True)
    hashed = sha256(raw.encode()).hexdigest()[:16]
    return str(hashed), key_mapping
