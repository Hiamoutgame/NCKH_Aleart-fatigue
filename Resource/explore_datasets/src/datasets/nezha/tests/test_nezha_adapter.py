"""Unit tests for Nezha adapter."""

from __future__ import annotations

from src.datasets.nezha import NezhaAdapter


def test_nezha_inspect():
    adapter = NezhaAdapter()
    info = adapter.inspect()
    assert info["dataset_source"] == "nezha"
    assert info["total_fault_incidents"] == 24
    assert info["log_csv_files_count"] >= 1


def test_nezha_load_incidents():
    adapter = NezhaAdapter()
    incidents = adapter.load_incidents()
    assert len(incidents) == 24
    inc0 = incidents[0]
    assert inc0.incident_id.startswith("nezha_")
    assert inc0.inject_time is not None


def test_nezha_load_logs():
    adapter = NezhaAdapter()
    logs = adapter.load_logs("nezha_1661140434", limit=20)
    assert len(logs) == 20
    assert logs[0].service_id is not None
    assert logs[0].trace_id is not None
