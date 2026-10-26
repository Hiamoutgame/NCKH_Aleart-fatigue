"""Integrity checks for one normalized dataset directory.

Reads log_events.parquet one row group (= one incident) at a time and compares
it with what the adapter counts from raw independently. Hard checks decide
`passed`; statistics are reported only.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from src.shared.domain.canonical import Incident
from src.shared.domain.ports import BaseDatasetAdapter
from src.shared.infrastructure.drain import template_hash
from src.shared.infrastructure.log_table import LOG_EVENTS_SCHEMA
from src.shared.infrastructure.manifest import MANIFEST_NAME

REPORT_NAME = "verification_report.json"
CHECK_COLUMNS = [
    "log_id", "incident_id", "raw_message", "source_file", "source_row_id", "timestamp_utc",
    "service_id", "entity_id", "parsed_message", "template_id", "drain_template", "drain_template_id",
]
EXAMPLES = 5


class Checks:
    """Failure count and a few examples per named check."""

    def __init__(self) -> None:
        self.failures: dict[str, int] = {}
        self.examples: dict[str, list[str]] = defaultdict(list)

    def require(self, name: str, ok: bool, example: str = "") -> None:
        self.failures.setdefault(name, 0)
        if not ok:
            self.failures[name] += 1
            if example and len(self.examples[name]) < EXAMPLES:
                self.examples[name].append(example)

    def results(self) -> list[dict[str, Any]]:
        return [
            {"check": name, "passed": count == 0, "failures": count, "examples": self.examples[name]}
            for name, count in self.failures.items()
        ]


def verify_normalized(
    adapter: BaseDatasetAdapter, dataset_dir: Path, sample_per_incident: int = 20, seed: int = 42
) -> dict[str, Any]:
    dataset_dir = Path(dataset_dir)
    checks = Checks()
    rng = np.random.default_rng(seed)
    manifest = json.loads((dataset_dir / MANIFEST_NAME).read_text())

    # Incidents and ground truth against a fresh read of raw.
    raw_incidents = {incident.incident_id: incident for incident in adapter.load_incidents()}
    raw_truth_ids = [truth.incident_id for truth in adapter.load_ground_truth()]
    incidents = pd.read_parquet(dataset_dir / "incidents.parquet")
    truths = pd.read_parquet(dataset_dir / "ground_truth.parquet")
    checks.require("incidents match raw", sorted(incidents["incident_id"]) == sorted(raw_incidents),
                   f"{len(incidents)} written vs {len(raw_incidents)} in raw")
    checks.require("incident_id unique", incidents["incident_id"].is_unique)
    checks.require("ground truth matches raw", sorted(truths["incident_id"]) == sorted(raw_truth_ids),
                   f"{len(truths)} written vs {len(raw_truth_ids)} in raw")
    checks.require("every ground truth has an incident", set(truths["incident_id"]) <= set(incidents["incident_id"]))
    targets = dict(zip(truths["incident_id"], truths["canonical_target"]))

    # Which incidents must have logs, and how many rows each, counted from raw.
    expected_ids = manifest["outputs"]["incidents_with_logs"]
    if manifest["settings"].get("max_cases") is None:
        with_logs = adapter.log_incident_ids()
        checks.require("every incident with raw logs was normalized", sorted(expected_ids) == sorted(with_logs),
                       f"{len(expected_ids)} normalized vs {len(with_logs)} with raw logs")
    expected = adapter.expected_log_rows([raw_incidents[i] for i in expected_ids])

    log_file = pq.ParquetFile(dataset_dir / "log_events.parquet")
    checks.require("log_events schema", log_file.schema_arrow.equals(LOG_EVENTS_SCHEMA, check_metadata=False))
    seen: set[str] = set()
    kept_rows: dict[str, list[np.ndarray]] = defaultdict(list)
    per_incident: list[dict[str, Any]] = []
    entity_services: set[str] = set()

    for group_index in range(log_file.num_row_groups):
        frame = log_file.read_row_group(group_index, columns=CHECK_COLUMNS).to_pandas()
        ids = frame["incident_id"].unique()
        checks.require("one incident per row group", len(ids) == 1, f"row group {group_index}: {list(ids)[:3]}")
        incident_id = str(ids[0])
        checks.require("incident written once", incident_id not in seen, incident_id)
        seen.add(incident_id)
        checks.require("log belongs to an expected incident", incident_id in expected["per_incident"], incident_id)
        checks.require("log_id unique within incident", frame["log_id"].is_unique, incident_id)
        checks.require(
            "row count matches raw", len(frame) == expected["per_incident"].get(incident_id, -1),
            f"{incident_id}: {len(frame)} written vs {expected['per_incident'].get(incident_id)} in raw",
        )
        for source_file, rows in frame.groupby("source_file")["source_row_id"]:
            kept_rows[source_file].append(rows.astype(np.int32).to_numpy())

        _check_templates(checks, frame, incident_id)
        incident = raw_incidents.get(incident_id)
        if adapter.logs_cut_to_window and incident is not None:
            inside = frame["timestamp_utc"].between(pd.Timestamp(incident.start_time), pd.Timestamp(incident.end_time))
            checks.require("log inside incident window", bool(inside.all()), f"{incident_id}: {int((~inside).sum())} outside")
        _check_sample(checks, adapter, frame, incident_id, rng, sample_per_incident)

        entity_services.update(f"{e} -> {s}" for e, s in frame[["entity_id", "service_id"]].drop_duplicates().itertuples(index=False))
        per_incident.append(_incident_stats(frame, incident_id, incident, targets))

    missing = [i for i in expected_ids if i not in seen and expected["per_incident"].get(i, 0) > 0]
    checks.require("every expected incident has logs", not missing, f"missing: {missing[:5]}")
    duplicated_rows = _check_file_rows(checks, kept_rows, expected["rows_by_file"])

    stats = pd.DataFrame(per_incident)
    summary: dict[str, Any] = {
        "incidents": len(incidents),
        "incidents_with_logs": len(seen),
        "log_events": int(log_file.metadata.num_rows),
        "raw": {key: value for key, value in expected["summary"].items() if key != "rejected"},
        "rejected_rows": expected["summary"].get("rejected", []),
        "raw_rows_in_more_than_one_incident": duplicated_rows,
        "entity_to_service": sorted(entity_services),
    }
    if len(stats):
        summary.update({
            "coverage": float(stats["target_in_logs"].mean()),
            "groups_g1_total": int(stats["groups_g1"].sum()),
            "groups_g2_total": int(stats["groups_g2"].sum()),
            "median_visible_log_reduction_g1": float(stats["reduction_g1"].median()),
            "median_visible_log_reduction_g2": float(stats["reduction_g2"].median()),
        })
    if adapter.logs_cut_to_window:
        summary["incidents_with_another_injection_in_window"] = _overlapping_injections(list(raw_incidents.values()))

    results = checks.results()
    report = {
        "dataset_source": adapter.dataset_source,
        "dataset_dir": str(dataset_dir),
        "passed": all(result["passed"] for result in results),
        "sample_per_incident": sample_per_incident,
        "seed": seed,
        "checks": results,
        "summary": summary,
        "per_incident": stats.to_dict("records"),
    }
    (dataset_dir / REPORT_NAME).write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    return report


def _check_templates(checks: Checks, frame: pd.DataFrame, incident_id: str) -> None:
    has_text = frame["parsed_message"].fillna("") != ""
    checks.require("non-empty message has template_id",
                   bool(frame.loc[has_text, "template_id"].notna().all()), incident_id)
    checks.require("non-empty message has drain_template_id",
                   bool(frame.loc[has_text, "drain_template_id"].notna().all()), incident_id)
    pairs = frame.dropna(subset=["drain_template"]).drop_duplicates(["drain_template", "drain_template_id"])
    bad = [t for t, i in zip(pairs["drain_template"], pairs["drain_template_id"]) if template_hash(t) != i]
    checks.require("drain_template_id is MD5 of drain_template", not bad, f"{incident_id}: {bad[:1]}")
    checks.require("timestamps are UTC", str(frame["timestamp_utc"].dt.tz) == "UTC", incident_id)


def _check_sample(checks: Checks, adapter, frame: pd.DataFrame, incident_id: str, rng, size: int) -> None:
    """Re-open randomly chosen rows in the raw files through their provenance."""
    if frame.empty or size <= 0:
        return
    picked = frame.iloc[np.sort(rng.choice(len(frame), size=min(size, len(frame)), replace=False))]
    for source_file, rows in picked.groupby("source_file"):
        raw = adapter.read_raw_records(source_file, list(rows["source_row_id"]))
        for row in rows.itertuples(index=False):
            original = raw[row.source_row_id]
            same = (
                original["raw_message"] == row.raw_message
                and _same_time(original["timestamp_utc"], row.timestamp_utc)
                and original["entity_id"] == (None if pd.isna(row.entity_id) else row.entity_id)
            )
            checks.require("sampled rows match raw", same, f"{incident_id}: {source_file}#row_{row.source_row_id}")


def _same_time(a, b) -> bool:
    if pd.isna(a) or pd.isna(b):
        return bool(pd.isna(a) and pd.isna(b))
    return pd.Timestamp(a) == pd.Timestamp(b)


def _check_file_rows(checks: Checks, kept: dict[str, list[np.ndarray]], expected: dict[str, np.ndarray]) -> int:
    """Every raw row that should be kept is kept, and nothing else. Returns rows kept more than once."""
    duplicated = 0
    for source_file in sorted(set(kept) | set(expected)):
        parts = kept.pop(source_file, [])
        written_all = np.concatenate(parts) if parts else np.array([], dtype=np.int32)
        written = np.unique(written_all)
        duplicated += len(written_all) - len(written)
        wanted = np.asarray(expected.get(source_file, np.array([], dtype=np.int32)))
        checks.require("raw rows kept exactly once per file", np.array_equal(written, wanted),
                       f"{source_file}: {len(written)} written vs {len(wanted)} expected")
    return duplicated


def _incident_stats(frame: pd.DataFrame, incident_id: str, incident: Incident | None, targets: dict) -> dict[str, Any]:
    n_logs = len(frame)
    groups_g1 = len(frame[["service_id", "template_id"]].drop_duplicates())
    groups_g2 = len(frame[["service_id", "drain_template_id"]].drop_duplicates())
    services = set(frame["service_id"].dropna())
    stats: dict[str, Any] = {
        "incident_id": incident_id,
        "n_logs": n_logs,
        "n_services": len(services),
        "groups_g1": groups_g1,
        "groups_g2": groups_g2,
        "reduction_g1": 1 - groups_g1 / n_logs,
        "reduction_g2": 1 - groups_g2 / n_logs,
        "target_in_logs": targets.get(incident_id) in services,
    }
    if incident is not None and incident.inject_time is not None:
        inject = pd.Timestamp(incident.inject_time)
        stats["minutes_before"] = round(max(0.0, (inject - frame["timestamp_utc"].min()).total_seconds()) / 60, 2)
        stats["minutes_after"] = round(max(0.0, (frame["timestamp_utc"].max() - inject).total_seconds()) / 60, 2)
    return stats


def _overlapping_injections(incidents: list[Incident]) -> list[str]:
    return [
        f"{incident.incident_id} contains {other.incident_id}"
        for incident in incidents
        for other in incidents
        if other is not incident and incident.start_time <= other.inject_time <= incident.end_time
    ]
