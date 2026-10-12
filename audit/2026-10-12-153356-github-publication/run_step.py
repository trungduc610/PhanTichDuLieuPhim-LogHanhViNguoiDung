"""Execute one authorized step, preserving argv/environment/exit/stdout/stderr."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
AUDIT = Path(__file__).resolve().parent
def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()
if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--label',required=True)
    parser.add_argument('--inventory',action='store_true')
    parser.add_argument('argv',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    if args.inventory:
        entries=[]
        for p in sorted(ROOT.rglob('*')):
            if p.is_file() and '.git' not in p.relative_to(ROOT).parts and not p.is_relative_to(AUDIT):
                entries.append({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
        write(AUDIT/'inventory-before.json',entries)
        write(AUDIT/'instructions-before.json',{'ancestors_checked':[str(p/'AGENTS.md') for p in [ROOT,*ROOT.parents]],'found':[str(p/'AGENTS.md') for p in [ROOT,*ROOT.parents] if (p/'AGENTS.md').exists()]})
        print('Inventory files:',len(entries))
        sys.exit(0)
    argv=args.argv[1:] if args.argv and args.argv[0]=='--' else args.argv
    if not argv:
        parser.error('Command required after --')
    folder=AUDIT/'execution'/f'{args.label}-{uuid.uuid4().hex[:8]}'
    folder.mkdir(parents=True)
    env=os.environ.copy()
    env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8')
    temporary=AUDIT/'temporary'
    temporary.mkdir(exist_ok=True)
    for k in ['TMP','TEMP','TMPDIR']:
        env[k]=str(temporary)
    record={'argv':argv,'cwd':str(ROOT),'started_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version,'python_executable':sys.executable,'os':platform.platform(),'environment':{k:env.get(k) for k in ['DOCKER_HOST','DOCKER_CONTEXT','DOCKER_CONFIG','RUN_DIR','LOG_DIR','TMP','PYTHONDONTWRITEBYTECODE']},'stdout_path':str(folder/'stdout.txt'),'stderr_path':str(folder/'stderr.txt')}
    write(folder/'command.json',record)
    try:
        with (folder/'stdout.txt').open('wb') as out,(folder/'stderr.txt').open('wb') as err:
            proc=subprocess.run(argv,cwd=ROOT,env=env,stdout=out,stderr=err)
        record['exit_code']=proc.returncode
    except OSError as exc:
        record.update(exit_code=None,error=str(exc))
    record['finished_at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    write(folder/'command.json',record)
    print(json.dumps({'folder':str(folder),'exit_code':record['exit_code'],'error':record.get('error')},ensure_ascii=True),flush=True)
    sys.exit(0 if record['exit_code']==0 else 1)
