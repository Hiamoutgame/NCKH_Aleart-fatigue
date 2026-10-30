"""Kev zero-shot decision ranker wrapping the KevClient."""

from __future__ import annotations

from typing import Optional, Sequence

from src.integrations.kev.client import DEFAULT_INSTRUCTIONS, KevClient
from src.ranking.base import RankedService, ServiceRanker, sort_services_by_score
from src.ranking.rules import select_supporting_group_ids
from src.views.incident_view import IncidentView
from src.views.state import StateConfig, render_state


class KevRanker(ServiceRanker):
    """Zero-shot microservice candidate ranker powered by Kev."""

    def __init__(
        self,
        client: Optional[KevClient] = None,
        state_config: Optional[StateConfig] = None,
        instructions: str = DEFAULT_INSTRUCTIONS,
        use_permutation: bool = False,
        name: Optional[str] = None,
    ) -> None:
        self.client = client or KevClient()
        self.state_config = state_config or StateConfig()
        self.instructions = instructions
        self.use_permutation = use_permutation
        self.name = name or f"kev-{self.client.model_name}"

    def rank(
        self,
        incident_view: IncidentView,
        candidate_services: Sequence[str],
    ) -> list[RankedService]:
        unique_candidates = sorted(dict.fromkeys(candidate_services))
        if not unique_candidates:
            return []

        rendered = render_state(incident_view, unique_candidates, self.state_config)

        if self.use_permutation:
            probabilities = self.client.permute(
                state=rendered.state_text,
                options=unique_candidates,
                instructions=self.instructions,
            )
        else:
            probabilities = self.client.choice(
                state=rendered.state_text,
                options=unique_candidates,
                instructions=self.instructions,
            )

        sorted_candidate_ids = sort_services_by_score(probabilities)
        service_view_lookup = {
            service_view.service_id: service_view for service_view in incident_view.services
        }

        ranked_results: list[RankedService] = []
        for rank_position, service_id in enumerate(sorted_candidate_ids, start=1):
            service_view = service_view_lookup.get(service_id)
            supporting_groups = (
                select_supporting_group_ids(service_view.groups) if service_view is not None else ()
            )
            ranked_results.append(RankedService(
                service_id=service_id,
                score=probabilities[service_id],
                rank=rank_position,
                supporting_group_ids=supporting_groups,
                method=f"{self.name}|evidence:new>error>count",
            ))

        return ranked_results
