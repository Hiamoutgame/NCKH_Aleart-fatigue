"""Hand-computed checks for ranking metrics and improvement estimates."""

from __future__ import annotations

import pytest

from src.evaluation import (
    IncidentRanking,
    error_reduction,
    expected_random_hit,
    expected_random_reciprocal_rank,
    hit_at_k,
    order_by_score,
    paired_bootstrap,
    reciprocal_rank,
    relative_improvement,
    summarize,
)


def ranking(incident: str, order: str, target: str, candidates: str | None = None) -> IncidentRanking:
    services = tuple(order)
    return IncidentRanking(
        incident_id=incident,
        ranked_services=services,
        targets=frozenset(target),
        candidates=frozenset(candidates if candidates is not None else order),
    )


def test_order_by_score_breaks_ties_by_service_id():
    assert order_by_score({"b": 2.0, "a": 2.0, "c": 5.0}) == ("c", "a", "b")


def test_hit_and_reciprocal_rank():
    r = ranking("i1", "abcd", "c")  # target at rank 3
    assert hit_at_k(r, 1) == 0.0
    assert hit_at_k(r, 3) == 1.0
    assert reciprocal_rank(r) == pytest.approx(1 / 3)


def test_k_larger_than_candidate_list_uses_all_candidates():
    r = ranking("i1", "ab", "b")
    assert hit_at_k(r, 5) == 1.0


def test_missing_target_counts_as_zero_end_to_end_but_not_conditional():
    rankings = [
        ranking("i1", "abc", "a"),         # rank 1
        ranking("i2", "abc", "b"),         # rank 2
        ranking("i3", "abc", "z"),         # target not a candidate
        ranking("i4", "", "a", ""),        # no candidates at all
    ]
    s = summarize(rankings, ks=(1, 3))
    assert s["coverage"] == pytest.approx(2 / 4)
    assert s["top1_end_to_end"] == pytest.approx(1 / 4)
    assert s["top1_conditional"] == pytest.approx(1 / 2)
    assert s["top3_end_to_end"] == pytest.approx(2 / 4)
    assert s["mrr"] == pytest.approx((1 + 0.5 + 0 + 0) / 4)


def test_empty_set_reports_none():
    s = summarize([], ks=(1,))
    assert s["coverage"] is None and s["top1_end_to_end"] is None and s["mrr"] is None


def test_expected_random_baseline():
    assert expected_random_hit(4, True, 1) == pytest.approx(0.25)
    assert expected_random_hit(4, True, 3) == pytest.approx(0.75)
    assert expected_random_hit(2, True, 3) == pytest.approx(1.0)
    assert expected_random_hit(4, False, 1) == 0.0
    # (1 + 1/2 + 1/3 + 1/4) / 4
    assert expected_random_reciprocal_rank(4, True) == pytest.approx(25 / 48)


def test_improvement_formulas():
    assert relative_improvement(0.55, 0.40) == pytest.approx(0.375)
    assert error_reduction(0.55, 0.40) == pytest.approx(0.25)
    assert relative_improvement(0.3, 0.0) is None
    assert error_reduction(1.0, 1.0) is None


def test_paired_bootstrap_point_estimates_weight_every_incident():
    # Group g1 has two incidents, g2 has one: the mean is over incidents, not groups.
    candidate = {"a": 1.0, "b": 1.0, "c": 0.0}
    baseline = {"a": 1.0, "b": 0.0, "c": 0.0}
    groups = {"a": "g1", "b": "g1", "c": "g2"}
    report = paired_bootstrap(candidate, baseline, groups, n_resamples=200)
    assert report.n_incidents == 3 and report.n_groups == 2
    assert report.candidate == pytest.approx(2 / 3)
    assert report.baseline == pytest.approx(1 / 3)
    assert report.relative_improvement == pytest.approx(1.0)
    assert report.error_reduction == pytest.approx(0.5)


def test_paired_bootstrap_identical_methods_show_no_improvement():
    scores = {f"i{n}": float(n % 2) for n in range(20)}
    groups = {incident: f"g{n // 2}" for n, incident in enumerate(scores)}
    report = paired_bootstrap(scores, dict(scores), groups, n_resamples=200)
    assert report.absolute_delta == 0.0
    assert report.delta_ci == (0.0, 0.0)
    assert not report.improved


def test_paired_bootstrap_is_reproducible_and_detects_clear_gain():
    candidate = {f"i{n}": 1.0 for n in range(30)}
    baseline = {f"i{n}": float(n < 10) for n in range(30)}
    groups = {f"i{n}": f"g{n}" for n in range(30)}
    first = paired_bootstrap(candidate, baseline, groups, n_resamples=300, seed=7)
    second = paired_bootstrap(candidate, baseline, groups, n_resamples=300, seed=7)
    assert first == second
    assert first.improved
    assert first.relative_improvement == pytest.approx(2.0)


def test_paired_bootstrap_counts_resamples_with_zero_baseline():
    candidate = {"a": 1.0, "b": 0.0}
    baseline = {"a": 0.0, "b": 0.0}
    report = paired_bootstrap(candidate, baseline, {"a": "g1", "b": "g2"}, n_resamples=100)
    assert report.relative_improvement is None
    assert report.undefined_relative_resamples == 100


def test_paired_bootstrap_rejects_mismatched_incidents():
    with pytest.raises(ValueError):
        paired_bootstrap({"a": 1.0}, {"b": 1.0}, {"a": "g", "b": "g"})
