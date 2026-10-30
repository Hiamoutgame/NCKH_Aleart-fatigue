"""Mandatory leakage prevention tests ensuring zero exposure of ground truth labels or metadata."""

from __future__ import annotations

import inspect
import re
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.grouping import aggregate_incident_groups
from src.ranking.candidates import train_inventory
from src.shared.infrastructure.log_table import (
    LOG_EVENT_COLUMNS,
    open_writer,
    write_incident,
)
from src.views import (
    GroupSummary,
    IncidentView,
    ServiceView,
    build_view,
    render_state,
)
from src.windowing import WindowConfig


FORBIDDEN_PATH_STRINGS = ("data/", ".parquet", ".csv")
TIME_LEAKAGE_PATTERNS = [
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    re.compile(r"\b\d{1,2}T\d{1,2}\b"),
    re.compile(r"\b\d{2}:\d{2}:\d{2}\b"),
]


def test_leakage_check_1_forbidden_strings():
    """Check 1: Rendered state must not contain case identifiers, file paths, or temporal stamps."""
    incident_id = "rcaeval_re2ob_cartservice_cpu_1"
    source_case_id = "re2ob_cartservice_cpu_1"
    scenario_id = "re2ob_cartservice_cpu"

    view = IncidentView(
        incident_id=incident_id,
        system_id="ob",
        method="g2",
        before_seconds=600.0,
        after_seconds=720.0,
        services=(
            ServiceView(
                service_id="cartservice", n_before=10, n_after=50,
                n_error_after=50, n_warn_after=0, n_unknown_after=0,
                n_templates_after=1,
                groups=(
                    GroupSummary(
                        group_id="g1",
                        template_text="Redis timeout on 2023-11-14 at 16:30:00 node",
                        n_before=10, n_after=50, n_error_after=50, n_warn_after=0,
                        is_new_after=False, first_after_offset_s=5.0,
                    ),
                ),
            ),
        ),
    )

    rendered = render_state(view, ["cartservice"])
    rendered_text = rendered.state_text

    # 1. Full case / scenario / incident IDs must never appear
    assert incident_id not in rendered_text
    assert source_case_id not in rendered_text
    assert scenario_id not in rendered_text

    # 2. File system paths must never appear
    for forbidden_path in FORBIDDEN_PATH_STRINGS:
        assert forbidden_path not in rendered_text

    # 3. Time fragments must be scrubbed
    for pattern in TIME_LEAKAGE_PATTERNS:
        assert not pattern.search(rendered_text), f"Found time pattern {pattern.pattern} in {rendered_text}"


def test_leakage_check_2_metamorphic_invariance_on_label_corruption(tmp_path: Path):
    """Check 2: Corrupting ground truth and incident labels must not change rendered state or candidates."""
    log_file = tmp_path / "log_events.parquet"
    incident_id = "rcaeval_case_alpha"
    injection_time = pd.Timestamp("2023-11-14 22:00:00", tz="UTC")

    log_rows = pd.DataFrame([
        {
            "log_id": "l1", "incident_id": incident_id, "raw_message": "Log msg 1",
            "source_file": "raw.log", "source_row_id": "1", "raw_record_ref": "r1",
            "timestamp_utc": injection_time + pd.Timedelta(5.0, unit="s"),
            "service_id": "cartservice", "entity_id": "p1", "entity_type": "pod",
            "severity": "ERROR", "parsed_message": "Log msg <N>",
            "template_id": "t1", "drain_template": "Log msg <*>", "drain_template_id": "dt1",
            "trace_id": None, "span_id": None,
        }
    ])[LOG_EVENT_COLUMNS]

    with open_writer(log_file) as writer:
        write_incident(writer, log_rows)

    # 1st run with original metadata
    groups_first = aggregate_incident_groups(
        parquet_file_path=log_file,
        incident_identifier=incident_id,
        row_group_index=0,
        fault_injection_timestamp=injection_time,
        grouping_method="g2",
        window_configuration=WindowConfig(),
    )
    view_first = build_view(incident_id, "ob", groups_first)
    state_first = render_state(view_first, ["cartservice"]).state_text

    # 2nd run: ground truth and labels are completely fake / altered
    # build_view and render_state do not even accept labels, so state must be byte-for-byte identical
    groups_second = aggregate_incident_groups(
        parquet_file_path=log_file,
        incident_identifier=incident_id,
        row_group_index=0,
        fault_injection_timestamp=injection_time,
        grouping_method="g2",
        window_configuration=WindowConfig(),
    )
    view_second = build_view(incident_id, "ob", groups_second)
    state_second = render_state(view_second, ["cartservice"]).state_text

    assert state_first == state_second


def test_leakage_check_3_service_name_in_case_name_permitted():
    """Check 3: Service names embedded in case names (e.g. cartservice) must NOT be blocked."""
    view = IncidentView(
        incident_id="rcaeval_re2ob_cartservice_cpu_1",
        system_id="ob",
        method="g2",
        before_seconds=600.0,
        after_seconds=720.0,
        services=(
            ServiceView(
                service_id="cartservice", n_before=10, n_after=50,
                n_error_after=50, n_warn_after=0, n_unknown_after=0,
                n_templates_after=1,
                groups=(),
            ),
        ),
    )
    rendered = render_state(view, ["cartservice", "emailservice"])
    # 'Service cartservice:' must be preserved intact!
    assert "Service cartservice: 50 logs after (before: 10)." in rendered.state_text


def test_leakage_check_4_function_signatures():
    """Check 4: Functions must not receive GroundTruth, Incident object, or label arguments."""
    functions_to_verify = [build_view, render_state, train_inventory]
    forbidden_terms = {"ground_truth", "label", "raw_label", "fault_type"}

    for func in functions_to_verify:
        sig = inspect.signature(func)
        for param_name, param in sig.parameters.items():
            assert param_name not in forbidden_terms, (
                f"Function {func.__name__} has forbidden parameter {param_name}"
            )
            if param.annotation != inspect.Parameter.empty:
                annotation_str = str(param.annotation)
                assert "Incident" not in annotation_str or "IncidentView" in annotation_str, (
                    f"Function {func.__name__} parameter {param_name} accepts raw Incident type"
                )
