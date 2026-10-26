"""Dataset locations anchored to this checkout, never to the working directory."""

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPOSITORY_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
NORMALIZED_DIR = DATA_DIR / "normalized"
DATASET_PATHS = {
    "rcaeval": RAW_DATA_DIR / "huggingface" / "rcaeval",
    "nezha": RAW_DATA_DIR / "nezha",
}


def record_source_path(path: Path, data_root: Path) -> str:
    """Keep repository provenance; use paths relative to custom input roots elsewhere."""
    resolved = path.resolve()
    for root in (REPOSITORY_ROOT, data_root.resolve()):
        try:
            return resolved.relative_to(root).as_posix()
        except ValueError:
            continue
    return str(resolved)


def resolve_source_path(source_file: str, data_root: Path) -> Path:
    """Inverse of record_source_path: find the raw file a source_file value points to."""
    path = Path(source_file)
    if path.is_absolute():
        return path
    for root in (REPOSITORY_ROOT, data_root):
        if (root / path).exists():
            return root / path
    raise FileNotFoundError(f"source file {source_file} not found under {REPOSITORY_ROOT} or {data_root}")
