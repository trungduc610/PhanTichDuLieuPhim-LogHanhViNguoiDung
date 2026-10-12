"""Remove only temporary Spark networks belonging to this audit; retain volumes."""
import datetime
import json
import subprocess

projects=['movie-spark-fixture-221710','movie-spark-demo-221710','movie-spark-parser-221710',
          'movie-runtime-221710','movie-spark-main-221710','movie-independent-221710']
for project in projects:
    argv=['docker','compose','-p',project,'down']
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    result=subprocess.run(argv,capture_output=True,text=True)
    print(json.dumps({'argv':argv,'started_at_utc':started,
       'finished_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr}))
    if result.returncode:
        raise SystemExit(result.returncode)
