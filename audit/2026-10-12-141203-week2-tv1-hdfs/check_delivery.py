"""Check report structure, line references, command receipts and final paths."""
import ast
import json
import re
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from common import sha256,utcnow
from hdfs_common import new_json

report=AUDIT/'bao-cao-nghiem-thu-tv1-tuan-2-hdfs.md'
text=report.read_text(encoding='utf-8')
assert re.findall(r'^## ([A-G])\.',text,re.M)==list('ABCDEFG')
rows=re.findall(r'^\| (TV1-W2-\d{2}) \|[^\n]+',text,re.M)
assert rows==[f'TV1-W2-{i:02d}' for i in range(1,11)]
assert len(re.findall(r'^\| TV1-W2-\d{2} \|[^\n]*\| ĐẠT \|',text,re.M))==10
section=text.split('## D.')[1].split('## E.')[0]
assert len(re.findall(r'^\| [1-7] \|',section,re.M))==7
evidence=ROOT/'evidence/week2-hdfs/hdfs-385a18d3f03a'
planned_manifest=evidence/'delivery_manifest.json'
checked=0
for file in [report,*sorted((ROOT/'docs').glob('week2_*.md'))]:
    body=file.read_text(encoding='utf-8')
    for target in re.findall(r'\]\(([^)]+)\)',body):
        if target.startswith(('http://','https://')):continue
        # Full Windows path C:/...:line; relative document links also checked.
        match=re.match(r'^(.*):(\d+)$',target)
        path=Path(match.group(1) if match else target)
        if not path.is_absolute():path=(file.parent/path).resolve()
        if path==planned_manifest:continue  # Must be created only after report is frozen.
        assert path.is_file(),str(path)
        if match:assert 1<=int(match.group(2))<=len(path.read_text(encoding='utf-8').splitlines())
        checked+=1
records=json.loads((AUDIT/'commands-final.json').read_text(encoding='utf-8'))['records']
for record in records:
    assert record['cwd']==str(ROOT)
    assert record['argv'] and record['finished_at_utc']>=record['started_at_utc']
    for keys in [('stdout_path','stdout'),('stderr_path','stderr')]:
        value=next((record[key] for key in keys if key in record),None)
        assert value and Path(value).is_file(),record['record_path']
for file in AUDIT.glob('*.py'):ast.parse(file.read_text(encoding='utf-8'),filename=str(file))
new_json(AUDIT/'delivery-paths-checked.json',{'status':'PASS','checked_at_utc':utcnow(),
    'report_sha256':sha256(report),'checked_links':checked,'completed_command_records':len(records),
    'tasks':10,'products':7,'sections':list('ABCDEFG'),
    'planned_manifest':str(planned_manifest),'note':'All existing artifact links checked. The manifest is created next; its later verification receipt is outside the frozen scope.'})
print(f'PASS: A-G, 10 tasks, 7 products, {checked} links, {len(records)} actual command records')
