"""Pilot: relative improvement of untrained ranking heuristics on raw RCAEval logs.

Scores every RCAEval case that has logs with four rankers that learn nothing
(so no train/test split is needed yet), then compares them with a paired
bootstrap over fault scenarios. The output is a pilot of the measurement, not
the final evaluation: the final numbers must come from the locked test split.

    R0  uniform random order (expected value, computed exactly)
    R1  most log lines after inject_time
    R2  most ERROR/FATAL lines after inject_time (adapter severity rules)
    R3  largest growth: lines after / (lines before + 1)

Candidates are the services seen in that case's logs; the ground-truth service
is never added. inject_time only splits the window and is never a score input.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.evaluation import (  # noqa: E402
    IncidentRanking,
    expected_random_hit,
    expected_random_reciprocal_rank,
    hit_at_k,
    order_by_score,
    paired_bootstrap,
    reciprocal_rank,
)
from src.shared.infrastructure.paths import DATASET_PATHS, DATA_DIR  # noqa: E402
from src.shared.infrastructure.severity import (  # noqa: E402
    ERR_NULL_RE,
    ERROR_RE,
    LOG4J_LEVEL_RE,
    WARN_RE,
)

METHODS = ("R1", "R2", "R3")
COMPARISONS = (("R1", "R0"), ("R2", "R0"), ("R3", "R0"), ("R2", "R1"), ("R3", "R1"), ("R3", "R2"))
METRICS = ("top1", "top3", "rr")


def error_mask(messages: pd.Series) -> pd.Series:
    """Vectorised form of rcaeval adapter `extract_explicit_severity` in {ERROR, FATAL}."""
    header = messages.str.extract(LOG4J_LEVEL_RE, expand=False).str.upper()
    no_header = header.isna()
    warn = messages.str.contains(WARN_RE)
    error_body = messages.str.replace(ERR_NULL_RE, "", regex=True).str.contains(ERROR_RE)
    return header.isin(["ERROR", "FATAL"]) | (no_header & ~warn & error_body)


def score_case(log_path: Path, inject_time: int) -> tuple[dict[str, dict[str, float]], set[str], bool]:
    table = pq.read_table(log_path, columns=["timestamp", "container_name", "message"]).to_pandas()
    table = table.dropna(subset=["container_name"])
    table["service"] = table["container_name"].astype(str).str.strip()
    candidates = set(table["service"])
    after = table["timestamp"] >= inject_time
    after_counts = table.loc[after, "service"].value_counts()
    before_counts = table.loc[~after, "service"].value_counts()
    after_messages = table.loc[after, "message"].fillna("").astype(str)
    errors = table.loc[after].loc[error_mask(after_messages), "service"].value_counts()
    scores = {
        "R1": {s: float(after_counts.get(s, 0)) for s in candidates},
        "R2": {s: float(errors.get(s, 0)) for s in candidates},
        "R3": {s: after_counts.get(s, 0) / (before_counts.get(s, 0) + 1) for s in candidates},
    }
    return scores, candidates, bool((~after).any())


def tied_at_top(scores: dict[str, float]) -> bool:
    if not scores:
        return False
    best = max(scores.values())
    return sum(value == best for value in scores.values()) > 1


def score_all(data_root: Path, limit: int | None, started: float) -> pd.DataFrame:
    """One row per case with per-method Top-1, Top-3 and reciprocal rank."""
    cases = pd.read_parquet(data_root / "cases.parquet").set_index("case")
    log_paths = sorted(data_root.rglob("logs.parquet"))[:limit]
    rows = []
    for number, log_path in enumerate(log_paths, start=1):
        case = log_path.parent.name
        meta = cases.loc[case]
        target = str(meta["root_cause_service"])
        scores, candidates, has_before = score_case(log_path, int(meta["inject_time"]))
        covered = target in candidates
        row = {
            "case": case,
            "scenario": case.rsplit("_", 1)[0],
            "suite": meta["suite"],
            "system": meta["system"],
            "fault": meta["fault"],
            "n_candidates": len(candidates),
            "covered": covered,
            "has_before_window": has_before,
            "R0_top1": expected_random_hit(len(candidates), covered, 1),
            "R0_top3": expected_random_hit(len(candidates), covered, 3),
            "R0_rr": expected_random_reciprocal_rank(len(candidates), covered),
        }
        for method in METHODS:
            ranked = IncidentRanking(case, order_by_score(scores[method]), frozenset({target}), frozenset(candidates))
            row[f"{method}_top1"] = hit_at_k(ranked, 1)
            row[f"{method}_top3"] = hit_at_k(ranked, 3)
            row[f"{method}_rr"] = reciprocal_rank(ranked)
            row[f"{method}_tie_at_top"] = tied_at_top(scores[method])
        rows.append(row)
        if number % 25 == 0:
            print(f"{number}/{len(log_paths)} cases, {time.time() - started:.0f}s", file=sys.stderr)
    return pd.DataFrame(rows).set_index("case")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-root", type=Path, default=DATASET_PATHS["rcaeval"])
    parser.add_argument("--output-dir", type=Path, default=DATA_DIR / "runs" / f"pilot_relative_improvement_{date.today()}")
    parser.add_argument("--resamples", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--limit", type=int, help="Score only the first N cases (smoke test)")
    parser.add_argument("--per-case", type=Path, help="Reuse a per_case.csv from an earlier run instead of re-reading logs")
    args = parser.parse_args(argv)

    started = time.time()
    if args.per_case is not None:
        per_case = pd.read_csv(args.per_case, index_col="case")
    else:
        per_case = score_all(args.data_root, args.limit, started)
    groups = per_case["scenario"].to_dict()

    def compare(frame: pd.DataFrame) -> list[dict]:
        out = []
        for candidate, baseline in COMPARISONS:
            for metric in METRICS:
                report = paired_bootstrap(
                    frame[f"{candidate}_{metric}"].to_dict(),
                    frame[f"{baseline}_{metric}"].to_dict(),
                    {case: groups[case] for case in frame.index},
                    n_resamples=args.resamples,
                    seed=args.seed,
                )
                # report.to_dict() already has numeric "candidate"/"baseline" keys.
                out.append({"candidate_method": candidate, "baseline_method": baseline, "metric": metric, **report.to_dict()})
        return out

    report = {
        "description": "Pilot on all RCAEval cases with logs; untrained heuristics only; not the locked test split.",
        "data_root": str(args.data_root),
        "n_cases": len(per_case),
        "n_scenarios": per_case["scenario"].nunique(),
        "coverage": float(per_case["covered"].mean()),
        "means": {col: float(per_case[col].mean()) for col in per_case.columns if col[:2] in {"R0", "R1", "R2", "R3"}},
        "comparisons_all": compare(per_case),
        "comparisons_by_suite": {suite: compare(part) for suite, part in per_case.groupby("suite")},
        "resamples": args.resamples,
        "seed": args.seed,
        "runtime_seconds": round(time.time() - started, 1),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    per_case.to_csv(args.output_dir / "per_case.csv")
    (args.output_dir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps({k: report[k] for k in ("n_cases", "n_scenarios", "coverage", "means", "runtime_seconds")}, indent=2))
    print(f"Wrote {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
