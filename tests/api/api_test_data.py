"""Fixture data shared by the API conftest and endpoint tests."""

DATASET_ID = "test_ds"

VALID_MEMBERS = ["CBRIG", "CELEG", "LOA2", "BMALA", "AVITE", "EELAP"]

DEFAULT_PARTITION_SET = {
    "out": ["CBRIG", "CELEG"],
    "filarial": ["LOA2", "BMALA"],
}
ALT_PARTITION_SET = {
    "groupA": ["AVITE", "EELAP"],
    "groupB": ["CBRIG", "CELEG", "LOA2", "BMALA"],
}

SUMMARY_COLUMNS = [
    "label",
    "tag",
    "SC",
    "OC",
    "EC",
    "OC_singleton",
    "EC_singleton",
    "OC_specific",
    "EC_specific",
    "OC_shared",
    "EC_shared",
]

# 25 rows so that the default page size (20) yields two pages.
DEFAULT_SUMMARY_ROWS = [
    {
        "label": "default",
        "tag": f"subset_{i:02d}",
        "SC": i % 5 + 1,
        "OC": 100 + i,
        "EC": 1000 + i,
        "OC_singleton": i,
        "EC_singleton": i,
        "OC_specific": 10 + i,
        "EC_specific": 20 + i,
        "OC_shared": 50 + i,
        "EC_shared": 60 + i,
    }
    for i in range(25)
]

# Distinct values so a lookup that hits the wrong file is detectable.
ALT_SUMMARY_ROWS = [
    {
        "label": "alt",
        "tag": f"alt_{i}",
        "SC": 9,
        "OC": 9000 + i,
        "EC": 9999,
        "OC_singleton": 0,
        "EC_singleton": 0,
        "OC_specific": 0,
        "EC_specific": 0,
        "OC_shared": 0,
        "EC_shared": 0,
    }
    for i in range(3)
]

PARTITION_COLUMNS = ["orthogroup_id", "OT", "SC", "EC"]
PARTITION_ROWS = [
    {
        "orthogroup_id": f"OG{i:07d}",
        "OT": "shared" if i % 2 else "specific",
        "SC": i % 4 + 1,
        "EC": 10 * (i + 1),
    }
    for i in range(30)
]

TALLY_ROWS = {
    "EC": [{"EC": i, "count": 100 - i} for i in range(1, 26)],
    "SC": [{"SC": i, "count": 50 - i} for i in range(1, 6)],
}

PARTITION_SUBSET = ["filarial", "out"]
