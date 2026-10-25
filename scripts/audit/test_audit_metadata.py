"""Safety checks on synthetic files only: python3 -m unittest discover -s scripts/audit -p 'test_audit_metadata.py'."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import audit_metadata as audit
import pyarrow as pa
import pyarrow.parquet as pq


class AuditGuards(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=audit.AUDIT_DIR / '.audit_tmp')
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_l0_never_asks_for_data_and_l1_stops_at_200(self):
        path = self.root / 'sample.parquet'
        pq.write_table(pa.table({'timestamp': range(900), 'message': ['x'] * 900}),
                       path, row_group_size=450)
        actual = pq.ParquetFile

        class FooterOnly:
            def __init__(self, path):
                self.pf = actual(path)
                self.metadata = self.pf.metadata
                self.schema_arrow = self.pf.schema_arrow

            def iter_batches(self, *args, **kwargs):
                raise AssertionError('L0 attempted a data read')

            def close(self):
                self.pf.close()

        with patch.object(pq, 'ParquetFile', FooterOnly):
            meta = audit.footer(path)
        self.assertEqual((meta['num_rows'], meta['num_row_groups']), (900, 2))
        rows, _ = audit.bounded_parquet(path, 200)
        self.assertEqual(len(rows), 200)
        self.assertEqual(rows[-1]['timestamp'], 199)

    def test_ledger_reuses_read_and_rejects_changed_budget_or_selection(self):
        path = self.root / 'input.csv'
        path.write_text('a\n1\n')
        calls = []

        def reader(path, limit):
            calls.append(path)
            return {'rows_analyzed': 1}

        budget = audit.Budget(self.root, self.root)
        budget.freeze_selection(['fixed'])
        budget.read('input.csv', 'test', reader)
        audit.Budget(self.root, self.root).read('input.csv', 'test', reader)
        self.assertEqual(len(calls), 1)
        with self.assertRaises(audit.AuditStop):
            budget.read('input.csv', 'test', reader, limit=199)
        with self.assertRaises(audit.AuditStop):
            budget.freeze_selection(['different'])
        with self.assertRaises(audit.AuditStop):
            budget.read('input.csv', 'test', reader, limit=201)

    def test_interrupted_read_cannot_be_silently_retried(self):
        (self.root / 'input').write_text('x')
        budget = audit.Budget(self.root, self.root)

        def fail(path, limit):
            raise RuntimeError('unsupported schema')

        with self.assertRaises(audit.AuditStop):
            budget.read('input', 'test', fail)
        with self.assertRaisesRegex(audit.AuditStop, 'human review'):
            budget.read('input', 'test', lambda p, n: {'rows_analyzed': 0})

    def test_csv_cap_counts_multiline_records(self):
        path = self.root / 'records.csv'
        with path.open('w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'message'])
            writer.writerows((i, 'line one\nline two') for i in range(250))
        rows, _ = audit.bounded_csv(path, 200)
        self.assertEqual(len(rows), 200)
        self.assertEqual(rows[-1]['timestamp'], '199')

    def test_hourly_json_cap_counts_records_across_arrays(self):
        path = self.root / 'faults.json'
        row = dict(inject_time='x', inject_timestamp='0', inject_pod='p', inject_type='f')
        path.write_text(json.dumps({'01': [row] * 150, '02': [row] * 150}))
        result = audit.nezha_index_prefix(path, 200)
        self.assertEqual(result['rows_analyzed'], 200)
        self.assertEqual(result['partition_hours'].count('01'), 150)
        self.assertEqual(result['partition_hours'].count('02'), 50)

    def test_elasticsearch_cap_counts_hits_not_wrapper(self):
        path = self.root / 'logs.json'
        path.write_text(json.dumps({'hits': {'hits': [
            {'_id': str(i), '_source': {'message': str(i)}} for i in range(250)]}}))
        result = audit.lemma_partition_profile(path, 200)
        self.assertEqual(result['rows_analyzed'], 200)
        self.assertEqual(result['unit'], 'partition, not fault case')

    def test_readonly_check_detects_new_or_modified_inputs(self):
        path = self.root / 'one'
        path.write_text('before')
        st = path.stat()
        snapshot = [{'relative_path': 'one', 'bytes': st.st_size, 'mtime_ns': st.st_mtime_ns}]
        self.assertTrue(audit.check_unchanged(self.root, snapshot)['unchanged_size_mtime'])
        (self.root / 'two').write_text('new')
        changed = audit.check_unchanged(self.root, snapshot)
        self.assertEqual(changed['added_paths'], ['two'])
        self.assertFalse(changed['unchanged_size_mtime'])
        path.write_text('different size')
        self.assertIn('one', audit.check_unchanged(self.root, snapshot)['changed_paths'])


if __name__ == '__main__':
    unittest.main()
