"""
Fixtures for KinFin API endpoint contract tests.

The API package lives under ``src/`` and is imported as ``api``. Importing
``api.endpoints`` instantiates ``api.sessions.QueryManager``, which exits the
interpreter unless ``RESULTS_BASE_DIR`` is an absolute path, so the variable is
set here before any API module is imported.

Each test gets an isolated fixture dataset on disk (``tmp_path``) and a fresh
``DATASETS`` registry, so tests never touch real data or each other's state.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

os.environ.setdefault("RESULTS_BASE_DIR", tempfile.mkdtemp(prefix="kinfin-api-tests-"))

from api_test_data import (  # noqa: E402
    ALT_PARTITION_SET,
    ALT_SUMMARY_ROWS,
    DATASET_ID,
    DEFAULT_PARTITION_SET,
    DEFAULT_SUMMARY_ROWS,
    PARTITION_COLUMNS,
    PARTITION_ROWS,
    PARTITION_SUBSET,
    SUMMARY_COLUMNS,
    TALLY_ROWS,
    VALID_MEMBERS,
)
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import api.utils as api_utils  # noqa: E402
from api.core.limiter import limiter  # noqa: E402
from api.endpoints import router  # noqa: E402

COLUMN_DESCRIPTIONS_YAML = SRC_DIR / "api" / "column_descriptions.yaml"


def _write_tsv(path: Path, columns: list, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["\t".join(columns)]
    lines += ["\t".join(str(row[c]) for c in columns) for row in rows]
    path.write_text("\n".join(lines) + "\n")


def _write_status(root: Path, partition_id: str, status: dict) -> None:
    status_dir = root / DATASET_ID / "partitions" / partition_id
    status_dir.mkdir(parents=True, exist_ok=True)
    (status_dir / "status.json").write_text(json.dumps(status))


@pytest.fixture(scope="session", autouse=True)
def column_registry():
    api_utils.load_column_descriptions(str(COLUMN_DESCRIPTIONS_YAML))


@pytest.fixture
def partition_ids():
    default_id, _ = api_utils.partition_selection_to_id(DEFAULT_PARTITION_SET)
    alt_id, _ = api_utils.partition_selection_to_id(ALT_PARTITION_SET)
    return {"default": default_id, "alt": alt_id}


@pytest.fixture
def dataset(tmp_path, monkeypatch, partition_ids):
    """
    Builds an on-disk dataset with this layout (relative to RESULTS_BASE_DIR):

        test_ds/partitions/<default_id>/status.json       completed, output_name=clade
        test_ds/partitions/<alt_id>/status.json           completed, output_name=alt
        test_ds/partitions/initialising0000/status.json   running
        test_ds/partitions/outputnameonly0/status.json    completed, no artifact_dir
        artifacts/partition/clade.summary.tsv
        artifacts/partition/clade.filarial_vs_out.partition.tsv
        artifacts/partition/alt.summary.tsv
        artifacts/tally/orthogroups.{EC,SC}.tally.tsv
    """
    monkeypatch.setenv("RESULTS_BASE_DIR", str(tmp_path))

    artifacts = tmp_path / "artifacts"
    _write_tsv(
        artifacts / "partition" / "clade.summary.tsv",
        SUMMARY_COLUMNS,
        DEFAULT_SUMMARY_ROWS,
    )
    _write_tsv(
        artifacts / "partition" / "alt.summary.tsv",
        SUMMARY_COLUMNS,
        ALT_SUMMARY_ROWS,
    )
    _write_tsv(
        artifacts
        / "partition"
        / f"clade.{'_vs_'.join(PARTITION_SUBSET)}.partition.tsv",
        PARTITION_COLUMNS,
        PARTITION_ROWS,
    )
    for field, rows in TALLY_ROWS.items():
        _write_tsv(
            artifacts / "tally" / f"orthogroups.{field}.tally.tsv",
            [field, "count"],
            rows,
        )

    _write_status(
        tmp_path,
        partition_ids["default"],
        {
            "schema_version": 1,
            "run_name": "default",
            "partition_id": partition_ids["default"],
            "state": "completed",
            "message": "Default analysis completed successfully.",
            "updated_at": "2026-08-18T12:05:00Z",
            "expires_at": "3026-08-19T12:08:32Z",
            "artifact_dir": "partition",
            "output_name": "clade",
        },
    )
    _write_status(
        tmp_path,
        partition_ids["alt"],
        {
            "schema_version": 1,
            "run_name": "alt",
            "partition_id": partition_ids["alt"],
            "state": "completed",
            "message": "Alt analysis completed successfully.",
            "updated_at": "2026-08-18T13:00:00Z",
            "expires_at": "3026-08-19T13:00:00Z",
            "artifact_dir": "partition",
            "output_name": "alt",
        },
    )
    _write_status(
        tmp_path,
        "initialising0000",
        {
            "schema_version": 1,
            "run_name": "pending",
            "partition_id": "initialising0000",
            "state": "running",
            "message": "Analysis in progress.",
            "updated_at": "2026-08-18T14:00:00Z",
        },
    )
    # Same shape as src/api/examples/.../status.json: relies on output_name alone
    # to locate artifacts under the dataset's partition artifact directory.
    _write_status(
        tmp_path,
        "outputnameonly0",
        {
            "schema_version": 1,
            "run_name": "default",
            "partition_id": "outputnameonly0",
            "state": "completed",
            "message": "Completed without artifact_dir.",
            "output_name": "clade",
        },
    )

    datasets = {
        DATASET_ID: {
            "id": DATASET_ID,
            "name": "Test dataset",
            "status_root": ".",
            "artifact_root": "artifacts",
            "artifacts": {"partition": "partition", "tally": "tally"},
            "default_partition_id": partition_ids["default"],
            "default_partition_set": DEFAULT_PARTITION_SET,
            "valid_members": VALID_MEMBERS,
        }
    }
    monkeypatch.setattr(api_utils, "DATASETS", datasets)
    return {"root": tmp_path, "id": DATASET_ID, "partition_ids": partition_ids}


@pytest.fixture
def app():
    """Mirror the app wiring in ``api.run_server`` without starting uvicorn."""
    application = FastAPI()
    application.state.limiter = limiter
    application.include_router(router)
    return application


@pytest.fixture
def client(app, dataset):
    # Unhandled exceptions are surfaced as 500 responses (as in production)
    # rather than re-raised, so error-shape contracts can be asserted.
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
