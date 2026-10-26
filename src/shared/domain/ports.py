"""Ports and abstract base interfaces for dataset adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional, Sequence

from .canonical import GroundTruth, Incident, LogEvent


class BaseDatasetAdapter(ABC):
    """Abstract base adapter for dataset normalization."""

    # True when an incident's logs are cut from shared files by its time window.
    logs_cut_to_window: bool = False

    @property
    @abstractmethod
    def dataset_source(self) -> str:
        """The canonical dataset slug (e.g. 'rcaeval', 'nezha')."""
        ...

    @abstractmethod
    def inspect(self) -> dict[str, Any]:
        """Inspect the dataset status, files, availability, and schema metrics."""
        ...

    @abstractmethod
    def load_incidents(self) -> list[Incident]:
        """Load all canonical incidents identified in the dataset."""
        ...

    @abstractmethod
    def load_logs(self, incident_id: str, limit: Optional[int] = None) -> list[LogEvent]:
        """Load and normalize log events for a specific incident."""
        ...

    @abstractmethod
    def load_ground_truth(self) -> list[GroundTruth]:
        """Load ground truth root-cause targets for all incidents."""
        ...

    @abstractmethod
    def normalize(self, output_dir: Optional[str] = None, max_cases: Optional[int] = None) -> dict[str, Any]:
        """Normalize every incident with logs (or the first `max_cases`) and export canonical tables."""
        ...

    def log_incident_ids(self) -> list[str]:
        """Incidents that have raw logs to normalize."""
        raise NotImplementedError

    def read_raw_records(self, source_file: str, source_row_ids: Sequence[str]) -> dict[str, dict[str, Any]]:
        """Re-read raw rows by provenance: {row_id: {raw_message, timestamp_utc, entity_id}}."""
        raise NotImplementedError

    def expected_log_rows(self, incidents: Sequence[Incident]) -> dict[str, Any]:
        """What log_events must contain for these incidents, counted from raw independently:
        {"per_incident": {incident_id: n_rows}, "rows_by_file": {source_file: sorted row ids},
        "summary": {...}}."""
        raise NotImplementedError
