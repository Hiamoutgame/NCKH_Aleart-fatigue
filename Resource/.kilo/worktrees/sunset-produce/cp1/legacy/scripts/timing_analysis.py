#!/usr/bin/env python3
"""
PHAN TICH QUYET DINH: WARN trong RCAEval roi vao cua so NAO?
  - normal window : [time_start, inject_time)
  - faulty window : [inject_time, time_end]

Va: root_cause.txt chua gi (README noi co "root cause indicator")?

Output: cp1/_timing_out.txt
"""

from __future__ import annotations

import io
import json
import re

import pandas as pd
from datasets import load_dataset
from huggingface_hub import hf_hub_download, list_repo_files

REPO = "phamquiluan/RCAEval"
OUT = io.StringIO()


def say(*a):
    line = " ".join(str(x) for x in a)
    print(line, flush=True)
    OUT.write(line + "\n")


def section(t):
    say("")
    say("=" * 78)
    say(t)
    say("=" * 78)


WARN = re.compile(r"\bWARN(?:ING)?\b")


def main():
    section("[1] XAC NHAN cua so thoi gian tu inject_time")
    cases = load_dataset(REPO, "cases", split="train").to_pandas()
    c0 = cases.iloc[0]
    say(f"case mau: {c0['case']}")
    say(f"  time_start          = {c0['time_start']}")
    say(f"  inject_time         = {c0['inject_time']}")
    say(f"  time_end            = {c0['time_end']}")
    say(f"  n_timesteps         = {c0['n_timesteps']}")
    say(f"  normal_timesteps    = {c0['normal_timesteps']}  <- SO LUONG, khong phai list")
    say(f"  faulty_timesteps    = {c0['faulty_timesteps']}")
    say(f"  inject - start      = {c0['inject_time'] - c0['time_start']}")
    say(f"  end - inject        = {c0['time_end'] - c0['inject_time']}")
    say("")
    say("  => normal_timesteps/faulty_timesteps la SO DIEM (int), KHONG phai danh sach timestamp.")
    say("  => Cua so phai suy tu (time_start, inject_time, time_end).")

    section("[2] WARN roi vao normal hay faulty window?  (cac case Sock Shop nhieu WARN)")
    idx = cases.set_index("case")
    dfcsv = pd.read_csv("cp1/_warning_per_case.csv")
    targets = dfcsv[dfcsv["sys"].str.contains("SS")].nlargest(10, "n_warn")["case"].tolist()
    targets += ["re2ss_carts_cpu_1", "re2tt_ts-auth-service_cpu_2", "re2ob_checkoutservice_cpu_1"]
    targets = [t for t in dict.fromkeys(targets) if t in idx.index]

    rows = []
    for case in targets:
        meta = idx.loc[case]
        p = hf_hub_download(REPO, f"{case}/logs.parquet", repo_type="dataset")
        df = pd.read_parquet(p, columns=["timestamp", "container_name", "message"])
        w = df[df["message"].astype("string").str.contains(WARN, regex=True, na=False)].copy()
        t0, tinj, t1 = int(meta["time_start"]), int(meta["inject_time"]), int(meta["time_end"])
        n_norm = int((w["timestamp"] < tinj).sum())
        n_fault = int((w["timestamp"] >= tinj).sum())
        span = w["timestamp"]
        rows.append({
            "case": case,
            "n_logs": len(df),
            "n_warn": len(w),
            "warn_normal": n_norm,
            "warn_faulty": n_fault,
            "pct_warn_normal": round(100 * n_norm / max(len(w), 1), 1),
            "warn_first_ts": int(span.min()) if len(w) else -1,
            "inject_time": tinj,
            "warn_before_inject_s": int(tinj - span.min()) if len(w) else -1,
            "n_containers_warn": int(w["container_name"].nunique()),
            "root_cause_service": meta["root_cause_service"],
            "warn_containers": ",".join(sorted(w["container_name"].astype(str).unique())[:5]),
        })
    t = pd.DataFrame(rows)
    say(t.to_string(index=False))

    section("[3] root_cause.txt (README: 'root cause indicator e.g. specific log')")
    files = list_repo_files(REPO, repo_type="dataset")
    rcs = sorted({f.split("/")[0] for f in files if f.endswith("/root_cause.txt")})
    say(f"case co root_cause.txt: {len(rcs)} -> {rcs}")
    for case in rcs:
        p = hf_hub_download(REPO, f"{case}/root_cause.txt", repo_type="dataset")
        with open(p, encoding="utf-8", errors="replace") as f:
            content = f.read()
        say(f"--- {case} ---")
        say(f"  {content[:800]}")

    section("[4] Chi tiet 1 case Sock Shop: WARN theo thoi gian")
    case = targets[0]
    meta = idx.loc[case]
    p = hf_hub_download(REPO, f"{case}/logs.parquet", repo_type="dataset")
    df = pd.read_parquet(p)
    w = df[df["message"].astype("string").str.contains(WARN, regex=True, na=False)].copy()
    t0, tinj, t1 = int(meta["time_start"]), int(meta["inject_time"]), int(meta["time_end"])
    say(f"case={case}  root_cause={meta['root_cause_service']}  fault={meta['fault']}")
    say(f"  time_start={t0}  inject={tinj}  time_end={t1}  duration={t1-t0}s")
    say(f"  tong WARN={len(w)}")
    w["rel_s"] = w["timestamp"] - tinj
    say("  WARN theo container:")
    say(w["container_name"].value_counts().to_string())
    say("  WARN theo giay tuong doi so voi inject (top 15 moc):")
    say(w["rel_s"].value_counts().sort_index().head(15).to_string())
    say("  message WARN duy nhat (template rut gon, top 10):")
    tmpl = w["message"].astype("string").str.replace(r"\b\d+(?:\.\d+)?\b|[0-9a-f]{8,}", "<*>", regex=True)
    for m, n in tmpl.value_counts().head(10).items():
        say(f"    {n:5d}  {m[:170]}")

    section("[5] Kiem tra cac dong log KHONG phai WARN nhung la tin hieu fault (trong faulty window)")
    fw = df[(df["timestamp"] >= tinj) & (df["timestamp"] <= t1)]
    nw = df[df["timestamp"] < tinj]
    say(f"  log trong faulty window : {len(fw)}")
    say(f"  log trong normal window : {len(nw)}")
    say("  template xuat hien NHIEU HON trong faulty window (top 12):")
    def tpl(s):
        return s.astype("string").str.replace(r"\b\d+(?:\.\d+)?\b|[0-9a-f]{8,}", "<*>", regex=True)
    a = tpl(fw["message"]).value_counts()
    b = tpl(nw["message"]).value_counts()
    cmp = pd.DataFrame({"faulty": a, "normal": b}).fillna(0)
    cmp["ratio"] = (cmp["faulty"] + 1) / (cmp["normal"] + 1)
    cmp = cmp[cmp["faulty"] >= 5].sort_values("ratio", ascending=False)
    for m, r in cmp.head(12).iterrows():
        say(f"    faulty={int(r['faulty']):6d} normal={int(r['normal']):6d} ratio={r['ratio']:6.1f}  {str(m)[:120]}")

    with open("cp1/_timing_out.txt", "w", encoding="utf-8") as f:
        f.write(OUT.getvalue())
    print("\n>> da ghi cp1/_timing_out.txt")


if __name__ == "__main__":
    main()
