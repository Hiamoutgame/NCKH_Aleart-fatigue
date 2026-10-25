"""Use cases for LEMMA-RCA dataset."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from ..domain.models import DownloadPlan, LemmaIncident, LemmaLogRecord
from ..infrastructure.downloader import LemmaDownloader
from ..infrastructure.loader import LemmaLoader


def fetch_lemma_use_case(
    mode: str = "sample",
    target_dir: Optional[str | Path] = None,
    dry_run: bool = False,
) -> DownloadPlan:
    """Use case: Chuan bi va thuc thi tai dataset LEMMA-RCA (ho tro dry-run)."""
    downloader = LemmaDownloader(default_target_dir=target_dir)
    plan = downloader.prepare_download_plan(mode=mode, target_dir=target_dir)
    downloader.execute_download(plan=plan, dry_run=dry_run)
    return plan


def describe_lemma_use_case(
    data_root: Optional[str | Path] = None,
    sample_limit: Optional[int] = 10000,
) -> dict[str, Any]:
    """Use case: Mo ta dataset theo 4 tieu chi (shape, columns, head, value_counts)."""
    loader = LemmaLoader(data_root=data_root)
    rows = loader.load_canonical_rows(limit=sample_limit)
    if not rows:
        return {
            "name": "lemma_rca",
            "n_rows": 0,
            "n_cols": 0,
            "columns": [],
            "head": [],
            "value_counts": {},
            "files": [],
        }

    n_rows = len(rows)
    cols = list(rows[0].keys())
    head_rows = rows[:10]

    # Value counts cho service, level, log_type
    value_counts: dict[str, dict[str, int]] = {}
    for c in ["service", "level", "log_type"]:
        counts: dict[str, int] = {}
        for r in rows:
            val = str(r.get(c, ""))
            counts[val] = counts.get(val, 0) + 1
        sorted_counts = dict(sorted(counts.items(), key=lambda x: -x[1])[:10])
        value_counts[c] = sorted_counts

    files = [f.name for f in loader.locate_log_files()]

    return {
        "name": "LEMMA-RCA",
        "n_rows": n_rows,
        "n_cols": len(cols),
        "columns": cols,
        "head": head_rows,
        "value_counts": value_counts,
        "files": files,
        "sampled": sample_limit is not None and n_rows >= sample_limit,
    }


def list_lemma_incidents_use_case() -> list[LemmaIncident]:
    """Use case: Liet ke danh sach cac ca su co (Ground Truth)."""
    loader = LemmaLoader()
    return loader.list_documented_incidents()


def get_lemma_incident_use_case(incident_id: str) -> Optional[LemmaIncident]:
    """Use case: Doc chi tiet mot ca su co theo ID."""
    loader = LemmaLoader()
    return loader.get_incident(incident_id)


def inspect_lemma_logs_use_case(
    data_root: Optional[str | Path] = None,
    service: Optional[str] = None,
    level: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 20,
) -> list[LemmaLogRecord]:
    """Use case: Loc va xem chi tiet cac dong log theo tieu chi."""
    loader = LemmaLoader(data_root=data_root)
    records: list[LemmaLogRecord] = []
    for rec in loader.iter_log_records(limit=limit, service=service, level=level, query=query):
        records.append(rec)
    return records


def export_lemma_logs_use_case(
    output_path: str | Path,
    format: str = "csv",
    data_root: Optional[str | Path] = None,
    service: Optional[str] = None,
    level: Optional[str] = None,
    query: Optional[str] = None,
    limit: Optional[int] = None,
) -> dict[str, Any]:
    """Use case: Xuat du lieu log canonical ra file CSV hoac JSON."""
    import csv
    import json

    loader = LemmaLoader(data_root=data_root)
    rows = loader.load_canonical_rows(
        limit=limit,
        service=service,
        level=level,
        query=query,
    )

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    fmt = format.lower()
    if fmt == "csv":
        headers = (
            list(rows[0].keys())
            if rows
            else ["timestamp", "service", "level", "message", "pod", "host", "log_type", "root_cause"]
        )
        with out_file.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
    elif fmt == "json":
        with out_file.open("w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
    else:
        raise ValueError(f"Dinh dang '{format}' khong duoc ho tro. Hay chon 'csv' hoac 'json'.")

    return {
        "output_path": str(out_file),
        "total_exported": len(rows),
        "format": fmt,
    }
