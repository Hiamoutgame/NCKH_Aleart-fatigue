"""Columnar log_events helpers shared by the dataset adapters.

Adapters build one pandas frame per incident with the raw columns filled in;
`add_templates` then sorts it into arrival order and adds the regex template
(G1) and the Drain template (G2). Frames are written with LOG_EVENTS_SCHEMA,
one Parquet row group per incident, so later steps can read one incident at a
time on a small machine.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Iterator, Optional, Sequence

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


def incident_row_groups(parquet_file_path: Path | str) -> dict[str, int]:
    """Map each incident_id to its Parquet row group index using column chunk statistics.

    Raises ValueError if statistics are missing or if any row group mixes multiple incidents.
    """
    parquet_path = Path(parquet_file_path)
    parquet_file = pq.ParquetFile(parquet_path)
    file_metadata = parquet_file.metadata

    incident_to_row_group_index: dict[str, int] = {}
    total_row_groups = file_metadata.num_row_groups

    for row_group_index in range(total_row_groups):
        row_group_metadata = file_metadata.row_group(row_group_index)
        incident_column_chunk = None
        for column_index in range(row_group_metadata.num_columns):
            column_chunk = row_group_metadata.column(column_index)
            if column_chunk.path_in_schema == "incident_id":
                incident_column_chunk = column_chunk
                break

        if incident_column_chunk is None or incident_column_chunk.statistics is None:
            raise ValueError(
                f"Row group {row_group_index} in {parquet_path} lacks column statistics for 'incident_id'"
            )

        column_statistics = incident_column_chunk.statistics
        if not column_statistics.has_min_max:
            raise ValueError(
                f"Row group {row_group_index} in {parquet_path} lacks min/max statistics for 'incident_id'"
            )

        minimum_incident_id = column_statistics.min
        maximum_incident_id = column_statistics.max

        if minimum_incident_id != maximum_incident_id:
            raise ValueError(
                f"Row group {row_group_index} in {parquet_path} mixes incidents: "
                f"min={minimum_incident_id!r}, max={maximum_incident_id!r}"
            )

        incident_identifier = str(minimum_incident_id)
        if incident_identifier in incident_to_row_group_index:
            previous_row_group_index = incident_to_row_group_index[incident_identifier]
            raise ValueError(
                f"Duplicate incident_id {incident_identifier!r} found across multiple row groups: "
                f"{previous_row_group_index} and {row_group_index}"
            )

        incident_to_row_group_index[incident_identifier] = row_group_index

    return incident_to_row_group_index


def iter_incident_ids(parquet_file_path: Path | str) -> Iterator[tuple[str, int]]:
    """Iterate over (incident_id, row_group_index) without reading table row data."""
    incident_mapping = incident_row_groups(parquet_file_path)
    for incident_identifier, row_group_index in incident_mapping.items():
        yield incident_identifier, row_group_index


def read_incident(
    parquet_file_path: Path | str,
    incident_identifier: str,
    columns: Optional[Sequence[str]] = None,
) -> pd.DataFrame:
    """Read all log events for a single incident directly from its designated row group."""
    parquet_path = Path(parquet_file_path)
    row_group_mapping = incident_row_groups(parquet_path)
    if incident_identifier not in row_group_mapping:
        raise KeyError(
            f"Incident {incident_identifier!r} not found in {parquet_path}. "
            f"Available incidents: {len(row_group_mapping)}"
        )

    target_row_group_index = row_group_mapping[incident_identifier]
    parquet_file = pq.ParquetFile(parquet_path)
    selected_columns = list(columns) if columns is not None else None
    arrow_table = parquet_file.read_row_group(target_row_group_index, columns=selected_columns)
    return arrow_table.to_pandas()


def iter_incident_batches(
    parquet_file_path: Path | str,
    row_group_index: int,
    columns: Optional[Sequence[str]] = None,
    batch_size: int = 20_000,
) -> Iterator[pd.DataFrame]:
    """Stream batches of log events for a given row group to minimize process memory RSS."""
    parquet_path = Path(parquet_file_path)
    parquet_file = pq.ParquetFile(parquet_path)
    selected_columns = list(columns) if columns is not None else None
    record_batch_iterator = parquet_file.iter_batches(
        batch_size=batch_size, row_groups=[row_group_index], columns=selected_columns
    )
    for record_batch in record_batch_iterator:
        yield record_batch.to_pandas()
