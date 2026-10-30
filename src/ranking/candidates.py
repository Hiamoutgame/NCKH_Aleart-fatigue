"""Candidate root-cause service inventory construction and retrieval.

In accordance with the evaluation protocol:
  - RCAEval: Candidate services are strictly derived from training set observations
    (train_inventory) per system family, ensuring zero test label leakage.
  - Nezha: Observed services in the incident are used as candidates (observed_candidates).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

import pandas as pd
import pyarrow.parquet as pq

from src.evaluation.split import load_splits


def train_inventory(
    groups_parquet_path: Path | str,
    splits_dataframe_or_path: pd.DataFrame | Path | str,
) -> dict[str, list[str]]:
    """Extract distinct services per system family observed across training incidents only.

    Parameters:
        groups_parquet_path: Path to groups.parquet containing service_id and incident_id columns.
        splits_dataframe_or_path: Either a DataFrame or path to splits.parquet containing split_purpose and system_id.

    Returns:
        Dictionary mapping system_id (e.g. 'ob', 'ss', 'tt') to an alphabetically sorted list of candidate services.
    """
    if isinstance(splits_dataframe_or_path, (str, Path)):
        splits_path = Path(splits_dataframe_or_path)
        if splits_path.is_file():
            # If direct file path, pass its parent to load_splits for hash verification
            splits_frame = load_splits(splits_path.parent)
        else:
            splits_frame = load_splits(splits_path)
    else:
        splits_frame = splits_dataframe_or_path.copy()

    training_incidents_frame = splits_frame[splits_frame["split_purpose"] == "train"]
    if training_incidents_frame.empty:
        return {}

    train_incident_to_system = dict(
        zip(training_incidents_frame["incident_id"], training_incidents_frame["system_id"])
    )
    train_incident_ids_set = set(train_incident_to_system.keys())

    groups_path = Path(groups_parquet_path)
    groups_table = pq.read_table(
        groups_path,
        columns=["incident_id", "service_id"],
    )
    groups_frame = groups_table.to_pandas()

    train_groups = groups_frame[groups_frame["incident_id"].isin(train_incident_ids_set)]

    system_to_services_set: dict[str, set[str]] = {}
    # Initialize known systems
    for system_identifier in training_incidents_frame["system_id"].unique():
        system_to_services_set[str(system_identifier).lower()] = set()

    for _, row in train_groups.iterrows():
        raw_service_id = row["service_id"]
        if pd.isna(raw_service_id):
            continue
        service_identifier = str(raw_service_id).strip()
        if not service_identifier:
            continue

        incident_identifier = row["incident_id"]
        system_identifier = str(train_incident_to_system[incident_identifier]).lower()
        system_to_services_set[system_identifier].add(service_identifier)

    system_candidates_inventory: dict[str, list[str]] = {
        system_identifier: sorted(services_set)
        for system_identifier, services_set in sorted(system_to_services_set.items())
    }
    return system_candidates_inventory


def observed_candidates(incident_view_or_groups: Any) -> list[str]:
    """Extract all distinct non-null services that have >= 1 log event in the incident."""
    if hasattr(incident_view_or_groups, "services"):
        # IncidentView object
        candidate_services = [
            service_view.service_id
            for service_view in incident_view_or_groups.services
            if service_view.service_id and (service_view.n_before + service_view.n_after > 0)
        ]
        return sorted(set(candidate_services))

    if isinstance(incident_view_or_groups, pd.DataFrame):
        groups_frame = incident_view_or_groups
        active_services = groups_frame[
            groups_frame["service_id"].notna() & (groups_frame["n_logs"] > 0)
        ]["service_id"].astype(str).unique()
        return sorted(active_services)

    raise TypeError(
        f"Expected IncidentView or DataFrame, got {type(incident_view_or_groups)}"
    )


def save_candidates(
    output_json_path: Path | str,
    candidates_inventory: Mapping[str, Sequence[str]],
    metadata: Optional[Mapping[str, Any]] = None,
) -> Path:
    """Persist candidate inventory to a JSON file."""
    target_path = Path(output_json_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {
        "metadata": dict(metadata) if metadata is not None else {},
        "candidates_by_system": {
            system_id: list(services) for system_id, services in candidates_inventory.items()
        },
    }
    target_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return target_path


def load_candidates(candidates_json_path: Path | str) -> dict[str, list[str]]:
    """Load candidate inventory from a saved JSON file."""
    target_path = Path(candidates_json_path)
    if not target_path.exists():
        raise FileNotFoundError(f"Candidates file not found at {target_path}")
    payload = json.loads(target_path.read_text(encoding="utf-8"))
    candidates_by_system = payload.get("candidates_by_system", {})
    return {str(k): list(v) for k, v in candidates_by_system.items()}
