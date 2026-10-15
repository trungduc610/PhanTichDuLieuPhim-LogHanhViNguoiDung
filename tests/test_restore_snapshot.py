"""Restoration must never overwrite local data or accept changed HDFS bytes."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import restore_hdfs_snapshot as restore
from common import sha256


class RestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        payload = self.root / 'payload'
        payload.write_bytes(b'abc\n')
        self.record = {'kind': 'movies', 'local_path': 'data/processed/movies.csv',
                       'hdfs_path': '/movie-log/raw/movies/snapshot/movies.csv',
                       'bytes': 4, 'sha256': sha256(payload)}
        self.source = {'status': 'PASS', 'authority': 'hdfs://namenode:9000',
                       'hdfs_run_id': 'hdfs-a', 'flume_run_id': 'run-a',
                       'movies_uri': 'hdfs://namenode:9000' + self.record['hdfs_path'],
                       'logs_uri': 'hdfs://namenode:9000/movie-log/raw/user_logs/run-a/hdfs-a',
                       'files': [self.record]}
        self.manifest = self.root / 'source.json'
        self.manifest.write_text(json.dumps(self.source), encoding='utf-8')
        self.target = self.root / self.record['local_path']
        self.patch = patch.object(restore, 'ROOT', self.root)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def run_restore(self, data=b'abc\n'):
        def read(argv, stdout, **kwargs):
            self.assertEqual(argv[3:6], ['hdfs', 'dfs', '-cat'])
            stdout.write(data)
            return SimpleNamespace(returncode=0, stderr=b'')
        with patch.object(restore.subprocess, 'run', side_effect=read):
            return restore.restore(self.manifest, 'namenode', self.root / 'report.json')

    def test_verified_remote_bytes_published(self):
        self.assertEqual(self.run_restore()['status'], 'PASS')
        self.assertEqual(self.target.read_bytes(), b'abc\n')

    def test_wrong_remote_hash_quarantines_partial(self):
        self.assertEqual(self.run_restore(b'bad\n')['status'], 'FAIL')
        self.assertFalse(self.target.exists())
        self.assertTrue(self.target.with_name('movies.csv.restore.part').exists())

    def test_existing_different_data_preserved(self):
        self.target.parent.mkdir(parents=True)
        self.target.write_bytes(b'existing')
        self.assertEqual(self.run_restore()['status'], 'FAIL')
        self.assertEqual(self.target.read_bytes(), b'existing')

    def test_traversal_rejected(self):
        self.source['files'][0]['local_path'] = 'data/processed/../../outside'
        self.manifest.write_text(json.dumps(self.source), encoding='utf-8')
        self.assertEqual(self.run_restore()['status'], 'FAIL')
        self.assertFalse((self.root / 'outside').exists())


if __name__ == '__main__':
    unittest.main()
