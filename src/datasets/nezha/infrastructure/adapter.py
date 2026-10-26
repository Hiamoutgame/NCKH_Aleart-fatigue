"""Adapter implementation for the Nezha dataset.

Raw layout (Nezha paper data, see docs/research/05_methodology/dataset.md):
  <date>/<date>-fault_list.json   injections grouped by hour
  <date>/log/HH_MM_log.csv        one minute of logs per file (UTC)
Files at the dataset root (fault_list.json, 03_53_log.csv) are earlier sample
copies of dated files and are not read.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import OrderedDict
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

import numpy as np
import pandas as pd

from src.shared.infrastructure.drain import DrainConfig
from src.shared.infrastructure.log_table import (
    add_templates,
    frame_to_events,
    map_unique,
    open_writer,
    optional_text,
    write_incident,
)
from src.shared.infrastructure.manifest import write_manifest
from src.shared.infrastructure.paths import (
    DATASET_PATHS,
    NORMALIZED_DIR,
    record_source_path,
    resolve_source_path,
)
from src.shared.domain.canonical import (
    GroundTruth,
    Incident,
    LogEvent,
    ground_truths_to_dataframe,
    incidents_to_dataframe,
)
from src.shared.domain.ports import BaseDatasetAdapter

# Same system codes as RCAEval. Source: Nezha paper data (2022 = OnlineBoutique, 2023 = TrainTicket).
SYSTEM_BY_DATE = {
    "2022-08-22": "ob",
    "2022-08-23": "ob",
    "2023-01-29": "tt",
    "2023-01-30": "tt",
}
# Project rule, not taken from the paper: logs from 2 minutes before to 3 minutes after injection.
WINDOW_BEFORE = timedelta(minutes=2)
WINDOW_AFTER = timedelta(minutes=3)
LOG_FILE_RE = re.compile(r"^(\d{2})_(\d{2})_log\.csv$")
# A file named HH_MM holds roughly HH:MM-1:41 .. HH:MM+0:20; the margin keeps every candidate.
FILE_MARGIN = timedelta(minutes=2)
FILE_CACHE_SIZE = 12

csv.field_size_limit(sys.maxsize)

# Service regex patterns for OnlineBoutique and TrainTicket
SERVICE_PATTERNS = [
    re.compile(r"^(ts-[a-z0-9-]+-service)"),
    re.compile(
        r"^(adservice|cartservice|checkoutservice|currencyservice|emailservice|frontend|loadgenerator|paymentservice|productcatalogservice|recommendationservice|shippingservice)"
    ),
]


def map_pod_to_service(pod_name: Optional[str]) -> Optional[str]:
    """Deterministically map pod name to canonical microservice name."""
    if not pod_name or not isinstance(pod_name, str):
        return None
    for pattern in SERVICE_PATTERNS:
        match = pattern.match(pod_name)
        if match:
            return match.group(1)
    parts = pod_name.split("-")
    if len(parts) >= 3:
        return parts[0]
    return None


def parse_nezha_log_payload(raw_log: Any) -> tuple[str, Optional[str]]:
    """Parse nested JSON from Nezha's Log column.

    Returns:
        (extracted_message, severity)
    """
    if not raw_log or not isinstance(raw_log, str):
        return ("", None)

    message = raw_log
    severity = None

    try:
        outer = json.loads(raw_log)
        if isinstance(outer, dict):
            inner_val = outer.get("log")
            if isinstance(inner_val, str):
                clean_inner = inner_val.rstrip("\n")
                try:
                    inner_json = json.loads(clean_inner)
                    if isinstance(inner_json, dict):
                        message = inner_json.get("message") or clean_inner
                        severity = inner_json.get("severity") or inner_json.get("level")
                    else:
                        message = clean_inner
                except Exception:
                    message = clean_inner
            elif inner_val is not None:
                message = str(inner_val)
    except Exception:
        message = raw_log

    if severity:
        sev_str = str(severity).strip().upper()
        if sev_str in {"WARN", "WARNING"}:
            severity = "WARN"
        elif sev_str in {"ERROR", "ERR", "SEVERE", "FATAL"}:
            severity = "ERROR"
        elif sev_str in {"INFO"}:
            severity = "INFO"
        elif sev_str in {"DEBUG", "TRACE"}:
            severity = "DEBUG"
        else:
            severity = None
    else:
        severity = None

    return (message, severity)


def parse_inject_time(fault: dict[str, str]) -> datetime:
    """Injection time from the `inject_time` string, read as UTC.

    The string matches the UTC log file minutes for all 101 entries. The epoch
    `inject_timestamp` does not: on 2023-01-29 24/28 entries are about 8 hours
    early (a UTC+8 shift) and two different injections (09:03:53, 09:12:56)
    share one epoch. So the epoch is reported but never used.
    """
    return datetime.strptime(fault["inject_time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


def nezha_incident_id(fault: dict[str, str]) -> str:
    return f"nezha_{int(parse_inject_time(fault).timestamp())}"


def epoch_mismatch_seconds(fault: dict[str, str]) -> int:
    epoch = datetime.fromtimestamp(int(fault["inject_timestamp"]), tz=timezone.utc)
    return round((epoch - parse_inject_time(fault)).total_seconds())


def parse_unix_nano(value: str) -> Optional[int]:
    value = value.strip()
    return int(value) if value.isdigit() else None


class NezhaAdapter(BaseDatasetAdapter):
    """Adapter for normalizing Nezha data into Canonical Schema."""

    logs_cut_to_window = True

    def __init__(
        self, data_root: Optional[str | Path] = None, drain_config: Optional[DrainConfig] = None
    ) -> None:
        if data_root is None:
            self.data_root = DATASET_PATHS["nezha"]
        else:
            self.data_root = Path(data_root)
        self.drain_config = drain_config or DrainConfig()
        self.duplicate_faults = 0
        self._faults: Optional[list[dict[str, str]]] = None
        self._file_cache: OrderedDict[Path, tuple[pd.DataFrame, list[dict[str, Any]]]] = OrderedDict()
        self._rejected: dict[tuple[str, str], dict[str, Any]] = {}

    @property
    def dataset_source(self) -> str:
        return "nezha"

    # ------------------------------------------------------------------
    # Raw files
    # ------------------------------------------------------------------
    def locate_fault_lists(self) -> list[Path]:
        """Dated fault lists only; the root fault_list.json duplicates 2022-08-22."""
        dated = sorted(self.data_root.glob("20*/*fault_list.json"))
        if not dated:
            raise FileNotFoundError(f"No <date>/*fault_list.json found under {self.data_root}")
        return dated

    def locate_log_csvs(self) -> list[Path]:
        """Per-minute log files under <date>/log/ (metric/trace CSVs and root samples excluded)."""
        return sorted(self.data_root.glob("20*/log/*.csv"))

    def _faults_by_injection(self) -> list[dict[str, str]]:
        """One record per injection (keyed by inject_time), ordered by time. Exact duplicate entries are dropped."""
        if self._faults is None:
            seen: dict[str, dict[str, str]] = {}
            duplicates = 0
            for fault_path in self.locate_fault_lists():
                date_dir = fault_path.parent.name
                if date_dir not in SYSTEM_BY_DATE:
                    raise ValueError(f"Unknown Nezha date folder {date_dir}; add it to SYSTEM_BY_DATE")
                with fault_path.open("r", encoding="utf-8") as f:
                    fault_dict = json.load(f)
                for items in fault_dict.values():
                    for item in items:
                        record = {
                            "date": date_dir,
                            "system_id": SYSTEM_BY_DATE[date_dir],
                            "inject_timestamp": str(item["inject_timestamp"]),
                            "inject_time": str(item["inject_time"]),
                            "inject_pod": str(item.get("inject_pod", "")),
                            "inject_type": str(item.get("inject_type", "")),
                        }
                        key = nezha_incident_id(record)
                        if key in seen:
                            if seen[key] != record:
                                raise ValueError(f"Different faults share inject_time {record['inject_time']}")
                            duplicates += 1
                            continue
                        seen[key] = record
            self._faults = [seen[key] for key in sorted(seen)]
            self.duplicate_faults = duplicates
        return self._faults

    def _read_log_file(self, path: Path) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
        """All well-formed records of one CSV plus the malformed ones (never dropped silently).

        `row` is the 0-based record number, the same as the pandas index earlier
        versions used as source_row_id.
        """
        if path in self._file_cache:
            self._file_cache.move_to_end(path)
            return self._file_cache[path]
        source_file = record_source_path(path, self.data_root)
        rows: list[list[str]] = []
        numbers: list[int] = []
        rejected: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader)
            for number, record in enumerate(reader):
                if len(record) != len(header):
                    rejected.append({
                        "source_file": source_file,
                        "source_row_id": str(number),
                        "n_fields": len(record),
                        "expected_fields": len(header),
                        "preview": ",".join(record)[:200],
                    })
                    continue
                rows.append(record)
                numbers.append(number)
        frame = pd.DataFrame(rows, columns=header)
        frame["row"] = numbers
        frame["time_ns"] = pd.array([parse_unix_nano(value) for value in frame["TimeUnixNano"]], dtype="Int64")
        result = (frame, rejected)
        self._file_cache[path] = result
        if len(self._file_cache) > FILE_CACHE_SIZE:
            self._file_cache.popitem(last=False)
        for item in rejected:
            self._rejected[(item["source_file"], item["source_row_id"])] = item
        return result

    def _candidate_files(self, date_dir: str, start: datetime, end: datetime) -> list[Path]:
        candidates = []
        for path in sorted((self.data_root / date_dir / "log").glob("*.csv")):
            match = LOG_FILE_RE.match(path.name)
            if match is None:
                candidates.append(path)  # unknown name: read it rather than risk missing rows
                continue
            minute = datetime.strptime(f"{date_dir} {match[1]}:{match[2]}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
            if start - FILE_MARGIN <= minute <= end + FILE_MARGIN:
                candidates.append(path)
        return candidates

    # ------------------------------------------------------------------
    # Canonical tables
    # ------------------------------------------------------------------
    def inspect(self) -> dict[str, Any]:
        """Inspect available Nezha files, incidents, and logs."""
        fault_lists = self.locate_fault_lists()
        faults = self._faults_by_injection()
        csv_files = self.locate_log_csvs()
        return {
            "dataset_source": self.dataset_source,
            "data_root": str(self.data_root),
            "fault_list_files": [record_source_path(path, self.data_root) for path in fault_lists],
            "distinct_injections": len(faults),
            "duplicate_fault_entries": self.duplicate_faults,
            "injections_by_system": {k: int(v) for k, v in pd.Series([f["system_id"] for f in faults]).value_counts().items()},
            "log_csv_files_count": len(csv_files),
        }

    def load_incidents(self) -> list[Incident]:
        """One Incident per distinct injection across all dated fault lists."""
        incidents: list[Incident] = []
        for fault in self._faults_by_injection():
            inject_dt = parse_inject_time(fault)
            incidents.append(Incident(
                incident_id=nezha_incident_id(fault),
                dataset_source=self.dataset_source,
                system_id=fault["system_id"],
                source_case_id=fault["inject_time"],
                start_time=inject_dt - WINDOW_BEFORE,
                end_time=inject_dt + WINDOW_AFTER,
                inject_time=inject_dt,
                fault_type=fault["inject_type"],
                raw_label=f"{fault['inject_pod']}:{fault['inject_type']}",
            ))
        return incidents

    def load_ground_truth(self) -> list[GroundTruth]:
        """Load canonical GroundTruth entities for Nezha across all dates."""
        ground_truths: list[GroundTruth] = []
        for fault in self._faults_by_injection():
            pod = fault["inject_pod"]
            canonical_svc = map_pod_to_service(pod)
            ground_truths.append(GroundTruth(
                incident_id=nezha_incident_id(fault),
                label_level="pod",
                original_target=pod,
                canonical_target=canonical_svc,
                fault_type=fault["inject_type"],
                label_source="fault_list.json:inject_pod",
                mapping_status="verified" if canonical_svc else "inferred",
            ))
        return ground_truths

    def _incident(self, incident_id: str) -> tuple[Incident, str]:
        canonical_incident_id = incident_id if incident_id.startswith("nezha_") else f"nezha_{incident_id}"
        for incident, fault in zip(self.load_incidents(), self._faults_by_injection()):
            if incident.incident_id == canonical_incident_id:
                return incident, fault["date"]
        raise ValueError(f"Unknown Nezha incident {incident_id}")

    def load_log_frame(self, incident_id: str, limit: Optional[int] = None) -> pd.DataFrame:
        """Logs inside the incident window as a frame (columns of LOG_EVENTS_SCHEMA)."""
        incident, date_dir = self._incident(incident_id)
        start_ns = int(pd.Timestamp(incident.start_time).value)
        end_ns = int(pd.Timestamp(incident.end_time).value)

        parts = []
        for path in self._candidate_files(date_dir, incident.start_time, incident.end_time):
            records, _ = self._read_log_file(path)
            inside = records["time_ns"].between(start_ns, end_ns).fillna(False).astype(bool)
            if inside.any():
                part = records.loc[inside].copy()
                part["path"] = path
                parts.append(part)
        if not parts:
            return add_templates(self._empty_frame(), self.drain_config)
        raw = pd.concat(parts, ignore_index=True)
        raw = raw.sort_values("time_ns", kind="stable").reset_index(drop=True)
        if limit is not None and limit > 0:
            raw = raw.iloc[:limit]

        payloads = [parse_nezha_log_payload(value) for value in raw["Log"]]
        pods = raw["PodName"].map(optional_text)
        row_ids = raw["row"].astype(str)
        source_files = raw["path"].map(lambda path: record_source_path(path, self.data_root))
        stems = raw["path"].map(lambda path: path.stem)
        frame = pd.DataFrame({
            "log_id": incident.incident_id + "_" + stems + "_" + row_ids,
            "incident_id": incident.incident_id,
            "raw_message": [message for message, _ in payloads],
            "source_file": source_files,
            "source_row_id": row_ids,
            "raw_record_ref": source_files + "#row_" + row_ids,
            "timestamp_utc": pd.to_datetime(raw["time_ns"].astype("int64"), unit="ns", utc=True),
            "service_id": map_unique(pods.fillna(""), lambda pod: map_pod_to_service(pod or None)),
            "entity_id": pods,
            "entity_type": "pod",
            "severity": [severity for _, severity in payloads],
            "trace_id": raw["TraceID"].map(optional_text),
            "span_id": raw["SpanID"].map(optional_text),
        })
        return add_templates(frame, self.drain_config)

    @staticmethod
    def _empty_frame() -> pd.DataFrame:
        columns = ["log_id", "incident_id", "raw_message", "source_file", "source_row_id", "raw_record_ref",
                   "timestamp_utc", "service_id", "entity_id", "entity_type", "severity", "trace_id", "span_id"]
        frame = pd.DataFrame({column: pd.Series(dtype=object) for column in columns})
        frame["timestamp_utc"] = pd.Series(dtype="datetime64[ns, UTC]")
        return frame

    def load_logs(self, incident_id: str, limit: Optional[int] = None) -> list[LogEvent]:
        """Load and normalize log events for a given Nezha incident."""
        return frame_to_events(self.load_log_frame(incident_id, limit))

    # ------------------------------------------------------------------
    # Verification hooks
    # ------------------------------------------------------------------
    def log_incident_ids(self) -> list[str]:
        return [incident.incident_id for incident in self.load_incidents()]

    def read_raw_records(self, source_file: str, source_row_ids: Sequence[str]) -> dict[str, dict[str, Any]]:
        records, _ = self._read_log_file(resolve_source_path(source_file, self.data_root))
        by_row = records.set_index("row")
        result = {}
        for row_id in source_row_ids:
            record = by_row.loc[int(row_id)]
            result[row_id] = {
                "raw_message": parse_nezha_log_payload(record["Log"])[0],
                "timestamp_utc": pd.Timestamp(int(record["time_ns"]), unit="ns", tz="UTC"),
                "entity_id": optional_text(record["PodName"]),
            }
        return result

    def expected_log_rows(self, incidents: Sequence[Incident]) -> dict[str, Any]:
        """Scan every log file once and count, per incident, the raw rows inside its window."""
        windows = [
            (incident.incident_id, int(pd.Timestamp(incident.start_time).value), int(pd.Timestamp(incident.end_time).value))
            for incident in incidents
        ]
        per_incident = {incident_id: 0 for incident_id, _, _ in windows}
        rows_by_file: dict[str, np.ndarray] = {}
        raw_rows = rejected_rows = missing_time = outside = 0
        rejected: list[dict[str, Any]] = []
        for path in self.locate_log_csvs():
            records, bad = self._read_log_file(path)
            raw_rows += len(records) + len(bad)
            rejected_rows += len(bad)
            rejected.extend(bad)
            times = records["time_ns"]
            missing_time += int(times.isna().sum())
            values = times.fillna(-1).astype("int64").to_numpy()
            in_any = np.zeros(len(values), dtype=bool)
            for incident_id, start, end in windows:
                inside = (values >= start) & (values <= end)
                per_incident[incident_id] += int(inside.sum())
                in_any |= inside
            outside += int((~in_any).sum())
            if in_any.any():
                rows_by_file[record_source_path(path, self.data_root)] = np.sort(
                    records["row"].to_numpy(dtype=np.int32)[in_any]
                )
        return {
            "per_incident": per_incident,
            "rows_by_file": rows_by_file,
            "summary": {
                "raw_rows": raw_rows,
                "rejected_rows": rejected_rows,
                "rows_without_timestamp": missing_time,
                "rows_outside_every_window": outside,
                "rejected": rejected,
            },
        }

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------
    def normalize(
        self, output_dir: Optional[str | Path] = None, max_cases: Optional[int] = None
    ) -> dict[str, Any]:
        """Normalize every incident (or the first `max_cases`), one incident at a time."""
        started = datetime.now(timezone.utc)
        out_path = NORMALIZED_DIR / "nezha" if output_dir is None else Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        incidents = self.load_incidents()
        df_incidents = incidents_to_dataframe(incidents)
        df_incidents.to_parquet(out_path / "incidents.parquet", index=False)
        df_gt = ground_truths_to_dataframe(self.load_ground_truth())
        df_gt.to_parquet(out_path / "ground_truth.parquet", index=False)

        selected = incidents[:max_cases] if max_cases is not None and max_cases > 0 else incidents
        total_logs = 0
        writer = open_writer(out_path / "log_events.parquet")
        try:
            for number, incident in enumerate(selected, start=1):
                total_logs += write_incident(writer, self.load_log_frame(incident.incident_id))
                print(f"[nezha] {number}/{len(selected)} {incident.incident_id}: {total_logs:,} logs so far",
                      file=sys.stderr, flush=True)
        finally:
            writer.close()

        rejected = sorted(self._rejected.values(), key=lambda item: (item["source_file"], int(item["source_row_id"])))
        outputs = {
            "incidents": len(df_incidents),
            "ground_truth": len(df_gt),
            "log_events": total_logs,
            "incidents_with_logs": [incident.incident_id for incident in selected],
            "duplicate_fault_entries": self.duplicate_faults,
            "inject_time_source": "fault_list inject_time string, read as UTC",
            "epoch_mismatch_seconds": {
                nezha_incident_id(fault): epoch_mismatch_seconds(fault)
                for fault in self._faults_by_injection()
                if epoch_mismatch_seconds(fault) != 0
            },
            "rejected_rows_seen": rejected,
        }
        write_manifest(
            out_path, self.dataset_source, self.data_root,
            inputs=[*self.locate_fault_lists(), *self.locate_log_csvs()],
            settings={
                "drain_config": asdict(self.drain_config),
                "max_cases": max_cases,
                "window_before_seconds": WINDOW_BEFORE.total_seconds(),
                "window_after_seconds": WINDOW_AFTER.total_seconds(),
                "system_by_date": SYSTEM_BY_DATE,
            },
            outputs=outputs,
            started=started,
        )
        return {
            "dataset_source": self.dataset_source,
            "output_dir": str(out_path),
            "incidents_count": len(df_incidents),
            "ground_truth_count": len(df_gt),
            "log_events_count": total_logs,
            "duplicate_fault_entries": self.duplicate_faults,
            "rejected_rows_seen": len(rejected),
            "drain_config": asdict(self.drain_config),
        }
