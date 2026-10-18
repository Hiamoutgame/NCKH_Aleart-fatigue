"""Domain entities and value objects for LEMMA-RCA dataset."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class LemmaLogRecord:
    """Dai dien cho mot ban ghi log duoc parse tu Elasticsearch scroll JSON cua LEMMA-RCA."""

    record_id: str
    timestamp_str: str
    service: str
    level: str  # DEBUG | INFO | WARN | ERROR | FATAL | unknown
    message: str
    pod_name: Optional[str] = None
    container_name: Optional[str] = None
    namespace: Optional[str] = None
    host: Optional[str] = None
    log_type: str = "app"  # 'app' (ung dung) hoac 'infra' (he thong / node / journald)
    raw: str = ""


@dataclass(frozen=True)
class LemmaIncident:
    """Dai dien cho mot kich ban su co / lan tiem loi trong LEMMA-RCA (Ground Truth)."""

    incident_id: str
    system: str  # book-info | sock-shop | robot-shop
    date: str
    fault_type: str  # DDoS | OOM | Storage Failure | Resource Contention | Noisy Neighbor
    root_cause_service: str
    start_time: str
    inject_time: str
    end_time: str
    description: str
    symptoms: str
    impacted_services: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DownloadItem:
    """Thong tin mot tap tin hoac file zip can tai ve trong dataset LEMMA-RCA."""

    name: str
    relative_path: str
    remote_url: str
    estimated_size_bytes: int
    is_essential: bool  # True cho sample/metadata; False cho full 13GB zip


@dataclass(frozen=True)
class DownloadPlan:
    """Ke hoach tai dataset de nguoi dung quan sat truoc khi thuc thi (dry-run)."""

    mode: str  # 'sample' (khuyen dung) | 'full' (~51GB)
    target_dir: str
    items: list[DownloadItem] = field(default_factory=list)
    total_estimated_bytes: int = 0
    notes: list[str] = field(default_factory=list)
