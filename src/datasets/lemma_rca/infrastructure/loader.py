"""Loader and adapter for LEMMA-RCA dataset.

Chiu trach nhiem doc, parse va chuan hoa cac file JSON export tu Elasticsearch cua LEMMA-RCA
thanh domain models hoac danh sach cac dong canonical theo dung quy chuan explore_datasets.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from src.shared.infrastructure.paths import DATASET_PATHS
from typing import Any, Iterator, Optional

from ..domain.models import LemmaIncident, LemmaLogRecord

# Regex nhan dien log level tu header message (vi du: DEBUG:urllib3..., I0516... [k8s glog], WARN [carts]...)
LEVEL_PATTERN = re.compile(
    r"(?P<glog>^[IWEF]\d{4})|(?:\b(?P<lvl>DEBUG|INFO|WARN(?:ING)?|ERROR|FATAL|CRITICAL|TRACE)\b)"
)
GLOG_MAP = {
    "I": "INFO",
    "W": "WARN",
    "E": "ERROR",
    "F": "FATAL",
}


class LemmaLoader:
    """Adapter doc va parse du lieu log LEMMA-RCA tu dia."""

    def __init__(self, data_root: Optional[str | Path] = None) -> None:
        if data_root is None:
            self.data_root = DATASET_PATHS["lemma_rca"]
        else:
            self.data_root = Path(data_root)

    def locate_log_files(self, incident_id: Optional[str] = None) -> list[Path]:
        """Tim cac file JSON log trong thu muc local, loc theo incident_id neu duoc chi dinh."""
        if not self.data_root.exists():
            return []

        def is_log_file(p: Path) -> bool:
            return (
                p.is_file()
                and p.stat().st_size > 1024
                and (p.name.startswith("app-") or p.name.startswith("infra-"))
            )

        if incident_id:
            for tag in ["20220606", "20210517", "20210524", "20211203"]:
                if tag in incident_id:
                    matched = sorted([
                        p for p in self.data_root.rglob("*.json")
                        if is_log_file(p) and tag in str(p)
                    ])
                    if matched:
                        return matched

        return sorted([p for p in self.data_root.rglob("*.json") if is_log_file(p)])

    @staticmethod
    def extract_level_from_message(raw_msg: str, default_level: str = "INFO") -> str:
        """Trich xuat log level tu noi dung message neu cot level goc la 'unknown'."""
        if not raw_msg:
            return default_level

        match = LEVEL_PATTERN.search(raw_msg)
        if match:
            gd = match.groupdict()
            if gd.get("glog"):
                return GLOG_MAP.get(gd["glog"][0], default_level)
            if gd.get("lvl"):
                lvl = gd["lvl"].upper()
                return "WARN" if lvl == "WARNING" else lvl

        return default_level

    @classmethod
    def parse_elasticsearch_hit(cls, hit: dict[str, Any], file_hint: str = "") -> LemmaLogRecord:
        record_id = hit.get("_id", "")
        source = hit.get("_source", {})
        index_name = hit.get("_index", "")

        timestamp_str = source.get("@timestamp") or source.get("timestamp") or ""
        raw_msg = source.get("message") or ""

        # Lay container / pod / namespace tu kubernetes block neu co
        k8s = source.get("kubernetes", {})
        container_name = k8s.get("container_name")
        pod_name = k8s.get("pod_name")
        namespace = k8s.get("namespace_name")
        host = k8s.get("host") or source.get("hostname")

        # Xac dinh service
        if container_name:
            service = container_name
        elif pod_name:
            # Thuong pod_name co dang productpage-v1-xxx -> cat lay productpage
            service = pod_name.split("-")[0]
        elif "systemd" in source:
            comm = source["systemd"].get("t", {}).get("COMM")
            service = f"systemd:{comm}" if comm else "systemd"
        elif index_name:
            service = index_name
        else:
            service = "unknown"

        # Xac dinh log level
        raw_level = source.get("level", "")
        if raw_level and raw_level.lower() != "unknown":
            level = raw_level.upper()
            if level == "WARNING":
                level = "WARN"
        else:
            level = cls.extract_level_from_message(raw_msg)

        # Xac dinh log_type (app vs infra)
        if "infra" in index_name.lower() or "infra" in file_hint.lower() or "systemd" in source:
            log_type = "infra"
        else:
            log_type = "app"

        return LemmaLogRecord(
            record_id=record_id,
            timestamp_str=timestamp_str,
            service=service,
            level=level,
            message=raw_msg,
            pod_name=pod_name,
            container_name=container_name,
            namespace=namespace,
            host=host,
            log_type=log_type,
            raw=json.dumps(source, ensure_ascii=False),
        )

    def iter_log_records(
        self,
        limit: Optional[int] = None,
        service: Optional[str] = None,
        level: Optional[str] = None,
        query: Optional[str] = None,
    ) -> Iterator[LemmaLogRecord]:
        """Duyet stream cac ban ghi log tu cac file JSON co trong local directory."""
        files = self.locate_log_files()
        if not files:
            return

        count = 0
        service_lower = service.lower() if service else None
        level_upper = level.upper() if level else None
        query_lower = query.lower() if query else None

        for file_path in files:
            file_hint = file_path.name
            try:
                with file_path.open("r", encoding="utf-8", errors="replace") as handle:
                    data = json.load(handle)
            except Exception:
                continue

            hits = data.get("hits", {}).get("hits", [])
            for hit in hits:
                record = self.parse_elasticsearch_hit(hit, file_hint=file_hint)

                # Bo loc
                if service_lower and service_lower not in record.service.lower():
                    continue
                if level_upper and record.level != level_upper:
                    continue
                if query_lower and query_lower not in record.message.lower():
                    continue

                yield record
                count += 1
                if limit is not None and count >= limit:
                    return

    def load_canonical_rows(
        self,
        limit: Optional[int] = 10000,
        service: Optional[str] = None,
        level: Optional[str] = None,
        query: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Tra ve danh sach cac dict voi format canonical phuc vu 4 tieu chi explore_datasets."""
        rows: list[dict[str, Any]] = []
        for rec in self.iter_log_records(limit=limit, service=service, level=level, query=query):
            rows.append(
                {
                    "timestamp": rec.timestamp_str,
                    "service": rec.service,
                    "level": rec.level,
                    "message": rec.message,
                    "pod": rec.pod_name or "",
                    "host": rec.host or "",
                    "log_type": rec.log_type,
                    "root_cause": "reviews-v2/reviews-v3" if "reviews" in rec.service else "normal",
                }
            )
        return rows

    @staticmethod
    def list_documented_incidents() -> list[LemmaIncident]:
        """Danh sach Ground Truth cac kich ban su co da duoc ghi nhan trong LEMMA-RCA."""
        return [
            LemmaIncident(
                incident_id="lemma-20220606-ddos-oom",
                system="book-info (Openshift OKD)",
                date="2022-06-06",
                fault_type="DDoS Attack / Excessive Traffic -> OOM Error",
                root_cause_service="reviews-v2, reviews-v3",
                start_time="2022-06-03 18:30:00",
                inject_time="2022-06-04 18:30:00",
                end_time="2022-06-05 19:40:00",
                description=(
                    "Kich ban DDoS tai tang vot vao service book-info gay ap luc bo nho, "
                    "dan den loi Java OutOfMemory (OOM) trong cac pod reviews-v2 va reviews-v3. "
                    "Service productpage mat ket noi den reviews va tra ve loi HTTP 503."
                ),
                symptoms="HTTP status 503 tu productpage toi reviews; Jaeger trace bi cham; Memory metrics tang vot",
                impacted_services=["productpage", "reviews-v1", "reviews-v2", "reviews-v3"],
            ),
            LemmaIncident(
                incident_id="lemma-20210517-jmeter-stress",
                system="book-info",
                date="2021-05-17",
                fault_type="Resource Contention / High Workload Stress",
                root_cause_service="productpage / compute nodes",
                start_time="2021-05-15 06:00:00",
                inject_time="2021-05-15 13:00:00",
                end_time="2021-05-17 10:00:00",
                description="Tai chay stress test JMeter Case04 49 gio voi 176,400 requests gay nghẽn CPU va network.",
                symptoms="Do tre request tang cao, ket noi bi gián đoạn, log cảnh báo retry",
                impacted_services=["productpage", "details", "ratings"],
            ),
            LemmaIncident(
                incident_id="lemma-20211203-storage-failure",
                system="book-info + mongodb NFS",
                date="2021-12-03",
                fault_type="External Storage Failure / Disk Full",
                root_cause_service="mongodb-v1 / external NFS",
                start_time="2021-12-03 10:00:00",
                inject_time="2021-12-04 12:00:00",
                end_time="2021-12-05 18:00:00",
                description="Loi storage NFS ben ngoai khien mongodb khong ghi duoc du lieu ratings/reviews.",
                symptoms="Trace jaeger timeout tai mongodb, log loi IO",
                impacted_services=["mongodb", "ratings", "reviews"],
            ),
            LemmaIncident(
                incident_id="lemma-20210524-noisy-neighbor",
                system="book-info + openshift infra",
                date="2021-05-24",
                fault_type="Noisy Neighbor / Pod CPU Throttle",
                root_cause_service="ocp4-compute-1 / tuned",
                start_time="2021-05-24 08:00:00",
                inject_time="2021-05-24 14:00:00",
                end_time="2021-05-25 12:00:00",
                description="Tien trinh tren cung worker node chiem dung CPU gay anh huong lan cận (noisy neighbor).",
                symptoms="Tang CPU throttle tren cac pod book-info, do tre phan hoi dao dong",
                impacted_services=["productpage", "reviews"],
            ),
        ]

    def get_incident(self, incident_id: str) -> Optional[LemmaIncident]:
        """Lay chi tiet su co theo incident_id."""
        for inc in self.list_documented_incidents():
            if inc.incident_id == incident_id:
                return inc
        return None
