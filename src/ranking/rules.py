"""Rule-based zero-shot ranking heuristic baselines (R1, R2, R3).

Implements:
  - R1 MostLogsAfter: Ranks microservices by descending post-alert log volume.
  - R2 MostErrorsAfter: Ranks microservices by descending post-alert ERROR/FATAL log volume.
  - R3 GrowthAfter: Ranks microservices by relative post-alert log growth ratio.
"""

from __future__ import annotations

from typing import Sequence

from src.ranking.base import RankedService, ServiceRanker, sort_services_by_score
from src.views.incident_view import GroupSummary, IncidentView

DEFAULT_EVIDENCE_SPECIFICATION = "evidence:new>error>count"


def select_supporting_group_ids(
    group_summaries: Sequence[GroupSummary],
    maximum_evidence_count: int = 3,
) -> tuple[str, ...]:
    """Select top evidence group IDs prioritizing new templates, error density, and total count."""
    if not group_summaries:
        return ()
    sorted_summaries = sorted(
        group_summaries,
        key=lambda group: (
            0 if group.is_new_after else 1,
            -group.n_error_after,
            -group.n_after,
            group.group_id,
        ),
    )
    return tuple(group.group_id for group in sorted_summaries[:maximum_evidence_count])


def assemble_ranked_services(
    service_scores: dict[str, float],
    incident_view: IncidentView,
    ranker_name: str,
) -> list[RankedService]:
    """Sort candidates by score and construct RankedService records with evidence."""
    sorted_candidate_ids = sort_services_by_score(service_scores)
    service_view_lookup = {
        service_view.service_id: service_view for service_view in incident_view.services
    }

    ranked_services_list: list[RankedService] = []
    for rank_position, service_id in enumerate(sorted_candidate_ids, start=1):
        score_value = service_scores[service_id]
        service_view = service_view_lookup.get(service_id)
        supporting_groups = (
            select_supporting_group_ids(service_view.groups) if service_view is not None else ()
        )
        provenance_method = f"{ranker_name}|{DEFAULT_EVIDENCE_SPECIFICATION}"

        ranked_services_list.append(RankedService(
            service_id=service_id,
            score=score_value,
            rank=rank_position,
            supporting_group_ids=supporting_groups,
            method=provenance_method,
        ))

    return ranked_services_list


class MostLogsAfterRanker(ServiceRanker):
    """R1: Ranks services by post-alert log count."""
    name: str = "r1"

    def rank(
        self,
        incident_view: IncidentView,
        candidate_services: Sequence[str],
    ) -> list[RankedService]:
        unique_candidates = list(dict.fromkeys(candidate_services))
        service_view_lookup = {
            service_view.service_id: service_view for service_view in incident_view.services
        }

        service_scores: dict[str, float] = {}
        for service_id in unique_candidates:
            service_view = service_view_lookup.get(service_id)
            service_scores[service_id] = float(service_view.n_after) if service_view else 0.0

        return assemble_ranked_services(service_scores, incident_view, self.name)


class MostErrorsAfterRanker(ServiceRanker):
    """R2: Ranks services by post-alert ERROR/FATAL count."""
    name: str = "r2"

    def rank(
        self,
        incident_view: IncidentView,
        candidate_services: Sequence[str],
    ) -> list[RankedService]:
        unique_candidates = list(dict.fromkeys(candidate_services))
        service_view_lookup = {
            service_view.service_id: service_view for service_view in incident_view.services
        }

        service_scores: dict[str, float] = {}
        for service_id in unique_candidates:
            service_view = service_view_lookup.get(service_id)
            service_scores[service_id] = float(service_view.n_error_after) if service_view else 0.0

        return assemble_ranked_services(service_scores, incident_view, self.name)


class GrowthAfterRanker(ServiceRanker):
    """R3: Ranks services by relative post-alert log growth ratio."""
    name: str = "r3"

    def rank(
        self,
        incident_view: IncidentView,
        candidate_services: Sequence[str],
    ) -> list[RankedService]:
        unique_candidates = list(dict.fromkeys(candidate_services))
        service_view_lookup = {
            service_view.service_id: service_view for service_view in incident_view.services
        }

        service_scores: dict[str, float] = {}
        for service_id in unique_candidates:
            service_view = service_view_lookup.get(service_id)
            if service_view is not None:
                service_scores[service_id] = float(service_view.n_after) / float(service_view.n_before + 1.0)
            else:
                service_scores[service_id] = 0.0

        return assemble_ranked_services(service_scores, incident_view, self.name)
