"""
Contract tests for the partition-based KinFin API endpoints retained after the
session-based API is removed (see genomehubs/kinfin#118, #119).

Paths use ``datasets`` in place of ``clusterings`` following #117.

Tests marked ``xfail(strict=True)`` describe the intended contract where the
current implementation drifts from it. They are expected to fail today; once a
fix lands they will XPASS, which fails the run under ``strict=True`` and is the
cue to remove the marker.
"""

import pytest
from api_test_data import (
    ALT_PARTITION_SET,
    ALT_SUMMARY_ROWS,
    DEFAULT_PARTITION_SET,
    DEFAULT_SUMMARY_ROWS,
    PARTITION_ROWS,
    PARTITION_SUBSET,
    TALLY_ROWS,
)
from fastapi.routing import APIRoute

RETAINED_ENDPOINTS = [
    ("GET", "/kinfin/datasets/{dataset_id}/summary"),
    ("POST", "/kinfin/datasets/summary"),
    ("GET", "/kinfin/datasets/{dataset_id}/tally"),
    ("POST", "/kinfin/datasets/table"),
    ("POST", "/kinfin/partitions/resolve"),
    ("GET", "/kinfin/datasets/{dataset_id}/partitions/{partition_id}/status"),
    ("POST", "/kinfin/partitions/status"),
]

RESPONSE_SCHEMA_KEYS = {
    "status",
    "message",
    "query",
    "data",
    "timestamp",
    "error",
    "total_pages",
    "current_page",
    "entries_per_page",
}

DRIFT = "Schema drift: log and resolve as a separate issue (see #119)."


def assert_success(response, status_code=200):
    assert response.status_code == status_code, response.text
    body = response.json()
    assert set(body) == RESPONSE_SCHEMA_KEYS
    assert body["status"] == "success"
    assert body["error"] is None
    assert isinstance(body["message"], str) and body["message"]
    return body


def assert_error(response, status_code):
    assert response.status_code == status_code, response.text
    body = response.json()
    assert set(body) == RESPONSE_SCHEMA_KEYS
    assert body["status"] == "error"
    assert isinstance(body["message"], str) and body["message"]
    assert body["data"] is None
    return body


def assert_paginated(data, *, rows_key, current_page, total_pages, page_len):
    assert data["current_page"] == current_page
    assert data["total_pages"] == total_pages
    assert isinstance(data[rows_key], list)
    assert len(data[rows_key]) == page_len


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("method,path", RETAINED_ENDPOINTS)
def test_route_is_registered(app, method, path):
    routes = {
        (m, route.path)
        for route in app.routes
        if isinstance(route, APIRoute)
        for m in route.methods
    }
    assert (method, path) in routes


@pytest.mark.parametrize("method,path", RETAINED_ENDPOINTS)
def test_route_rejects_other_method(client, method, path):
    other = "POST" if method == "GET" else "GET"
    url = path.format(dataset_id="test_ds", partition_id="abc")
    assert client.request(other, url).status_code == 405


# ---------------------------------------------------------------------------
# POST /kinfin/partitions/resolve
# ---------------------------------------------------------------------------


class TestResolvePartition:
    url = "/kinfin/partitions/resolve"

    def test_resolves_default_partition(self, client, dataset):
        response = client.post(
            self.url,
            json={"dataset_id": dataset["id"], "partition_set": DEFAULT_PARTITION_SET},
        )
        data = assert_success(response)["data"]
        assert data["dataset_id"] == dataset["id"]
        assert data["partition_id"] == dataset["partition_ids"]["default"]
        assert set(data["key_map"]) == set(DEFAULT_PARTITION_SET)
        assert sorted(data["key_map"].values()) == list(
            range(len(DEFAULT_PARTITION_SET))
        )
        assert data["message"] == "Default analysis completed successfully."
        assert data["updated_at"] == "2026-08-18T12:05:00Z"
        assert data["expires_at"] == "3026-08-19T12:08:32Z"

    def test_partition_id_is_canonical(self, client, dataset):
        """Label names, member order and case must not change the partition id."""
        reordered = {
            "zzz": [m.lower() for m in reversed(DEFAULT_PARTITION_SET["filarial"])],
            "aaa": list(reversed(DEFAULT_PARTITION_SET["out"])),
        }
        response = client.post(
            self.url, json={"dataset_id": dataset["id"], "partition_set": reordered}
        )
        data = assert_success(response)["data"]
        assert data["partition_id"] == dataset["partition_ids"]["default"]

    def test_distinct_sets_resolve_to_distinct_ids(self, client, dataset):
        response = client.post(
            self.url,
            json={"dataset_id": dataset["id"], "partition_set": ALT_PARTITION_SET},
        )
        data = assert_success(response)["data"]
        assert data["partition_id"] == dataset["partition_ids"]["alt"]
        assert data["partition_id"] != dataset["partition_ids"]["default"]

    def test_validate_alias_accepted(self, client, dataset):
        response = client.post(
            self.url,
            json={
                "dataset_id": dataset["id"],
                "partition_set": {"a": ["NOT_A_MEMBER"]},
                "validate": False,
            },
        )
        assert_success(response)

    @pytest.mark.parametrize(
        "partition_set,error_fragment",
        [
            ({"a": ["NOT_A_MEMBER"]}, "not a valid ID"),
            ({"a": ["CBRIG"], "b": ["cbrig"]}, "Duplicate"),
            ({"a": []}, "non-empty list"),
            ({"a": [""]}, "non-empty strings"),
        ],
    )
    def test_invalid_partition_set_returns_400(
        self, client, dataset, partition_set, error_fragment
    ):
        response = client.post(
            self.url, json={"dataset_id": dataset["id"], "partition_set": partition_set}
        )
        body = assert_error(response, 400)
        assert body["message"] == "Invalid partition set"
        assert error_fragment in body["error"]

    def test_unknown_dataset_fails_validation(self, client, dataset):
        response = client.post(
            self.url,
            json={
                "dataset_id": "no_such_dataset",
                "partition_set": DEFAULT_PARTITION_SET,
            },
        )
        assert_error(response, 400)

    @pytest.mark.parametrize(
        "payload",
        [
            {},
            {"dataset_id": "test_ds"},
            {"partition_set": DEFAULT_PARTITION_SET},
            {"dataset_id": "test_ds", "partition_set": ["not", "a", "dict"]},
        ],
    )
    def test_malformed_payload_returns_422(self, client, payload):
        assert client.post(self.url, json=payload).status_code == 422

    def test_unrun_partition_reports_missing(self, client, dataset):
        response = client.post(
            self.url,
            json={"dataset_id": dataset["id"], "partition_set": {"x": ["AVITE"]}},
        )
        data = assert_success(response)["data"]
        assert data["status"] in {"missing", "error"}

    @pytest.mark.xfail(
        strict=True, reason=f"Raw status file state is returned. {DRIFT}"
    )
    def test_status_is_normalised(self, client, dataset):
        response = client.post(
            self.url,
            json={"dataset_id": dataset["id"], "partition_set": DEFAULT_PARTITION_SET},
        )
        assert response.json()["data"]["status"] == "ready"

    @pytest.mark.xfail(
        strict=True,
        reason=f"Missing status file is reported as state 'error'. {DRIFT}",
    )
    def test_unrun_partition_status_is_missing(self, client, dataset):
        response = client.post(
            self.url,
            json={"dataset_id": dataset["id"], "partition_set": {"x": ["AVITE"]}},
        )
        assert response.json()["data"]["status"] == "missing"


# ---------------------------------------------------------------------------
# GET /kinfin/datasets/{dataset_id}/partitions/{partition_id}/status
# ---------------------------------------------------------------------------


class TestPartitionStatusById:
    @staticmethod
    def url(dataset_id, partition_id):
        return f"/kinfin/datasets/{dataset_id}/partitions/{partition_id}/status"

    def test_ready_partition(self, client, dataset):
        partition_id = dataset["partition_ids"]["default"]
        response = client.get(self.url(dataset["id"], partition_id))
        data = assert_success(response)["data"]
        assert data["dataset_id"] == dataset["id"]
        assert data["partition_id"] == partition_id
        assert data["message"] == "Default analysis completed successfully."
        assert data["updated_at"] == "2026-08-18T12:05:00Z"
        assert data["expires_at"] == "3026-08-19T12:08:32Z"
        assert isinstance(data["details"], dict)

    def test_reads_status_for_requested_partition(self, client, dataset):
        response = client.get(self.url(dataset["id"], dataset["partition_ids"]["alt"]))
        data = assert_success(response)["data"]
        assert data["message"] == "Alt analysis completed successfully."

    def test_initialising_partition(self, client, dataset):
        response = client.get(self.url(dataset["id"], "initialising0000"))
        data = assert_success(response)["data"]
        assert data["message"] == "Analysis in progress."
        assert data["expires_at"] is None

    def test_unknown_partition_does_not_return_success(self, client, dataset):
        response = client.get(self.url(dataset["id"], "0000000000000000"))
        body = response.json()
        assert body["data"] is None or body["data"]["status"] != "ready"

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "read_run_status_file reports a missing status file as state 'error' "
            f"so the 404 branch is unreachable. {DRIFT}"
        ),
    )
    def test_unknown_partition_returns_404(self, client, dataset):
        response = client.get(self.url(dataset["id"], "0000000000000000"))
        body = assert_error(response, 404)
        assert body["error"] == "partition_not_found"

    @pytest.mark.xfail(
        strict=True, reason=f"Raw status file state is returned. {DRIFT}"
    )
    def test_status_is_normalised(self, client, dataset):
        partition_id = dataset["partition_ids"]["default"]
        response = client.get(self.url(dataset["id"], partition_id))
        assert response.json()["data"]["status"] == "ready"


# ---------------------------------------------------------------------------
# POST /kinfin/partitions/status
# ---------------------------------------------------------------------------


class TestPartitionStatusBatch:
    url = "/kinfin/partitions/status"

    def test_returns_entry_per_partition(self, client, dataset):
        ids = [
            dataset["partition_ids"]["default"],
            dataset["partition_ids"]["alt"],
            "initialising0000",
        ]
        response = client.post(
            self.url, json={"dataset_id": dataset["id"], "partition_ids": ids}
        )
        data = assert_success(response)["data"]
        assert set(data) == set(ids)
        for partition_id, entry in data.items():
            assert set(entry) == {
                "dataset_id",
                "partition_id",
                "status",
                "message",
                "updated_at",
                "expires_at",
            }
            assert entry["dataset_id"] == dataset["id"]
            assert entry["partition_id"] == partition_id
        assert data[dataset["partition_ids"]["alt"]]["message"] == (
            "Alt analysis completed successfully."
        )
        assert data["initialising0000"]["message"] == "Analysis in progress."

    def test_empty_list(self, client, dataset):
        response = client.post(
            self.url, json={"dataset_id": dataset["id"], "partition_ids": []}
        )
        assert assert_success(response)["data"] == {}

    def test_unknown_partition_included(self, client, dataset):
        response = client.post(
            self.url,
            json={"dataset_id": dataset["id"], "partition_ids": ["0000000000000000"]},
        )
        data = assert_success(response)["data"]
        assert "0000000000000000" in data
        assert data["0000000000000000"]["status"] != "ready"

    @pytest.mark.parametrize(
        "payload",
        [
            {},
            {"dataset_id": "test_ds"},
            {"partition_ids": []},
            {"dataset_id": "test_ds", "partition_ids": "not-a-list"},
        ],
    )
    def test_malformed_payload_returns_422(self, client, payload):
        assert client.post(self.url, json=payload).status_code == 422

    @pytest.mark.xfail(
        strict=True,
        reason=f"Raw state is returned and missing partitions report 'error'. {DRIFT}",
    )
    def test_statuses_are_normalised(self, client, dataset):
        default_id = dataset["partition_ids"]["default"]
        response = client.post(
            self.url,
            json={
                "dataset_id": dataset["id"],
                "partition_ids": [default_id, "initialising0000", "0000000000000000"],
            },
        )
        data = response.json()["data"]
        assert data[default_id]["status"] == "ready"
        assert data["initialising0000"]["status"] == "initialising"
        assert data["0000000000000000"]["status"] == "missing"


# ---------------------------------------------------------------------------
# GET /kinfin/datasets/{dataset_id}/summary
# ---------------------------------------------------------------------------


class TestGetDatasetSummary:
    @staticmethod
    def url(dataset_id):
        return f"/kinfin/datasets/{dataset_id}/summary"

    def test_first_page(self, client, dataset):
        response = client.get(self.url(dataset["id"]))
        data = assert_success(response)["data"]
        assert data["dataset_id"] == dataset["id"]
        assert data["partition_id"] == dataset["partition_ids"]["default"]
        assert_paginated(
            data, rows_key="summary", current_page=1, total_pages=2, page_len=20
        )
        assert data["summary"][0]["tag"] == DEFAULT_SUMMARY_ROWS[0]["tag"]

    def test_last_page(self, client, dataset):
        response = client.get(self.url(dataset["id"]), params={"page": 2})
        data = assert_success(response)["data"]
        assert_paginated(
            data, rows_key="summary", current_page=2, total_pages=2, page_len=5
        )
        assert data["summary"][-1]["tag"] == DEFAULT_SUMMARY_ROWS[-1]["tag"]

    def test_page_size(self, client, dataset):
        response = client.get(self.url(dataset["id"]), params={"size": 10, "page": 3})
        data = assert_success(response)["data"]
        assert_paginated(
            data, rows_key="summary", current_page=3, total_pages=3, page_len=5
        )

    def test_page_past_end_is_empty(self, client, dataset):
        response = client.get(self.url(dataset["id"]), params={"page": 99})
        data = assert_success(response)["data"]
        assert_paginated(
            data, rows_key="summary", current_page=99, total_pages=2, page_len=0
        )

    def test_default_columns(self, client, dataset):
        data = assert_success(client.get(self.url(dataset["id"])))["data"]
        columns = set(data["summary"][0])
        assert "tag" in columns
        assert "label" not in columns  # default_visible: false
        assert "EC_singleton" not in columns

    def test_fields_selection_includes_always_visible(self, client, dataset):
        response = client.get(
            self.url(dataset["id"]),
            params=[("fields", "SC"), ("fields", "orthogroup_count")],
        )
        data = assert_success(response)["data"]
        assert set(data["summary"][0]) == {"tag", "SC", "OC"}

    def test_sort(self, client, dataset):
        response = client.get(
            self.url(dataset["id"]),
            params={"sort_by": "OC", "sort_order": "desc", "size": 3},
        )
        data = assert_success(response)["data"]
        assert [row["OC"] for row in data["summary"]] == [124, 123, 122]

    @pytest.mark.parametrize("params", [{"page": 0}, {"size": 0}, {"page": "x"}])
    def test_invalid_pagination_returns_422(self, client, dataset, params):
        assert client.get(self.url(dataset["id"]), params=params).status_code == 422

    @pytest.mark.xfail(
        strict=True,
        reason=f"Unknown dataset raises an unhandled ValueError (500). {DRIFT}",
    )
    def test_unknown_dataset_returns_404(self, client):
        assert_error(client.get(self.url("no_such_dataset")), 404)

    @pytest.mark.xfail(
        strict=True,
        reason=f"Missing artifact raises an unhandled FileNotFoundError. {DRIFT}",
    )
    def test_missing_artifact_returns_404(self, client, dataset):
        (dataset["root"] / "artifacts" / "partition" / "clade.summary.tsv").unlink()
        assert_error(client.get(self.url(dataset["id"])), 404)

    @pytest.mark.xfail(
        strict=True,
        reason=f"Pagination is nested in data; top-level fields stay null. {DRIFT}",
    )
    def test_top_level_pagination_fields(self, client, dataset):
        body = client.get(self.url(dataset["id"]), params={"size": 10}).json()
        assert (
            body["current_page"],
            body["total_pages"],
            body["entries_per_page"],
        ) == (
            1,
            3,
            10,
        )


# ---------------------------------------------------------------------------
# POST /kinfin/datasets/summary
# ---------------------------------------------------------------------------


class TestPostDatasetSummary:
    url = "/kinfin/datasets/summary"

    @pytest.mark.parametrize("partition_id", [None, "default"])
    def test_default_partition(self, client, dataset, partition_id):
        payload = {"dataset_id": dataset["id"]}
        if partition_id:
            payload["partition_id"] = partition_id
        data = assert_success(client.post(self.url, json=payload))["data"]
        assert data["partition_id"] == dataset["partition_ids"]["default"]
        assert_paginated(
            data, rows_key="summary", current_page=1, total_pages=2, page_len=20
        )

    def test_resolves_requested_partition_file(self, client, dataset):
        response = client.post(
            self.url,
            json={
                "dataset_id": dataset["id"],
                "partition_id": dataset["partition_ids"]["alt"],
            },
        )
        data = assert_success(response)["data"]
        assert data["partition_id"] == dataset["partition_ids"]["alt"]
        assert_paginated(
            data, rows_key="summary", current_page=1, total_pages=1, page_len=3
        )
        assert [row["tag"] for row in data["summary"]] == [
            r["tag"] for r in ALT_SUMMARY_ROWS
        ]

    def test_prefers_parquet_over_tsv(self, client, dataset):
        import pandas as pd

        partition_dir = dataset["root"] / "artifacts" / "partition"
        df = pd.read_csv(partition_dir / "alt.summary.tsv", sep="\t")
        df["tag"] = "from_parquet"
        df.to_parquet(partition_dir / "alt.summary.parquet")
        response = client.post(
            self.url,
            json={
                "dataset_id": dataset["id"],
                "partition_id": dataset["partition_ids"]["alt"],
            },
        )
        data = assert_success(response)["data"]
        assert {row["tag"] for row in data["summary"]} == {"from_parquet"}

    def test_pagination(self, client, dataset):
        response = client.post(
            self.url, json={"dataset_id": dataset["id"], "page": 3, "size": 10}
        )
        data = assert_success(response)["data"]
        assert_paginated(
            data, rows_key="summary", current_page=3, total_pages=3, page_len=5
        )

    def test_fields(self, client, dataset):
        response = client.post(
            self.url,
            json={"dataset_id": dataset["id"], "fields": ["EC", "OC_specific"]},
        )
        data = assert_success(response)["data"]
        assert set(data["summary"][0]) == {"tag", "EC", "OC_specific"}

    def test_filter_numeric(self, client, dataset):
        response = client.post(
            self.url,
            json={
                "dataset_id": dataset["id"],
                "fields": ["SC"],
                "filters": [{"field": "SC", "op": "gte", "value": 4}],
                "size": 100,
            },
        )
        data = assert_success(response)["data"]
        expected = [r["tag"] for r in DEFAULT_SUMMARY_ROWS if r["SC"] >= 4]
        assert [row["tag"] for row in data["summary"]] == expected
        assert data["total_pages"] == 1

    def test_filter_by_alias_and_combined(self, client, dataset):
        response = client.post(
            self.url,
            json={
                "dataset_id": dataset["id"],
                "fields": ["SC", "OC"],
                "filters": [
                    {"field": "sample_count", "op": "eq", "value": 1},
                    {"field": "OC", "op": "lt", "value": 115},
                ],
            },
        )
        data = assert_success(response)["data"]
        expected = [
            r["tag"] for r in DEFAULT_SUMMARY_ROWS if r["SC"] == 1 and r["OC"] < 115
        ]
        assert [row["tag"] for row in data["summary"]] == expected

    def test_filter_string_contains(self, client, dataset):
        response = client.post(
            self.url,
            json={
                "dataset_id": dataset["id"],
                "filters": [{"field": "tag", "op": "contains", "value": "_1"}],
            },
        )
        data = assert_success(response)["data"]
        assert [row["tag"] for row in data["summary"]] == [
            f"subset_{i:02d}" for i in range(10, 20)
        ]

    def test_filter_with_no_matches(self, client, dataset):
        response = client.post(
            self.url,
            json={
                "dataset_id": dataset["id"],
                "fields": ["OC"],
                "filters": [{"field": "OC", "op": "gt", "value": 10**6}],
            },
        )
        data = assert_success(response)["data"]
        assert_paginated(
            data, rows_key="summary", current_page=1, total_pages=1, page_len=0
        )

    def test_filter_then_sort_then_paginate(self, client, dataset):
        response = client.post(
            self.url,
            json={
                "dataset_id": dataset["id"],
                "fields": ["SC", "OC"],
                "filters": [{"field": "SC", "op": "eq", "value": 2}],
                "sort_by": "OC",
                "sort_order": "desc",
                "size": 2,
                "page": 2,
            },
        )
        data = assert_success(response)["data"]
        ocs = sorted(
            (r["OC"] for r in DEFAULT_SUMMARY_ROWS if r["SC"] == 2), reverse=True
        )
        assert [row["OC"] for row in data["summary"]] == ocs[2:4]
        assert data["total_pages"] == (len(ocs) + 1) // 2

    def test_missing_dataset_id_returns_422(self, client):
        assert client.post(self.url, json={}).status_code == 422

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "POST fields defaults to [] (always-visible only) while GET defaults "
            f"to the default-visible columns. {DRIFT}"
        ),
    )
    def test_default_columns_match_get(self, client, dataset):
        get_rows = client.get(f"/kinfin/datasets/{dataset['id']}/summary").json()
        post_rows = client.post(self.url, json={"dataset_id": dataset["id"]}).json()
        assert set(post_rows["data"]["summary"][0]) == set(
            get_rows["data"]["summary"][0]
        )

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "Only requested fields are loaded, so filtering on an unselected "
            f"column raises KeyError (500). {DRIFT}"
        ),
    )
    def test_filter_on_unselected_field(self, client, dataset):
        response = client.post(
            self.url,
            json={
                "dataset_id": dataset["id"],
                "fields": ["EC"],
                "filters": [{"field": "SC", "op": "eq", "value": 1}],
            },
        )
        data = assert_success(response)["data"]
        assert "SC" not in data["summary"][0]

    @pytest.mark.xfail(
        strict=True,
        reason=f"Unknown filter field raises an unhandled ValueError. {DRIFT}",
    )
    def test_invalid_filter_field_returns_400(self, client, dataset):
        response = client.post(
            self.url,
            json={
                "dataset_id": dataset["id"],
                "filters": [{"field": "nope", "op": "eq", "value": 1}],
            },
        )
        assert_error(response, 400)

    @pytest.mark.xfail(
        strict=True, reason=f"Invalid filter op raises an unhandled ValueError. {DRIFT}"
    )
    def test_invalid_filter_op_returns_400(self, client, dataset):
        response = client.post(
            self.url,
            json={
                "dataset_id": dataset["id"],
                "filters": [{"field": "tag", "op": "gt", "value": "a"}],
            },
        )
        assert_error(response, 400)

    @pytest.mark.xfail(
        strict=True,
        reason=f"POST page/size are unvalidated; size=0 divides by zero. {DRIFT}",
    )
    @pytest.mark.parametrize("override", [{"page": 0}, {"size": 0}])
    def test_invalid_pagination_returns_422(self, client, dataset, override):
        response = client.post(self.url, json={"dataset_id": dataset["id"], **override})
        assert response.status_code == 422

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "get_partition_artifact_dir shadows artifact_dir with the walrus "
            "operator, so a status with output_name but no artifact_dir "
            f"crashes with TypeError. {DRIFT}"
        ),
    )
    def test_status_with_output_name_only_resolves(self, client, dataset):
        response = client.post(
            self.url,
            json={"dataset_id": dataset["id"], "partition_id": "outputnameonly0"},
        )
        data = assert_success(response)["data"]
        assert data["summary"][0]["tag"] == DEFAULT_SUMMARY_ROWS[0]["tag"]

    @pytest.mark.xfail(
        strict=True,
        reason=f"Not-ready partition raises an unhandled ValueError. {DRIFT}",
    )
    def test_not_ready_partition_returns_error_shape(self, client, dataset):
        response = client.post(
            self.url,
            json={"dataset_id": dataset["id"], "partition_id": "initialising0000"},
        )
        assert response.status_code in {404, 409}
        assert response.json()["status"] == "error"


# ---------------------------------------------------------------------------
# GET /kinfin/datasets/{dataset_id}/tally
# ---------------------------------------------------------------------------


class TestGetDatasetTally:
    @staticmethod
    def url(dataset_id):
        return f"/kinfin/datasets/{dataset_id}/tally"

    def test_default_field_is_ec(self, client, dataset):
        data = assert_success(client.get(self.url(dataset["id"])))["data"]
        assert data["dataset_id"] == dataset["id"]
        assert_paginated(
            data, rows_key="tally", current_page=1, total_pages=2, page_len=20
        )
        assert set(data["tally"][0]) == {"EC", "count"}
        assert data["tally"][0] == TALLY_ROWS["EC"][0]

    def test_sc_field_resolves_sc_file(self, client, dataset):
        response = client.get(self.url(dataset["id"]), params={"tally_field": "SC"})
        data = assert_success(response)["data"]
        assert_paginated(
            data, rows_key="tally", current_page=1, total_pages=1, page_len=5
        )
        assert data["tally"] == TALLY_ROWS["SC"]

    def test_pagination_and_sort(self, client, dataset):
        response = client.get(
            self.url(dataset["id"]),
            params={"sort_by": "count", "sort_order": "asc", "size": 10, "page": 3},
        )
        data = assert_success(response)["data"]
        assert_paginated(
            data, rows_key="tally", current_page=3, total_pages=3, page_len=5
        )
        counts = sorted(r["count"] for r in TALLY_ROWS["EC"])
        assert [row["count"] for row in data["tally"]] == counts[20:]

    def test_invalid_tally_field_returns_400(self, client, dataset):
        response = client.get(self.url(dataset["id"]), params={"tally_field": "XX"})
        body = assert_error(response, 400)
        assert body["error"] == "invalid_tally_field"

    @pytest.mark.parametrize("params", [{"page": 0}, {"size": 0}])
    def test_invalid_pagination_returns_422(self, client, dataset, params):
        assert client.get(self.url(dataset["id"]), params=params).status_code == 422

    @pytest.mark.xfail(
        strict=True,
        reason=f"Unknown dataset raises an unhandled ValueError (500). {DRIFT}",
    )
    def test_unknown_dataset_returns_404(self, client):
        assert_error(client.get(self.url("no_such_dataset")), 404)


# ---------------------------------------------------------------------------
# POST /kinfin/datasets/table
# ---------------------------------------------------------------------------


class TestPostDatasetTable:
    url = "/kinfin/datasets/table"

    def test_summary_table_is_default(self, client, dataset):
        data = assert_success(
            client.post(self.url, json={"dataset_id": dataset["id"]})
        )["data"]
        assert data["dataset_id"] == dataset["id"]
        assert data["partition_id"] == dataset["partition_ids"]["default"]
        assert_paginated(
            data, rows_key="table", current_page=1, total_pages=2, page_len=20
        )
        assert data["table"][0]["tag"] == DEFAULT_SUMMARY_ROWS[0]["tag"]

    def test_summary_table_for_requested_partition(self, client, dataset):
        response = client.post(
            self.url,
            json={
                "dataset_id": dataset["id"],
                "partition_id": dataset["partition_ids"]["alt"],
            },
        )
        data = assert_success(response)["data"]
        assert [row["tag"] for row in data["table"]] == [
            r["tag"] for r in ALT_SUMMARY_ROWS
        ]

    def test_partition_table_resolves_subset_file(self, client, dataset):
        response = client.post(
            self.url,
            json={
                "dataset_id": dataset["id"],
                "table_name": "partition",
                "subset": PARTITION_SUBSET,
                "fields": ["default"],
            },
        )
        data = assert_success(response)["data"]
        assert_paginated(
            data, rows_key="table", current_page=1, total_pages=2, page_len=20
        )
        assert set(data["table"][0]) == {"orthogroup_id", "OT", "SC", "EC"}
        assert data["table"][0] == PARTITION_ROWS[0]

    def test_partition_table_filters_and_pagination(self, client, dataset):
        response = client.post(
            self.url,
            json={
                "dataset_id": dataset["id"],
                "table_name": "partition",
                "subset": PARTITION_SUBSET,
                "filters": [
                    {"field": "orthogroup_type", "op": "eq", "value": "shared"},
                    {"field": "EC", "op": "gte", "value": 100},
                ],
                "fields": ["orthogroup_type", "EC"],
                "sort_by": "EC",
                "sort_order": "desc",
                "size": 5,
                "page": 2,
            },
        )
        data = assert_success(response)["data"]
        expected = sorted(
            (r for r in PARTITION_ROWS if r["OT"] == "shared" and r["EC"] >= 100),
            key=lambda r: r["EC"],
            reverse=True,
        )
        assert data["total_pages"] == (len(expected) + 4) // 5
        assert [row["orthogroup_id"] for row in data["table"]] == [
            r["orthogroup_id"] for r in expected[5:10]
        ]
        assert set(data["table"][0]) == {"orthogroup_id", "OT", "EC"}

    @pytest.mark.parametrize(
        "subset",
        [None, [], ["out"], ["a", "b", "c"]],
        ids=["none", "empty", "one", "three"],
    )
    def test_partition_table_requires_pair_subset(self, client, dataset, subset):
        payload = {"dataset_id": dataset["id"], "table_name": "partition"}
        if subset is not None:
            payload["subset"] = subset
        body = assert_error(client.post(self.url, json=payload), 400)
        assert body["error"] == "missing_subset"

    def test_missing_dataset_id_returns_422(self, client):
        assert client.post(self.url, json={"table_name": "summary"}).status_code == 422

    @pytest.mark.xfail(
        strict=True,
        reason=f"Unknown subset pair raises FileNotFoundError (500). {DRIFT}",
    )
    def test_unknown_subset_pair_returns_404(self, client, dataset):
        response = client.post(
            self.url,
            json={
                "dataset_id": dataset["id"],
                "table_name": "partition",
                "subset": ["x", "y"],
            },
        )
        assert_error(response, 404)

    @pytest.mark.xfail(
        strict=True,
        reason=f"Unknown table_name raises an unhandled error (500). {DRIFT}",
    )
    def test_unknown_table_name_returns_400(self, client, dataset):
        response = client.post(
            self.url, json={"dataset_id": dataset["id"], "table_name": "nope"}
        )
        assert_error(response, 400)
