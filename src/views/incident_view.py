"""IncidentView and hierarchical representation of an incident for ranking models.

Structures group aggregates into a clean service-level hierarchy while strictly
isolating inference features from ground truth labels and case identities.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional, Sequence

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class GroupSummary:
    """Summary metrics for a single log event group."""
    group_id: str
    template_text: str
    n_before: int
    n_after: int
    n_error_after: int
    n_warn_after: int
    is_new_after: bool
    first_after_offset_s: Optional[float]


@dataclass(frozen=True)
class ServiceView:
    """Aggregated observation view for a single microservice candidate."""
    service_id: str
    n_before: int
    n_after: int
    n_error_after: int
    n_warn_after: int
    n_unknown_after: int
    n_templates_after: int
    groups: tuple[GroupSummary, ...]


@dataclass(frozen=True)
class IncidentView:
    """Incident-level structured hierarchy without labels or case identifiers in state."""
    incident_id: str
    system_id: str
    method: str
    before_seconds: float
    after_seconds: float
    services: tuple[ServiceView, ...]
    unknown_service_groups: tuple[GroupSummary, ...] = field(default_factory=tuple)


def build_view(
    incident_identifier: str,
    system_identifier: str,
    groups_frame: pd.DataFrame,
) -> IncidentView:
    """Construct an IncidentView from a single incident's groups DataFrame.

    Parameters:
        incident_identifier: Canonical incident ID (e.g. 'rcaeval_re2ob_cartservice_cpu_1').
        system_identifier: System ID (e.g. 'ob', 'ss', 'tt').
        groups_frame: DataFrame matching GROUPS_TABLE_SCHEMA for this incident.

    Note:
        This function explicitly avoids receiving any GroundTruth, Incident object, or label.
    """
    if groups_frame.empty:
        return IncidentView(
            incident_id=incident_identifier,
            system_id=system_identifier,
            method="unknown",
            before_seconds=0.0,
            after_seconds=0.0,
            services=(),
            unknown_service_groups=(),
        )

    grouping_method = str(groups_frame["method"].iloc[0])

    # Calculate actual before and after durations in seconds from group offsets
    valid_first_offsets = groups_frame["first_offset_s"].dropna()
    negative_offsets = valid_first_offsets[valid_first_offsets < 0.0]
    before_duration = float(abs(negative_offsets.min())) if not negative_offsets.empty else 0.0

    valid_last_offsets = groups_frame["last_offset_s"].dropna()
    positive_offsets = valid_last_offsets[valid_last_offsets >= 0.0]
    after_duration = float(positive_offsets.max()) if not positive_offsets.empty else 0.0

    # Separate groups with known service vs unknown (null/empty) service
    unknown_service_rows = groups_frame[
        groups_frame["service_id"].isna() | (groups_frame["service_id"].astype(str).str.strip() == "")
    ]
    known_service_rows = groups_frame[
        groups_frame["service_id"].notna() & (groups_frame["service_id"].astype(str).str.strip() != "")
    ]

    unknown_groups_list: list[GroupSummary] = []
    for _, row in unknown_service_rows.iterrows():
        first_after_offset = (
            float(row["first_after_offset_s"]) if pd.notna(row["first_after_offset_s"]) else None
        )
        unknown_groups_list.append(GroupSummary(
            group_id=str(row["group_id"]),
            template_text=str(row["template_text"]),
            n_before=int(row["n_before"]),
            n_after=int(row["n_after"]),
            n_error_after=int(row["n_error_after"]),
            n_warn_after=int(row["n_warn_after"]),
            is_new_after=bool(row["is_new_after"]),
            first_after_offset_s=first_after_offset,
        ))

    service_views_list: list[ServiceView] = []
    for service_name, service_group_frame in known_service_rows.groupby("service_id"):
        group_summaries: list[GroupSummary] = []
        for _, row in service_group_frame.iterrows():
            first_after_offset = (
                float(row["first_after_offset_s"]) if pd.notna(row["first_after_offset_s"]) else None
            )
            group_summaries.append(GroupSummary(
                group_id=str(row["group_id"]),
                template_text=str(row["template_text"]),
                n_before=int(row["n_before"]),
                n_after=int(row["n_after"]),
                n_error_after=int(row["n_error_after"]),
                n_warn_after=int(row["n_warn_after"]),
                is_new_after=bool(row["is_new_after"]),
                first_after_offset_s=first_after_offset,
            ))

        # Sort groups by n_after descending, then first_after_offset_s ascending
        sorted_groups = sorted(
            group_summaries,
            key=lambda g: (-g.n_after, g.first_after_offset_s if g.first_after_offset_s is not None else float("inf")),
        )

        service_views_list.append(ServiceView(
            service_id=str(service_name).strip(),
            n_before=int(service_group_frame["n_before"].sum()),
            n_after=int(service_group_frame["n_after"].sum()),
            n_error_after=int(service_group_frame["n_error_after"].sum()),
            n_warn_after=int(service_group_frame["n_warn_after"].sum()),
            n_unknown_after=int(service_group_frame["n_unknown_after"].sum()),
            n_templates_after=int((service_group_frame["n_after"] > 0).sum()),
            groups=tuple(sorted_groups),
        ))

    # Sort services alphabetically by service_id
    sorted_services = sorted(service_views_list, key=lambda s: s.service_id)

    return IncidentView(
        incident_id=incident_identifier,
        system_id=system_identifier,
        method=grouping_method,
        before_seconds=before_duration,
        after_seconds=after_duration,
        services=tuple(sorted_services),
        unknown_service_groups=tuple(unknown_groups_list),
    )


def view_to_dict(incident_view: IncidentView) -> dict[str, Any]:
    """Serialize an IncidentView into a JSON-compatible dictionary."""
    return asdict(incident_view)


def view_from_dict(payload: dict[str, Any]) -> IncidentView:
    """Deserialize an IncidentView from a dictionary."""
    services_list: list[ServiceView] = []
    for service_dict in payload.get("services", []):
        groups_list = [
            GroupSummary(**group_dict) for group_dict in service_dict.get("groups", [])
        ]
        services_list.append(ServiceView(
            service_id=service_dict["service_id"],
            n_before=service_dict["n_before"],
            n_after=service_dict["n_after"],
            n_error_after=service_dict["n_error_after"],
            n_warn_after=service_dict["n_warn_after"],
            n_unknown_after=service_dict["n_unknown_after"],
            n_templates_after=service_dict["n_templates_after"],
            groups=tuple(groups_list),
        ))

    unknown_groups = [
        GroupSummary(**g) for g in payload.get("unknown_service_groups", [])
    ]

    return IncidentView(
        incident_id=payload["incident_id"],
        system_id=payload["system_id"],
        method=payload["method"],
        before_seconds=float(payload["before_seconds"]),
        after_seconds=float(payload["after_seconds"]),
        services=tuple(services_list),
        unknown_service_groups=tuple(unknown_groups),
    )
