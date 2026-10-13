#!/usr/bin/env python3
"""
Verify RCAEval: schema thuc te + kha nang sinh WARNING alert stream.

Chay: python cp1/verify_rcaeval.py
Output: cp1/_verify_out.txt (cung luc in ra console)

Muc dich (theo note/28-09.md, Uu tien 1):
  1. Dataset tai duoc khong.
  2. So case thuc te + field thuc te.
  3. Log nam o config/field nao.
  4. Co timestamp, service, message, severity/level khong.
  5. Co log WARNING khong, so luong/ty le.
"""

from __future__ import annotations

import io
import json
import sys
from collections import Counter, defaultdict

import pandas as pd
from datasets import load_dataset
from huggingface_hub import hf_hub_download, list_repo_files

REPO = "phamquiluan/RCAEval"

OUT = io.StringIO()


def say(*args):
    line = " ".join(str(a) for a in args)
    print(line)
    OUT.write(line + "\n")


def section(title: str):
    say("")
    say("=" * 72)
    say(title)
    say("=" * 72)


# ---------------------------------------------------------------- 1. cases
def check_cases():
    section("[1] CONFIG 'cases' — schema cap case")
    ds = load_dataset(REPO, "cases", split="train")
    say(f"total cases            : {len(ds)}")
    say(f"features               : {list(ds.features.keys())}")
    say("")
    say("kieu du lieu tung field (lay tu 1 case dau):")
    for k, v in ds[0].items():
        say(f"  {k:24s} {type(v).__name__:8s}  {str(v)[:60]}")

    df = ds.to_pandas()
    say("")
    say("dtype pandas (toan bo cases):")
    for k, t in df.dtypes.items():
        say(f"  {k:24s} {str(t)}")
    return df


# ------------------------------------------------------------- 2. inventory
def check_inventory():
    section("[2] INVENTORY file trong repo HF")
    files = list_repo_files(REPO, repo_type="dataset")
    kinds = Counter(f.split("/")[-1] for f in files if "/" in f)
    say(f"tong so file           : {len(files)}")
    for name, n in kinds.most_common():
        say(f"  {name:20s} {n}")

    cases_with_logs = sorted({f.split("/")[0] for f in files if f.endswith("/logs.parquet")})
    cases_with_traces = sorted({f.split("/")[0] for f in files if f.endswith("/traces.parquet")})
    cases_with_rc = sorted({f.split("/")[0] for f in files if f.endswith("/root_cause.txt")})
    say("")
    say(f"case co logs.parquet   : {len(cases_with_logs)}")
    say(f"case co traces.parquet : {len(cases_with_traces)}")
    say(f"case co root_cause.txt : {len(cases_with_rc)}")
    say("")
    say("CAC LOAI CONFIG TRONG HF DATASET (load_dataset khong truyen config):")
    return cases_with_logs


# ---------------------------------------------------------------- 3. case row
def check_case_row(df: pd.DataFrame):
    section("[3] PHAN BO cac field quan trong")
    say(f"has_logs=True          : {int(df['has_logs'].sum())}/{len(df)}")
    say(f"has_traces=True        : {int(df['has_traces'].sum())}/{len(df)}")
    say(f"has_root_cause_file    : {int(df['has_root_cause_file'].sum())}/{len(df)}")
    say("")
    say("system_name x has_logs:")
    piv = df.groupby(["system_name", "has_logs"]).size().unstack(fill_value=0)
    say(piv.to_string())
    say("")
    say("fault types (case co has_logs=True):")
    sub = df[df["has_logs"]]
    say(sub["fault"].value_counts().to_string())
    say("")
    say("so case co logs theo (system, fault):")
    say(sub.groupby(["system", "fault"]).size().unstack(fill_value=0).to_string())
    say("")
    say(f"n_logs min/max/mean    : {int(sub['n_logs'].min())} / {int(sub['n_logs'].max())} / {int(sub['n_logs'].mean())}")


# ---------------------------------------------------------------- 4. logs
def check_logs(cases_with_logs: list[str], n_sample: int = 5):
    section("[4] LOG SCHEMA — file logs.parquet cua tung case")
    say(f"lay mau {n_sample} case dau co logs: {cases_with_logs[:n_sample]}")
    say("")

    schemas = {}
    samples = {}
    for case in cases_with_logs[:n_sample]:
        path = hf_hub_download(REPO, f"{case}/logs.parquet", repo_type="dataset")
        df = pd.read_parquet(path)
        schemas[case] = list(df.columns)
        samples[case] = df
        say(f"--- {case} ---")
        say(f"  rows    : {len(df)}")
        say(f"  columns : {list(df.columns)}")
        say(f"  dtypes  : {dict(df.dtypes.astype(str))}")
        say("  head(5):")
        with pd.option_context("display.max_colwidth", 120, "display.width", 200):
            say(df.head(5).to_string())
        say("")

    section("[4b] CO field timestamp / service / message / severity khong?")
    need = {
        "timestamp": ["timestamp", "time", "ts", "datetime", "@timestamp"],
        "service": ["service", "service_name", "container", "pod", "cmdb_id", "component"],
        "message": ["message", "msg", "log", "body", "content"],
        "severity": ["severity", "level", "log_level", "loglevel", "priority"],
    }
    all_cols = set()
    for cols in schemas.values():
        all_cols |= set(c.lower() for c in cols)
    for concept, candidates in need.items():
        hit = [c for c in candidates if c in all_cols]
        say(f"  {concept:10s} -> {'FOUND: ' + str(hit) if hit else 'NOT FOUND'}")

    section("[5] WARNING LEVEL — co log WARNING khong?")
    for case, df in samples.items():
        say(f"--- {case} ---")
        lvl_col = None
        for c in df.columns:
            if c.lower() in ("level", "severity", "log_level", "loglevel"):
                lvl_col = c
                break
        if lvl_col is None:
            say("  khong tim thay cot level/severity")
            continue
        vc = df[lvl_col].astype(str).value_counts()
        say(f"  cot level = '{lvl_col}'")
        say(f"  phan bo : {dict(vc)}")
        warn = df[df[lvl_col].astype(str).str.upper().str.contains("WARN")]
        say(f"  so WARNING: {len(warn)} / {len(df)} = {100.0 * len(warn) / max(len(df), 1):.2f}%")
        if len(warn):
            with pd.option_context("display.max_colwidth", 140, "display.width", 220):
                say("  vi du WARNING (5 dong):")
                say(warn.head(5).to_string())
        say("")

    return samples


# ------------------------------------------------ 6. distribution WARNING
def check_warning_scale(cases_with_logs: list[str], limit: int = 40):
    section(f"[6] QUY MO WARNING tren {min(limit, len(cases_with_logs))} case (uoc luong)")
    rows = []
    for case in cases_with_logs[:limit]:
        try:
            path = hf_hub_download(REPO, f"{case}/logs.parquet", repo_type="dataset")
            df = pd.read_parquet(path)
        except Exception as e:  # noqa: BLE001
            say(f"  {case}: LOI {e}")
            continue
        lvl_col = next((c for c in df.columns if c.lower() in ("level", "severity", "log_level", "loglevel")), None)
        if lvl_col is None:
            continue
        levels = df[lvl_col].astype(str).str.upper().value_counts().to_dict()
        n_warn = sum(v for k, v in levels.items() if "WARN" in k)
        rows.append(
            {
                "case": case,
                "n_logs": len(df),
                "n_warning": n_warn,
                "pct_warning": round(100.0 * n_warn / max(len(df), 1), 2),
                "levels": levels,
            }
        )
    if rows:
        r = pd.DataFrame(rows)
        say(f"  case kiem tra     : {len(r)}")
        say(f"  tong log          : {int(r['n_logs'].sum())}")
        say(f"  tong WARNING      : {int(r['n_warning'].sum())}")
        say(f"  %WARNING trung binh: {r['pct_warning'].mean():.2f}%")
        say(f"  case co WARNING>0 : {int((r['n_warning'] > 0).sum())}/{len(r)}")
        say("")
        say("  phan bo level gop toan bo mau:")
        agg = Counter()
        for d in r["levels"]:
            agg.update(d)
        say(f"  {dict(agg)}")
    return rows


def main():
    cases_df = check_cases()
    cases_with_logs = check_inventory()
    check_case_row(cases_df)
    samples = check_logs(cases_with_logs)
    warnings_rows = check_warning_scale(cases_with_logs)

    section("KET QUA JSON (raw)")
    say(json.dumps({"n_warning_sample_rows": warnings_rows[:5]}, ensure_ascii=False, indent=2, default=str))

    with open("cp1/_verify_out.txt", "w", encoding="utf-8") as f:
        f.write(OUT.getvalue())
    print("\n>> da ghi cp1/_verify_out.txt")


if __name__ == "__main__":
    main()
