"""Adapter implementation for the LEMMA-RCA dataset."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
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

from .loader import LEVEL_PATTERN, GLOG_MAP, LemmaLoader


def parse_lemma_timestamp(ts_val: Any) -> Optional[datetime]:
    """Parse LEMMA ISO timestamp string into a timezone-aware UTC datetime."""
    if not ts_val or not isinstance(ts_val, str):
        return None
    try:
        clean = ts_val.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def extract_lemma_severity(raw_level: Any, raw_msg: str) -> Optional[str]:
    """Extract explicit severity level without guessing default 'INFO'.

    If raw_level is 'unknown' or empty, inspect message for explicit regex indicators.
    Returns None if no explicit indicator is found.
    """
    if isinstance(raw_level, str) and raw_level.strip():
        lvl = raw_level.strip().upper()
        if lvl not in {"UNKNOWN", ""}:
            return "WARN" if lvl in {"WARN", "WARNING"} else lvl

    if not raw_msg:
        return None

    match = LEVEL_PATTERN.search(raw_msg)
    if match:
        gd = match.groupdict()
        if gd.get("glog"):
            return GLOG_MAP.get(gd["glog"][0])
        if gd.get("lvl"):
            l = gd["lvl"].upper()
            return "WARN" if l == "WARNING" else l

    return None


class LemmaAdapter(BaseDatasetAdapter):
    """Adapter for normalizing LEMMA-RCA data into Canonical Schema."""

    def __init__(self, data_root: Optional[str | Path] = None) -> None:
        if data_root is None:
            self.data_root = DATASET_PATHS["lemma_rca"]
        else:
            self.data_root = Path(data_root)
        self.loader = LemmaLoader(data_root=self.data_root)

    @property
    def dataset_source(self) -> str:
        return "lemma_rca"

    def inspect(self) -> dict[str, Any]:
        """Inspect available LEMMA-RCA files and metadata."""
        files = self.loader.locate_log_files()
        incidents = self.loader.list_documented_incidents()
        return {
            "dataset_source": self.dataset_source,
            "data_root": str(self.data_root),
            "log_files_count": len(files),
            "log_files": [f.name for f in files],
            "documented_incidents_count": len(incidents),
            "documented_incident_ids": [i.incident_id for i in incidents],
        }

    def load_incidents(self) -> list[Incident]:
        """Load canonical Incident entities from documented LEMMA-RCA scenarios."""
        doc_incidents = self.loader.list_documented_incidents()
        incidents: list[Incident] = []

        for inc in doc_incidents:
            start_dt = parse_lemma_timestamp(inc.start_time)
            end_dt = parse_lemma_timestamp(inc.end_time)
            inject_dt = parse_lemma_timestamp(inc.inject_time)

            incident = Incident(
                incident_id=f"lemma_{inc.incident_id}",
                dataset_source=self.dataset_source,
                system_id="book-info",
                source_case_id=inc.incident_id,
                start_time=start_dt,
                end_time=end_dt,
                inject_time=inject_dt,
                fault_type=inc.fault_type,
                raw_label=inc.root_cause_service,
            )
            incidents.append(incident)
        return incidents

    def load_ground_truth(self) -> list[GroundTruth]:
        """Load canonical GroundTruth entities for LEMMA-RCA."""
        doc_incidents = self.loader.list_documented_incidents()
        ground_truths: list[GroundTruth] = []

        for inc in doc_incidents:
            canonical_target = inc.root_cause_service.split(",")[0].split("/")[0].strip()

            gt = GroundTruth(
                incident_id=f"lemma_{inc.incident_id}",
                label_level="service",
                original_target=inc.root_cause_service,
                canonical_target=canonical_target,
                fault_type=inc.fault_type,
                label_source="LEMMA_RCA_20220606_Scenario_GroundTruth.pptx",
                mapping_status="verified",
            )
            ground_truths.append(gt)
        return ground_truths

    def load_logs(self, incident_id: str, limit: Optional[int] = None) -> list[LogEvent]:
        """Load and normalize log events for LEMMA-RCA."""
        canonical_incident_id = (
            incident_id if incident_id.startswith("lemma_") else f"lemma_{incident_id}"
        )

        files = self.loader.locate_log_files(canonical_incident_id)
        if not files:
            return []

        events: list[LogEvent] = []
        count = 0


        for file_path in files:
            rel_file = record_source_path(file_path, self.data_root)

            try:
                with file_path.open("r", encoding="utf-8", errors="replace") as handle:
                    data = json.load(handle)
            except Exception:
                continue

            hits = data.get("hits", {}).get("hits", [])
            for hit in hits:
                record_id = hit.get("_id", f"row_{count}")
                source = hit.get("_source", {})

                ts_str = source.get("@timestamp") or source.get("timestamp") or ""
                dt_utc = parse_lemma_timestamp(ts_str)

                k8s = source.get("kubernetes", {})
                container_name = k8s.get("container_name")
                pod_name = k8s.get("pod_name")

                if pod_name and any(pod_name.startswith(svc) for svc in ["reviews", "productpage", "ratings", "details", "mongodb"]):
                    parts = pod_name.split("-")
                    if len(parts) >= 3 and parts[1].startswith("v"):
                        service_id = f"{parts[0]}-{parts[1]}"
                    else:
                        service_id = parts[0]
                elif container_name and container_name not in {"istio-proxy", "proxy"}:
                    service_id = container_name
                elif pod_name:
                    service_id = pod_name.split("-")[0]
                else:
                    service_id = None

                raw_msg = source.get("message") or ""
                parsed_msg = normalize_message(raw_msg)
                template_id = (
                    hashlib.md5(parsed_msg.encode("utf-8")).hexdigest()[:12]
                    if parsed_msg
                    else None
                )

                raw_level = source.get("level")
                severity = extract_lemma_severity(raw_level, raw_msg)

                event = LogEvent(
                    log_id=f"{canonical_incident_id}_{record_id}",
                    incident_id=canonical_incident_id,
                    raw_message=raw_msg,
                    source_file=rel_file,
                    source_row_id=record_id,
                    raw_record_ref=f"{file_path.name}#{record_id}",
                    timestamp_utc=dt_utc,
                    service_id=service_id,
                    entity_id=pod_name or container_name,
                    entity_type="pod" if pod_name else "container",
                    severity=severity,
                    parsed_message=parsed_msg,
                    template_id=template_id,
                    trace_id=None,
                    span_id=None,
                )
                events.append(event)
                count += 1
                if limit is not None and count >= limit:
                    return events

        return events

    def normalize(
        self, output_dir: Optional[str | Path] = None, limit_per_incident: Optional[int] = 50000
    ) -> dict[str, Any]:
        """Normalize LEMMA-RCA data and export Parquet datasets."""
        if output_dir is None:
            out_path = NORMALIZED_DIR / "lemma_rca"
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

        # 3. Export Log Events across all available scenarios
        all_events: list[LogEvent] = []
        for inc in incidents:
            events = self.load_logs(inc.incident_id, limit=limit_per_incident)
            all_events.extend(events)

        df_logs = log_events_to_dataframe(all_events)
        logs_file = out_path / "log_events.parquet"
        df_logs.to_parquet(logs_file, index=False)

        return {
            "dataset_source": self.dataset_source,
            "output_dir": str(out_path),
            "incidents_count": len(df_incidents),
            "ground_truth_count": len(df_gt),
            "log_events_count": len(df_logs),
            "scenarios_loaded": [i.incident_id for i in incidents if len(self.loader.locate_log_files(i.incident_id)) > 0],
        }
