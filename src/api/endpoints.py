import asyncio
import csv
import json
import os
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from api.sessions import query_manager


RUN_SUMMARY_FILEPATH = "summary.json"
COUNTS_FILEPATH = "cluster_counts_by_taxon.txt"


class InputSchema(BaseModel):
    config: List[Dict[str, str]]


# X-Session-ID header will be required to access plots/files later
header_scheme = APIKeyHeader(name="x-session-id")

router = APIRouter()


async def run_cli_command(command: list):
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate()

    stdout = stdout.decode().strip()
    stderr = stderr.decode().strip()

    if process.returncode != 0:
        raise RuntimeError(
            f"CLI command failed with return code {process.returncode}: {stderr}"
        )

    return stdout


@router.post("/kinfin/init")
async def initialize(input_data: InputSchema) -> JSONResponse:
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
        if not isinstance(input_data.config, list):
            raise HTTPException(
                status_code=400,
                detail="Data must be a list of dictionaries.",
            )

        if not all(isinstance(item, dict) for item in input_data.config):
            raise HTTPException(
                status_code=400,
                detail="Each item in data must be a dictionary.",
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
            query_manager.cluster_f,
            "-c",
            config_f,
            "-s",
            query_manager.sequence_ids_f,
            "-m",
            query_manager.taxon_idx_mapping_file,
            "-o",
            result_dir,
            "--plot_format",
            "png",
        ]

        asyncio.create_task(run_cli_command(command))

        return JSONResponse(
            content={"detail": "Analysis task has been queued."},
            headers={"X-Session-ID": session_id},
            status_code=202,
        )

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal Server Error: {str(e)}"
        ) from e


@router.get("/kinfin/run-summary")
async def get_run_summary(session_id: str = Depends(header_scheme)):
    try:
        result_dir = query_manager.get_session_dir(session_id)
        if not result_dir:
            raise HTTPException(status_code=401, detail="Invalid Session ID provided")

        file_path = os.path.join(result_dir, RUN_SUMMARY_FILEPATH)

        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404,
                detail=f"{RUN_SUMMARY_FILEPATH} File Not Found",
            )

        with open(file_path, "r") as f:
            data = json.load(f)
        return JSONResponse(content=data)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal Server Error: {str(e)}",
        ) from e


@router.get("/kinfin/counts-by-taxon")
async def get_counts_by_tanon(
    request: Request,
    session_id: str = Depends(header_scheme),
    include_clusters: Optional[str] = Query(None),
    exclude_clusters: Optional[str] = Query(None),
    min_count: Optional[int] = Query(None),
    max_count: Optional[int] = Query(None),
    include_taxons: Optional[str] = Query(None),
    exclude_taxons: Optional[str] = Query(None),
):
    try:
        result_dir = query_manager.get_session_dir(session_id)
        if not result_dir:
            raise HTTPException(status_code=401, detail="Invalid Session ID provided")

        file_path = os.path.join(result_dir, COUNTS_FILEPATH)
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404,
                detail=f"{COUNTS_FILEPATH} File Not Found",
            )

        included_clusters = (
            set(include_clusters.split(",")) if include_clusters else None
        )
        excluded_clusters = (
            set(exclude_clusters.split(",")) if exclude_clusters else None
        )
        include_taxons_set = set(include_taxons.split(",")) if include_taxons else None
        exclude_taxons_set = set(exclude_taxons.split(",")) if exclude_taxons else None

        result = {}
        with open(file_path, "r", newline="") as file:
            reader = csv.DictReader(file, delimiter="\t")
            for row in reader:
                cluster_id = row["#ID"]

                if included_clusters and cluster_id not in included_clusters:
                    continue
                if excluded_clusters and cluster_id in excluded_clusters:
                    continue

                filtered_values = {}
                for taxon, count in row.items():
                    if taxon == "#ID":
                        continue

                    count = int(count)

                    if min_count is not None and count < min_count:
                        continue

                    if max_count is not None and count > max_count:
                        continue

                    if include_taxons_set and taxon not in include_taxons_set:
                        continue

                    if exclude_taxons_set and taxon in exclude_taxons_set:
                        continue

                    filtered_values[taxon] = count

                if filtered_values:
                    result[cluster_id] = filtered_values

        response = {
            "query": str(request.url),
            "result": result,
        }
        return JSONResponse(response)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal Server Error: {str(e)}",
        ) from e


@router.get("/plot/{plot_type}")
async def get_plot(
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
            raise HTTPException(status_code=404)

        result_dir = query_manager.get_session_dir(session_id)
        if not result_dir:
            raise HTTPException(status_code=401, detail="Invalid Session ID provided")

        file_path: str = ""
        match plot_type:
            case "cluster-size-distribution":
                file_path = "cluster_size_distribution.png"
            case "all-rarefaction-curve":
                file_path = "all/all.rarefaction_curve.png"
            case _:
                raise HTTPException(
                    status_code=404,
                    detail=f"Invalid plot type: {plot_type}",
                )

        file_path = os.path.join(result_dir, file_path)

        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404,
                detail=f"{plot_type} File Not Found",
            )

        return FileResponse(
            file_path,
            media_type="image/png",
            headers={"Content-Disposition": "inline"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal Server Error: {str(e)}",
        ) from e
