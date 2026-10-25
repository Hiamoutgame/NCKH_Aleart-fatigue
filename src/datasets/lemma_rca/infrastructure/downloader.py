"""Downloader implementation for LEMMA-RCA dataset.

Ho tro 2 che do tai:
1. 'sample' (Khuyen dung - ~30-50MB):
   Su dung HTTP Range Requests (thong qua fsspec + zipfile) de doc truc tiep tu xa
   va chi trich xuat cac file log ung dung (app-*), log ha tang (infra-*) va file
   mo ta ground truth (README.pptx, pod config) ma khong can tai toan bo 51GB.
2. 'full' (~51GB):
   Tai toan bo cac file zip (20210517.zip, 20210524.zip, 20211203.zip, 20220606.zip) tu Hugging Face.
Co co 'dry_run' de nguoi dung quan sat ke hoach truoc khi tai.
"""

from __future__ import annotations

import os
import shutil
import zipfile
from pathlib import Path

from src.shared.infrastructure.paths import DATASET_PATHS
from typing import Optional

from ..domain.models import DownloadItem, DownloadPlan

HF_REPO_ID = "Lemma-RCA-NEC/Product_Review_Original"
HF_RESOLVE_BASE = f"https://huggingface.co/datasets/{HF_REPO_ID}/resolve/main"

# Cac file sample can trich xuat trong che do 'sample'
SAMPLE_FILES_PLAN = [
    {
        "name": "README & Dataset Description",
        "relative_path": "README.md",
        "remote_zip": None,
        "remote_url": f"{HF_RESOLVE_BASE}/README.md",
        "estimated_size_bytes": 832,
        "is_essential": True,
    },
    {
        "name": "Scenario Presentation & Ground Truth (20220606/README.pptx)",
        "relative_path": "LEMMA_RCA_20220606_Scenario_GroundTruth.pptx",
        "remote_zip": "20220606.zip",
        "inner_path": "20220606/README.pptx",
        "remote_url": f"{HF_RESOLVE_BASE}/20220606.zip",
        "estimated_size_bytes": 210937,
        "is_essential": True,
    },
    {
        "name": "Pod Topology Before Fault (20220606/all_pod_before.txt)",
        "relative_path": "pod_topology/all_pod_before.txt",
        "remote_zip": "20220606.zip",
        "inner_path": "20220606/pod/all_pod_before.txt",
        "remote_url": f"{HF_RESOLVE_BASE}/20220606.zip",
        "estimated_size_bytes": 71729,
        "is_essential": True,
    },
    {
        "name": "Pod Topology After Fault (20220606/all_pod_after.txt)",
        "relative_path": "pod_topology/all_pod_after.txt",
        "remote_zip": "20220606.zip",
        "inner_path": "20220606/pod/all_pod_after.txt",
        "remote_url": f"{HF_RESOLVE_BASE}/20220606.zip",
        "estimated_size_bytes": 71289,
        "is_essential": True,
    },
    {
        "name": "Application Microservice Logs Sample 1 (app-000174)",
        "relative_path": "sample/app-000174log20210517_132254.json",
        "remote_zip": "20210517.zip",
        "inner_path": "CPF_data02_20210517_extract/Log/20210517/app-000174/app-000174log20210517_132254.json",
        "remote_url": f"{HF_RESOLVE_BASE}/20210517.zip",
        "estimated_size_bytes": 23033799,
        "is_essential": True,
    },
    {
        "name": "Infrastructure Node & Journald Logs Sample 1 (infra-000185)",
        "relative_path": "sample/infra-000185log20210517_211114.json",
        "remote_zip": "20210517.zip",
        "inner_path": "CPF_data02_20210517_extract/Log/20210517/infra-000185/infra-000185log20210517_211114.json",
        "remote_url": f"{HF_RESOLVE_BASE}/20210517.zip",
        "estimated_size_bytes": 26503890,
        "is_essential": True,
    },
]

# Cac file full zip
FULL_ZIP_FILES = [
    ("20210517.zip", 14040008257),
    ("20210524.zip", 11721862708),
    ("20211203.zip", 18012496133),
    ("20220606.zip", 9859441848),
]


class LemmaDownloader:
    """Dieu phoi viec tai va trich xuat du lieu LEMMA-RCA."""

    def __init__(self, default_target_dir: Optional[str | Path] = None) -> None:
        if default_target_dir is None:
            # data/raw/huggingface/lemma_rca
            self.default_target_dir = DATASET_PATHS["lemma_rca"]
        else:
            self.default_target_dir = Path(default_target_dir)

    def prepare_download_plan(
        self, mode: str = "sample", target_dir: Optional[str | Path] = None
    ) -> DownloadPlan:
        """Lap ke hoach tai du lieu (Dry-run plan) ma khong bat buoc tai that."""
        dest = Path(target_dir) if target_dir else self.default_target_dir
        items: list[DownloadItem] = []
        notes: list[str] = []

        if mode == "sample":
            for entry in SAMPLE_FILES_PLAN:
                items.append(
                    DownloadItem(
                        name=entry["name"],
                        relative_path=entry["relative_path"],
                        remote_url=entry["remote_url"],
                        estimated_size_bytes=entry["estimated_size_bytes"],
                        is_essential=entry["is_essential"],
                    )
                )
            total_bytes = sum(it.estimated_size_bytes for it in items)
            notes.append("Che do SAMPLE (Khuyen dung): Trich xuat file log mau & ground truth truc tiep qua HTTP Range.")
            notes.append(f"Tong dung luong can tai ve: ~{total_bytes / (1024 * 1024):.2f} MB.")
            notes.append(f"Thu muc luu tru dich: {dest}")
            notes.append("Uu diem: Khong can tai 51GB zip; doc duoc ngay 20,000+ dong log elasticsearch va ground truth.")

        elif mode == "full":
            for fname, size_bytes in FULL_ZIP_FILES:
                items.append(
                    DownloadItem(
                        name=f"Full archive: {fname}",
                        relative_path=fname,
                        remote_url=f"{HF_RESOLVE_BASE}/{fname}",
                        estimated_size_bytes=size_bytes,
                        is_essential=False,
                    )
                )
            total_bytes = sum(it.estimated_size_bytes for it in items)
            notes.append("CANH BAO CHE DO FULL: Toan bo 4 file zip lon cua dataset LEMMA-RCA.")
            notes.append(f"Tong dung luong can tai ve: ~{total_bytes / (1024 * 1024 * 1024):.2f} GB (~51 GB).")
            notes.append("Chi dung khi co du dung luong o dia va duong truyen mang on dinh.")

        else:
            raise ValueError(f"Che do '{mode}' khong hop le. Chon 'sample' hoac 'full'.")

        return DownloadPlan(
            mode=mode,
            target_dir=str(dest),
            items=items,
            total_estimated_bytes=sum(it.estimated_size_bytes for it in items),
            notes=notes,
        )

    def execute_download(self, plan: DownloadPlan, dry_run: bool = False) -> list[str]:
        """Thuc thi ke hoach tai du lieu."""
        dest_dir = Path(plan.target_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        saved_files: list[str] = []

        print(f"=== LEMMA-RCA DOWNLOAD EXECUTOR [{plan.mode.upper()}] ===")
        for note in plan.notes:
            print(f"[*] {note}")

        if dry_run:
            print("\n[DRY RUN] Ke hoach danh sach cac file se duoc tai:")
            for idx, item in enumerate(plan.items, start=1):
                mb = item.estimated_size_bytes / (1024 * 1024)
                print(f"  ({idx}) {item.name}: ~{mb:.2f} MB -> {item.relative_path}")
            return []

        if plan.mode == "sample":
            # Tai cac file sample thong qua HTTP range doc truc tiep tu remote zip
            try:
                import fsspec
            except ImportError:
                raise RuntimeError("Can cai dat fsspec de tai selective qua HTTP range: pip install fsspec")

            remote_zips: dict[str, Any] = {}
            try:
                for entry in SAMPLE_FILES_PLAN:
                    target_file = dest_dir / entry["relative_path"]
                    target_file.parent.mkdir(parents=True, exist_ok=True)

                    if target_file.exists() and target_file.stat().st_size > 0:
                        print(f"-> File da ton tai san: {target_file.name} ({target_file.stat().st_size} bytes)")
                        saved_files.append(str(target_file))
                        continue

                    zip_name = entry.get("remote_zip")
                    if zip_name is None:
                        # Tai file thong thuong (README)
                        print(f"-> Dang tai {entry['name']}...")
                        import urllib.request
                        urllib.request.urlretrieve(entry["remote_url"], str(target_file))
                    else:
                        # Doc tu remote zip qua fsspec
                        if zip_name not in remote_zips:
                            print(f"-> Dang ket noi remote zip {zip_name} qua HTTP Range...")
                            fs_file = fsspec.open(entry["remote_url"], mode="rb")
                            remote_zips[zip_name] = (fs_file, zipfile.ZipFile(fs_file.open()))

                        _, zf = remote_zips[zip_name]
                        inner_path = entry["inner_path"]
                        print(f"-> Dang trich xuat {inner_path}...")
                        content = zf.read(inner_path)
                        target_file.write_bytes(content)

                    print(f"   [OK] Da luu: {target_file} ({target_file.stat().st_size} bytes)")
                    saved_files.append(str(target_file))
            finally:
                for fs_file, _ in remote_zips.values():
                    try:
                        fs_file.close()
                    except Exception:
                        pass

        elif plan.mode == "full":
            from huggingface_hub import hf_hub_download
            for fname, _ in FULL_ZIP_FILES:
                print(f"-> Dang tai {fname} tu Hugging Face repo {HF_REPO_ID} (kich thuoc lon)...")
                downloaded = hf_hub_download(
                    repo_id=HF_REPO_ID,
                    filename=fname,
                    repo_type="dataset",
                    local_dir=str(dest_dir),
                )
                saved_files.append(downloaded)
                print(f"   [OK] Da tai ve: {downloaded}")

        return saved_files
