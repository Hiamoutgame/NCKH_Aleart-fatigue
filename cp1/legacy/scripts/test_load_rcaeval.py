#!/usr/bin/env python3
"""
[DEPRECATED — 2026-09-28] Script này có 2 giả định SAI:
  1. `normal_timesteps` / `faulty_timesteps` là danh sách timestamp.
     Thực tế chúng là SỐ NGUYÊN (số điểm), không subscript được.
  2. Log nằm trong config 'cases' hoặc config 'logs'.
     Thực tế log nằm ở file `logs.parquet` riêng của TỪNG case,
     và chỉ 359/735 case có file này.

=> Dùng `cp1/verify_rcaeval.py` thay thế.
   Xem kết quả kiểm chứng đầy đủ tại `cp1/data_schema_notes.md`.

Test load RCAEval từ HuggingFace + kiểm tra log format thực tế
Chạy: python test_load_rcaeval.py
"""

from datasets import load_dataset
import pandas as pd
import json

def main():
    print("=" * 60)
    print("LOAD RCAEval DATASET FROM HUGGINGFACE")
    print("=" * 60)

    # Load dataset
    print("\n[1/4] Loading dataset: phamquiluan/RCAEval (config=cases, split=train)...")
    ds = load_dataset("phamquiluan/RCAEval", "cases", split="train")
    print(f"    Total cases: {len(ds)}")
    print(f"    Features: {list(ds.features.keys())}")

    # Inspect first case
    print("\n[2/4] Inspecting first case (index 0)...")
    case = ds[0]
    for k, v in case.items():
        if isinstance(v, (list, dict)):
            print(f"  {k}: {type(v).__name__} (len={len(v) if hasattr(v, '__len__') else 'N/A'})")
        else:
            print(f"  {k}: {v}")

    # Check log availability
    print("\n[3/4] Checking log data availability...")
    has_logs_count = sum(1 for c in ds if c['has_logs'])
    print(f"    Cases with has_logs=True: {has_logs_count}/{len(ds)}")

    if has_logs_count > 0:
        # Find first case with logs
        for i, c in enumerate(ds):
            if c['has_logs']:
                print(f"\n    First case with logs: index {i}")
                print(f"    n_logs: {c['n_logs']}")
                print(f"    system: {c['system']}")
                print(f"    root_cause_service: {c['root_cause_service']}")
                print(f"    fault: {c['fault']}")
                print(f"    fault_description: {c['fault_description']}")
                print(f"    inject_time: {c['inject_time']}")
                # FIX 2026-09-28: normal_timesteps / faulty_timesteps la SO NGUYEN (so diem),
                # khong phai danh sach timestamp -> khong subscript duoc.
                print(f"    normal_timesteps: {c['normal_timesteps']} (so diem, KHONG phai list)")
                print(f"    faulty_timesteps: {c['faulty_timesteps']} (so diem, KHONG phai list)")
                print(f"    time_start={c['time_start']}  inject_time={c['inject_time']}  time_end={c['time_end']}")
                
                # Check if logs are in a separate field or need separate loading
                print(f"\n    All fields in this case:")
                for k, v in c.items():
                    if 'log' in k.lower():
                        print(f"      {k}: {type(v)} = {v}")
                break

    # Check if there's a separate logs dataset/config
    print("\n[4/4] Checking all configs in dataset...")
    try:
        all_configs = load_dataset("phamquiluan/RCAEval")
        print(f"    Available configs: {list(all_configs.keys())}")
        for config_name, config_ds in all_configs.items():
            print(f"      {config_name}: {config_ds}")
            if hasattr(config_ds, 'features'):
                print(f"        Features: {list(config_ds['train'].features.keys()) if 'train' in config_ds else list(config_ds.features.keys())}")
    except Exception as e:
        print(f"    Error loading all configs: {e}")

    # Try to load logs config if exists
    print("\n[BONUS] Trying to load logs config...")
    try:
        logs_ds = load_dataset("phamquiluan/RCAEval", "logs", split="train")
        print(f"    Logs dataset: {len(logs_ds)} entries")
        print(f"    Logs features: {list(logs_ds.features.keys())}")
        if len(logs_ds) > 0:
            log_sample = logs_ds[0]
            print(f"    Sample log entry:")
            for k, v in log_sample.items():
                print(f"      {k}: {v}")
    except Exception as e:
        print(f"    No separate logs config or error: {e}")

if __name__ == "__main__":
    main()