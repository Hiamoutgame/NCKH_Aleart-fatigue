"""Unit tests for RCAEval adapter."""

from __future__ import annotations

from src.datasets.rcaeval import RCAEvalAdapter


def test_rcaeval_inspect():
    adapter = RCAEvalAdapter()
    info = adapter.inspect()
    assert info["dataset_source"] == "rcaeval"
    assert info["total_cases"] == 735
    assert info["cases_with_local_logs"] >= 1


def test_rcaeval_load_incidents():
    adapter = RCAEvalAdapter()
    incidents = adapter.load_incidents()
    assert len(incidents) == 735
    inc0 = incidents[0]
    assert inc0.incident_id.startswith("rcaeval_")
    assert inc0.start_time is not None
    assert inc0.start_time.tzinfo is not None


def test_rcaeval_load_logs():
    adapter = RCAEvalAdapter()
    info = adapter.inspect()
    case_id = info["available_local_case_ids"][0]
    logs = adapter.load_logs(case_id, limit=20)
    assert len(logs) == 20
    assert logs[0].service_id is not None
    assert "#row_" in logs[0].raw_record_ref
