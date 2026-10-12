"""Import/verify a selected Flume snapshot with one Hadoop Java client JVM."""
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from common import sha256,utcnow
from hdfs_common import new_json,snapshot_namespaces,snapshot_file_diff
from pyspark.sql import SparkSession


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-manifest',required=True)
    parser.add_argument('--report',required=True)
    parser.add_argument('--upload',action='store_true')
    args=parser.parse_args()
    if Path(args.report).exists():raise FileExistsError(args.report)
    source=json.loads(Path(args.source_manifest).read_text(encoding='utf-8'))
    namespaces=snapshot_namespaces(source)
    report={'status':'FAIL','started_at_utc':utcnow(),'hdfs_run_id':source['hdfs_run_id'],
            'flume_run_id':source['flume_run_id'],'source_manifest_sha256':sha256(args.source_manifest),
            'stage':'HDFS_BYTE_VERIFICATION','files':[],
            'note':'Every remote byte is hashed. Independent record counts and schema QA are checked by spark_hdfs_validate.py.',
            'source_hashes':{name:sha256(ROOT/name) for name in ['scripts/hdfs_spark_import.py','scripts/hdfs_common.py']}}
    spark=None
    try:
        if args.upload:
            for record in source['files']:
                local=(ROOT/record['local_path']).resolve()
                if ROOT not in local.parents or local.stat().st_size!=record['bytes'] or sha256(local)!=record['sha256']:
                    raise ValueError('Local source differs from manifest: '+record['local_path'])
        spark=(SparkSession.builder.master('local[1]').appName('TV1-HDFS-Snapshot-Import')
               .config('spark.hadoop.fs.defaultFS',source['authority'])
               .config('spark.hadoop.dfs.client.use.datanode.hostname','true').getOrCreate())
        spark.sparkContext.setLogLevel('WARN')
        jvm=spark._jvm
        fs=jvm.org.apache.hadoop.fs.FileSystem.get(jvm.java.net.URI(source['authority']),spark.sparkContext._jsc.hadoopConfiguration())
        report['filesystem_class']=fs.getClass().getName()
        if report['filesystem_class']!='org.apache.hadoop.hdfs.DistributedFileSystem':raise ValueError('Refuses non-HDFS filesystem')
        report['actual_filesystem_uri']=fs.getUri().toString()
        if args.upload:
            for directory in source['directories']:
                if not fs.mkdirs(jvm.org.apache.hadoop.fs.Path(directory)):raise ValueError('Cannot create HDFS directory: '+directory)
        for record in source['files']:
            uri=source['authority']+record['hdfs_path'];path=jvm.org.apache.hadoop.fs.Path(uri)
            existed=fs.exists(path)
            if not existed:
                if not args.upload:raise FileNotFoundError('Missing HDFS file: '+uri)
                local=jvm.org.apache.hadoop.fs.Path(str(ROOT/record['local_path']))
                fs.copyFromLocalFile(False,False,local,path)
            before=fs.getFileStatus(path)
            if not before.isFile() or before.getLen()!=record['bytes']:
                raise ValueError('Existing HDFS size/type differs; refusing overwrite: '+uri)
            digest=jvm.java.security.MessageDigest.getInstance('SHA-256')
            stream=jvm.java.security.DigestInputStream(fs.open(path),digest)
            sink=jvm.java.io.OutputStream.nullOutputStream()
            try:jvm.org.apache.hadoop.io.IOUtils.copyBytes(stream,sink,65536,False)
            finally:stream.close();sink.close()
            measured=bytes(digest.digest()).hex();after=fs.getFileStatus(path)
            matches=measured==record['sha256'] and after.getLen()==record['bytes'] and after.getReplication()==1
            stable=before.getLen()==after.getLen() and before.getModificationTime()==after.getModificationTime()
            if not matches or not stable:raise ValueError('HDFS content differs; refusing overwrite: '+uri)
            action=('SKIP_VERIFIED' if existed else 'UPLOADED') if args.upload else 'VERIFIED'
            report['files'].append({'uri':uri,'kind':record['kind'],'bytes':after.getLen(),'sha256':measured,
                                    'replication':after.getReplication(),'matches_source':matches,
                                    'unchanged_during_read':stable,'action':action})
        listed=set()
        for namespace in namespaces:
            iterator=fs.listFiles(jvm.org.apache.hadoop.fs.Path(namespace),True)
            while iterator.hasNext():listed.add(iterator.next().getPath().toUri().getPath())
        report['missing_files'],report['unexpected_files']=snapshot_file_diff(source,listed)
        if report['missing_files'] or report['unexpected_files']:raise ValueError('Raw snapshot file list differs from manifest')
        report.update(status='PASS',local_fallback=False,total_bytes=sum(item['bytes'] for item in report['files']),
                      uploaded=sum(item['action']=='UPLOADED' for item in report['files']),
                      skipped_verified=sum(item['action']=='SKIP_VERIFIED' for item in report['files']))
    except Exception as exc:report['error']=str(exc)
    finally:
        if spark is not None:spark.stop()
        report['finished_at_utc']=utcnow();new_json(args.report,report)
    print(json.dumps({key:value for key,value in report.items() if key!='files'},ensure_ascii=True,indent=2))
    return 0 if report['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
