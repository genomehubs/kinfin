"""Tests for key-map label translation and partition label validation in the API."""

import os
import sys

import pandas as pd
import pytest

SRC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
sys.path.insert(0, SRC_DIR)
os.environ.setdefault("RESULTS_BASE_DIR", "/tmp/kinfin_test_results")

from api.fileparsers import read_table_payload  # noqa: E402
from api.utils import (  # noqa: E402
    load_column_descriptions,
    parse_key_map_query,
    translate_keymap_labels,
    validate_key_map,
    validate_partition_label,
)

load_column_descriptions(os.path.join(SRC_DIR, "api", "column_descriptions.yaml"))


@pytest.fixture
def summary_table(tmp_path):
    path = tmp_path / "summary.tsv"
    pd.DataFrame(
        {
            "label": ["p", "p", "p"],
            "tag": ["0", "1", "10"],
            "SC": [3, 4, 5],
            "OC": [10, 20, 30],
            "OC_singleton": [1, 2, 3],
        }
    ).to_csv(path, sep="\t", index=False)
    return str(path)


@pytest.mark.parametrize(
    "label",
    [
        "OC",  # column name
        "oc",  # case-insensitive
        "tag",  # label column
        "singleton",  # token of OC_singleton
        "count",  # alias token (sample_count)
        "orthogroup",  # token of an alias
        "all",  # field keyword
        "default",  # field keyword
        "remainder",  # CLI remainder label
    ],
)
def test_reserved_labels_rejected(label):
    with pytest.raises(ValueError, match="reserved"):
        validate_partition_label(label)


@pytest.mark.parametrize("label", ["n_16", "a,b", "", " n16", "n16 ", "a\tb", 5])
def test_malformed_labels_rejected(label):
    with pytest.raises(ValueError):
        validate_partition_label(label)


@pytest.mark.parametrize("label", ["n16", "out", "Clade A", "1", "x" * 128])
def test_valid_labels_accepted(label):
    assert validate_partition_label(label) == label


@pytest.mark.parametrize(
    "key_map",
    [
        {"foo": "OC"},  # canonical must be an integer ID
        {"foo": -1},
        {"foo": True},
        {"foo": 1.5},
        {"a": 0, "b": 0},  # canonical IDs must be unique
        {"OC": 0},  # reserved user label
    ],
)
def test_invalid_key_maps_rejected(key_map):
    with pytest.raises(ValueError):
        validate_key_map(key_map)


def test_key_map_digit_strings_normalised():
    assert validate_key_map({"n16": "0", "out": 1}) == {"n16": 0, "out": 1}


def test_parse_key_map_query():
    assert parse_key_map_query('{"n16": 0}') == {"n16": 0}
    assert parse_key_map_query(None) is None
    for bad in ["not json", "[1, 2]", '{"OC": 0}']:
        with pytest.raises(ValueError):
            parse_key_map_query(bad)


def test_translation_matches_whole_tokens_only():
    df = pd.DataFrame({"tag": ["1", "10"], "SC_1": [1, 2], "SC_10": [3, 4]})
    out = translate_keymap_labels(df, {"a": 1, "b": 10})
    assert list(out.columns) == ["tag", "SC_a", "SC_b"]
    assert list(out["tag"]) == ["a", "b"]


def test_table_payload_translates_fields_filters_and_sort(summary_table):
    rows, _ = read_table_payload(
        summary_table,
        table_name="summary",
        requested_fields=["tag", "OC", "OC_singleton"],
        filters=[{"field": "tag", "op": "ne", "value": "out"}],
        sort_by="OC",
        sort_order="desc",
        key_map={"n16": 0, "out": 1, "n11": 10},
    )
    assert rows == [
        {"tag": "n11", "OC": 30, "OC_singleton": 3},
        {"tag": "n16", "OC": 10, "OC_singleton": 1},
    ]


def test_table_payload_rejects_reserved_label(summary_table):
    with pytest.raises(ValueError, match="reserved"):
        read_table_payload(
            summary_table,
            table_name="summary",
            requested_fields=["tag", "OC"],
            filters=[],
            key_map={"OC": 0, "out": 1},
        )


@pytest.fixture
def client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from api.endpoints import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_resolve_rejects_reserved_label_even_without_validation(client):
    response = client.post(
        "/kinfin/partitions/resolve",
        json={
            "dataset_id": "nematodes_v1.0",
            "partition_set": {"OC": ["CBRIG"], "n16": ["LSIGM"]},
            "validate_partition_set": False,
        },
    )
    assert response.status_code == 400
    assert "reserved" in response.json()["error"]


def test_table_endpoint_rejects_reserved_label(client):
    response = client.post(
        "/kinfin/datasets/table",
        json={"dataset_id": "nematodes_v1.0", "key_map": {"OC": 0}},
    )
    assert response.status_code == 422
    assert "reserved" in response.text


def test_summary_endpoint_rejects_reserved_label_in_query(client):
    response = client.get(
        "/kinfin/datasets/nematodes_v1.0/summary",
        params={"key_map": '{"tag": 0}'},
    )
    assert response.status_code == 400
    assert "reserved" in response.json()["detail"]
