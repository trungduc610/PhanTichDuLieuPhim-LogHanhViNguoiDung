"""Host checks for output isolation and measured model selection."""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from tv2_common import output_roots,safe_output_uri,select_best_k

class TV2ContractTests(unittest.TestCase):
    run_id='tv2-012345abcdef'
    def candidates(self):
        return [dict(k=k,silhouette=k/10,cluster_sizes=[10]*k,users=10*k) for k in range(2,7)]
    def test_output_roots_and_allowed_descendant(self):
        roots=output_roots('hdfs://namenode:9000',self.run_id)
        for uri in roots.values():self.assertEqual(safe_output_uri(uri+'/joined_events',self.run_id),uri+'/joined_events')
    def test_reject_raw_local_other_run_and_traversal(self):
        root=output_roots('hdfs://namenode:9000',self.run_id)['processed']
        for uri in ['file:///tmp/x','/tmp/x','hdfs://namenode:9000/movie-log/raw/x',
                    root.replace(self.run_id,'tv2-ffffffffffff'),root+'/../raw',root+'//x',root+'?q=1']:
            with self.subTest(uri=uri),self.assertRaises(ValueError):safe_output_uri(uri,self.run_id)
    def test_reject_invalid_authority_and_run(self):
        for authority,run in [('file://','tv2-012345abcdef'),('hdfs://namenode:9000','existing')]:
            with self.assertRaises(ValueError):output_roots(authority,run)
    def test_measured_max_and_exact_tie(self):
        rows=self.candidates()
        self.assertEqual(select_best_k(rows)['k'],6)
        rows[0]['silhouette']=0.9;rows[-1]['silhouette']=0.9
        self.assertEqual(select_best_k(rows)['k'],2)
    def test_reject_missing_k_invalid_score_and_size(self):
        originals=self.candidates()
        bad=[originals[:-1]]
        rows=copy.deepcopy(originals);rows[0]['silhouette']=float('nan');bad.append(rows)
        rows=copy.deepcopy(originals);rows[0]['cluster_sizes']=[0,20];bad.append(rows)
        rows=copy.deepcopy(originals);rows[0]['users']=21;bad.append(rows)
        for rows in bad:
            with self.assertRaises(ValueError):select_best_k(rows)

if __name__=='__main__':unittest.main()
