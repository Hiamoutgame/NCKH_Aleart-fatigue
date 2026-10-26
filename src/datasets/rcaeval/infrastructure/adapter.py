"""Adapter implementation for the RCAEval dataset."""

from __future__ import annotations

import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from src.shared.infrastructure.drain import DrainConfig
from src.shared.infrastructure.log_table import (
    add_templates,
    frame_to_events,
    map_unique,
    open_writer,
    write_incident,
)
from src.shared.infrastructure.manifest import write_manifest
from src.shared.infrastructure.paths import (
    DATASET_PATHS,
    NORMALIZED_DIR,
    record_source_path,
    resolve_source_path,
)
from src.shared.infrastructure.severity import DEBUG_RE, ERROR_RE, ERR_NULL_RE, INFO_RE, LOG4J_LEVEL_RE, WARN_RE
from src.shared.domain.canonical import (
    GroundTruth,
    Incident,
    LogEvent,
    ground_truths_to_dataframe,
    incidents_to_dataframe,
)
from src.shared.domain.ports import BaseDatasetAdapter

RAW_LOG_COLUMNS = ["timestamp", "container_name", "message"]


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
    cleaned = ERR_NULL_RE.sub("", message)
    if ERROR_RE.search(cleaned):
        return "ERROR"
    if DEBUG_RE.search(message):
        return "DEBUG"
    if INFO_RE.search(message):
        return "INFO"
    return None


def raw_columns(raw: pd.DataFrame) -> pd.DataFrame:
    """raw_message, timestamp_utc and entity_id exactly as stored in log_events."""
    seconds = raw["timestamp"].astype("Float64")
    return pd.DataFrame({
        "raw_message": raw["message"].astype(object).where(raw["message"].notna(), "").astype(str),
        "timestamp_utc": pd.to_datetime(seconds, unit="s", utc=True),
        "entity_id": raw["container_name"].astype("string").str.strip(),
    }, index=raw.index)


class RCAEvalAdapter(BaseDatasetAdapter):
    """Adapter for normalizing RCAEval data into Canonical Schema."""

    def __init__(
        self, data_root: Optional[str | Path] = None, drain_config: Optional[DrainConfig] = None
    ) -> None:
        if data_root is None:
            self.data_root = DATASET_PATHS["rcaeval"]
        else:
            self.data_root = Path(data_root)
        self.drain_config = drain_config or DrainConfig()

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

    def _log_path(self, source_case_id: str) -> Path:
        log_path = self.data_root / source_case_id / "logs.parquet"
        if log_path.exists():
            return log_path
        candidates = list(self.data_root.rglob(f"{source_case_id}/logs.parquet"))
        if candidates:
            return candidates[0]
        raise FileNotFoundError(f"logs.parquet for {source_case_id} not found at {log_path}")

    def load_log_frame(self, incident_id: str, limit: Optional[int] = None) -> pd.DataFrame:
        """One incident's log_events as a frame (columns of LOG_EVENTS_SCHEMA)."""
        source_case_id = incident_id.removeprefix("rcaeval_")
        canonical_incident_id = f"rcaeval_{source_case_id}"
        log_path = self._log_path(source_case_id)

        raw = pd.read_parquet(log_path, columns=RAW_LOG_COLUMNS)
        if limit is not None and limit > 0:
            raw = raw.iloc[:limit]
        row_ids = pd.Series(raw.index.astype(str), index=raw.index)
        columns = raw_columns(raw)

        frame = pd.DataFrame({
            "log_id": f"{canonical_incident_id}_" + row_ids,
            "incident_id": canonical_incident_id,
            "raw_message": columns["raw_message"],
            "source_file": record_source_path(log_path, self.data_root),
            "source_row_id": row_ids,
            "raw_record_ref": f"{source_case_id}/logs.parquet#row_" + row_ids,
            "timestamp_utc": columns["timestamp_utc"],
            # In RCAEval, container_name maps directly to service
            "service_id": columns["entity_id"],
            "entity_id": columns["entity_id"],
            "entity_type": "container",
            "severity": map_unique(columns["raw_message"], extract_explicit_severity),
            "trace_id": None,
            "span_id": None,
        })
        return add_templates(frame, self.drain_config)

    def load_logs(self, incident_id: str, limit: Optional[int] = None) -> list[LogEvent]:
        """Load and normalize log events for a given incident."""
        return frame_to_events(self.load_log_frame(incident_id, limit))

    def log_incident_ids(self) -> list[str]:
        return [f"rcaeval_{case_id}" for case_id in self.list_available_log_cases()]

    def read_raw_records(self, source_file: str, source_row_ids: Sequence[str]) -> dict[str, dict[str, Any]]:
        raw = pd.read_parquet(resolve_source_path(source_file, self.data_root), columns=RAW_LOG_COLUMNS)
        picked = raw_columns(raw.iloc[[int(row_id) for row_id in source_row_ids]])
        return {
            row_id: {
                "raw_message": record.raw_message,
                "timestamp_utc": record.timestamp_utc,
                "entity_id": None if pd.isna(record.entity_id) else record.entity_id,
            }
            for row_id, record in zip(source_row_ids, picked.itertuples(index=False))
        }

    def expected_log_rows(self, incidents: Sequence[Incident]) -> dict[str, Any]:
        """Every raw row of each case's logs.parquet must appear once, in that case."""
        per_incident: dict[str, int] = {}
        rows_by_file: dict[str, np.ndarray] = {}
        for incident in incidents:
            log_path = self._log_path(incident.source_case_id)
            n_rows = pq.ParquetFile(log_path).metadata.num_rows
            per_incident[incident.incident_id] = n_rows
            rows_by_file[record_source_path(log_path, self.data_root)] = np.arange(n_rows, dtype=np.int32)
        return {
            "per_incident": per_incident,
            "rows_by_file": rows_by_file,
            "summary": {"raw_rows": int(sum(per_incident.values()))},
        }

    def select_balanced_cases(self, case_ids: list[str], max_cases: int) -> list[str]:
        """Select a representative balanced subset across systems."""
        df_cases = pd.read_parquet(self._get_cases_path())
        df_avail = df_cases[df_cases["case"].isin(case_ids)]
        per_sys = max(1, max_cases // 3)
        selected = []
        for sys_name in ["ob", "ss", "tt"]:
            sys_cases = df_avail[df_avail["system"] == sys_name]["case"].tolist()
            selected.extend(sys_cases[:per_sys])
        return selected

    def normalize(
        self, output_dir: Optional[str | Path] = None, max_cases: Optional[int] = None
    ) -> dict[str, Any]:
        """Normalize every case with logs (or a balanced `max_cases` subset), one incident at a time."""
        started = datetime.now(timezone.utc)
        out_path = NORMALIZED_DIR / "rcaeval" if output_dir is None else Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        df_incidents = incidents_to_dataframe(self.load_incidents())
        df_incidents.to_parquet(out_path / "incidents.parquet", index=False)
        df_gt = ground_truths_to_dataframe(self.load_ground_truth())
        df_gt.to_parquet(out_path / "ground_truth.parquet", index=False)

        available_cases = self.list_available_log_cases()
        selected_cases = list(available_cases.keys())
        if max_cases is not None and max_cases > 0 and len(selected_cases) > max_cases:
            selected_cases = self.select_balanced_cases(selected_cases, max_cases)

        total_logs = 0
        writer = open_writer(out_path / "log_events.parquet")
        try:
            for number, case_id in enumerate(selected_cases, start=1):
                total_logs += write_incident(writer, self.load_log_frame(case_id))
                print(f"[rcaeval] {number}/{len(selected_cases)} {case_id}: {total_logs:,} logs so far",
                      file=sys.stderr, flush=True)
        finally:
            writer.close()

        outputs = {
            "incidents": len(df_incidents),
            "ground_truth": len(df_gt),
            "log_events": total_logs,
            "incidents_with_logs": [f"rcaeval_{case_id}" for case_id in selected_cases],
        }
        write_manifest(
            out_path, self.dataset_source, self.data_root,
            inputs=[self._get_cases_path(), *(available_cases[case_id] for case_id in selected_cases)],
            settings={"drain_config": asdict(self.drain_config), "max_cases": max_cases},
            outputs=outputs,
            started=started,
        )
        return {
            "dataset_source": self.dataset_source,
            "output_dir": str(out_path),
            "incidents_count": len(df_incidents),
            "ground_truth_count": len(df_gt),
            "log_events_count": total_logs,
            "cases_normalized": selected_cases,
            "drain_config": asdict(self.drain_config),
        }
