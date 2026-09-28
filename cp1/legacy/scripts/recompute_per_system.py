#!/usr/bin/env python3
"""Recompute per-system breakdown tu cp1/_warning_per_case.csv (da co san, khong tai lai)."""
import re
import pandas as pd

df = pd.read_csv("cp1/_warning_per_case.csv")

def sysname(c):
    m = re.match(r"(re\d)(ob|ss|tt)_", c)
    return f"{m.group(1)}-{m.group(2).upper()}" if m else "OTHER"

df["sys"] = df["case"].apply(sysname)
df.to_csv("cp1/_warning_per_case.csv", index=False, encoding="utf-8")

print("SUITE x SYSTEM:")
g = df.groupby("sys").agg(
    cases=("case", "count"),
    logs=("n_logs", "sum"),
    warn=("n_warn", "sum"),
    error=("n_error", "sum"),
    info=("n_info", "sum"),
    log4j=("has_log4j_level", "sum"),
    cases_warn_gt0=("n_warn", lambda s: int((s > 0).sum())),
    warn_max=("n_warn", "max"),
)
g["pct_warn"] = (100 * g["warn"] / g["logs"]).round(5)
print(g.to_string())
print()
print("CHI THEO HE THONG (ob/ss/tt):")
df["sys2"] = df["sys"].str.split("-").str[1]
g2 = df.groupby("sys2").agg(
    cases=("case", "count"),
    logs=("n_logs", "sum"),
    warn=("n_warn", "sum"),
    error=("n_error", "sum"),
    cases_warn_gt0=("n_warn", lambda s: int((s > 0).sum())),
    warn_mean=("n_warn", "mean"),
    warn_max=("n_warn", "max"),
)
g2["pct_warn"] = (100 * g2["warn"] / g2["logs"]).round(5)
print(g2.to_string())
print()
print("TONG:")
print(f"  logs={int(df['n_logs'].sum()):,} warn={int(df['n_warn'].sum()):,} "
      f"error={int(df['n_error'].sum()):,} cases_warn_gt0={int((df['n_warn']>0).sum())}/{len(df)}")
print()
print("TOP 20 CASE NHIEU WARN (da gan nhan dung):")
print(df.nlargest(20, "n_warn")[["case", "sys", "n_logs", "n_warn", "n_error"]].to_string(index=False))
print()
print("PHAN BO n_warn:")
for lo, hi in [(0, 0), (1, 9), (10, 49), (50, 99), (100, 999)]:
    n = int(((df["n_warn"] >= lo) & (df["n_warn"] <= hi)).sum())
    print(f"  {lo:>3}-{hi:<4}: {n:>3} case")
