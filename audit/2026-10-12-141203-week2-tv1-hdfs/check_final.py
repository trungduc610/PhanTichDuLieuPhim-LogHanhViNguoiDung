"""Independent consistency/preservation checks on final Week 2 artifacts."""
import ast
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from common import sha256,utcnow
from hdfs_common import new_json
from create_delivery_manifest import verify as verify_week1


def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def main():
    evidence=ROOT/'evidence/week2-hdfs/hdfs-385a18d3f03a'
    context=load(evidence/'context.json')
    source=load(evidence/'source_manifest.json')
    spark=load(evidence/'spark-hdfs.json')
    hashes=load(evidence/'final-hdfs-hashes.json')
    content=load(evidence/'content-after-restart.json')
    persistence=load(evidence/'persistence-reviewed.json')
    live=load(evidence/'final-runtime.json')
    issues=[]
    before=load(AUDIT/'inventory-before.json')
    for record in before:
        file=ROOT/record['path']
        if not file.is_file() or file.stat().st_size!=record['bytes'] or sha256(file)!=record['sha256']:
            issues.append({'path':record['path'],'error':'preexisting file changed or missing'})
    old=verify_week1(ROOT/'evidence/recheck-20261011-221710/delivery_manifest.json')
    if old['status']!='PASS':issues.append({'error':'Week 1 manifest failed','details':old})
    for mapping in [context['configuration_hashes'],spark['source_hashes'],content['source_hashes']]:
        for rel,digest in mapping.items():
            if sha256(ROOT/rel)!=digest:issues.append({'path':rel,'error':'current source differs from executed source'})
    for file,receipt,key in [
        (ROOT/'scripts/hdfs_restart_verify.py',persistence,'verification_source_sha256'),
        (ROOT/'scripts/hdfs_hash_verify.py',hashes,'verification_source_sha256'),
        (AUDIT/'final_live.py',live,'verification_source_sha256'),
        (ROOT/'scripts/hdfs_service.sh',load(evidence/'guard-tests.json'),'service_script_sha256')]:
        if sha256(file)!=receipt[key]:issues.append({'path':str(file),'error':'receipt verification source changed'})
    assert source['status']==hashes['status']==content['status']==spark['status']==persistence['status']==live['status']=='PASS'
    assert source['hdfs_run_id']==content['hdfs_run_id']==spark['hdfs_run_id']==hashes['hdfs_run_id']==context['run_id']
    assert source['flume_run_id']==spark['flume_run_id']=='run-aa6b9eb58dca'
    assert all(r['source_manifest_sha256']==sha256(evidence/'source_manifest.json') for r in [hashes,content,spark])
    assert spark['verification_sha256']==sha256(evidence/'content-after-restart.json')
    assert persistence['original_report_sha256']==sha256(evidence/'persistence.json')
    assert persistence['all_storage_properties_unchanged'] and persistence['format_marker_count']==1 and persistence['reuse_markers']==2
    assert not any(spark['errors'].values()) and spark['movies']['rows']==source['expected_movies']==9742
    assert spark['logs']['rows']==source['expected_logs']==1000000 and spark['local_fallback'] is False
    assert hashes['total_bytes']==content['total_bytes']==343872495
    assert spark['runtime']['filesystem_class']==hashes['filesystem_class']=='org.apache.hadoop.hdfs.DistributedFileSystem'
    assert set(spark['observed_log_files'])=={source['authority']+f['hdfs_path'] for f in source['files'] if f['kind']=='logs' and f['bytes']}
    expected={source['authority']+f['hdfs_path']:f for f in source['files']}
    for report in [content,hashes]:
        assert {f['uri'] for f in report['files']}==set(expected)
        for measured in report['files']:
            frozen=expected[measured['uri']]
            assert measured['bytes']==frozen['bytes'] and measured['sha256']==frozen['sha256'] and measured['replication']==1
    for file in source['files']:
        local=ROOT/file['local_path']
        assert local.stat().st_size==file['bytes'] and sha256(local)==file['sha256']
    assert load(evidence/'guard-tests.json')['status']=='PASS'
    refused=load(evidence/'overwrite-refused.json')
    # str(FileExistsError(path)) is just the path, not the class name.
    assert refused['status']=='FAIL' and refused['error']==source['files'][0]['hdfs_path']
    refusal_commands=[]
    for file in (evidence/'commands').glob('*/finished.json'):
        record=load(file)
        if refused['started_at_utc']<=record['started_at_utc']<=refused['finished_at_utc']:
            refusal_commands.append(record)
    assert any('-test' in r['argv'] and '-e' in r['argv'] and r['exit_code']==0 for r in refusal_commands)
    assert not any('-put' in r['argv'] for r in refusal_commands)
    unit=next((AUDIT/'execution').glob('unit-tests-*/command.json'))
    assert load(unit)['exit_code']==0
    unitlog=unit.parent/'stderr.txt'
    assert 'Ran 21 tests' in unitlog.read_text(encoding='utf-8') and re.search(r'\nOK\s*$',unitlog.read_text(encoding='utf-8'))
    inspected=[]
    review=[]
    selected=[ROOT/'compose.hdfs.yaml',ROOT/'src/schemas.py',ROOT/'scripts/spark_smoke_test.py',
              ROOT/'scripts/run_hdfs.py',ROOT/'scripts/spark_hdfs_validate.py',ROOT/'scripts/create_hdfs_manifest.py',
              ROOT/'tests/test_hdfs_properties.py']
    selected+=sorted((ROOT/'config/hdfs').glob('*'))+sorted((ROOT/'scripts').glob('hdfs_*'))+sorted((ROOT/'docs').glob('week2_*.md'))
    for file in sorted(set(selected)):
        text=file.read_text(encoding='utf-8')
        if file.suffix=='.py':ast.parse(text,filename=str(file))
        if file.suffix=='.xml':ET.fromstring(text)
        rel=file.relative_to(ROOT).as_posix()
        inspected.append({'path':rel,'bytes':file.stat().st_size,'sha256':sha256(file),'lines':len(text.splitlines())})
        review.append('\n### '+rel+'\n'+'\n'.join(f'{i:04d}: {line}' for i,line in enumerate(text.splitlines(),1)))
    assert all((ROOT/'docs'/name).is_file() for name in ['week2_tv1_hdfs_report.md','week2_tv2_hdfs_handoff.md','week2_system_architecture.md'])
    assert (evidence/'screenshots/namenode-full-page.jpg').stat().st_size>100000
    with (AUDIT/'source-review-final.txt').open('x',encoding='utf-8') as file:file.write('\n'.join(review))
    new_json(AUDIT/'artifacts-final.json',{'status':'PASS' if not issues else 'FAIL','checked_at_utc':utcnow(),
        'preexisting_files_checked':len(before),'preexisting_changes':issues,'week1_manifest':old,
        'executed_source_hashes_match':not issues,'reviewed_source_docs':inspected,
        'source_review':'source-review-final.txt','final_remote_files_checked':len(expected)})
    if issues:raise ValueError(issues)
    stages={'runtime':'ĐẠT','upload':'ĐẠT','content':'ĐẠT','spark':'ĐẠT','e2e':'ĐẠT'}
    receipts=['context.json','source_manifest.json','runtime_status.json','upload_status.json','content-import.json',
              'content-after-restart.json','persistence-reviewed.json','spark-hdfs.json','final-hdfs-hashes.json','final-runtime.json']
    new_json(evidence/'acceptance_status.json',{'status':'ĐẠT','checked_at_utc':utcnow(),'run_id':context['run_id'],
        'stages':stages,'evidence_sha256':{name:sha256(evidence/name) for name in receipts},
        'source_config_matches_executed':True,'preexisting_files_preserved':len(before),
        'note':'Final stage state; earlier runtime_status remains the immutable startup checkpoint. Technical TV1 acceptance does not claim TV2/group approval or all Week 2 completion.'})
    print(json.dumps({'status':'PASS','preexisting_files_preserved':len(before),'week1_manifest_files':old['files_checked'],
                      'reviewed_sources':len(inspected),'remote_files':len(expected),'stages':stages},ensure_ascii=True))


if __name__=='__main__':main()
