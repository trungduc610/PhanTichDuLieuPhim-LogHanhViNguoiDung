"""Verify the exact supplemental index before the second, ordinary commit."""
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from common import sha256,utcnow
from hdfs_common import new_json
from prepare_publication import scan,git,paths
plan=json.loads((AUDIT/'supplement-plan.json').read_text(encoding='utf-8'))
assert git('rev-parse','HEAD').decode().strip()==plan['head']
assert git('branch','--show-current').decode().strip()=='codex/week2-tv1-hdfs'
assert set(paths('diff','--cached','--name-only','-z'))=={f['path'] for f in plan['files']}
rows=[]
for record in plan['files']:
    rel=record['path']; local=(ROOT/rel).read_bytes(); index=git('show',':'+rel)
    assert len(local)==record['bytes'] and sha256(ROOT/rel)==record['sha256']
    assert index in [local,local.replace(b'\r\n',b'\n')]
    assert not scan(rel,index)
    rows.append({'path':rel,'local_bytes':len(local),'index_bytes':len(index),
                 'local_sha256':record['sha256'],'index_sha256':hashlib.sha256(index).hexdigest()})
patch=git('diff','--cached','--no-ext-diff')
with (AUDIT/'supplement-staged.patch').open('xb') as file:file.write(patch)
git('diff','--cached','--check')
new_json(AUDIT/'supplement-review.json',{'status':'PASS','checked_at_utc':utcnow(),'files':rows,
    'secret_findings':[],'diff_check':'PASS','diff_sha256':sha256(AUDIT/'supplement-staged.patch')})
print('PASS: exact 4-path supplemental diff, content, sizes and secret checks')
