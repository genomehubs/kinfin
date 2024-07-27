import asyncio
import json
import os
from typing import Dict, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from api.sessions import session_manager


class InputSchema(BaseModel):
    config: List[Dict[str, str]]


# X-Session-ID header will be required to access plots/files later
header_scheme = APIKeyHeader(name="x-session-id")

router = APIRouter()


async def run_cli_command(command: list):
    process = await asyncio.create_subprocess_exec(
        *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()

    stdout = stdout.decode().strip()
    stderr = stderr.decode().strip()

    if process.returncode != 0:
        raise RuntimeError(
            f"CLI command failed with return code {process.returncode}: {stderr}"
        )

    return stdout


@router.post("/init")
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

        session_id, result_dir = session_manager.new()
        os.makedirs(result_dir, exist_ok=True)
        config_f = os.path.join(result_dir, "config.json")

        with open(config_f, "w") as file:
            json.dump(input_data.config, file)

        command = [
            "python",
            "src/main.py",
            "analyse",
            "-g",
            session_manager.cluster_f,
            "-c",
            config_f,
            "-s",
            session_manager.sequence_ids_f,
            "-m",
            session_manager.taxon_idx_mapping_file,
            "-o",
            result_dir,
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
    if plot_type not in ["cluster-size-distribution", "all-rarefaction-curve"]:
        raise HTTPException(status_code=404)

    result_dir = session_manager.get(session_id)
    if not result_dir:
        raise HTTPException(status_code=401, detail="Invalid Session ID provided")

    file_path: str = ""
    match plot_type:
        case "cluster-size-distribution":
            file_path = "cluster_size_distribution.png"
        case "all-rarefaction-curve":
            file_path = "all/all.rarefaction_curve.png"

    file_path = os.path.join(result_dir, file_path)

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail=f"{plot_type} File Not Found",
        )

    return FileResponse(file_path, media_type="image/png")
