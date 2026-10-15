"""Week 3 baseline selection and fail-fast runtime gate regressions."""
import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import run_tv2
from tv2_common import evidence_folder,validate_week3_baseline,valid_hourly_ranks,portable_repo_path

REPO=Path(__file__).resolve().parents[1]
CONTEXT='evidence/week2-hdfs/fix-run-f63c810e9d8d-20261012-verified/run-context.json'

class Week3Tests(unittest.TestCase):
    def baseline(self):
        context=json.loads((REPO/CONTEXT).read_text(encoding='utf-8'))
        source=json.loads((REPO/context['evidence']/'source_manifest.json').read_text(encoding='utf-8'))
        return context,source
    def test_context_reference_is_repo_relative_and_portable(self):
        self.assertEqual(portable_repo_path(REPO,REPO/'evidence'/'week2-hdfs'/'context.json'),'evidence/week2-hdfs/context.json')
        with self.assertRaises(ValueError):portable_repo_path(REPO,REPO.parent/'outside.json')
    def test_exact_baseline_allowed(self):
        validate_week3_baseline(*self.baseline())
    def test_other_release_and_wrong_input_refused(self):
        for field,value in [('run_id','hdfs-385a18d3f03a'),('flume_run_id','run-63efa2865c76'),('project','other')]:
            context,source=self.baseline();context[field]=value
            with self.assertRaises(ValueError):validate_week3_baseline(context,source)
        context,source=self.baseline();source['logs_uri']='file:///local'
        with self.assertRaises(ValueError):validate_week3_baseline(context,source)
    def test_manifest_count_and_bytes_not_forced_to_pass(self):
        for field in ['expected_movies','expected_logs']:
            context,source=self.baseline();source[field]-=1
            with self.assertRaises(ValueError):validate_week3_baseline(context,source)
        context,source=self.baseline();source['files'][0]['bytes']+=1
        with self.assertRaises(ValueError):validate_week3_baseline(context,source)
    def test_evidence_scope_cannot_traverse_or_select_tv1(self):
        root=Path('.')
        self.assertEqual(evidence_folder(root,'tv2-012345abcdef','evidence/week3-tv2'),root/'evidence/week3-tv2/tv2-012345abcdef')
        for scope in ['../outside','evidence/week3-tv1','evidence/week3-tv2/../week2-tv2']:
            with self.assertRaises(ValueError):evidence_folder(root,'tv2-012345abcdef',scope)
    def test_sparse_hours_and_less_than_three_movies_are_valid(self):
        rows=[dict(hour=9,rank=1,movieId=1,playCount=8),dict(hour=9,rank=2,movieId=2,playCount=4)]
        self.assertTrue(valid_hourly_ranks(rows))
        self.assertTrue(valid_hourly_ranks([]))
    def test_bad_rank_tie_order_and_duplicate_movies_fail(self):
        original=[dict(hour=9,rank=1,movieId=1,playCount=8),dict(hour=9,rank=2,movieId=2,playCount=4)]
        for field,value in [('rank',3),('movieId',1),('playCount',9),('hour',24)]:
            rows=copy.deepcopy(original);rows[1][field]=value
            self.assertFalse(valid_hourly_ranks(rows))
        self.assertFalse(valid_hourly_ranks([dict(hour=9,rank=1,movieId=2,playCount=4),dict(hour=9,rank=2,movieId=1,playCount=4)]))
    def test_stopped_baseline_blocks_before_build_or_spark(self):
        context,source=self.baseline();calls=[]
        class FakeLedger:
            def __init__(self,*args,**kwargs):pass
            def command(self,argv,label,check=True):
                calls.append(argv)
                output=chr(10).join(json.dumps(dict(Service=role,State='exited')) for role in ['namenode','datanode']) if label=='hdfs-services' else ''
                return 0,output,Path('.')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source_dir=root/context['evidence'];source_dir.mkdir(parents=True)
            (source_dir/'source_manifest.json').write_text(json.dumps(source),encoding='utf-8')
            path=root/'context.json';path.write_text(json.dumps(context),encoding='utf-8')
            args=SimpleNamespace(hdfs_context=str(path),seed=None,driver_memory='1536m',evidence_root='evidence/week3-tv2')
            with patch.object(run_tv2,'ROOT',root),patch.object(run_tv2,'PROTECTED',[]),patch.object(run_tv2,'TV2_FILES',[]),patch.object(run_tv2,'Ledger',FakeLedger),patch.object(run_tv2.os,'chdir'),patch.object(run_tv2.shutil,'which',return_value='docker'),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(run_tv2.run(args),1)
            report=json.loads(next((root/'evidence/week3-tv2').glob('*/run_status.json')).read_text())
            self.assertEqual(report['status'],'BLOCKED_BY_TV1_RUNTIME')
            self.assertFalse(report['local_fallback'])
            self.assertFalse(any(word in argv for argv in calls for word in ['build','run','start','up','restart']))
            self.assertFalse(list(root.rglob('pipeline_summary.json')))

if __name__=='__main__':unittest.main()
