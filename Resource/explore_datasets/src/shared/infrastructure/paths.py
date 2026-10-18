"""Dataset locations anchored to this checkout, never to the working directory."""

from pathlib import Path


RESOURCE_ROOT = Path(__file__).resolve().parents[4]
REPOSITORY_ROOT = RESOURCE_ROOT.parent
RAW_DATA_DIR = RESOURCE_ROOT / "cp1" / "raw_data"
NORMALIZED_DIR = RESOURCE_ROOT / "datasets" / "normalized"
DATASET_PATHS = {
    "rcaeval": RAW_DATA_DIR / "huggingface" / "rcaeval",
    "lemma_rca": RAW_DATA_DIR / "huggingface" / "lemma_rca",
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
