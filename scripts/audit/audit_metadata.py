#!/usr/bin/env python3
"""Bounded, read-only dataset audit. Reads data/raw/, writes all outputs to data/audit/.

Run from the repository root (Python 3 with pyarrow and ijson):
  python3 -m pip install --target data/audit/.audit_deps --no-cache-dir -r scripts/audit/audit_requirements.txt
  python3 scripts/audit/audit_metadata.py                 # L0: directories/stat/manifest/footer
  python3 scripts/audit/audit_metadata.py --level l1      # explicit, persisted bounded samples
  # Fresh ledger ONLY after the same external scope has been approved:
  python3 scripts/audit/audit_metadata.py --level l1 --approved-external-schema
  python3 scripts/audit/audit_metadata.py --verify       # output and unchanged-input checks

L1 never uses read_table/read_row_group, and never extracts archives. Only the
first batch (<=200 records) of row group zero is exposed to Python. The Parquet
reader may still fetch/decode compressed column pages containing more records.
CSV/JSON use streaming readers; transport buffers may read ahead, but no more
than the stated number of logical records is materialized/analyzed.

The persisted ledger reserves a read BEFORE opening data. Interrupted reads
cannot be silently retried. Finished reads are reused, including after reruns.
No --force or L2 mode exists. Stop events require a documented human decision.
GB = bytes / 1e9; file_size_mb = bytes / 1e6 (decimal, not MiB).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
AUDIT_DIR = REPO_ROOT / 'data' / 'audit'   # artifacts + optional .audit_deps
sys.path.insert(0, str(AUDIT_DIR / '.audit_deps'))
UNKNOWN = 'chưa xác nhận'
LIMIT = 200
MODALITIES = ('logs', 'metrics', 'traces')
FIELDS = ['source_id', 'system', 'service_in_name', 'fault_type', 'run_id',
          'modality', 'file_size_mb', 'num_rows', 'num_row_groups', 'columns',
          'has_logs', 'has_label_in_cases_parquet', 'case_id', 'relative_path']
TIME_NAMES = {'time', 'timestamp', 'ts', 'datetime', 'starttime', 'endtime',
              'injecttime', 'faulttime', 'anomalytime', 'eventtime'}


class AuditStop(RuntimeError):
    """Do not broaden a read after an unsupported or ambiguous schema."""


def json_default(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode('utf-8', errors='replace')
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, 'as_py'):
        return value.as_py()
    return str(value)


def write_json(path, value):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2,
                               default=json_default), encoding='utf-8')
    temp.replace(path)


def norm(name):
    return re.sub(r'[^a-z0-9]', '', name.lower())


def identify_source(relative):
    parts = relative.parts
    if len(parts) >= 3 and parts[0] == 'huggingface':
        return parts[1]
    if parts[0] == 'nezha':
        return 'nezha'
    return '_workspace_auxiliary'


def classify(relative):
    parts = relative.parts
    lower_parts = [p.lower() for p in parts]
    name = parts[-1].lower()
    suffix = relative.suffix.lower()
    if '.cache' in parts:
        return 'cache', None
    if suffix == '.zip':
        return 'archive', None
    if name in ('cases.parquet', 'inject_time.txt', 'root_cause.txt') or 'fault_list' in name:
        return 'annotation', None
    if name in [m + '.parquet' for m in MODALITIES]:
        return 'telemetry', name.removesuffix('.parquet')
    if suffix in ('.csv', '.json'):
        for folder, modality in [('log', 'logs'), ('metrics', 'metrics'),
                                 ('metric', 'metrics'), ('trace', 'traces')]:
            if folder in lower_parts:
                return 'telemetry', modality
        if name.endswith('_log.csv'):
            return 'telemetry_unmapped', 'logs'
        if 'sample' in lower_parts and 'log' in name:
            return 'telemetry_sample', 'logs'
    return 'auxiliary', None


def parse_case(name):
    parts = name.rsplit('_', 3)
    if len(parts) != 4 or not re.fullmatch(r're\d+(ob|ss|tt)', parts[0]) or not parts[3].isdigit():
        raise AuditStop(f'Unexpected RCAEval case name: {name}')
    system, service, fault, run = parts
    family = re.fullmatch(r're\d+(ob|ss|tt)', system).group(1)
    return dict(case_id=name, source_id='rcaeval', system=system,
                system_family=family, service_in_name=service,
                fault_type=fault, run_id=run)


def footer(path):
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(path)
    try:
        md, schema = pf.metadata, pf.schema_arrow
        result = {'num_rows': md.num_rows, 'num_row_groups': md.num_row_groups,
                  'columns': schema.names,
                  'schema': [{'name': f.name, 'type': str(f.type),
                              'nullable': f.nullable} for f in schema],
                  'timestamp_statistics': {}}
        for rg_index in range(md.num_row_groups):
            rg = md.row_group(rg_index)
            for col_index in range(rg.num_columns):
                col = rg.column(col_index)
                if norm(col.path_in_schema) not in TIME_NAMES:
                    continue
                stats = col.statistics
                item = {'row_group': rg_index, 'rows': rg.num_rows,
                        'physical_type': col.physical_type,
                        'has_min_max': bool(stats and stats.has_min_max)}
                if stats is not None:
                    item['null_count'] = stats.null_count
                if stats is not None and stats.has_min_max:
                    item.update(min=stats.min, max=stats.max)
                result['timestamp_statistics'].setdefault(col.path_in_schema, []).append(item)
        return result
    finally:
        pf.close()


def inventory(root):
    files, errors = [], []
    for current, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not (Path(current) / d).is_symlink())
        for name in sorted(names):
            path = Path(current) / name
            if path.is_symlink():
                continue
            rel = path.relative_to(root)
            st = path.stat()
            category, modality = classify(rel)
            item = dict(relative_path=rel.as_posix(), source_id=identify_source(rel),
                        bytes=st.st_size, mtime_ns=st.st_mtime_ns,
                        category=category, modality=modality)
            if path.suffix == '.parquet' and category != 'cache':
                try:
                    item['parquet'] = footer(path)
                except Exception as exc:
                    errors.append({'path': rel.as_posix(), 'error': str(exc)})
            files.append(item)
    return files, errors


def build_cases(files):
    cases = {}
    for item in files:
        parts = Path(item['relative_path']).parts
        if item['source_id'] != 'rcaeval' or item['category'] == 'cache' or len(parts) < 4:
            continue
        case_id = parts[2]
        case = cases.setdefault(case_id, {**parse_case(case_id), 'files': {}})
        if len(parts) == 4:
            case['files'][parts[3]] = item['relative_path']
    return cases


def l0_summary(files, cases, by_path):
    source = defaultdict(lambda: {'files': 0, 'bytes': 0, 'categories': {}, 'modalities': {}})
    for item in files:
        group = source[item['source_id']]
        group['files'] += 1
        group['bytes'] += item['bytes']
        key = item['category']
        group['categories'][key] = group['categories'].get(key, 0) + item['bytes']
        if item['modality']:
            key = item['modality']
            group['modalities'][key] = group['modalities'].get(key, 0) + item['bytes']
    coverage, fault_counts = {}, Counter()
    fault_log_counts = Counter()
    proxy_all, proxy_logs = Counter(), Counter()
    for case in cases.values():
        system = case['system']
        group = coverage.setdefault(system, {'cases': 0, **{m: 0 for m in MODALITIES},
                                             **{m + '_nonempty': 0 for m in MODALITIES}})
        group['cases'] += 1
        fault_counts[(system, case['fault_type'])] += 1
        proxy_all[(case['system_family'], case['service_in_name'])] += 1
        for modality in MODALITIES:
            path = case['files'].get(modality + '.parquet')
            if path:
                group[modality] += 1
                md = by_path[path].get('parquet', {})
                group[modality + '_nonempty'] += int(md.get('num_rows', 0) > 0)
        if 'logs.parquet' in case['files']:
            proxy_logs[(case['system_family'], case['service_in_name'])] += 1
            if by_path[case['files']['logs.parquet']].get('parquet', {}).get('num_rows', 0) > 0:
                fault_log_counts[(system, case['fault_type'])] += 1
    def counter_rows(counter):
        return [{'system_family': k[0], 'service_in_name': k[1], 'cases': v}
                for k, v in sorted(counter.items())]
    return {'total_bytes': sum(x['bytes'] for x in files), 'sources': dict(source),
            'rcaeval_coverage': coverage,
            'rcaeval_cases_by_system_fault': [dict(system=k[0], fault_type=k[1], cases=v,
                                                  nonempty_log_cases=fault_log_counts[k])
                                             for k, v in sorted(fault_counts.items())],
            'directory_service_proxy_all': counter_rows(proxy_all),
            'directory_service_proxy_with_log_files': counter_rows(proxy_logs),
            'ground_truth_distribution_status': UNKNOWN,
            'ground_truth_distribution_reason': 'Full label index scan not authorized; names are proxies.'}


def write_map(out, cases, by_path, confirmed=None):
    confirmed = confirmed or {}
    with (out / 'dataset_map.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for case_id, case in sorted(cases.items()):
            for modality in MODALITIES:
                path = case['files'].get(modality + '.parquet')
                if not path:
                    continue
                item = by_path[path]
                md = item.get('parquet', {})
                row = {k: case[k] for k in ['source_id', 'system', 'service_in_name',
                                           'fault_type', 'run_id', 'case_id']}
                row.update(modality=modality, relative_path=path,
                           file_size_mb=f"{item['bytes'] / 1e6:.6f}",
                           num_rows=md.get('num_rows', UNKNOWN),
                           num_row_groups=md.get('num_row_groups', UNKNOWN),
                           columns=json.dumps(md['columns'], ensure_ascii=False) if md else UNKNOWN,
                           has_logs=str('logs.parquet' in case['files']).lower(),
                           has_label_in_cases_parquet=confirmed.get(case_id, UNKNOWN))
                writer.writerow(row)


class Budget:
    def __init__(self, root, out):
        self.root, self.path = root, out / 'l1_ledger.json'
        self.data = json.loads(self.path.read_text()) if self.path.exists() else {
            'version': 1, 'limit_per_read': LIMIT, 'selection': None, 'reads': {}, 'stops': []}

    def save(self):
        write_json(self.path, self.data)

    def freeze_selection(self, selection):
        previous = self.data['selection']
        if previous is not None and previous != selection:
            raise AuditStop('Sample selection changed. No new samples may be read without user approval.')
        self.data['selection'] = selection
        self.save()

    def read(self, relative, purpose, reader, limit=LIMIT, key=None):
        if not 0 < limit <= LIMIT:
            raise AuditStop('L1 limit must be between 1 and 200.')
        path = self.root / relative
        st = path.stat()
        fingerprint = [st.st_size, st.st_mtime_ns]
        receipt_key = key or relative
        old = self.data['reads'].get(receipt_key)
        if old:
            if old['fingerprint'] != fingerprint or old['limit'] != limit:
                raise AuditStop(f'Input/budget changed: {relative}')
            if old['status'] != 'complete':
                raise AuditStop(f'Interrupted/failed read needs human review: {relative}')
            return old['result']
        receipt = dict(purpose=purpose, relative_path=relative, fingerprint=fingerprint, limit=limit,
                       status='reserved', reserved_at=datetime.now(timezone.utc).isoformat())
        self.data['reads'][receipt_key] = receipt
        self.save()
        try:
            result = reader(path, limit)
            if result['rows_analyzed'] > limit:
                raise AuditStop('Reader exceeded its record budget.')
            receipt.update(status='complete', result=result)
        except Exception as exc:
            receipt.update(status='stopped', error=str(exc))
            self.data['stops'].append({'path': relative, 'reason': str(exc)})
            self.save()
            raise AuditStop(f'{relative}: {exc}') from exc
        self.save()
        return result


def bounded_parquet(path, limit):
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(path)
    try:
        if pf.metadata.num_row_groups == 0:
            return [], pf.schema_arrow
        batches = pf.iter_batches(batch_size=limit, row_groups=[0], use_threads=False)
        batch = next(batches, None)
        return ([] if batch is None else batch.to_pylist()), pf.schema_arrow
    finally:
        pf.close()


def prefix_index(path, limit):
    rows, schema = bounded_parquet(path, limit)
    return {'rows_analyzed': len(rows), 'columns': schema.names, 'rows': rows}


def bounded_csv(path, limit):
    from itertools import islice
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames
        if not columns or len(columns) != len(set(columns)):
            raise AuditStop('Missing or duplicate CSV header.')
        rows = list(islice(reader, limit))
    if any(None in row for row in rows):
        raise AuditStop('CSV records do not match header width.')
    return rows, columns


def bounded_json(path, limit):
    import ijson
    from itertools import islice
    # Inspect the container through a separate parser, never a complete json.load.
    with path.open('rb') as f:
        events = ijson.parse(f)
        first = next(events, None)
    if first is None:
        raise AuditStop('Empty JSON.')
    if first[1] == 'start_array':
        with path.open('rb') as f:
            rows = list(islice(ijson.items(f, 'item'), limit))
        if any(not isinstance(row, dict) for row in rows):
            raise AuditStop('JSON array contains non-object records.')
        columns = sorted({key for row in rows for key in row})
        return rows, columns
    raise AuditStop('JSON root is not an array of records; streaming path needs human confirmation.')


def profile_rows(rows, columns, types=None):
    times = [c for c in columns if norm(c) in TIME_NAMES]
    content = [c for c in columns if norm(c) in {'message', 'log', 'body', 'content', 'logmessage', 'msg'}]
    identities = [c for c in columns if any(x in norm(c) for x in ['service', 'container', 'pod', 'host'])]
    severity = [c for c in columns if norm(c) in {'severity', 'severitytext', 'severitynumber', 'level', 'loglevel'}]
    time_samples = {}
    for c in times:
        values = [r[c] for r in rows if r.get(c) is not None]
        if values:
            try:
                lo, hi = min(values), max(values)
            except TypeError:
                lo, hi = UNKNOWN, UNKNOWN
            time_samples[c] = {'min': lo, 'max': hi, 'first': values[:3],
                               'scope': 'sample prefix only',
                               'arrow_type': (types or {}).get(c, UNKNOWN)}
    # Keep only three short examples; never serialize a complete telemetry sample.
    examples = [{c: str(row.get(c))[:400] for c in columns[:16]} for row in rows[:3]]
    text = '\n'.join(str(row.get(c, '')) for row in rows for c in content)
    markers = {term: len(re.findall(term, text, re.I)) for term in
               ['root[_ -]?cause', 'fault[_ -]?inject', 'chaos', 'ground[_ -]?truth']}
    tokens = Counter(re.findall(r'\b(?:TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)\b', text))
    return {'rows_analyzed': len(rows), 'columns': columns, 'types': types or {},
            'timestamp_candidates': time_samples, 'content_candidates': content,
            'identity_candidates': identities, 'severity_columns': severity,
            'severity_tokens_in_content': dict(tokens), 'marker_counts_in_content': markers,
            'examples': examples,
            'timezone_status': UNKNOWN,
            'timezone_reason': 'Must be established from explicit Arrow type/offset or source evidence.'}


def profile_parquet(path, limit):
    rows, schema = bounded_parquet(path, limit)
    return profile_rows(rows, schema.names, {f.name: str(f.type) for f in schema})


def profile_csv(path, limit):
    rows, columns = bounded_csv(path, limit)
    return profile_rows(rows, columns)


def profile_json(path, limit):
    rows, columns = bounded_json(path, limit)
    return profile_rows(rows, columns)


def nezha_index_prefix(path, limit):
    """Approved shape: hour -> array of fault annotations. Never load an hour."""
    import ijson
    rows, hours = [], []
    with path.open('rb') as f:
        events = ijson.parse(f)
        if next(events, None) != ('', 'start_map', None):
            raise AuditStop('Nezha annotation root differs from approved hourly object.')
        for prefix, event, value in events:
            if event == 'start_map' and re.fullmatch(r'\d{2}\.item', prefix):
                builder = ijson.ObjectBuilder()
                builder.event(event, value)
                depth = 1
                for _, inner_event, inner_value in events:
                    builder.event(inner_event, inner_value)
                    depth += int(inner_event in ('start_map', 'start_array'))
                    depth -= int(inner_event in ('end_map', 'end_array'))
                    if depth == 0:
                        break
                if depth != 0:
                    raise AuditStop('Incomplete Nezha annotation object.')
                rows.append(builder.value)
                hours.append(prefix.split('.')[0])
                if len(rows) == limit:
                    break
    required = {'inject_time', 'inject_timestamp', 'inject_pod', 'inject_type'}
    if not rows or any(not required.issubset(row) or any(not isinstance(row[k], str) for k in required)
                       for row in rows):
        raise AuditStop('Nezha hourly annotation fields differ from approved structural probe.')
    return {'rows_analyzed': len(rows), 'columns': sorted({k for row in rows for k in row}),
            'rows': rows, 'partition_hours': hours,
            'scope': 'bounded prefix of one dated annotation; other dates not inspected'}


def lemma_partition_profile(path, limit):
    """Approved Elasticsearch export, hits.hits.item, one partition only."""
    import ijson
    from itertools import islice
    with path.open('rb') as f:
        hits = list(islice(ijson.items(f, 'hits.hits.item'), limit))
    if not hits or any(not isinstance(hit.get('_source'), dict) for hit in hits):
        raise AuditStop('LEMMA Elasticsearch hits lack object-valued _source.')
    rows = [hit['_source'] for hit in hits]
    profile = profile_rows(rows, sorted({key for row in rows for key in row}))
    profile.update(json_record_path='hits.hits.item._source', unit='partition, not fault case',
                   hit_identity_examples=[{k: hit.get(k) for k in ['_index', '_type', '_id']} for hit in hits[:3]])
    return profile


def read_inject(path, limit):
    # One annotation value attached to an already selected case, not telemetry.
    with path.open('r', encoding='utf-8') as f:
        value = f.readline(256).strip()
        if f.read(1):
            raise AuditStop('inject_time.txt has unexpected additional content.')
    return {'rows_analyzed': 1, 'value': value,
            'unit': UNKNOWN, 'timezone': UNKNOWN,
            'reason': 'Plain integer text alone does not prove epoch unit or timezone.'}


def choose_samples(cases, by_path):
    groups = defaultdict(list)
    for case in cases.values():
        groups[(case['source_id'], case['system'], case['fault_type'])].append(case)
    chosen = []
    for group in sorted(groups):
        def preference(case):
            names = case['files']
            has_log = 'logs.parquet' in names and by_path[names['logs.parquet']].get('parquet', {}).get('num_rows', 0) > 0
            count = sum(m + '.parquet' in names for m in MODALITIES)
            return (not has_log, -count, case['case_id'])
        chosen.append(min(groups[group], key=preference)['case_id'])
    return chosen


def check_unchanged(root, files):
    changes = []
    for item in files:
        path = root / item['relative_path']
        try:
            st = path.stat()
            if [st.st_size, st.st_mtime_ns] != [item['bytes'], item['mtime_ns']]:
                changes.append(item['relative_path'])
        except OSError:
            changes.append(item['relative_path'])
    expected = {item['relative_path'] for item in files}
    current_paths = set()
    for current, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if not (Path(current) / d).is_symlink()]
        for name in names:
            path = Path(current) / name
            if not path.is_symlink():
                current_paths.add(path.relative_to(root).as_posix())
    additions = sorted(current_paths - expected)
    return {'unchanged_size_mtime': not changes and not additions, 'changed_paths': changes,
            'added_paths': additions,
            'method': 'stat only, no content hashing or telemetry scan'}


def verify(out, root):
    metadata = json.loads((out / 'audit_metadata.json').read_text())
    files = metadata['files']
    by_path = {x['relative_path']: x for x in files}
    cases = build_cases(files)
    rows = list(csv.DictReader((out / 'dataset_map.csv').open(encoding='utf-8')))
    assert len(rows) == sum(sum(m + '.parquet' in c['files'] for m in MODALITIES) for c in cases.values())
    assert len({(r['source_id'], r['case_id'], r['modality']) for r in rows}) == len(rows)
    for row in rows:
        assert int(row['num_rows']) == by_path[row['relative_path']]['parquet']['num_rows']
    summary = json.loads((out / 'audit_summary.json').read_text())
    assert summary['total_bytes'] == sum(s['bytes'] for s in summary['sources'].values())
    ledger_path = out / 'l1_ledger.json'
    if ledger_path.exists():
        ledger = json.loads(ledger_path.read_text())
        selected = [cases[key] for key in ledger['selection']['rcaeval']]
        assert len({(c['source_id'], c['system'], c['fault_type']) for c in selected}) == len(selected)
        for receipt in ledger['reads'].values():
            assert receipt['limit'] <= LIMIT
            if receipt['status'] == 'complete':
                assert receipt['result']['rows_analyzed'] <= receipt['limit']
        external = ledger.get('external_selection', {}).get('nezha', [])
        assert len({(x['system'], x['fault_type']) for x in external}) == len(external)
    baseline_path = out / 'raw_stat_baseline.json'
    baseline = json.loads(baseline_path.read_text()) if baseline_path.exists() else {'files': files}
    result = {'verified_map_rows': len(rows), 'verified_parquet_files': sum('parquet' in x for x in files),
              **check_unchanged(root, baseline['files'])}
    assert result['unchanged_size_mtime'], result['changed_paths']
    write_json(out / 'verification.json', result)
    print(json.dumps(result, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--level', choices=['l0', 'l1'], default='l0')
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--approved-external-schema', action='store_true',
                        help='Record explicit human approval for bounded Nezha object + one LEMMA partition; no extra row budget.')
    args = parser.parse_args()
    root, out = REPO_ROOT / 'data' / 'raw', AUDIT_DIR
    if args.verify:
        verify(out, root)
        return
    try:
        import pyarrow
    except ImportError:
        parser.error('Install pyarrow into data/audit/.audit_deps; see script header.')
    files, errors = inventory(root)
    baseline_path = out / 'raw_stat_baseline.json'
    if baseline_path.exists():
        baseline = json.loads(baseline_path.read_text())
        check = check_unchanged(root, baseline['files'])
        if not check['unchanged_size_mtime']:
            raise AuditStop(f'Raw input changed since baseline: {check}')
    else:
        observations = [{k: f[k] for k in ['relative_path', 'bytes', 'mtime_ns']} for f in files]
        signature = hashlib.sha256(json.dumps(observations, sort_keys=True).encode()).hexdigest()
        write_json(baseline_path, {'files': observations, 'stat_observations_sha256': signature,
                                   'note': 'Digest of path/size/mtime observations only; no raw content hashing.'})
    cases = build_cases(files)
    by_path = {x['relative_path']: x for x in files}
    with (root / 'manifest.csv').open(newline='', encoding='utf-8-sig') as f:
        manifest = list(csv.DictReader(f))
    write_json(out / 'audit_metadata.json', {'level': 'L0', 'pyarrow_version': pyarrow.__version__,
                                           'manifest': manifest, 'files': files, 'errors': errors})
    summary = l0_summary(files, cases, by_path)
    write_json(out / 'audit_summary.json', summary)
    write_map(out, cases, by_path)
    print(json.dumps({'level': 'L0', 'files': len(files), 'parquet_files': sum('parquet' in x for x in files),
                      'cases': len(cases), 'bytes': summary['total_bytes'], 'errors': errors}, ensure_ascii=False))
    if errors:
        raise AuditStop('Unreadable Parquet metadata. L1 prohibited pending review.')
    try:
        if args.level == 'l1':
            if args.approved_external_schema:
                budget = Budget(root, out)
                budget.data.setdefault('approvals', {})['external_schema_2026_10_20'] = {
                    'nezha': 'Explicit CLI approval: hourly object annotations <=200 records, one case per fault.',
                    'lemma_rca': 'Explicit CLI approval: one <=200-record Elasticsearch log partition, not a case.'}
                budget.save()
            run_l1(root, out, files, cases, by_path, summary)
    finally:
        build_deliverables(out, files, cases, by_path, summary)


def run_l1(root, out, files, cases, by_path, summary):
    budget = Budget(root, out)
    selection = {'rcaeval': choose_samples(cases, by_path),
                 'external_policy': 'annotation prefix first; no telemetry until case mapping is confirmed'}
    budget.freeze_selection(selection)
    result = {'selected_rcaeval_cases': selection['rcaeval'], 'rcaeval': {},
              'index': {}, 'external': {}, 'stops': []}
    confirmed = {}
    try:
        index_rel = 'huggingface/rcaeval/cases.parquet'
        index = budget.read(index_rel, 'single label-index prefix', prefix_index)
        required = {'case', 'root_cause_service', 'inject_time'}
        if not required.issubset(index['columns']):
            raise AuditStop(f'Unexpected RCAEval index schema; missing {sorted(required - set(index["columns"]))}')
        labels = []
        for record in index['rows']:
            case_id = record['case']
            if case_id not in cases:
                raise AuditStop(f'Index references a case not in directory inventory: {case_id}')
            label = record['root_cause_service']
            has_label = isinstance(label, str) and bool(label.strip())
            confirmed[case_id] = str(has_label).lower()
            matches = label == cases[case_id]['service_in_name'] if has_label else None
            labels.append({'case_id': case_id, 'root_cause_service': label,
                           'matches_directory_service': matches,
                           'inject_time': record['inject_time'],
                           'has_log_file': 'logs.parquet' in cases[case_id]['files']})
            if has_label and not matches:
                raise AuditStop(f'Root-cause label does not match directory service: {case_id}')
        counts = Counter(x['root_cause_service'] for x in labels if x['root_cause_service'])
        result['index'] = {'path': index_rel, 'rows_analyzed': index['rows_analyzed'],
                           'columns': index['columns'], 'labels': labels,
                           'root_cause_column': 'root_cause_service', 'inject_column': 'inject_time',
                           'label_counts_in_prefix': dict(counts),
                           'majority_fraction_in_prefix': max(counts.values()) / sum(counts.values()) if counts else None,
                           'confirmed_ranking_cases_in_prefix': sum(x['has_log_file'] and bool(x['root_cause_service']) for x in labels),
                           'scope': 'first <=200 index rows; not representative or full ground truth'}
        index_by_case = {record['case']: record for record in index['rows']}
        for case_id in selection['rcaeval']:
            case = cases[case_id]
            profiles = {}
            result['rcaeval'][case_id] = profiles
            for modality in MODALITIES:
                rel = case['files'].get(modality + '.parquet')
                if not rel:
                    continue
                profile = budget.read(rel, f'{case_id}: {modality}', profile_parquet)
                profiles[modality] = profile
                required_columns = {'logs': {'timestamp', 'container_name', 'message'},
                                    'metrics': {'time'},
                                    'traces': {'traceID', 'spanID', 'serviceName', 'parentSpanID'}}[modality]
                if not required_columns.issubset(profile['columns']):
                    raise AuditStop(f'Unexpected {modality} schema in {rel}')
            inject_rel = case['files'].get('inject_time.txt')
            if inject_rel:
                inject = budget.read(inject_rel, f'{case_id}: inject annotation', read_inject, limit=1)
                profiles['inject_annotation'] = inject
                record = index_by_case.get(case_id)
                if record:
                    profiles['inject_index_agrees_with_text'] = str(record['inject_time']) == inject['value']
                    if not profiles['inject_index_agrees_with_text']:
                        raise AuditStop(f'Inject annotation/index mismatch: {case_id}')
            profiles['label_in_prefix'] = confirmed.get(case_id, UNKNOWN)
        # The dated Nezha annotation is canonical for this audit. Do not read the
        # standalone fault_list.json as an additional, possibly duplicate index.
        nezha_indices = sorted(x['relative_path'] for x in files
                               if x['source_id'] == 'nezha' and 'fault_list' in x['relative_path']
                               and len(Path(x['relative_path']).parts) == 3)
        if nezha_indices:
            rel = nezha_indices[0]
            approval = budget.data.get('approvals', {}).get('external_schema_2026_10_20')
            if not approval:
                raise AuditStop('External object schema and partition sampling require user confirmation.')
            annotation = budget.read(rel, 'user-approved hourly annotation prefix', nezha_index_prefix)
            result['external']['nezha_annotation_prefix'] = {'path': rel, **annotation}
            selected = {}
            for record in sorted(annotation['rows'], key=lambda r: r['inject_time']):
                selected.setdefault(record['inject_type'], record)
            external_selection = []
            date_path = Path(rel).parent.as_posix()
            for fault, record in sorted(selected.items()):
                minute = record['inject_time'][11:16].replace(':', '_')
                paths = {m: f'{date_path}/{folder}/{minute}_{suffix}.csv'
                         for m, folder, suffix in [('logs', 'log', 'log'), ('traces', 'trace', 'trace')]}
                if any(path not in by_path for path in paths.values()):
                    raise AuditStop(f'No exact-minute Nezha log/trace match for {record["inject_time"]}')
                external_selection.append({'fault_type': fault, 'system': UNKNOWN,
                                           'annotation': record, 'paths': paths})
            lemma_path = sorted(x['relative_path'] for x in files if x['source_id'] == 'lemma_rca'
                                and x['category'] == 'telemetry' and x['modality'] == 'logs')[0]
            external_policy = {'nezha': external_selection, 'lemma_partition': lemma_path}
            previous = budget.data.get('external_selection')
            if previous is not None and previous != external_policy:
                raise AuditStop('External sample selection changed; user review required.')
            budget.data['external_selection'] = external_policy
            budget.save()
            result['external']['nezha'] = []
            for chosen in external_selection:
                item = {**chosen, 'profiles': {}}
                result['external']['nezha'].append(item)
                for modality, path in chosen['paths'].items():
                    item['profiles'][modality] = budget.read(path, f'Nezha {chosen["fault_type"]}: {modality}', profile_csv)
                item['case_window_status'] = UNKNOWN
                item['service_label_status'] = UNKNOWN
                item['reason'] = 'Exact injection-minute file, not a verified complete fault window; inject_pod is a pod label.'
            result['external']['lemma_partition'] = {
                'path': lemma_path,
                **budget.read(lemma_path, 'user-approved single partition schema sample', lemma_partition_profile)}
        result['external']['eligibility'] = {
            'confirmed_ranking_cases': 0, 'confirmed_full_case_grouping_cases': 0,
            'reason': 'Nezha has pod labels but no verified service mapping/full window; LEMMA has no inspected fault labels.'}
    except AuditStop as exc:
        result['stops'].append(str(exc))
        write_json(out / 'l1_evidence.json', result)
        write_map(out, cases, by_path, confirmed)
        write_json(out / 'raw_readonly_check.json', check_unchanged(root, files))
        raise
    write_json(out / 'l1_evidence.json', result)
    write_map(out, cases, by_path, confirmed)
    write_json(out / 'raw_readonly_check.json', check_unchanged(root, files))
    print(json.dumps({'level': 'L1', 'rcaeval_sample_cases': len(result['rcaeval']),
                      'label_prefix_rows': result['index'].get('rows_analyzed'),
                      'external_nezha_samples': len(result['external'].get('nezha', [])),
                      'lemma_partitions': int('lemma_partition' in result['external']),
                      'reads_in_ledger': len(budget.data['reads'])}, ensure_ascii=False))


def build_deliverables(out, files, cases, by_path, summary):
    """Derive reports exclusively from L0 output and already cached L1 evidence."""
    evidence_path = out / 'l1_evidence.json'
    evidence = json.loads(evidence_path.read_text()) if evidence_path.exists() else {}
    ledger_path = out / 'l1_ledger.json'
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {'reads': {}}
    for key, receipt in ledger['reads'].items():
        path = receipt.get('relative_path', key.split('#')[0])
        item = by_path.get(path)
        if not item or receipt['fingerprint'] != [item['bytes'], item['mtime_ns']]:
            raise AuditStop(f'Cached L1 evidence is stale: {path}')
    labels = evidence.get('index', {}).get('labels', [])
    confirmed = {row['case_id']: str(isinstance(row['root_cause_service'], str)
                                     and bool(row['root_cause_service'].strip())).lower() for row in labels}
    write_map(out, cases, by_path, confirmed)

    log_cases = sorted(case_id for case_id, case in cases.items()
                       if 'logs.parquet' in case['files']
                       and by_path[case['files']['logs.parquet']]['parquet']['num_rows'] > 0)
    def modality_bytes(ids, modalities):
        return sum(by_path[cases[c]['files'][m + '.parquet']]['bytes']
                   for c in ids for m in modalities if m + '.parquet' in cases[c]['files'])
    selected = evidence.get('selected_rcaeval_cases', [])
    dev = []
    for family in ['ob', 'ss', 'tt']:
        options = sorted((c for c in selected if c in log_cases and cases[c]['system_family'] == family),
                         key=lambda c: (cases[c]['fault_type'], c))
        dev.extend(options[:2])
    def group(case_id):
        c = cases[case_id]
        return (c['system_family'], c['service_in_name'], c['fault_type'])
    excluded_groups = {group(c) for c in dev}
    dev_group_cases = sorted(c for c in cases if group(c) in excluded_groups)
    ranking = sorted(row['case_id'] for row in labels
                     if row['root_cause_service'] and row['matches_directory_service'] and row['case_id'] in log_cases)
    candidates = [c for c in log_cases if c not in ranking]
    traces = sorted(c for c in cases if 'traces.parquet' in cases[c]['files'])
    metrics = sorted(c for c in cases if 'metrics.parquet' in cases[c]['files'])
    deferred = sorted(set(cases) - set(log_cases))
    source_info = summary['sources']
    source_bytes = {source: x['bytes'] for source, x in source_info.items()}
    slices = {
        'units': {'bytes': 'physical file sizes, decimal GB', 'counts': 'distinct known cases only'},
        'dev': {'case_ids': dev, 'cases': len(dev), 'log_bytes': modality_bytes(dev, ['logs']),
                'all_modalities_bytes': modality_bytes(dev, MODALITIES),
                'evaluation_excluded_case_ids_by_repeat_group': dev_group_cases},
        'grouping': {'source_id': 'rcaeval', 'case_ids': log_cases, 'confirmed_cases': len(log_cases),
                     'log_bytes': modality_bytes(log_cases, ['logs']),
                     'external_partitions_reserved_from_development': ['lemma_rca', 'nezha']},
        'ranking': {'confirmed_case_ids': ranking, 'confirmed_cases': len(ranking),
                    'confirmed_log_bytes': modality_bytes(ranking, ['logs']),
                    'candidate_case_ids': candidates, 'candidate_cases': len(candidates),
                    'candidate_log_bytes': modality_bytes(candidates, ['logs']),
                    'reason': 'Only labels in the authorized <=200-row index prefix were checked.'},
        'external_test': {'source_ids': ['lemma_rca', 'nezha'], 'confirmed_eligible_cases': 0,
                          'available_physical_bytes': sum(source_bytes.get(s, 0) for s in ['lemma_rca', 'nezha']),
                          'usable_case_bytes': UNKNOWN,
                          'reason': 'Unverified service labels/case boundaries; different schemas need adapters.'},
        'dependency': {'source_id': 'rcaeval', 'trace_case_ids': traces, 'trace_cases': len(traces),
                       'trace_bytes': modality_bytes(traces, ['traces']),
                       'metric_case_ids': metrics, 'metric_cases': len(metrics),
                       'metric_bytes': modality_bytes(metrics, ['metrics']),
                       'action': 'proposal only; no graph or inventory extracted in bulk'},
        'deferred': {'rcaeval_case_ids_without_nonempty_logs': deferred, 'rcaeval_cases': len(deferred),
                     'rcaeval_telemetry_bytes': modality_bytes(deferred, MODALITIES),
                     'external_case_counts': UNKNOWN,
                     'fixtures': 'tests/fixtures absent from current workspace'},
        'split_protocol': {'seed': 42, 'repeat_group': ['system_family', 'service_in_name', 'fault_type'],
                           'A': {'ratios': [0.6, 0.2, 0.2], 'strata': ['system', 'fault_type']},
                           'B': {'test': 'leave one observed fault code out', 'train_val': [0.8, 0.2]},
                           'C': {'test': 'leave one entire family ob/ss/tt out across all versions', 'train_val': [0.8, 0.2]},
                           'status': 'protocol only; no train/test assignment or model training'},
        'raw_log_id_contract': {
            'parquet': ['source_id', 'source_revision_or_snapshot', 'relative_path', 'row_group_index', 'row_offset'],
            'csv': ['source_id', 'source_revision_or_snapshot', 'relative_path', 'logical_record_offset_excluding_header'],
            'json': ['source_id', 'source_revision_or_snapshot', 'relative_path', 'json_record_path', 'record_offset'],
            'groups': 'every input ID belongs to exactly one group; retain all IDs and permit raw retrieval',
            'status': 'future parser acceptance criteria; not measured by metadata audit'}}
    strata = defaultdict(set)
    for case_id in log_cases:
        if group(case_id) not in excluded_groups:
            case = cases[case_id]
            strata[(case['system'], case['fault_type'])].add(group(case_id))
    slices['split_protocol']['A']['strata_with_fewer_than_three_repeat_groups_after_dev'] = [
        {'system': key[0], 'fault_type': key[1], 'repeat_groups': len(groups)}
        for key, groups in sorted(strata.items()) if len(groups) < 3]
    write_json(out / 'slice_manifest.json', slices)

    totals = defaultdict(lambda: {'files': 0, 'rows': 0, 'bytes': 0, 'empty_files': 0})
    all_bounds, sampled_comparisons = [], []
    for case_id in log_cases:
        item = by_path[cases[case_id]['files']['logs.parquet']]
        md = item['parquet']
        system = cases[case_id]['system']
        entry = totals[system]
        entry['files'] += 1
        entry['rows'] += md['num_rows']
        entry['bytes'] += item['bytes']
        stats = md['timestamp_statistics'].get('timestamp', [])
        if len(stats) == md['num_row_groups'] and all(s['has_min_max'] and s['null_count'] == 0 for s in stats):
            lo, hi = min(s['min'] for s in stats), max(s['max'] for s in stats)
            all_bounds.append({'case_id': case_id, 'min': lo, 'max': hi, 'duration_ticks': hi - lo,
                               'scope': 'whole file, footer min/max', 'unit': UNKNOWN})
            p = evidence.get('rcaeval', {}).get(case_id, {})
            annotation = p.get('inject_annotation')
            if annotation and annotation['value'].isdigit():
                injection = int(annotation['value'])
                sampled_comparisons.append({'case_id': case_id, 'log_min': lo, 'log_max': hi,
                                            'inject_value': injection,
                                            'numeric_min_before_inject': lo < injection,
                                            'numeric_max_after_inject': hi > injection,
                                            'unit_status': 'comparison in raw numeric domain; seconds inferred, timezone unconfirmed'})
    log_profiles = [p['logs'] for p in evidence.get('rcaeval', {}).values() if 'logs' in p]
    markers = {case_id: p['logs']['marker_counts_in_content']
               for case_id, p in evidence.get('rcaeval', {}).items()
               if 'logs' in p and any(p['logs']['marker_counts_in_content'].values())}
    rows_read = sum(r.get('result', {}).get('rows_analyzed', 0) for r in ledger['reads'].values())
    proxy_by_family = {}
    for family in ['ob', 'ss', 'tt']:
        counts = {x['service_in_name']: x['cases'] for x in summary['directory_service_proxy_with_log_files']
                  if x['system_family'] == family}
        if counts:
            proxy_by_family[family] = {'service_counts_from_directory_only': counts,
                                      'majority_service': min(counts, key=lambda k: (-counts[k], k)),
                                      'majority_fraction': max(counts.values()) / sum(counts.values()),
                                      'scope': 'filename proxy, NOT ground truth or test accuracy'}
    prefix_records = ledger['reads'].get('huggingface/rcaeval/cases.parquet', {}).get('result', {}).get('rows', [])
    index_alignment = {
        'rows': len(prefix_records),
        'fault_matches_directory': sum(r.get('fault') == cases[r['case']]['fault_type'] for r in prefix_records),
        'repetition_matches_directory': sum(str(r.get('repetition')) == cases[r['case']]['run_id'] for r in prefix_records),
        'system_matches_family': sum(r.get('system') == cases[r['case']]['system_family'] for r in prefix_records),
        'seconds_supported_by_duration': sum(r.get('time_end', 0) - r.get('time_start', 0) == r.get('duration_minutes', -1) * 60
                                            for r in prefix_records),
        'seconds_supported_within_rounding_3s': sum(abs(r.get('time_end', 0) - r.get('time_start', 0) - r.get('duration_minutes', -1) * 60) <= 3
                                                   for r in prefix_records),
        'inject_outside_index_metric_window': [
            {k: r[k] for k in ['case', 'inject_time', 'time_start', 'time_end']}
            for r in prefix_records if not r['time_start'] <= r['inject_time'] <= r['time_end']]}
    derived = {'rcaeval_logs_by_system': dict(totals), 'log_bounds_from_footer': all_bounds,
               'sampled_inject_comparisons': sampled_comparisons,
               'root_cause_token_candidates_not_proven_label_leakage': markers,
               'sampled_log_rows': sum(p['rows_analyzed'] for p in log_profiles),
               'l1_logical_rows_materialized': rows_read,
               'l1_reads_completed': sum(r['status'] == 'complete' for r in ledger['reads'].values()),
               'index': evidence.get('index', {}),
               'index_alignment_in_prefix': index_alignment,
               'directory_proxy_distribution_with_logs': proxy_by_family,
               'timestamp_interpretation': {
                   'rcaeval': 'int64 has no declared unit/timezone. Seconds supported by time_end-time_start = duration_minutes*60 in inspected index, and trace startTimeMillis scale. Log timezone remains unconfirmed.',
                   'nezha': 'Timestamp includes Z; TimeUnixNano and StartTimeUnixNano explicitly name nanoseconds. Annotation inject_time agrees with inject_timestamp interpreted as Unix seconds in inspected records.',
                   'lemma': '@timestamp explicitly contains +00:00 in saved sample; whole partition bounds unavailable. Filename date is not event date.'},
               'map_conventions': {'system': 'directory code, e.g. re2ob; family ob/ss/tt is recorded separately for C',
                                   'has_logs': 'file existence, not row count; num_rows separately establishes nonempty Parquet',
                                   'unknown_label': 'case not checked within authorized label prefix; not a negative label',
                                   'unmapped_sources': 'external non-case files recorded separately, not fake dataset_map cases'}}
    write_json(out / 'audit_findings.json', derived)

    # External partitions remain separate from the case-level dataset_map.
    profiles = {}
    ext = evidence.get('external', {})
    if 'lemma_partition' in ext:
        profiles[ext['lemma_partition']['path']] = ext['lemma_partition']
    for chosen in ext.get('nezha', []):
        profiles.update({chosen['paths'][m]: p for m, p in chosen['profiles'].items()})
    with (out / 'unmapped_inventory.csv').open('w', encoding='utf-8', newline='') as f:
        fields = ['source_id', 'relative_path', 'category', 'modality_hint', 'bytes',
                  'case_status', 'num_rows', 'sample_rows', 'sample_columns', 'reason']
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for item in files:
            if item['source_id'] in ('rcaeval', '_workspace_auxiliary'):
                continue
            p = profiles.get(item['relative_path'], {})
            writer.writerow({'source_id': item['source_id'], 'relative_path': item['relative_path'],
                             'category': item['category'], 'modality_hint': item['modality'] or UNKNOWN,
                             'bytes': item['bytes'], 'case_status': UNKNOWN, 'num_rows': UNKNOWN,
                             'sample_rows': p.get('rows_analyzed', 0),
                             'sample_columns': json.dumps(p.get('columns', []), ensure_ascii=False),
                             'reason': ('No complete case mapping; full telemetry row totals not scanned.'
                                        if item['modality'] else
                                        'Not case-level telemetry; archive/cache/annotation/auxiliary kept separately.')})
    write_report(out, summary, slices, derived, evidence)


def write_report(out, summary, slices, findings, evidence):
    """Compact report; detailed per-case evidence is in JSON/CSV sidecars."""
    gb = lambda n: f'{n / 1e9:.3f}'
    mb = lambda n: f'{n / 1e6:.2f}'
    sources = summary['sources']
    if not evidence or evidence.get('stops'):
        pending = '\n'.join('- ' + x for x in evidence.get('stops', ['L1 chưa chạy; chỉ có L0.']))
        source_text = '\n'.join(f'- {source}: {info["bytes"] / 1e9:.3f} GB'
                                for source, info in sources.items())
        (out / 'DATASET_PLAN.md').write_text(
            '# DATASET PLAN — L0 / kiểm tra còn chờ\n\n'
            f'Tổng {summary["total_bytes"] / 1e9:.3f} GB; số liệu chi tiết ở audit_summary.json.\n\n'
            + source_text + '\n\n' + pending + '\n\n'
            'Chưa hoàn tất xác minh schema/nhãn; không tự mở rộng L1. '
            'Bảng case ở dataset_map.csv; phần chưa ánh xạ ở unmapped_inventory.csv.\n', encoding='utf-8')
        return
    coverage = summary['rcaeval_coverage']
    index = evidence.get('index', {})
    dev, grouping, ranking = slices['dev'], slices['grouping'], slices['ranking']
    dep, deferred = slices['dependency'], slices['deferred']
    bounds = findings['log_bounds_from_footer']
    tick_min = min((b['duration_ticks'] for b in bounds), default=0)
    tick_max = max((b['duration_ticks'] for b in bounds), default=0)
    comparisons = findings['sampled_inject_comparisons']
    both = sum(x['numeric_min_before_inject'] and x['numeric_max_after_inject'] for x in comparisons)
    label_rows = index.get('rows_analyzed', 0)
    majority = index.get('majority_fraction_in_prefix')
    majority_text = f'{100 * majority:.1f}%' if majority is not None else UNKNOWN
    log_rows = sum(x['rows'] for x in findings['rcaeval_logs_by_system'].values())
    source_lines = []
    for source in ['rcaeval', 'lemma_rca', 'nezha']:
        info = sources[source]
        modality = info['modalities']
        source_lines.append(f'| {source} | {gb(info["bytes"])} | ' +
                            ' / '.join(gb(modality.get(m, 0)) for m in MODALITIES) + ' |')
    coverage_text = '; '.join(f'{system}: {x["cases"]}/{x["logs_nonempty"]}/{x["traces_nonempty"]}'
                              for system, x in sorted(coverage.items()))
    sampled_counts = Counter(m for p in evidence.get('rcaeval', {}).values() for m in MODALITIES if m in p)
    ext = evidence.get('external', {})
    nezha_count = ext.get('nezha_annotation_prefix', {}).get('rows_analyzed', 0)
    neq = len(ext.get('nezha', []))
    lemma_sample = ext.get('lemma_partition', {})
    proxy_text = '; '.join(f'{family} {100 * p["majority_fraction"]:.1f}%'
                           for family, p in findings['directory_proxy_distribution_with_logs'].items())
    sparse_count = len(slices['split_protocol']['A']['strata_with_fewer_than_three_repeat_groups_after_dev'])
    outside_count = len(findings['index_alignment_in_prefix']['inject_outside_index_metric_window'])
    report = f'''# DATASET PLAN — audit L0/L1, 20/10/2026

## Bản đồ và bằng chứng

Tổng **{gb(summary['total_bytes'])} GB** theo kích thước file (GB thập phân), chưa khử trùng. Không L2, không huấn luyện/parse hàng loạt. L1: {len(evidence.get('rcaeval', {}))} case RCAEval và mẫu external được duyệt, tổng {findings['l1_logical_rows_materialized']:,} bản ghi kể cả nhãn. Footer/schema ở `audit_metadata.json`; bằng chứng/ngân sách ở `l1_evidence.json`, `l1_ledger.json`; chạy lại tái dùng mẫu.

| Nguồn (ID thư mục) | Tổng GB | Logs / metrics / traces GB¹ |
|---|---:|---:|
{chr(10).join(source_lines)}

¹ Modality ngoài Parquet gán theo đường dẫn, chỉ schema mẫu được xác minh. LEMMA có **{gb(sources['lemma_rca']['categories'].get('archive', 0))} GB ZIP**, ngoài telemetry; chưa kết luận archive trùng bản giải nén. Cache/auxiliary ngoài ba nguồn: {gb(sources['_workspace_auxiliary']['bytes'])} GB.

RCAEval: **735 case; {grouping['confirmed_cases']} log không rỗng, {log_rows:,} dòng; 735 metrics; 240 traces**. Độ phủ `case/log/traces`: {coverage_text}. Cả 735 metrics đều không rỗng. `system` trong CSV là mã thư mục; họ `ob/ss/tt` dùng cho C.

Manifest thực tế **2 bản ghi**: HF RCAEval và GitHub RCAEval (repo mã nguồn). Không có bản ghi LEMMA/Nezha; đường dẫn manifest là Windows cũ. Mốc “5 dòng” không khớp snapshot hiện tại, nguyên nhân lịch sử **chưa xác nhận**; không tự sửa manifest.

## Schema, nhãn và thời gian

- RCAEval: footer cả 359 log có `timestamp:int64`, `container_name`, `message`; không có cột severity riêng. Trong {sampled_counts.get('logs', 0)} log case lấy mẫu, một số nội dung có token severity; không suy ra chất lượng toàn corpus. Traces có `serviceName`, `traceID`, `spanID`, `parentSpanID`; tên container và service cần đối chiếu alias.
- `cases.parquet`: nhãn **`root_cause_service`**, inject **`inject_time`**. Prefix {label_rows} dòng: nhãn khớp tên thư mục, **0 có log**. Vì thế **{ranking['confirmed_cases']} case ranking đã xác minh**, không có nghĩa phần còn lại thiếu nhãn. Phân bố mẫu: 8 service ×25; majority mô tả **{majority_text} (25/{label_rows})**, chưa phải test score; mẫu RE1 có thiên lệch, toàn bộ ground truth **chưa xác nhận**.
- Log RCAEval: span toàn file từ footer **{tick_min}–{tick_max} tick**. Giây là suy luận có đối chứng từ `startTimeMillis`/duration index, không phải đơn vị Arrow khai báo; nếu là giây: {tick_min / 60:.2f}–{tick_max / 60:.2f} phút. Múi giờ **chưa xác nhận**. {both}/{len(comparisons)} mẫu có min < inject < max trong cùng miền số; chi tiết ở `audit_findings.json`. Index có {outside_count} mẫu inject ngoài cửa sổ metrics; footer inject min **16933142** khác thang thường gặp: không tự sửa/quy đổi hàng loạt.
- Nezha: {nezha_count} annotation ở một ngày; {neq} loại lỗi lấy một mẫu log/trace mỗi loại. Log: `Timestamp` có `Z`, `TimeUnixNano`, `PodName`, `Container`, `Log`; severity có trong JSON lồng ở ví dụ, không có cột riêng. Nhãn **pod** `inject_pod`, thời điểm `inject_timestamp`/`inject_time`; mapping service, span và trước/sau inject toàn case **chưa xác nhận**. Metrics chỉ L0 vì file dùng chung theo pod/ngày.
- LEMMA: một partition, {lemma_sample.get('rows_analyzed', 0)} log ở `hits.hits[*]._source`: `@timestamp` offset `+00:00`, `message`, `level` (ví dụ `unknown`), `kubernetes.container_name/pod_name`. Timestamp mẫu **2021-05-15** khác ngày tên file **20210517**. Không dùng tên file làm thời gian sự kiện; nhãn service/case lỗi **chưa xác nhận**. Cả hai nguồn external có schema khác RCAEval.

## Sáu lát cắt đề xuất

Các lát cắt chồng lấn; dung lượng log là kích thước file, không phải RAM khi đọc.

| Lát cắt | Số case; dung lượng | Vai trò và giới hạn |
|---|---|---|
| Dev — RCAEval | {dev['cases']}; log {mb(dev['log_bytes'])} MB, cả modality {mb(dev['all_modalities_bytes'])} MB | Hai/họ từ L1; parser, bảo toàn ID. IDs trong `slice_manifest.json`. Loại cả {len(dev['evaluation_excluded_case_ids_by_repeat_group'])} case cùng nhóm lặp khỏi đánh giá. |
| Grouping — RCAEval | {grouping['confirmed_cases']}; log {gb(grouping['log_bytes'])} GB | Visible Log Reduction = 1−số nhóm/N; Raw Log Traceability = số ID truy ngược được/N, mục tiêu 100%. Chưa đo các chỉ số. |
| Ranking — RCAEval | {ranking['confirmed_cases']} xác minh; {ranking['candidate_cases']} ứng viên, log {gb(ranking['candidate_log_bytes'])} GB | Chờ xác minh nhãn; LR/XGBoost chấm điểm cặp case–service ở bước sau. |
| External — LEMMA/Nezha | 0 case đủ điều kiện; {gb(slices['external_test']['available_physical_bytes'])} GB hiện hữu | Đặt trước, không chỉnh parser/tham số theo kết quả external. Case/dung lượng dùng được chưa xác nhận. |
| Dependency — RCAEval | {dep['trace_cases']} traces/{gb(dep['trace_bytes'])} GB; {dep['metric_cases']} metrics/{gb(dep['metric_bytes'])} GB | Cạnh gọi + inventory; metrics ablation sau. Cạnh quan sát không chứng minh causation. |
| Gác lại | {deferred['rcaeval_cases']} RCAEval/{gb(deferred['rcaeval_telemetry_bytes'])} GB telemetry | Không log; external chưa ánh xạ; archive/cache, sample rời. `tests/fixtures` không có trong workspace này. |

LEMMA log theo đường dẫn {gb(sources['lemma_rca']['modalities']['logs'])} GB và Nezha {gb(sources['nezha']['modalities']['logs'])} GB là ứng viên grouping theo partition, **chưa phải số case hợp lệ**; chưa được ingest.

## Giao thức, rủi ro và quyết định còn thiếu

**A:** 60/20/20, seed 42, phân tầng mã hệ thống/lỗi; **B:** lần lượt bỏ một mã lỗi, train/val 80/20 (ý nghĩa `f1–f5` chưa xác nhận); **C:** bỏ toàn bộ một họ `ob/ss/tt` qua mọi phiên bản, train/val 80/20. Báo cáo C là mức khó nhất, chưa có kết quả. Nhóm `(họ, service, mã lỗi)` không tách fold; thiếu nhóm thì báo không thể phân tầng, không nhân bản để lấp tỷ lệ. Parser có học/preprocessing/model và baseline majority chỉ fit trên train; chọn tham số bằng validation.

Sau bỏ dev có **{sparse_count} stratum dưới 3 nhóm lặp**; không thể bảo đảm cả ba phần đều có mặt. Majority từ **proxy tên thư mục log**, không phải ground truth: {proxy_text}. Không đưa case/path, nhãn, fault code hay annotation inject vào đặc trưng. Token “root cause” ở 3 mẫu log chưa chứng minh lộ nhãn (có thể là exception); không có marker cũng không chứng minh an toàn. Inventory/cạnh chỉ lấy trong cửa sổ hợp lệ, không dùng nhãn tạo ứng viên. Mỗi nhóm giữ mọi `raw_log_id` nguồn/snapshot/file/vị trí bản ghi; tổng thành viên = N, mỗi ID đúng một nhóm, truy ngược 100%; không xóa log gốc.

**Ba quyết định cho bước sau:** (1) Có cấp ngoại lệ đọc riêng toàn bảng nhãn để mở khóa ranking không? (2) Ai xác nhận pod→service và cửa sổ Nezha? (3) Giữ LEMMA cho grouping partition hay bổ sung ground truth để xét external ranking? Hiện giữ nguyên L1; không tự mở rộng.
'''
    (out / 'DATASET_PLAN.md').write_text(report, encoding='utf-8')


if __name__ == '__main__':
    try:
        main()
    except AuditStop as exc:
        print(f'STOP: {exc}', file=sys.stderr)
        sys.exit(2)
