"""Hierarchical log event grouping and summary table construction.

Constructs groups.parquet by aggregating log events into:
  - G1: (incident_id, service_id, template_id)
  - G2: (incident_id, service_id, drain_template_id)

Streaming batch aggregation ensures peak RAM remains below 500 MB on memory-constrained machines.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Mapping, Optional, Sequence

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.shared.infrastructure.log_table import (
    incident_row_groups,
    iter_incident_batches,
)
from src.shared.infrastructure.manifest import git_state, sha256_file
from src.shared.infrastructure.paths import DATA_DIR, NORMALIZED_DIR
from src.windowing.windows import WindowConfig, assign_windows, offset_seconds

GROUPS_PARQUET_NAME = "groups.parquet"
GROUPS_MANIFEST_NAME = "manifest.json"

GROUPS_TABLE_SCHEMA = pa.schema([
    ("group_id", pa.string()),
    ("method", pa.string()),
    ("incident_id", pa.string()),
    ("service_id", pa.string()),
    ("template_key", pa.string()),
    ("template_text", pa.string()),
    ("n_logs", pa.int64()),
    ("n_before", pa.int64()),
    ("n_after", pa.int64()),
    ("n_outside", pa.int64()),
    ("n_error", pa.int64()),
    ("n_warn", pa.int64()),
    ("n_unknown_severity", pa.int64()),
    ("n_error_after", pa.int64()),
    ("n_warn_after", pa.int64()),
    ("n_unknown_after", pa.int64()),
    ("first_offset_s", pa.float64()),
    ("last_offset_s", pa.float64()),
    ("first_after_offset_s", pa.float64()),
    ("is_new_after", pa.bool_()),
    ("example_log_ids", pa.list_(pa.string())),
])


@dataclass
class GroupAccumulator:
    """In-memory accumulator for streaming log event aggregation within one incident."""
    service_key: str
    template_key: str
    actual_service_id: Optional[str]
    template_text: str = ""
    n_logs: int = 0
    n_before: int = 0
    n_after: int = 0
    n_outside: int = 0
    n_error: int = 0
    n_warn: int = 0
    n_unknown_severity: int = 0
    n_error_after: int = 0
    n_warn_after: int = 0
    n_unknown_after: int = 0
    first_offset_s: float = float("inf")
    last_offset_s: float = float("-inf")
    first_after_offset_s: Optional[float] = None
    example_log_ids: list[str] = field(default_factory=list)


def compute_fallback_template_key(
    raw_message_series: pd.Series,
    log_id_series: pd.Series,
) -> pd.Series:
    """Compute fallback keys for missing template IDs using md5 of raw_message or log_id."""
    fallback_series = pd.Series("", index=raw_message_series.index, dtype=object)
    non_empty_raw_mask = raw_message_series.notna() & (raw_message_series.str.strip() != "")

    if non_empty_raw_mask.any():
        unique_raw_messages = raw_message_series[non_empty_raw_mask].unique()
        raw_to_hash_mapping = {
            message: "raw:" + hashlib.md5(message.encode("utf-8")).hexdigest()[:12]
            for message in unique_raw_messages
        }
        fallback_series.loc[non_empty_raw_mask] = raw_message_series[non_empty_raw_mask].map(
            raw_to_hash_mapping
        )

    empty_raw_mask = ~non_empty_raw_mask
    if empty_raw_mask.any():
        fallback_series.loc[empty_raw_mask] = "log:" + log_id_series[empty_raw_mask].astype(str)

    return fallback_series


def extract_batch_template_keys(
    batch_frame: pd.DataFrame,
    grouping_method: str,
) -> tuple[pd.Series, pd.Series]:
    """Extract (template_key, template_text) series for a batch under method 'g1' or 'g2'."""
    method_key = grouping_method.lower().strip()
    if method_key == "g1":
        candidate_key_series = batch_frame["template_id"].copy()
        primary_text_series = batch_frame["parsed_message"].fillna("").astype(str)
    elif method_key == "g2":
        candidate_key_series = batch_frame["drain_template_id"].copy()
        primary_text_series = batch_frame["drain_template"].fillna("").astype(str)
    else:
        raise ValueError(f"Unsupported grouping method: {grouping_method!r}. Expected 'g1' or 'g2'.")

    raw_messages = batch_frame["raw_message"].fillna("").astype(str)
    missing_key_mask = candidate_key_series.isna() | (candidate_key_series.astype(str).str.strip() == "")
    if missing_key_mask.any():
        fallback_keys = compute_fallback_template_key(
            raw_message_series=raw_messages.loc[missing_key_mask],
            log_id_series=batch_frame["log_id"].loc[missing_key_mask],
        )
        candidate_key_series.loc[missing_key_mask] = fallback_keys

    final_template_key_series = candidate_key_series.astype(str)

    # template_text selection
    template_text_series = primary_text_series.copy()
    empty_text_mask = template_text_series.str.strip() == ""
    if empty_text_mask.any():
        template_text_series.loc[empty_text_mask] = raw_messages.loc[empty_text_mask].str[:300]

    return final_template_key_series, template_text_series


def aggregate_incident_groups(
    parquet_file_path: Path | str,
    incident_identifier: str,
    row_group_index: int,
    fault_injection_timestamp: pd.Timestamp | str | int | float,
    grouping_method: str,
    window_configuration: Optional[WindowConfig] = None,
    batch_size: int = 20_000,
) -> pd.DataFrame:
    """Aggregate log events of an incident into group summaries using streaming batches."""
    required_columns = [
        "log_id",
        "incident_id",
        "raw_message",
        "timestamp_utc",
        "service_id",
        "severity",
        "parsed_message",
        "template_id",
        "drain_template",
        "drain_template_id",
    ]

    effective_window_config = window_configuration or WindowConfig()
    accumulator_dictionary: dict[tuple[str, str], GroupAccumulator] = {}
    total_incident_log_count = 0

    batch_generator = iter_incident_batches(
        parquet_file_path=parquet_file_path,
        row_group_index=row_group_index,
        columns=required_columns,
        batch_size=batch_size,
    )

    for batch_frame in batch_generator:
        batch_row_count = len(batch_frame)
        if batch_row_count == 0:
            continue
        total_incident_log_count += batch_row_count

        template_key_series, template_text_series = extract_batch_template_keys(
            batch_frame=batch_frame,
            grouping_method=grouping_method,
        )

        raw_services = batch_frame["service_id"]
        service_key_series = raw_services.fillna("").astype(str)

        signed_offsets_series = offset_seconds(
            timestamps_series=batch_frame["timestamp_utc"],
            fault_injection_timestamp=fault_injection_timestamp,
        )
        window_labels_series = assign_windows(
            timestamps_series=batch_frame["timestamp_utc"],
            fault_injection_timestamp=fault_injection_timestamp,
            window_configuration=effective_window_config,
        )

        normalized_severity = batch_frame["severity"].fillna("").astype(str).str.upper()
        is_error_series = normalized_severity.isin(["ERROR", "FATAL"])
        is_warn_series = normalized_severity == "WARN"
        is_unknown_severity_series = (~is_error_series) & (~is_warn_series)

        is_after_series = window_labels_series == "after"
        is_before_series = window_labels_series == "before"
        is_outside_series = window_labels_series == "outside"

        is_error_after_series = is_error_series & is_after_series
        is_warn_after_series = is_warn_series & is_after_series
        is_unknown_after_series = is_unknown_severity_series & is_after_series

        first_after_offset_series = signed_offsets_series.where(is_after_series)

        batch_work_frame = pd.DataFrame({
            "service_key": service_key_series,
            "template_key": template_key_series,
            "template_text": template_text_series,
            "log_id": batch_frame["log_id"].astype(str),
            "service_id": raw_services,
            "offset_s": signed_offsets_series,
            "first_after_offset_s": first_after_offset_series,
            "is_before": is_before_series.astype(int),
            "is_after": is_after_series.astype(int),
            "is_outside": is_outside_series.astype(int),
            "is_error": is_error_series.astype(int),
            "is_warn": is_warn_series.astype(int),
            "is_unknown": is_unknown_severity_series.astype(int),
            "is_error_after": is_error_after_series.astype(int),
            "is_warn_after": is_warn_after_series.astype(int),
            "is_unknown_after": is_unknown_after_series.astype(int),
        })

        # Aggregate batch by (service_key, template_key)
        grouped = batch_work_frame.groupby(["service_key", "template_key"], sort=False)

        aggregated_batch_stats = grouped.agg(
            n_logs=("log_id", "count"),
            n_before=("is_before", "sum"),
            n_after=("is_after", "sum"),
            n_outside=("is_outside", "sum"),
            n_error=("is_error", "sum"),
            n_warn=("is_warn", "sum"),
            n_unknown_severity=("is_unknown", "sum"),
            n_error_after=("is_error_after", "sum"),
            n_warn_after=("is_warn_after", "sum"),
            n_unknown_after=("is_unknown_after", "sum"),
            first_offset_s=("offset_s", "min"),
            last_offset_s=("offset_s", "max"),
            first_after_offset_s=("first_after_offset_s", "min"),
            first_service_id=("service_id", "first"),
            first_template_text=("template_text", "first"),
        )

        for (service_key, template_key), stats_row in aggregated_batch_stats.iterrows():
            group_lookup_key = (str(service_key), str(template_key))
            if group_lookup_key not in accumulator_dictionary:
                raw_service_value = stats_row["first_service_id"]
                service_identifier = (
                    None
                    if (pd.isna(raw_service_value) or str(raw_service_value).strip() == "")
                    else str(raw_service_value).strip()
                )
                accumulator = GroupAccumulator(
                    service_key=str(service_key),
                    template_key=str(template_key),
                    actual_service_id=service_identifier,
                    template_text=str(stats_row["first_template_text"]),
                )
                accumulator_dictionary[group_lookup_key] = accumulator
            else:
                accumulator = accumulator_dictionary[group_lookup_key]
                if not accumulator.template_text and stats_row["first_template_text"]:
                    accumulator.template_text = str(stats_row["first_template_text"])

            accumulator.n_logs += int(stats_row["n_logs"])
            accumulator.n_before += int(stats_row["n_before"])
            accumulator.n_after += int(stats_row["n_after"])
            accumulator.n_outside += int(stats_row["n_outside"])
            accumulator.n_error += int(stats_row["n_error"])
            accumulator.n_warn += int(stats_row["n_warn"])
            accumulator.n_unknown_severity += int(stats_row["n_unknown_severity"])
            accumulator.n_error_after += int(stats_row["n_error_after"])
            accumulator.n_warn_after += int(stats_row["n_warn_after"])
            accumulator.n_unknown_after += int(stats_row["n_unknown_after"])

            batch_min_offset = stats_row["first_offset_s"]
            if pd.notna(batch_min_offset) and batch_min_offset < accumulator.first_offset_s:
                accumulator.first_offset_s = float(batch_min_offset)

            batch_max_offset = stats_row["last_offset_s"]
            if pd.notna(batch_max_offset) and batch_max_offset > accumulator.last_offset_s:
                accumulator.last_offset_s = float(batch_max_offset)

            batch_after_offset = stats_row["first_after_offset_s"]
            if pd.notna(batch_after_offset):
                if (
                    accumulator.first_after_offset_s is None
                    or batch_after_offset < accumulator.first_after_offset_s
                ):
                    accumulator.first_after_offset_s = float(batch_after_offset)

        # Collect example log IDs up to 3 per group
        for (service_key, template_key), subgroup in grouped:
            group_lookup_key = (str(service_key), str(template_key))
            accumulator = accumulator_dictionary[group_lookup_key]
            if len(accumulator.example_log_ids) < 3:
                remaining_quota = 3 - len(accumulator.example_log_ids)
                log_ids_to_add = subgroup["log_id"].iloc[:remaining_quota].tolist()
                accumulator.example_log_ids.extend(log_ids_to_add)

    output_records: list[dict[str, Any]] = []
    for (service_key, template_key), accumulator in accumulator_dictionary.items():
        # Hash group_id stably
        key_identity_string = f"{incident_identifier}|{service_key}|{template_key}"
        group_hash = hashlib.md5(key_identity_string.encode("utf-8")).hexdigest()[:16]
        generated_group_id = f"{grouping_method}:{group_hash}"

        is_new_after = bool((accumulator.n_before == 0) and (accumulator.n_after > 0))
        resolved_first_offset = (
            None if np.isinf(accumulator.first_offset_s) else accumulator.first_offset_s
        )
        resolved_last_offset = (
            None if np.isinf(accumulator.last_offset_s) else accumulator.last_offset_s
        )

        output_records.append({
            "group_id": generated_group_id,
            "method": grouping_method,
            "incident_id": incident_identifier,
            "service_id": accumulator.actual_service_id,
            "template_key": accumulator.template_key,
            "template_text": accumulator.template_text,
            "n_logs": accumulator.n_logs,
            "n_before": accumulator.n_before,
            "n_after": accumulator.n_after,
            "n_outside": accumulator.n_outside,
            "n_error": accumulator.n_error,
            "n_warn": accumulator.n_warn,
            "n_unknown_severity": accumulator.n_unknown_severity,
            "n_error_after": accumulator.n_error_after,
            "n_warn_after": accumulator.n_warn_after,
            "n_unknown_after": accumulator.n_unknown_after,
            "first_offset_s": resolved_first_offset,
            "last_offset_s": resolved_last_offset,
            "first_after_offset_s": accumulator.first_after_offset_s,
            "is_new_after": is_new_after,
            "example_log_ids": accumulator.example_log_ids,
        })

    groups_dataframe = pd.DataFrame(output_records)
    if groups_dataframe.empty:
        empty_table = pa.Table.from_batches([], schema=GROUPS_TABLE_SCHEMA)
        return empty_table.to_pandas()

    # Hard invariant checks
    summed_logs = int(groups_dataframe["n_logs"].sum())
    if summed_logs != total_incident_log_count:
        raise ValueError(
            f"Integrity check failed for {incident_identifier}: "
            f"sum(n_logs)={summed_logs} != incident total rows {total_incident_log_count}"
        )

    partition_sum = (
        groups_dataframe["n_before"] + groups_dataframe["n_after"] + groups_dataframe["n_outside"]
    )
    if not (partition_sum == groups_dataframe["n_logs"]).all():
        raise ValueError(
            f"Integrity check failed for {incident_identifier}: "
            f"n_before + n_after + n_outside != n_logs"
        )

    if not groups_dataframe["group_id"].is_unique:
        raise ValueError(
            f"Integrity check failed for {incident_identifier}: "
            f"duplicate group_id detected"
        )

    return groups_dataframe


def build_groups(
    dataset_slug: str,
    grouping_method: str,
    window_configuration: Optional[WindowConfig] = None,
    normalized_root_directory: Optional[Path | str] = None,
    artifacts_root_directory: Optional[Path | str] = None,
    batch_size: int = 20_000,
    verbose: bool = True,
) -> tuple[Path, Path]:
    """Build groups.parquet and manifest.json under data/artifacts/<dataset>/groups_<method>/."""
    normalized_root = Path(normalized_root_directory or NORMALIZED_DIR)
    dataset_directory = normalized_root / dataset_slug
    log_events_parquet_path = dataset_directory / "log_events.parquet"
    incidents_parquet_path = dataset_directory / "incidents.parquet"

    if not log_events_parquet_path.exists():
        raise FileNotFoundError(f"log_events.parquet not found at {log_events_parquet_path}")
    if not incidents_parquet_path.exists():
        raise FileNotFoundError(f"incidents.parquet not found at {incidents_parquet_path}")

    window_config = window_configuration or WindowConfig()
    artifacts_root = Path(artifacts_root_directory or (DATA_DIR / "artifacts"))
    output_target_directory = artifacts_root / dataset_slug / f"groups_{grouping_method}"
    output_target_directory.mkdir(parents=True, exist_ok=True)

    output_parquet_path = output_target_directory / GROUPS_PARQUET_NAME
    output_manifest_path = output_target_directory / GROUPS_MANIFEST_NAME

    # Load incident injection times
    incidents_metadata = pd.read_parquet(
        incidents_parquet_path,
        columns=["incident_id", "inject_time"],
    ).set_index("incident_id")

    incident_groups_mapping = incident_row_groups(log_events_parquet_path)
    total_groups_created = 0
    total_logs_processed = 0
    total_incident_count = len(incident_groups_mapping)

    with pq.ParquetWriter(output_parquet_path, schema=GROUPS_TABLE_SCHEMA, compression="snappy") as parquet_writer:
        for index, (incident_identifier, row_group_index) in enumerate(incident_groups_mapping.items(), start=1):
            if incident_identifier not in incidents_metadata.index:
                raise KeyError(f"Incident {incident_identifier} missing in incidents.parquet")

            inject_time = incidents_metadata.loc[incident_identifier, "inject_time"]

            incident_groups_frame = aggregate_incident_groups(
                parquet_file_path=log_events_parquet_path,
                incident_identifier=incident_identifier,
                row_group_index=row_group_index,
                fault_injection_timestamp=inject_time,
                grouping_method=grouping_method,
                window_configuration=window_config,
                batch_size=batch_size,
            )

            total_groups_created += len(incident_groups_frame)
            total_logs_processed += int(incident_groups_frame["n_logs"].sum())

            arrow_table = pa.Table.from_pandas(
                incident_groups_frame,
                schema=GROUPS_TABLE_SCHEMA,
                preserve_index=False,
            )
            parquet_writer.write_table(arrow_table, row_group_size=len(incident_groups_frame))

            if verbose and (index % 10 == 0 or index == total_incident_count):
                print(
                    f"[{index}/{total_incident_count}] Processed {incident_identifier}: "
                    f"{len(incident_groups_frame)} groups, {int(incident_groups_frame['n_logs'].sum())} logs",
                    flush=True,
                )

    manifest_payload: dict[str, Any] = {
        "generated_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "dataset_slug": dataset_slug,
        "grouping_method": grouping_method,
        "window_config": {
            "before_seconds": window_config.before_seconds,
            "after_seconds": window_config.after_seconds,
        },
        "batch_size": batch_size,
        "total_incidents": len(incident_groups_mapping),
        "total_groups": total_groups_created,
        "total_logs": total_logs_processed,
        "sha256": sha256_file(output_parquet_path),
        "git_state": git_state(),
    }
    output_manifest_path.write_text(json.dumps(manifest_payload, indent=2, ensure_ascii=False) + "\n")

    return output_parquet_path, output_manifest_path


def members(
    log_events_parquet_path: Path | str,
    group_record: Mapping[str, Any] | pd.Series,
    batch_size: int = 20_000,
) -> pd.DataFrame:
    """Stream and filter matching log events for a given group summary record without materializing full table."""
    incident_identifier = str(group_record["incident_id"])
    target_service_id = group_record["service_id"]
    target_template_key = str(group_record["template_key"])
    grouping_method = str(group_record["method"])

    row_group_index_mapping = incident_row_groups(log_events_parquet_path)
    if incident_identifier not in row_group_index_mapping:
        raise KeyError(f"Incident {incident_identifier} not found in {log_events_parquet_path}")

    target_row_group = row_group_index_mapping[incident_identifier]
    batch_iterator = iter_incident_batches(
        parquet_file_path=log_events_parquet_path,
        row_group_index=target_row_group,
        columns=None,
        batch_size=batch_size,
    )

    matching_batches: list[pd.DataFrame] = []
    for batch_frame in batch_iterator:
        template_keys, _ = extract_batch_template_keys(
            batch_frame=batch_frame,
            grouping_method=grouping_method,
        )

        template_match_mask = template_keys == target_template_key
        if target_service_id is None or pd.isna(target_service_id) or str(target_service_id).strip() == "":
            service_match_mask = (
                batch_frame["service_id"].isna() | (batch_frame["service_id"].str.strip() == "")
            )
        else:
            service_match_mask = batch_frame["service_id"] == str(target_service_id)

        combined_mask = template_match_mask & service_match_mask
        if combined_mask.any():
            matching_batches.append(batch_frame[combined_mask])

    if not matching_batches:
        return pd.DataFrame(columns=batch_frame.columns)
    return pd.concat(matching_batches, ignore_index=True)
