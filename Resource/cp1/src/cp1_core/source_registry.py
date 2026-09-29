"""Read the explicit CP1 source registry."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .paths import CONFIG_DIR, EXTERNAL_REPOS_DIR, HF_DATA_DIR


@dataclass(frozen=True)
class Source:
    source_id: str
    type: str
    local_name: str | None = None
    repo_id: str | None = None
    repo_url: str | None = None
    revision: str | None = None
    role: str | None = None
    notes: str | None = None

    @property
    def local_path(self) -> Path | None:
        if self.type == "huggingface_dataset" and self.local_name:
            return HF_DATA_DIR / self.local_name
        if self.type == "github_repository" and self.local_name:
            return EXTERNAL_REPOS_DIR / self.local_name
        return None


def load_sources() -> dict[str, Source]:
    registry_path = CONFIG_DIR / "sources.yaml"
    with registry_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    sources: dict[str, Source] = {}
    for source_id, values in (raw.get("sources") or {}).items():
        values = values or {}
        sources[source_id] = Source(source_id=source_id, **values)
    return sources


def get_source(source_id: str) -> Source:
    try:
        return load_sources()[source_id]
    except KeyError as error:
        raise ValueError(f"Khong tim thay source '{source_id}' trong config/sources.yaml") from error
