"""Regression checks for independent entrypoints and canonical output locations."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest

from src.shared.infrastructure.paths import DATASET_PATHS, REPOSITORY_ROOT


def run_cli(arguments, cwd):
    env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        arguments, cwd=cwd, env=env, capture_output=True, text=True, check=True,
    )


@pytest.mark.parametrize("entrypoint", [
    REPOSITORY_ROOT / "scripts/run_lemma_rca.py",
    REPOSITORY_ROOT / "scripts/run_datasets.py",
    REPOSITORY_ROOT / "Resource/cp1/src/main_RCAEval.py",
    REPOSITORY_ROOT / "Resource/cp1/src/main_LEMMA_RCA.py",
    REPOSITORY_ROOT / "Resource/cp1/src/main_Nezha.py",
])
def test_entrypoints_work_without_pythonpath_from_other_directory(tmp_path, entrypoint):
    result = run_cli([sys.executable, str(entrypoint), "--help"], tmp_path)
    assert "usage:" in result.stdout


def test_shell_wrappers_work_from_other_directory(tmp_path):
    result = run_cli(["bash", str(REPOSITORY_ROOT / "run_datasets.sh"), "list"], tmp_path)
    assert json.loads(result.stdout) == {slug: str(path) for slug, path in DATASET_PATHS.items()}
    result = run_cli(["bash", str(REPOSITORY_ROOT / "run_lemma_rca.sh"), "--help"], tmp_path)
    assert "logs" in result.stdout


def test_custom_input_and_output_roots_are_respected(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    case = raw / "sample_case"
    case.mkdir()
    pd.DataFrame([{
        "case": "sample_case", "system": "ss", "has_logs": True,
        "fault": "cpu", "root_cause_service": "carts",
        "time_start": 1700000000, "time_end": 1700000060,
        "inject_time": 1700000030,
    }]).to_parquet(raw / "cases.parquet", index=False)
    message = "2023-11-14 22:13:20.000 WARN carts retry 123"
    pd.DataFrame([{
        "timestamp": 1700000000, "container_name": "carts", "message": message,
    }]).to_parquet(case / "logs.parquet", index=False)
    output = tmp_path / "output"
    script = REPOSITORY_ROOT / "scripts/run_datasets.py"
    result = run_cli([
        sys.executable, str(script), "normalize", "rcaeval",
        "--data-root", str(raw), "--output-root", str(output),
    ], tmp_path)
    assert json.loads(result.stdout)["rcaeval"]["table_rows"] == {
        "incidents.parquet": 1, "ground_truth.parquet": 1, "log_events.parquet": 1,
    }
    logs = pd.read_parquet(output / "rcaeval/log_events.parquet")
    assert logs.loc[0, "raw_message"] == message
    assert logs.loc[0, "source_file"] == "sample_case/logs.parquet"
    assert logs.loc[0, "incident_id"] == "rcaeval_sample_case"


def test_export_module_is_safe_to_import(tmp_path):
    script = REPOSITORY_ROOT / "scripts/export_all_normalized.py"
    code = (
        "import runpy, sys; "
        f"sys.path.insert(0, {str(script.parent)!r}); "
        f"runpy.run_path({str(script)!r}, run_name='import_check')"
    )
    result = run_cli([sys.executable, "-c", code], tmp_path)
    assert result.stdout == ""
    assert list(tmp_path.iterdir()) == []
