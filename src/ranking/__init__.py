"""Candidate retrieval and ranking module."""

from .base import (
    RankedService,
    ServiceRanker,
    sort_services_by_score,
)
from .rules import (
    GrowthAfterRanker,
    MostErrorsAfterRanker,
    MostLogsAfterRanker,
    select_supporting_group_ids,
)
from .features import (
    R4_FEATURE_NAMES,
    R5_FEATURE_NAMES,
    build_incident_feature_matrix,
    extract_candidate_features,
)
from .logreg import (
    LogisticRegressionRanker,
    load_logreg_ranker,
    train_logreg_model,
)

from .candidates import (
    load_candidates,
    observed_candidates,
    save_candidates,
    train_inventory,
)

__all__ = [
    "RankedService",
    "ServiceRanker",
    "sort_services_by_score",
    "MostLogsAfterRanker",
    "MostErrorsAfterRanker",
    "GrowthAfterRanker",
    "select_supporting_group_ids",
    "R4_FEATURE_NAMES",
    "R5_FEATURE_NAMES",
    "extract_candidate_features",
    "build_incident_feature_matrix",
    "LogisticRegressionRanker",
    "train_logreg_model",
    "load_logreg_ranker",
    "load_candidates",
    "observed_candidates",
    "save_candidates",
    "train_inventory",
]
