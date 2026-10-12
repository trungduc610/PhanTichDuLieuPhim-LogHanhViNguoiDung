"""Correct omission of three extensionless text Dockerfile snapshots."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from common import sha256,utcnow
from hdfs_common import new_json
from prepare_publication import scan,git
names=['docs/github_publication_scope.md',
       'evidence/run-8ceda3a1111e/source-snapshot/Dockerfile',
       'evidence/run-aa6b9eb58dca/source-snapshot/Dockerfile',
       'evidence/run-aefc814b0b5f/source-snapshot/Dockerfile']
records=[]
for rel in names:
    file=ROOT/rel;data=file.read_bytes()
    data.decode('utf-8',errors='strict')
    assert len(data)<2*1024*1024 and not scan(rel,data)
    records.append({'path':rel,'bytes':len(data),'sha256':sha256(file)})
new_json(AUDIT/'supplement-plan.json',{'status':'PASS','checked_at_utc':utcnow(),
    'head':git('rev-parse','HEAD').decode().strip(),'files':records,'secret_findings':[],
    'reason':'Extensionless Dockerfile source snapshots are lightweight configuration; publish them intact in a new commit.'})
with (AUDIT/'supplement-paths.txt').open('x',encoding='utf-8',newline='\n') as file:
    for rel in names:file.write(rel+'\n')
print('PASS: 3 immutable Dockerfile snapshots and the new publication scope document')
