"""Adapter implementation for the RCAEval dataset."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

import pandas as pd

from src.shared.infrastructure.normalization import normalize_message
from src.shared.infrastructure.paths import DATASET_PATHS, NORMALIZED_DIR, record_source_path
from src.shared.infrastructure.severity import DEBUG_RE, ERROR_RE, INFO_RE, LOG4J_LEVEL_RE, WARN_RE
from src.shared.domain.canonical import (
    GroundTruth,
    Incident,
    LogEvent,
    ground_truths_to_dataframe,
    incidents_to_dataframe,
    log_events_to_dataframe,
)
from src.shared.domain.ports import BaseDatasetAdapter


def extract_explicit_severity(message: object) -> Optional[str]:
    """Extract explicit severity level from message header or keywords.

    Strictly returns None if no explicit indicator is found. Never guesses 'INFO'.
    """
    if not isinstance(message, str) or not message.strip():
        return None
    header = LOG4J_LEVEL_RE.search(message)
    if header:
        level = header.group(1).upper()
        return "WARN" if level == "WARNING" else level
    if WARN_RE.search(message):
        return "WARN"
    if ERROR_RE.search(message):
        return "ERROR"
    if DEBUG_RE.search(message):
        return "DEBUG"
    if INFO_RE.search(message):
        return "INFO"
    return None


class RCAEvalAdapter(BaseDatasetAdapter):
    """Adapter for normalizing RCAEval data into Canonical Schema."""

    def __init__(self, data_root: Optional[str | Path] = None) -> None:
        if data_root is None:
            self.data_root = DATASET_PATHS["rcaeval"]
        else:
            self.data_root = Path(data_root)

    @property
    def dataset_source(self) -> str:
        return "rcaeval"

    def _get_cases_path(self) -> Path:
        cases_file = self.data_root / "cases.parquet"
        if not cases_file.exists():
            # Check recursive
            candidates = list(self.data_root.rglob("cases.parquet"))
            if candidates:
                return candidates[0]
            raise FileNotFoundError(f"cases.parquet not found under {self.data_root}")
        return cases_file

    def list_available_log_cases(self) -> dict[str, Path]:
        """Return mapping of case_id -> logs.parquet path for locally available cases."""
        paths: dict[str, Path] = {}
        for p in self.data_root.rglob("logs.parquet"):
            case_id = p.parent.name
            paths[case_id] = p
        return dict(sorted(paths.items()))

    def inspect(self) -> dict[str, Any]:
        """Inspect RCAEval files and metadata."""
        cases_path = self._get_cases_path()
        df_cases = pd.read_parquet(cases_path)
        log_paths = self.list_available_log_cases()

        return {
            "dataset_source": self.dataset_source,
            "data_root": str(self.data_root),
            "cases_file": str(cases_path),
            "total_cases": len(df_cases),
            "cases_has_logs_metadata": int(df_cases["has_logs"].sum()),
            "cases_with_local_logs": len(log_paths),
            "available_local_case_ids": list(log_paths.keys()),
            "systems": df_cases["system"].unique().tolist(),
            "faults": df_cases["fault"].unique().tolist(),
        }

    def load_incidents(self) -> list[Incident]:
        """Load canonical Incident entities from cases.parquet."""
        cases_path = self._get_cases_path()
        df = pd.read_parquet(cases_path)

        incidents: list[Incident] = []
        for _, row in df.iterrows():
            case_id = str(row["case"])
            start_dt = (
                datetime.fromtimestamp(int(row["time_start"]), tz=timezone.utc)
                if pd.notna(row.get("time_start"))
                else None
            )
            end_dt = (
                datetime.fromtimestamp(int(row["time_end"]), tz=timezone.utc)
                if pd.notna(row.get("time_end"))
                else None
            )
            inject_dt = (
                datetime.fromtimestamp(int(row["inject_time"]), tz=timezone.utc)
                if pd.notna(row.get("inject_time"))
                else None
            )

            raw_label = (
                f"{row.get('root_cause_service')}:{row.get('fault')}"
                if pd.notna(row.get("root_cause_service"))
                else None
            )

            incident = Incident(
                incident_id=f"rcaeval_{case_id}",
                dataset_source=self.dataset_source,
                system_id=str(row.get("system", "")).lower(),
                source_case_id=case_id,
                start_time=start_dt,
                end_time=end_dt,
                inject_time=inject_dt,
                fault_type=str(row.get("fault", "")) if pd.notna(row.get("fault")) else None,
                raw_label=raw_label,
            )
            incidents.append(incident)
        return incidents

    def load_ground_truth(self) -> list[GroundTruth]:
        """Load canonical GroundTruth entities from cases.parquet."""
        cases_path = self._get_cases_path()
        df = pd.read_parquet(cases_path)

        ground_truths: list[GroundTruth] = []
        for _, row in df.iterrows():
            case_id = str(row["case"])
            rc_service = (
                str(row["root_cause_service"]) if pd.notna(row.get("root_cause_service")) else ""
            )
            fault = str(row.get("fault", "")) if pd.notna(row.get("fault")) else None

            gt = GroundTruth(
                incident_id=f"rcaeval_{case_id}",
                label_level="service",
                original_target=rc_service,
                canonical_target=rc_service if rc_service else None,
                fault_type=fault,
                label_source="cases.parquet:root_cause_service",
                mapping_status="verified" if rc_service else "missing",
            )
            ground_truths.append(gt)
        return ground_truths

    def load_logs(self, incident_id: str, limit: Optional[int] = None) -> list[LogEvent]:
        """Load and normalize log events for a given incident."""
        source_case_id = (
            incident_id[len("rcaeval_") :] if incident_id.startswith("rcaeval_") else incident_id
        )

        canonical_incident_id = (
            incident_id if incident_id.startswith("rcaeval_") else f"rcaeval_{incident_id}"
        )

        log_path = self.data_root / source_case_id / "logs.parquet"
        if not log_path.exists():
            candidates = list(self.data_root.rglob(f"{source_case_id}/logs.parquet"))
            if candidates:
                log_path = candidates[0]
            else:
                raise FileNotFoundError(f"logs.parquet for {source_case_id} not found at {log_path}")

        df = pd.read_parquet(log_path)
        if limit is not None and limit > 0:
            df = df.iloc[:limit]

        events: list[LogEvent] = []
        rel_file = record_source_path(log_path, self.data_root)

        for idx, row in df.iterrows():
            row_idx_str = str(idx)
            ts_val = row.get("timestamp")
            dt_utc = (
                datetime.fromtimestamp(int(ts_val), tz=timezone.utc)
                if pd.notna(ts_val)
                else None
            )

            container = (
                str(row["container_name"]).strip()
                if pd.notna(row.get("container_name"))
                else None
            )
            service_id = container  # In RCAEval, container_name maps directly to service

            raw_msg = str(row.get("message", "")) if pd.notna(row.get("message")) else ""
            parsed_msg = normalize_message(raw_msg)
            template_id = (
                hashlib.md5(parsed_msg.encode("utf-8")).hexdigest()[:12]
                if parsed_msg
                else None
            )

            severity = extract_explicit_severity(raw_msg)

            event = LogEvent(
                log_id=f"{canonical_incident_id}_{row_idx_str}",
                incident_id=canonical_incident_id,
                raw_message=raw_msg,
                source_file=rel_file,
                source_row_id=row_idx_str,
                raw_record_ref=f"{source_case_id}/logs.parquet#row_{row_idx_str}",
                timestamp_utc=dt_utc,
                service_id=service_id,
                entity_id=container,
                entity_type="container",
                severity=severity,
                parsed_message=parsed_msg,
                template_id=template_id,
                trace_id=None,
                span_id=None,
            )
            events.append(event)

        return events

    def normalize(self, output_dir: Optional[str | Path] = None) -> dict[str, Any]:
        """Normalize all available cases and export Parquet datasets."""
        if output_dir is None:
            out_path = NORMALIZED_DIR / "rcaeval"
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

        # 3. Export Log Events for all locally available cases
        available_cases = self.list_available_log_cases()
        all_events: list[LogEvent] = []
        for case_id in available_cases:
            events = self.load_logs(case_id)
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
            "cases_normalized": list(available_cases.keys()),
        }
