"""Ports (interfaces) for LEMMA-RCA dataset."""

from __future__ import annotations

from typing import Iterator, Optional, Protocol, runtime_checkable

from .models import DownloadPlan, LemmaIncident, LemmaLogRecord


@runtime_checkable
class LemmaDownloaderPort(Protocol):
    """Port thuc hien viec tai va trich xuat du lieu tu Hugging Face LEMMA-RCA."""

    def prepare_download_plan(self, mode: str, target_dir: str) -> DownloadPlan:
        """Lap ke hoach tai (dry-run) de nguoi dung quan sat truoc khi tai."""
        ...

    def execute_download(self, plan: DownloadPlan, dry_run: bool = False) -> list[str]:
        """Thuc thi tai du lieu theo ke hoach."""
        ...


@runtime_checkable
class LemmaRepositoryPort(Protocol):
    """Port doc va truy van du lieu log/incident cua LEMMA-RCA tu dia."""

    def load_log_records(
        self,
        limit: Optional[int] = None,
        service: Optional[str] = None,
        level: Optional[str] = None,
    ) -> Iterator[LemmaLogRecord]:
        """Doc danh sach cac dong log."""
        ...

    def list_incidents(self) -> list[LemmaIncident]:
        """Liet ke cac ca su co (ground truth) duoc ghi nhan trong dataset."""
        ...

    def get_incident(self, incident_id: str) -> Optional[LemmaIncident]:
        """Doc chi tiet mot ca su co."""
        ...
