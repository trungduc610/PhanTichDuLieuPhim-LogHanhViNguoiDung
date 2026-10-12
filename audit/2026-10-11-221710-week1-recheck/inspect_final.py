"""Independent read-only inspection; creates new audit evidence only."""
import argparse
import ast
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from common import sha256, utcnow, write_json
from movie_quality import inspect_movies

def new_json(name,value):
    path=AUDIT/name
    if path.exists():
        raise FileExistsError(path)
    write_json(path,value)

def main():
    global AUDIT
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--demo',required=True)
    p.add_argument('--main',required=True)
    p.add_argument('--output-dir')
    a=p.parse_args()
    before=json.loads((AUDIT/'inventory-before.json').read_text(encoding='utf-8'))
    if a.output_dir:
        AUDIT=(ROOT/a.output_dir).resolve()
        if not AUDIT.is_relative_to(ROOT/'audit'):
            raise ValueError('Output audit must stay under project audit directory')
        AUDIT.mkdir(parents=True,exist_ok=False)
    changed,protected_errors,unchanged=[],[],[]
    for record in before:
        path=ROOT/record['path']
        if path.is_file() and sha256(path)==record['sha256']:
            unchanged.append(record['path'])
        else:
            changed.append(record['path'])
            if record['path'].startswith(('evidence/','audit/2026-10-11-week1/','data/','logs/')):
                protected_errors.append(record['path'])
    new_json('preservation-final.json',{'checked_at_utc':utcnow(),'baseline_files':len(before),
        'unchanged_files':len(unchanged),'changed_authorized_source_docs':changed,
        'protected_history_errors':protected_errors,'status':'PASS' if not protected_errors else 'FAIL'})
    managed=[ROOT/name for name in ['README.md','Dockerfile','compose.yaml','requirements.txt','.gitignore','.gitattributes','.dockerignore']]
    for folder in ['scripts','src','tests','config','docs']:
        managed+=sorted(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    numbered=AUDIT/'numbered-final-project-files.txt'
    if numbered.exists():
        raise FileExistsError(numbered)
    inventory,source_errors,path_checks=[],[],[]
    with numbered.open('x',encoding='utf-8') as out:
        for path in managed:
            text=path.read_text(encoding='utf-8',errors='strict')
            rel=path.relative_to(ROOT).as_posix()
            inventory.append({'path':rel,'bytes':path.stat().st_size,'sha256':sha256(path),'lines':len(text.splitlines())})
            out.write('\nFILE '+rel+'\n')
            for line,body in enumerate(text.splitlines(),1):
                out.write(f'{line:5d}: {body}\n')
            if path.suffix=='.py':
                try:
                    ast.parse(text,filename=rel)
                except SyntaxError as exc:
                    source_errors.append(str(exc))
            if path.suffix=='.md':
                for match in re.finditer(r'`((?:data|evidence|audit|scripts|src|config|docs)/[^`\n]+)`',text):
                    target=match.group(1)
                    if '<' in target or 'DEMO-MOI' in target or 'run-id' in target or target.startswith(('data/raw-new','data/runs/run-...')):
                        continue
                    if target.endswith('-new.json') or '-repeat' in target or 'recheck-new' in target or 'repeat-validation' in target:
                        continue # Explicit NEW command destinations, not delivered artifacts.
                    present=bool(list(ROOT.glob(target))) if '*' in target else (ROOT/target).exists()
                    path_checks.append({'source':rel,'line':text[:match.start()].count('\n')+1,'target':target,'exists':present})
    new_json('source-final.json',{'checked_at_utc':utcnow(),'files_read':inventory,'ast_errors':source_errors,
        'artifact_references':path_checks,'missing_references':[r for r in path_checks if not r['exists']],
        'note':'All managed source/config/tests/docs decoded and read in full; referenced fresh output destinations excluded. Delivery manifest/report are authored after this inspection.'})
    raw=[]
    for path in sorted((ROOT/'data/raw/ml-latest-small').glob('*.csv')):
        with path.open(encoding='utf-8',errors='strict',newline='') as f:
            reader=csv.reader(f,strict=True)
            header=next(reader)
            rows=bad=0
            for row in reader:
                rows+=1
                bad+=len(row)!=len(header)
        raw.append({'path':path.relative_to(ROOT).as_posix(),'header':header,'rows':rows,'bad_field_count':bad,
                    'bytes':path.stat().st_size,'sha256':sha256(path)})
    _,movie=inspect_movies(ROOT/'data/processed/movies.csv')
    new_json('dataset-independent.json',{'checked_at_utc':utcnow(),'csv_parser':'Python csv.reader strict UTF-8, all records',
        'raw_csv':raw,'processed_movies':movie,'zip_bytes':(ROOT/'data/raw/ml-latest-small.zip').stat().st_size,
        'zip_sha256':sha256(ROOT/'data/raw/ml-latest-small.zip'),'license_sha256':sha256(ROOT/'data/raw/ml-latest-small/README.txt'),
        'status':'PASS' if movie['status']=='PASS' and not any(r['bad_field_count'] for r in raw) else 'FAIL'})
    runs=[]
    for run in [a.demo,a.main]:
        folder=ROOT/'evidence'/run
        status=json.loads((folder/'status.json').read_text(encoding='utf-8'))
        rec=json.loads((folder/'reconciliation.json').read_text(encoding='utf-8'))
        hash_errors=[name for name,h in status['source_config_hashes'].items() if sha256(ROOT/name)!=h]
        hashes=[f['path'] for f in rec['output_files'] if not Path(f['path']).is_file() or sha256(f['path'])!=f['sha256'] or Path(f['path']).stat().st_size!=f['bytes']]
        sink=ROOT/'data/runs'/run/'output'
        names={Path(f['path']).name for f in rec['output_files']}
        extra=[p.name for p in sink.iterdir() if p.is_file() and p.name not in names]
        log=(folder/'flume-operational.log').read_text(encoding='utf-8')
        heap=re.findall(r'MaxHeapSize\s+:=\s+(\d+)',log)
        metrics=json.loads((folder/'metrics-final.json').read_text(encoding='utf-8'))
        counters={'accepted':int(metrics['SOURCE.r1']['EventAcceptedCount']),
                  'put':int(metrics['CHANNEL.c1']['EventPutSuccessCount']),
                  'take':int(metrics['CHANNEL.c1']['EventTakeSuccessCount']),
                  'sink':int(metrics['SINK.k1']['EventDrainSuccessCount']),
                  'channel_remaining':int(metrics['CHANNEL.c1']['ChannelSize'])}
        cmd=json.loads((folder/'commands.json').read_text(encoding='utf-8'))
        nonzero=[r for r in cmd['commands'] if r.get('exit_code')!=0]
        expected=rec['input']['total']
        okay=(status['status']==rec['status']=='PASS' and not hash_errors and not hashes and not extra
              and heap==['536870912'] and counters['channel_remaining']==0
              and all(counters[k]==expected for k in ['accepted','put','take','sink']) and not nonzero)
        runs.append({'run':run,'status':'PASS' if okay else 'FAIL','source_hash_errors':hash_errors,
                     'sink_hash_errors':hashes,'unexpected_files':extra,'actual_agent_max_heap_bytes':heap,
                     'counters':counters,'nonzero_commands':nonzero,'sink_file_summary':rec['output_file_summary']})
    new_json('runs-independent.json',{'checked_at_utc':utcnow(),'runs':runs,'status':'PASS' if all(r['status']=='PASS' for r in runs) else 'FAIL'})
    git={}
    for key,argv in [('revision',['git','rev-parse','HEAD']),('branch',['git','branch','--show-current']),
                     ('status',['git','status','--porcelain=v1']),('diff_stat',['git','diff','--stat']),
                     ('diff',['git','diff','--no-ext-diff'])]:
        proc=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
        git[key]={'argv':argv,'cwd':str(ROOT),'exit_code':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr}
    new_json('git-final.json',{'checked_at_utc':utcnow(),**git})
    print(json.dumps({'history_preserved':not protected_errors,'source_files_read':len(inventory),
                      'ast_errors':source_errors,'reference_issues':[r for r in path_checks if not r['exists']],
                      'raw_rows':{r['path']:r['rows'] for r in raw},'runs':runs},ensure_ascii=False,indent=2))
    return 0 if not protected_errors and not source_errors and all(r['status']=='PASS' for r in runs) else 1


if __name__=='__main__':
    raise SystemExit(main())
