"""Dataset split and purpose assignment module.

Implements scenario-based, stratified train/validation/test splitting for RCAEval
and external test assignment for Nezha, strictly adhering to:
  - docs/research/05_methodology/dataset.md (Section 4)
  - docs/research/research_protocol_v3.md (Section 4)

Key invariants:
  - Repetition leakage prevention: Every run of a repeated fault scenario
    (e.g., scenario 're2ob_cartservice_cpu' with runs '_1', '_2', '_3')
    must belong to the exact same split partition.
  - Stratification: Scenarios are stratified across (suite x system) strata
    to ensure all failure types and systems exist in train, validation, and test.
  - Determinism: Fixed seed guarantees reproducible assignments.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import re
from pathlib import Path
from typing import Any, Literal, Mapping, Optional, Sequence

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.shared.infrastructure.manifest import sha256_file

SPLIT_MANIFEST_NAME = "split_manifest.json"
SPLITS_PARQUET_NAME = "splits.parquet"


SplitPurposeType = Literal["train", "val", "test", "external_test", "excluded_no_logs"]


class SplitPurpose(str, Enum):
    TRAIN = "train"
    VAL = "val"
    TEST = "test"
    EXTERNAL_TEST = "external_test"
    EXCLUDED_NO_LOGS = "excluded_no_logs"


@dataclass(frozen=True)
class SplitAssignment:
    incident_id: str
    dataset_source: str
    scenario_id: str
    system_id: str
    stratum: str
    split_purpose: str
    has_logs: bool

SPLITS_TABLE_SCHEMA = pa.schema([
    ("incident_id", pa.string()),
    ("dataset_source", pa.string()),
    ("scenario_id", pa.string()),
    ("system_id", pa.string()),
    ("stratum", pa.string()),
    ("split_purpose", pa.string()),
    ("has_logs", pa.bool_()),
])

RE_REPETITION_SUFFIX = re.compile(r"_\d{1,2}$")


def extract_scenario_id(source_case_identifier: str) -> str:
    """Extract the base fault scenario identifier by stripping the repetition run suffix.

    Examples:
        're2ob_cartservice_cpu_1' -> 're2ob_cartservice_cpu'
        're3tt_ts-order-service_f1_3' -> 're3tt_ts-order-service_f1'
        'nezha_1661140434' -> 'nezha_1661140434'
    """
    if not source_case_identifier:
        return ""
    case_text = str(source_case_identifier).strip()
    if case_text.startswith("nezha_"):
        return case_text
    return RE_REPETITION_SUFFIX.sub("", case_text)


def compute_stratum_identifier(suite_name: str, system_identifier: str) -> str:
    """Construct a stratum string combining suite and system (e.g. 're2_ob')."""
    normalized_suite = str(suite_name).strip().lower()
    normalized_system = str(system_identifier).strip().lower()
    return f"{normalized_suite}_{normalized_system}"


def stratified_scenario_split(
    incidents_frame: pd.DataFrame,
    incidents_with_logs: Optional[Sequence[str] | set[str]] = None,
    train_ratio: float = 0.70,
    validation_ratio: float = 0.15,
    test_ratio: float = 0.15,
    random_seed: int = 42,
) -> pd.DataFrame:
    """Perform scenario-level stratified splitting on RCAEval incidents.

    Parameters:
        incidents_frame: DataFrame loaded from incidents.parquet.
        incidents_with_logs: Optional collection of incident IDs that have valid log events.
            If None, all incidents in incidents_frame are assumed eligible.
        train_ratio: Proportion of scenarios assigned to training (default 0.70).
        validation_ratio: Proportion of scenarios assigned to validation (default 0.15).
        test_ratio: Proportion of scenarios assigned to in-distribution test (default 0.15).
        random_seed: Seed for random number generator to ensure determinism.

    Returns:
        DataFrame matching SPLITS_TABLE_SCHEMA with one assignment per incident.
    """
    ratio_sum = train_ratio + validation_ratio + test_ratio
    if not np.isclose(ratio_sum, 1.0):
        raise ValueError(f"Split ratios must sum to 1.0, got {ratio_sum:.4f}")

    if incidents_with_logs is not None:
        logged_incident_ids = set(incidents_with_logs)
    else:
        logged_incident_ids = set(incidents_frame["incident_id"])

    working_frame = incidents_frame.copy()
    working_frame["has_logs"] = working_frame["incident_id"].isin(logged_incident_ids)
    working_frame["scenario_id"] = working_frame["source_case_id"].apply(extract_scenario_id)

    # Determine suite from prefix (e.g. 're2', 're3')
    working_frame["suite"] = working_frame["source_case_id"].str[:3].str.lower()
    working_frame["stratum"] = working_frame.apply(
        lambda row: compute_stratum_identifier(row["suite"], row["system_id"]),
        axis=1,
    )

    logged_scenarios_frame = (
        working_frame[working_frame["has_logs"]][["scenario_id", "stratum"]]
        .drop_duplicates()
        .sort_values("scenario_id")
        .reset_index(drop=True)
    )

    random_generator = np.random.default_rng(seed=random_seed)
    scenario_to_split_mapping: dict[str, SplitPurposeType] = {}

    # Allocate scenarios per stratum
    for stratum_name, stratum_group in logged_scenarios_frame.groupby("stratum"):
        scenario_list = stratum_group["scenario_id"].tolist()
        shuffled_scenarios = list(scenario_list)
        random_generator.shuffle(shuffled_scenarios)

        total_scenarios_in_stratum = len(shuffled_scenarios)
        allocated_train_count = int(round(total_scenarios_in_stratum * train_ratio))
        allocated_validation_count = int(round(total_scenarios_in_stratum * validation_ratio))

        # Guarantee representation in validation and test if stratum has at least 3 scenarios
        if total_scenarios_in_stratum >= 3:
            allocated_validation_count = max(1, allocated_validation_count)
            allocated_test_count = (
                total_scenarios_in_stratum - allocated_train_count - allocated_validation_count
            )
            if allocated_test_count < 1:
                allocated_train_count -= 1
                allocated_test_count = 1
        else:
            allocated_test_count = (
                total_scenarios_in_stratum - allocated_train_count - allocated_validation_count
            )

        training_scenarios = shuffled_scenarios[:allocated_train_count]
        validation_scenarios = shuffled_scenarios[
            allocated_train_count : allocated_train_count + allocated_validation_count
        ]
        test_scenarios = shuffled_scenarios[
            allocated_train_count + allocated_validation_count :
        ]

        for scenario_identifier in training_scenarios:
            scenario_to_split_mapping[scenario_identifier] = "train"
        for scenario_identifier in validation_scenarios:
            scenario_to_split_mapping[scenario_identifier] = "val"
        for scenario_identifier in test_scenarios:
            scenario_to_split_mapping[scenario_identifier] = "test"

    split_purpose_series: list[SplitPurposeType] = []
    for _, row in working_frame.iterrows():
        if not row["has_logs"]:
            split_purpose_series.append("excluded_no_logs")
        else:
            assigned_purpose = scenario_to_split_mapping.get(row["scenario_id"], "excluded_no_logs")
            split_purpose_series.append(assigned_purpose)

    working_frame["split_purpose"] = split_purpose_series

    columns_to_select = [
        "incident_id",
        "dataset_source",
        "scenario_id",
        "system_id",
        "stratum",
        "split_purpose",
        "has_logs",
    ]
    return working_frame[columns_to_select].reset_index(drop=True)


def create_nezha_splits(
    incidents_frame: pd.DataFrame,
    incidents_with_logs: Optional[Sequence[str] | set[str]] = None,
) -> pd.DataFrame:
    """Assign external_test purpose to all Nezha incidents.

    Nezha is solely used as an out-of-distribution external evaluation benchmark.
    """
    if incidents_with_logs is not None:
        logged_incident_ids = set(incidents_with_logs)
    else:
        logged_incident_ids = set(incidents_frame["incident_id"])

    working_frame = incidents_frame.copy()
    working_frame["has_logs"] = working_frame["incident_id"].isin(logged_incident_ids)
    working_frame["scenario_id"] = working_frame["source_case_id"]
    working_frame["stratum"] = working_frame["system_id"].str.lower()

    working_frame["split_purpose"] = working_frame["has_logs"].apply(
        lambda has_log_value: "external_test" if has_log_value else "excluded_no_logs"
    )

    columns_to_select = [
        "incident_id",
        "dataset_source",
        "scenario_id",
        "system_id",
        "stratum",
        "split_purpose",
        "has_logs",
    ]
    return working_frame[columns_to_select].reset_index(drop=True)


def verify_splits(
    splits_frame: pd.DataFrame,
    incidents_frame: pd.DataFrame,
) -> dict[str, Any]:
    """Verify integrity, coverage, and leakage-freedom of the generated splits.

    Hard checks:
      1. Incidents alignment: Every incident in incidents_frame exists in splits_frame.
      2. Incident uniqueness: incident_id is unique in splits_frame.
      3. Repetition leakage freedom: No scenario spans more than one of (train, val, test).
      4. Evaluated incidents have logs: Every incident in (train, val, test, external_test) has has_logs == True.
    """
    failures_list: list[str] = []

    raw_incident_ids = set(incidents_frame["incident_id"])
    split_incident_ids = set(splits_frame["incident_id"])

    if raw_incident_ids != split_incident_ids:
        missing_in_splits = raw_incident_ids - split_incident_ids
        extra_in_splits = split_incident_ids - raw_incident_ids
        failures_list.append(
            f"Incident ID mismatch: missing={len(missing_in_splits)}, extra={len(extra_in_splits)}"
        )

    if not splits_frame["incident_id"].is_unique:
        failures_list.append("Duplicate incident_id values discovered in splits_frame")

    # Check repetition leakage across evaluation partitions
    active_eval_splits = ("train", "val", "test")
    scenarios_per_split: dict[str, set[str]] = {}
    for split_purpose in active_eval_splits:
        matching_rows = splits_frame[splits_frame["split_purpose"] == split_purpose]
        scenarios_per_split[split_purpose] = set(matching_rows["scenario_id"])

    for index_a, split_a in enumerate(active_eval_splits):
        for split_b in active_eval_splits[index_a + 1 :]:
            shared_scenarios = scenarios_per_split[split_a] & scenarios_per_split[split_b]
            if shared_scenarios:
                failures_list.append(
                    f"Repetition leakage detected between '{split_a}' and '{split_b}': "
                    f"{len(shared_scenarios)} shared scenarios (e.g. {list(shared_scenarios)[:3]})"
                )

    eval_rows = splits_frame[splits_frame["split_purpose"].isin([*active_eval_splits, "external_test"])]
    invalid_log_rows = eval_rows[~eval_rows["has_logs"]]
    if len(invalid_log_rows) > 0:
        failures_list.append(
            f"Evaluation incidents lack logs: {len(invalid_log_rows)} rows marked without logs"
        )

    summary_dictionary: dict[str, Any] = {
        "total_incidents": len(splits_frame),
        "logged_incidents": int(splits_frame["has_logs"].sum()),
        "counts_by_split": splits_frame["split_purpose"].value_counts().to_dict(),
        "scenarios_by_split": (
            splits_frame[splits_frame["has_logs"]]
            .groupby("split_purpose")["scenario_id"]
            .nunique()
            .to_dict()
        ),
    }

    return {
        "passed": len(failures_list) == 0,
        "failures": failures_list,
        "summary": summary_dictionary,
    }


def save_splits(
    output_directory: Path,
    splits_frame: pd.DataFrame,
    settings_metadata: Mapping[str, Any],
) -> tuple[Path, Path]:
    """Persist splits.parquet and split_manifest.json under output_directory."""
    target_directory = Path(output_directory)
    target_directory.mkdir(parents=True, exist_ok=True)

    splits_parquet_path = target_directory / SPLITS_PARQUET_NAME
    arrow_table = pa.Table.from_pandas(splits_frame, schema=SPLITS_TABLE_SCHEMA, preserve_index=False)
    pq.write_table(arrow_table, splits_parquet_path)

    manifest_payload: dict[str, Any] = {
        "generated_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "settings": dict(settings_metadata),
        "counts_by_split": splits_frame["split_purpose"].value_counts().to_dict(),
        "scenarios_by_split": (
            splits_frame[splits_frame["has_logs"]]
            .groupby("split_purpose")["scenario_id"]
            .nunique()
            .to_dict()
        ),
        "counts_by_stratum_and_split": (
            splits_frame[splits_frame["has_logs"]]
            .groupby(["stratum", "split_purpose"])
            .size()
            .unstack(fill_value=0)
            .to_dict()
        ),
        "sha256": sha256_file(splits_parquet_path),
    }

    split_manifest_path = target_directory / SPLIT_MANIFEST_NAME
    split_manifest_path.write_text(json.dumps(manifest_payload, indent=2, ensure_ascii=False) + "\n")

    return splits_parquet_path, split_manifest_path


def load_splits(normalized_dataset_directory: Path | str) -> pd.DataFrame:
    """Load splits.parquet and verify its cryptographic SHA-256 integrity against split_manifest.json.

    Parameters:
        normalized_dataset_directory: Directory containing splits.parquet and split_manifest.json.

    Returns:
        DataFrame containing split assignments matching SPLITS_TABLE_SCHEMA.

    Raises:
        FileNotFoundError: If splits.parquet or split_manifest.json does not exist.
        ValueError: If the computed SHA-256 hash does not match the manifest checksum.
    """
    directory_path = Path(normalized_dataset_directory)
    splits_parquet_path = directory_path / SPLITS_PARQUET_NAME
    split_manifest_path = directory_path / SPLIT_MANIFEST_NAME

    if not splits_parquet_path.exists():
        raise FileNotFoundError(f"Splits table not found at {splits_parquet_path}")
    if not split_manifest_path.exists():
        raise FileNotFoundError(f"Split manifest not found at {split_manifest_path}")

    manifest_data = json.loads(split_manifest_path.read_text(encoding="utf-8"))
    expected_sha256 = manifest_data.get("sha256")
    actual_sha256 = sha256_file(splits_parquet_path)

    if expected_sha256 is not None and expected_sha256 != actual_sha256:
        raise ValueError(
            f"Integrity check failed for {splits_parquet_path}: "
            f"manifest expected {expected_sha256}, but computed {actual_sha256}"
        )

    return pd.read_parquet(splits_parquet_path)


def load_split_incidents(
    normalized_dataset_directory: Path | str,
    split_purpose: SplitPurposeType | SplitPurpose | str,
) -> list[str]:
    """Read splits.parquet with integrity verification and return incident_ids assigned to the purpose."""
    target_purpose_string = (
        split_purpose.value if isinstance(split_purpose, SplitPurpose) else str(split_purpose)
    )
    splits_frame = load_splits(normalized_dataset_directory)
    filtered_frame = splits_frame[splits_frame["split_purpose"] == target_purpose_string]
    return filtered_frame["incident_id"].tolist()
