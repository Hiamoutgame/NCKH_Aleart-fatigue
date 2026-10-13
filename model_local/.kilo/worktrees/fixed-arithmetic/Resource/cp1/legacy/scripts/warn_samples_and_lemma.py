#!/usr/bin/env python3
"""
1. Lay vi du WARN THAT trong RCAEval (Sock Shop) — de biet chung la gi.
2. Kiem tra LEMMA-RCA (backup) co cot severity khong.
Output: cp1/_warn_samples_out.txt
"""

from __future__ import annotations

import io
import re

import pandas as pd
from huggingface_hub import HfApi, hf_hub_download, list_repo_files

RCA = "phamquiluan/RCAEval"
LEMMA = "Lemma-RCA-NEC/Product_Review_Original"
OUT = io.StringIO()


def say(*a):
    line = " ".join(str(x) for x in a)
    print(line, flush=True)
    OUT.write(line + "\n")


def section(t):
    say("")
    say("=" * 74)
    say(t)
    say("=" * 74)


WARN = re.compile(r"\bWARN(?:ING)?\b")


def samples():
    section("[1] WARN THAT trong RCAEval (Sock Shop) — chung la gi?")
    dfcsv = pd.read_csv("cp1/_warning_per_case.csv")
    top = dfcsv[dfcsv["sys"].str.contains("SS")].nlargest(4, "n_warn")["case"].tolist()
    say(f"case chon: {top}")
    for case in top:
        p = hf_hub_download(RCA, f"{case}/logs.parquet", repo_type="dataset")
        df = pd.read_parquet(p)
        w = df[df["message"].astype("string").str.contains(WARN, regex=True, na=False)]
        say("")
        say(f"--- {case}: {len(w)} WARN / {len(df)} dong ---")
        say(f"  container co WARN: {dict(w['container_name'].value_counts())}")
        tmpl = w["message"].astype("string").str.replace(
            r"[0-9a-fA-F]{8}-[0-9a-fA-F-]{20,}|\b\d+(?:\.\d+)?\b", "<*>", regex=True)
        say(f"  so template WARN duy nhat: {tmpl.nunique()}")
        say("  top template WARN:")
        for t, n in tmpl.value_counts().head(8).items():
            say(f"    {n:6d}  {t[:150]}")
        say("  3 dong raw:")
        for m in w["message"].astype("string").head(3):
            say(f"    {m[:220]}")


def lemma():
    section("[2] LEMMA-RCA (backup) — co cot severity khong?")
    try:
        fs = list_repo_files(LEMMA, repo_type="dataset")
    except Exception as e:  # noqa: BLE001
        say(f"  KHONG list duoc: {e}")
        return
    say(f"  tong file: {len(fs)}")
    import collections, os
    say(f"  ext: {collections.Counter(os.path.splitext(f)[1] for f in fs)}")
    say("  30 file dau:")
    for f in fs[:30]:
        say(f"    {f}")


def main():
    samples()
    lemma()
    with open("cp1/_warn_samples_out.txt", "w", encoding="utf-8") as f:
        f.write(OUT.getvalue())
    print("\n>> da ghi cp1/_warn_samples_out.txt")


if __name__ == "__main__":
    main()
