"""Adapter doc file thanh pandas DataFrame."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

SUPPORTED = {".csv", ".tsv", ".json", ".jsonl", ".parquet"}


def load_table(path: str | Path, **kwargs) -> pd.DataFrame:
    """Doc mot file va tra ve DataFrame. Chi doc, khong sua file goc."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError("Khong tim thay: " + str(p))
    ext = p.suffix.lower()
    if ext == ".csv":
        return pd.read_csv(p, **kwargs)
    if ext == ".tsv":
        return pd.read_csv(p, sep="\t", **kwargs)
    if ext == ".json":
        return pd.read_json(p, **kwargs)
    if ext == ".jsonl":
        return pd.read_json(p, lines=True, **kwargs)
    if ext == ".parquet":
        return pd.read_parquet(p, **kwargs)
    raise ValueError(
        "Duoi file chua ho tro: " + ext + " (ho tro: " + ", ".join(sorted(SUPPORTED)) + ")"
    )
