import asyncio
import csv
import io
import itertools
import json
import logging
import os
import re
import shlex
import sys
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.security import APIKeyHeader
from pydantic import AliasChoices, BaseModel, Field

from api.fileparsers import (
    parse_attribute_summary_file,
    parse_cluster_metrics_file,
    parse_cluster_summary_file,
    parse_clustering_file,
    parse_pairwise_file,
    parse_taxon_counts_file,
    parse_valid_proteome_ids_file,
    read_table_payload,
)
from api.sessions import query_manager
from api.utils import (
    DATASETS,
    derive_default_partition_id,
    derive_run_status,
    extract_error_message,
    extract_attributes_and_taxon_sets,
    flatten_dict,
    get_common_artifact_path,
    get_dataset_artifact_dir,
    get_partition_artifact_path,
    get_partition_status_dir,
    get_partition_status_path,
    normalise_run_state,
    normalise_field_list,
    partition_selection_to_id,
    read_json_file,
    read_run_status_file,
    read_status,
    run_cli_command,
    sort_and_paginate_result,
    validate_partition_dict,
)
from core.utils import check_file

from .config.limits import LIMIT_INIT, LIMIT_STANDARD
from .core.limiter import limiter

LOGGER = logging.getLogger("uvicorn.error")
LOGGER.setLevel(logging.DEBUG)

RUN_SUMMARY_FILEPATH = "summary.json"
COUNTS_FILEPATH = "cluster_counts_by_taxon.txt"
CLUSTER_SUMMARY_FILENAME = "cluster_summary.txt"
ATTRIBUTE_METRICS_FILENAME = "attribute_metrics.txt"
CLUSTER_METRICS_FILENAME = "cluster_metrics.txt"
PAIRWISE_ANALYSIS_FILE = "pairwise_representation_test.txt"


router = APIRouter()

json_path = os.path.join(os.path.dirname(__file__), "column_descriptions.json")

with open(json_path, "r") as f:
    COLUMN_DESCRIPTIONS = json.load(f)

# Create a quick lookup for code -> name mapping
CODE_TO_COLUMN_NAME = {item["code"]: item["name"] for item in COLUMN_DESCRIPTIONS}
CODE_TO_FILETYPE = {item["code"]: item["file"] for item in COLUMN_DESCRIPTIONS}


class InputSchema(BaseModel):
    config: List[Dict[str, str]]
    dataset_id: str = Field(validation_alias=AliasChoices("dataset_id", "clusterId"))
    isAdvanced: bool


class ResponseSchema(BaseModel):
    status: str
    message: str
    query: Optional[str] = None
    data: Optional[Any] = None
    timestamp: str = datetime.now().isoformat()
    error: Optional[str] = None
    total_pages: Optional[int] = None
    current_page: Optional[int] = None
    entries_per_page: Optional[int] = None


# X-Session-ID header will be required to access plots/files later
header_scheme = APIKeyHeader(name="x-session-id")

router = APIRouter()


def check_kinfin_session(func):
    @wraps(func)
    async def wrapper(request: Request, session_id: str, *args, **kwargs):
        try:
            result_dir = query_manager.get_session_dir(session_id)
            if not result_dir:
                return JSONResponse(
                    content=ResponseSchema(
                        status="error",
                        message="Kinfin analysis not initialized",
                        error="session_not_initialized",
                        query=str(request.url),
                    ).model_dump(),
                    status_code=428,
                )

            status_file = os.path.join(result_dir, f"{session_id}.status")
            if not os.path.exists(status_file):
                return JSONResponse(
                    content=ResponseSchema(
                        status="error",
                        message="Kinfin analysis not initialized",
                        error="session_not_initialized",
                        query=str(request.url),
                    ).model_dump(),
                    status_code=428,
                )

            run_status = read_status(status_file)
            status = run_status.get("status")

            if status in ["initialising", "running"]:
                return JSONResponse(
                    content=ResponseSchema(
                        status="error",
                        message="Kinfin analysis is still running. Please wait for analysis to complete",
                        data={"is_complete": False},
                        query=str(request.url),
                    ).model_dump(),
                    status_code=202,
                )
            elif status == "error":
                return JSONResponse(
                    content=ResponseSchema(
                        status="error",
                        message="Some error occurred during Kinfin analysis.",
                        error=run_status,
                        data={"session_terminated_due_to_error": True},
                        query=str(request.url),
                    ).model_dump(),
                    status_code=400,
                )

            return await func(request, session_id=session_id, *args, **kwargs)

        except Exception as e:
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message="Internal Server Error",
                    error=str(e),
                    query=str(request.url),
                ).model_dump(),
                status_code=500,
            )

    return wrapper


def get_session_status(session_id: str) -> Dict:
    result_dir = query_manager.get_session_dir(session_id)
    if not result_dir:
        return {
            "session_id": session_id,
            "status": "not_initialized",
            "expiryDate": None,
        }

    status_file = os.path.join(result_dir, f"{session_id}.status")
    if not os.path.exists(status_file):
        return {
            "session_id": session_id,
            "status": "not_initialized",
            "expiryDate": None,
        }

    run_status = read_status(status_file)
    status = run_status.get("status")

    expiry_date = datetime.fromtimestamp(os.path.getmtime(result_dir)) + timedelta(
        hours=query_manager.expiration_hours
    )
    return {
        "session_id": session_id,
        "status": status,
        "expiryDate": expiry_date.isoformat(),
    }


def get_nested_value(data, path):
    keys = path.split(".")
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, {})
        else:
            return None
    return data if data != {} else None


def utc_timestamp() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def write_partition_status_file(status_path: str, status: dict):
    os.makedirs(os.path.dirname(status_path), exist_ok=True)
    with open(status_path, "w") as file:
        json.dump(status, file, indent=2)
        file.write("\n")


def resolve_dataset_path(
    dataset_info: dict, *keys: str, default_filename: str | None = None
):
    files = dataset_info.get("files", {})
    value = None
    for key in keys:
        value = files.get(key) or dataset_info.get(key)
        if value:
            break
    if not value and default_filename:
        value = default_filename
    if not value:
        return None
    if value.startswith("~"):
        value = os.path.expanduser(value)
    if os.path.isabs(value):
        return value
    if dataset_path := dataset_info.get("path"):
        workdir = os.getenv("KINFIN_WORKDIR", "")
        return os.path.join(workdir, dataset_path, value)
    return value


def default_partition_config_rows(
    partition_set: dict[str, list[str]]
) -> list[dict[str, str]]:
    return [
        {"sample_id": member, "default_partition": label}
        for label, members in partition_set.items()
        for member in members
    ]


def validate_partition_set_shape(
    partition_set: dict[str, list[str]]
) -> tuple[bool, str]:
    seen_ids = set()
    for values in partition_set.values():
        if not isinstance(values, list) or not values:
            return False, "Values must be a non-empty list."
        for value in values:
            if not isinstance(value, str) or not value:
                return False, "Values must be non-empty strings."
            lc_value = value.lower()
            if lc_value in seen_ids:
                return False, f"Duplicate value '{value}' found."
            seen_ids.add(lc_value)
    return True, ""


def build_dataset_init_command(
    dataset_id: str,
    dataset_info: dict,
    partition_id: str,
    config_path: str,
    output_dir: str,
    status_path: str,
) -> list[str]:
    command_template = os.getenv("KINFIN_INIT_COMMAND")
    if command_template:
        return [
            part.format(
                dataset_id=dataset_id,
                partition_id=partition_id,
                config_path=config_path,
                output_dir=output_dir,
                status_path=status_path,
            )
            for part in shlex.split(command_template)
        ]

    orthogroups_file = resolve_dataset_path(
        dataset_info,
        "orthogroups_file",
        "orthogroups",
        "cluster_file",
        default_filename="Orthogroups.txt",
    )
    if not orthogroups_file:
        raise ValueError("No orthogroups file configured for dataset.")
    check_file(orthogroups_file, install_kinfin=True)

    command = [
        os.getenv("KINFIN_INIT_PYTHON", sys.executable),
        os.getenv("KINFIN_INIT_SCRIPT", "src_new/src/main.py"),
        "analysis",
        "-g",
        orthogroups_file,
        "-c",
        config_path,
        "-d",
        output_dir,
    ]

    fasta_dir = resolve_dataset_path(dataset_info, "fasta_dir", "fastas")
    sequence_ids_file = resolve_dataset_path(
        dataset_info,
        "sequence_ids_file",
        "sequence_ids",
        default_filename="kinfin.SequenceIDs.txt",
    )
    species_ids_file = resolve_dataset_path(
        dataset_info,
        "species_ids_file",
        "species_ids",
        default_filename="kinfin.SpeciesIDs.txt",
    )
    if fasta_dir and os.path.isdir(fasta_dir):
        command.extend(["-f", fasta_dir])
    elif (
        sequence_ids_file
        and species_ids_file
        and os.path.exists(sequence_ids_file)
        and os.path.exists(species_ids_file)
    ):
        command.extend(["-s", sequence_ids_file, "-S", species_ids_file])
    else:
        command.append("-P")

    optional_file_args = [
        ("tree_file", "tree", "-t", "kinfin.tree.nwk"),
        ("interpro_file", "interpro", "-i", None),
        ("table_file", "table", "-a", None),
    ]
    for primary_key, secondary_key, flag, default_filename in optional_file_args:
        path = resolve_dataset_path(
            dataset_info,
            primary_key,
            secondary_key,
            default_filename=default_filename,
        )
        if path and os.path.exists(path):
            command.extend([flag, path])

    interpro_dir = resolve_dataset_path(dataset_info, "interpro_dir")
    if interpro_dir and os.path.isdir(interpro_dir):
        command.extend(["-I", interpro_dir])

    cli_options = dataset_info.get("init_cli_options", {})
    if output_format := cli_options.get("output_format"):
        command.extend(["-F", output_format])
    if processes := cli_options.get("processes"):
        command.extend(["-p", str(processes)])
    if plot_format := cli_options.get("plot_format"):
        command.extend(["-l", plot_format])
    if cli_options.get("no_plots"):
        command.append("-L")
    command.extend(cli_options.get("extra_args", []))
    return command


async def run_dataset_init_command(
    command: list[str],
    status_path: str,
    dataset_id: str,
    partition_id: str,
    output_name: str,
    started_at: str,
):
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        stdout = stdout.decode().strip()
        stderr = stderr.decode().strip()
        finished_at = utc_timestamp()

        if process.returncode == 0:
            write_partition_status_file(
                status_path,
                {
                    "schema_version": 1,
                    "run_name": "default",
                    "dataset_id": dataset_id,
                    "partition_id": partition_id,
                    "state": "ready",
                    "message": "Default partition analysis completed successfully.",
                    "started_at": started_at,
                    "updated_at": finished_at,
                    "finished_at": finished_at,
                    "error": None,
                    "output_name": output_name,
                },
            )
            return

        write_partition_status_file(
            status_path,
            {
                "schema_version": 1,
                "run_name": "default",
                "dataset_id": dataset_id,
                "partition_id": partition_id,
                "state": "error",
                "message": "Default partition analysis failed.",
                "started_at": started_at,
                "updated_at": finished_at,
                "finished_at": finished_at,
                "error": {
                    "code": "cli_failed",
                    "message": (
                        extract_error_message(stderr) if stderr else "CLI failed."
                    ),
                    "exit_code": process.returncode,
                    "stderr": stderr,
                    "stdout": stdout,
                },
                "output_name": output_name,
            },
        )
    except Exception as e:
        failed_at = utc_timestamp()
        write_partition_status_file(
            status_path,
            {
                "schema_version": 1,
                "run_name": "default",
                "dataset_id": dataset_id,
                "partition_id": partition_id,
                "state": "error",
                "message": "Default partition analysis failed to start.",
                "started_at": started_at,
                "updated_at": failed_at,
                "finished_at": failed_at,
                "error": {
                    "code": "start_failed",
                    "message": str(e),
                },
                "output_name": output_name,
            },
        )


@router.post("/kinfin/init", response_model=ResponseSchema)
@limiter.limit(LIMIT_INIT)
async def initialize(input_data: InputSchema, request: Request):
    """
    Initialize the analysis process.

    Args:
        input_data (InputSchema): The input data for analysis.
        background_tasks (BackgroundTasks): FastAPI's BackgroundTasks for running analysis asynchronously.

    Returns:
        JSONResponse: A response indicating that the analysis task has been queued.

    Raises:
        HTTPException: If there's an error in the input data or during processing.
    """
    try:
        if not isinstance(input_data.config, list) or not all(
            isinstance(i, dict) for i in input_data.config
        ):
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message="Config must be a list of dictionaries.",
                    error="Invalid input format",
                    query=str(request.url),
                ).model_dump(),
                status_code=400,
            )
        dataset_id = input_data.dataset_id
        cluster_info = DATASETS.get(dataset_id)

        if not cluster_info:
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message=f"Invalid dataset_id: {dataset_id}",
                    error="Dataset not found",
                    query=str(request.url),
                ).model_dump(),
                status_code=404,
            )

        KINFIN_WORKDIR = os.getenv("KINFIN_WORKDIR")
        cluster_path = os.path.join(KINFIN_WORKDIR, cluster_info["path"])

        cluster_f = os.path.join(cluster_path, "Orthogroups.txt")
        sequence_ids_f = os.path.join(cluster_path, "kinfin.SequenceIDs.txt")
        taxon_idx_mapping_file = os.path.join(cluster_path, "taxon_idx_mapping.json")
        species_id = os.path.join(cluster_path, "kinfin.SpeciesIDs.txt")
        fasta_dir = os.path.join(cluster_path, "fastas")
        tree = os.path.join(cluster_path, "kinfin.tree.nwk")
        annotations = os.path.join(cluster_path, "kinfin.functional_annotation.txt")

        try:
            check_file(cluster_f, install_kinfin=True)
            check_file(sequence_ids_f, install_kinfin=True)
            check_file(taxon_idx_mapping_file, install_kinfin=True)
        except FileNotFoundError as e:
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message="Missing dataset file(s)",
                    error=str(e),
                    query=str(request.url),
                ).model_dump(),
                status_code=400,
            )

        session_id, result_dir = query_manager.get_or_create_session(input_data.config)
        config_f = os.path.join(result_dir, "config.json")
        with open(config_f, "w") as file:
            json.dump(input_data.config, file)

        command = [
            "python",
            "src_new/src/main.py",
            "analysis",
            "-g",
            cluster_f,
            "-c",
            config_f,
            "-s",
            sequence_ids_f,
            "-m",
            taxon_idx_mapping_file,
            "-d",
            result_dir,
            "-l",
            "png",
        ]
        if (input_data.isAdvanced) :
            command.extend([
                "-S", species_id,
                "-f", fasta_dir,
                "-t", tree,
                "-a", annotations,
            ])

        status_file = os.path.join(result_dir, f"{session_id}.status")
        asyncio.create_task(run_cli_command(command, status_file))

        return JSONResponse(
            content=ResponseSchema(
                status="success",
                message="Analysis task has been queued.",
                data={"session_id": session_id},
                query=str(request.url),
            ).model_dump(),
            status_code=202,
        )
    except Exception as e:
        return JSONResponse(
            content=ResponseSchema(
                status="error",
                message="Internal Server Error",
                query=str(request.url),
                error=str(e),
            ).model_dump(),
            status_code=500,
        )


@router.get("/kinfin/status", response_model=ResponseSchema)
@limiter.limit(LIMIT_STANDARD)
@check_kinfin_session
async def get_run_status(request: Request, session_id: str = Depends(header_scheme)):
    try:
        return JSONResponse(
            content=ResponseSchema(
                status="success",
                message="Kinfin analysis is complete.",
                data={"is_complete": True},
                query=str(request.url),
            ).model_dump(),
            status_code=200,
        )

    except Exception as e:
        print(e)
        return JSONResponse(
            content=ResponseSchema(
                status="error",
                message="Internal Server Error",
                query=str(request.url),
                error=str(e),
            ).model_dump(),
            status_code=500,
        )


@router.post("/kinfin/status", response_model=ResponseSchema)
@limiter.limit(LIMIT_STANDARD)
async def get_batch_status(request: Request, session_ids: List[str] = Body(...)):
    try:
        statuses = [get_session_status(session_id) for session_id in session_ids]
        return JSONResponse(
            content=ResponseSchema(
                status="success",
                message="Batch session status fetched successfully.",
                data={"sessions": statuses},
                query=str(request.url),
            ).model_dump(),
            status_code=200,
        )
    except Exception as e:
        LOGGER.error(f"Error in batch status check: {str(e)}", exc_info=True)
        return JSONResponse(
            content=ResponseSchema(
                status="error",
                message="Internal Server Error",
                error=str(e),
                query=str(request.url),
            ).model_dump(),
            status_code=500,
        )


@router.get("/kinfin/run-summary", response_model=ResponseSchema)
@limiter.limit(LIMIT_STANDARD)
@check_kinfin_session
async def get_run_summary(
    request: Request,
    session_id: str = Depends(header_scheme),
    detailed: Optional[bool] = Query(False),
):
    try:
        result_dir = query_manager.get_session_dir(session_id)
        filepath = os.path.join(result_dir, RUN_SUMMARY_FILEPATH)
        if not os.path.exists(filepath):
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message=f"{RUN_SUMMARY_FILEPATH} File Not Found",
                    error="File does not exist",
                    query=str(request.url),
                ).model_dump(),
                status_code=404,
            )

        with open(filepath, "r") as f:
            data = json.load(f)

        if not detailed:
            data = {
                k: v
                for k, v in data.items()
                if k not in ["included_proteins", "excluded_proteins"]
            }

        response = ResponseSchema(
            status="success",
            message="Run summary retrieved successfully.",
            query=str(request.url),
            data=data,
        )
        return JSONResponse(content=response.model_dump())
    except Exception as e:
        print(e)
        return JSONResponse(
            content=ResponseSchema(
                status="error",
                message="Internal Server Error",
                query=str(request.url),
                error=str(e),
            ).model_dump(),
            status_code=500,
        )


@router.get("/kinfin/counts-by-taxon", response_model=ResponseSchema)
@limiter.limit(LIMIT_STANDARD)
@check_kinfin_session
async def get_counts_by_tanon(
    request: Request,
    session_id: str = Depends(header_scheme),
    include_clusters: Optional[str] = Query(None),
    exclude_clusters: Optional[str] = Query(None),
    min_count: Optional[int] = Query(None),
    max_count: Optional[int] = Query(None),
    include_taxons: Optional[str] = Query(None),
    exclude_taxons: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_order: Optional[str] = Query("asc"),
    page: Optional[int] = Query(1),
    size: Optional[int] = Query(10),
):
    try:
        result_dir = query_manager.get_session_dir(session_id)
        filepath = os.path.join(result_dir, COUNTS_FILEPATH)

        if not os.path.exists(filepath):
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message=f"{RUN_SUMMARY_FILEPATH} File Not Found",
                    error="File does not exist",
                    query=str(request.url),
                ).model_dump(),
                status_code=404,
            )

        result = parse_taxon_counts_file(
            filepath,
            include_clusters,
            exclude_clusters,
            include_taxons,
            exclude_taxons,
            min_count,
            max_count,
        )

        paginated_result, total_pages = sort_and_paginate_result(
            result,
            sort_by,
            sort_order,
            page,
            size,
        )

        response = ResponseSchema(
            status="success",
            message="Cluster counts by Taxon retrieved successfully",
            data=paginated_result,
            query=str(request.url),
            current_page=page,
            entries_per_page=size,
            total_pages=total_pages,
        )
        return JSONResponse(response.model_dump())
    except Exception as e:
        print(e)
        return JSONResponse(
            content=ResponseSchema(
                status="error",
                message="Internal Server Error",
                query=str(request.url),
                error=str(e),
            ).model_dump(),
            status_code=500,
        )


@router.get("/kinfin/cluster-summary/{attribute}", response_model=ResponseSchema)
@limiter.limit(LIMIT_STANDARD)
@check_kinfin_session
async def get_cluster_summary(
    request: Request,
    attribute: str,
    session_id: str = Depends(header_scheme),
    include_clusters: Optional[str] = Query(None),
    exclude_clusters: Optional[str] = Query(None),
    include_properties: Optional[str] = Query(None),
    exclude_properties: Optional[str] = Query(None),
    min_cluster_protein_count: Optional[int] = Query(None),
    max_cluster_protein_count: Optional[int] = Query(None),
    min_protein_median_count: Optional[float] = Query(None),
    max_protein_median_count: Optional[float] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_order: Optional[str] = Query("asc"),
    page: Optional[int] = Query(1),
    size: Optional[int] = Query(10),
    as_file: Optional[bool] = Query(False),
    CS_code: Optional[List[str]] = Query(None, alias="CS_code"),   # ✅ only one param
) -> JSONResponse:
    try:
        result_dir = query_manager.get_session_dir(session_id)
        config_f = os.path.join(result_dir, "config.json")
        if not os.path.exists(config_f):
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message="Kinfin analysis not initialized",
                    error="session_not_initialized",
                    query=str(request.url),
                ).model_dump(),
                status_code=428,
            )

        valid_endpoints = extract_attributes_and_taxon_sets(result_dir)
        valid_attributes = valid_endpoints["attributes"]

        if attribute and attribute not in valid_attributes:
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message=f"Invalid attribute: {attribute}. Must be one of {valid_attributes}.",
                    error="Invalid Input",
                ).model_dump(),
                status_code=400,
            )

        filename = f"{attribute}/{attribute}.{CLUSTER_SUMMARY_FILENAME}"
        filepath = os.path.join(result_dir, filename)

        if not os.path.exists(filepath):
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message=f"{COUNTS_FILEPATH} File Not Found",
                    error="File does not exist",
                    query=str(request.url),
                ).model_dump(),
                status_code=404,
            )

        # --- Parse file ---
        result = parse_cluster_summary_file(
            filepath=filepath,
            include_clusters=include_clusters,
            exclude_clusters=exclude_clusters,
            include_properties=include_properties,
            exclude_properties=exclude_properties,
            min_cluster_protein_count=min_cluster_protein_count,
            max_cluster_protein_count=max_cluster_protein_count,
            min_protein_median_count=min_protein_median_count,
            max_protein_median_count=max_protein_median_count,
        )

        # --- Flatten rows ---
        flat_result = {k: flatten_dict(v) for k, v in result.items()}

        # --- Load descriptions once ---
        current_dir = os.path.dirname(os.path.abspath(__file__))
        descriptions_file_path = os.path.join(current_dir, "column_descriptions.json")
        with open(descriptions_file_path, "r") as f:
            column_descriptions = json.load(f)

        code_to_column = {item["code"]: item["name"] for item in column_descriptions}
        code_to_alias = {item["code"]: item.get("alias", item["name"]) for item in column_descriptions}
        if CS_code:
            # === OPTIMIZED: build the global key set ONCE ===
            all_keys_ordered: List[str] = []
            seen_keys = set()
            for row in flat_result.values():
                for k in row.keys():
                    if k not in seen_keys:
                        seen_keys.add(k)
                        all_keys_ordered.append(k)

            selected_columns: List[str] = []
            selected_set = set()
            column_aliases = {}

            # First handle non-dynamic columns (no X)
            for code in CS_code:
                name = code_to_column.get(code)
                if not name:
                    continue
                alias_template = code_to_alias.get(code, name)
                if "X" not in name:
                    flat_name = name.replace(".", "_")
                    if flat_name not in selected_set:
                        selected_columns.append(flat_name)
                        selected_set.add(flat_name)
                        column_aliases[flat_name] = alias_template

            # Then handle dynamic columns (with X)
            compiled_patterns = []
            for code in CS_code:
                name = code_to_column.get(code)
                if not name or "X" not in name:
                    continue
                pat = re.compile("^" + name.replace("X", "(.+)") + "$")
                compiled_patterns.append((pat, code_to_alias.get(code, name)))

            for key, (pat, alias_template) in itertools.product(all_keys_ordered, compiled_patterns):
                m = pat.match(key)
                if m and key not in selected_set:
                    selected_columns.append(key)
                    selected_set.add(key)
                    column_aliases[key] = alias_template.replace("X", m.group(1))

            # Keep only selected columns; fill missing with "-"
            flat_result = {
                rid: {col: row.get(col, "-") for col in selected_columns}
                for rid, row in flat_result.items()
            }

        # --- File Download ---
        if as_file:
            if not flat_result:
                return JSONResponse(
                    content=ResponseSchema(
                        status="error",
                        message="No data available for download.",
                        error="no_data",
                        query=str(request.url),
                    ).model_dump(),
                    status_code=404,
                )
            try:
                rows = list(flat_result.values())
                fieldnames = list(rows[0].keys()) if rows else []
                buffer = io.StringIO()
                writer = csv.DictWriter(buffer, fieldnames=fieldnames, delimiter="\t")
                writer.writeheader()
                writer.writerows(rows)
                buffer.seek(0)
                return StreamingResponse(
                    buffer,
                    media_type="text/tab-separated-values",
                    headers={"Content-Disposition": f"attachment; filename={attribute}_cluster_summary.tsv"},
                )
            except Exception as e:
                return JSONResponse(
                    content=ResponseSchema(
                        status="error",
                        message="Failed to generate TSV file",
                        error=str(e),
                        query=str(request.url),
                    ).model_dump(),
                    status_code=500,
                )

        # --- Sort & paginate flattened result ---
        paginated_result, total_pages = sort_and_paginate_result(
            flat_result, sort_by, sort_order, page, size
        )

        response = ResponseSchema(
            status="success",
            message="Cluster summary retrieved successfully",
            data=paginated_result,
            query=str(request.url),
            current_page=page,
            entries_per_page=size,
            total_pages=total_pages,
        )
        return JSONResponse(response.model_dump())

    except Exception as e:
        print(e)
        return JSONResponse(
            content=ResponseSchema(
                status="error",
                message="Internal Server Error",
                query=str(request.url),
                error=str(e),
            ).model_dump(),
            status_code=500,
        )


@router.get("/kinfin/available-attributes-taxonsets")
@limiter.limit(LIMIT_STANDARD)
@check_kinfin_session
async def get_available_attributes_and_taxon_sets(
    request: Request,
    session_id: str = Depends(header_scheme),
):
    try:
        result_dir = query_manager.get_session_dir(session_id)
        result = extract_attributes_and_taxon_sets(result_dir)
        return JSONResponse(
            content=ResponseSchema(
                status="success",
                message="List of available attributes and taxon sets fetched",
                data=result,
                query=str(request.url),
            ).model_dump(),
            status_code=200,
        )
    except Exception as e:
        print(e)
        return JSONResponse(
            content=ResponseSchema(
                status="error",
                message="Internal Server Error",
                query=str(request.url),
                error=str(e),
            ).model_dump(),
            status_code=500,
        )


@router.get("/kinfin/valid-proteome-ids", response_model=ResponseSchema)
@limiter.limit(LIMIT_STANDARD)
async def get_valid_taxons_api(
    request: Request,
    dataset_id: str | None = Query(None),
    clusterId: str | None = Query(None, include_in_schema=False),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
):
    try:
        dataset_id = dataset_id or clusterId
        if not dataset_id:
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message="Missing dataset_id query parameter",
                    error="Field required",
                    query=str(request.url),
                ).model_dump(),
                status_code=422,
            )

        cluster_info = DATASETS.get(dataset_id)
        if not cluster_info:
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message=f"Invalid dataset_id: {dataset_id}",
                    error="Dataset not found",
                    query=str(request.url),
                ).model_dump(),
                status_code=404,
            )

        KINFIN_WORKDIR = os.getenv("KINFIN_WORKDIR")
        cluster_path = os.path.join(KINFIN_WORKDIR, cluster_info["path"])
        taxon_idx_mapping_file = os.path.join(cluster_path, "taxon_idx_mapping.json")
        try:
            check_file(taxon_idx_mapping_file, install_kinfin=True)
        except FileNotFoundError as e:
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message="Missing dataset file(s)",
                    error=str(e),
                    query=str(request.url),
                ).model_dump(),
                status_code=400,
            )

        taxons = await asyncio.to_thread(
            parse_valid_proteome_ids_file, taxon_idx_mapping_file
        )
    except FileNotFoundError as e:
        LOGGER.error("Taxon file not found", exc_info=True)
        return JSONResponse(
            content=ResponseSchema(
                status="error",
                message="Taxon index file not found",
                query=str(request.url),
                error=str(e),
            ).model_dump(),
            status_code=404,
        )
    except ValueError as e:
        LOGGER.error("Error parsing taxon index file", exc_info=True)
        return JSONResponse(
            content=ResponseSchema(
                status="error",
                message="Error parsing taxon index file",
                query=str(request.url),
                error=str(e),
            ).model_dump(),
            status_code=422,
        )
    except Exception as e:
        LOGGER.error("Error fetching valid taxons", exc_info=True)
        return JSONResponse(
            content=ResponseSchema(
                status="error",
                message="Internal Server Error",
                query=str(request.url),
                error=str(e),
            ).model_dump(),
            status_code=500,
        )

    items = list(taxons.items())
    total_items = len(items)
    total_pages = (total_items + size - 1) // size
    start = (page - 1) * size
    end = start + size
    paginated_items = dict(items[start:end])

    response = ResponseSchema(
        status="success",
        message="List of valid proteome IDs fetched",
        data=paginated_items,
        query=str(request.url),
        current_page=page,
        entries_per_page=size,
        total_pages=total_pages,
    )
    return JSONResponse(response.model_dump(), status_code=200)


@router.get("/kinfin/datasets", response_model=ResponseSchema)
@limiter.limit(LIMIT_STANDARD)
async def get_datasets_api(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
):
    try:
        clustering_file_path = os.getenv("KINFIN_CLUSTERING_FILE")
        if not clustering_file_path:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            clustering_file_path = os.path.join(current_dir, "clustering.json")

        dataset_data = await asyncio.to_thread(
            parse_clustering_file, clustering_file_path
        )
    except FileNotFoundError as e:
        LOGGER.error("Dataset file not found", exc_info=True)
        return JSONResponse(
            content=ResponseSchema(
                status="error",
                message="Dataset file not found",
                query=str(request.url),
                error=str(e),
            ).model_dump(),
            status_code=404,
        )
    except ValueError as e:
        LOGGER.error("Error parsing dataset file", exc_info=True)
        return JSONResponse(
            content=ResponseSchema(
                status="error",
                message="Error parsing dataset file",
                query=str(request.url),
                error=str(e),
            ).model_dump(),
            status_code=422,
        )
    except Exception as e:
        LOGGER.error("Error fetching datasets", exc_info=True)
        return JSONResponse(
            content=ResponseSchema(
                status="error",
                message="Internal Server Error",
                query=str(request.url),
                error=str(e),
            ).model_dump(),
            status_code=500,
        )

    total_items = len(dataset_data)
    total_pages = (total_items + size - 1) // size
    start = (page - 1) * size
    end = start + size
    paginated_data = dataset_data[start:end]

    # TODO: validate current page datasets and cache for future fetches
    for dataset in paginated_data:
        if dataset_id := dataset.get("id"):
            default_status = derive_run_status(dataset_id)
            dataset["status"] = default_status["state"]
        else:
            dataset["status"] = "unknown"

    response = ResponseSchema(
        status="success",
        message="Datasets fetched successfully",
        data=paginated_data,
        query=str(request.url),
        current_page=page,
        entries_per_page=size,
        total_pages=total_pages,
    )
    return JSONResponse(response.model_dump(), status_code=200)


@router.get("/kinfin/column-descriptions", response_model=ResponseSchema)
async def get_column_descriptions_api(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(40, ge=1, le=100),
    sort_by: str = Query(None, description="Comma-separated fields to sort by"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort order: asc or desc"),
    file: str = Query(None, description="Filter by file name"),
):
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        descriptions_file_path = os.path.join(current_dir, "column_descriptions.json")
        column_data = await asyncio.to_thread(read_json_file, descriptions_file_path)
    except FileNotFoundError as e:
        LOGGER.error("Column descriptions file not found", exc_info=True)
        return JSONResponse(
            content=ResponseSchema(
                status="error",
                message="Column descriptions file not found",
                query=str(request.url),
                error=str(e),
            ).model_dump(),
            status_code=404,
        )
    except ValueError as e:
        LOGGER.error("Error parsing column descriptions file", exc_info=True)
        return JSONResponse(
            content=ResponseSchema(
                status="error",
                message="Error parsing column descriptions file",
                query=str(request.url),
                error=str(e),
            ).model_dump(),
            status_code=422,
        )
    except Exception as e:
        LOGGER.error("Error fetching column descriptions", exc_info=True)
        return JSONResponse(
            content=ResponseSchema(
                status="error",
                message="Internal Server Error",
                query=str(request.url),
                error=str(e),
            ).model_dump(),
            status_code=500,
        )

    if file:
        column_data = [row for row in column_data if row.get("file") == file]
    data_dict = {str(i): row for i, row in enumerate(column_data)}

    paginated_data_dict, total_pages = sort_and_paginate_result(
        result=data_dict,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        size=size,
    )

    paginated_data = list(paginated_data_dict.values())

    response = ResponseSchema(
        status="success",
        message="Column descriptions fetched successfully",
        data=paginated_data,
        query=str(request.url),
        current_page=page,
        entries_per_page=size,
        total_pages=total_pages,
    )
    return JSONResponse(response.model_dump(), status_code=200)


@router.get("/kinfin/attribute-summary/{attribute}", response_model=ResponseSchema)
@limiter.limit(LIMIT_STANDARD)
@check_kinfin_session
async def get_attribute_summary(
    request: Request,
    attribute: str,
    session_id: str = Depends(header_scheme),
    sort_by: Optional[str] = Query(None),
    sort_order: Optional[str] = Query("asc"),
    page: Optional[int] = Query(1),
    size: Optional[int] = Query(10),
    as_file: Optional[bool] = Query(False),
    AS_code: Optional[List[str]] = Query(None, alias="AS_code"),
):
    try:
        # ---- Validate Kinfin session ----
        result_dir = query_manager.get_session_dir(session_id)
        config_f = os.path.join(result_dir, "config.json")
        if not os.path.exists(config_f):
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message="Kinfin analysis not initialized",
                    error="session_not_initialized",
                    query=str(request.url),
                ).model_dump(),
                status_code=428,
            )

        # ---- Validate attribute ----
        valid_endpoints = extract_attributes_and_taxon_sets(result_dir)
        valid_attributes = valid_endpoints["attributes"]
        if attribute and attribute not in valid_attributes:
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message=f"Invalid attribute: {attribute}. Must be one of {valid_attributes}.",
                    error="Invalid Input",
                ).model_dump(),
                status_code=400,
            )

        # ---- Load mapping file ----
        current_dir = os.path.dirname(os.path.abspath(__file__))
        descriptions_file_path = os.path.join(current_dir, "column_descriptions.json")
        with open(descriptions_file_path, "r") as f:
            column_descriptions = json.load(f)
        code_to_column = {item["code"]: item["name"] for item in column_descriptions}

        # ---- Read attribute file ----
        filename = f"{attribute}/{attribute}.{ATTRIBUTE_METRICS_FILENAME}"
        filepath = os.path.join(result_dir, filename)
        if not os.path.exists(filepath):
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message=f"{COUNTS_FILEPATH} File Not Found",
                    error="File does not exist",
                    query=str(request.url),
                ).model_dump(),
                status_code=404,
            )

        # ---- Parse flattened attribute summary directly ----
        result = parse_attribute_summary_file(filepath=filepath)

        # ---- Apply AS_code filter ----
        if AS_code:
            selected_columns = []
            for code in AS_code:
                if code in code_to_column:
                    col_name = code_to_column[code]
                    flat_name = col_name.replace(".", "_")
                    selected_columns.append(flat_name)

            result = {
                k: {col: v.get(col, "-") for col in selected_columns}
                for k, v in result.items()
            }

        # ---- File download mode ----
        if as_file:
            if not result:
                return ResponseSchema(
                    status="error",
                    message="No data available for download.",
                    error="no_data",
                    query=str(request.url),
                ).to_json_response(status_code=404)

            rows = list(result.values())
            fieldnames = list(result[next(iter(result))].keys()) if rows else []

            buffer = io.StringIO()
            writer = csv.DictWriter(buffer, fieldnames=fieldnames, delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)
            buffer.seek(0)

            return StreamingResponse(
                buffer,
                media_type="text/tab-separated-values",
                headers={
                    "Content-Disposition": f"attachment; filename={attribute}_attribute_summary.tsv"
                },
            )

        # ---- Paginate ----
        paginated_result, total_pages = sort_and_paginate_result(
            result,
            sort_by,
            sort_order,
            page,
            size,
        )

        return JSONResponse(
            ResponseSchema(
                status="success",
                message="Attribute summary retrieved successfully",
                data=paginated_result,
                query=str(request.url),
                current_page=page,
                entries_per_page=size,
                total_pages=total_pages,
            ).model_dump()
        )

    except Exception as e:
        print(e)
        return JSONResponse(
            content=ResponseSchema(
                status="error",
                message="Internal Server Error",
                query=str(request.url),
                error=str(e),
            ).model_dump(),
            status_code=500,
        )


@router.get(
    "/kinfin/cluster-metrics/{attribute}/{taxon_set}",
    response_model=ResponseSchema,
)
@limiter.limit(LIMIT_STANDARD)
@check_kinfin_session
async def get_cluster_metrics(
    request: Request,
    attribute: str,
    taxon_set: str,
    session_id: str = Depends(header_scheme),
    cluster_status: Optional[str] = Query(None),
    cluster_type: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_order: Optional[str] = Query("asc"),
    page: Optional[int] = Query(1),
    size: Optional[int] = Query(10),
    as_file: Optional[bool] = Query(False),
    CM_code: Optional[List[str]] = Query(None, alias="CM_code"),
):
    try:
        # ---- Validate Kinfin session ----
        result_dir = query_manager.get_session_dir(session_id)
        config_f = os.path.join(result_dir, "config.json")
        if not os.path.exists(config_f):
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message="Kinfin analysis not initialized",
                    error="session_not_initialized",
                    query=str(request.url),
                ).model_dump(),
                status_code=428,
            )

        # ---- Validate attribute & taxon_set ----
        valid_endpoints = extract_attributes_and_taxon_sets(result_dir)
        valid_attributes = valid_endpoints["attributes"]

        if taxon_set == "all":
            attribute = "all"

        if attribute and attribute not in valid_attributes:
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message=f"Invalid attribute: {attribute}. Must be one of {valid_attributes}.",
                    error="Invalid Input",
                ).model_dump(),
                status_code=400,
            )

        valid_taxon_sets = valid_endpoints["taxon_set"][attribute]
        if taxon_set and taxon_set not in valid_taxon_sets:
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message=f"Invalid taxon set: {taxon_set}. Must be one of {valid_taxon_sets}.",
                    error="Invalid Input",
                ).model_dump(),
                status_code=400,
            )

        # ---- Load column descriptions (for CM_code) ----
        current_dir = os.path.dirname(os.path.abspath(__file__))
        descriptions_file_path = os.path.join(current_dir, "column_descriptions.json")
        with open(descriptions_file_path, "r") as f:
            column_descriptions = json.load(f)
        code_to_column = {item["code"]: item["name"] for item in column_descriptions}

        # ---- Parse cluster metrics file (already formatted & flat) ----
        filename = f"{attribute}/{attribute}.{taxon_set}.{CLUSTER_METRICS_FILENAME}"
        filepath = os.path.join(result_dir, filename)
        if not os.path.exists(filepath):
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message=f"{CLUSTER_METRICS_FILENAME} File Not Found",
                    error="File does not exist",
                    query=str(request.url),
                ).model_dump(),
                status_code=404,
            )

        result = parse_cluster_metrics_file(filepath, cluster_status, cluster_type)
        rows = list(result.values())

        # ---- Apply CM_code filter ----
        if CM_code:
            selected_columns = [code_to_column[code] for code in CM_code if code in code_to_column]

            # Ensure cluster_id is always included
            if "cluster_id" not in selected_columns:
                selected_columns.insert(0, "cluster_id")

            rows = [
                {col: row.get(col, "-") for col in selected_columns}
                for row in rows
            ]

        # ---- File download mode ----
        if as_file:
            if not rows:
                return JSONResponse(
                    content=ResponseSchema(
                        status="error",
                        message="No data available for download.",
                        error="no_data",
                        query=str(request.url),
                    ).model_dump(),
                    status_code=404,
                )

            buffer = io.StringIO()
            writer = csv.DictWriter(buffer, fieldnames=rows[0].keys(), delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)
            buffer.seek(0)

            return StreamingResponse(
                buffer,
                media_type="text/tab-separated-values",
                headers={
                    "Content-Disposition": f"attachment; filename={attribute}_{taxon_set}_cluster_metrics.tsv"
                },
            )

        # ---- Paginate ----
        flat_dict = {rows[i]["cluster_id"]: rows[i] for i in range(len(rows))}
        paginated_result, total_pages = sort_and_paginate_result(
            flat_dict,
            sort_by,
            sort_order,
            page,
            size,
        )

        return JSONResponse(
            ResponseSchema(
                status="success",
                message="Cluster metrics retrieved successfully",
                data=paginated_result,
                query=str(request.url),
                current_page=page,
                entries_per_page=size,
                total_pages=total_pages,
            ).model_dump()
        )

    except Exception as e:
        return JSONResponse(
            content=ResponseSchema(
                status="error",
                message="Internal Server Error",
                query=str(request.url),
                error=str(e),
            ).model_dump(),
            status_code=500,
        )


@router.get(
    "/kinfin/pairwise-analysis/{attribute}",
    response_model=ResponseSchema,
)
@limiter.limit(LIMIT_STANDARD)
@check_kinfin_session
async def get_pairwise_analysis(
    request: Request,
    attribute: str,
    session_id: str = Depends(header_scheme),
    taxon_1: Optional[str] = Query(None),
    taxon_2: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_order: Optional[str] = Query("asc"),
    page: Optional[int] = Query(1),
    size: Optional[int] = Query(10),
):
    try:
        result_dir = query_manager.get_session_dir(session_id)
        config_f = os.path.join(result_dir, "config.json")
        if not os.path.exists(config_f):
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message="Kinfin analysis not initialized",
                    error="session_not_initialized",
                    query=str(request.url),
                ).model_dump(),
                status_code=428,
            )

        valid_endpoints = extract_attributes_and_taxon_sets(result_dir)
        valid_attributes = valid_endpoints["attributes"]

        if attribute and attribute not in valid_attributes:
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message=f"Invalid attribute: {attribute}. Must be one of {valid_attributes}.",
                    error="Invalid Input",
                ).model_dump(),
                status_code=400,
            )

        filename = f"{attribute}/{attribute}.{PAIRWISE_ANALYSIS_FILE}"
        filepath = os.path.join(result_dir, filename)

        if not os.path.exists(filepath):
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message=f"{PAIRWISE_ANALYSIS_FILE} File Not Found",
                    error="File does not exist",
                    query=str(request.url),
                ).model_dump(),
                status_code=404,
            )

        result = parse_pairwise_file(filepath, taxon_1, taxon_2)

        if isinstance(result, list):
            result = {str(i): item for i, item in enumerate(result)}
        paginated_result, total_pages = sort_and_paginate_result(
            result,
            sort_by,
            sort_order,
            page,
            size,
        )

        response = ResponseSchema(
            status="success",
            message="Pairwise analysis retrieved successfully",
            data=paginated_result,
            query=str(request.url),
            current_page=page,
            entries_per_page=size,
            total_pages=total_pages,
        )

        return JSONResponse(response.model_dump())

    except Exception as e:
        print(e)
        return JSONResponse(
            content=ResponseSchema(
                status="error",
                message="Internal Server Error",
                query=str(request.url),
                error=str(e),
            ).model_dump(),
            status_code=500,
        )


@router.get("/kinfin/plot/{attribute}/{plot_type}")
@check_kinfin_session
@limiter.limit(LIMIT_STANDARD)
async def get_plot(
    request: Request,
    attribute: str,
    plot_type: str,
    session_id: str = Depends(header_scheme),
) -> FileResponse:
    """
    Retrieve a specific plot type for a given session.

    Args:
        attribute (str): The attribute associated with the plot.
        plot_type (str): The type of plot to retrieve.
        session_id (str): The session ID for authentication.

    Returns:
        FileResponse: The requested plot file.

    Raises:
        HTTPException: If the plot type is invalid, session ID is invalid, or the file is not found.
    """
    try:
        if plot_type not in ["cluster-size-distribution", "rarefaction-curve"]:
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message="Invalid Plot Type",
                    error="invalid_plot_type",
                    query=str(request.url),
                ).model_dump(),
                status_code=404,
            )

        result_dir = query_manager.get_session_dir(session_id)
        filepath: str = ""
        match plot_type:
            case "cluster-size-distribution":
                filepath = "cluster_size_distribution.png"
            case "rarefaction-curve":
                filepath = f"{attribute}/{attribute}.rarefaction_curve.png"
            case _:
                return JSONResponse(
                    content=ResponseSchema(
                        status="error",
                        message="Invalid Plot Type",
                        error="invalid_plot_type",
                        query=str(request.url),
                    ).model_dump(),
                    status_code=404,
                )

        filepath = os.path.join(result_dir, filepath)

        if not os.path.exists(filepath):
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message="Plot not found",
                    error="plot_not_found",
                    query=str(request.url),
                ).model_dump(),
                status_code=404,
            )

        return FileResponse(
            filepath,
            media_type="image/png",
            headers={"Content-Disposition": "inline"},
        )
    except HTTPException as e:
        print(e)
        return JSONResponse(
            content=ResponseSchema(
                status="error",
                message=e.detail,
                query=str(request.url),
            ).model_dump(),
            status_code=e.status_code,
        )
    except Exception as e:
        print(e)
        return JSONResponse(
            content=ResponseSchema(
                status="error",
                message="Internal Server Error",
                error=str(e),
                query=str(request.url),
            ).model_dump(),
            status_code=500,
        )


class PartitionResolveRequest(BaseModel):
    dataset_id: str = Field(..., description="Dataset id")
    partition_set: Dict[str, List[str]] = Field(
        ..., description="Dictionary mapping partition names to lists of cluster IDs"
    )
    validate_partition_set: Optional[bool] = Field(
        True,
        validation_alias=AliasChoices("validate_partition_set", "validate"),
        serialization_alias="validate_partition_set",
        description="Whether to validate the partition set before resolving",
    )


class PartitionStatusPayload(BaseModel):
    dataset_id: str
    partition_id: str
    status: Literal["missing", "initialising", "ready", "error", "expired"]
    message: str
    updated_at: Optional[str] = None
    expires_at: Optional[str] = None
    details: Dict[str, Any] = {}


@router.post("/kinfin/partitions/resolve", response_model=ResponseSchema)
async def resolve_partition_set(payload: PartitionResolveRequest, request: Request):
    try:
        dataset_id = payload.dataset_id
        partition_set = payload.partition_set
        validate = payload.validate_partition_set

        if validate:
            is_valid, error_message = validate_partition_dict(dataset_id, partition_set)
            if not is_valid:
                return JSONResponse(
                    content=ResponseSchema(
                        status="error",
                        message="Invalid partition set",
                        error=error_message,
                        query=str(request.url),
                    ).model_dump(),
                    status_code=400,
                )

        partition_id, key_map = partition_selection_to_id(partition_set)
        status = read_run_status_file(dataset_id, partition_id)

        return JSONResponse(
            content=ResponseSchema(
                status="success",
                message="Partition set resolved successfully.",
                data={
                    "dataset_id": dataset_id,
                    "partition_id": partition_id,
                    "key_map": key_map,
                    "status": status.get("state", "missing"),
                    "message": status.get("message", ""),
                    "updated_at": status.get("updated_at"),
                    "expires_at": status.get("expires_at"),
                },
                query=str(request.url),
            ).model_dump(),
            status_code=200,
        )
    except Exception as e:
        return JSONResponse(
            content=ResponseSchema(
                status="error",
                message="Internal Server Error",
                error=str(e),
                query=str(request.url),
            ).model_dump(),
            status_code=500,
        )


@router.get(
    "/kinfin/datasets/{dataset_id}/partitions/{partition_id}/status",
    response_model=ResponseSchema,
)
async def get_partition_status_by_id(
    request: Request,
    dataset_id: str,
    partition_id: str,
):
    try:
        status = read_run_status_file(dataset_id, partition_id)

        if status.get("state", "missing") == "missing" and not status.get("run_exists", False):
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message="Partition not found for this dataset.",
                    error="partition_not_found",
                    query=str(request.url),
                ).model_dump(),
                status_code=404,
            )

        return JSONResponse(
            content=ResponseSchema(
                status="success",
                message="Partition status retrieved successfully.",
                data={
                    "dataset_id": dataset_id,
                    "partition_id": partition_id,
                    "status": status.get("state", "missing"),
                    "message": status.get("message", ""),
                    "updated_at": status.get("updated_at"),
                    "expires_at": status.get("expires_at"),
                    "details": status.get("details", {}),
                },
                query=str(request.url),
            ).model_dump(),
            status_code=200,
        )
    except Exception as e:
        return JSONResponse(
            content=ResponseSchema(
                status="error",
                message="Internal Server Error",
                error=str(e),
                query=str(request.url),
            ).model_dump(),
            status_code=500,
        )


class PartitionStatusBatchRequest(BaseModel):
    dataset_id: str
    partition_ids: List[str]


@router.post("/kinfin/datasets/{dataset_id}/init", response_model=ResponseSchema)
@limiter.limit(LIMIT_INIT)
async def initialize_dataset_default_partition(
    request: Request,
    dataset_id: str,
    force: bool = Query(False),
):
    try:
        dataset_info = DATASETS.get(dataset_id)
        if not dataset_info:
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message=f"Invalid dataset_id: {dataset_id}",
                    error="Dataset not found",
                    query=str(request.url),
                ).model_dump(),
                status_code=404,
            )

        partition_set = dataset_info.get("default_partition_set")
        if not partition_set:
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message="Dataset has no default partition set.",
                    error="default_partition_set_not_configured",
                    query=str(request.url),
                ).model_dump(),
                status_code=400,
            )

        if dataset_info.get("valid_members"):
            is_valid, error_message = validate_partition_dict(
                dataset_id, partition_set
            )
        else:
            is_valid, error_message = validate_partition_set_shape(partition_set)
        if not is_valid:
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message="Invalid default partition set.",
                    error=error_message,
                    query=str(request.url),
                ).model_dump(),
                status_code=400,
            )

        partition_id, key_map = partition_selection_to_id(partition_set)
        configured_partition_id = derive_default_partition_id(dataset_id)
        if configured_partition_id and configured_partition_id != partition_id:
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message="Default partition ID does not match default partition set.",
                    error=(
                        f"Configured default_partition_id '{configured_partition_id}' "
                        f"does not match resolved ID '{partition_id}'."
                    ),
                    query=str(request.url),
                ).model_dump(),
                status_code=400,
            )

        status = read_run_status_file(dataset_id, partition_id)
        normalized_state = normalise_run_state(status.get("state", "missing"))
        if normalized_state == "ready" and not force:
            return JSONResponse(
                content=ResponseSchema(
                    status="success",
                    message="Default partition is already ready.",
                    data={
                        "dataset_id": dataset_id,
                        "partition_id": partition_id,
                        "key_map": key_map,
                        "status": normalized_state,
                        "message": status.get("message", ""),
                        "updated_at": status.get("updated_at"),
                        "expires_at": status.get("expires_at"),
                    },
                    query=str(request.url),
                ).model_dump(),
                status_code=200,
            )
        if normalized_state == "initialising" and not force:
            return JSONResponse(
                content=ResponseSchema(
                    status="success",
                    message="Default partition analysis is already queued.",
                    data={
                        "dataset_id": dataset_id,
                        "partition_id": partition_id,
                        "key_map": key_map,
                        "status": normalized_state,
                        "message": status.get("message", ""),
                        "updated_at": status.get("updated_at"),
                    },
                    query=str(request.url),
                ).model_dump(),
                status_code=202,
            )

        try:
            status_dir = get_partition_status_dir(dataset_id, partition_id)
            status_path = get_partition_status_path(dataset_id, partition_id)
            config_path = os.path.join(status_dir, "default_partition_config.json")
            output_name = dataset_info.get("default_output_name", partition_id)
            output_dir = os.path.join(
                get_dataset_artifact_dir(dataset_id, "partition"), output_name
            )
            os.makedirs(status_dir, exist_ok=True)
            os.makedirs(output_dir, exist_ok=True)
            with open(config_path, "w") as file:
                json.dump(default_partition_config_rows(partition_set), file, indent=2)
                file.write("\n")
            command = build_dataset_init_command(
                dataset_id=dataset_id,
                dataset_info=dataset_info,
                partition_id=partition_id,
                config_path=config_path,
                output_dir=output_dir,
                status_path=status_path,
            )
        except (FileNotFoundError, ValueError) as e:
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message="Default partition analysis could not be queued.",
                    error=str(e),
                    query=str(request.url),
                ).model_dump(),
                status_code=400,
            )

        started_at = utc_timestamp()
        write_partition_status_file(
            status_path,
            {
                "schema_version": 1,
                "run_name": "default",
                "dataset_id": dataset_id,
                "partition_id": partition_id,
                "state": "initialising",
                "message": "Default partition analysis has been queued.",
                "started_at": started_at,
                "updated_at": started_at,
                "error": None,
                "output_name": output_name,
            },
        )
        asyncio.create_task(
            run_dataset_init_command(
                command=command,
                status_path=status_path,
                dataset_id=dataset_id,
                partition_id=partition_id,
                output_name=output_name,
                started_at=started_at,
            )
        )

        return JSONResponse(
            content=ResponseSchema(
                status="success",
                message="Default partition analysis has been queued.",
                data={
                    "dataset_id": dataset_id,
                    "partition_id": partition_id,
                    "key_map": key_map,
                    "status": "initialising",
                    "status_path": status_path,
                    "config_path": config_path,
                    "output_dir": output_dir,
                },
                query=str(request.url),
            ).model_dump(),
            status_code=202,
        )
    except Exception as e:
        return JSONResponse(
            content=ResponseSchema(
                status="error",
                message="Internal Server Error",
                error=str(e),
                query=str(request.url),
            ).model_dump(),
            status_code=500,
        )


@router.post("/kinfin/partitions/status", response_model=ResponseSchema)
async def get_partition_statuses_batch(
    payload: PartitionStatusBatchRequest,
    request: Request,
):
    try:
        dataset_id = payload.dataset_id
        partition_ids = payload.partition_ids

        statuses = {
            partition_id: read_run_status_file(dataset_id, partition_id)
            for partition_id in partition_ids
        }
        response = {
            partition_id: {
                "dataset_id": dataset_id,
                "partition_id": partition_id,
                "status": status.get("state", "missing"),
                "message": status.get("message", ""),
                "updated_at": status.get("updated_at"),
                "expires_at": status.get("expires_at"),
            }
            for partition_id, status in statuses.items()
        }

        return JSONResponse(
            content=ResponseSchema(
                status="success",
                message="Partition statuses retrieved successfully.",
                data=response,
                query=str(request.url),
            ).model_dump(),
            status_code=200,
        )
    except Exception as e:
        return JSONResponse(
            content=ResponseSchema(
                status="error",
                message="Internal Server Error",
                error=str(e),
                query=str(request.url),
            ).model_dump(),
            status_code=500,
        )


@router.get("/kinfin/datasets/{dataset_id}/summary", response_model=ResponseSchema)
async def get_dataset_summary(
    request: Request,
    dataset_id: str,
    fields: Optional[List[str]] = Query(default=None),
    sort_by: Optional[str] = Query(default=None),
    sort_order: str = Query(default="asc"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1),
):
    partition_id = derive_default_partition_id(dataset_id)
    file_path = get_partition_artifact_path(
        dataset_id=dataset_id,
        partition_name=partition_id,
        artifact_type="partition",
        artifact_file="summary",
        kind="table",
    )

    df_rows, total_pages = read_table_payload(
        file_path=file_path,
        table_name="summary",
        requested_fields=fields,
        filters=[],
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        size=size,
    )

    return JSONResponse(
        content=ResponseSchema(
            status="success",
            message="Dataset summary retrieved successfully.",
            data={
                "dataset_id": dataset_id,
                "partition_id": partition_id,
                "summary": df_rows,
                "current_page": page,
                "total_pages": total_pages,
            },
            query=str(request.url),
        ).model_dump(),
        status_code=200,
    )


class DatasetSummaryRequest(BaseModel):
    dataset_id: str
    partition_id: Optional[str] = None
    fields: List[str] = Field(default_factory=list)
    filters: List[dict[str, Any]] = Field(default_factory=list)
    sort_by: Optional[str] = None
    sort_order: str = "asc"
    page: int = 1
    size: int = 20


@router.post("/kinfin/datasets/summary", response_model=ResponseSchema)
async def post_dataset_summary(payload: DatasetSummaryRequest, request: Request):
    dataset_id = payload.dataset_id
    partition_id = payload.partition_id if hasattr(payload, "partition_id") else None
    if not partition_id or partition_id == "default":
        partition_id = derive_default_partition_id(dataset_id)
    print(f"Fetching summary for dataset_id: {dataset_id}, partition_id: {partition_id}")
    file_path = get_partition_artifact_path(
        dataset_id=dataset_id,
        partition_name=partition_id,
        artifact_type="partition",
        artifact_file="summary",
        kind="table",
    )

    df_rows, total_pages = read_table_payload(
        file_path=file_path,
        table_name="summary",
        requested_fields=payload.fields,
        filters=payload.filters,
        sort_by=payload.sort_by,
        sort_order=payload.sort_order,
        page=payload.page,
        size=payload.size,
    )

    return JSONResponse(
        content=ResponseSchema(
            status="success",
            message="Dataset summary retrieved successfully.",
            data={
                "dataset_id": dataset_id,
                "partition_id": partition_id,
                "summary": df_rows,
                "current_page": payload.page,
                "total_pages": total_pages,
            },
            query=str(request.url),
        ).model_dump(),
        status_code=200,
    )


@router.get("/kinfin/datasets/{dataset_id}/tally", response_model=ResponseSchema)
async def get_dataset_tally(
    request: Request,
    dataset_id: str,
    tally_field: str = Query(default="EC"),
    sort_by: Optional[str] = Query(default=None),
    sort_order: str = Query(default="asc"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1),
):
    if tally_field not in ["EC", "SC"]:
        return JSONResponse(
            content=ResponseSchema(
                status="error",
                message=f"Invalid tally field: {tally_field}. Must be one of ['EC', 'SC'].",
                error="invalid_tally_field",
                query=str(request.url),
            ).model_dump(),
            status_code=400,
        )

    file_path = get_common_artifact_path(
        dataset_id=dataset_id,
        artifact_type="tally",
        artifact_file=f"orthogroups.{tally_field}.tally",
        kind="table",
    )

    df_rows, total_pages = read_table_payload(
        file_path=file_path,
        table_name="tally",
        requested_fields=[tally_field],
        filters=[],
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        size=size,
    )

    return JSONResponse(
        content=ResponseSchema(
            status="success",
            message="Dataset tally retrieved successfully.",
            data={
                "dataset_id": dataset_id,
                "tally": df_rows,
                "current_page": page,
                "total_pages": total_pages,
            },
            query=str(request.url),
        ).model_dump(),
        status_code=200,
    )


class DatasetTableRequest(BaseModel):
    dataset_id: str
    table_name: str = "summary"
    partition_id: Optional[str] = None
    subset: Optional[List[str]] = None
    fields: List[str] = Field(default_factory=list)
    filters: List[dict[str, Any]] = Field(default_factory=list)
    sort_by: Optional[str] = None
    sort_order: str = "asc"
    page: int = 1
    size: int = 20


@router.post("/kinfin/datasets/table", response_model=ResponseSchema)
async def post_dataset_table(payload: DatasetTableRequest, request: Request):
    dataset_id = payload.dataset_id
    partition_id = payload.partition_id if hasattr(payload, "partition_id") else None
    if not partition_id or partition_id == "default":
        partition_id = derive_default_partition_id(dataset_id)
    table_name = payload.table_name if hasattr(payload, "table_name") else "summary"
    if table_name == "partition":
        if not payload.subset or not isinstance(payload.subset, list) or len(payload.subset) != 2:
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message="Subset of cluster IDs must be provided for 'partition' table.",
                    error="missing_subset",
                    query=str(request.url),
                ).model_dump(),
                status_code=400,
            )
        table_name = f"{'_vs_'.join(payload.subset)}.partition"
    print(f"Fetching table for dataset_id: {dataset_id}, partition_id: {partition_id}")
    file_path = get_partition_artifact_path(
        dataset_id=dataset_id,
        partition_name=partition_id,
        artifact_type="partition",
        artifact_file=table_name,
        kind="table",
    )

    df_rows, total_pages = read_table_payload(
        file_path=file_path,
        table_name=payload.table_name,
        requested_fields=payload.fields,
        filters=payload.filters,
        sort_by=payload.sort_by,
        sort_order=payload.sort_order,
        page=payload.page,
        size=payload.size,
    )

    return JSONResponse(
        content=ResponseSchema(
            status="success",
            message="Dataset table retrieved successfully.",
            data={
                "dataset_id": dataset_id,
                "partition_id": partition_id,
                "table": df_rows,
                "current_page": payload.page,
                "total_pages": total_pages,
            },
            query=str(request.url),
        ).model_dump(),
        status_code=200,
    )
