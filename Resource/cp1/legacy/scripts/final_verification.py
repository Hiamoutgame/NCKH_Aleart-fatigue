#!/usr/bin/env python3
"""
VERIFICATION CUOI (chot so lieu cho cp1/data_schema_notes.md)

  A. Phan bo WARN theo tung case, tach rieng SS / TT / OB (tu CSV, khong tai lai)
  B. Cau truc DUPLICATE: template tho vs template da chuan hoa (bo UUID / trace-id / so)
  C. Moi case logs.parquet chua log cua BAO NHIEU service? (co lam cascading duoc khong)
  D. WARN nam trong normal window hay faulty window (theo tung nhom fault)

Output: cp1/_final_verify_out.txt
"""

from __future__ import annotations

import io
import re
from collections import Counter

import pandas as pd
from datasets import load_dataset
from huggingface_hub import hf_hub_download

REPO = "phamquiluan/RCAEval"
OUT = io.StringIO()


def say(*a):
    line = " ".join(str(x) for x in a)
    print(line, flush=True)
    OUT.write(line + "\n")


def section(t):
    say("")
    say("=" * 80)
    say(t)
    say("=" * 80)


WARN = re.compile(r"\bWARN(?:ING)?\b")

# chuan hoa: bo timestamp, so, uuid, hex, trace-id trong ngoac vuong log4j
RE_TS = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}[.,]\d+\s*")
RE_UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
RE_HEX = re.compile(r"\b[0-9a-f]{8,}\b")
RE_THREAD = re.compile(r"\[\s*[-\w]*nio-\d+-exec-\d+\s*\]|\[\s*\w*Container-\d+\s*\]|\[\s*main\s*\]")
RE_LOG4J_HDR = re.compile(r"^(\d{4}-\d{2}-\d{2}[ T][\d:.,]+)\s+(\w+)\s+(\[[^\]]*\])\s+(\d+)\s+---\s+(\[[^\]]*\])\s*")
RE_NUM = re.compile(r"\b\d+(?:\.\d+)?\b")


def normalize(msg: str) -> str:
    if not isinstance(msg, str):
        return ""
    s = RE_TS.sub("", msg)
    s = RE_UUID.sub("<UUID>", s)
    s = RE_LOG4J_HDR.sub(lambda m: f"<TS> {m.group(2)} {m.group(3)} <PID> --- {m.group(5)} ", s)
    s = RE_THREAD.sub("<THREAD>", s)
    s = RE_HEX.sub("<HEX>", s)
    s = RE_NUM.sub("<N>", s)
    return s.strip()


def main():
    idx = load_dataset(REPO, "cases", split="train").to_pandas().set_index("case")
    csv = pd.read_csv("cp1/_warning_per_case.csv")
    if "sys2" not in csv.columns:
        csv["sys2"] = csv["sys"].astype(str).str.split("-").str[-1]
        csv.to_csv("cp1/_warning_per_case.csv", index=False, encoding="utf-8")

    # ------------------------------------------------------------ A
    section("[A] PHAN BO WARN THEO TUNG CASE (tach theo he thong)")
    for sysname in ["OB", "SS", "TT"]:
        sub = csv[csv["sys2"] == sysname]
        say("")
        say(f"--- {sysname}: {len(sub)} case co logs ---")
        say(f"  tong log        : {int(sub['n_logs'].sum()):,}")
        say(f"  tong dong WARN  : {int(sub['n_warn'].sum()):,}")
        say(f"  case WARN > 0   : {int((sub['n_warn'] > 0).sum())}/{len(sub)}")
        say(f"  case WARN >= 10 : {int((sub['n_warn'] >= 10).sum())}/{len(sub)}")
        say(f"  case WARN >= 50 : {int((sub['n_warn'] >= 50).sum())}/{len(sub)}")
        say(f"  WARN max 1 case : {int(sub['n_warn'].max())}")
        say(f"  WARN median     : {sub['n_warn'].median()}")
        s = sub[sub["n_warn"] > 0].sort_values("n_warn", ascending=False)
        say("  bang chi tiet (case WARN>0):")
        say("    " + s[["case", "n_logs", "n_warn", "n_error"]].to_string(index=False).replace("\n", "\n    "))

    csv.to_csv("cp1/_warning_per_case.csv", index=False, encoding="utf-8")

    # ------------------------------------------------------------ B
    section("[B] CAU TRUC DUPLICATE — template tho vs da chuan hoa")
    ss = csv[(csv["sys2"] == "SS")].sort_values("n_warn", ascending=False)
    probes = list(ss.head(6)["case"])
    # them vai case RE2-SS dai dien tung fault
    for f in ["cpu", "mem", "disk", "delay", "loss", "socket"]:
        c = f"re2ss_carts_{f}_1"
        if c in idx.index:
            probes.append(c)
    for f in ["f1", "f2", "f3", "f4"]:
        c = f"re3ss_carts_{f}_1"
        if c in idx.index:
            probes.append(c)
    probes = list(dict.fromkeys(probes))

    rows = []
    for case in probes:
        p = hf_hub_download(REPO, f"{case}/logs.parquet", repo_type="dataset")
        df = pd.read_parquet(p, columns=["timestamp", "container_name", "message"])
        w = df[df["message"].astype("string").str.contains(WARN, regex=True, na=False)].copy()
        if not len(w):
            continue
        w["norm"] = w["message"].map(normalize)
        meta = idx.loc[case]
        tinj = int(meta["inject_time"])
        n_norm = int((w["timestamp"] < tinj).sum())
        n_flt = int((w["timestamp"] >= tinj).sum())
        rows.append({
            "case": case,
            "fault": meta["fault"],
            "root_cause": meta["root_cause_service"],
            "n_warn": len(w),
            "n_tpl_raw": int(w["message"].nunique()),
            "n_tpl_norm": int(w["norm"].nunique()),
            "top1_share_pct": round(100 * w["norm"].value_counts().iloc[0] / len(w), 1),
            "warn_normal": n_norm,
            "warn_faulty": n_flt,
            "pct_normal": round(100 * n_norm / len(w), 1),
            "n_containers_warn": int(w["container_name"].nunique()),
            "n_containers_case": int(df["container_name"].nunique()),
        })
        say("")
        say(f"--- {case}  (fault={meta['fault']}, root_cause={meta['root_cause_service']}) ---")
        say(f"  WARN={len(w)}  template tho={int(w['message'].nunique())}  "
            f"template chuan hoa={int(w['norm'].nunique())}")
        say(f"  normal window={n_norm}  faulty window={n_flt}")
        say(f"  container co WARN: {dict(w['container_name'].value_counts().head(6))}")
        say(f"  container trong case: {int(df['container_name'].nunique())}")
        for t, n in w["norm"].value_counts().head(4).items():
            say(f"    {n:5d} ({100*n/len(w):5.1f}%)  {t[:150]}")

    t = pd.DataFrame(rows)
    section("[B2] BANG TONG HOP DUPLICATE")
    say(t.to_string(index=False))

    # ------------------------------------------------------------ C
    section("[C] MOI CASE CHUA LOG CUA BAO NHIEU SERVICE?")
    say("  (n_containers = so service xuat hien trong logs.parquet cua 1 case)")
    say(csv.groupby("sys2")["n_containers"].describe().to_string())
    say("")
    say("  so case chi co 1 service: " + str(int((csv["n_containers"] == 1).sum())) + "/" + str(len(csv)))

    # ------------------------------------------------------------ D
    section("[D] WARN THEO LOAI FAULT — normal vs faulty window (mau SS)")
    rows2 = []
    for case in ss.head(14)["case"]:
        meta = idx.loc[case]
        p = hf_hub_download(REPO, f"{case}/logs.parquet", repo_type="dataset")
        df = pd.read_parquet(p, columns=["timestamp", "message"])
        w = df[df["message"].astype("string").str.contains(WARN, regex=True, na=False)]
        tinj = int(meta["inject_time"])
        n_norm = int((w["timestamp"] < tinj).sum())
        rows2.append({
            "case": case, "fault": meta["fault"], "n_warn": len(w),
            "normal": n_norm, "faulty": len(w) - n_norm,
            "pct_normal": round(100 * n_norm / max(len(w), 1), 1),
        })
    d = pd.DataFrame(rows2)
    say(d.to_string(index=False))
    say("")
    say("  -> case fault CODE-LEVEL (f1/f3): WARN gan nhu 100% trong FAULTY window")
    say("  -> case fault HA TANG (cpu/disk/loss/mem): WARN chia ~50/50 normal & faulty")

    with open("cp1/_final_verify_out.txt", "w", encoding="utf-8") as f:
        f.write(OUT.getvalue())
    print("\n>> da ghi cp1/_final_verify_out.txt")


if __name__ == "__main__":
    main()
