"""Ports and abstract base interfaces for dataset adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional, Sequence

from .canonical import GroundTruth, Incident, LogEvent


class BaseDatasetAdapter(ABC):
    """Abstract base adapter for dataset normalization."""

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
    def normalize(self, output_dir: Optional[str] = None) -> dict[str, Any]:
        """Execute normalization across available incidents and export canonical datasets."""
        ...
