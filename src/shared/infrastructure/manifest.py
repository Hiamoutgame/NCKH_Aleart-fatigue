"""Reproducibility manifest written next to each normalized dataset."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import pyarrow as pa

from src.shared.infrastructure.paths import REPOSITORY_ROOT, record_source_path

MANIFEST_NAME = "manifest.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_state() -> dict[str, Any]:
    def run(*args: str) -> str | None:
        try:
            result = subprocess.run(["git", *args], cwd=REPOSITORY_ROOT, capture_output=True, text=True, check=True)
        except (OSError, subprocess.CalledProcessError):
            return None
        return result.stdout.strip()

    status = run("status", "--porcelain")
    return {"commit": run("rev-parse", "HEAD"), "dirty": None if status is None else bool(status)}


def write_manifest(
    out_dir: Path,
    dataset_source: str,
    data_root: Path,
    inputs: Iterable[Path],
    settings: dict[str, Any],
    outputs: dict[str, Any],
    started: datetime,
) -> Path:
    finished = datetime.now(timezone.utc)
    manifest = {
        "dataset_source": dataset_source,
        "started_utc": started.isoformat(),
        "finished_utc": finished.isoformat(),
        "runtime_seconds": round((finished - started).total_seconds(), 1),
        "code": git_state(),
        "versions": {"python": platform.python_version(), "pandas": pd.__version__, "pyarrow": pa.__version__},
        "data_root": str(data_root),
        "settings": settings,
        "inputs": [
            {"path": record_source_path(path, data_root), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in sorted(set(inputs))
        ],
        "outputs": outputs,
    }
    path = Path(out_dir) / MANIFEST_NAME
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, default=str))
    return path
