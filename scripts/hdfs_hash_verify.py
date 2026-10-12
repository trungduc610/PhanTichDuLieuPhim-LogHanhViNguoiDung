"""Read every real HDFS byte with Hadoop's Java client and verify SHA256.

Independent of the CLI/Python line parser used by hdfs_io.py. This check does
not replace full CSV/JSON parsing and Spark QA; it verifies final remote bytes.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from common import sha256, utcnow
from hdfs_common import new_json
from pyspark.sql import SparkSession


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-manifest', required=True)
    parser.add_argument('--report', required=True)
    args = parser.parse_args()
    if Path(args.report).exists():
        raise FileExistsError(args.report)
    source = json.loads(Path(args.source_manifest).read_text(encoding='utf-8'))
    if source['status'] != 'PASS' or source['authority'] != 'hdfs://namenode:9000':
        raise ValueError('Requires the verified HDFS manifest')
    report = {'status': 'FAIL', 'started_at_utc': utcnow(),
              'hdfs_run_id': source['hdfs_run_id'],
              'source_manifest_sha256': sha256(args.source_manifest),
              'verification_source_sha256': sha256(__file__), 'files': [],
              'method': 'HDFS FSDataInputStream -> Java DigestInputStream SHA-256 -> IOUtils.copyBytes -> nullOutputStream'}
    spark = None
    try:
        spark = (SparkSession.builder.master('local[1]').appName('HDFS-Final-Byte-Verification')
                 .config('spark.hadoop.fs.defaultFS', source['authority'])
                 .config('spark.hadoop.dfs.client.use.datanode.hostname', 'true').getOrCreate())
        spark.sparkContext.setLogLevel('WARN')
        jvm = spark._jvm
        fs = jvm.org.apache.hadoop.fs.FileSystem.get(jvm.java.net.URI(source['authority']),
                                                    spark.sparkContext._jsc.hadoopConfiguration())
        report['filesystem_class'] = fs.getClass().getName()
        if report['filesystem_class'] != 'org.apache.hadoop.hdfs.DistributedFileSystem':
            raise ValueError('Refuses a non-HDFS filesystem')
        report['hadoop_client'] = jvm.org.apache.hadoop.util.VersionInfo.getVersion()
        iterator = fs.listFiles(jvm.org.apache.hadoop.fs.Path('/movie-log'), True)
        listed = set()
        while iterator.hasNext():
            listed.add(iterator.next().getPath().toUri().getPath())
        expected = {f['hdfs_path'] for f in source['files']}
        report['missing_files'] = sorted(expected-listed)
        report['unexpected_files'] = sorted(listed-expected)
        if listed != expected:
            raise ValueError('Final namespace file list differs')
        for record in source['files']:
            uri = source['authority'] + record['hdfs_path']
            path = jvm.org.apache.hadoop.fs.Path(uri)
            before = fs.getFileStatus(path)
            digest = jvm.java.security.MessageDigest.getInstance('SHA-256')
            stream = jvm.java.security.DigestInputStream(fs.open(path), digest)
            sink = jvm.java.io.OutputStream.nullOutputStream()
            try:
                jvm.org.apache.hadoop.io.IOUtils.copyBytes(stream, sink, 65536, False)
            finally:
                stream.close()
                sink.close()
            measured = bytes(digest.digest()).hex()
            after = fs.getFileStatus(path)
            item = {'uri': uri, 'bytes': after.getLen(), 'sha256': measured,
                    'replication': after.getReplication(),
                    'matches_source': measured == record['sha256'] and after.getLen() == record['bytes'],
                    'unchanged_during_read': before.getLen() == after.getLen() and before.getModificationTime() == after.getModificationTime()}
            report['files'].append(item)
            if not item['matches_source'] or not item['unchanged_during_read'] or item['replication'] != 1:
                raise ValueError('Final remote bytes/hash/replication changed: ' + uri)
        report.update(status='PASS', total_bytes=sum(f['bytes'] for f in report['files']), local_fallback=False)
    except Exception as exc:
        report['error'] = str(exc)
    finally:
        if spark is not None:
            spark.stop()
        report['finished_at_utc'] = utcnow()
        new_json(args.report, report)
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
