"""Tests for row-group level incident streaming and metadata resolution."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.shared.infrastructure.log_table import (
    LOG_EVENT_COLUMNS,
    incident_row_groups,
    iter_incident_batches,
    iter_incident_ids,
    open_writer,
    read_incident,
    write_incident,
)
from src.shared.infrastructure.paths import NORMALIZED_DIR


def create_synthetic_incident_log_frame(
    incident_identifier: str,
    number_of_records: int,
) -> pd.DataFrame:
    """Construct a synthetic log events DataFrame for a single incident."""
    rows = []
    for index in range(number_of_records):
        rows.append({
            "log_id": f"{incident_identifier}_log_{index}",
            "incident_id": incident_identifier,
            "raw_message": f"Sample message {index} for {incident_identifier}",
            "source_file": "synthetic.log",
            "source_row_id": str(index),
            "raw_record_ref": f"ref_{index}",
            "timestamp_utc": pd.Timestamp("2023-11-14 22:00:00", tz="UTC") + pd.Timedelta(float(index), unit="s"),
            "service_id": "cartservice",
            "entity_id": "cartservice-pod",
            "entity_type": "pod",
            "severity": "WARN" if index % 2 == 0 else "ERROR",
            "parsed_message": f"Sample message <N> for {incident_identifier}",
            "template_id": f"tmpl_{index % 3}",
            "drain_template": f"Sample message <N> for {incident_identifier}",
            "drain_template_id": f"dtmpl_{index % 3}",
            "trace_id": None,
            "span_id": None,
        })
    frame = pd.DataFrame(rows)
    return frame[LOG_EVENT_COLUMNS]


def test_synthetic_incident_read_and_batch_iteration(tmp_path: Path):
    """Verify reading incidents individually and streaming in batches produces identical data."""
    parquet_target_path = tmp_path / "synthetic_log_events.parquet"
    incident_identifiers = ["incident_alpha", "incident_beta"]

    first_incident_frame = create_synthetic_incident_log_frame(incident_identifiers[0], number_of_records=50)
    second_incident_frame = create_synthetic_incident_log_frame(incident_identifiers[1], number_of_records=30)

    with open_writer(parquet_target_path) as parquet_writer:
        write_incident(parquet_writer, first_incident_frame)
        write_incident(parquet_writer, second_incident_frame)

    row_group_index_mapping = incident_row_groups(parquet_target_path)
    assert row_group_index_mapping == {"incident_alpha": 0, "incident_beta": 1}

    incident_id_pairs = list(iter_incident_ids(parquet_target_path))
    assert incident_id_pairs == [("incident_alpha", 0), ("incident_beta", 1)]

    # Full read
    read_first_frame = read_incident(parquet_target_path, "incident_alpha")
    pd.testing.assert_frame_equal(read_first_frame, first_incident_frame)

    read_second_frame = read_incident(parquet_target_path, "incident_beta", columns=["incident_id", "service_id"])
    assert list(read_second_frame.columns) == ["incident_id", "service_id"]
    assert len(read_second_frame) == 30

    # Streaming batches reconciliation
    batches_list = list(
        iter_incident_batches(
            parquet_target_path,
            row_group_index=0,
            columns=None,
            batch_size=15,
        )
    )
    assert len(batches_list) == 4  # 15 + 15 + 15 + 5 = 50 rows
    reconciled_frame = pd.concat(batches_list, ignore_index=True)
    pd.testing.assert_frame_equal(reconciled_frame, first_incident_frame)


def test_read_incident_raises_key_error_for_unknown_incident(tmp_path: Path):
    """Verify KeyError when requesting non-existent incident identifier."""
    parquet_target_path = tmp_path / "synthetic_log_events.parquet"
    sample_frame = create_synthetic_incident_log_frame("incident_existing", number_of_records=5)
    with open_writer(parquet_target_path) as parquet_writer:
        write_incident(parquet_writer, sample_frame)

    with pytest.raises(KeyError, match="Incident 'incident_nonexistent' not found"):
        read_incident(parquet_target_path, "incident_nonexistent")


def test_real_normalized_datasets_incident_row_groups_counts():
    """Verify column metadata statistics on real normalized RCAEval and Nezha datasets."""
    rcaeval_log_events_path = NORMALIZED_DIR / "rcaeval" / "log_events.parquet"
    if rcaeval_log_events_path.exists():
        rcaeval_mapping = incident_row_groups(rcaeval_log_events_path)
        assert len(rcaeval_mapping) == 359, (
            f"Expected exactly 359 row groups in RCAEval log_events, got {len(rcaeval_mapping)}"
        )

    nezha_log_events_path = NORMALIZED_DIR / "nezha" / "log_events.parquet"
    if nezha_log_events_path.exists():
        nezha_mapping = incident_row_groups(nezha_log_events_path)
        assert len(nezha_mapping) == 101, (
            f"Expected exactly 101 row groups in Nezha log_events, got {len(nezha_mapping)}"
        )
