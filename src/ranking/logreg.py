"""Logistic Regression supervised rankers R4 (basic) and R5 (enhanced).

Trains Pipeline(StandardScaler(), LogisticRegression(class_weight='balanced')) exclusively
on the train split, tuning hyperparameter C on validation MRR.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

import numpy as np

# Ensure extra local packages are discoverable
EXTRA_PACKAGES_DIR = Path(__file__).resolve().parents[2] / ".cache" / "site-packages"
if EXTRA_PACKAGES_DIR.exists() and str(EXTRA_PACKAGES_DIR) not in sys.path:
    sys.path.insert(0, str(EXTRA_PACKAGES_DIR))

import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.evaluation.metrics import IncidentRanking, reciprocal_rank
from src.ranking.base import RankedService, ServiceRanker, sort_services_by_score
from src.ranking.features import (
    R4_FEATURE_NAMES,
    R5_FEATURE_NAMES,
    build_incident_feature_matrix,
)
from src.ranking.rules import select_supporting_group_ids
from src.views.incident_view import IncidentView

C_CANDIDATE_VALUES = (0.01, 0.1, 1.0, 10.0)


class LogisticRegressionRanker(ServiceRanker):
    """Supervised logistic regression ranker using calibrated class-1 posterior probabilities."""

    def __init__(
        self,
        model_pipeline: Pipeline,
        feature_set: str = "r4",
        name: Optional[str] = None,
    ) -> None:
        self.model_pipeline = model_pipeline
        self.feature_set = feature_set.lower().strip()
        self.name = name or self.feature_set

    def rank(
        self,
        incident_view: IncidentView,
        candidate_services: Sequence[str],
    ) -> list[RankedService]:
        unique_candidates = list(dict.fromkeys(candidate_services))
        if not unique_candidates:
            return []

        feature_matrix = build_incident_feature_matrix(
            incident_view=incident_view,
            candidate_services=unique_candidates,
            feature_set=self.feature_set,
        )

        probabilities = self.model_pipeline.predict_proba(feature_matrix)[:, 1]
        scores_dictionary = {
            candidate_id: float(probabilities[index])
            for index, candidate_id in enumerate(unique_candidates)
        }

        sorted_candidate_ids = sort_services_by_score(scores_dictionary)
        service_view_lookup = {
            service_view.service_id: service_view for service_view in incident_view.services
        }

        ranked_results: list[RankedService] = []
        for rank_position, service_id in enumerate(sorted_candidate_ids, start=1):
            service_view = service_view_lookup.get(service_id)
            supporting_groups = (
                select_supporting_group_ids(service_view.groups) if service_view is not None else ()
            )
            ranked_results.append(RankedService(
                service_id=service_id,
                score=scores_dictionary[service_id],
                rank=rank_position,
                supporting_group_ids=supporting_groups,
                method=f"{self.name}|evidence:new>error>count",
            ))

        return ranked_results


def build_training_dataset(
    incident_views: Sequence[IncidentView],
    ground_truth_lookup: Mapping[str, str],
    candidates_inventory: Mapping[str, Sequence[str]],
    feature_set: str,
) -> tuple[np.ndarray, np.ndarray, int]:
    """Build X and y feature arrays from training incident views.

    Returns (X, y, unobserved_target_incident_count).
    """
    feature_rows: list[list[float]] = []
    binary_labels: list[int] = []
    unobserved_target_count = 0

    for incident_view in incident_views:
        target_service = ground_truth_lookup.get(incident_view.incident_id)
        system_candidates = candidates_inventory.get(incident_view.system_id, [])

        if target_service not in system_candidates:
            unobserved_target_count += 1

        feature_matrix = build_incident_feature_matrix(
            incident_view=incident_view,
            candidate_services=system_candidates,
            feature_set=feature_set,
        )

        for index, candidate_id in enumerate(system_candidates):
            feature_rows.append(feature_matrix[index].tolist())
            binary_labels.append(1 if (target_service and candidate_id == target_service) else 0)

    feature_array = np.array(feature_rows, dtype=np.float64)
    label_array = np.array(binary_labels, dtype=np.int32)
    return feature_array, label_array, unobserved_target_count


def train_logreg_model(
    train_views: Sequence[IncidentView],
    val_views: Sequence[IncidentView],
    ground_truth_lookup: Mapping[str, str],
    candidates_inventory: Mapping[str, Sequence[str]],
    feature_set: str = "r4",
    output_directory: Optional[Path | str] = None,
    random_seed: int = 42,
) -> tuple[LogisticRegressionRanker, dict[str, Any]]:
    """Train Logistic Regression ranker, selecting C on validation MRR.

    Parameters:
        train_views: Sequence of IncidentView for train partition.
        val_views: Sequence of IncidentView for validation partition.
        ground_truth_lookup: Dict mapping incident_id to canonical root cause service.
        candidates_inventory: Dict mapping system_id to candidate microservices.
        feature_set: 'r4' or 'r5'.
        output_directory: Optional destination directory for model.joblib and config.json.
        random_seed: Random seed for Logistic Regression optimization.

    Returns:
        Tuple of (trained LogisticRegressionRanker, metadata dict).
    """
    feature_mode = feature_set.lower().strip()
    if feature_mode not in ("r4", "r5"):
        raise ValueError(f"Unsupported feature set {feature_set!r}")

    X_train, y_train, unobserved_targets_in_train = build_training_dataset(
        incident_views=train_views,
        ground_truth_lookup=ground_truth_lookup,
        candidates_inventory=candidates_inventory,
        feature_set=feature_mode,
    )

    val_mrr_by_c: dict[str, float] = {}

    # Evaluate each candidate C on validation MRR
    for c_value in C_CANDIDATE_VALUES:
        candidate_pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(
                C=c_value,
                class_weight="balanced",
                max_iter=1000,
                random_state=random_seed,
            )),
        ])
        candidate_pipeline.fit(X_train, y_train)

        candidate_ranker = LogisticRegressionRanker(
            model_pipeline=candidate_pipeline,
            feature_set=feature_mode,
        )

        mrr_sum = 0.0
        for val_view in val_views:
            val_target = ground_truth_lookup.get(val_view.incident_id)
            system_candidates = candidates_inventory.get(val_view.system_id, [])
            ranked_services = candidate_ranker.rank(val_view, system_candidates)
            ranking_record = IncidentRanking(
                incident_id=val_view.incident_id,
                ranked_services=tuple(s.service_id for s in ranked_services),
                targets=frozenset({val_target}) if val_target else frozenset(),
                candidates=frozenset(system_candidates),
            )
            mrr_sum += reciprocal_rank(ranking_record)

        mean_val_mrr = mrr_sum / len(val_views) if val_views else 0.0
        val_mrr_by_c[str(c_value)] = mean_val_mrr

    # Select C that maximizes MRR; in case of tie, select the smaller C value
    best_c_value = min(
        C_CANDIDATE_VALUES,
        key=lambda c: (-val_mrr_by_c[str(c)], c),
    )

    final_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", LogisticRegression(
            C=best_c_value,
            class_weight="balanced",
            max_iter=1000,
            random_state=random_seed,
        )),
    ])
    final_pipeline.fit(X_train, y_train)

    final_ranker = LogisticRegressionRanker(
        model_pipeline=final_pipeline,
        feature_set=feature_mode,
        name=feature_mode,
    )

    feature_names = list(R4_FEATURE_NAMES if feature_mode == "r4" else R5_FEATURE_NAMES)
    metadata = {
        "feature_set": feature_mode,
        "features": feature_names,
        "selected_c": best_c_value,
        "val_mrr_by_c": val_mrr_by_c,
        "train_incident_count": len(train_views),
        "train_row_count": len(X_train),
        "unobserved_targets_in_train": unobserved_targets_in_train,
    }

    if output_directory is not None:
        target_directory = Path(output_directory)
        target_directory.mkdir(parents=True, exist_ok=True)
        joblib.dump(final_pipeline, target_directory / "model.joblib")
        (target_directory / "config.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False) + "\n"
        )

    return final_ranker, metadata


def load_logreg_ranker(model_directory: Path | str) -> LogisticRegressionRanker:
    """Load a persisted LogisticRegressionRanker from disk."""
    target_directory = Path(model_directory)
    model_file_path = target_directory / "model.joblib"
    config_file_path = target_directory / "config.json"

    if not model_file_path.exists():
        raise FileNotFoundError(f"Model file not found at {model_file_path}")
    if not config_file_path.exists():
        raise FileNotFoundError(f"Config file not found at {config_file_path}")

    model_pipeline = joblib.load(model_file_path)
    config_payload = json.loads(config_file_path.read_text(encoding="utf-8"))
    feature_set = config_payload.get("feature_set", "r4")
    return LogisticRegressionRanker(model_pipeline=model_pipeline, feature_set=feature_set)
