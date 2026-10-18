"""Adapter implementation for the Nezha dataset."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

import pandas as pd

from src.shared.infrastructure.normalization import normalize_message
from src.shared.infrastructure.paths import DATASET_PATHS, NORMALIZED_DIR, record_source_path
from src.shared.domain.canonical import (
    GroundTruth,
    Incident,
    LogEvent,
    ground_truths_to_dataframe,
    incidents_to_dataframe,
    log_events_to_dataframe,
)
from src.shared.domain.ports import BaseDatasetAdapter

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


class NezhaAdapter(BaseDatasetAdapter):
    """Adapter for normalizing Nezha data into Canonical Schema."""

    def __init__(self, data_root: Optional[str | Path] = None) -> None:
        if data_root is None:
            self.data_root = DATASET_PATHS["nezha"]
        else:
            self.data_root = Path(data_root)

    @property
    def dataset_source(self) -> str:
        return "nezha"

    def locate_fault_list(self) -> Path:
        p = self.data_root / "fault_list.json"
        if p.exists():
            return p
        candidates = list(self.data_root.rglob("*fault_list.json"))
        if candidates:
            return candidates[0]
        raise FileNotFoundError(f"fault_list.json not found under {self.data_root}")

    def locate_log_csvs(self) -> list[Path]:
        return sorted([p for p in self.data_root.rglob("*.csv") if p.is_file()])

    def inspect(self) -> dict[str, Any]:
        """Inspect available Nezha files, incidents, and logs."""
        csv_files = self.locate_log_csvs()
        fault_path = self.locate_fault_list()

        with fault_path.open("r", encoding="utf-8") as f:
            fault_dict = json.load(f)

        total_faults = sum(len(items) for items in fault_dict.values())

        return {
            "dataset_source": self.dataset_source,
            "data_root": str(self.data_root),
            "fault_list_file": str(fault_path),
            "fault_hours_count": len(fault_dict),
            "total_fault_incidents": total_faults,
            "log_csv_files_count": len(csv_files),
            "log_csv_files": [f.name for f in csv_files],
        }

    def load_incidents(self) -> list[Incident]:
        """Load canonical Incident entities from fault_list.json."""
        fault_path = self.locate_fault_list()
        with fault_path.open("r", encoding="utf-8") as f:
            fault_dict = json.load(f)

        incidents: list[Incident] = []
        for hour_key, items in fault_dict.items():
            for item in items:
                inj_ts_str = str(item["inject_timestamp"])
                inj_ts = int(inj_ts_str)
                inject_dt = datetime.fromtimestamp(inj_ts, tz=timezone.utc)

                # Standard observation window: 2 minutes prior, 3 minutes post fault
                start_dt = inject_dt - timedelta(minutes=2)
                end_dt = inject_dt + timedelta(minutes=3)

                incident_id = f"nezha_{inj_ts_str}"
                pod = item.get("inject_pod", "")
                fault_type = item.get("inject_type", "")

                inc = Incident(
                    incident_id=incident_id,
                    dataset_source=self.dataset_source,
                    system_id="onlineboutique",
                    source_case_id=inj_ts_str,
                    start_time=start_dt,
                    end_time=end_dt,
                    inject_time=inject_dt,
                    fault_type=fault_type,
                    raw_label=f"{pod}:{fault_type}",
                )
                incidents.append(inc)
        return incidents

    def load_ground_truth(self) -> list[GroundTruth]:
        """Load canonical GroundTruth entities for Nezha."""
        fault_path = self.locate_fault_list()
        with fault_path.open("r", encoding="utf-8") as f:
            fault_dict = json.load(f)

        ground_truths: list[GroundTruth] = []
        for hour_key, items in fault_dict.items():
            for item in items:
                inj_ts_str = str(item["inject_timestamp"])
                pod = item.get("inject_pod", "")
                fault_type = item.get("inject_type", "")
                canonical_svc = map_pod_to_service(pod)

                gt = GroundTruth(
                    incident_id=f"nezha_{inj_ts_str}",
                    label_level="pod",
                    original_target=pod,
                    canonical_target=canonical_svc,
                    fault_type=fault_type,
                    label_source="fault_list.json:inject_pod",
                    mapping_status="verified" if canonical_svc else "inferred",
                )
                ground_truths.append(gt)
        return ground_truths

    def load_logs(self, incident_id: str, limit: Optional[int] = None) -> list[LogEvent]:
        """Load and normalize log events for a given Nezha incident."""
        incidents = {inc.incident_id: inc for inc in self.load_incidents()}
        canonical_incident_id = (
            incident_id if incident_id.startswith("nezha_") else f"nezha_{incident_id}"
        )
        target_inc = incidents.get(canonical_incident_id)

        csv_files = self.locate_log_csvs()
        if not csv_files:
            return []

        events: list[LogEvent] = []

        count = 0
        for csv_path in csv_files:
            rel_file = record_source_path(csv_path, self.data_root)

            df = pd.read_csv(csv_path)

            for idx, row in df.iterrows():
                # Nanosecond timestamp conversion
                nano_val = row.get("TimeUnixNano")
                if pd.notna(nano_val):
                    dt_utc = datetime.fromtimestamp(int(nano_val) / 1e9, tz=timezone.utc)
                else:
                    dt_utc = None

                # If filtering by target incident window
                if target_inc and dt_utc:
                    if target_inc.start_time and dt_utc < target_inc.start_time:
                        continue
                    if target_inc.end_time and dt_utc > target_inc.end_time:
                        continue

                pod = str(row.get("PodName", "")).strip() if pd.notna(row.get("PodName")) else None
                service_id = map_pod_to_service(pod)

                raw_log_payload = str(row.get("Log", "")) if pd.notna(row.get("Log")) else ""
                msg, severity = parse_nezha_log_payload(raw_log_payload)
                parsed_msg = normalize_message(msg)
                template_id = (
                    hashlib.md5(parsed_msg.encode("utf-8")).hexdigest()[:12]
                    if parsed_msg
                    else None
                )

                trace_id = (
                    str(row.get("TraceID")).strip()
                    if pd.notna(row.get("TraceID")) and str(row.get("TraceID")).strip()
                    else None
                )
                span_id = (
                    str(row.get("SpanID")).strip()
                    if pd.notna(row.get("SpanID")) and str(row.get("SpanID")).strip()
                    else None
                )

                row_idx_str = str(idx)
                event = LogEvent(
                    log_id=f"{canonical_incident_id}_{csv_path.stem}_{row_idx_str}",
                    incident_id=canonical_incident_id,
                    raw_message=msg,
                    source_file=rel_file,
                    source_row_id=row_idx_str,
                    raw_record_ref=f"{csv_path.name}#row_{row_idx_str}",
                    timestamp_utc=dt_utc,
                    service_id=service_id,
                    entity_id=pod,
                    entity_type="pod",
                    severity=severity,
                    parsed_message=parsed_msg,
                    template_id=template_id,
                    trace_id=trace_id,
                    span_id=span_id,
                )
                events.append(event)
                count += 1
                if limit is not None and count >= limit:
                    return events

        return events

    def normalize(self, output_dir: Optional[str | Path] = None) -> dict[str, Any]:
        """Normalize Nezha data and export Parquet datasets."""
        if output_dir is None:
            out_path = NORMALIZED_DIR / "nezha"
        else:
            out_path = Path(output_dir)

        out_path.mkdir(parents=True, exist_ok=True)

        # 1. Export Incidents
        incidents = self.load_incidents()
        df_incidents = incidents_to_dataframe(incidents)
        incidents_file = out_path / "incidents.parquet"
        df_incidents.to_parquet(incidents_file, index=False)

        # 2. Export Ground Truth
        gts = self.load_ground_truth()
        df_gt = ground_truths_to_dataframe(gts)
        gt_file = out_path / "ground_truth.parquet"
        df_gt.to_parquet(gt_file, index=False)

        # 3. Export Log Events for the first incident (or all available)
        primary_incident = incidents[0].incident_id if incidents else "nezha_default"
        events = self.load_logs(primary_incident)
        df_logs = log_events_to_dataframe(events)
        logs_file = out_path / "log_events.parquet"
        df_logs.to_parquet(logs_file, index=False)

        return {
            "dataset_source": self.dataset_source,
            "output_dir": str(out_path),
            "incidents_count": len(df_incidents),
            "ground_truth_count": len(df_gt),
            "log_events_count": len(df_logs),
            "primary_incident": primary_incident,
        }
