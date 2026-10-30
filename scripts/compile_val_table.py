#!/usr/bin/env python3
"""Compile validation summary table comparing R0, R1, R2, R3, R4, R5 and R5 vs R2."""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from src.evaluation.metrics import (
    IncidentRanking,
    expected_random_hit,
    expected_random_reciprocal_rank,
    hit_at_k,
    paired_bootstrap,
    reciprocal_rank,
    summarize,
)
from src.evaluation.split import load_splits
from src.shared.infrastructure.paths import DATA_DIR, NORMALIZED_DIR

RUN_IDS = {
    "R1": "rcaeval_r1_g2_val_20261030-173436",
    "R2": "rcaeval_r2_g2_val_20261030-173453",
    "R3": "rcaeval_r3_g2_val_20261030-173505",
    "R4": "rcaeval_r4_g2_val_20261030-173510",
    "R5": "rcaeval_r5_g2_val_20261030-173516",
}


def run():
    dataset_slug = "rcaeval"
    splits_frame = load_splits(NORMALIZED_DIR / dataset_slug)
    scenario_map = dict(zip(splits_frame["incident_id"], splits_frame["scenario_id"]))

    gt_frame = pd.read_parquet(NORMALIZED_DIR / dataset_slug / "ground_truth.parquet")
    gt_map = dict(zip(gt_frame["incident_id"], gt_frame["canonical_target"]))

    # Load predictions for all rankers
    all_rankings = {}
    for name, run_id in RUN_IDS.items():
        pred_file = DATA_DIR / "runs" / run_id / "predictions.parquet"
        df = pq.read_table(pred_file).to_pandas()
        rankings = {}
        for inc_id, grp in df.groupby("incident_id"):
            sorted_grp = grp.sort_values("rank")
            target = gt_map.get(str(inc_id))
            rankings[str(inc_id)] = IncidentRanking(
                incident_id=str(inc_id),
                ranked_services=tuple(sorted_grp["service_id"]),
                targets=frozenset({target}) if target else frozenset(),
                candidates=frozenset(sorted_grp["service_id"]),
            )
        all_rankings[name] = rankings

    # Build R0 baseline scores per incident
    first_run_rankings = list(all_rankings["R1"].values())
    r0_top1 = {r.incident_id: expected_random_hit(len(r.candidates), r.covered, 1) for r in first_run_rankings}
    r0_top3 = {r.incident_id: expected_random_hit(len(r.candidates), r.covered, 3) for r in first_run_rankings}
    r0_rr = {r.incident_id: expected_random_reciprocal_rank(len(r.candidates), r.covered) for r in first_run_rankings}

    results_table = []
    for name in ["R1", "R2", "R3", "R4", "R5"]:
        rankings = all_rankings[name]
        c_top1 = {i: hit_at_k(rankings[i], 1) for i in rankings}
        c_top3 = {i: hit_at_k(rankings[i], 3) for i in rankings}
        c_rr = {i: reciprocal_rank(rankings[i]) for i in rankings}

        boot_top1 = paired_bootstrap(c_top1, r0_top1, scenario_map, seed=42)
        boot_top3 = paired_bootstrap(c_top3, r0_top3, scenario_map, seed=42)
        boot_rr = paired_bootstrap(c_rr, r0_rr, scenario_map, seed=42)

        results_table.append({
            "Method": name,
            "Top-1": boot_top1.candidate,
            "Top-1 Δ vs R0": boot_top1.absolute_delta,
            "Top-1 95% CI": boot_top1.delta_ci,
            "Top-1 RI": boot_top1.relative_improvement,
            "Top-1 Improved": boot_top1.improved,
            "Top-3": boot_top3.candidate,
            "Top-3 Δ vs R0": boot_top3.absolute_delta,
            "Top-3 95% CI": boot_top3.delta_ci,
            "Top-3 RI": boot_top3.relative_improvement,
            "Top-3 Improved": boot_top3.improved,
            "MRR": boot_rr.candidate,
            "MRR Δ vs R0": boot_rr.absolute_delta,
            "MRR 95% CI": boot_rr.delta_ci,
            "MRR RI": boot_rr.relative_improvement,
            "MRR Improved": boot_rr.improved,
        })

    # Also compare R5 vs R2
    r5_top1 = {i: hit_at_k(all_rankings["R5"][i], 1) for i in all_rankings["R5"]}
    r5_top3 = {i: hit_at_k(all_rankings["R5"][i], 3) for i in all_rankings["R5"]}
    r5_rr = {i: reciprocal_rank(all_rankings["R5"][i]) for i in all_rankings["R5"]}

    r2_top1 = {i: hit_at_k(all_rankings["R2"][i], 1) for i in all_rankings["R2"]}
    r2_top3 = {i: hit_at_k(all_rankings["R2"][i], 3) for i in all_rankings["R2"]}
    r2_rr = {i: reciprocal_rank(all_rankings["R2"][i]) for i in all_rankings["R2"]}

    boot_r5_r2_top1 = paired_bootstrap(r5_top1, r2_top1, scenario_map, seed=42)
    boot_r5_r2_top3 = paired_bootstrap(r5_top3, r2_top3, scenario_map, seed=42)
    boot_r5_r2_rr = paired_bootstrap(r5_rr, r2_rr, scenario_map, seed=42)

    comp_r5_r2 = {
        "Comparison": "R5 vs R2",
        "Top-1 Base(R2)": boot_r5_r2_top1.baseline,
        "Top-1 Cand(R5)": boot_r5_r2_top1.candidate,
        "Top-1 Δ": boot_r5_r2_top1.absolute_delta,
        "Top-1 95% CI": boot_r5_r2_top1.delta_ci,
        "Top-1 RI": boot_r5_r2_top1.relative_improvement,
        "Top-1 Improved": boot_r5_r2_top1.improved,
        "Top-3 Base(R2)": boot_r5_r2_top3.baseline,
        "Top-3 Cand(R5)": boot_r5_r2_top3.candidate,
        "Top-3 Δ": boot_r5_r2_top3.absolute_delta,
        "Top-3 95% CI": boot_r5_r2_top3.delta_ci,
        "Top-3 RI": boot_r5_r2_top3.relative_improvement,
        "Top-3 Improved": boot_r5_r2_top3.improved,
        "MRR Base(R2)": boot_r5_r2_rr.baseline,
        "MRR Cand(R5)": boot_r5_r2_rr.candidate,
        "MRR Δ": boot_r5_r2_rr.absolute_delta,
        "MRR 95% CI": boot_r5_r2_rr.delta_ci,
        "MRR RI": boot_r5_r2_rr.relative_improvement,
        "MRR Improved": boot_r5_r2_rr.improved,
    }

    out_json = {
        "R0_baseline": {
            "Top-1": float(np.mean(list(r0_top1.values()))),
            "Top-3": float(np.mean(list(r0_top3.values()))),
            "MRR": float(np.mean(list(r0_rr.values()))),
        },
        "rankers_vs_r0": results_table,
        "r5_vs_r2": comp_r5_r2,
    }
    (DATA_DIR / "runs" / "val_summary_report.json").write_text(
        json.dumps(out_json, indent=2, ensure_ascii=False) + "\n"
    )
    print(json.dumps(out_json, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run()
