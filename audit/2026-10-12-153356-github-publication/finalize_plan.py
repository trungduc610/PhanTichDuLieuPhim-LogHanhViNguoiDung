"""Add the requested publication-scope document to the reviewed allowlist."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from common import sha256,utcnow
from hdfs_common import new_json
from prepare_publication import scan
plan=json.loads((AUDIT/'publication-plan.json').read_text(encoding='utf-8'))
for record in plan['files']:
    file=ROOT/record['path']
    assert file.stat().st_size==record['bytes'] and sha256(file)==record['sha256'],record['path']
rel='docs/github_publication_scope.md'
file=ROOT/rel
assert not scan(rel,file.read_bytes())
plan['files'].append({'path':rel,'bytes':file.stat().st_size,'sha256':sha256(file),'change':'new'})
plan['files'].sort(key=lambda f:f['path'])
plan.update(created_at_utc=utcnow(),total_files=len(plan['files']),total_bytes=sum(f['bytes'] for f in plan['files']))
new_json(AUDIT/'publication-plan-final.json',plan)
with (AUDIT/'stage-paths-final.txt').open('x',encoding='utf-8',newline='\n') as output:
    for record in plan['files']:output.write(record['path']+'\n')
print(json.dumps({'status':'PASS','files':plan['total_files'],'bytes':plan['total_bytes'],
    'max_file_bytes':max(f['bytes'] for f in plan['files']),'secret_findings':plan['secret_scan_findings']},ensure_ascii=True))
