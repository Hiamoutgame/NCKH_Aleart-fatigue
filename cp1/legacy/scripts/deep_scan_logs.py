#!/usr/bin/env python3
"""
Deep scan RCAEval logs: tim severity trong text, template, granularity timestamp.

Chay: python cp1/deep_scan_logs.py
Output: cp1/_deep_scan_out.txt

Cau hoi can tra loi:
  Q1. Co cot level/severity khong?  -> khong (xac nhan lai)
  Q2. Severity co NAM TRONG message khong? (WARN/ERROR/FATAL/level=WARN)
  Q3. Message template nao chiem da so? (co dedup duoc khong)
  Q4. Timestamp granularity? (co bi trung 1 giay nhieu khong)
  Q5. Log cua Train Ticket (tt) / Sock Shop (ss) khac gi so voi Online Boutique (ob)?
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


SEV_RE = re.compile(
    r"(?i)(\b(?:TRACE|DEBUG|INFO|NOTICE|WARN(?:ING)?|ERROR|ERR|SEVERE|FATAL|CRITICAL|ALERT|EMERG)\b)"
    r"|(level\s*[=:]\s*\w+)"
    r"|(\[\s*(?:WARN|ERROR|FATAL|INFO|DEBUG)\s*\])"
)
TMPL_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F-]{20,}|\b\d+(?:\.\d+)?\b|\"[^\"]*\"|'[^']*'")


def template(msg: str) -> str:
    return TMPL_RE.sub("<*>", msg)


def main():
    files = list_repo_files(REPO, repo_type="dataset")
    log_cases = sorted({f.split("/")[0] for f in files if f.endswith("/logs.parquet")})
    say(f"tong case co logs.parquet: {len(log_cases)}")

    # chon mau trai deu 3 he thong
    by_sys = {"ob": [], "ss": [], "tt": []}
    for c in log_cases:
        m = re.match(r"re\d(ob|ss|tt)_", c)
        if m:
            by_sys[m.group(1)].append(c)
    say(f"so case log theo he thong: { {k: len(v) for k, v in by_sys.items()} }")

    section("[Q2] SEVERITY CO NAM TRONG MESSAGE KHONG?")
    sev_hits = Counter()
    total_msgs = 0
    per_sys_hit = Counter()
    per_sys_total = Counter()

    for sysname, cases in by_sys.items():
        for case in cases[:6]:
            df = load(case)
            msgs = df["message"].astype(str)
            total_msgs += len(msgs)
            per_sys_total[sysname] += len(msgs)
            hits = msgs[msgs.str.contains(SEV_RE, regex=True, na=False)]
            per_sys_hit[sysname] += len(hits)
            for m in hits.head(2000):
                mm = SEV_RE.search(m)
                if mm:
                    sev_hits[mm.group(0).upper()] += 1
    say(f"tong message quet      : {total_msgs}")
    say(f"message co keyword sev : {sum(sev_hits.values())} (mau toi da 2000/he thong)")
    say(f"phan bo keyword        : {dict(sev_hits.most_common(20))}")
    say("")
    say("theo he thong (ty le %):")
    for s in by_sys:
        t = per_sys_total[s]
        h = per_sys_hit[s]
        say(f"  {s}: {h}/{t} = {100.0 * h / max(t, 1):.3f}%")

    section("[Q3] MESSAGE TEMPLATE — co dedup duoc khong")
    case = by_sys["ob"][0]
    df = load(case)
    say(f"case mau: {case}  rows={len(df)}")
    df = df.copy()
    df["tpl"] = df["message"].astype(str).map(template)
    vc = df["tpl"].value_counts()
    say(f"so template duy nhat   : {len(vc)}")
    say(f"top 15 template:")
    for t, n in vc.head(15).items():
        say(f"  {n:7d}  {t[:110]}")
    say(f"ty le message thuoc top-20 template: {100.0 * vc.head(20).sum() / len(df):.2f}%")

    section("[Q4] TIMESTAMP GRANULARITY")
    ts = df["timestamp"]
    say(f"kieu        : {ts.dtype}")
    say(f"min / max   : {ts.min()} / {ts.max()}")
    say(f"so gia tri  : {ts.nunique()}")
    say(f"span (giay) : {int(ts.max()) - int(ts.min())}")
    dup = ts.value_counts()
    say(f"giay dong log nhat: {dup.index[0]} voi {dup.iloc[0]} dong")
    say(f"trung binh dong/giay: {len(df) / max(ts.nunique(), 1):.1f}")
    deltas = ts.sort_values().diff().dropna()
    say(f"delta giua cac dong lien tiep: median={deltas.median()}  mean={deltas.mean():.2f}  p95={deltas.quantile(0.95)}")

    section("[Q5] SO SANH 3 HE THONG")
    for sysname, cases in by_sys.items():
        if not cases:
            continue
        c = cases[0]
        d = load(c)
        tpl = d["message"].astype(str).map(template)
        say(f"--- {sysname} : {c} ---")
        say(f"  rows          : {len(d)}")
        say(f"  columns       : {list(d.columns)}")
        say(f"  container_name uniq: {d['container_name'].nunique()} -> {sorted(d['container_name'].unique())[:15]}")
        say(f"  template uniq : {tpl.nunique()}")
        say(f"  vi du message :")
        for m in d["message"].astype(str).drop_duplicates().head(8):
            say(f"     {m[:120]}")

    with open("cp1/_deep_scan_out.txt", "w", encoding="utf-8") as f:
        f.write(OUT.getvalue())
    print("\n>> da ghi cp1/_deep_scan_out.txt")


if __name__ == "__main__":
    main()
