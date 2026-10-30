"""Pipeline CLI for grouping, candidates, views, training, ranking, and evaluation."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

import numpy as np
import pandas as pd
import pyarrow as pa
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
from src.evaluation.split import load_split_incidents, load_splits
from src.grouping import GROUPS_PARQUET_NAME, build_groups
from src.ranking import (
    GrowthAfterRanker,
    MostErrorsAfterRanker,
    MostLogsAfterRanker,
    RankedService,
    load_candidates,
    load_logreg_ranker,
    observed_candidates,
    save_candidates,
    train_inventory,
    train_logreg_model,
)
from src.shared.infrastructure.manifest import git_state, sha256_file
from src.shared.infrastructure.paths import DATA_DIR, NORMALIZED_DIR
from src.views import (
    IncidentView,
    build_view,
    view_from_dict,
    view_to_dict,
)
from src.windowing import WindowConfig

SUPPORTED_DATASETS = ("rcaeval", "nezha")
PREDICTIONS_SCHEMA = pa.schema([
    ("incident_id", pa.string()),
    ("service_id", pa.string()),
    ("score", pa.float64()),
    ("rank", pa.int64()),
    ("supporting_group_ids", pa.list_(pa.string())),
    ("method", pa.string()),
])


def cmd_group(args: argparse.Namespace) -> int:
    datasets = SUPPORTED_DATASETS if args.dataset == "all" else [args.dataset]
    window_config = WindowConfig(
        before_seconds=args.before_seconds,
        after_seconds=args.after_seconds,
    )
    results = {}
    for slug in datasets:
        out_parquet, out_manifest = build_groups(
            dataset_slug=slug,
            grouping_method=args.method,
            window_configuration=window_config,
            batch_size=args.batch_size,
        )
        results[slug] = {
            "groups_parquet": str(out_parquet),
            "manifest": str(out_manifest),
        }
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


def cmd_candidates(args: argparse.Namespace) -> int:
    datasets = SUPPORTED_DATASETS if args.dataset == "all" else [args.dataset]
    results = {}
    for slug in datasets:
        if slug == "rcaeval":
            groups_path = DATA_DIR / "artifacts" / slug / f"groups_{args.method}" / GROUPS_PARQUET_NAME
            if not groups_path.exists():
                # Fallback to g2 if specified method not yet generated
                alt_path = DATA_DIR / "artifacts" / slug / "groups_g2" / GROUPS_PARQUET_NAME
                if alt_path.exists():
                    groups_path = alt_path
                else:
                    raise FileNotFoundError(f"groups.parquet not found under artifacts for {slug}")

            splits_frame = load_splits(NORMALIZED_DIR / slug)
            inventory = train_inventory(groups_path, splits_frame)
            train_incidents_count = len(splits_frame[splits_frame["split_purpose"] == "train"])
            out_path = DATA_DIR / "artifacts" / slug / "candidates.json"
            save_candidates(
                out_path,
                inventory,
                metadata={"dataset": slug, "train_incidents": train_incidents_count},
            )
            results[slug] = {"candidates_file": str(out_path), "inventory": inventory}
        else:
            results[slug] = {"mode": "observed_candidates"}
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


def cmd_views(args: argparse.Namespace) -> int:
    datasets = SUPPORTED_DATASETS if args.dataset == "all" else [args.dataset]
    results = {}
    for slug in datasets:
        groups_path = DATA_DIR / "artifacts" / slug / f"groups_{args.method}" / GROUPS_PARQUET_NAME
        if not groups_path.exists():
            raise FileNotFoundError(f"Groups table not found at {groups_path}. Run group first.")

        incidents_path = NORMALIZED_DIR / slug / "incidents.parquet"
        incidents_system_map = dict(
            zip(
                pd.read_parquet(incidents_path, columns=["incident_id"])["incident_id"],
                pd.read_parquet(incidents_path, columns=["system_id"])["system_id"],
            )
        )

        groups_table = pq.read_table(groups_path)
        groups_df = groups_table.to_pandas()

        out_views_file = DATA_DIR / "artifacts" / slug / f"views_{args.method}.jsonl"
        out_views_file.parent.mkdir(parents=True, exist_ok=True)

        views_count = 0
        with out_views_file.open("w", encoding="utf-8") as handle:
            for incident_id, incident_groups_frame in groups_df.groupby("incident_id", sort=False):
                system_id = incidents_system_map.get(str(incident_id), "unknown")
                view = build_view(str(incident_id), str(system_id), incident_groups_frame)
                view_dict = view_to_dict(view)
                handle.write(json.dumps(view_dict, ensure_ascii=False) + "\n")
                views_count += 1

        results[slug] = {"views_file": str(out_views_file), "views_count": views_count}
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


def _load_views_map(views_jsonl_path: Path) -> dict[str, IncidentView]:
    views_map: dict[str, IncidentView] = {}
    with views_jsonl_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            view = view_from_dict(payload)
            views_map[view.incident_id] = view
    return views_map


def cmd_train_logreg(args: argparse.Namespace) -> int:
    slug = args.dataset
    if slug != "rcaeval":
        raise ValueError("train-logreg is only applicable to rcaeval (Nezha is external test only)")

    views_file = DATA_DIR / "artifacts" / slug / f"views_{args.method}.jsonl"
    if not views_file.exists():
        raise FileNotFoundError(f"Views file not found at {views_file}. Run views first.")

    candidates_file = DATA_DIR / "artifacts" / slug / "candidates.json"
    if not candidates_file.exists():
        raise FileNotFoundError(f"Candidates file not found at {candidates_file}. Run candidates first.")

    candidates_inventory = load_candidates(candidates_file)
    splits_frame = load_splits(NORMALIZED_DIR / slug)
    train_ids = set(splits_frame[splits_frame["split_purpose"] == "train"]["incident_id"])
    val_ids = set(splits_frame[splits_frame["split_purpose"] == "val"]["incident_id"])

    gt_path = NORMALIZED_DIR / slug / "ground_truth.parquet"
    gt_frame = pd.read_parquet(gt_path)
    gt_map = dict(zip(gt_frame["incident_id"], gt_frame["canonical_target"]))

    views_map = _load_views_map(views_file)
    train_views = [views_map[i_id] for i_id in train_ids if i_id in views_map]
    val_views = [views_map[i_id] for i_id in val_ids if i_id in views_map]

    out_model_dir = DATA_DIR / "artifacts" / slug / "models" / args.features
    ranker, metadata = train_logreg_model(
        train_views=train_views,
        val_views=val_views,
        ground_truth_lookup=gt_map,
        candidates_inventory=candidates_inventory,
        feature_set=args.features,
        output_directory=out_model_dir,
        random_seed=args.seed,
    )
    print(json.dumps({"model_dir": str(out_model_dir), "metadata": metadata}, indent=2, ensure_ascii=False))
    return 0


def cmd_rank(args: argparse.Namespace) -> int:
    if args.split in ("test", "external_test") and not getattr(args, "allow_test", False):
        print(
            f"Error: Split '{args.split}' is protected. You must pass --allow-test to rank test partitions.",
            file=sys.stderr,
        )
        return 1

    slug = args.dataset
    views_file = DATA_DIR / "artifacts" / slug / f"views_{args.method}.jsonl"
    if not views_file.exists():
        raise FileNotFoundError(f"Views file not found at {views_file}. Run views first.")

    views_map = _load_views_map(views_file)
    splits_frame = load_splits(NORMALIZED_DIR / slug)
    split_incident_ids = splits_frame[splits_frame["split_purpose"] == args.split]["incident_id"].tolist()

    # Initialize ranker
    ranker_name = args.ranker.lower()
    if ranker_name == "r1":
        ranker = MostLogsAfterRanker()
    elif ranker_name == "r2":
        ranker = MostErrorsAfterRanker()
    elif ranker_name == "r3":
        ranker = GrowthAfterRanker()
    elif ranker_name in ("r4", "r5"):
        model_dir = DATA_DIR / "artifacts" / slug / "models" / ranker_name
        ranker = load_logreg_ranker(model_dir)
    else:
        raise ValueError(f"Unsupported ranker {args.ranker!r}")

    # Determine candidates mode
    candidate_mode = "train_inventory" if slug == "rcaeval" else "observed_candidates"
    candidates_inventory = {}
    if candidate_mode == "train_inventory":
        cand_file = DATA_DIR / "artifacts" / slug / "candidates.json"
        if not cand_file.exists():
            raise FileNotFoundError(f"candidates.json not found at {cand_file}")
        candidates_inventory = load_candidates(cand_file)

    now_iso = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_id = f"{slug}_{ranker_name}_{args.method}_{args.split}_{now_iso}"
    run_directory = DATA_DIR / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=True)

    prediction_records: list[dict[str, Any]] = []
    for incident_id in split_incident_ids:
        if incident_id not in views_map:
            continue
        view = views_map[incident_id]
        if candidate_mode == "train_inventory":
            candidates = candidates_inventory.get(view.system_id, [])
        else:
            candidates = observed_candidates(view)

        ranked_services: list[RankedService] = ranker.rank(view, candidates)
        for r in ranked_services:
            prediction_records.append({
                "incident_id": incident_id,
                "service_id": r.service_id,
                "score": r.score,
                "rank": r.rank,
                "supporting_group_ids": list(r.supporting_group_ids),
                "method": r.method,
            })

    predictions_parquet = run_directory / "predictions.parquet"
    pred_frame = pd.DataFrame(prediction_records)
    arrow_table = pa.Table.from_pandas(pred_frame, schema=PREDICTIONS_SCHEMA, preserve_index=False)
    pq.write_table(arrow_table, predictions_parquet)

    groups_parquet_path = DATA_DIR / "artifacts" / slug / f"groups_{args.method}" / GROUPS_PARQUET_NAME
    splits_parquet_path = NORMALIZED_DIR / slug / "splits.parquet"

    manifest_payload = {
        "run_id": run_id,
        "dataset": slug,
        "ranker": ranker_name,
        "grouping_method": args.method,
        "split": args.split,
        "candidate_mode": candidate_mode,
        "total_evaluated_incidents": len(split_incident_ids),
        "splits_sha256": sha256_file(splits_parquet_path) if splits_parquet_path.exists() else None,
        "groups_sha256": sha256_file(groups_parquet_path) if groups_parquet_path.exists() else None,
        "git_state": git_state(),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    (run_directory / "manifest.json").write_text(json.dumps(manifest_payload, indent=2) + "\n")

    print(json.dumps({"run_id": run_id, "run_dir": str(run_directory)}, indent=2))
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    run_input = Path(args.run)
    if not run_input.is_dir():
        run_dir = DATA_DIR / "runs" / args.run
    else:
        run_dir = run_input

    if not run_dir.exists():
        raise FileNotFoundError(f"Run directory not found at {run_dir}")

    predictions_file = run_dir / "predictions.parquet"
    manifest_file = run_dir / "manifest.json"
    if not predictions_file.exists():
        raise FileNotFoundError(f"predictions.parquet not found at {predictions_file}")

    run_manifest = json.loads(manifest_file.read_text()) if manifest_file.exists() else {}
    dataset_slug = run_manifest.get("dataset", "rcaeval")
    split_name = run_manifest.get("split", "val")

    splits_frame = load_splits(NORMALIZED_DIR / dataset_slug)
    gt_frame = pd.read_parquet(NORMALIZED_DIR / dataset_slug / "ground_truth.parquet")
    gt_map = dict(zip(gt_frame["incident_id"], gt_frame["canonical_target"]))

    pred_table = pq.read_table(predictions_file)
    pred_df = pred_table.to_pandas()

    rankings_list: list[IncidentRanking] = []
    top1_ties_count = 0

    for incident_id, group_frame in pred_df.groupby("incident_id"):
        sorted_group = group_frame.sort_values("rank")
        ranked_services = tuple(sorted_group["service_id"])
        target_service = gt_map.get(str(incident_id))
        targets_set = frozenset({target_service}) if target_service else frozenset()
        candidates_set = frozenset(ranked_services)

        # Check tie at top score
        if len(sorted_group) > 1:
            top_score = sorted_group["score"].iloc[0]
            if sorted_group["score"].iloc[1] == top_score:
                top1_ties_count += 1

        rankings_list.append(IncidentRanking(
            incident_id=str(incident_id),
            ranked_services=ranked_services,
            targets=targets_set,
            candidates=candidates_set,
        ))

    summary_metrics = summarize(rankings_list, ks=(1, 3, 5))
    summary_metrics["top1_tie_proportion"] = top1_ties_count / len(rankings_list) if rankings_list else 0.0

    # Breakdown by stratum
    splits_stratum_map = dict(zip(splits_frame["incident_id"], splits_frame["stratum"]))
    strata_metrics: dict[str, Any] = {}
    for stratum_name in set(splits_frame["stratum"]):
        stratum_rankings = [
            r for r in rankings_list if splits_stratum_map.get(r.incident_id) == stratum_name
        ]
        if stratum_rankings:
            strata_metrics[stratum_name] = summarize(stratum_rankings, ks=(1, 3, 5))

    summary_metrics["strata_metrics"] = strata_metrics

    # Baseline comparison
    baseline_report_dict: Optional[dict[str, Any]] = None
    if getattr(args, "baseline", None):
        scenario_map = dict(zip(splits_frame["incident_id"], splits_frame["scenario_id"]))
        candidate_top1_scores = {r.incident_id: hit_at_k(r, 1) for r in rankings_list}
        candidate_top3_scores = {r.incident_id: hit_at_k(r, 3) for r in rankings_list}
        candidate_rr_scores = {r.incident_id: reciprocal_rank(r) for r in rankings_list}

        baseline_spec = args.baseline.strip()
        if baseline_spec.lower() == "r0":
            baseline_top1_scores = {
                r.incident_id: expected_random_hit(len(r.candidates), r.covered, 1)
                for r in rankings_list
            }
            baseline_top3_scores = {
                r.incident_id: expected_random_hit(len(r.candidates), r.covered, 3)
                for r in rankings_list
            }
            baseline_rr_scores = {
                r.incident_id: expected_random_reciprocal_rank(len(r.candidates), r.covered)
                for r in rankings_list
            }
        else:
            # Baseline is another run_id
            base_run_dir = DATA_DIR / "runs" / baseline_spec if not Path(baseline_spec).is_dir() else Path(baseline_spec)
            base_pred_df = pq.read_table(base_run_dir / "predictions.parquet").to_pandas()
            base_rankings = {}
            for inc_id, b_group in base_pred_df.groupby("incident_id"):
                b_sorted = b_group.sort_values("rank")
                b_target = gt_map.get(str(inc_id))
                base_rankings[str(inc_id)] = IncidentRanking(
                    incident_id=str(inc_id),
                    ranked_services=tuple(b_sorted["service_id"]),
                    targets=frozenset({b_target}) if b_target else frozenset(),
                    candidates=frozenset(b_sorted["service_id"]),
                )
            baseline_top1_scores = {inc: hit_at_k(base_rankings[inc], 1) for inc in candidate_top1_scores}
            baseline_top3_scores = {inc: hit_at_k(base_rankings[inc], 3) for inc in candidate_top1_scores}
            baseline_rr_scores = {inc: reciprocal_rank(base_rankings[inc]) for inc in candidate_top1_scores}

        bootstrap_top1 = paired_bootstrap(candidate_top1_scores, baseline_top1_scores, scenario_map)
        bootstrap_top3 = paired_bootstrap(candidate_top3_scores, baseline_top3_scores, scenario_map)
        bootstrap_rr = paired_bootstrap(candidate_rr_scores, baseline_rr_scores, scenario_map)

        baseline_report_dict = {
            "baseline": baseline_spec,
            "top1": bootstrap_top1.to_dict(),
            "top3": bootstrap_top3.to_dict(),
            "rr": bootstrap_rr.to_dict(),
        }
        summary_metrics["baseline_comparison"] = baseline_report_dict

    out_metrics_file = run_dir / "metrics.json"
    out_metrics_file.write_text(json.dumps(summary_metrics, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(summary_metrics, indent=2, ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command")

    # group
    group_p = commands.add_parser("group", help="Build groups.parquet for a dataset")
    group_p.add_argument("dataset", choices=[*SUPPORTED_DATASETS, "all"])
    group_p.add_argument("--method", choices=["g1", "g2"], default="g2")
    group_p.add_argument("--before-seconds", type=float, default=None)
    group_p.add_argument("--after-seconds", type=float, default=None)
    group_p.add_argument("--batch-size", type=int, default=20_000)

    # candidates
    cand_p = commands.add_parser("candidates", help="Build candidate inventory")
    cand_p.add_argument("dataset", choices=[*SUPPORTED_DATASETS, "all"])
    cand_p.add_argument("--method", choices=["g1", "g2"], default="g2")

    # views
    views_p = commands.add_parser("views", help="Build IncidentViews jsonl")
    views_p.add_argument("dataset", choices=[*SUPPORTED_DATASETS, "all"])
    views_p.add_argument("--method", choices=["g1", "g2"], default="g2")

    # train-logreg
    train_p = commands.add_parser("train-logreg", help="Train Logistic Regression ranker on train split")
    train_p.add_argument("dataset", choices=["rcaeval"])
    train_p.add_argument("--features", choices=["r4", "r5"], default="r4")
    train_p.add_argument("--method", choices=["g1", "g2"], default="g2")
    train_p.add_argument("--seed", type=int, default=42)

    # rank
    rank_p = commands.add_parser("rank", help="Rank candidates for incidents in a split")
    rank_p.add_argument("dataset", choices=["rcaeval", "nezha"])
    rank_p.add_argument("--ranker", choices=["r1", "r2", "r3", "r4", "r5", "kev"], required=True)
    rank_p.add_argument("--method", choices=["g1", "g2"], default="g2")
    rank_p.add_argument("--split", choices=["train", "val", "test", "external_test"], default="val")
    rank_p.add_argument("--allow-test", action="store_true", help="Flag to confirm ranking on held-out test splits")

    # evaluate
    eval_p = commands.add_parser("evaluate", help="Compute metrics and paired bootstrap comparisons")
    eval_p.add_argument("--run", required=True, help="Run ID or path to run directory")
    eval_p.add_argument("--baseline", default=None, help="Baseline run ID, path, or 'r0'")

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "group":
        return cmd_group(args)
    if args.command == "candidates":
        return cmd_candidates(args)
    if args.command == "views":
        return cmd_views(args)
    if args.command == "train-logreg":
        return cmd_train_logreg(args)
    if args.command == "rank":
        return cmd_rank(args)
    if args.command == "evaluate":
        return cmd_evaluate(args)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
