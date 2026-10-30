"""State rendering and time fragment scrubbing for inference models and LLM prompts.

Renders incident hierarchy into fixed English state representations without leaking
ground truth labels, dataset file paths, or temporal case run identifiers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Sequence

from src.views.incident_view import IncidentView, ServiceView

TIME_FRAGMENT_RE = re.compile(
    r"(?:<N>|\d+)-(?:<N>|\d+)-(?:<N>|\d{1,2})[T ](?:<N>|\d{1,2})[:-](?:<N>|\d{1,2})(?:[:-](?:<N>|\d{1,2}))?"
    r"(?:[.,](?:<N>|<HEX>|\d+))?(?:Z|[+-](?:<N>|\d{1,2})(?::?(?:<N>|\d{2}))?)?"
)
MONTH_DAY_RE = re.compile(
    r"\b(?:(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(?:<N>|\d{1,2})(?!\d)"
)
ISO_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
ISO_TIME_SHORT_RE = re.compile(r"\b\d{1,2}T\d{1,2}\b")
WALL_CLOCK_TIME_RE = re.compile(r"\b\d{2}:\d{2}:\d{2}\b")


def scrub_time(text: str) -> str:
    """Remove real-world and normalized time fragments from template text.

    Replaces explicit date/time stamps with '<TIME>' so that ranking models
    cannot memorize temporal run markers.
    """
    if not text:
        return ""
    cleaned_text = TIME_FRAGMENT_RE.sub("<TIME>", text)
    cleaned_text = MONTH_DAY_RE.sub("<TIME>", cleaned_text)
    cleaned_text = ISO_DATE_RE.sub("<TIME>", cleaned_text)
    cleaned_text = ISO_TIME_SHORT_RE.sub("<TIME>", cleaned_text)
    cleaned_text = WALL_CLOCK_TIME_RE.sub("<TIME>", cleaned_text)
    return cleaned_text


@dataclass(frozen=True)
class StateConfig:
    """Configuration flags and truncation limits for prompt state rendering."""
    include_before: bool = True          # False = ablation A1
    include_template_text: bool = True   # False = ablation A2
    include_severity: bool = True        # False = ablation A3
    max_new_templates: int = 3
    max_frequent_templates: int = 2
    max_template_chars: int = 160
    max_chars: int = 12_000              # Maximum total state characters


@dataclass(frozen=True)
class RenderedState:
    """Container for rendered state text and truncation metadata."""
    state_text: str
    state_chars: int
    truncated: bool


def _render_state_lines(
    incident_view: IncidentView,
    candidate_services: Sequence[str],
    config: StateConfig,
    effective_max_new_templates: int,
    effective_max_frequent_templates: int,
    effective_max_template_chars: int,
) -> list[str]:
    """Internal helper to assemble state text lines given current template quotas."""
    output_lines: list[str] = []

    total_after_logs = sum(service_view.n_after for service_view in incident_view.services)
    after_duration_minutes = max(1, int(round(incident_view.after_seconds / 60.0)))

    if config.include_before:
        total_before_logs = sum(service_view.n_before for service_view in incident_view.services)
        before_duration_minutes = (
            max(1, int(round(incident_view.before_seconds / 60.0)))
            if incident_view.before_seconds > 0.0
            else 0
        )
        system_header_line = (
            f"System: {incident_view.system_id}. "
            f"Logs after the alert: {total_after_logs:,} over {after_duration_minutes} min. "
            f"Logs before: {total_before_logs:,} over {before_duration_minutes} min."
        )
    else:
        system_header_line = (
            f"System: {incident_view.system_id}. "
            f"Logs after the alert: {total_after_logs:,} over {after_duration_minutes} min."
        )
    output_lines.append(system_header_line)

    services_by_id = {service_view.service_id: service_view for service_view in incident_view.services}
    sorted_candidate_services = sorted(candidate_services)

    for candidate_service_id in sorted_candidate_services:
        service_view = services_by_id.get(candidate_service_id)

        # Check if service has any relevant log observations
        has_logs = (
            service_view is not None
            and (service_view.n_after > 0 or (config.include_before and service_view.n_before > 0))
        )

        if not has_logs:
            output_lines.append(f"Service {candidate_service_id}: no logs.")
            continue

        assert service_view is not None
        service_line_parts = [f"Service {candidate_service_id}: {service_view.n_after:,} logs after"]
        if config.include_before:
            service_line_parts.append(f" (before: {service_view.n_before:,})")
        service_line_parts.append(".")

        if config.include_severity:
            service_line_parts.append(
                f" ERROR {service_view.n_error_after:,}, "
                f"WARN {service_view.n_warn_after:,}, "
                f"unknown level {service_view.n_unknown_after:,}."
            )

        output_lines.append("".join(service_line_parts))

        if not config.include_template_text:
            continue

        # New templates after alert (only available when before logs are included)
        new_templates_list = []
        if config.include_before and effective_max_new_templates > 0:
            for group_summary in service_view.groups:
                if group_summary.is_new_after and group_summary.n_after > 0:
                    new_templates_list.append(group_summary)
                    if len(new_templates_list) >= effective_max_new_templates:
                        break

        for new_group in new_templates_list:
            cleaned_template_text = scrub_time(new_group.template_text)[:effective_max_template_chars]
            output_lines.append(
                f'  New after alert: [{new_group.n_after}] "{cleaned_template_text}"'
            )

        # Frequent templates after alert (excluding those already shown in new_templates)
        frequent_templates_list = []
        if effective_max_frequent_templates > 0:
            shown_group_ids = {g.group_id for g in new_templates_list}
            for group_summary in service_view.groups:
                if group_summary.n_after > 0 and group_summary.group_id not in shown_group_ids:
                    frequent_templates_list.append(group_summary)
                    if len(frequent_templates_list) >= effective_max_frequent_templates:
                        break

        for frequent_group in frequent_templates_list:
            cleaned_template_text = scrub_time(frequent_group.template_text)[:effective_max_template_chars]
            output_lines.append(
                f'  Most frequent after alert: [{frequent_group.n_after}] "{cleaned_template_text}"'
            )

    return output_lines


def render_state(
    incident_view: IncidentView,
    candidate_services: Sequence[str],
    config: Optional[StateConfig] = None,
) -> RenderedState:
    """Render the incident hierarchy into fixed formatted text for inference.

    Parameters:
        incident_view: IncidentView containing service-level metrics.
        candidate_services: Target candidate service names to enumerate.
        config: StateConfig flags controlling ablations and character limits.

    Returns:
        RenderedState object with state_text, state_chars, and truncated flag.
    """
    state_configuration = config or StateConfig()

    # Try standard quota first
    fallback_quotas = [
        (state_configuration.max_new_templates, state_configuration.max_frequent_templates, state_configuration.max_template_chars),
        (2, 1, state_configuration.max_template_chars),
        (1, 1, 100),
        (1, 0, 80),
        (0, 0, 0),  # Header and Service lines only
    ]

    truncated_flag = False
    selected_lines: list[str] = []

    for quota_index, (new_limit, frequent_limit, char_limit) in enumerate(fallback_quotas):
        rendered_lines = _render_state_lines(
            incident_view=incident_view,
            candidate_services=candidate_services,
            config=state_configuration,
            effective_max_new_templates=new_limit,
            effective_max_frequent_templates=frequent_limit,
            effective_max_template_chars=char_limit,
        )
        joined_text = "\n".join(rendered_lines)
        if len(joined_text) <= state_configuration.max_chars:
            selected_lines = rendered_lines
            truncated_flag = quota_index > 0
            break

    if not selected_lines:
        # Last resort: truncate template characters in minimal quota
        rendered_lines = _render_state_lines(
            incident_view=incident_view,
            candidate_services=candidate_services,
            config=state_configuration,
            effective_max_new_templates=0,
            effective_max_frequent_templates=0,
            effective_max_template_chars=0,
        )
        joined_text = "\n".join(rendered_lines)
        selected_lines = rendered_lines
        truncated_flag = True

    final_text = "\n".join(selected_lines)
    return RenderedState(
        state_text=final_text,
        state_chars=len(final_text),
        truncated=truncated_flag,
    )
