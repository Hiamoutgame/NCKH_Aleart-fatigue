"""Automated validation tests for canonical dataset normalization.

Covers the 8 core requirements:
  1. Raw preservation
  2. Traceability
  3. Timestamp UTC
  4. Service mapping
  5. Ground truth preservation
  6. Incident segmentation
  7. Label leakage prevention
  8. Determinism
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
import pytest

from src.datasets.rcaeval import RCAEvalAdapter
from src.datasets.nezha import NezhaAdapter
from src.shared.domain.canonical import Incident, LogEvent, GroundTruth


@pytest.fixture
def rcaeval_adapter():
    return RCAEvalAdapter()


@pytest.fixture
def nezha_adapter():
    return NezhaAdapter()


# ----------------------------------------------------------------------
# 1. Raw preservation
# ----------------------------------------------------------------------
def test_raw_preservation(rcaeval_adapter, nezha_adapter):
    # RCAEval
    rca_logs = rcaeval_adapter.load_logs("rcaeval_re2ss_carts_cpu_1", limit=10)
    assert len(rca_logs) > 0
    for event in rca_logs:
        assert isinstance(event.raw_message, str)
        assert len(event.raw_message) > 0

    # Nezha
    nezha_logs = nezha_adapter.load_logs("nezha_1661140434", limit=10)
    assert len(nezha_logs) > 0
    for event in nezha_logs:
        assert isinstance(event.raw_message, str)
        assert len(event.raw_message) > 0


# ----------------------------------------------------------------------
# 2. Traceability
# ----------------------------------------------------------------------
def test_traceability(rcaeval_adapter, nezha_adapter):
    for adapter, inc_id in [
        (rcaeval_adapter, "rcaeval_re2ss_carts_cpu_1"),
        (nezha_adapter, "nezha_1661140434"),
    ]:
        logs = adapter.load_logs(inc_id, limit=5)
        for event in logs:
            assert event.source_file, f"Missing source_file in {adapter.dataset_source}"
            assert event.source_row_id is not None, f"Missing source_row_id in {adapter.dataset_source}"
            assert event.raw_record_ref, f"Missing raw_record_ref in {adapter.dataset_source}"
            assert "#" in event.raw_record_ref, f"raw_record_ref must reference internal record pointer"


# ----------------------------------------------------------------------
# 3. Timestamp UTC
# ----------------------------------------------------------------------
def test_timestamp_utc(rcaeval_adapter, nezha_adapter):
    for adapter, inc_id in [
        (rcaeval_adapter, "rcaeval_re2ss_carts_cpu_1"),
        (nezha_adapter, "nezha_1661140434"),
    ]:
        logs = adapter.load_logs(inc_id, limit=5)
        for event in logs:
            if event.timestamp_utc is not None:
                assert event.timestamp_utc.tzinfo is not None, f"Timestamp must be timezone-aware: {event}"
                assert event.timestamp_utc.tzinfo == timezone.utc, f"Timestamp must be UTC: {event}"


# ----------------------------------------------------------------------
# 4. Service mapping
# ----------------------------------------------------------------------
def test_service_mapping(rcaeval_adapter, nezha_adapter):
    # RCAEval: container_name is preserved as service_id
    rca_logs = rcaeval_adapter.load_logs("rcaeval_re2ss_carts_cpu_1", limit=10)
    for event in rca_logs:
        assert event.service_id == event.entity_id

    # Nezha: PodName (e.g. frontend-xxx) is mapped to service (frontend)
    nezha_logs = nezha_adapter.load_logs("nezha_1661140434", limit=10)
    for event in nezha_logs:
        if event.entity_id:
            assert event.service_id is not None
            assert event.service_id in event.entity_id


# ----------------------------------------------------------------------
# 5. Ground truth preservation
# ----------------------------------------------------------------------
def test_ground_truth_preservation(rcaeval_adapter, nezha_adapter):
    for adapter in [rcaeval_adapter, nezha_adapter]:
        gts = adapter.load_ground_truth()
        assert len(gts) > 0
        for gt in gts[:5]:
            assert gt.incident_id, "Ground truth missing incident_id"
            assert gt.label_level in {"service", "pod", "container"}, f"Invalid label level: {gt.label_level}"
            assert gt.original_target, "Missing original_target"
            assert gt.mapping_status in {"verified", "inferred", "missing"}, f"Invalid mapping status: {gt.mapping_status}"


# ----------------------------------------------------------------------
# 6. Incident segmentation
# ----------------------------------------------------------------------
def test_incident_segmentation(rcaeval_adapter, nezha_adapter):
    for adapter, inc_id in [
        (rcaeval_adapter, "rcaeval_re2ss_carts_cpu_1"),
        (nezha_adapter, "nezha_1661140434"),
    ]:
        incidents = {i.incident_id: i for i in adapter.load_incidents()}
        logs = adapter.load_logs(inc_id, limit=5)
        for event in logs:
            assert event.incident_id in incidents, f"Orphan log event {event.log_id} has invalid incident {event.incident_id}"


# ----------------------------------------------------------------------
# 7. Label leakage prevention
# ----------------------------------------------------------------------
def test_label_leakage_prevention(rcaeval_adapter, nezha_adapter):
    """Ensure LogEvent attributes do not contain ground truth target labels."""
    forbidden_gt_attributes = {"root_cause", "is_root_cause", "ground_truth", "rc_label"}
    for adapter, inc_id in [
        (rcaeval_adapter, "rcaeval_re2ss_carts_cpu_1"),
        (nezha_adapter, "nezha_1661140434"),
    ]:
        logs = adapter.load_logs(inc_id, limit=5)
        for event in logs:
            event_dict = event.to_dict()
            for key in forbidden_gt_attributes:
                assert key not in event_dict, f"Label leakage detected! Found {key} in LogEvent"


# ----------------------------------------------------------------------
# 8. Determinism
# ----------------------------------------------------------------------
def test_determinism(rcaeval_adapter, nezha_adapter):
    for adapter, inc_id in [
        (rcaeval_adapter, "rcaeval_re2ss_carts_cpu_1"),
        (nezha_adapter, "nezha_1661140434"),
    ]:
        run1 = adapter.load_logs(inc_id, limit=5)
        run2 = adapter.load_logs(inc_id, limit=5)
        assert len(run1) == len(run2)
        for e1, e2 in zip(run1, run2):
            assert e1 == e2, f"Non-deterministic log loading in {adapter.dataset_source}"
