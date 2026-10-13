"""Pure-ish RCAEval analyses that write only through the reporting layer."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from .dataset_io import list_case_log_paths, load_case_logs
from .normalization import normalize_message
from .severity import DEBUG_RE, ERROR_RE, INFO_RE, WARN_RE


CASE_RE = re.compile(r"^(re\d)(ob|ss|tt)_", re.IGNORECASE)


def classify_case_id(case_id: str) -> dict[str, str]:
    match = CASE_RE.match(case_id)
    if not match:
        return {"suite": "OTHER", "system": "OTHER", "sys": "OTHER", "sys2": "OTHER"}
    suite = match.group(1).upper()
    system = match.group(2).upper()
    return {"suite": suite, "system": system, "sys": f"{suite}-{system}", "sys2": system}


def is_normal_window(timestamp: int | float, inject_time: int | float) -> bool:
    """The normal window is [time_start, inject_time)."""
    return timestamp < inject_time


def scan_warnings(rcaeval_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, int | str]] = []
    for case_id, log_path in list_case_log_paths(rcaeval_dir).items():
        frame = load_case_logs(log_path, columns=["timestamp", "container_name", "message"])
        messages = frame["message"].astype("string")
        row: dict[str, int | str] = {
            "case": case_id,
            **classify_case_id(case_id),
            "n_logs": len(frame),
            "n_containers": int(frame["container_name"].nunique()),
            "n_warn": int(messages.str.contains(WARN_RE, regex=True, na=False).sum()),
            "n_error": int(messages.str.contains(ERROR_RE, regex=True, na=False).sum()),
            "n_info": int(messages.str.contains(INFO_RE, regex=True, na=False).sum()),
            "n_debug": int(messages.str.contains(DEBUG_RE, regex=True, na=False).sum()),
        }
        rows.append(row)
    columns = ["case", "suite", "system", "sys", "sys2", "n_logs", "n_containers", "n_warn", "n_error", "n_info", "n_debug"]
    return pd.DataFrame(rows, columns=columns).sort_values("case").reset_index(drop=True)


def timing_table(
    rcaeval_dir: Path,
    cases: pd.DataFrame,
    warning_table: pd.DataFrame,
    limit: int = 10,
) -> pd.DataFrame:
    index = cases.set_index("case")
    targets = warning_table.loc[warning_table["sys2"] == "SS"].nlargest(limit, "n_warn")["case"].tolist()
    targets.extend(["re2ss_carts_cpu_1", "re2tt_ts-auth-service_cpu_2", "re2ob_checkoutservice_cpu_1"])

    rows: list[dict[str, int | float | str]] = []
    log_paths = list_case_log_paths(rcaeval_dir)
    for case_id in dict.fromkeys(targets):
        if case_id not in index.index or case_id not in log_paths:
            continue
        meta = index.loc[case_id]
        frame = load_case_logs(log_paths[case_id], columns=["timestamp", "container_name", "message"])
        warnings = frame[frame["message"].astype("string").str.contains(WARN_RE, regex=True, na=False)]
        inject_time = int(meta["inject_time"])
        normal = int(warnings["timestamp"].map(lambda timestamp: is_normal_window(timestamp, inject_time)).sum())
        rows.append({
            "case": case_id,
            "fault": str(meta.get("fault", "")),
            "root_cause_service": str(meta.get("root_cause_service", "")),
            "n_logs": len(frame),
            "n_warn": len(warnings),
            "warn_normal": normal,
            "warn_faulty": len(warnings) - normal,
            "pct_warn_normal": round(100 * normal / max(len(warnings), 1), 1),
            "n_containers_warn": int(warnings["container_name"].nunique()),
        })
    return pd.DataFrame(rows)


def verification_table(
    rcaeval_dir: Path,
    cases: pd.DataFrame,
    warning_table: pd.DataFrame,
    limit: int = 6,
) -> pd.DataFrame:
    index = cases.set_index("case")
    log_paths = list_case_log_paths(rcaeval_dir)
    probes = warning_table.loc[warning_table["sys2"] == "SS"].nlargest(limit, "n_warn")["case"].tolist()
    rows: list[dict[str, int | float | str]] = []
    for case_id in probes:
        if case_id not in index.index or case_id not in log_paths:
            continue
        meta = index.loc[case_id]
        frame = load_case_logs(log_paths[case_id], columns=["timestamp", "container_name", "message"])
        warnings = frame[frame["message"].astype("string").str.contains(WARN_RE, regex=True, na=False)].copy()
        if warnings.empty:
            continue
        warnings["normalized_message"] = warnings["message"].map(normalize_message)
        inject_time = int(meta["inject_time"])
        normal = int(warnings["timestamp"].map(lambda timestamp: is_normal_window(timestamp, inject_time)).sum())
        rows.append({
            "case": case_id,
            "fault": str(meta.get("fault", "")),
            "root_cause_service": str(meta.get("root_cause_service", "")),
            "n_warn": len(warnings),
            "n_templates_raw": int(warnings["message"].nunique()),
            "n_templates_normalized": int(warnings["normalized_message"].nunique()),
            "warn_normal": normal,
            "warn_faulty": len(warnings) - normal,
            "n_containers_warn": int(warnings["container_name"].nunique()),
            "n_containers_case": int(frame["container_name"].nunique()),
        })
    return pd.DataFrame(rows)


def summary_lines(warning_table: pd.DataFrame) -> list[str]:
    lines = ["RCAEval warning scan", f"cases_with_logs: {len(warning_table)}"]
    if warning_table.empty:
        return lines
    lines.extend([
        f"total_logs: {int(warning_table['n_logs'].sum())}",
        f"total_warn: {int(warning_table['n_warn'].sum())}",
        f"cases_warn_gt_zero: {int((warning_table['n_warn'] > 0).sum())}",
        "",
        "system breakdown:",
        warning_table.groupby("sys2")[["n_logs", "n_warn", "n_error"]].sum().to_string(),
    ])
    return lines
