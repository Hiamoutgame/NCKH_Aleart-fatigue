"""Time windowing utilities relative to incident fault injection timestamps.

Partitions log timestamps into 'before', 'after', and 'outside' windows based on
the known fault injection instant without persisting redundant timestamp copies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class WindowConfig:
    """Configuration for observation windows around the fault injection timestamp.

    Attributes:
        before_seconds: Maximum lookback duration before the fault in seconds.
            None indicates all available logs prior to the fault are included.
        after_seconds: Maximum lookahead duration after the fault in seconds.
            None indicates all available logs following the fault are included.
    """
    before_seconds: Optional[float] = None
    after_seconds: Optional[float] = None


def normalize_injection_timestamp(
    fault_injection_timestamp: pd.Timestamp | str | int | float,
) -> pd.Timestamp:
    """Normalize arbitrary timestamp inputs to UTC pd.Timestamp."""
    if isinstance(fault_injection_timestamp, (int, float)):
        # Treat numeric as Unix epoch seconds
        return pd.to_datetime(fault_injection_timestamp, unit="s", utc=True)
    normalized = pd.to_datetime(fault_injection_timestamp, utc=True)
    return normalized


def offset_seconds(
    timestamps_series: pd.Series,
    fault_injection_timestamp: pd.Timestamp | str | int | float,
) -> pd.Series:
    """Calculate signed elapsed seconds from the fault injection timestamp.

    Negative values represent events prior to fault injection; positive values
    represent events following fault injection. Missing or NaT timestamps evaluate to NaN.
    """
    normalized_injection_time = normalize_injection_timestamp(fault_injection_timestamp)
    utc_timestamps = pd.to_datetime(timestamps_series, utc=True)
    time_difference = utc_timestamps - normalized_injection_time
    return time_difference.dt.total_seconds()


def assign_windows(
    timestamps_series: pd.Series,
    fault_injection_timestamp: pd.Timestamp | str | int | float,
    window_configuration: WindowConfig,
) -> pd.Series:
    """Assign each timestamp to 'before', 'after', or 'outside' relative to the fault injection.

    Rules:
      - Exact fault injection timestamp (delta == 0) is categorized as 'after'.
      - Missing or NaT timestamps are categorized as 'outside'.
      - Events prior to injection (delta < 0) fall into 'before' if within before_seconds.
      - Events after injection (delta >= 0) fall into 'after' if within after_seconds.
      - Any event exceeding the configured limits is categorized as 'outside'.
    """
    signed_offsets_in_seconds = offset_seconds(timestamps_series, fault_injection_timestamp)
    
    window_labels = pd.Series(
        data="outside",
        index=timestamps_series.index,
        dtype=object,
    )

    valid_mask = signed_offsets_in_seconds.notna()
    before_condition = valid_mask & (signed_offsets_in_seconds < 0.0)
    after_condition = valid_mask & (signed_offsets_in_seconds >= 0.0)

    if window_configuration.before_seconds is not None:
        before_condition = before_condition & (
            signed_offsets_in_seconds >= -float(window_configuration.before_seconds)
        )

    if window_configuration.after_seconds is not None:
        after_condition = after_condition & (
            signed_offsets_in_seconds <= float(window_configuration.after_seconds)
        )

    window_labels.loc[before_condition] = "before"
    window_labels.loc[after_condition] = "after"

    return window_labels
