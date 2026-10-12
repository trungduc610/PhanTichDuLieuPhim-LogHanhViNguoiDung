"""Check final references/citations/scope after the manifest's independent verify."""
import json
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from common import sha256,utcnow,write_json

def main():
    target=AUDIT/'artifacts-final.json'
    if target.exists():raise FileExistsError(target)
    sources=json.loads((AUDIT/'final-inspection/source-final.json').read_text(encoding='utf-8'))
    report=AUDIT/'bao-cao-nghiem-thu-tuan-1-recheck.md'
    text=report.read_text(encoding='utf-8')
    issues=[]
    refs=[]
    spark_checks=[]
    for label,run in [('demo','run-aefc814b0b5f'),('main','run-aa6b9eb58dca')]:
        spark=json.loads((ROOT/f'evidence/recheck-20261011-221710/spark-{label}.json').read_text(encoding='utf-8'))
        rec=json.loads((ROOT/f'evidence/{run}/reconciliation.json').read_text(encoding='utf-8'))
        correct=(spark['status']=='PASS' and spark['run_id']==run and not any(spark['errors'].values())
          and spark['source_hashes']['schema']==sha256(ROOT/'src/schemas.py')
          and spark['source_hashes']['smoke']==sha256(ROOT/'scripts/spark_smoke_test.py')
          and spark['logs']['rows']==rec['output']['total'] and spark['movies']['rows']==9742
          and spark['actions']==rec['output']['actions']
          and all(spark['logs'][key]==rec['output'][key] for key in ['users','movies','sessions','watch_seconds','timestamp_min','timestamp_max']))
        spark_checks.append({'run':run,'status':'PASS' if correct else 'FAIL'})
        if not correct:issues.append({'kind':'spark_evidence_or_source_mismatch','run':run})
    for item in sources['artifact_references']:
        name=item['target']
        exists=bool(list(ROOT.glob(name))) if '*' in name else (ROOT/name).exists()
        refs.append(dict(item,exists=exists))
        if not exists:issues.append({'kind':'artifact_reference','reference':item})
    for path,number in re.findall(r'\]\(<([^>]+?)(?::(\d+))?>\)',text):
        source=Path(path)
        if not source.exists():
            issues.append({'kind':'citation_missing','path':path})
        elif number and source.is_file():
            with source.open(encoding='utf-8',errors='strict') as f:
                found=any(i==int(number) for i,_ in enumerate(f,1))
            if not found:issues.append({'kind':'citation_line_missing','path':path,'line':number})
    source_hash_errors=[record['path'] for record in sources['files_read'] if sha256(ROOT/record['path'])!=record['sha256']]
    issues += [{'kind':'managed_source_changed_after_inspection','path':name} for name in source_hash_errors]
    current=text.split('## C.')[1].split('So sánh theo từng')[0]
    matrix=[row for row in current.splitlines() if row.startswith('| TV')]
    states=[row.split('|')[3].strip() for row in matrix]
    if len(matrix)!=22 or states.count('ĐẠT')!=21 or states.count('ĐẠT MỘT PHẦN')!=1:
        issues.append({'kind':'matrix','rows':len(matrix),'states':states})
    products=text.split('## D.')[1].split('## E.')[0]
    product_rows=[row for row in products.splitlines() if re.match(r'^\| \d+ \|',row)]
    if len(product_rows)!=11:issues.append({'kind':'product_rows','rows':len(product_rows)})
    manifest=json.loads((ROOT/'evidence/recheck-20261011-221710/delivery_manifest.json').read_text(encoding='utf-8'))
    for record in sources['files_read']:
        if record['path'] not in manifest['files']:
            issues.append({'kind':'manifest_scope_missing_source','path':record['path']})
    verifies=list((AUDIT/'execution').glob('manifest-verify-*/stdout.txt'))
    if len(verifies)!=1:raise ValueError(verifies)
    verified=json.loads(verifies[0].read_text(encoding='utf-8'))
    if verified['status']!='PASS' or verified['files_checked']!=len(manifest['files']):
        issues.append({'kind':'manifest_verify','result':verified})
    result={'checked_at_utc':utcnow(),'status':'PASS' if not issues else 'FAIL',
       'report':str(report),'report_sha256':sha256(report),'source_files_unchanged':len(sources['files_read']),
       'artifact_references':refs,'matrix_rows':len(matrix),'products':len(product_rows),
       'spark_final_source_checks':spark_checks,
       'manifest_files':len(manifest['files']),'manifest_bytes':sum(v['bytes'] for v in manifest['files'].values()),
       'manifest_verify':verified,'issues':issues}
    write_json(target,result)
    print(json.dumps({k:v for k,v in result.items() if k!='artifact_references'},ensure_ascii=False,indent=2))
    return 0 if not issues else 1


if __name__=='__main__':
    raise SystemExit(main())
