"""Tests for rule-based zero-shot rankers (R1, R2, R3) and pilot regression verification."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import json
import pytest

from src.evaluation.metrics import (
    IncidentRanking,
    hit_at_k,
    order_by_score,
    reciprocal_rank,
)
from src.grouping import aggregate_incident_groups
from src.ranking import (
    GrowthAfterRanker,
    MostErrorsAfterRanker,
    MostLogsAfterRanker,
    RankedService,
    observed_candidates,
    select_supporting_group_ids,
    sort_services_by_score,
)
from src.shared.infrastructure.paths import DATA_DIR, NORMALIZED_DIR
from src.views import GroupSummary, IncidentView, ServiceView, build_view


def test_sort_services_by_score_matches_evaluation_metrics_order_by_score():
    """Verify sort_services_by_score behaves identically to evaluation.metrics.order_by_score."""
    test_scores = {"cartservice": 5.0, "adservice": 10.0, "frontend": 10.0, "emailservice": 1.0}
    ranking_internal = sort_services_by_score(test_scores)
    ranking_metrics = order_by_score(test_scores)
    assert ranking_internal == ranking_metrics
    assert ranking_internal == ("adservice", "frontend", "cartservice", "emailservice")


def test_evidence_selection_prioritization():
    """Verify evidence selection orders by is_new_after > n_error_after > n_after > group_id."""
    groups = [
        GroupSummary(
            group_id="g_old_high_err", template_text="t1",
            n_before=10, n_after=100, n_error_after=50, n_warn_after=0,
            is_new_after=False, first_after_offset_s=1.0,
        ),
        GroupSummary(
            group_id="g_new_low_err", template_text="t2",
            n_before=0, n_after=5, n_error_after=5, n_warn_after=0,
            is_new_after=True, first_after_offset_s=2.0,
        ),
        GroupSummary(
            group_id="g_new_high_err", template_text="t3",
            n_before=0, n_after=20, n_error_after=20, n_warn_after=0,
            is_new_after=True, first_after_offset_s=3.0,
        ),
    ]

    selected_group_ids = select_supporting_group_ids(groups, maximum_evidence_count=2)
    # g_new_high_err first, then g_new_low_err
    assert selected_group_ids == ("g_new_high_err", "g_new_low_err")


def test_rule_rankers_contracts():
    """Verify R1, R2, R3 rank candidates, preserve length, and assign valid 1-indexed ranks."""
    cart_groups = (
        GroupSummary(
            group_id="g1", template_text="t1",
            n_before=10, n_after=100, n_error_after=10, n_warn_after=0,
            is_new_after=False, first_after_offset_s=1.0,
        ),
    )
    email_groups = (
        GroupSummary(
            group_id="g2", template_text="t2",
            n_before=0, n_after=50, n_error_after=50, n_warn_after=0,
            is_new_after=True, first_after_offset_s=2.0,
        ),
    )

    cart_service = ServiceView("cartservice", n_before=10, n_after=100, n_error_after=10, n_warn_after=0, n_unknown_after=0, n_templates_after=1, groups=cart_groups)
    email_service = ServiceView("emailservice", n_before=0, n_after=50, n_error_after=50, n_warn_after=0, n_unknown_after=0, n_templates_after=1, groups=email_groups)

    view = IncidentView(
        incident_id="inc1", system_id="ob", method="g2",
        before_seconds=600.0, after_seconds=600.0,
        services=(cart_service, email_service),
    )
    candidates = ["frontend", "emailservice", "cartservice"]  # frontend has no logs

    # R1: cartservice (100) > emailservice (50) > frontend (0)
    r1_results = MostLogsAfterRanker().rank(view, candidates)
    assert [r.service_id for r in r1_results] == ["cartservice", "emailservice", "frontend"]
    assert [r.rank for r in r1_results] == [1, 2, 3]

    # R2: emailservice (50 err) > cartservice (10 err) > frontend (0)
    r2_results = MostErrorsAfterRanker().rank(view, candidates)
    assert [r.service_id for r in r2_results] == ["emailservice", "cartservice", "frontend"]
    assert [r.rank for r in r2_results] == [1, 2, 3]

    # R3: emailservice (50 / 1 = 50) > cartservice (100 / 11 ≈ 9.09) > frontend (0)
    r3_results = GrowthAfterRanker().rank(view, candidates)
    assert [r.service_id for r in r3_results] == ["emailservice", "cartservice", "frontend"]
    assert [r.rank for r in r3_results] == [1, 2, 3]


def test_pilot_regression_case_matches_per_case_csv():
    """Verify rankers match exact pilot per_case.csv scores on representative sample cases."""
    pilot_csv_path = DATA_DIR / "runs" / "pilot_relative_improvement_2026-10-26" / "per_case.csv"
    if not pilot_csv_path.exists():
        pytest.skip(f"Pilot per_case.csv not found at {pilot_csv_path}")

    rcaeval_gt_path = NORMALIZED_DIR / "rcaeval" / "ground_truth.parquet"
    views_g2_path = DATA_DIR / "artifacts" / "rcaeval" / "views_g2.jsonl"
    if not (rcaeval_gt_path.exists() and views_g2_path.exists()):
        pytest.skip("Normalized RCAEval dataset files not present")

    pilot_dataframe = pd.read_csv(pilot_csv_path).set_index("case")
    ground_truth_metadata = pd.read_parquet(rcaeval_gt_path).set_index("incident_id")
    target_sample_cases = [
        "re2ob_checkoutservice_cpu_1",
        "re2ob_checkoutservice_cpu_2",
        "re2ob_checkoutservice_cpu_3",
        "re2ob_checkoutservice_delay_1",
        "re2ob_checkoutservice_delay_2",
    ]

    r1_ranker = MostLogsAfterRanker()
    r2_ranker = MostErrorsAfterRanker()
    r3_ranker = GrowthAfterRanker()

    from src.views import view_from_dict
    evaluated_count = 0
    with views_g2_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            incident_view = view_from_dict(json.loads(line))
            case_name = incident_view.incident_id.replace("rcaeval_", "")
            if case_name not in pilot_dataframe.index:
                continue
            if case_name not in target_sample_cases:
                continue

            expected_row = pilot_dataframe.loc[case_name]
            canonical_target = ground_truth_metadata.loc[incident_view.incident_id, "canonical_target"]
            candidates = observed_candidates(incident_view)

            r1_ranked = r1_ranker.rank(incident_view, candidates)
            r2_ranked = r2_ranker.rank(incident_view, candidates)
            r3_ranked = r3_ranker.rank(incident_view, candidates)

            ranking_r1 = IncidentRanking(incident_view.incident_id, tuple(s.service_id for s in r1_ranked), frozenset({canonical_target}), frozenset(candidates))
            ranking_r2 = IncidentRanking(incident_view.incident_id, tuple(s.service_id for s in r2_ranked), frozenset({canonical_target}), frozenset(candidates))
            ranking_r3 = IncidentRanking(incident_view.incident_id, tuple(s.service_id for s in r3_ranked), frozenset({canonical_target}), frozenset(candidates))

            assert hit_at_k(ranking_r1, 1) == pytest.approx(float(expected_row["R1_top1"]))
            assert hit_at_k(ranking_r1, 3) == pytest.approx(float(expected_row["R1_top3"]))
            assert reciprocal_rank(ranking_r1) == pytest.approx(float(expected_row["R1_rr"]))

            assert hit_at_k(ranking_r2, 1) == pytest.approx(float(expected_row["R2_top1"]))
            assert hit_at_k(ranking_r2, 3) == pytest.approx(float(expected_row["R2_top3"]))
            assert reciprocal_rank(ranking_r2) == pytest.approx(float(expected_row["R2_rr"]))

            assert hit_at_k(ranking_r3, 1) == pytest.approx(float(expected_row["R3_top1"]))
            assert hit_at_k(ranking_r3, 3) == pytest.approx(float(expected_row["R3_top3"]))
            assert reciprocal_rank(ranking_r3) == pytest.approx(float(expected_row["R3_rr"]))
            evaluated_count += 1
            if evaluated_count >= len(target_sample_cases):
                break

    assert evaluated_count == len(target_sample_cases)
