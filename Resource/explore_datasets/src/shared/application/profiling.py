"""Use case: mo ta mot DataFrame theo 4 tieu chi."""

from __future__ import annotations

from typing import Any, Iterable

import pandas as pd

from src.shared.domain.models import ColumnProfile, DatasetProfile


def _sample(value: Any) -> Any:
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def profile_dataframe(
    df: pd.DataFrame,
    name: str = "dataset",
    head_n: int = 10,
    value_count_columns: Iterable[str] = (),
) -> DatasetProfile:
    """Tra ve DatasetProfile gom shape, columns, head va value_counts."""
    columns: list[ColumnProfile] = []
    for col in df.columns:
        series = df[col]
        columns.append(
            ColumnProfile(
                name=str(col),
                dtype=str(series.dtype),
                non_null=int(series.notna().sum()),
                null=int(series.isna().sum()),
                unique=int(series.nunique(dropna=True)),
                sample=_sample(series.iloc[0]) if len(series) else None,
            )
        )

    value_counts: dict[str, list[tuple[str, int]]] = {}
    for col in value_count_columns:
        if col in df.columns:
            counts = df[col].astype("string").value_counts(dropna=False).head(20)
            value_counts[col] = [(str(k), int(v)) for k, v in counts.items()]

    return DatasetProfile(
        name=name,
        n_rows=int(df.shape[0]),
        n_cols=int(df.shape[1]),
        columns=columns,
        head_rows=df.head(head_n).to_dict(orient="records"),
        value_counts=value_counts,
    )


def format_profile(profile: DatasetProfile) -> str:
    """Render DatasetProfile thanh text de doc."""
    lines: list[str] = []
    lines.append("=== " + profile.name + " ===")
    lines.append("shape: " + str((profile.n_rows, profile.n_cols)))
    lines.append("")
    lines.append("columns:")
    for c in profile.columns:
        lines.append(
            "  - " + c.name
            + " | dtype=" + c.dtype
            + " | non_null=" + str(c.non_null)
            + " | null=" + str(c.null)
            + " | unique=" + str(c.unique)
        )
    lines.append("")
    lines.append("head(" + str(len(profile.head_rows)) + "):")
    for row in profile.head_rows:
        lines.append("  " + str(row))
    lines.append("")
    lines.append("value_counts:")
    if not profile.value_counts:
        lines.append("  (khong co cot nao duoc chon)")
    for col, counts in profile.value_counts.items():
        lines.append("  " + col + ":")
        total = sum(v for _, v in counts) or 1
        for value, count in counts:
            pct = round(100.0 * count / total, 2)
            lines.append("    " + str(value) + " : " + str(count) + " (" + str(pct) + "%)")
    return chr(10).join(lines)
