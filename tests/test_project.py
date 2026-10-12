"""Unit/integration tests use temporary fixtures, NOT Flume output evidence."""
import contextlib
import csv
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from generate_logs import generate
from prepare_movies import prepare
from validate_pipeline import validate


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.movies = self.root / 'movies.csv'
        self.movies.write_text('movieId,title,genres\n1,Phim Việt (2001),Drama\n2,No year,(no genres listed)\n3,Series (2000–2001),Comedy\n', encoding='utf-8')
        self.output = self.root / 'events.jsonl'
        self.sink = self.root / 'mock-sink'
        self.sink.mkdir()
        self.quiet = contextlib.redirect_stdout(io.StringIO())
        self.quiet.__enter__()

    def tearDown(self):
        self.quiet.__exit__(None, None, None)
        self.temp.cleanup()

    def make(self, n=101):
        generate(self.movies, self.output, events=n, users=100)
        return self.output.read_text(encoding='utf-8').splitlines()

    def check(self, output_dir=None):
        return validate(self.output, self.movies, output_dir, self.root / 'report.json')

    def test_normalization_preserves_missing_year(self):
        normalized = self.root / 'normalized.csv'
        result = prepare(self.movies, normalized, self.root / 'quality.json')
        self.assertEqual(result['missing_or_unparsed_release_year'], 2)
        with normalized.open(encoding='utf-8', newline='') as f:
            self.assertEqual(next(csv.DictReader(f))['releaseYear'], '2001')

    def test_duplicate_movies_rejected(self):
        with self.movies.open('a', encoding='utf-8') as f:
            f.write('1,Duplicate,Drama\n')
        with self.assertRaises(ValueError):
            prepare(self.movies, self.root / 'normalized.csv', self.root / 'quality.json')

    def test_invalid_utf8_rejected(self):
        self.movies.write_bytes(b'movieId,title,genres\n1,\xff,Drama\n')
        with self.assertRaises(UnicodeDecodeError):
            prepare(self.movies, self.root / 'normalized.csv', self.root / 'quality.json')

    def test_exact_counts_boundaries_and_sessions(self):
        for n in [1, 2, 3, 4, 5, 17, 10000]:
            path = self.root / f'events-{n}.jsonl'
            generate(self.movies, path, events=n, users=1000)
            result = validate(path, self.movies, report=self.root / f'report-{n}.json')
            self.assertEqual(result['status'], 'INPUT_PASS')
            self.assertEqual(result['input']['total'], n)

    def test_seed_reproducibility(self):
        self.make()
        other = self.root / 'repeat.jsonl'
        generate(self.movies, other, events=101, users=100)
        self.assertEqual(self.output.read_bytes(), other.read_bytes())

    def test_output_protection(self):
        self.make()
        with self.assertRaises(FileExistsError):
            generate(self.movies, self.output, events=101, users=100)

    def test_mock_reordered_output_matches(self):
        rows = self.make()
        (self.sink / 'part').write_text('\n'.join(reversed(rows)) + '\n', encoding='utf-8')
        self.assertEqual(self.check(self.sink)['status'], 'PASS')

    def test_missing_duplicate_invalid_and_mutated_detected(self):
        rows = self.make()
        changed = json.loads(rows[2])
        changed['userId'] = 'tampered'
        (self.sink / 'part').write_text('\n'.join([rows[0], rows[0], json.dumps(changed)] + rows[3:] + ['not json']) + '\n', encoding='utf-8')
        result = self.check(self.sink)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['missing_event_ids'], 1)
        self.assertEqual(result['output']['duplicates'], 1)
        self.assertEqual(result['output']['invalid'], 1)
        self.assertEqual(result['changed_payloads'], 1)

    def test_empty_sink_never_passes(self):
        self.make()
        self.assertEqual(self.check(self.sink)['status'], 'FAIL')

    def test_unknown_movie_rejected(self):
        rows = self.make()
        event = json.loads(rows[0])
        event['movieId'] = 99999999
        rows[0] = json.dumps(event)
        (self.sink / 'part').write_text('\n'.join(rows) + '\n', encoding='utf-8')
        self.assertEqual(self.check(self.sink)['output']['invalid'], 1)

    def test_duration_tampering_rejected(self):
        rows = self.make()
        for i, row in enumerate(rows):
            event = json.loads(row)
            if event['action'] in ['pause', 'stop', 'complete']:
                event['watchDuration'] += 1
                rows[i] = json.dumps(event)
                break
        self.output.write_text('\n'.join(rows) + '\n', encoding='utf-8')
        self.assertGreater(self.check()['session_errors'], 0)

    def test_naive_timezone_rejected(self):
        with self.assertRaises(ValueError):
            generate(self.movies, self.output, events=10, start='2026-09-01T00:00:00')

    def test_missing_genres_rejected(self):
        self.movies.write_text('movieId,title,genres\n1,Fixture (2001),\n', encoding='utf-8')
        with self.assertRaises(ValueError):
            prepare(self.movies, self.root / 'normalized.csv', self.root / 'quality.json')

    def test_validator_checks_duplicate_movie_ids(self):
        self.make()
        with self.movies.open('a', encoding='utf-8') as f:
            f.write('1,Duplicate,Drama\n')
        result = self.check()
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['movies_quality']['error_rows'], 1)

    def test_validator_reports_empty_roll_file(self):
        rows = self.make()
        (self.sink / 'part').write_text('\n'.join(rows) + '\n', encoding='utf-8')
        (self.sink / 'empty').write_bytes(b'')
        result = self.check(self.sink)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['output_file_summary']['empty_files'], 1)

    def test_truncated_event_rejected(self):
        rows = self.make()
        (self.sink / 'part').write_text('\n'.join(rows), encoding='utf-8')
        result = self.check(self.sink)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['output_file_summary']['missing_final_newline_files'], 1)

    def test_integer_overflow_rejected(self):
        rows = self.make()
        event = json.loads(rows[0])
        event['sequenceNumber'] = 2**63
        rows[0] = json.dumps(event)
        self.output.write_text('\n'.join(rows)+'\n', encoding='utf-8')
        self.assertEqual(self.check()['input']['invalid'], 1)

    def test_validation_evidence_not_overwritten(self):
        self.make()
        self.check()
        with self.assertRaises(FileExistsError):
            self.check()


if __name__ == '__main__':
    unittest.main(verbosity=2)
