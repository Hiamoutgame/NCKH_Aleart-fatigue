"""Stable paths for CP1, independent of the terminal working directory."""

from __future__ import annotations

from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[1]
CP1_ROOT = SRC_ROOT.parent
PROJECT_ROOT = CP1_ROOT.parent
CONFIG_DIR = CP1_ROOT / "config"
RAW_DATA_DIR = CP1_ROOT / "raw_data"
HF_DATA_DIR = RAW_DATA_DIR / "huggingface"
EXTERNAL_REPOS_DIR = CP1_ROOT / "external_repos" / "github"
ARTIFACTS_DIR = CP1_ROOT / "artifacts"
DOCS_DIR = CP1_ROOT / "docs"


def artifact_dir(dataset_name: str) -> Path:
    """Create and return the output directory for one dataset."""
    path = ARTIFACTS_DIR / dataset_name
    for child in (path / "tables", path / "reports", path / "runs"):
        child.mkdir(parents=True, exist_ok=True)
    return path


def ensure_data_directories() -> None:
    HF_DATA_DIR.mkdir(parents=True, exist_ok=True)
    EXTERNAL_REPOS_DIR.mkdir(parents=True, exist_ok=True)
