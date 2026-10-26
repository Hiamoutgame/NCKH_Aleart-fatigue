"""Incident-level ranking metrics and paired improvement estimates.

Every score is computed per incident first and averaged over the evaluation
set `E`, so incidents whose target is missing from the candidates still count
(as 0) in end-to-end numbers. Definitions follow docs/research_protocol_v3.md §5
and docs/research/05_methodology/evaluation_metrics.md.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Optional, Sequence

import numpy as np


@dataclass(frozen=True)
class IncidentRanking:
    """One ranker's ordered output for one incident, with its true targets."""

    incident_id: str
    ranked_services: tuple[str, ...]
    targets: frozenset[str]
    candidates: frozenset[str]

    @property
    def covered(self) -> bool:
        return bool(self.targets & self.candidates)


def order_by_score(scores: Mapping[str, float]) -> tuple[str, ...]:
    """Highest score first; ties broken by service ID so runs are reproducible."""
    return tuple(sorted(scores, key=lambda service: (-scores[service], service)))


def first_target_rank(ranking: IncidentRanking) -> Optional[int]:
    for position, service in enumerate(ranking.ranked_services, start=1):
        if service in ranking.targets:
            return position
    return None


def hit_at_k(ranking: IncidentRanking, k: int) -> float:
    """1.0 when a true target is within the first k' = min(k, #candidates) services."""
    rank = first_target_rank(ranking)
    limit = min(k, len(ranking.ranked_services))
    return 1.0 if rank is not None and rank <= limit else 0.0


def reciprocal_rank(ranking: IncidentRanking) -> float:
    rank = first_target_rank(ranking)
    return 0.0 if rank is None else 1.0 / rank


def expected_random_hit(n_candidates: int, covered: bool, k: int) -> float:
    """Expected Top-k of a uniformly random order over n candidates, one target."""
    if not covered or n_candidates == 0:
        return 0.0
    return min(k, n_candidates) / n_candidates


def expected_random_reciprocal_rank(n_candidates: int, covered: bool) -> float:
    """E[1/rank] for a uniform random position among n candidates: H_n / n."""
    if not covered or n_candidates == 0:
        return 0.0
    return sum(1.0 / rank for rank in range(1, n_candidates + 1)) / n_candidates


def summarize(rankings: Sequence[IncidentRanking], ks: Sequence[int] = (1, 3, 5)) -> dict[str, Any]:
    """Coverage, end-to-end and conditional Top-k, and MRR over the evaluation set."""
    total = len(rankings)
    covered = [ranking for ranking in rankings if ranking.covered]
    summary: dict[str, Any] = {
        "n_incidents": total,
        "n_covered": len(covered),
        "coverage": len(covered) / total if total else None,
        "mrr": float(np.mean([reciprocal_rank(r) for r in rankings])) if total else None,
    }
    for k in ks:
        hits = sum(hit_at_k(ranking, k) for ranking in rankings)
        summary[f"top{k}_end_to_end"] = hits / total if total else None
        summary[f"top{k}_conditional"] = hits / len(covered) if covered else None
    return summary


def absolute_delta(candidate: float, baseline: float) -> float:
    return candidate - baseline


def relative_improvement(candidate: float, baseline: float) -> Optional[float]:
    """(candidate - baseline) / baseline; undefined when the baseline scores 0."""
    if baseline == 0:
        return None
    return (candidate - baseline) / baseline


def error_reduction(candidate: float, baseline: float) -> Optional[float]:
    """Share of the baseline's misses that the candidate recovers; undefined at 1."""
    if baseline == 1:
        return None
    return (candidate - baseline) / (1 - baseline)


@dataclass(frozen=True)
class ImprovementReport:
    """Point estimates and percentile bootstrap intervals for one metric."""

    n_incidents: int
    n_groups: int
    baseline: float
    candidate: float
    absolute_delta: float
    relative_improvement: Optional[float]
    error_reduction: Optional[float]
    delta_ci: tuple[float, float]
    relative_ci: Optional[tuple[float, float]]
    error_reduction_ci: Optional[tuple[float, float]]
    share_delta_positive: float
    undefined_relative_resamples: int
    n_resamples: int
    confidence: float

    @property
    def improved(self) -> bool:
        """Decision rule fixed before testing: the delta interval lies above 0."""
        return self.delta_ci[0] > 0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["improved"] = self.improved
        return data


def _interval(values: list[float], confidence: float) -> Optional[tuple[float, float]]:
    if not values:
        return None
    tail = (1 - confidence) / 2 * 100
    low, high = np.percentile(values, [tail, 100 - tail])
    return float(low), float(high)


def paired_bootstrap(
    candidate: Mapping[str, float],
    baseline: Mapping[str, float],
    groups: Mapping[str, str],
    n_resamples: int = 1000,
    seed: int = 42,
    confidence: float = 0.95,
) -> ImprovementReport:
    """Compare two methods scored on the same incidents.

    `candidate` and `baseline` map incident ID -> per-incident score (e.g. a
    hit, a reciprocal rank, or an expected value for the random baseline).
    `groups` maps incident ID -> independence group (e.g. fault scenario); each
    resample draws whole groups with replacement so repeated runs of one
    scenario never count as independent evidence.
    """
    if set(candidate) != set(baseline):
        raise ValueError("candidate and baseline must score the same incidents")
    missing = set(candidate) - set(groups)
    if missing:
        raise ValueError(f"{len(missing)} incidents have no group, e.g. {sorted(missing)[:3]}")

    incident_ids = sorted(candidate)
    group_ids = sorted({groups[incident] for incident in incident_ids})
    members = {group: [i for i in incident_ids if groups[i] == group] for group in group_ids}
    # Per-group sums let one resample be computed without touching incidents again.
    cand_sum = np.array([sum(candidate[i] for i in members[g]) for g in group_ids])
    base_sum = np.array([sum(baseline[i] for i in members[g]) for g in group_ids])
    sizes = np.array([len(members[g]) for g in group_ids])

    base_point = float(base_sum.sum() / sizes.sum())
    cand_point = float(cand_sum.sum() / sizes.sum())

    rng = np.random.default_rng(seed)
    deltas: list[float] = []
    relatives: list[float] = []
    reductions: list[float] = []
    undefined = 0
    for _ in range(n_resamples):
        picked = rng.integers(0, len(group_ids), size=len(group_ids))
        n = sizes[picked].sum()
        base_mean = base_sum[picked].sum() / n
        cand_mean = cand_sum[picked].sum() / n
        deltas.append(float(cand_mean - base_mean))
        relative = relative_improvement(cand_mean, base_mean)
        if relative is None:
            undefined += 1
        else:
            relatives.append(float(relative))
        reduction = error_reduction(cand_mean, base_mean)
        if reduction is not None:
            reductions.append(float(reduction))

    return ImprovementReport(
        n_incidents=len(incident_ids),
        n_groups=len(group_ids),
        baseline=base_point,
        candidate=cand_point,
        absolute_delta=absolute_delta(cand_point, base_point),
        relative_improvement=relative_improvement(cand_point, base_point),
        error_reduction=error_reduction(cand_point, base_point),
        delta_ci=_interval(deltas, confidence),
        relative_ci=_interval(relatives, confidence),
        error_reduction_ci=_interval(reductions, confidence),
        share_delta_positive=float(np.mean([delta > 0 for delta in deltas])),
        undefined_relative_resamples=undefined,
        n_resamples=n_resamples,
        confidence=confidence,
    )
