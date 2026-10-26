"""End-to-end normalize + verify on small synthetic raw folders."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import pytest

from src.datasets.nezha import NezhaAdapter
from src.datasets.rcaeval import RCAEvalAdapter
from src.shared.application.verify_normalized import verify_normalized
from src.shared.infrastructure.log_table import LOG_EVENTS_SCHEMA


# ----------------------------------------------------------------------
# RCAEval
# ----------------------------------------------------------------------
@pytest.fixture
def rcaeval_raw(tmp_path: Path) -> Path:
    raw = tmp_path / "rcaeval"
    raw.mkdir()
    cases = []
    logs = {
        "re2ob_cartservice_cpu_1": [
            (1700000000, "cartservice", "request started"),
            (1700000001, "cartservice", "request complete"),
            (1700000002, None, "orphan line without container"),
            (1700000003, "frontend", None),
        ],
        "re2tt_ts-order-service_cpu_1": [
            (1700000100, "ts-order-service", "INFO 1 --- [io-8080-exec-1] o.OrderController : Order 12 created"),
            (1700000101, "ts-order-service", "INFO 1 --- [io-8080-exec-2] o.OrderController : Order 13 created"),
            (1700000102, "ts-route-service", "ts=2024-01-18T16:30:59Z caller=x.go:36 took=2.003432ms"),
        ],
    }
    for case, rows in logs.items():
        (raw / case).mkdir()
        pd.DataFrame(rows, columns=["timestamp", "container_name", "message"]).astype(
            {"timestamp": "Int64", "container_name": "string", "message": "string"}
        ).to_parquet(raw / case / "logs.parquet", index=False)
    for case in [*logs, "re1ob_cartservice_cpu_1"]:
        system = case[3:5]
        cases.append({
            "case": case, "system": system, "has_logs": case in logs, "fault": "cpu",
            "root_cause_service": case.split("_")[1], "time_start": 1699999000,
            "time_end": 1700001000, "inject_time": 1700000050,
        })
    pd.DataFrame(cases).to_parquet(raw / "cases.parquet", index=False)
    return raw


def test_rcaeval_normalize_all_cases_and_verify(rcaeval_raw: Path, tmp_path: Path):
    out = tmp_path / "out"
    adapter = RCAEvalAdapter(rcaeval_raw)
    result = adapter.normalize(out)
    assert result["log_events_count"] == 7
    assert len(result["cases_normalized"]) == 2

    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["settings"]["drain_config"] == {"depth": 4, "st": 0.4, "max_child": 100}
    assert manifest["settings"]["max_cases"] is None
    assert all(len(item["sha256"]) == 64 for item in manifest["inputs"])

    log_file = pq.ParquetFile(out / "log_events.parquet")
    assert log_file.num_row_groups == 2  # one per incident
    logs = log_file.read().to_pandas()
    orphan = logs[logs["raw_message"] == "orphan line without container"].iloc[0]
    assert orphan["service_id"] is None
    empty = logs[logs["raw_message"] == ""].iloc[0]
    assert empty["template_id"] is None and empty["drain_template_id"] is None
    orders = logs[logs["service_id"] == "ts-order-service"]
    assert orders["drain_template"].nunique() == 1
    assert orders["drain_template"].iloc[0] == "INFO o.OrderController : Order <N> created"

    report = verify_normalized(RCAEvalAdapter(rcaeval_raw), out)
    assert report["passed"], [c for c in report["checks"] if not c["passed"]]
    assert report["summary"]["log_events"] == 7


def test_verify_catches_a_dropped_row(rcaeval_raw: Path, tmp_path: Path):
    out = tmp_path / "out"
    RCAEvalAdapter(rcaeval_raw).normalize(out)
    path = out / "log_events.parquet"
    log_file = pq.ParquetFile(path)
    groups = [log_file.read_row_group(i) for i in range(log_file.num_row_groups)]
    writer = pq.ParquetWriter(path.with_suffix(".tmp"), LOG_EVENTS_SCHEMA)
    for index, table in enumerate(groups):
        writer.write_table(table.slice(1) if index == 0 else table)  # drop one row of the first incident
    writer.close()
    path.with_suffix(".tmp").replace(path)

    report = verify_normalized(RCAEvalAdapter(rcaeval_raw), out)
    failed = {check["check"] for check in report["checks"] if not check["passed"]}
    assert not report["passed"]
    assert {"row count matches raw", "raw rows kept exactly once per file"} <= failed


def test_rcaeval_load_logs_matches_frame(rcaeval_raw: Path):
    adapter = RCAEvalAdapter(rcaeval_raw)
    frame = adapter.load_log_frame("rcaeval_re2ob_cartservice_cpu_1")
    events = adapter.load_logs("rcaeval_re2ob_cartservice_cpu_1")
    assert [event.log_id for event in events] == list(frame["log_id"])
    assert [event.drain_template_id for event in events] == [
        None if pd.isna(value) else value for value in frame["drain_template_id"]
    ]
    assert events[0].timestamp_utc == datetime(2023, 11, 14, 22, 13, 20, tzinfo=timezone.utc)


# ----------------------------------------------------------------------
# Nezha
# ----------------------------------------------------------------------
HEADER = ["Timestamp", "TimeUnixNano", "Node", "PodName", "Container", "TraceID", "SpanID", "Log"]


def utc(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


def log_row(when: str, pod: str, message: str, time_ns: str | None = None) -> list[str]:
    moment = utc(when)
    inner = json.dumps({"message": f"TraceID: abc SpanID: def {message}", "severity": "info"}) + "\n"
    payload = json.dumps({"log": inner, "stream": "stdout"})
    nanos = str(int(moment.timestamp()) * 10**9) if time_ns is None else time_ns
    return [moment.isoformat(), nanos, "node", pod, "server", "abc", "def", payload]


def write_csv(path: Path, rows: list[list[str]], broken_line: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADER)
        writer.writerows(rows)
        if broken_line is not None:
            handle.write(broken_line + "\n")


def fault(when: str, epoch: int, pod: str, kind: str = "cpu_contention") -> dict[str, str]:
    return {"inject_time": when, "inject_timestamp": str(epoch), "inject_pod": pod, "inject_type": kind}


@pytest.fixture
def nezha_raw(tmp_path: Path) -> Path:
    raw = tmp_path / "nezha"
    a = fault("2022-08-22 03:53:54", 1661140434, "cartservice-579f59597d-wc2lz")
    b = fault("2022-08-22 03:59:00", 1661140740, "frontend-579b9bff58-t2dbm")
    # 2023-01-29: the epoch is 8 hours early and shared by two different injections.
    c = fault("2023-01-29 08:43:04", 1674953044, "ts-travel-service-64469b5b48-25zj6", "return")
    d = fault("2023-01-29 09:12:56", 1674953044, "ts-basic-service-5dc8d4f9fd-46997", "return")
    for date, faults in {"2022-08-22": {"03": [a, b, dict(a)]}, "2023-01-29": {"08": [c], "09": [d]}}.items():
        (raw / date).mkdir(parents=True)
        (raw / date / f"{date}-fault_list.json").write_text(json.dumps(faults))
    (raw / "fault_list.json").write_text(json.dumps({"03": [a]}))  # root sample copy

    pod = "cartservice-579f59597d-wc2lz"
    write_csv(raw / "2022-08-22/log/03_50_log.csv", [log_row("2022-08-22 03:49:00", pod, "before every window")])
    write_csv(raw / "2022-08-22/log/03_53_log.csv", [
        log_row("2022-08-22 03:54:30", pod, "request complete"),
        log_row("2022-08-22 03:53:00", pod, "request started"),
    ])
    write_csv(raw / "2022-08-22/log/03_55_log.csv", [log_row("2022-08-22 03:55:10", pod, "request started")])
    write_csv(raw / "2022-08-22/log/03_58_log.csv", [log_row("2022-08-22 03:58:00", "frontend-579b9bff58-t2dbm", "serving page")])
    write_csv(raw / "03_53_log.csv", [log_row("2022-08-22 03:53:00", pod, "request started")])  # root sample copy
    write_csv(
        raw / "2023-01-29/log/08_43_log.csv",
        [
            log_row("2023-01-29 08:42:30", "ts-travel-service-64469b5b48-25zj6", "Get route"),
            log_row("2023-01-29 08:42:31", "ts-travel-service-64469b5b48-25zj6", "no time", time_ns=""),
        ],
        broken_line='2023-01-29T08:42:32Z,1674981752000000000,node,ts-user-service-1-2,server,a,b,{"log":"x","t":1}',
    )
    write_csv(raw / "2023-01-29/log/09_13_log.csv", [log_row("2023-01-29 09:13:00", "ts-basic-service-5dc8d4f9fd-46997", "Query")])
    return raw


def test_nezha_incidents_ground_truth_and_systems(nezha_raw: Path):
    adapter = NezhaAdapter(nezha_raw)
    incidents = {incident.incident_id: incident for incident in adapter.load_incidents()}
    assert adapter.duplicate_faults == 1
    assert sorted(incidents) == ["nezha_1661140434", "nezha_1661140740", "nezha_1674981784", "nezha_1674983576"]
    assert [incidents[i].system_id for i in sorted(incidents)] == ["ob", "ob", "tt", "tt"]
    assert incidents["nezha_1674981784"].inject_time == utc("2023-01-29 08:43:04")
    truths = {truth.incident_id: truth.canonical_target for truth in adapter.load_ground_truth()}
    assert truths["nezha_1674983576"] == "ts-basic-service"


def test_nezha_conflicting_entries_are_an_error(nezha_raw: Path):
    path = nezha_raw / "2023-01-29/2023-01-29-fault_list.json"
    faults = json.loads(path.read_text())
    faults["08"].append(dict(faults["08"][0], inject_pod="ts-order-service-1-2"))
    path.write_text(json.dumps(faults))
    with pytest.raises(ValueError):
        NezhaAdapter(nezha_raw).load_incidents()


def test_nezha_normalize_every_incident_and_verify(nezha_raw: Path, tmp_path: Path):
    out = tmp_path / "out"
    result = NezhaAdapter(nezha_raw).normalize(out)
    assert result["incidents_count"] == 4
    assert result["log_events_count"] == 3 + 1 + 1 + 1

    logs = pd.read_parquet(out / "log_events.parquet")
    assert set(logs.groupby("incident_id").size()) == {3, 1}
    assert not logs["source_file"].str.endswith("nezha/03_53_log.csv").any()  # root copy is never read
    first = logs[logs["incident_id"] == "nezha_1661140434"]
    assert list(first["raw_message"]) == [
        "TraceID: abc SpanID: def request started",
        "TraceID: abc SpanID: def request complete",
        "TraceID: abc SpanID: def request started",
    ]  # sorted by time across files
    assert first["drain_template"].iloc[0] == "request started"
    assert first["raw_record_ref"].iloc[0].endswith("2022-08-22/log/03_53_log.csv#row_1")

    manifest = json.loads((out / "manifest.json").read_text())
    assert [row["source_row_id"] for row in manifest["outputs"]["rejected_rows_seen"]] == ["2"]
    assert manifest["outputs"]["epoch_mismatch_seconds"]["nezha_1674981784"] == -28740  # 7 h 59 min

    report = verify_normalized(NezhaAdapter(nezha_raw), out)
    assert report["passed"], [c for c in report["checks"] if not c["passed"]]
    raw_summary = report["summary"]["raw"]
    assert raw_summary == {
        "raw_rows": 9, "rejected_rows": 1, "rows_without_timestamp": 1, "rows_outside_every_window": 2,
    }
