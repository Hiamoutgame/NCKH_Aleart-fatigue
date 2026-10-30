"""Unit tests for Logistic Regression rankers (R4, R5) and feature extractors."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from src.ranking import (
    R4_FEATURE_NAMES,
    R5_FEATURE_NAMES,
    extract_candidate_features,
    load_logreg_ranker,
    train_logreg_model,
)
from src.views import GroupSummary, IncidentView, ServiceView


def create_synthetic_incident_view(incident_id: str, is_target_cart: bool) -> IncidentView:
    """Construct synthetic incident view with distinct signal for cartservice vs others."""
    cart_groups = (
        GroupSummary(
            group_id="g1", template_text="Redis timeout",
            n_before=10, n_after=200 if is_target_cart else 10,
            n_error_after=150 if is_target_cart else 0,
            n_warn_after=0,
            is_new_after=is_target_cart,
            first_after_offset_s=5.0,
        ),
    )
    ad_groups = (
        GroupSummary(
            group_id="g2", template_text="Ad display",
            n_before=50, n_after=50,
            n_error_after=0,
            n_warn_after=0,
            is_new_after=False,
            first_after_offset_s=10.0,
        ),
    )

    cart_service = ServiceView(
        service_id="cartservice",
        n_before=10, n_after=200 if is_target_cart else 10,
        n_error_after=150 if is_target_cart else 0,
        n_warn_after=0, n_unknown_after=0, n_templates_after=1,
        groups=cart_groups,
    )
    ad_service = ServiceView(
        service_id="adservice",
        n_before=50, n_after=50,
        n_error_after=0, n_warn_after=0, n_unknown_after=0, n_templates_after=1,
        groups=ad_groups,
    )

    return IncidentView(
        incident_id=incident_id, system_id="ob", method="g2",
        before_seconds=600.0, after_seconds=600.0,
        services=(cart_service, ad_service),
    )


def test_feature_extraction_vector_dimensions_and_finite_values():
    """Verify feature vector length, absence of NaN/inf, and zero-handling for absent candidates."""
    view = create_synthetic_incident_view("inc_1", is_target_cart=True)

    r4_features = extract_candidate_features(view, "cartservice", feature_set="r4")
    assert len(r4_features) == len(R4_FEATURE_NAMES)
    assert np.isfinite(r4_features).all()
    assert r4_features[0] == 1.0  # has_logs
    assert r4_features[1] == 200.0  # log_count

    r5_features = extract_candidate_features(view, "cartservice", feature_set="r5")
    assert len(r5_features) == len(R5_FEATURE_NAMES)
    assert np.isfinite(r5_features).all()

    # Candidate with no logs
    unobserved_features = extract_candidate_features(view, "emailservice", feature_set="r5")
    assert len(unobserved_features) == len(R5_FEATURE_NAMES)
    assert all(val == 0.0 for val in unobserved_features)


def test_train_logreg_model_and_persistence_roundtrip(tmp_path: Path):
    """Verify training LogisticRegressionRanker selects C and saves model artifacts."""
    # Create 4 training incidents
    train_views = [
        create_synthetic_incident_view("train_1", is_target_cart=True),
        create_synthetic_incident_view("train_2", is_target_cart=False),
        create_synthetic_incident_view("train_3", is_target_cart=True),
        create_synthetic_incident_view("train_4", is_target_cart=False),
    ]
    val_views = [
        create_synthetic_incident_view("val_1", is_target_cart=True),
        create_synthetic_incident_view("val_2", is_target_cart=False),
    ]

    ground_truth = {
        "train_1": "cartservice",
        "train_2": "adservice",
        "train_3": "cartservice",
        "train_4": "adservice",
        "val_1": "cartservice",
        "val_2": "adservice",
    }
    candidates_inventory = {"ob": ["adservice", "cartservice", "emailservice"]}

    output_dir = tmp_path / "models" / "r4"
    ranker, metadata = train_logreg_model(
        train_views=train_views,
        val_views=val_views,
        ground_truth_lookup=ground_truth,
        candidates_inventory=candidates_inventory,
        feature_set="r4",
        output_directory=output_dir,
        random_seed=42,
    )

    assert (output_dir / "model.joblib").exists()
    assert (output_dir / "config.json").exists()
    assert metadata["selected_c"] in (0.01, 0.1, 1.0, 10.0)
    assert metadata["train_incident_count"] == 4

    # Reload ranker from disk
    loaded_ranker = load_logreg_ranker(output_dir)
    ranked = loaded_ranker.rank(val_views[0], candidates_inventory["ob"])
    assert len(ranked) == 3
    # For val_1 where cartservice is true target, cartservice should rank first
    assert ranked[0].service_id == "cartservice"
    assert ranked[0].rank == 1
