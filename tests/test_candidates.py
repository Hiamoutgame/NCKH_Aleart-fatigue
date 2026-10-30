"""Unit tests for candidate inventory construction and isolation from test labels."""

from __future__ import annotations

import inspect
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.ranking.candidates import (
    load_candidates,
    observed_candidates,
    save_candidates,
    train_inventory,
)


def test_train_inventory_function_signature_has_no_labels_or_ground_truth():
    """Verify train_inventory signature has no parameter related to labels or ground truth."""
    sig = inspect.signature(train_inventory)
    parameter_names = set(sig.parameters.keys())
    forbidden_names = {"ground_truth", "label", "raw_label", "fault_type", "incident"}
    assert parameter_names.isdisjoint(forbidden_names)


def test_train_inventory_extracts_only_train_services(tmp_path: Path):
    """Verify that only services appearing in training incidents are included in inventory."""
    groups_data = pd.DataFrame([
        # Train incident 1 for ob
        {"incident_id": "inc_train_1", "service_id": "frontend", "n_logs": 10},
        {"incident_id": "inc_train_1", "service_id": "cartservice", "n_logs": 5},
        # Train incident 2 for ob
        {"incident_id": "inc_train_2", "service_id": "adservice", "n_logs": 20},
        {"incident_id": "inc_train_2", "service_id": None, "n_logs": 2},  # null service ignored
        # Val incident for ob (contains a service NOT in train)
        {"incident_id": "inc_val_1", "service_id": "paymentservice", "n_logs": 50},
        # Test incident for ob (contains a service NOT in train)
        {"incident_id": "inc_test_1", "service_id": "emailservice", "n_logs": 50},
        # Train incident for ss
        {"incident_id": "inc_train_ss", "service_id": "orders", "n_logs": 15},
    ])

    groups_parquet_path = tmp_path / "groups.parquet"
    pq.write_table(pa.Table.from_pandas(groups_data), groups_parquet_path)

    splits_data = pd.DataFrame([
        {"incident_id": "inc_train_1", "system_id": "ob", "split_purpose": "train"},
        {"incident_id": "inc_train_2", "system_id": "ob", "split_purpose": "train"},
        {"incident_id": "inc_val_1", "system_id": "ob", "split_purpose": "val"},
        {"incident_id": "inc_test_1", "system_id": "ob", "split_purpose": "test"},
        {"incident_id": "inc_train_ss", "system_id": "ss", "split_purpose": "train"},
    ])

    inventory = train_inventory(groups_parquet_path, splits_data)

    # ob must only contain train services, alphabetically sorted
    assert inventory["ob"] == ["adservice", "cartservice", "frontend"]
    # paymentservice and emailservice must NOT be leaked into ob inventory
    assert "paymentservice" not in inventory["ob"]
    assert "emailservice" not in inventory["ob"]

    # ss must only contain train services
    assert inventory["ss"] == ["orders"]


def test_save_and_load_candidates_roundtrip(tmp_path: Path):
    """Verify saving and reloading candidate inventory from JSON."""
    inventory = {
        "ob": ["adservice", "cartservice", "frontend"],
        "ss": ["catalogue", "orders", "user"],
    }
    json_target_path = tmp_path / "candidates.json"
    save_candidates(json_target_path, inventory, metadata={"dataset": "rcaeval"})

    loaded_inventory = load_candidates(json_target_path)
    assert loaded_inventory == inventory


def test_observed_candidates_from_dataframe():
    """Verify observed_candidates filters active services with n_logs > 0."""
    groups_data = pd.DataFrame([
        {"service_id": "frontend", "n_logs": 10},
        {"service_id": "cartservice", "n_logs": 0},
        {"service_id": "adservice", "n_logs": 5},
        {"service_id": None, "n_logs": 12},
    ])
    candidates = observed_candidates(groups_data)
    assert candidates == ["adservice", "frontend"]
