"""Local-only readers for datasets already fetched into CP1 raw_data."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from datasets import load_dataset


def list_case_log_paths(rcaeval_dir: Path) -> dict[str, Path]:
    """Return ``case_id -> logs.parquet`` from a local RCAEval snapshot."""
    paths: dict[str, Path] = {}
    for path in rcaeval_dir.rglob("logs.parquet"):
        if ".cache" not in path.parts:
            paths[path.parent.name] = path
    return dict(sorted(paths.items()))


def load_case_logs(log_path: Path, columns: list[str] | None = None) -> pd.DataFrame:
    return pd.read_parquet(log_path, columns=columns)


def load_rcaeval_cases(rcaeval_dir: Path) -> pd.DataFrame:
    """Load local case metadata without contacting Hugging Face.

    RCAEval releases have used both an on-disk dataset builder and parquet
    metadata. Prefer a local parquet file when present, then the local builder.
    """
    candidates = [
        rcaeval_dir / "cases.parquet",
        rcaeval_dir / "cases" / "cases.parquet",
        rcaeval_dir / "data" / "cases.parquet",
    ]
    candidates.extend(
        path for path in rcaeval_dir.rglob("*.parquet")
        if "case" in path.name.lower() and path.name != "logs.parquet"
    )
    for candidate in dict.fromkeys(candidates):
        if candidate.exists():
            frame = pd.read_parquet(candidate)
            if "case" in frame.columns:
                return frame

    try:
        dataset = load_dataset(str(rcaeval_dir), "cases", split="train")
    except Exception as error:  # noqa: BLE001
        raise FileNotFoundError(
            "Khong tim thay local metadata cua RCAEval. Kiem tra snapshot co "
            "dataset builder/config 'cases' hoac parquet metadata hay khong."
        ) from error
    return dataset.to_pandas()


def inspect_local_source(source_dir: Path) -> dict[str, int | str]:
    files = [path for path in source_dir.rglob("*") if path.is_file() and ".cache" not in path.parts]
    return {
        "path": str(source_dir),
        "files": len(files),
        "bytes": sum(path.stat().st_size for path in files),
    }
