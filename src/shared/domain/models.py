"""Domain models dung chung cho moi dataset."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ColumnProfile:
    """Mo ta mot cot trong dataset."""

    name: str
    dtype: str
    non_null: int
    null: int
    unique: int | None = None
    sample: Any = None


@dataclass(frozen=True)
class DatasetProfile:
    """Ket qua profile mot dataset theo 4 tieu chi."""

    name: str
    n_rows: int
    n_cols: int
    columns: list[ColumnProfile] = field(default_factory=list)
    head_rows: list[dict[str, Any]] = field(default_factory=list)
    value_counts: dict[str, list[tuple[str, int]]] = field(default_factory=dict)
