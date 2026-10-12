"""Restart only this run's HDFS services, preserve volumes, verify all content."""
import argparse
import json
import sys
import time
from pathlib import Path
from common import utcnow,sha256
from hdfs_common import ROOT,Ledger,compose,new_json

def properties(text):
    """Compare every VERSION property; Java Properties timestamp comments are not identity."""
    values={}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith(('#','!')):continue
        key,value=line.split('=',1)
        if key in values:raise ValueError('Duplicate storage property '+key)
        values[key]=value
    return values

def review(path,evidence):
    previous=json.loads(Path(path).read_text(encoding='utf-8'))
    before={key:properties(value) for key,value in previous['before'].items()}
    after={key:properties(value) for key,value in previous['after'].items()}
    content=json.loads(Path(previous['content_report']).read_text(encoding='utf-8'))
    okay=before==after and content['status']=='PASS' and previous['format_marker_count_in_entire_logs']==1 and previous['reuse_markers']==2
    result={'status':'PASS' if okay else 'FAIL','checked_at_utc':utcnow(),'run_id':previous['run_id'],
       'reviewed_original_report':str(path),'original_report_sha256':sha256(path),
       'verification_source_sha256':sha256(__file__),'all_storage_properties_unchanged':before==after,
       'before_properties':before,'after_properties':after,'content_report':previous['content_report'],
       'format_marker_count':previous['format_marker_count_in_entire_logs'],'reuse_markers':previous['reuse_markers'],
       'raw_version_text_unchanged':previous['before']==previous['after'],
       'note':'Original FAIL retained. Only timestamp comments changed; all properties and actual data bytes/counts were compared. No second restart or reformat was needed.'}
    new_json(Path(evidence)/'persistence-reviewed.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if okay else 1

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--context',required=True)
    p.add_argument('--review',help='Review an immutable earlier restart record without restarting again')
    a=p.parse_args()
    context=json.loads(Path(a.context).read_text(encoding='utf-8'))
    evidence=ROOT/context['evidence']
    if a.review:return review(a.review,evidence)
    if (evidence/'persistence.json').exists():raise FileExistsError('Use a new check/report for a second restart')
    ledger=Ledger(evidence,{'HDFS_RUN_ID':context['run_id']})
    base=compose(context['project'])
    before={}
    for service,store in [('namenode','name'),('datanode','data')]:
        _,text,_=ledger.command(base+['exec','-T',service,'cat',f'/hdfs/{store}/current/VERSION'],'version-before-restart-'+service)
        before[service]=text
    ledger.command(base+['restart','namenode','datanode'],'restart-own-hdfs')
    ready=False
    for attempt in range(24):
        code,text,_=ledger.command(base+['exec','-T','namenode','hdfs','dfsadmin','-report'],f'restart-ready-{attempt:02d}',False)
        if code==0 and 'Live datanodes (1)' in text:
            _,safe,_=ledger.command(base+['exec','-T','namenode','hdfs','dfsadmin','-safemode','get'],f'restart-safe-{attempt:02d}')
            if 'Safe mode is OFF' in safe:ready=True;break
        time.sleep(5)
    if not ready:raise RuntimeError('HDFS did not recover one live DataNode/safe mode OFF')
    after={}
    for service,store in [('namenode','name'),('datanode','data')]:
        _,text,_=ledger.command(base+['exec','-T',service,'cat',f'/hdfs/{store}/current/VERSION'],'version-after-restart-'+service)
        after[service]=text
    _,logs,folder=ledger.command(base+['logs','--timestamps','--no-color'],'logs-after-restart')
    ledger.command(base+['ps','--all'],'ps-after-restart')
    ledger.command([sys.executable,'-B','scripts/hdfs_io.py','--context',a.context,'--label','content-after-restart'],'verify-all-after-restart')
    verified=json.loads((evidence/'content-after-restart.json').read_text(encoding='utf-8'))
    metadata_equal={key:properties(value) for key,value in before.items()}=={key:properties(value) for key,value in after.items()}
    result={'status':'PASS' if metadata_equal and verified['status']=='PASS' and logs.count('FORMAT_NEW_EMPTY_VOLUME')==1 and logs.count('REUSE_VERIFIED_VOLUME')==2 else 'FAIL',
       'checked_at_utc':utcnow(),'run_id':context['run_id'],'storage_version_unchanged':before==after,
       'all_storage_properties_unchanged':metadata_equal,
       'format_marker_count_in_entire_logs':logs.count('FORMAT_NEW_EMPTY_VOLUME'),
       'reuse_markers':logs.count('REUSE_VERIFIED_VOLUME'),'logs':str(folder/'stdout.txt'),
       'content_report':str(evidence/'content-after-restart.json'),'before':before,'after':after,
       'note':'Controlled restart of this run only; demonstrates persistence, not HA/fault tolerance.'}
    new_json(evidence/'persistence.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
