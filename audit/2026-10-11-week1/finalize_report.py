"""Resolve evidence links, validate coverage and preserve baseline files."""
import collections
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
template = (OUT/'report.template.md').read_text(encoding='utf-8')
links = []
def link(m):
    rel, number = m.group(1), int(m.group(2))
    p = ROOT/rel
    assert p.is_file(), f'Missing citation {rel}'
    lines = p.read_bytes().decode('utf-8').split('\n')
    if lines and not lines[-1]:
        lines.pop()
    assert 1 <= number <= len(lines), f'Bad line {rel}:{number}'
    links.append({'path':rel,'line':number})
    return f'[{rel}:{number}](<{p.as_posix()}:{number}>)'
report = re.sub(r'\[\[([^\[\]]+):(\d+)\]\]',link,template)
rows = []
for line in report.splitlines():
    if re.match(r'\| TV[12]-\d\d \|',line):
        cells = [x.strip() for x in line.split('|')[1:-1]]
        assert len(cells)==6, cells
        rows.append({'id':cells[0],'requirement':cells[1],'status':cells[2]})
assert len(rows)==22
assert {x['id'] for x in rows} == {f'TV{member}-{i:02}' for member,n in [(1,12),(2,10)] for i in range(1,n+1)}
counts = collections.Counter(x['status'] for x in rows)
assert dict(counts)=={'ĐẠT':7,'ĐẠT MỘT PHẦN':11,'CHƯA ĐẠT':1,'CHƯA THỂ XÁC MINH':3},counts
products = [line for line in report.splitlines() if re.match(r'\| \d+ \|',line)]
assert len(products)==11
for heading in 'ABCDEFG':
    assert f'## {heading}.' in report
(OUT/'bao-cao-nghiem-thu-tuan-1.md').write_text(report,encoding='utf-8')
(OUT/'task-statuses.json').write_text(json.dumps({'tasks':rows,'counts':dict(counts),'pass_rate_formula':'7/22*100','pass_rate_percent':7/22*100},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
baseline = json.loads((OUT/'inventory.json').read_text(encoding='utf-8'))
changed = [x['path'] for x in baseline if hashlib.sha256((ROOT/x['path']).read_bytes()).hexdigest()!=x['sha256']]
assert not changed,changed
metadata = {}
for name,args in [('status',['git','status','--porcelain=v1','--untracked-files=all']),('log',['git','log','-3','--format=%H %aI %s']),('autocrlf',['git','config','--get','core.autocrlf']),('branch',['git','branch','--show-current'])]:
    p = subprocess.run(args,cwd=ROOT,capture_output=True)
    metadata[name]={'argv':args,'exit_code':p.returncode,'stdout':p.stdout.decode('utf-8'),'stderr':p.stderr.decode('utf-8')}
assert all(not line or line[3:].startswith('audit/') for line in metadata['status']['stdout'].splitlines()),metadata['status']
(OUT/'git-final-metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
quality = {'tasks':22,'products':11,'sections':'A-G','citations_checked':len(links),'status_counts':dict(counts),'baseline_files':len(baseline),'baseline_changed':changed,'only_audit_changes':True,'citation_line_separator':'LF','report_utf8':True}
(OUT/'report-quality-check.json').write_text(json.dumps(quality,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(quality,ensure_ascii=True,indent=2))
