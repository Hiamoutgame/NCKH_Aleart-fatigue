#!/usr/bin/env python3
"""
Full scan 359 case RCAEval co logs: dem WARNING chinh xac + kiem tra
tap con nao dung duoc cho de tai (WARNING-level alert aggregation).

Chay: python cp1/full_scan_warning.py
Output: cp1/_full_scan_out.txt + cp1/_warning_per_case.csv
"""

from __future__ import annotations

import io
import re
import sys

import pandas as pd
from huggingface_hub import hf_hub_download, list_repo_files

REPO = "phamquiluan/RCAEval"
OUT = io.StringIO()


def say(*a):
    line = " ".join(str(x) for x in a)
    print(line, flush=True)
    OUT.write(line + "\n")


# log4j / logback: "2024-01-23 15:38:31.234  WARN 1 --- [thread] class : msg"
LOG4J_LEVEL = re.compile(r"^\s*\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}[.,]\d+\s+(\w+)\s")
WARN_ANY = re.compile(r"\bWARN(?:ING)?\b")
ERROR_ANY = re.compile(r"\bERROR\b")
INFO_ANY = re.compile(r"\bINFO\b")
DEBUG_ANY = re.compile(r"\bDEBUG\b")


def load(case):
    p = hf_hub_download(REPO, f"{case}/logs.parquet", repo_type="dataset")
    return pd.read_parquet(p, columns=["timestamp", "container_name", "message"])


def main():
    files = list_repo_files(REPO, repo_type="dataset")
    log_cases = sorted({f.split("/")[0] for f in files if f.endswith("/logs.parquet")})
    say(f"Tong case co logs.parquet: {len(log_cases)}")

    rows = []
    for i, case in enumerate(log_cases, 1):
        try:
            df = load(case)
        except Exception as e:  # noqa: BLE001
            say(f"[{i}/{len(log_cases)}] {case}: LOI {e}")
            continue
        msgs = df["message"].astype("string")
        n = len(df)
        sysname = "ob" if "_ob" in case else ("ss" if "_ss" in case else "tt")
        r = {
            "case": case,
            "system": sysname,
            "n_logs": n,
            "n_containers": int(df["container_name"].nunique()),
            "n_warn": int(msgs.str.contains(WARN_ANY, regex=True, na=False).sum()),
            "n_error": int(msgs.str.contains(ERROR_ANY, regex=True, na=False).sum()),
            "n_info": int(msgs.str.contains(INFO_ANY, regex=True, na=False).sum()),
            "n_debug": int(msgs.str.contains(DEBUG_ANY, regex=True, na=False).sum()),
            "has_log4j_level": int(msgs.str.contains(LOG4J_LEVEL, regex=True, na=False).sum()),
        }
        rows.append(r)
        if i % 25 == 0 or i == len(log_cases):
            say(f"  ...{i}/{len(log_cases)} done")

    dfr = pd.DataFrame(rows)
    dfr.to_csv("cp1/_warning_per_case.csv", index=False, encoding="utf-8")

    say("")
    say("=" * 78)
    say("TONG HOP TOAN BO 359 CASE")
    say("=" * 78)
    say(f"case quet duoc        : {len(dfr)}")
    say(f"tong log              : {int(dfr['n_logs'].sum()):,}")
    say(f"tong dong chua WARN   : {int(dfr['n_warn'].sum()):,}")
    say(f"tong dong chua ERROR  : {int(dfr['n_error'].sum()):,}")
    say(f"tong dong chua INFO   : {int(dfr['n_info'].sum()):,}")
    say(f"tong dong co log4j lvl: {int(dfr['has_log4j_level'].sum()):,}")
    say("")
    say("THEO HE THONG:")
    agg = dfr.groupby("system").agg(
        cases=("case", "count"),
        logs=("n_logs", "sum"),
        warn=("n_warn", "sum"),
        error=("n_error", "sum"),
        info=("n_info", "sum"),
        log4j=("has_log4j_level", "sum"),
    )
    agg["pct_warn"] = (100.0 * agg["warn"] / agg["logs"]).round(5)
    agg["pct_log4j"] = (100.0 * agg["log4j"] / agg["logs"]).round(2)
    say(agg.to_string())
    say("")
    say("CASE CO NHIEU WARN NHAT (top 25):")
    top = dfr.nlargest(25, "n_warn")[["case", "system", "n_logs", "n_warn", "n_error", "n_info"]]
    say(top.to_string(index=False))
    say("")
    say(f"case co n_warn > 0    : {int((dfr['n_warn'] > 0).sum())}/{len(dfr)}")
    say(f"case co n_warn >= 10  : {int((dfr['n_warn'] >= 10).sum())}/{len(dfr)}")
    say(f"case co n_warn >= 100 : {int((dfr['n_warn'] >= 100).sum())}/{len(dfr)}")
    say("")
    say("WARN phan bo theo he thong (chi case >0):")
    sub = dfr[dfr["n_warn"] > 0]
    if len(sub):
        say(sub.groupby("system")["n_warn"].describe().to_string())

    with open("cp1/_full_scan_out.txt", "w", encoding="utf-8") as f:
        f.write(OUT.getvalue())
    print("\n>> da ghi cp1/_full_scan_out.txt va cp1/_warning_per_case.csv")


if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    main()
