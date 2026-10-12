"""Inspect every staged blob and complete diff; no Git/index mutation."""
import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from common import sha256,utcnow
from hdfs_common import new_json
from prepare_publication import scan,git,paths

plan=json.loads((AUDIT/'publication-plan-final.json').read_text(encoding='utf-8'))
expected={f['path']:f for f in plan['files']}
actual=paths('diff','--cached','--name-only','-z')
assert set(actual)==set(expected),'Staged set differs from reviewed allowlist'
assert git('branch','--show-current').decode().strip()=='codex/week2-tv1-hdfs'
assert git('remote','get-url','--push','--all','origin').decode().splitlines()==['https://github.com/trungduc610/PhanTichDuLieuPhim-LogHanhViNguoiDung.git']
assert git('rev-parse','HEAD').decode().strip()==plan['head']
entries=[]
for record in git('ls-files','--stage','-z').split(b'\0'):
    if not record:continue
    meta,rel=record.split(b'\t',1)
    mode,oid,stage=meta.split()
    assert stage==b'0' and mode in [b'100644',b'100755'],'unmerged/symlink entry needs review'
    entries.append((rel.decode('utf-8'),oid.decode()))
batch=subprocess.run(['git','cat-file','--batch'],cwd=ROOT,
    input=('\n'.join(oid for _,oid in entries)+'\n').encode(),capture_output=True,check=True).stdout
position=0; findings=[]; sizes=[]; changed=[]; normalization=[]
for rel,oid in entries:
    end=batch.index(b'\n',position)
    header=batch[position:end].split()
    assert header[0].decode()==oid and header[1]==b'blob'
    size=int(header[2]); data=batch[end+1:end+1+size]
    assert len(data)==size and batch[end+1+size:end+2+size]==b'\n'
    position=end+2+size
    findings+=scan(rel,data)
    sizes.append({'path':rel,'bytes':size,'git_blob':oid,'sha256':hashlib.sha256(data).hexdigest()})
    if rel in expected:
        working=(ROOT/rel).read_bytes()
        assert len(working)==expected[rel]['bytes'] and hashlib.sha256(working).hexdigest()==expected[rel]['sha256'],rel
        assert data in [working,working.replace(b'\r\n',b'\n')],'index content differs beyond newline normalization: '+rel
        if data!=working:normalization.append(rel)
        if Path(rel).suffix=='.py':ast.parse(data.decode('utf-8'),filename=rel)
        assert size<=2*1024*1024,rel
        assert not rel.startswith(('data/','logs/')) and Path(rel).suffix.lower() not in ['.bin','.pem','.key','.p12','.pfx','.sqlite','.pyc','.part'],rel
        changed.append({'path':rel,'local_bytes':len(working),'index_bytes':size,'index_sha256':hashlib.sha256(data).hexdigest(),'git_blob':oid})
assert position==len(batch)
assert not findings,findings
assert not [f for f in sizes if f['bytes']>50*1024*1024],'tracked large file'
patch=git('diff','--cached','--no-ext-diff','--binary')
with (AUDIT/'staged-diff-complete.patch').open('xb') as file:file.write(patch)
status=subprocess.run(['git','diff','--cached','--check'],cwd=ROOT,capture_output=True)
with (AUDIT/'staged-whitespace-check.txt').open('xb') as file:file.write(status.stdout+status.stderr)
new_json(AUDIT/'staged-review.json',{'status':'PASS','checked_at_utc':utcnow(),
    'staged_files':len(changed),'staged_local_bytes':sum(f['local_bytes'] for f in changed),
    'staged_index_bytes':sum(f['index_bytes'] for f in changed),'all_index_files_scanned':len(entries),
    'all_index_bytes_scanned':sum(f['bytes'] for f in sizes),'secret_findings':findings,
    'file_list_matches_allowlist':True,'content_matches_worktree_except_git_newline_normalization':True,
    'normalized_text_files':normalization,'files':changed,
    'full_staged_diff_sha256':sha256(AUDIT/'staged-diff-complete.patch'),
    'whitespace_check_exit':status.returncode,'whitespace_log':'staged-whitespace-check.txt',
    'note':'Every index blob was scanned, including unchanged tracked files. No full dataset/binary stream/secret/cache was added.'})
print(json.dumps({'status':'PASS','staged_files':len(changed),'staged_index_bytes':sum(f['index_bytes'] for f in changed),
    'index_files_scanned':len(entries),'normalized_text_files':len(normalization),'whitespace_check_exit':status.returncode,
    'secret_findings':findings},ensure_ascii=True))
