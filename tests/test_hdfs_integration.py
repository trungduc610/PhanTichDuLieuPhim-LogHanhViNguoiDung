"""Temporary integration fixtures; these tests never claim real HDFS/Flume evidence."""
import copy
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import hdfs_source
import hdfs_io
from hdfs_common import snapshot_namespaces,snapshot_file_diff
from common import sha256

class SourceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.run='run-012345abcdef';self.cluster='hdfs-012345abcdef'
        self.evidence=self.root/'evidence'/self.run
        self.sink=self.root/'data/runs'/self.run/'output'
        self.evidence.mkdir(parents=True);self.sink.mkdir(parents=True)
        (self.root/'config').mkdir()
        (self.root/'config/flume.conf').write_bytes(b'fixture-config\n')
        (self.root/'config/log4j2.xml').write_bytes((hdfs_source.ROOT/'config/log4j2.xml').read_bytes())
        movies=self.root/'data/processed/movies.csv';movies.parent.mkdir()
        movies.write_text('movieId,title,genres,releaseYear\n1,Fixture (2001),Drama,2001\n',encoding='utf-8')
        generated=self.root/'data/generated/input.jsonl';generated.parent.mkdir()
        events=[{'eventId':str(i),'userId':'u','sessionId':str(i),'movieId':1,'action':'view',
                 'timestamp':'2026-09-01T00:00:00Z','watchDuration':0,'sequenceNumber':0,
                 'isSynthetic':True,'simulatedMovieDuration':3600,'durationSource':'synthetic','runId':'payload'} for i in range(2)]
        payload=''.join(json.dumps(event)+'\n' for event in events).encode()
        generated.write_bytes(payload)
        (self.sink/'part.jsonl').write_bytes(payload);(self.sink/'empty.jsonl').write_bytes(b'')
        self.generated=generated
        self.status={'run_id':self.run,'status':'PASS','input':str(generated),'input_sha256':sha256(generated),
                     'config_sha256':sha256(self.root/'config/flume.conf')}
        stats={'total':2,'unique':2,'invalid':0,'duplicates':0,'conflicting_ids':0}
        self.rec={'status':'PASS','mode':'pipeline_reconciliation','input':stats.copy(),'output':stats.copy(),
                  'input_sha256':sha256(generated),'movies_sha256':sha256(movies),
                  'missing_event_ids':0,'unexpected_event_ids':0,'changed_payloads':0,
                  'session_errors':0,'user_overlap_errors':0,'manifest_errors':[],
                  'output_files':[{'path':str(p),'bytes':p.stat().st_size,'sha256':sha256(p)} for p in sorted(self.sink.iterdir())]}
        manifest={'events':2,'sha256':sha256(generated),'movies_sha256':sha256(movies),'runId':'payload',
                  'start':'2026-09-01T00:00:00Z','end':'2026-10-01T00:00:00Z'}
        generated.with_suffix('.jsonl.manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
        self.write_proof();self.patch=patch.object(hdfs_source,'ROOT',self.root);self.patch.start()
    def tearDown(self):self.patch.stop();self.temp.cleanup()
    def write_proof(self):
        (self.evidence/'status.json').write_text(json.dumps(self.status),encoding='utf-8')
        (self.evidence/'reconciliation.json').write_text(json.dumps(self.rec),encoding='utf-8')
    def build(self):return hdfs_source.source_manifest(self.cluster,self.root/'new-evidence',self.run)
    def test_legacy_run_dynamic_parts_and_sink_only(self):
        result=self.build()
        self.assertEqual(result['flume_run_id'],self.run);self.assertEqual(result['expected_logs'],2)
        self.assertEqual(len(result['files']),3)
        self.assertEqual(sum(x['expected_records'] for x in result['files'] if x['kind']=='logs'),2)
        self.assertTrue(all('/output/' in x['local_path'] for x in result['files'] if x['kind']=='logs'))
    def test_bad_reconciliation_or_non_pass_rejected(self):
        for section,key,value in [('output','duplicates',1),('output','total',1),('input','unique',1)]:
            with self.subTest(key=key):
                old=self.rec[section][key];self.rec[section][key]=value;self.write_proof()
                with self.assertRaises(ValueError):self.build()
                self.rec[section][key]=old
        for key in ['missing_event_ids','unexpected_event_ids','changed_payloads']:
            self.rec[key]=1;self.write_proof()
            with self.assertRaises(ValueError):self.build()
            self.rec[key]=0
        self.status['status']='FAIL';self.write_proof()
        with self.assertRaises(ValueError):self.build()
    def test_changed_sink_or_file_list_rejected(self):
        (self.sink/'extra.jsonl').write_bytes(b'')
        with self.assertRaises(ValueError):self.build()
        (self.sink/'extra.jsonl').unlink();(self.sink/'part.jsonl').write_bytes(b'changed\n')
        with self.assertRaises(ValueError):self.build()
    def test_missing_sink_never_falls_back_to_generated(self):
        (self.sink/'part.jsonl').unlink()
        with self.assertRaises(ValueError):self.build()
    def test_config_hash_and_required_log4j_hash_enforced(self):
        path=self.root/'config/flume.conf';original=path.read_bytes();path.write_bytes(b'changed')
        with self.assertRaises(ValueError):self.build()
        path.write_bytes(original);(self.root/'config/log4j2.xml').write_bytes(b'changed')
        with self.assertRaises(ValueError):self.build()
    def test_input_hash_enforced(self):
        self.generated.write_bytes(b'changed')
        with self.assertRaises(ValueError):self.build()
    def test_modern_source_hashes_still_enforced(self):
        self.status['source_config_hashes']={'config/flume.conf':'wrong'};self.write_proof()
        with self.assertRaises(ValueError):self.build()
    def test_windows_evidence_paths_are_portable(self):
        for proof in self.rec['output_files']:proof['path']=proof['path'].replace('/','\\')
        self.status['input']=self.status['input'].replace('/','\\');self.write_proof()
        self.assertEqual(self.build()['expected_logs'],2)

class NamespaceTests(unittest.TestCase):
    def setUp(self):
        self.source={'status':'PASS','authority':'hdfs://namenode:9000','flume_run_id':'run-a','hdfs_run_id':'hdfs-a',
                     'movies_uri':'hdfs://namenode:9000/movie-log/raw/movies/snapshot/movies.csv',
                     'logs_uri':'hdfs://namenode:9000/movie-log/raw/user_logs/run-a/hdfs-a',
                     'files':[{'kind':'movies','hdfs_path':'/movie-log/raw/movies/snapshot/movies.csv'},
                              {'kind':'logs','hdfs_path':'/movie-log/raw/user_logs/run-a/hdfs-a/part.jsonl'}]}
        self.paths=[x['hdfs_path'] for x in self.source['files']]
    def test_processed_results_and_other_snapshots_do_not_fail(self):
        self.assertEqual(snapshot_file_diff(self.source,self.paths+['/movie-log/processed/a','/movie-log/results/b',
                         '/movie-log/raw/user_logs/another-run/another-import/a']),([],[]))
    def test_extra_nested_file_and_missing_snapshot_file_detected(self):
        extra='/movie-log/raw/movies/snapshot/nested/extra.csv'
        missing,unexpected=snapshot_file_diff(self.source,[self.paths[1],extra])
        self.assertEqual(missing,[self.paths[0]]);self.assertEqual(unexpected,[extra])
    def test_local_uri_wrong_namespace_and_traversal_rejected(self):
        for key,value in [('authority','file:///'),('logs_uri','hdfs://namenode:9000/movie-log/processed'),
                          ('movies_uri','hdfs://namenode:9000/movie-log/raw/movies/../movies.csv')]:
            source=copy.deepcopy(self.source);source[key]=value
            with self.assertRaises(ValueError):snapshot_namespaces(source)

class UploadTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.folder=Path(self.temp.name)
        self.source={'directories':['/movie-log/raw/test'],'files':[
            {'hdfs_path':'/movie-log/raw/test/a','local_path':'a','bytes':3,'sha256':hashlib.sha256(b'abc').hexdigest()},
            {'hdfs_path':'/movie-log/raw/test/b','local_path':'b','bytes':3,'sha256':hashlib.sha256(b'def').hexdigest()}]}
        self.remote={};self.puts=[];self.error='';self.calls=0;owner=self
        class Ledger:
            env={}
            def command(self,argv,label,check=True):
                owner.calls+=1;folder=owner.folder/str(owner.calls);folder.mkdir()
                (folder/'stderr.txt').write_text(owner.error,encoding='utf-8')
                if '-test' in argv:return (0 if argv[-1] in owner.remote else 1),'',folder
                if '-put' in argv:
                    record=next(x for x in owner.source['files'] if x['hdfs_path']==argv[-1])
                    owner.remote[argv[-1]]=(record['bytes'],record['sha256']);owner.puts.append(argv)
                return 0,'',folder
        self.ledger=Ledger()
        self.fingerprint=patch.object(hdfs_io,'remote_fingerprint',side_effect=lambda ledger,base,record:self.remote[record['hdfs_path']])
        self.fingerprint.start()
    def tearDown(self):self.fingerprint.stop();self.temp.cleanup()
    def test_second_upload_skips_verified_existing_content(self):
        first=hdfs_io.upload_files(self.ledger,[],self.source);second=hdfs_io.upload_files(self.ledger,[],self.source)
        self.assertEqual([x['action'] for x in first],['UPLOADED','UPLOADED'])
        self.assertEqual([x['action'] for x in second],['SKIP_VERIFIED','SKIP_VERIFIED'])
        self.assertEqual(len(self.puts),2);self.assertTrue(all('-f' not in argv for argv in self.puts))
    def test_partial_upload_resumes_missing_file(self):
        record=self.source['files'][0];self.remote[record['hdfs_path']]=(record['bytes'],record['sha256'])
        actions=hdfs_io.upload_files(self.ledger,[],self.source)
        self.assertEqual([x['action'] for x in actions],['SKIP_VERIFIED','UPLOADED']);self.assertEqual(len(self.puts),1)
    def test_same_size_wrong_hash_refuses_overwrite(self):
        self.remote[self.source['files'][0]['hdfs_path']]=(3,'wrong-hash')
        with self.assertRaisesRegex(ValueError,'refusing overwrite'):hdfs_io.upload_files(self.ledger,[],self.source)
        self.assertEqual(self.puts,[])
    def test_existence_error_does_not_attempt_upload(self):
        self.error='Connection refused'
        with self.assertRaises(RuntimeError):hdfs_io.upload_files(self.ledger,[],self.source)
        self.assertEqual(self.puts,[])
    def test_remote_fingerprint_hashes_binary_bytes(self):
        self.fingerprint.stop()
        payload=b'abc\r\n\x00def'
        class Process:
            stdout=io.BytesIO(payload)
            def wait(self):return 0
        folder=self.folder/'hash';folder.mkdir()
        class HashLedger:
            env={}
            def start(self,argv,label):return folder,{'argv':argv}
        with patch.object(hdfs_io.subprocess,'Popen',return_value=Process()):
            size,digest=hdfs_io.remote_fingerprint(HashLedger(),[],self.source['files'][0])
        self.assertEqual(size,len(payload));self.assertEqual(digest,hashlib.sha256(payload).hexdigest())
        self.assertEqual(json.loads((folder/'finished.json').read_text())['stdout_bytes'],len(payload))

if __name__=='__main__':unittest.main()
