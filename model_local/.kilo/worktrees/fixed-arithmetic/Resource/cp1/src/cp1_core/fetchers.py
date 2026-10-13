"""Explicit local fetchers. Analysis functions never call these implicitly."""

from __future__ import annotations

import csv
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from huggingface_hub import HfApi, snapshot_download

from .paths import RAW_DATA_DIR, ensure_data_directories
from .source_registry import Source


MANIFEST_COLUMNS = [
    "source_id",
    "source_type",
    "repo_id",
    "revision",
    "local_path",
    "fetched_at",
    "notes",
]


def _record_fetch(source: Source, revision: str, local_path: Path, notes: str = "") -> None:
    manifest = RAW_DATA_DIR / "manifest.csv"
    records: dict[str, dict[str, str]] = {}
    if manifest.exists():
        with manifest.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if row.get("source_id"):
                    records[row["source_id"]] = {column: row.get(column, "") for column in MANIFEST_COLUMNS}

    records[source.source_id] = {
        "source_id": source.source_id,
        "source_type": source.type,
        "repo_id": source.repo_id or source.repo_url or "",
        "revision": revision,
        "local_path": str(local_path),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "notes": notes or source.notes or "",
    }
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        writer.writerows(records[key] for key in sorted(records))


def fetch_huggingface_dataset(source: Source) -> Path:
    if source.type != "huggingface_dataset" or not source.repo_id or not source.local_path:
        raise ValueError(f"{source.source_id} khong phai Hugging Face dataset hop le")

    ensure_data_directories()
    local_path = source.local_path
    snapshot_download(
        repo_id=source.repo_id,
        repo_type="dataset",
        revision=source.revision or "main",
        local_dir=local_path,
    )
    info = HfApi().dataset_info(source.repo_id, revision=source.revision or "main")
    _record_fetch(source, info.sha, local_path)
    return local_path


def fetch_github_repository(source: Source) -> Path:
    if source.type != "github_repository" or not source.repo_url or not source.local_path:
        raise ValueError(f"{source.source_id} khong phai GitHub repository hop le")

    ensure_data_directories()
    local_path = source.local_path
    if not local_path.exists():
        subprocess.run(["git", "clone", source.repo_url, str(local_path)], check=True)
    if not (local_path / ".git").exists():
        raise RuntimeError(f"{local_path} da ton tai nhung khong phai Git repository")
    revision = subprocess.check_output(
        ["git", "-C", str(local_path), "rev-parse", "HEAD"], text=True
    ).strip()
    _record_fetch(source, revision, local_path)
    return local_path


def fetch_source(source: Source) -> Path:
    if source.type == "huggingface_dataset":
        return fetch_huggingface_dataset(source)
    if source.type == "github_repository":
        return fetch_github_repository(source)
    raise RuntimeError(
        f"{source.source_id} chi la manifest-only: {source.notes or 'chua co URL tai hop le'}"
    )


def require_local(source: Source) -> Path:
    path = source.local_path
    if not path or not path.exists():
        raise FileNotFoundError(
            f"Chua co du lieu local cho '{source.source_id}'. Hay chay entrypoint "
            "tuong ung voi lenh 'fetch'."
        )
    return path
