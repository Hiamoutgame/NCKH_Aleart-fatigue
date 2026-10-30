"""Unit tests for IncidentView construction, serialization, and prompt state rendering."""

from __future__ import annotations

import pandas as pd
import pytest

from src.views import (
    GroupSummary,
    IncidentView,
    RenderedState,
    ServiceView,
    StateConfig,
    build_view,
    render_state,
    scrub_time,
    view_from_dict,
    view_to_dict,
)


def test_scrub_time_replaces_timestamps_with_placeholder():
    """Verify that various real-world date and time formats are sanitized to <TIME>."""
    assert scrub_time('created_time: "<N>-<N>-15T18:22:10Z"') == 'created_time: "<TIME>"'
    assert scrub_time('date="2023-11-14"') == 'date="<TIME>"'
    assert scrub_time('Event occurred at Jan 15 in node') == 'Event occurred at <TIME> in node'
    assert scrub_time('Event occurred at Tue Feb <N> in node') == 'Event occurred at <TIME> in node'
    assert scrub_time('Normal message without dates or times') == 'Normal message without dates or times'


def test_build_view_and_serialization_roundtrip():
    """Verify constructing IncidentView from group rows and roundtripping via dict."""
    groups_data = pd.DataFrame([
        {
            "group_id": "g2:hash1", "method": "g2", "incident_id": "inc_sample_1",
            "service_id": "cartservice", "template_key": "dtmpl_1",
            "template_text": "Failed connecting to redis",
            "n_logs": 20, "n_before": 5, "n_after": 15, "n_outside": 0,
            "n_error": 10, "n_warn": 0, "n_unknown_severity": 10,
            "n_error_after": 10, "n_warn_after": 0, "n_unknown_after": 5,
            "first_offset_s": -300.0, "last_offset_s": 600.0,
            "first_after_offset_s": 15.0, "is_new_after": False,
            "example_log_ids": ["log_1", "log_2"],
        },
        {
            "group_id": "g2:hash2", "method": "g2", "incident_id": "inc_sample_1",
            "service_id": "cartservice", "template_key": "dtmpl_2",
            "template_text": "Redis timeout exception",
            "n_logs": 8, "n_before": 0, "n_after": 8, "n_outside": 0,
            "n_error": 8, "n_warn": 0, "n_unknown_severity": 0,
            "n_error_after": 8, "n_warn_after": 0, "n_unknown_after": 0,
            "first_offset_s": 20.0, "last_offset_s": 500.0,
            "first_after_offset_s": 20.0, "is_new_after": True,
            "example_log_ids": ["log_3"],
        },
        {
            "group_id": "g2:hash3", "method": "g2", "incident_id": "inc_sample_1",
            "service_id": None, "template_key": "dtmpl_3",
            "template_text": "System node rebooting",
            "n_logs": 1, "n_before": 0, "n_after": 1, "n_outside": 0,
            "n_error": 0, "n_warn": 1, "n_unknown_severity": 0,
            "n_error_after": 0, "n_warn_after": 1, "n_unknown_after": 0,
            "first_offset_s": 1.0, "last_offset_s": 1.0,
            "first_after_offset_s": 1.0, "is_new_after": True,
            "example_log_ids": ["log_4"],
        },
    ])

    view = build_view(
        incident_identifier="inc_sample_1",
        system_identifier="ob",
        groups_frame=groups_data,
    )

    assert view.incident_id == "inc_sample_1"
    assert view.system_id == "ob"
    assert view.before_seconds == 300.0
    assert view.after_seconds == 600.0
    assert len(view.services) == 1
    assert view.services[0].service_id == "cartservice"
    assert view.services[0].n_before == 5
    assert view.services[0].n_after == 23
    assert view.services[0].n_error_after == 18
    assert len(view.unknown_service_groups) == 1

    serialized_dict = view_to_dict(view)
    deserialized_view = view_from_dict(serialized_dict)
    assert deserialized_view == view


def test_render_state_format_and_ablations():
    """Verify standard formatting and ablations (A1, A2, A3) in render_state."""
    group_redis = GroupSummary(
        group_id="g1", template_text="Redis timeout",
        n_before=10, n_after=100, n_error_after=80, n_warn_after=0,
        is_new_after=False, first_after_offset_s=5.0,
    )
    group_new = GroupSummary(
        group_id="g2", template_text="New crash error",
        n_before=0, n_after=50, n_error_after=50, n_warn_after=0,
        is_new_after=True, first_after_offset_s=10.0,
    )
    cart_service = ServiceView(
        service_id="cartservice", n_before=10, n_after=150,
        n_error_after=130, n_warn_after=0, n_unknown_after=20,
        n_templates_after=2, groups=(group_new, group_redis),
    )
    view = IncidentView(
        incident_id="inc_sample_1", system_id="ob", method="g2",
        before_seconds=600.0, after_seconds=720.0,
        services=(cart_service,),
    )

    candidates = ["cartservice", "emailservice"]

    # Standard configuration
    rendered_standard = render_state(view, candidates, StateConfig())
    text = rendered_standard.state_text
    assert "System: ob. Logs after the alert: 150 over 12 min. Logs before: 10 over 10 min." in text
    assert "Service cartservice: 150 logs after (before: 10). ERROR 130, WARN 0, unknown level 20." in text
    assert '  New after alert: [50] "New crash error"' in text
    assert '  Most frequent after alert: [100] "Redis timeout"' in text
    assert "Service emailservice: no logs." in text

    # Ablation A1: include_before=False
    rendered_a1 = render_state(view, candidates, StateConfig(include_before=False))
    assert "before:" not in rendered_a1.state_text
    assert "New after alert" not in rendered_a1.state_text  # New requires before awareness
    assert "Logs before:" not in rendered_a1.state_text

    # Ablation A2: include_template_text=False
    rendered_a2 = render_state(view, candidates, StateConfig(include_template_text=False))
    assert "New after alert" not in rendered_a2.state_text
    assert "Most frequent after alert" not in rendered_a2.state_text
    assert "Service cartservice: 150 logs after" in rendered_a2.state_text

    # Ablation A3: include_severity=False
    rendered_a3 = render_state(view, candidates, StateConfig(include_severity=False))
    assert "ERROR" not in rendered_a3.state_text
    assert "WARN" not in rendered_a3.state_text
    assert "unknown level" not in rendered_a3.state_text
