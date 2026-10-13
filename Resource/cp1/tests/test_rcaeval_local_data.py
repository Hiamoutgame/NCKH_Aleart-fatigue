from __future__ import annotations

import csv
from pathlib import Path

import pytest

from cp1_core.dataset_io import list_case_log_paths, load_case_logs
from cp1_core.severity import WARN_RE
from cp1_core.source_registry import get_source


@pytest.mark.local_data
def test_representative_warning_counts_match_cp1_baseline():
    source_dir = get_source("rcaeval").local_path
    if source_dir is None or not source_dir.exists():
        pytest.skip("RCAEval chua duoc fetch local")

    fixture = Path(__file__).parent / "fixtures" / "golden_rcaeval_warning_counts.csv"
    with fixture.open(newline="", encoding="utf-8") as handle:
        expected = {row["case"]: int(row["n_warn"]) for row in csv.DictReader(handle)}

    log_paths = list_case_log_paths(source_dir)
    for case_id, count in expected.items():
        assert case_id in log_paths, f"Thieu raw log cho {case_id}"
        messages = load_case_logs(log_paths[case_id], columns=["message"])["message"].astype("string")
        assert int(messages.str.contains(WARN_RE, regex=True, na=False).sum()) == count
