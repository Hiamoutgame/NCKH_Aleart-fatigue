"""Unit tests for time windowing relative to incident fault injection."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.windowing import WindowConfig, assign_windows, offset_seconds


def test_assign_windows_exact_injection_and_partitions():
    """Verify exact injection time is categorized as 'after', earlier as 'before', later as 'after'."""
    injection_time = pd.Timestamp("2023-11-14 22:10:00", tz="UTC")
    timestamps = pd.Series([
        injection_time - pd.Timedelta(120.0, unit="s"),
        injection_time - pd.Timedelta(1.0, unit="s"),
        injection_time,
        injection_time + pd.Timedelta(1.0, unit="s"),
        injection_time + pd.Timedelta(600.0, unit="s"),
        pd.NaT,
    ])

    unbounded_config = WindowConfig()
    assigned_labels = assign_windows(timestamps, injection_time, unbounded_config)

    assert assigned_labels.tolist() == [
        "before",
        "before",
        "after",
        "after",
        "after",
        "outside",
    ]


def test_assign_windows_with_duration_bounds():
    """Verify events outside before_seconds and after_seconds limits are labeled 'outside'."""
    injection_time = pd.Timestamp("2023-11-14 22:10:00", tz="UTC")
    timestamps = pd.Series([
        injection_time - pd.Timedelta(300.0, unit="s"),  # beyond before 60s -> outside
        injection_time - pd.Timedelta(60.0, unit="s"),   # exact before limit -> before
        injection_time - pd.Timedelta(30.0, unit="s"),   # within before -> before
        injection_time,                              # exact injection -> after
        injection_time + pd.Timedelta(120.0, unit="s"),  # within after -> after
        injection_time + pd.Timedelta(180.0, unit="s"),  # exact after limit -> after
        injection_time + pd.Timedelta(200.0, unit="s"),  # beyond after 180s -> outside
    ])

    bounded_config = WindowConfig(before_seconds=60.0, after_seconds=180.0)
    assigned_labels = assign_windows(timestamps, injection_time, bounded_config)

    assert assigned_labels.tolist() == [
        "outside",
        "before",
        "before",
        "after",
        "after",
        "after",
        "outside",
    ]


def test_offset_seconds_calculation():
    """Verify signed seconds difference calculation and NaN propagation."""
    injection_time = pd.Timestamp("2023-11-14 22:00:00", tz="UTC")
    timestamps = pd.Series([
        injection_time - pd.Timedelta(45.5, unit="s"),
        injection_time,
        injection_time + pd.Timedelta(120.25, unit="s"),
        pd.NaT,
    ])

    offsets = offset_seconds(timestamps, injection_time)
    assert offsets.iloc[0] == pytest.approx(-45.5)
    assert offsets.iloc[1] == pytest.approx(0.0)
    assert offsets.iloc[2] == pytest.approx(120.25)
    assert np.isnan(offsets.iloc[3])


def test_assign_windows_handles_numeric_epoch_and_string_injection():
    """Verify compatibility with numeric epoch and string inputs for injection time."""
    epoch_injection = 1700000000
    timestamps = pd.to_datetime([1699999900, 1700000000, 1700000100], unit="s", utc=True)

    labels_from_numeric = assign_windows(pd.Series(timestamps), epoch_injection, WindowConfig())
    assert labels_from_numeric.tolist() == ["before", "after", "after"]

    string_injection = "2023-11-14 22:13:20+00:00"
    injection_as_ts = pd.Timestamp(string_injection)
    timestamps_for_string = pd.Series([
        injection_as_ts - pd.Timedelta(10.0, unit="s"),
        injection_as_ts + pd.Timedelta(10.0, unit="s"),
    ])
    labels_from_string = assign_windows(timestamps_for_string, string_injection, WindowConfig())
    assert labels_from_string.tolist() == ["before", "after"]


def test_incident_with_no_logs_before_fault():
    """Verify that incidents with zero before-fault logs produce valid 'after' and 'outside' labels."""
    injection_time = pd.Timestamp("2023-11-14 22:00:00", tz="UTC")
    only_after_timestamps = pd.Series([
        injection_time + pd.Timedelta(10.0, unit="s"),
        injection_time + pd.Timedelta(20.0, unit="s"),
    ])

    assigned_labels = assign_windows(only_after_timestamps, injection_time, WindowConfig())
    assert (assigned_labels == "after").all()
    assert "before" not in assigned_labels.values
