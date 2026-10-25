"""Tests for LEMMA-RCA dataset module."""

import pytest
from src.datasets.lemma_rca.application.use_cases import (
    describe_lemma_use_case,
    export_lemma_logs_use_case,
    fetch_lemma_use_case,
    get_lemma_incident_use_case,
    list_lemma_incidents_use_case,
)
from src.datasets.lemma_rca.domain.models import LemmaIncident, LemmaLogRecord
from src.datasets.lemma_rca.infrastructure.downloader import LemmaDownloader
from src.datasets.lemma_rca.infrastructure.loader import LemmaLoader


def test_lemma_log_record_model():
    rec = LemmaLogRecord(
        record_id="rec-001",
        timestamp_str="2021-05-15T06:18:05Z",
        service="productpage",
        level="INFO",
        message="GET /details/0 200",
        pod_name="productpage-v1-abc",
        container_name="productpage",
        namespace="book-info",
        host="ocp4-compute-1",
        log_type="app",
    )
    assert rec.service == "productpage"
    assert rec.level == "INFO"
    assert rec.log_type == "app"


def test_extract_level_from_message():
    assert LemmaLoader.extract_level_from_message('DEBUG:urllib3.connectionpool:GET /') == "DEBUG"
    assert LemmaLoader.extract_level_from_message('INFO:werkzeug:127.0.0.1') == "INFO"
    assert LemmaLoader.extract_level_from_message('2021/05/15 06:18:01 instana: ERROR: Failed sending') == "ERROR"
    assert LemmaLoader.extract_level_from_message('WARN [carts] ConfigurationClassPostProcessor') == "WARN"
    assert LemmaLoader.extract_level_from_message('I0516 23:14:50.357205 1926 factory.go') == "INFO"
    assert LemmaLoader.extract_level_from_message('E0516 23:14:50 kubelet error') == "ERROR"
    assert LemmaLoader.extract_level_from_message('plain message without level') == "INFO"


def test_parse_elasticsearch_hit():
    mock_hit = {
        "_id": "hit-123",
        "_index": "app-000174",
        "_source": {
            "@timestamp": "2021-05-15T06:18:05.069451+00:00",
            "level": "unknown",
            "message": 'DEBUG:urllib3.connectionpool:http://details:9080 "GET /details/0 HTTP/1.1" 200 178',
            "kubernetes": {
                "container_name": "productpage",
                "pod_name": "productpage-v1-6687ddf68f-pbdzm",
                "namespace_name": "book-info",
                "host": "ocp4-compute-1",
            },
            "hostname": "ocp4-compute-1",
        },
    }
    rec = LemmaLoader.parse_elasticsearch_hit(mock_hit, file_hint="app-000174")
    assert rec.record_id == "hit-123"
    assert rec.service == "productpage"
    assert rec.level == "DEBUG"
    assert rec.pod_name == "productpage-v1-6687ddf68f-pbdzm"
    assert rec.host == "ocp4-compute-1"
    assert rec.log_type == "app"


def test_download_plan_sample():
    downloader = LemmaDownloader(default_target_dir="/tmp/test_lemma")
    plan = downloader.prepare_download_plan(mode="sample")
    assert plan.mode == "sample"
    assert len(plan.items) >= 4
    assert plan.total_estimated_bytes > 0
    assert any("app-000174" in it.name for it in plan.items)


def test_list_documented_incidents():
    incidents = list_lemma_incidents_use_case()
    assert len(incidents) >= 4
    assert any(i.incident_id == "lemma-20220606-ddos-oom" for i in incidents)

    inc = get_lemma_incident_use_case("lemma-20220606-ddos-oom")
    assert inc is not None
    assert "reviews" in inc.root_cause_service
    assert inc.system.startswith("book-info")


def test_describe_lemma_empty(tmp_path):
    res = describe_lemma_use_case(data_root=tmp_path)
    assert res["n_rows"] == 0
    assert res["columns"] == []


def test_export_lemma_logs(tmp_path):
    out_csv = tmp_path / "out.csv"
    res = export_lemma_logs_use_case(output_path=out_csv, format="csv", limit=5)
    assert out_csv.exists()
    assert res["total_exported"] >= 0
