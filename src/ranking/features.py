"""Microservice candidate feature extraction for supervised rankers (R4 and R5).

Features are computed strictly over observation windows without incorporating
service identifiers, system topologies, absolute timestamps, or ground truth labels.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

from src.views.incident_view import IncidentView, ServiceView

R4_FEATURE_NAMES = (
    "has_logs",
    "log_count",
    "log_rate",
    "service_log_share",
    "error_count",
    "warn_count",
    "error_ratio",
    "warn_ratio",
    "unknown_severity_ratio",
)

R5_FEATURE_NAMES = R4_FEATURE_NAMES + (
    "unique_template_count",
    "dominant_template_share",
    "new_template_count",
    "new_template_log_share",
    "first_seen_offset_ratio",
    "growth_ratio",
)


def extract_candidate_features(
    incident_view: IncidentView,
    candidate_service_id: str,
    feature_set: str = "r4",
) -> list[float]:
    """Extract numeric feature vector for a single (incident, candidate_service) pair."""
    feature_mode = feature_set.lower().strip()
    if feature_mode not in ("r4", "r5"):
        raise ValueError(f"Unknown feature set: {feature_set!r}. Expected 'r4' or 'r5'.")

    service_view_lookup = {
        service_view.service_id: service_view for service_view in incident_view.services
    }
    service_view = service_view_lookup.get(candidate_service_id)

    total_after_logs_in_incident = sum(
        s.n_after for s in incident_view.services
    )
    after_seconds_duration = float(incident_view.after_seconds)

    if service_view is None or (service_view.n_after == 0 and service_view.n_before == 0):
        # Candidate has no observed logs in this incident
        base_features = [0.0] * len(R4_FEATURE_NAMES)
        if feature_mode == "r5":
            return base_features + [0.0] * (len(R5_FEATURE_NAMES) - len(R4_FEATURE_NAMES))
        return base_features

    has_logs = 1.0 if service_view.n_after > 0 else 0.0
    log_count = float(service_view.n_after)
    log_rate = (
        log_count / after_seconds_duration if after_seconds_duration > 0.0 else 0.0
    )
    service_log_share = (
        log_count / float(total_after_logs_in_incident)
        if total_after_logs_in_incident > 0
        else 0.0
    )
    error_count = float(service_view.n_error_after)
    warn_count = float(service_view.n_warn_after)
    error_ratio = error_count / log_count if log_count > 0.0 else 0.0
    warn_ratio = warn_count / log_count if log_count > 0.0 else 0.0
    unknown_severity_ratio = (
        float(service_view.n_unknown_after) / log_count if log_count > 0.0 else 0.0
    )

    r4_vector = [
        has_logs,
        log_count,
        log_rate,
        service_log_share,
        error_count,
        warn_count,
        error_ratio,
        warn_ratio,
        unknown_severity_ratio,
    ]

    if feature_mode == "r4":
        return r4_vector

    # R5 extensions
    unique_template_count = float(service_view.n_templates_after)
    dominant_template_count = max(
        (group.n_after for group in service_view.groups), default=0
    )
    dominant_template_share = (
        float(dominant_template_count) / log_count if log_count > 0.0 else 0.0
    )

    new_groups = [group for group in service_view.groups if group.is_new_after and group.n_after > 0]
    new_template_count = float(len(new_groups))
    new_template_logs = sum(group.n_after for group in new_groups)
    new_template_log_share = (
        float(new_template_logs) / log_count if log_count > 0.0 else 0.0
    )

    first_after_offsets = [
        group.first_after_offset_s
        for group in service_view.groups
        if group.first_after_offset_s is not None and group.n_after > 0
    ]
    if first_after_offsets and after_seconds_duration > 0.0:
        first_seen_offset_ratio = float(min(first_after_offsets)) / after_seconds_duration
    else:
        first_seen_offset_ratio = 0.0

    growth_ratio = log_count / float(service_view.n_before + 1.0)

    r5_vector = r4_vector + [
        unique_template_count,
        dominant_template_share,
        new_template_count,
        new_template_log_share,
        first_seen_offset_ratio,
        growth_ratio,
    ]
    return r5_vector


def build_incident_feature_matrix(
    incident_view: IncidentView,
    candidate_services: Sequence[str],
    feature_set: str = "r4",
) -> np.ndarray:
    """Build 2D numpy array of shape (len(candidate_services), n_features)."""
    rows = [
        extract_candidate_features(incident_view, candidate_id, feature_set)
        for candidate_id in candidate_services
    ]
    matrix = np.array(rows, dtype=np.float64)
    if not np.isfinite(matrix).all():
        raise ValueError(f"Non-finite feature values discovered in matrix for {incident_view.incident_id}")
    return matrix
