"""Exercise Spark CSV/JSON parsing errors on isolated files, never Sink evidence."""
import argparse
import json
import tempfile
from pathlib import Path
from spark_smoke_test import SparkSession, MOVIE_SCHEMA, USER_LOG_SCHEMA
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--report', required=True)
    a = p.parse_args()
    target = Path(a.report)
    if target.exists():
        raise FileExistsError(target)
    spark = (SparkSession.builder.master('local[2]').appName('Week1-Parser-Fixtures')
             .config('spark.sql.csv.parser.columnPruning.enabled', 'false').getOrCreate())
    spark.sparkContext.setLogLevel('WARN')
    results = []
    try:
        with tempfile.TemporaryDirectory(prefix='spark-parser-fixture-') as tmp:
            folder = Path(tmp)
            movie_file = folder/'invalid.csv'
            movie_file.write_text('movieId,title,genres,releaseYear\n1,Valid (2001),Drama,2001\ninvalid,Bad (2001),Drama,2001\n', encoding='utf-8')
            log_file = folder/'invalid.jsonl'
            valid = {'eventId':'fixture', 'userId':'fixture', 'sessionId':'fixture', 'movieId':1,
                     'action':'view','timestamp':'2026-09-01T00:00:00Z','watchDuration':0,
                     'sequenceNumber':0,'runId':'fixture','isSynthetic':True,
                     'simulatedMovieDuration':3600,'durationSource':'synthetic'}
            wrong_type = dict(valid, eventId='wrong-type', movieId='not-a-long')
            log_file.write_text(json.dumps(valid)+'\n{broken json\n'+json.dumps(wrong_type)+'\n', encoding='utf-8')
            for name, schema, path, expected_rows, expected_bad in [
                ('CSV_invalid_integer', MOVIE_SCHEMA, movie_file, 2, 1),
                ('JSON_malformed_and_type_error', USER_LOG_SCHEMA, log_file, 3, 2)]:
                schema = StructType(list(schema.fields)+[StructField('_corrupt_record', StringType(), True)])
                reader = spark.read.schema(schema).option('mode','PERMISSIVE').option('columnNameOfCorruptRecord','_corrupt_record')
                frame = (reader.option('header','true').option('escape','"').csv(str(path)) if path.suffix=='.csv' else reader.json(str(path))).cache()
                # Collect all fields before querying corrupt-record column (Spark restriction).
                rows = [row.asDict() for row in frame.collect()]
                bad = sum(row['_corrupt_record'] is not None for row in rows)
                null_ids = sum(row['movieId'] is None for row in rows)
                passed = len(rows)==expected_rows and bad==expected_bad and null_ids==expected_bad
                results.append({'name':name,'rows':len(rows),'malformed_or_type_errors':bad,
                                'null_movie_ids':null_ids,'passed':passed,'examples':rows})
                frame.unpersist()
                if not passed:
                    raise AssertionError(name)
    finally:
        spark.stop()
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps({'fixture_only':True,'never_flume_evidence':True,
            'status':'PASS' if len(results)==2 and all(r['passed'] for r in results) else 'FAIL',
            'tests':results},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Spark parser fixtures: 2 PASS')


if __name__=='__main__':
    main()
