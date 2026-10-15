"""Prevent accidental demo selection, destructive startup and unsafe restart."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from week3_tv1 import official_selection, no_jobs, runtime, runner_status


class OfficialSelectionTests(unittest.TestCase):
    def setUp(self):
        self.context = {'flume_run_id': 'run-official', 'run_id': 'hdfs-existing'}
        self.acceptance = {'status': 'PASS', 'checks': {'pipeline': True},
                           'flume_run_id': 'run-official', 'hdfs_run_id': 'hdfs-existing', 'events': 1000000}

    def test_demo_override_refused_before_data_access(self):
        with self.assertRaisesRegex(ValueError, 'demo/fixture'):
            official_selection(self.context, self.acceptance, 'run-demo')

    def test_different_cluster_refused(self):
        self.context['run_id'] = 'hdfs-other'
        with self.assertRaisesRegex(ValueError, 'official snapshot'):
            official_selection(self.context, self.acceptance)

    def test_small_proof_refused(self):
        self.acceptance['events'] = 10000
        with self.assertRaisesRegex(ValueError, 'Small stability'):
            official_selection(self.context, self.acceptance)

    def test_failed_official_proof_refused(self):
        self.acceptance['checks']['pipeline'] = False
        with self.assertRaisesRegex(ValueError, 'PASS official'):
            official_selection(self.context, self.acceptance)

    @patch('week3_tv1.pipeline_hashes', return_value={'config': 'current'})
    @patch('week3_tv1.load', return_value={'status': 'PASS', 'source_config_hashes': {'config': 'changed'}})
    def test_changed_ingestion_refused(self, *_):
        with self.assertRaisesRegex(ValueError, 'rerun demo then main'):
            official_selection(self.context, self.acceptance)

    @patch('week3_tv1.pipeline_hashes', return_value={'config': 'current'})
    @patch('week3_tv1.load', return_value={'status': 'PASS', 'source_config_hashes': {'config': 'current'}})
    def test_unchanged_official_ingestion_accepted(self, *_):
        self.assertEqual(official_selection(self.context, self.acceptance), 'run-official')


class FakeLedger:
    def __init__(self, output):
        self.output = output
        self.calls = []

    def command(self, argv, label):
        self.calls.append(argv)
        return 0, self.output, Path('.')


class RuntimeGuardTests(unittest.TestCase):
    def test_cli_multiple_json_selects_final_status(self):
        result = runner_status('{"status":"INPUT_PASS"}\n{"status":"PASS"}\n{"status":"PASS","run_id":"run-012345abcdef"}')
        self.assertEqual(result['run_id'], 'run-012345abcdef')

    def test_non_status_json_refused(self):
        with self.assertRaisesRegex(ValueError, 'Missing final'):
            runner_status('{"status":"PASS"}')

    def test_no_cluster_does_not_create_or_format(self):
        ledger = FakeLedger('')
        with self.assertRaisesRegex(ValueError, 'refuses creation/format'):
            runtime({'project': 'missing', 'run_id': 'hdfs-existing'}, ledger, start=True)
        self.assertEqual(len(ledger.calls), 1)
        self.assertEqual(ledger.calls[0][:3], ['docker', 'ps', '-aq'])

    def test_active_spark_blocks_restart(self):
        ledger = FakeLedger('{"Image":"apache/spark:3.5.1","Names":"input-qa"}\n')
        with self.assertRaisesRegex(ValueError, 'postpone restart/stop'):
            no_jobs(ledger)

    def test_only_hdfs_is_safe_for_controlled_restart(self):
        no_jobs(FakeLedger('{"Image":"apache/hadoop:3.3.6","Names":"namenode"}\n'))


if __name__ == '__main__':
    unittest.main()
