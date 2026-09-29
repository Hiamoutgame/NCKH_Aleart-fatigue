#!/usr/bin/env python3
"""
Lap 2 diem UNVERIFIED trong cp1/data_schema_notes.md:
  #2. 74 dong WARN cua Train Ticket la gi? (co ho WARNING thu 3 khong)
  #3. 375 case khong co log co dung bang suite RE1 khong?
Output: cp1/_gaps_out.txt
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


def norm(msg: str) -> str:
    if not isinstance(msg, str):
        return ""
    s = re.sub(r"^\d{4}-\d{2}-\d{2}[ T][\d:.,]+\s*", "", msg)
    s = re.sub(r"\[[^\]]*\]", "<[]>", s)          # gop moi bracket (thread, trace, logger ctx)
    s = re.sub(r"\b[0-9a-f]{8,}\b", "<HEX>", s)
    s = re.sub(r"\b\d+(?:\.\d+)?\b", "<N>", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def main():
    cases = load_dataset(REPO, "cases", split="train").to_pandas()

    # ------------------------------------------------------------------ #3
    section("[#3] 375 case KHONG co log — co dung bang suite RE1 khong?")
    say("cross-tab suite x has_logs:")
    say(pd.crosstab(cases["suite"], cases["has_logs"], margins=True).to_string())
    say("")
    say("cross-tab dataset x has_logs:")
    say(pd.crosstab(cases["dataset"], cases["has_logs"], margins=True).to_string())
    say("")
    n_nolog = int((~cases["has_logs"]).sum())
    say(f"case khong co log: {n_nolog}")
    say(f"  trong do suite == RE1 : {int((cases.loc[~cases['has_logs'], 'suite'] == 'RE1').sum())}")
    say(f"  trong do suite != RE1 : {int((cases.loc[~cases['has_logs'], 'suite'] != 'RE1').sum())}")
    extra = cases[(~cases["has_logs"]) & (cases["suite"] != "RE1")]
    if len(extra):
        say("  cac case ngoai le (khong co log nhung khong phai RE1):")
        say("  " + extra[["case", "dataset", "suite", "system_name", "fault"]].to_string(index=False).replace("\n", "\n  "))
    say("")
    say("dataset nao THIEU 1 case (RE2-TT chi 89):")
    say(cases.groupby(["dataset", "has_logs"]).size().to_string())

    # ------------------------------------------------------------------ #2
    section("[#2] 74 dong WARN cua Train Ticket la gi?")
    csv = pd.read_csv("cp1/_warning_per_case.csv")
    tt = csv[(csv["sys2"] == "TT") & (csv["n_warn"] > 0)].sort_values("n_warn", ascending=False)
    say(f"so case TT co WARN>0: {len(tt)}, tong WARN: {int(tt['n_warn'].sum())}")

    all_tpl: Counter[str] = Counter()
    all_raw: list[str] = []
    rows = []
    for case in tt["case"]:
        p = hf_hub_download(REPO, f"{case}/logs.parquet", repo_type="dataset")
        df = pd.read_parquet(p, columns=["timestamp", "container_name", "message"])
        w = df[df["message"].astype("string").str.contains(WARN, regex=True, na=False)]
        if not len(w):
            continue
        n = w["message"].map(norm)
        all_tpl.update(n)
        all_raw.extend(w["message"].astype(str).tolist())
        rows.append({
            "case": case,
            "n_warn": len(w),
            "containers": ",".join(sorted(w["container_name"].astype(str).unique())),
            "n_tpl_norm": int(n.nunique()),
        })

    say("")
    say("CAC TEMPLATE WARN DUY NHAT TRONG TOAN BO TRAIN TICKET (sau chuan hoa):")
    for t, c in all_tpl.most_common(30):
        say(f"  {c:4d}  {t[:170]}")
    say("")
    say(f"tong so template WARN duy nhat (TT): {len(all_tpl)}")
    say("")
    say("10 dong WARN RAW dau tien cua TT:")
    for m in all_raw[:10]:
        say(f"  {m[:260]}")
    say("")
    say("case nao phat WARN (container):")
    say(pd.DataFrame(rows).to_string(index=False))

    # ------------------------------------------------------------------
    section("[TONG KET] So ho WARNING tim duoc tren ca dataset")
    say("  Ho 1 (RE3 code-level, SS carts): PageNotFound 'POST' not supported  -> DUPLICATE")
    say("  Ho 2 (RE2 ha tang, SS carts)   : Dropped spans UnknownHostException(zipkin) -> TRANSIENT/UNACTIONABLE")
    say(f"  Ho 3 (TT)                      : {len(all_tpl)} template, xem danh sach tren")

    with open("cp1/_gaps_out.txt", "w", encoding="utf-8") as f:
        f.write(OUT.getvalue())
    print("\n>> da ghi cp1/_gaps_out.txt")


if __name__ == "__main__":
    main()
