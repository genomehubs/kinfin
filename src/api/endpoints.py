import asyncio
import csv
import io
import json
import logging
import os
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from api.fileparsers import (
    parse_attribute_summary_file,
    parse_cluster_metrics_file,
    parse_cluster_summary_file,
    parse_clustering_file,
    parse_pairwise_file,
    parse_taxon_counts_file,
    parse_valid_proteome_ids_file,
)
from api.sessions import query_manager
from api.utils import (
    CLUSTERING_DATASETS,
    extract_attributes_and_taxon_sets,
    flatten_dict,
    read_json_file,
    read_status,
    run_cli_command,
    sort_and_paginate_result,
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


class InputSchema(BaseModel):
    config: List[Dict[str, str]]
    clusterId: str


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
                        status="success",
                        message="Kinfin analysis not initialized",
                        error="session_not_initialized",
                        query=str(request.url),
                    ).model_dump(),
                    status_code=428,
                )

            run_status = read_status(status_file)
            status = run_status.get("status")

            if status in ["running", "pending"]:
                return JSONResponse(
                    content=ResponseSchema(
                        status="success",
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
                        data={"session_terminated_due_to_error"},
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
        cluster_info = CLUSTERING_DATASETS.get(input_data.clusterId)

        if not cluster_info:
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message=f"Invalid clusterId: {input_data.clusterId}",
                    error="Clustering not found",
                    query=str(request.url),
                ).model_dump(),
                status_code=404,
            )

        KINFIN_WORKDIR = os.getenv("KINFIN_WORKDIR")
        cluster_path = os.path.join(KINFIN_WORKDIR, cluster_info["path"])

        cluster_f = os.path.join(cluster_path, "Orthogroups.txt")
        sequence_ids_f = os.path.join(cluster_path, "kinfin.SequenceIDs.txt")
        taxon_idx_mapping_file = os.path.join(cluster_path, "taxon_idx_mapping.json")

        try:
            check_file(cluster_f, install_kinfin=True)
            check_file(sequence_ids_f, install_kinfin=True)
            check_file(taxon_idx_mapping_file, install_kinfin=True)
        except FileNotFoundError as e:
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message="Missing clustering dataset file(s)",
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
            "src/main.py",
            "analyse",
            "-g",
            cluster_f,
            "-c",
            config_f,
            "-s",
            sequence_ids_f,
            "-m",
            taxon_idx_mapping_file,
            "-o",
            result_dir,
            "--plot_format",
            "png",
        ]

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
        if as_file:
            if not result:
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
                flattened_rows = [flatten_dict(row) for row in result.values()]

                if not flattened_rows:
                    return JSONResponse(
                        content=ResponseSchema(
                            status="error",
                            message="No valid rows in data.",
                            error="empty_result",
                            query=str(request.url),
                        ).model_dump(),
                        status_code=400,
                    )

                first_row = flattened_rows[0]
                buffer = io.StringIO()
                writer = csv.DictWriter(buffer, fieldnames=first_row.keys(), delimiter="\t")
                writer.writeheader()
                writer.writerows(flattened_rows)
                buffer.seek(0)

                return StreamingResponse(
                    buffer,
                    media_type="text/tab-separated-values",
                    headers={
                        "Content-Disposition": f"attachment; filename={attribute}_cluster_summary.tsv"
                    },
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
        paginated_result, total_pages = sort_and_paginate_result(
            result,
            sort_by,
            sort_order,
            page,
            size,
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
    clusterId: str,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
):
    try:
        cluster_info = CLUSTERING_DATASETS.get(clusterId)
        if not cluster_info:
            return JSONResponse(
                content=ResponseSchema(
                    status="error",
                    message=f"Invalid clusterId: {clusterId}",
                    error="Clustering not found",
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
                    message="Missing clustering dataset file(s)",
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


@router.get("/kinfin/clustering-sets", response_model=ResponseSchema)
@limiter.limit(LIMIT_STANDARD)
async def get_clustering_sets_api(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
):
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        clustering_file_path = os.path.join(current_dir, "clustering.json")

        clustering_data = await asyncio.to_thread(
            parse_clustering_file, clustering_file_path
        )
    except FileNotFoundError as e:
        LOGGER.error("Clustering file not found", exc_info=True)
        return JSONResponse(
            content=ResponseSchema(
                status="error",
                message="Clustering file not found",
                query=str(request.url),
                error=str(e),
            ).model_dump(),
            status_code=404,
        )
    except ValueError as e:
        LOGGER.error("Error parsing clustering file", exc_info=True)
        return JSONResponse(
            content=ResponseSchema(
                status="error",
                message="Error parsing clustering file",
                query=str(request.url),
                error=str(e),
            ).model_dump(),
            status_code=422,
        )
    except Exception as e:
        LOGGER.error("Error fetching clustering sets", exc_info=True)
        return JSONResponse(
            content=ResponseSchema(
                status="error",
                message="Internal Server Error",
                query=str(request.url),
                error=str(e),
            ).model_dump(),
            status_code=500,
        )

    total_items = len(clustering_data)
    total_pages = (total_items + size - 1) // size
    start = (page - 1) * size
    end = start + size
    paginated_data = clustering_data[start:end]

    response = ResponseSchema(
        status="success",
        message="Clustering sets fetched successfully",
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

        result = parse_attribute_summary_file(filepath=filepath)

        if as_file:
            if not result:
                return ResponseSchema(
                    status="error",
                    message="No data available for download.",
                    error="no_data",
                    query=str(request.url),
                ).to_json_response(status_code=404)

            rows = list(result.values())
            flattened_rows = [flatten_dict(row) for row in rows]
            first_row = flattened_rows[0]
            buffer = io.StringIO()
            writer = csv.DictWriter(buffer, fieldnames=first_row.keys(), delimiter="\t")
            writer.writeheader()
            writer.writerows(flattened_rows)
            buffer.seek(0)

            return StreamingResponse(
                buffer,
                media_type="text/tab-separated-values",
                headers={
                    "Content-Disposition": f"attachment; filename={attribute}_attribute_summary.tsv"
                },
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
            message="Attribute summary retrieved successfully",
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

        if as_file:
            if not result:
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
                rows = list(result.values())
                flattened_rows = [flatten_dict(row) for row in rows]
                first_row = flattened_rows[0] if flattened_rows else {}

                buffer = io.StringIO()
                writer = csv.DictWriter(buffer, fieldnames=first_row.keys(), delimiter="\t")
                writer.writeheader()
                writer.writerows(flattened_rows)
                buffer.seek(0)

                return StreamingResponse(
                    buffer,
                    media_type="text/tab-separated-values",
                    headers={
                        "Content-Disposition": f"attachment; filename={attribute}_{taxon_set}_cluster_metrics.tsv"
                    },
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

        paginated_result, total_pages = sort_and_paginate_result(
            result,
            sort_by,
            sort_order,
            page,
            size,
        )
        response = ResponseSchema(
            status="success",
            message="Cluster metrics retrieved successfully",
            data=paginated_result,
            query=str(request.url),
            current_page=page,
            entries_per_page=size,
            total_pages=total_pages,
        )

        return JSONResponse(response.model_dump())
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


@router.get("/kinfin/plot/{plot_type}")
@check_kinfin_session
@limiter.limit(LIMIT_STANDARD)
async def get_plot(
    request: Request,
    plot_type: str,
    session_id: str = Depends(header_scheme),
) -> FileResponse:
    """
    Retrieve a specific plot type for a given session.

    Args:
        plot_type (str): The type of plot to retrieve.
        session_id (str): The session ID for authentication.

    Returns:
        FileResponse: The requested plot file.

    Raises:
        HTTPException: If the plot type is invalid, session ID is invalid, or the file is not found.
    """
    try:
        if plot_type not in ["cluster-size-distribution", "all-rarefaction-curve"]:
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
            case "all-rarefaction-curve":
                filepath = "all/all.rarefaction_curve.png"
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
