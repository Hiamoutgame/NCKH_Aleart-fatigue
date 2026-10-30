"""Base abstract ranker definition and service ranking data structures.

Enforces the contract that all candidate rankers return exactly one ranked result
per valid candidate service, sorted deterministically by score descending and service_id ascending.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Mapping, Sequence

from src.views.incident_view import IncidentView


@dataclass(frozen=True)
class RankedService:
    """Individual ranked service candidate with provenance and score evidence."""
    service_id: str
    score: float
    rank: int
    supporting_group_ids: tuple[str, ...]
    method: str


def sort_services_by_score(service_scores: Mapping[str, float]) -> tuple[str, ...]:
    """Deterministically sort candidate service identifiers by score descending, then service_id ascending.

    Matches the tie-breaking behavior of src.evaluation.metrics.order_by_score
    without introducing circular cross-package dependencies.
    """
    return tuple(sorted(service_scores.keys(), key=lambda service_id: (-service_scores[service_id], service_id)))


class ServiceRanker(ABC):
    """Abstract base class for all root-cause candidate ranking strategies."""
    name: str

    @abstractmethod
    def rank(
        self,
        incident_view: IncidentView,
        candidate_services: Sequence[str],
    ) -> list[RankedService]:
        """Produce a ranked list of candidate microservices for the given incident view."""
        raise NotImplementedError
