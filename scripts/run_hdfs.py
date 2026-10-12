"""Start an isolated HDFS demo; never format or import into an existing run."""
import argparse
import json
import os
import time
import uuid
from pathlib import Path
from common import utcnow,sha256
from hdfs_common import ROOT,Ledger,new_json,compose
from hdfs_source import source_manifest

FILES=['compose.hdfs.yaml','config/hdfs/core-site.xml','config/hdfs/hdfs-site.xml','config/hdfs/log4j.properties',
       'scripts/hdfs_service.sh','scripts/run_hdfs.py','scripts/hdfs_common.py','scripts/hdfs_source.py']

def run(a):
    os.chdir(ROOT)
    run_id='hdfs-'+uuid.uuid4().hex[:12]
    evidence=ROOT/'evidence/week2-hdfs'/run_id
    evidence.mkdir(parents=True)
    project='movie-'+run_id
    context={'run_id':run_id,'project':project,'evidence':evidence.relative_to(ROOT).as_posix(),
        'audit':a.audit_dir,'started_at_utc':utcnow(),'ui_url':'http://127.0.0.1:19870',
        'configuration_hashes':{name:sha256(ROOT/name) for name in FILES}}
    new_json(evidence/'context.json',context)
    new_json(ROOT/a.audit_dir/'run-context.json',context)
    ledger=Ledger(evidence,{'HDFS_RUN_ID':run_id})
    base=compose(project)
    state={'runtime':'CHƯA THỂ XÁC MINH','upload':'CHƯA THỂ XÁC MINH','content':'CHƯA THỂ XÁC MINH',
           'spark':'CHƯA THỂ XÁC MINH','e2e':'CHƯA THỂ XÁC MINH'}
    try:
        source_manifest(run_id,evidence)
        ledger.command(['docker','version'],'docker-version')
        ledger.command(['docker','compose','version'],'compose-version')
        ledger.command(['docker','context','show'],'context')
        ledger.command(['docker','image','inspect','apache/hadoop:3.3.6','apache/spark:3.5.1'],'images')
        for volume in ['namenode','datanode']:
            code,_,_=ledger.command(['docker','volume','inspect',project+'_'+volume],'new-volume-'+volume,False)
            if code==0:raise ValueError('Volume already exists; refusing reuse')
        ledger.command(base+['config'],'compose-resolved')
        ledger.command(base+['up','-d','namenode','datanode'],'start-only-hdfs')
        ready=False
        for attempt in range(24):
            code,text,_=ledger.command(base+['exec','-T','namenode','hdfs','dfsadmin','-report'],f'ready-{attempt:02d}',False)
            if code==0 and 'Live datanodes (1)' in text:
                code,safe,_=ledger.command(base+['exec','-T','namenode','hdfs','dfsadmin','-safemode','get'],f'safe-{attempt:02d}',False)
                if code==0 and 'Safe mode is OFF' in safe:
                    ready=True;break
            time.sleep(5)
        if not ready:raise RuntimeError('HDFS failed to reach one live DataNode outside safe mode')
        for service in ['namenode','datanode']:
            ledger.command(base+['exec','-T',service,'hadoop','version'],service+'-version')
            ledger.command(base+['exec','-T',service,'java','-version'],service+'-java')
            ledger.command(base+['exec','-T',service,'cat',f'/hdfs/{"name" if service=="namenode" else "data"}/current/VERSION'],service+'-storage-version')
        ledger.command(base+['ps','--all'],'ps')
        ledger.command(base+['logs','--timestamps','--no-color'],'logs-runtime')
        ledger.command(['docker','volume','inspect',project+'_namenode',project+'_datanode'],'volumes')
        ledger.command(base+['exec','-T','namenode','hdfs','getconf','-confKey','fs.defaultFS'],'default-fs')
        state['runtime']='ĐẠT'
    except Exception as exc:
        state['reason']=str(exc)
        try:ledger.command(base+['logs','--timestamps','--no-color'],'logs-failure',False)
        except Exception:pass
    state.update(finished_at_utc=utcnow(),run_id=run_id,project=project)
    new_json(evidence/'runtime_status.json',state)
    print(json.dumps({'context':context,'status':state},ensure_ascii=False,indent=2))
    return 0 if state['runtime']=='ĐẠT' else 1

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--audit-dir',required=True)
    raise SystemExit(run(p.parse_args()))
