"""Record the remotely verified final publication and local preservation."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from common import sha256,utcnow
from hdfs_common import new_json
from create_delivery_manifest import verify as verify_week1
from create_hdfs_manifest import verify as verify_hdfs
from prepare_publication import git,paths,scan

head=git('rev-parse','HEAD').decode().strip()
main=git('rev-parse','main').decode().strip()
remote_log=next((AUDIT/'execution').glob('remote-final-*/stdout.txt'))
remote={row.split()[1]:row.split()[0] for row in remote_log.read_text(encoding='utf-8').splitlines() if row.strip()}
assert remote['refs/heads/codex/week2-tv1-hdfs']==head
assert remote['refs/heads/main']==main=='bcb28b7fac0c9d260af0e6acb121947f991355f8'
assert git('branch','--show-current').decode().strip()=='codex/week2-tv1-hdfs'
assert git('rev-parse','@{upstream}').decode().strip()==head
git('diff','--exit-code')
git('diff','--cached','--exit-code')
published=paths('diff','--name-only','-z','main...HEAD')
plan=json.loads((AUDIT/'publication-plan-final.json').read_text(encoding='utf-8'))
expected={f['path'] for f in plan['files']}
expected|={f'evidence/{run}/source-snapshot/Dockerfile' for run in ['run-8ceda3a1111e','run-aa6b9eb58dca','run-aefc814b0b5f']}
assert set(published)==expected and len(published)==1021
assert not any(rel.startswith(('data/','logs/')) or rel.endswith(('.bin','.pem','.key','.sqlite','.pyc','.part')) for rel in published)
findings=[]; entries=[]
for rel in published:
    data=git('show','HEAD:'+rel)
    findings+=scan(rel,data)
    file=ROOT/rel
    local=file.read_bytes()
    assert data in [local,local.replace(b'\r\n',b'\n')],rel
    entries.append({'path':rel,'local_bytes':len(local),'git_bytes':len(data),'local_sha256':sha256(file)})
assert not findings
week1=verify_week1(ROOT/'evidence/recheck-20261011-221710/delivery_manifest.json')
hdfs=verify_hdfs(ROOT/'evidence/week2-hdfs/hdfs-385a18d3f03a/delivery_manifest.json')
assert week1['status']==hdfs['status']=='PASS'
result={'status':'PASS','checked_at_utc':utcnow(),'repository':'https://github.com/trungduc610/PhanTichDuLieuPhim-LogHanhViNguoiDung',
    'branch':'codex/week2-tv1-hdfs','commit_sha':head,
    'commit_url':'https://github.com/trungduc610/PhanTichDuLieuPhim-LogHanhViNguoiDung/commit/'+head,
    'published_commits':git('log','--format=%H %s','main..HEAD').decode().splitlines(),
    'remote_sha_matches':True,'main_unchanged':main,'tracked_worktree_and_index_clean':True,
    'published_files':len(published),'local_bytes':sum(f['local_bytes'] for f in entries),'git_bytes':sum(f['git_bytes'] for f in entries),
    'files':entries,'secret_findings':findings,'week1_manifest':week1,'hdfs_manifest':hdfs,
    'tests':'21 host unit tests PASS; production source/config/docs diff-check PASS',
    'historical_whitespace':'Full diff --check exit 2 only in preserved audit/evidence; no whitespace errors in source/config/docs. Historical logs not edited.',
    'local_only':'Full data/raw/processed/generated/Sink, stdout.bin, spool/channel/volumes/temporary/fixtures/CA and this publication audit excluded.',
    'blockers':[],'note':'No merge, force push, history rewrite, pipeline run or container control during publication. Group/TV2 confirmations and later analysis work remain outstanding.'}
new_json(AUDIT/'publication-result.json',result)
print(json.dumps({key:value for key,value in result.items() if key not in ['files','local_only']},ensure_ascii=True,indent=2))
