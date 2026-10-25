import json

import pandas as pd

import sys
from pathlib import Path

# Make the repository root importable so `src` resolves from any working directory.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.shared.infrastructure.paths import DATASET_PATHS  # noqa: E402

def audit_rcaeval():
    print('=== 1. RCAEVAL AUDIT ===')
    cases_path = DATASET_PATHS["rcaeval"] / "cases.parquet"
    df_cases = pd.read_parquet(cases_path)
    print('cases.parquet shape:', df_cases.shape)
    print('cases.parquet columns and dtypes:')
    for col, dtype in df_cases.dtypes.items():
        print(f'  {col}: {dtype} (non-null: {df_cases[col].count()})')
    print('Sample row of cases.parquet (case with has_logs=True):')
    sample_case = df_cases[df_cases['has_logs']].iloc[0]
    for k, v in sample_case.items():
        print(f'  {k}: {v}')
    logs_path = DATASET_PATHS["rcaeval"] / "re2ss_carts_cpu_1/logs.parquet"
    df_logs = pd.read_parquet(logs_path)
    print('re2ss_carts_cpu_1 logs.parquet shape:', df_logs.shape)
    print('logs.parquet columns and dtypes:')
    for col, dtype in df_logs.dtypes.items():
        print(f'  {col}: {dtype} (non-null: {df_logs[col].count()})')
    print('Distinct containers in re2ss_carts_cpu_1:', df_logs['container_name'].unique().tolist())
    print('Timestamp min/max:', df_logs['timestamp'].min(), df_logs['timestamp'].max())
    print('Sample log messages:')
    for m in df_logs['message'].head(3):
        print('  ', repr(m))

def audit_nezha():
    print('=== 2. NEZHA AUDIT ===')
    fault_list_path = DATASET_PATHS["nezha"] / "fault_list.json"
    with open(fault_list_path) as f: fault_data = json.load(f)
    print('fault_list.json top-level keys:', list(fault_data.keys()))
    first_key = list(fault_data.keys())[0]
    print(f'Sample fault entries under key {first_key}:', json.dumps(fault_data[first_key], indent=2))
    nezha_log_path = DATASET_PATHS["nezha"] / "03_53_log.csv"
    df_nezha = pd.read_csv(nezha_log_path)
    print('Nezha log CSV shape:', df_nezha.shape)
    print('Nezha columns and dtypes:')
    for col, dtype in df_nezha.dtypes.items():
        print(f'  {col}: {dtype} (non-null: {df_nezha[col].count()})')
    print('Unique PodNames:', df_nezha['PodName'].unique().tolist())
    print('TimeUnixNano min/max:', df_nezha['TimeUnixNano'].min(), df_nezha['TimeUnixNano'].max())
    print('Sample Log column values:')
    for l in df_nezha['Log'].head(3):
        print('  ', repr(l))

def audit_lemma():
    print('=== 3. LEMMA-RCA AUDIT ===')
    lemma_log_path = DATASET_PATHS["lemma_rca"] / "sample/app-000174log20210517_132254.json"
    with open(lemma_log_path) as f: lemma_data = json.load(f)
    hits = lemma_data.get('hits', {}).get('hits', [])
    print('LEMMA hits count:', len(hits))
    if hits:
        hit0 = hits[0]
        print('Hit _id:', hit0.get('_id'))
        src = hit0.get('_source', {})
        print('Hit _source fields:', list(src.keys()))
        k8s = src.get('kubernetes', {})
        print('kubernetes fields:', list(k8s.keys()))
        print('pod_name:', k8s.get('pod_name'))
        print('container_name:', k8s.get('container_name'))
        print('@timestamp:', src.get('@timestamp'))
        print('level:', src.get('level'))
        print('message:', repr(src.get('message')))

if __name__ == '__main__':
    audit_rcaeval()
    audit_nezha()
    audit_lemma()