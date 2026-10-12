"""Create an explicit reviewed Git allowlist without changing existing artifacts."""
import ast
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from common import sha256,utcnow
from hdfs_common import new_json

def git(*args):
    result=subprocess.run(['git',*args],cwd=ROOT,capture_output=True,check=True)
    return result.stdout

def paths(*args):return [x.decode('utf-8') for x in git(*args).split(b'\0') if x]

def scan(path,data):
    # Findings report only pattern names/line numbers, never matching values.
    patterns={
        'private-key':rb'-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----',
        'github-token':rb'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})\b',
        'aws-access-id':rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
        'google-api-key':rb'\bAIza[A-Za-z0-9_-]{35}\b',
        'slack-token':rb'\bxox[baprs]-[A-Za-z0-9-]{20,}\b',
        'credential-url':rb'https?://[^\s/@:]+:[^\s/@]+@',
        'bearer-secret':rb'(?i)authorization["\s:]+bearer\s+[a-z0-9._~-]{16,}',
        'assigned-secret':rb'''(?i)(?:password|passwd|client_secret|api[_-]?key|access[_-]?token|github[_-]?token|aws_secret_access_key)\s*[=:]\s*["']([A-Za-z0-9+/_.~-]{16,})["']''',
    }
    findings=[]
    for name,pattern in patterns.items():
        for match in re.finditer(pattern,data):
            findings.append({'path':path,'pattern':name,'line':data[:match.start()].count(b'\n')+1})
    return findings

def main():
    changed=paths('diff','--name-only','-z')
    staged=paths('diff','--cached','--name-only','-z')
    if staged:raise ValueError('Preexisting index changes: keep user staging intact')
    untracked=paths('ls-files','--others','--exclude-standard','-z')
    selected=[]; excluded=[]; findings=[]
    code_roots={'scripts','src','tests','config','docs'}
    for rel in changed+untracked:
        path=ROOT/rel
        parts=Path(rel).parts
        root=parts[0]
        reason=None
        if root in code_roots or rel in ['.dockerignore','Dockerfile','README.md','compose.yaml','compose.hdfs.yaml','requirements.txt']:
            pass
        elif root in ['audit','evidence']:
            if path.is_relative_to(AUDIT):reason='current publication audit remains local; avoids recursive/self-referential staged-diff logs'
            elif any(p in parts for p in ['temporary','fixtures','__pycache__','spool','channel','work']):reason='temporary/fixture/cache/channel'
            elif path.suffix.lower() not in ['.json','.jsonl','.md','.txt','.log','.yaml','.yml','.py','.sh','.xml','.conf','.properties','.jpg','.jpeg','.png']:
                reason='not selected lightweight text/image evidence (binary stream/archive excluded)'
            elif path.suffix=='.jsonl' and not ('sample' in path.name or path.name=='progress.jsonl'):
                reason='full event stream excluded; only small labelled samples/counters selected'
        else:reason='outside source/config/docs/lightweight-audit scope'
        if any(p.lower() in ['.git','temporary','fixtures','__pycache__','spool','channel'] for p in parts) or path.suffix.lower() in ['.bin','.pem','.p12','.pfx','.key','.pyc','.sqlite','.part'] or path.name.lower().startswith('.env'):
            reason='protected binary/secret/cache/temporary path'
        size=path.stat().st_size
        if size>2*1024*1024:reason='larger than publication cap 2 MiB; retain local'
        if reason:
            excluded.append({'path':rel,'bytes':size,'reason':reason});continue
        data=path.read_bytes()
        findings+=scan(rel,data)
        if path.suffix.lower() not in ['.jpg','.jpeg','.png']:
            data.decode('utf-8',errors='strict')
            if b'\0' in data:raise ValueError('Binary content disguised as text: '+rel)
        if path.suffix=='.py':ast.parse(data.decode('utf-8'),filename=rel)
        selected.append({'path':rel,'bytes':size,'sha256':hashlib.sha256(data).hexdigest(),
                         'change':'modified' if rel in changed else 'new'})
    tracked=paths('ls-files','-z')
    tracked_large=[{'path':rel,'bytes':(ROOT/rel).stat().st_size} for rel in tracked if (ROOT/rel).is_file() and (ROOT/rel).stat().st_size>50*1024*1024]
    ignored=paths('ls-files','--others','--ignored','--exclude-standard','-z')
    ignored_large=sorted([{'path':rel,'bytes':(ROOT/rel).stat().st_size} for rel in ignored if (ROOT/rel).is_file() and (ROOT/rel).stat().st_size>2*1024*1024],key=lambda f:f['bytes'],reverse=True)
    new_json(AUDIT/'publication-plan.json',{'created_at_utc':utcnow(),'head':git('rev-parse','HEAD').decode().strip(),
        'branch_before':git('branch','--show-current').decode().strip(),
        'push_remote':git('remote','get-url','--push','origin').decode().strip(),
        'scope':'all modified project source/config/docs plus explicitly enumerated new lightweight evidence; no data directory contents',
        'files':sorted(selected,key=lambda f:f['path']),'total_files':len(selected),'total_bytes':sum(f['bytes'] for f in selected),
        'largest_selected':sorted(selected,key=lambda f:f['bytes'],reverse=True)[:12],
        'excluded_untracked':excluded,'ignored_large_local_files':ignored_large,
        'tracked_large':tracked_large,'secret_scan_findings':findings,
        'notes':['2 MiB maximum per newly staged file','existing unchanged tracked files remain in commit history','Git text normalization may change cloned-byte hashes; local acceptance manifests remain exact local snapshots']})
    with (AUDIT/'stage-paths.txt').open('x',encoding='utf-8',newline='\n') as file:
        for item in sorted(selected,key=lambda f:f['path']):file.write(item['path']+'\n')
    print(json.dumps({'selected':len(selected),'bytes':sum(f['bytes'] for f in selected),
        'changed_tracked':len(changed),'excluded_untracked':len(excluded),'ignored_large':len(ignored_large),
        'tracked_large':tracked_large,'secret_findings':findings,'largest_selected':sorted(selected,key=lambda f:f['bytes'],reverse=True)[:6]},ensure_ascii=True,indent=2))
    if findings or tracked_large:raise ValueError('Review findings before staging; values never printed')

if __name__=='__main__':main()
