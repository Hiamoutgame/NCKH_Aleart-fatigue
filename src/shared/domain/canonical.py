"""Canonical Schema definitions for multi-dataset normalization.

Defines the core entities:
  - Incident: Represents an anomaly, failure scenario, or experiment run.
  - LogEvent: Represents an individual normalized log entry with full provenance.
  - GroundTruth: Represents ground-truth root cause labels decoupled from model inputs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Optional, Sequence
import pandas as pd


@dataclass(frozen=True)
class Incident:
    """Canonical representation of an incident or failure scenario."""

    incident_id: str
    dataset_source: str
    system_id: str
    source_case_id: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    inject_time: Optional[datetime] = None
    fault_type: Optional[str] = None
    raw_label: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Incident:
        clean = dict(data)
        for key in ("start_time", "end_time", "inject_time"):
            val = clean.get(key)
            if isinstance(val, str) and val:
                clean[key] = datetime.fromisoformat(val)
        return cls(**clean)


@dataclass(frozen=True)
class LogEvent:
    """Canonical representation of an individual normalized log event."""

    log_id: str
    incident_id: str
    raw_message: str
    source_file: str
    source_row_id: str
    raw_record_ref: str
    timestamp_utc: Optional[datetime] = None
    service_id: Optional[str] = None
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None
    severity: Optional[str] = None
    parsed_message: Optional[str] = None
    template_id: Optional[str] = None
    drain_template: Optional[str] = None
    drain_template_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LogEvent:
        clean = dict(data)
        val = clean.get("timestamp_utc")
        if isinstance(val, str) and val:
            clean["timestamp_utc"] = datetime.fromisoformat(val)
        return cls(**clean)


@dataclass(frozen=True)
class GroundTruth:
    """Canonical representation of ground-truth root-cause labels."""

    incident_id: str
    label_level: str  # e.g., 'service', 'pod', 'container', 'code_region'
    original_target: str
    canonical_target: Optional[str] = None
    fault_type: Optional[str] = None
    label_source: str = "dataset_label"
    mapping_status: str = "verified"  # 'verified', 'inferred', 'unverified', 'missing'

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GroundTruth:
        return cls(**dict(data))


def incidents_to_dataframe(incidents: Sequence[Incident]) -> pd.DataFrame:
    """Convert a sequence of Incident entities into a strongly-typed pandas DataFrame."""
    if not incidents:
        return pd.DataFrame(
            columns=[
                "incident_id",
                "dataset_source",
                "system_id",
                "source_case_id",
                "start_time",
                "end_time",
                "inject_time",
                "fault_type",
                "raw_label",
            ]
        )
    df = pd.DataFrame([item.to_dict() for item in incidents])
    for col in ("start_time", "end_time", "inject_time"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True)
    return df


def log_events_to_dataframe(events: Sequence[LogEvent]) -> pd.DataFrame:
    """Convert a sequence of LogEvent entities into a strongly-typed pandas DataFrame."""
    if not events:
        return pd.DataFrame(
            columns=[
                "log_id",
                "incident_id",
                "timestamp_utc",
                "service_id",
                "entity_id",
                "entity_type",
                "severity",
                "raw_message",
                "parsed_message",
                "template_id",
                "drain_template",
                "drain_template_id",
                "trace_id",
                "span_id",
                "source_file",
                "source_row_id",
                "raw_record_ref",
            ]
        )
    df = pd.DataFrame([item.to_dict() for item in events])
    if "timestamp_utc" in df.columns:
        df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    return df


def ground_truths_to_dataframe(ground_truths: Sequence[GroundTruth]) -> pd.DataFrame:
    """Convert a sequence of GroundTruth entities into a strongly-typed pandas DataFrame."""
    if not ground_truths:
        return pd.DataFrame(
            columns=[
                "incident_id",
                "label_level",
                "original_target",
                "canonical_target",
                "fault_type",
                "label_source",
                "mapping_status",
            ]
        )
    return pd.DataFrame([item.to_dict() for item in ground_truths])
