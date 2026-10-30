"""Unit tests for hierarchical log event grouping and streaming aggregation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.grouping import (
    GROUPS_TABLE_SCHEMA,
    aggregate_incident_groups,
    members,
)
from src.shared.infrastructure.log_table import (
    LOG_EVENT_COLUMNS,
    open_writer,
    write_incident,
)
from src.windowing import WindowConfig


def create_synthetic_log_table_file(
    parquet_target_path: Path,
    incident_identifier: str = "inc_test_1",
) -> tuple[pd.DataFrame, pd.Timestamp]:
    """Create a synthetic parquet log events table covering missing services and empty messages."""
    injection_time = pd.Timestamp("2023-11-14 22:00:00", tz="UTC")

    log_records = [
        # Group A: cartservice, standard template, both before and after fault
        {
            "log_id": "log_1", "incident_id": incident_identifier,
            "raw_message": "Connecting to redis cache 1",
            "source_file": "raw.log", "source_row_id": "1", "raw_record_ref": "r1",
            "timestamp_utc": injection_time - pd.Timedelta(30.0, unit="s"),
            "service_id": "cartservice", "entity_id": "cart-pod", "entity_type": "pod",
            "severity": "INFO", "parsed_message": "Connecting to redis cache <N>",
            "template_id": "tmpl_redis", "drain_template": "Connecting to redis cache <*>",
            "drain_template_id": "dtmpl_redis", "trace_id": None, "span_id": None,
        },
        {
            "log_id": "log_2", "incident_id": incident_identifier,
            "raw_message": "Connecting to redis cache 2",
            "source_file": "raw.log", "source_row_id": "2", "raw_record_ref": "r2",
            "timestamp_utc": injection_time + pd.Timedelta(10.0, unit="s"),
            "service_id": "cartservice", "entity_id": "cart-pod", "entity_type": "pod",
            "severity": "ERROR", "parsed_message": "Connecting to redis cache <N>",
            "template_id": "tmpl_redis", "drain_template": "Connecting to redis cache <*>",
            "drain_template_id": "dtmpl_redis", "trace_id": None, "span_id": None,
        },
        # Group B: cartservice, brand new template after alert (is_new_after == True)
        {
            "log_id": "log_3", "incident_id": incident_identifier,
            "raw_message": "Redis connection timeout failure",
            "source_file": "raw.log", "source_row_id": "3", "raw_record_ref": "r3",
            "timestamp_utc": injection_time + pd.Timedelta(15.0, unit="s"),
            "service_id": "cartservice", "entity_id": "cart-pod", "entity_type": "pod",
            "severity": "FATAL", "parsed_message": "Redis connection timeout failure",
            "template_id": "tmpl_timeout", "drain_template": "Redis connection timeout failure",
            "drain_template_id": "dtmpl_timeout", "trace_id": None, "span_id": None,
        },
        # Group C: missing service_id (None), WARN severity
        {
            "log_id": "log_4", "incident_id": incident_identifier,
            "raw_message": "Unknown node warning message",
            "source_file": "raw.log", "source_row_id": "4", "raw_record_ref": "r4",
            "timestamp_utc": injection_time + pd.Timedelta(5.0, unit="s"),
            "service_id": None, "entity_id": None, "entity_type": None,
            "severity": "WARN", "parsed_message": "Unknown node warning message",
            "template_id": "tmpl_node", "drain_template": "Unknown node warning message",
            "drain_template_id": "dtmpl_node", "trace_id": None, "span_id": None,
        },
        # Group D: empty template with non-empty raw_message -> fallback raw:md5
        {
            "log_id": "log_5", "incident_id": incident_identifier,
            "raw_message": "Raw log line without parsed template",
            "source_file": "raw.log", "source_row_id": "5", "raw_record_ref": "r5",
            "timestamp_utc": injection_time + pd.Timedelta(20.0, unit="s"),
            "service_id": "emailservice", "entity_id": "email-pod", "entity_type": "pod",
            "severity": "INFO", "parsed_message": None,
            "template_id": None, "drain_template": None,
            "drain_template_id": None, "trace_id": None, "span_id": None,
        },
        # Group E: empty template with empty raw_message -> fallback log:log_id
        {
            "log_id": "log_6", "incident_id": incident_identifier,
            "raw_message": "",
            "source_file": "raw.log", "source_row_id": "6", "raw_record_ref": "r6",
            "timestamp_utc": injection_time + pd.Timedelta(25.0, unit="s"),
            "service_id": "emailservice", "entity_id": "email-pod", "entity_type": "pod",
            "severity": None, "parsed_message": None,
            "template_id": None, "drain_template": None,
            "drain_template_id": None, "trace_id": None, "span_id": None,
        },
    ]

    frame = pd.DataFrame(log_records)[LOG_EVENT_COLUMNS]
    with open_writer(parquet_target_path) as writer:
        write_incident(writer, frame)

    return frame, injection_time


def test_batch_size_invariance_and_new_after_logic(tmp_path: Path):
    """Verify that batch_size (1, 2, or 100) produces identical grouping output tables."""
    parquet_path = tmp_path / "test_logs.parquet"
    incident_id = "inc_test_1"
    raw_frame, injection_time = create_synthetic_log_table_file(parquet_path, incident_id)

    config = WindowConfig()

    # Run with small batch sizes and large batch sizes
    frame_batch_1 = aggregate_incident_groups(
        parquet_file_path=parquet_path,
        incident_identifier=incident_id,
        row_group_index=0,
        fault_injection_timestamp=injection_time,
        grouping_method="g2",
        window_configuration=config,
        batch_size=1,
    )

    frame_batch_2 = aggregate_incident_groups(
        parquet_file_path=parquet_path,
        incident_identifier=incident_id,
        row_group_index=0,
        fault_injection_timestamp=injection_time,
        grouping_method="g2",
        window_configuration=config,
        batch_size=2,
    )

    frame_batch_100 = aggregate_incident_groups(
        parquet_file_path=parquet_path,
        incident_identifier=incident_id,
        row_group_index=0,
        fault_injection_timestamp=injection_time,
        grouping_method="g2",
        window_configuration=config,
        batch_size=100,
    )

    # Sort rows by group_id before comparison to ensure order independence
    sorted_1 = frame_batch_1.sort_values("group_id").reset_index(drop=True)
    sorted_2 = frame_batch_2.sort_values("group_id").reset_index(drop=True)
    sorted_100 = frame_batch_100.sort_values("group_id").reset_index(drop=True)

    pd.testing.assert_frame_equal(sorted_1, sorted_2)
    pd.testing.assert_frame_equal(sorted_1, sorted_100)

    # Verify is_new_after behavior:
    # Group A (redis) has 1 before and 1 after -> is_new_after MUST be False even across batches!
    redis_group = sorted_1[sorted_1["template_key"] == "dtmpl_redis"].iloc[0]
    assert redis_group["n_before"] == 1
    assert redis_group["n_after"] == 1
    assert not redis_group["is_new_after"]

    # Group B (timeout) only has logs after alert -> is_new_after MUST be True
    timeout_group = sorted_1[sorted_1["template_key"] == "dtmpl_timeout"].iloc[0]
    assert timeout_group["n_before"] == 0
    assert timeout_group["n_after"] == 1
    assert bool(timeout_group["is_new_after"])

    # Group C has None service
    unknown_service_group = sorted_1[sorted_1["template_key"] == "dtmpl_node"].iloc[0]
    assert pd.isna(unknown_service_group["service_id"])
    assert unknown_service_group["n_warn_after"] == 1

    # Group D has fallback raw:
    raw_fallback_group = sorted_1[sorted_1["template_key"].str.startswith("raw:")].iloc[0]
    assert raw_fallback_group["n_logs"] == 1

    # Group E has fallback log:
    log_fallback_group = sorted_1[sorted_1["template_key"].str.startswith("log:")].iloc[0]
    assert log_fallback_group["n_logs"] == 1


def test_members_reconstruction(tmp_path: Path):
    """Verify members() retrieves exact log rows for each group matching n_logs."""
    parquet_path = tmp_path / "test_logs.parquet"
    incident_id = "inc_test_1"
    raw_frame, injection_time = create_synthetic_log_table_file(parquet_path, incident_id)

    groups_frame = aggregate_incident_groups(
        parquet_file_path=parquet_path,
        incident_identifier=incident_id,
        row_group_index=0,
        fault_injection_timestamp=injection_time,
        grouping_method="g2",
        window_configuration=WindowConfig(),
        batch_size=3,
    )

    for _, group_record in groups_frame.iterrows():
        member_events = members(parquet_path, group_record, batch_size=2)
        assert len(member_events) == group_record["n_logs"]
        if group_record["service_id"] is not None:
            assert (member_events["service_id"] == group_record["service_id"]).all()
        else:
            assert member_events["service_id"].isna().all()
