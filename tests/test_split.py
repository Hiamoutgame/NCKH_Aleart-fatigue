"""Unit and integration tests for dataset splitting and integrity verification.

Tests cover:
  - Scenario identifier extraction (stripping repetition suffixes)
  - Repetition leakage prevention (guaranteeing scenario runs stay within the same partition)
  - Stratification across suite and system combinations
  - Deterministic splitting given fixed random seeds
  - External test assignment for out-of-distribution evaluation (Nezha)
  - Strict validation of split contracts (verify_splits detecting leakage and tampering)
  - Cryptographic SHA-256 integrity checks upon loading saved split tables
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

import pandas as pd
import pytest

from src.evaluation.split import (
    SPLIT_MANIFEST_NAME,
    SPLITS_PARQUET_NAME,
    SplitPurpose,
    compute_stratum_identifier,
    create_nezha_splits,
    extract_scenario_id,
    load_split_incidents,
    load_splits,
    save_splits,
    stratified_scenario_split,
    verify_splits,
)
from src.shared.infrastructure.paths import NORMALIZED_DIR


def create_synthetic_rcaeval_incidents_dataframe(
    scenarios_per_stratum: int = 5,
    repetition_runs_per_scenario: int = 3,
) -> pd.DataFrame:
    """Build a deterministic synthetic RCAEval incidents DataFrame for testing."""
    strata_definitions: Sequence[tuple[str, str]] = [
        ("re2", "ob"),
        ("re2", "ss"),
        ("re2", "tt"),
        ("re3", "ob"),
        ("re3", "ss"),
        ("re3", "tt"),
    ]

    rows_list: list[dict[str, object]] = []
    for suite_name, system_identifier in strata_definitions:
        for scenario_index in range(1, scenarios_per_stratum + 1):
            base_scenario_name = f"{suite_name}{system_identifier}_fault_{scenario_index}"
            for repetition_index in range(1, repetition_runs_per_scenario + 1):
                case_identifier = f"{base_scenario_name}_{repetition_index}"
                rows_list.append({
                    "incident_id": f"rcaeval_{case_identifier}",
                    "source_case_id": case_identifier,
                    "dataset_source": "rcaeval",
                    "system_id": system_identifier,
                    "root_cause_service": f"service_{scenario_index}",
                    "time_start": 1700000000 + scenario_index * 1000 + repetition_index * 60,
                    "time_end": 1700001000 + scenario_index * 1000 + repetition_index * 60,
                    "inject_time": 1700000500 + scenario_index * 1000 + repetition_index * 60,
                })

    return pd.DataFrame(rows_list)


def test_extract_scenario_id_strips_repetition_suffixes():
    """Verify stripping of repetition run numbers while preserving base scenario identity."""
    assert extract_scenario_id("re2ob_cartservice_cpu_1") == "re2ob_cartservice_cpu"
    assert extract_scenario_id("re2ob_cartservice_cpu_12") == "re2ob_cartservice_cpu"
    assert extract_scenario_id("re3tt_ts-order-service_f1_3") == "re3tt_ts-order-service_f1"
    assert extract_scenario_id("re2ss_orders_loss_99") == "re2ss_orders_loss"
    # Case identifiers without repetition suffix remain unchanged
    assert extract_scenario_id("re2ob_cartservice_cpu") == "re2ob_cartservice_cpu"
    # Nezha identifiers remain untouched
    assert extract_scenario_id("nezha_1661140434") == "nezha_1661140434"
    # Empty or whitespace handling
    assert extract_scenario_id("") == ""
    assert extract_scenario_id("   ") == ""


def test_compute_stratum_identifier_combines_suite_and_system():
    """Verify stratum string construction with normalization."""
    assert compute_stratum_identifier("re2", "ob") == "re2_ob"
    assert compute_stratum_identifier("RE3", "TT") == "re3_tt"
    assert compute_stratum_identifier("  re2  ", "  ss  ") == "re2_ss"


def test_stratified_scenario_split_validates_ratio_sum():
    """Verify split raises ValueError when ratios do not sum to 1.0."""
    sample_dataframe = create_synthetic_rcaeval_incidents_dataframe(scenarios_per_stratum=2)
    with pytest.raises(ValueError, match="Split ratios must sum to 1.0"):
        stratified_scenario_split(
            sample_dataframe,
            train_ratio=0.70,
            validation_ratio=0.20,
            test_ratio=0.20,
        )


def test_stratified_scenario_split_repetition_leakage_free():
    """Ensure no fault scenario has runs divided across different split partitions."""
    synthetic_incidents = create_synthetic_rcaeval_incidents_dataframe(
        scenarios_per_stratum=6,
        repetition_runs_per_scenario=3,
    )
    splits_dataframe = stratified_scenario_split(
        synthetic_incidents,
        train_ratio=0.70,
        validation_ratio=0.15,
        test_ratio=0.15,
        random_seed=42,
    )

    # Every incident run of the same scenario must have the identical split purpose
    for scenario_identifier, grouped_rows in splits_dataframe.groupby("scenario_id"):
        assigned_purposes = set(grouped_rows["split_purpose"])
        assert len(assigned_purposes) == 1, (
            f"Scenario {scenario_identifier} is leaked across multiple splits: {assigned_purposes}"
        )

    train_scenarios = set(
        splits_dataframe[splits_dataframe["split_purpose"] == "train"]["scenario_id"]
    )
    validation_scenarios = set(
        splits_dataframe[splits_dataframe["split_purpose"] == "val"]["scenario_id"]
    )
    test_scenarios = set(
        splits_dataframe[splits_dataframe["split_purpose"] == "test"]["scenario_id"]
    )

    # Mathematical guarantee of disjoint sets
    assert train_scenarios.isdisjoint(validation_scenarios)
    assert train_scenarios.isdisjoint(test_scenarios)
    assert validation_scenarios.isdisjoint(test_scenarios)


def test_stratified_scenario_split_stratification():
    """Verify that all strata are represented in train, validation, and test partitions."""
    synthetic_incidents = create_synthetic_rcaeval_incidents_dataframe(
        scenarios_per_stratum=6,
        repetition_runs_per_scenario=3,
    )
    splits_dataframe = stratified_scenario_split(
        synthetic_incidents,
        train_ratio=0.70,
        validation_ratio=0.15,
        test_ratio=0.15,
        random_seed=42,
    )

    strata_in_splits = splits_dataframe.groupby(["stratum", "split_purpose"]).size().unstack(fill_value=0)
    for stratum_name in strata_in_splits.index:
        assert strata_in_splits.loc[stratum_name, "train"] > 0
        assert strata_in_splits.loc[stratum_name, "val"] > 0
        assert strata_in_splits.loc[stratum_name, "test"] > 0


def test_stratified_scenario_split_determinism():
    """Verify that splitting with the same seed produces identical output tables."""
    synthetic_incidents = create_synthetic_rcaeval_incidents_dataframe(scenarios_per_stratum=4)

    first_run_dataframe = stratified_scenario_split(synthetic_incidents, random_seed=42)
    second_run_dataframe = stratified_scenario_split(synthetic_incidents, random_seed=42)
    different_seed_dataframe = stratified_scenario_split(synthetic_incidents, random_seed=99)

    pd.testing.assert_frame_equal(first_run_dataframe, second_run_dataframe)
    # With high probability, a different seed generates different assignments
    assert not first_run_dataframe["split_purpose"].equals(
        different_seed_dataframe["split_purpose"]
    )


def test_stratified_scenario_split_handles_unlogged_incidents():
    """Verify incidents missing logs are categorized as excluded_no_logs."""
    synthetic_incidents = create_synthetic_rcaeval_incidents_dataframe(scenarios_per_stratum=4)
    all_incident_identifiers = synthetic_incidents["incident_id"].tolist()

    # Designate only half of the incidents as having valid logs
    logged_subset = set(all_incident_identifiers[: len(all_incident_identifiers) // 2])
    splits_dataframe = stratified_scenario_split(
        synthetic_incidents,
        incidents_with_logs=logged_subset,
        random_seed=42,
    )

    unlogged_records = splits_dataframe[~splits_dataframe["has_logs"]]
    assert len(unlogged_records) == len(all_incident_identifiers) - len(logged_subset)
    assert (unlogged_records["split_purpose"] == "excluded_no_logs").all()


def test_nezha_external_test_assignment():
    """Verify 100% of Nezha incidents with logs receive external_test purpose."""
    sample_nezha_incidents = pd.DataFrame([
        {
            "incident_id": "nezha_1661140434",
            "source_case_id": "nezha_1661140434",
            "dataset_source": "nezha",
            "system_id": "ob",
        },
        {
            "incident_id": "nezha_1661140500",
            "source_case_id": "nezha_1661140500",
            "dataset_source": "nezha",
            "system_id": "tt",
        },
        {
            "incident_id": "nezha_unlogged",
            "source_case_id": "nezha_unlogged",
            "dataset_source": "nezha",
            "system_id": "tt",
        },
    ])

    logged_identifiers = {"nezha_1661140434", "nezha_1661140500"}
    splits_dataframe = create_nezha_splits(
        sample_nezha_incidents,
        incidents_with_logs=logged_identifiers,
    )

    logged_rows = splits_dataframe[splits_dataframe["has_logs"]]
    assert len(logged_rows) == 2
    assert (logged_rows["split_purpose"] == SplitPurpose.EXTERNAL_TEST.value).all()

    unlogged_rows = splits_dataframe[~splits_dataframe["has_logs"]]
    assert len(unlogged_rows) == 1
    assert (unlogged_rows["split_purpose"] == SplitPurpose.EXCLUDED_NO_LOGS.value).all()


def test_verify_splits_catches_repetition_leakage():
    """Verify verify_splits detects cross-partition leakage of repeated scenarios."""
    synthetic_incidents = create_synthetic_rcaeval_incidents_dataframe(scenarios_per_stratum=4)
    splits_dataframe = stratified_scenario_split(synthetic_incidents, random_seed=42)

    # Deliberately contaminate the split: shift one run of a train scenario to test
    corrupted_splits = splits_dataframe.copy()
    train_scenario_name = corrupted_splits[
        corrupted_splits["split_purpose"] == "train"
    ]["scenario_id"].iloc[0]
    indices_to_modify = corrupted_splits[
        corrupted_splits["scenario_id"] == train_scenario_name
    ].index

    assert len(indices_to_modify) > 1
    corrupted_splits.loc[indices_to_modify[0], "split_purpose"] = "test"

    verification_report = verify_splits(corrupted_splits, synthetic_incidents)
    assert verification_report["passed"] is False
    assert any("Repetition leakage detected" in failure for failure in verification_report["failures"])


def test_verify_splits_catches_missing_and_duplicate_incidents():
    """Verify verify_splits detects missing or duplicated incident IDs."""
    synthetic_incidents = create_synthetic_rcaeval_incidents_dataframe(scenarios_per_stratum=3)
    splits_dataframe = stratified_scenario_split(synthetic_incidents, random_seed=42)

    # Drop one incident to simulate missing record
    dropped_splits = splits_dataframe.iloc[1:].copy()
    verification_report_missing = verify_splits(dropped_splits, synthetic_incidents)
    assert verification_report_missing["passed"] is False
    assert any("Incident ID mismatch" in failure for failure in verification_report_missing["failures"])

    # Duplicate one incident to simulate duplicate error
    duplicated_splits = pd.concat([splits_dataframe, splits_dataframe.iloc[:1]], ignore_index=True)
    verification_report_duplicate = verify_splits(duplicated_splits, synthetic_incidents)
    assert verification_report_duplicate["passed"] is False
    assert any("Duplicate incident_id" in failure for failure in verification_report_duplicate["failures"])


def test_verify_splits_catches_unlogged_evaluation_incident():
    """Verify verify_splits fails if an incident marked for evaluation lacks logs."""
    synthetic_incidents = create_synthetic_rcaeval_incidents_dataframe(scenarios_per_stratum=3)
    splits_dataframe = stratified_scenario_split(synthetic_incidents, random_seed=42)

    corrupted_splits = splits_dataframe.copy()
    # Mark an evaluated incident as has_logs = False
    corrupted_splits.loc[0, "has_logs"] = False

    verification_report = verify_splits(corrupted_splits, synthetic_incidents)
    assert verification_report["passed"] is False
    assert any("Evaluation incidents lack logs" in failure for failure in verification_report["failures"])


def test_save_and_load_splits_roundtrip_with_integrity_check(tmp_path: Path):
    """Verify saving splits persists parquet and manifest with valid sha256 checksum."""
    synthetic_incidents = create_synthetic_rcaeval_incidents_dataframe(scenarios_per_stratum=3)
    splits_dataframe = stratified_scenario_split(synthetic_incidents, random_seed=42)

    settings_metadata = {"seed": 42, "train_ratio": 0.70, "val_ratio": 0.15, "test_ratio": 0.15}
    splits_parquet_path, manifest_path = save_splits(tmp_path, splits_dataframe, settings_metadata)

    assert splits_parquet_path.exists()
    assert manifest_path.exists()

    loaded_dataframe = load_splits(tmp_path)
    pd.testing.assert_frame_equal(loaded_dataframe, splits_dataframe)

    # Test load_split_incidents filtering
    training_incident_ids = load_split_incidents(tmp_path, SplitPurpose.TRAIN)
    expected_training_ids = splits_dataframe[
        splits_dataframe["split_purpose"] == "train"
    ]["incident_id"].tolist()
    assert training_incident_ids == expected_training_ids


def test_load_splits_tamper_detection(tmp_path: Path):
    """Verify load_splits raises ValueError when splits.parquet or manifest is tampered with."""
    synthetic_incidents = create_synthetic_rcaeval_incidents_dataframe(scenarios_per_stratum=3)
    splits_dataframe = stratified_scenario_split(synthetic_incidents, random_seed=42)

    save_splits(tmp_path, splits_dataframe, {"seed": 42})
    splits_parquet_path = tmp_path / SPLITS_PARQUET_NAME

    # Append arbitrary byte to corrupt the parquet file
    with splits_parquet_path.open("ab") as file_handle:
        file_handle.write(b"\x00")

    with pytest.raises(ValueError, match="Integrity check failed"):
        load_splits(tmp_path)


def test_load_splits_missing_files_error(tmp_path: Path):
    """Verify FileNotFoundError is raised when files do not exist."""
    with pytest.raises(FileNotFoundError, match="Splits table not found"):
        load_splits(tmp_path)

    # Create only splits.parquet without manifest
    empty_parquet_path = tmp_path / SPLITS_PARQUET_NAME
    empty_parquet_path.write_bytes(b"dummy")
    with pytest.raises(FileNotFoundError, match="Split manifest not found"):
        load_splits(tmp_path)


def test_real_rcaeval_and_nezha_splits_artifacts_if_present():
    """Verify actual repository artifacts if normalized data directory is present."""
    rcaeval_directory = NORMALIZED_DIR / "rcaeval"
    if (rcaeval_directory / SPLITS_PARQUET_NAME).exists():
        rcaeval_splits = load_splits(rcaeval_directory)
        incidents_parquet_path = rcaeval_directory / "incidents.parquet"
        if incidents_parquet_path.exists():
            incidents_frame = pd.read_parquet(incidents_parquet_path)
            verification_report = verify_splits(rcaeval_splits, incidents_frame)
            assert verification_report["passed"] is True, f"RCAEval verification failed: {verification_report}"

        purpose_counts = rcaeval_splits["split_purpose"].value_counts().to_dict()
        # Match specifications: 254 train, 48 val, 57 test, 376 excluded_no_logs (total 735)
        assert purpose_counts.get("train") == 254
        assert purpose_counts.get("val") == 48
        assert purpose_counts.get("test") == 57
        assert purpose_counts.get("excluded_no_logs") == 376

    nezha_directory = NORMALIZED_DIR / "nezha"
    if (nezha_directory / SPLITS_PARQUET_NAME).exists():
        nezha_splits = load_splits(nezha_directory)
        incidents_parquet_path = nezha_directory / "incidents.parquet"
        if incidents_parquet_path.exists():
            incidents_frame = pd.read_parquet(incidents_parquet_path)
            verification_report = verify_splits(nezha_splits, incidents_frame)
            assert verification_report["passed"] is True, f"Nezha verification failed: {verification_report}"

        purpose_counts = nezha_splits["split_purpose"].value_counts().to_dict()
        assert purpose_counts.get("external_test") == 101
