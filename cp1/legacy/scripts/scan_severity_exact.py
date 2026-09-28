#!/usr/bin/env python3
"""
Scan chinh xac severity trong RCAEval logs (khong gioi han mau) + kiem tra
Train Ticket format + LEMMA-RCA severity.

Chay: python cp1/scan_severity_exact.py
Output: cp1/_severity_scan_out.txt
"""

from __future__ import annotations

import io
import re
from collections import Counter

import pandas as pd
from huggingface_hub import hf_hub_download, list_repo_files

REPO = "phamquiluan/RCAEval"
OUT = io.StringIO()


def say(*a):
    line = " ".join(str(x) for x in a)
    print(line)
    OUT.write(line + "\n")


def section(t):
    say("")
    say("=" * 74)
    say(t)
    say("=" * 74)


def load(case):
    p = hf_hub_download(REPO, f"{case}/logs.parquet", repo_type="dataset")
    return pd.read_parquet(p)


def template(msg) -> str:
    if not isinstance(msg, str):
        return ""
    return re.sub(r"[0-9a-fA-F]{8}-[0-9a-fA-F-]{20,}|\b\d+(?:\.\d+)?\b|\"[^\"]*\"|'[^']*'", "<*>", msg)


# keyword xuat hien nhu 1 tu rieng (word boundary), tranh khop "errored" lung tung
PATTERNS = {
    "WARN_token": re.compile(r"\bWARN(?:ING)?\b"),
    "log4j_style": re.compile(r"\b(?:WARN|ERROR|INFO|DEBUG|TRACE|FATAL)\b\s+\d"),
    "bracket_level": re.compile(r"\[\s*(?:WARN|WARNING|ERROR|FATAL|INFO|DEBUG|CRITICAL)\s*\]"),
    "level_eq": re.compile(r"\blevel\s*[=:]\s*[\"']?(?:warn|warning|error|fatal|info|debug|critical)", re.I),
    "severity_eq": re.compile(r"\bseverity\s*[=:]\s*[\"']?(?:warn|warning|error|fatal|info|debug|critical)", re.I),
    "ERROR_token": re.compile(r"\bERROR\b"),
    "FATAL_token": re.compile(r"\bFATAL|CRITICAL\b"),
    "exception": re.compile(r"\b\w*(?:Exception|Error)\b\s*[:(]"),
    "timeout": re.compile(r"\btime[d\s-]*out\b", re.I),
    "failed": re.compile(r"\b(?:failed|failure|unavailable|refused|reset by peer)\b", re.I),
}


def scan_case(case: str) -> dict:
    df = load(case)
    msgs = df["message"].astype("string")
    n = len(df)
    row = {"case": case, "n_logs": n}
    for name, pat in PATTERNS.items():
        cnt = int(msgs.str.contains(pat, regex=True, na=False).sum())
        row[name] = cnt
        row[name + "_pct"] = round(100.0 * cnt / max(n, 1), 4)
    return row


def main():
    files = list_repo_files(REPO, repo_type="dataset")
    log_cases = sorted({f.split("/")[0] for f in files if f.endswith("/logs.parquet")})

    by_sys = {"ob": [], "ss": [], "tt": []}
    for c in log_cases:
        m = re.match(r"re\d(ob|ss|tt)_", c)
        if m:
            by_sys[m.group(1)].append(c)

    section("[A] SEVERITY FORMAT — xem raw message cua ca 3 he thong")
    for sysname, cases in by_sys.items():
        case = cases[0]
        df = load(case)
        say(f"--- {sysname}: {case}  rows={len(df)} ---")
        say(f"  columns: {list(df.columns)}")
        say(f"  dtypes : { {k: str(v) for k, v in df.dtypes.items()} }")
        say(f"  null message: {int(df['message'].isna().sum())}")
        uniq = df["message"].astype('string').dropna().drop_duplicates()
        say(f"  message duy nhat: {len(uniq)}")
        say("  --- 20 message DAI NHAT (thuong chua level) ---")
        dl = df.assign(L=df["message"].astype('string').str.len()).nlargest(20, "L")["message"].astype('string')
        for m in dl:
            say(f"     {m[:200]}")
        say("")

    section("[B] DEM CHINH XAC keyword severity (3 case dau moi he thong, khong gioi han)")
    rows = []
    for sysname, cases in by_sys.items():
        for case in cases[:3]:
            r = scan_case(case)
            rows.append(r)
            say(f"--- {case}  n_logs={r['n_logs']} ---")
            for k in PATTERNS:
                say(f"    {k:14s} {r[k]:8d}  ({r[k + '_pct']}%)")
            say("")
    dfr = pd.DataFrame(rows)
    section("[C] TONG HOP 9 CASE")
    for k in PATTERNS:
        say(f"  {k:14s} tong={int(dfr[k].sum()):9d}   case>0: {int((dfr[k] > 0).sum())}/{len(dfr)}")

    with open("cp1/_severity_scan_out.txt", "w", encoding="utf-8") as f:
        f.write(OUT.getvalue())
    print("\n>> da ghi cp1/_severity_scan_out.txt")


if __name__ == "__main__":
    main()
