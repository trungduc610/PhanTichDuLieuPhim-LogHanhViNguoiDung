"""Real Spark fixture tests; generated in memory, never the project's raw data."""
import argparse
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from common import utcnow
from hdfs_common import new_json
from src.schemas import MOVIE_SCHEMA
from src.tv2_processing import clean_lines,transform_logs,join_movies,genres_array,validate_movies
from src.tv2_analytics import build_user_features,validate_features
from pyspark.sql import SparkSession,functions as F

START='2026-08-31T17:00:00+00:00'
END='2026-09-30T17:00:00+00:00'
RUN='fixture-only'
def event(event_id,**overrides):
    row=dict(eventId=event_id,userId='a',sessionId='s',movieId=1,action='view',
       timestamp='2026-08-31T17:00:00Z',watchDuration=0,sequenceNumber=0,runId=RUN,
       isSynthetic=True,simulatedMovieDuration=3600,durationSource='synthetic')
    row.update(overrides);return row

class SparkFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spark=(SparkSession.builder.master('local[2]').appName('TV2-Fixture-Tests')
          .config('spark.sql.session.timeZone','UTC').config('spark.sql.shuffle.partitions','2')
          .config('spark.sql.legacy.timeParserPolicy','CORRECTED')
          .config('spark.sql.ansi.enabled','false').getOrCreate())
        cls.spark.sparkContext.setLogLevel('WARN')
    @classmethod
    def tearDownClass(cls):cls.spark.stop()
    def movies(self):
        return self.spark.createDataFrame([(1,'Fixture Movie','Action| Drama |Action',2020)],MOVIE_SCHEMA).withColumn('_corrupt_record',F.lit(None).cast('string'))
    def lines(self,rows):
        return self.spark.createDataFrame([(row if isinstance(row,str) else json.dumps(row),) for row in rows],'value string')
    def test_cleaning_and_disjoint_reconciliation(self):
        good=event('good')
        missing=event('missing');del missing['sessionId']
        rows=[good,good,event('conflict'),event('conflict',userId='b'),'{"broken":',
          missing,event('null',userId=None),event('action',action='invalid'),
          event('time',timestamp='not-a-date'),event('negative',watchDuration=-1),
          event('typed',watchDuration='invalid'),event('orphan',movieId=999),
          event('empty',userId=''),event('complete-zero',action='complete'),
          event('view-positive',watchDuration=10),event('provenance',isSynthetic=False),
          event('sequence',sequenceNumber=-1),event('end',timestamp='2026-09-30T17:00:00Z')]
        clean,rejected,report,buffers=clean_lines(self.lines(rows),self.movies(),START,END,RUN)
        try:
            self.assertEqual(report['raw_log_count'],len(rows))
            self.assertEqual(report['clean_log_count'],1)
            self.assertEqual(report['duplicate_count'],3)
            self.assertEqual(report['exact_duplicate_count'],1)
            self.assertEqual(report['conflicting_event_id_groups'],1)
            self.assertEqual(report['conflicting_event_rows'],2)
            self.assertEqual(report['orphan_movie_id_count'],1)
            self.assertEqual(rejected.count(),len(rows)-1)
            self.assertEqual(sum(step['removed'] for step in report['steps']),len(rows)-1)
            for metric in ['malformed_json_count','null_count','empty_required_string_count',
                           'invalid_action_count','invalid_timestamp_count','invalid_watch_duration_count',
                           'invalid_integer_count','invalid_provenance_count']:
                self.assertGreater(report[metric],0,metric)
            reasons={reason for row in rejected.select('rejected_reason').collect() for reason in row[0]}
            self.assertTrue({'exact_duplicate','conflicting_event_id','orphan_movie_id'}<=reasons)
            self.assertEqual(clean.first()['eventId'],'good')
        finally:
            clean.unpersist()
            for frame in buffers:frame.unpersist()
    def test_features_time_genres_and_resumed_session_rate(self):
        rows=[event('v'),event('p',action='play',sequenceNumber=1),
          event('pause',action='pause',watchDuration=1200,sequenceNumber=2),
          event('resume',action='play',sequenceNumber=3),
          event('complete',action='complete',watchDuration=2400,sequenceNumber=4),
          event('only-view',userId='b',sessionId='s2')]
        clean,rejected,report,buffers=clean_lines(self.lines(rows),self.movies(),START,END,RUN)
        try:
            self.assertEqual(report['rejected_record_count'],0)
            joined=join_movies(transform_logs(clean),self.movies())
            first=joined.filter(F.col('eventId')=='v').first()
            self.assertEqual(str(first['date']),'2026-09-01')
            self.assertEqual(first['hour'],0)
            self.assertEqual(first['dayOfWeek'],3)
            self.assertEqual(first['genresArray'],['Action','Drama'])
            self.assertEqual(joined.filter(F.col('eventId')=='pause').first()['watchDurationMinutes'],20.0)
            features=build_user_features(joined)
            self.assertEqual(validate_features(features)['users'],2)
            users={row['userId']:row.asDict() for row in features.collect()}
            self.assertEqual(users['a']['playCount'],2)
            self.assertEqual(users['a']['sessionCount'],1)
            self.assertEqual(users['a']['totalWatchDuration'],3600)
            self.assertEqual(users['a']['avgWatchDuration'],1800.0)
            self.assertEqual(users['a']['completionRate'],1.0)
            self.assertEqual(users['a']['distinctGenres'],2)
            self.assertFalse(users['b']['completionRateDefined'])
            self.assertEqual(users['b']['avgWatchDuration'],0.0)
            self.assertEqual(users['b']['completionRate'],0.0)
            for value in [float('nan'),float('inf'),None]:
                bad=features.withColumn('avgWatchDuration',F.lit(value).cast('double'))
                with self.assertRaises(ValueError):validate_features(bad)
        finally:
            clean.unpersist()
            for frame in buffers:frame.unpersist()
    def test_independent_comparison_rejects_corrupt_duplicate_and_missing_rows(self):
        from tv2_runtime_verify import compare_frames
        expected=self.spark.createDataFrame([(1,2.0),(2,4.0)],'id long,value double')
        self.assertTrue(compare_frames(expected,expected,['id'])['pass'])
        for actual in [self.spark.createDataFrame([(1,2.0)],'id long,value double'),
                       self.spark.createDataFrame([(1,2.0),(1,2.0)],'id long,value double'),
                       self.spark.createDataFrame([(1,2.0),(2,99.0)],'id long,value double')]:
            self.assertFalse(compare_frames(expected,actual,['id'])['pass'])

    def test_movie_duplicates_and_allowed_unknown_metadata(self):
        movies=self.movies()
        self.assertEqual(validate_movies(movies)['rows'],1)
        with self.assertRaises(ValueError):validate_movies(movies.unionByName(movies))
        unknown=movies.withColumn('releaseYear',F.lit(None).cast('int')).withColumn('genres',F.lit('(no genres listed)'))
        self.assertEqual(validate_movies(unknown)['releaseYear_null'],1)
        self.assertEqual(unknown.select(genres_array().alias('genresArray')).first()[0],['(no genres listed)'])

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True);args=parser.parse_args()
    started=utcnow()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(SparkFixtures)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report=dict(status='PASS' if result.wasSuccessful() else 'FAIL',fixture_only=True,
       fixtures='In-memory temporary DataFrames, no project/HDFS raw mutations',
       started_at_utc=started,finished_at_utc=utcnow(),tests=result.testsRun,
       failures=[dict(test=str(test),trace=trace) for test,trace in result.failures],
       errors=[dict(test=str(test),trace=trace) for test,trace in result.errors])
    new_json(args.report,report);print(json.dumps(report,ensure_ascii=True),flush=True)
    return 0 if result.wasSuccessful() else 1
if __name__=='__main__':raise SystemExit(main())
