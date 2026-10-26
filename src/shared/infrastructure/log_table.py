"""Columnar log_events helpers shared by the dataset adapters.

Adapters build one pandas frame per incident with the raw columns filled in;
`add_templates` then sorts it into arrival order and adds the regex template
(G1) and the Drain template (G2). Frames are written with LOG_EVENTS_SCHEMA,
one Parquet row group per incident, so later steps can read one incident at a
time on a small machine.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.shared.domain.canonical import LogEvent
from src.shared.infrastructure.drain import DrainConfig, drain_columns, template_hash
from src.shared.infrastructure.normalization import normalize_message

LOG_EVENTS_SCHEMA = pa.schema([
    ("log_id", pa.string()),
    ("incident_id", pa.string()),
    ("raw_message", pa.string()),
    ("source_file", pa.string()),
    ("source_row_id", pa.string()),
    ("raw_record_ref", pa.string()),
    ("timestamp_utc", pa.timestamp("ns", tz="UTC")),
    ("service_id", pa.string()),
    ("entity_id", pa.string()),
    ("entity_type", pa.string()),
    ("severity", pa.string()),
    ("parsed_message", pa.string()),
    ("template_id", pa.string()),
    ("drain_template", pa.string()),
    ("drain_template_id", pa.string()),
    ("trace_id", pa.string()),
    ("span_id", pa.string()),
])
LOG_EVENT_COLUMNS = LOG_EVENTS_SCHEMA.names


def map_unique(values: pd.Series, func: Callable[[Any], Any]) -> pd.Series:
    """Apply func once per distinct value; logs repeat the same text many times.

    `values` must not hold missing values (fill them first).
    """
    lookup = {value: func(value) for value in pd.unique(values)}
    return pd.Series([lookup[value] for value in values], index=values.index, dtype=object)


def add_templates(frame: pd.DataFrame, drain_config: DrainConfig) -> pd.DataFrame:
    """Sort one incident into arrival order, then add regex and Drain templates.

    The sort is stable on timestamp_utc, so rows with the same (or no)
    timestamp keep the order the adapter read them in.
    """
    frame = frame.sort_values("timestamp_utc", kind="stable", na_position="last").reset_index(drop=True)
    frame["parsed_message"] = map_unique(frame["raw_message"], normalize_message)
    frame["template_id"] = map_unique(frame["parsed_message"], lambda text: template_hash(text) if text else None)
    frame["drain_template"], frame["drain_template_id"] = drain_columns(
        frame["incident_id"], frame["log_id"], frame["parsed_message"], drain_config
    )
    return frame[LOG_EVENT_COLUMNS]


def frame_to_events(frame: pd.DataFrame) -> list[LogEvent]:
    events = []
    for row in frame[LOG_EVENT_COLUMNS].itertuples(index=False):
        data = {name: (None if _missing(value) else value) for name, value in zip(LOG_EVENT_COLUMNS, row)}
        if data["timestamp_utc"] is not None:
            # LogEvent holds a datetime (microseconds); log_events.parquet keeps nanoseconds.
            data["timestamp_utc"] = data["timestamp_utc"].to_pydatetime(warn=False)
        events.append(LogEvent(**data))
    return events


def _missing(value: Any) -> bool:
    return value is None or (not isinstance(value, str) and bool(pd.isna(value)))


def open_writer(path) -> pq.ParquetWriter:
    return pq.ParquetWriter(path, schema=LOG_EVENTS_SCHEMA, compression="snappy")


def write_incident(writer: pq.ParquetWriter, frame: pd.DataFrame) -> int:
    """Append one incident as its own row group; returns the number of rows written."""
    if frame.empty:
        return 0
    table = pa.Table.from_pandas(frame[LOG_EVENT_COLUMNS], schema=LOG_EVENTS_SCHEMA, preserve_index=False)
    writer.write_table(table, row_group_size=len(frame))
    return len(frame)


def optional_text(value: Any) -> Optional[str]:
    """Stripped string, or None for missing/blank values."""
    if _missing(value):
        return None
    text = str(value).strip()
    return text or None
