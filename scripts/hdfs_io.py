"""Upload without overwrite and independently parse/hash byte streams from HDFS."""
import argparse
import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path
from common import sha256,utcnow,parse_time
from hdfs_common import ROOT,Ledger,new_json,compose
from validate_pipeline import REQUIRED

def execute(a):
    context=json.loads(Path(a.context).read_text(encoding='utf-8'))
    evidence=ROOT/context['evidence']
    source=json.loads((evidence/'source_manifest.json').read_text(encoding='utf-8'))
    target=evidence/(a.label+'.json')
    if target.exists():raise FileExistsError(target)
    ledger=Ledger(evidence,{'HDFS_RUN_ID':context['run_id']})
    base=compose(context['project'])+['exec','-T','namenode','hdfs']
    result={'status':'FAIL','started_at_utc':utcnow(),'hdfs_run_id':context['run_id'],
       'source_manifest_sha256':sha256(evidence/'source_manifest.json'),
       'source_hashes':{name:sha256(ROOT/name) for name in ['scripts/hdfs_io.py','scripts/hdfs_common.py','scripts/common.py']},
       'files':[],'issues':[]}
    identities=set()
    try:
        if a.upload:
            for record in source['files']:
                local=ROOT/record['local_path']
                if sha256(local)!=record['sha256'] or local.stat().st_size!=record['bytes']:
                    raise ValueError('Local source changed before upload: '+record['local_path'])
            ledger.command(base+['dfs','-mkdir','-p',*source['directories']],'mkdir-namespace')
            for record in source['files']:
                code,_,_=ledger.command(base+['dfs','-test','-e',record['hdfs_path']],'refuse-existing-target',False)
                if code==0:raise FileExistsError(record['hdfs_path'])
                ledger.command(base+['dfs','-put','/project/'+record['local_path'],record['hdfs_path']],'put-'+Path(record['local_path']).name)
            new_json(evidence/'upload_status.json',{'status':'ĐẠT','finished_at_utc':utcnow(),'files':len(source['files']),
               'source_manifest_sha256':sha256(evidence/'source_manifest.json'),'note':'Upload is complete; content verification is a separate stage.'})
        _,listing,_=ledger.command(base+['dfs','-ls','-R','/movie-log'],'list-namespace')
        listed={}
        for line in listing.splitlines():
            fields=line.split(None,7)
            if line.startswith('-') and len(fields)==8:
                listed[fields[7]]={'bytes':int(fields[4]),'replication':int(fields[1])}
        expected={record['hdfs_path']:record for record in source['files']}
        result['missing_files']=sorted(set(expected)-set(listed))
        result['unexpected_files']=sorted(set(listed)-set(expected))
        if result['missing_files'] or result['unexpected_files']:
            raise ValueError('HDFS file list differs from source manifest')
        ledger.command(base+['dfs','-du','-s','/movie-log/raw'],'du-raw')
        _,admin,_=ledger.command(base+['dfsadmin','-report'],'dfsadmin-report')
        _,safe,_=ledger.command(base+['dfsadmin','-safemode','get'],'safe-mode')
        _,fsck,_=ledger.command(base+['fsck','/movie-log','-files','-blocks','-locations'],'fsck-files-blocks')
        result.update(live_datanodes='Live datanodes (1)' in admin,safe_mode_off='Safe mode is OFF' in safe,
                      fsck_healthy='is HEALTHY' in fsck,fsck_log=fsck)
        if not result['live_datanodes'] or not result['safe_mode_off'] or not result['fsck_healthy']:
            raise ValueError('HDFS is not healthy/outside safe mode with one live DataNode')
        totals={'movies':0,'logs':0,'log_bytes':0,'duplicate_ids':0,'invalid_records':0}
        samples=[]
        # Each file is read using hdfs dfs -cat; stdout stays binary (no newline conversion).
        for record in source['files']:
            argv=base+['dfs','-cat',record['hdfs_path']]
            folder,command=ledger.start(argv,'cat-'+Path(record['hdfs_path']).name)
            digest=hashlib.sha256(); size=rows=0
            header=None
            with (folder/'stdout.bin').open('xb') as output,(folder/'stderr.txt').open('xb') as err:
                proc=subprocess.Popen(argv,cwd=ROOT,env=ledger.env,stdout=subprocess.PIPE,stderr=err)
                for number,line in enumerate(proc.stdout,1):
                    output.write(line); digest.update(line); size+=len(line)
                    if number<=3:samples.append({'uri':source['authority']+record['hdfs_path'],'line':number,'text':line.decode('utf-8',errors='strict').rstrip('\n')})
                    if record['kind']=='logs':
                        rows+=1
                        try:
                            if not line.endswith(b'\n'):raise ValueError('Missing final newline')
                            event=json.loads(line.decode('utf-8',errors='strict'))
                            if not isinstance(event,dict) or set(event)!=REQUIRED:raise ValueError('Unexpected log fields')
                            for key in ['eventId','userId','sessionId','runId','action','timestamp','durationSource']:
                                if not isinstance(event[key],str) or not event[key].strip():raise ValueError('Invalid string '+key)
                            for key in ['movieId','watchDuration','sequenceNumber','simulatedMovieDuration']:
                                if type(event[key]) is not int or not 0<=event[key]<=2**63-1:raise ValueError('Invalid integer '+key)
                            if not event['timestamp'].endswith('Z'):raise ValueError('Timestamp must be UTC Z')
                            parse_time(event['timestamp'])
                            if event['isSynthetic'] is not True or event['durationSource']!='synthetic':raise ValueError('Invalid provenance')
                            if event['action'] not in ['view','play','pause','stop','complete']:raise ValueError('Invalid action')
                            if not 3600<=event['simulatedMovieDuration']<=10800 or event['watchDuration']>event['simulatedMovieDuration']:raise ValueError('Invalid duration range')
                            if event['action'] in ['view','play'] and event['watchDuration']!=0:raise ValueError('Invalid view/play duration')
                            if event['action'] in ['pause','stop','complete'] and event['watchDuration']<=0:raise ValueError('Invalid terminal duration')
                            if event['eventId'] in identities:totals['duplicate_ids']+=1
                            identities.add(event['eventId'])
                        except (ValueError,TypeError,KeyError,UnicodeError) as exc:
                            totals['invalid_records']+=1
                            if len(result['issues'])<20:result['issues'].append({'uri':source['authority']+record['hdfs_path'],'line':number,'error':str(exc)})
                proc.stdout.close()
                code=proc.wait()
            command.update(exit_code=code,finished_at_utc=utcnow(),stdout=str(folder/'stdout.bin'),stdout_sha256=digest.hexdigest(),stdout_bytes=size)
            new_json(folder/'finished.json',command)
            if code:raise RuntimeError('hdfs cat failed: '+record['hdfs_path'])
            if record['kind']=='movies':
                with (folder/'stdout.bin').open(encoding='utf-8',errors='strict',newline='') as f:
                    reader=csv.DictReader(f,strict=True)
                    if reader.fieldnames!=['movieId','title','genres','releaseYear']:raise ValueError('Invalid HDFS CSV header')
                    for row in reader:
                        if None in row or any(value is None for value in row.values()):raise ValueError('Malformed HDFS CSV')
                        rows+=1
            measured={'uri':source['authority']+record['hdfs_path'],'local_path':record['local_path'],
              'bytes':size,'sha256':digest.hexdigest(),'records':rows,'replication':listed[record['hdfs_path']]['replication'],
              'empty':size==0,'command':str(folder/'finished.json')}
            measured['matches_source']=(size==record['bytes']==listed[record['hdfs_path']]['bytes'] and digest.hexdigest()==record['sha256'] and rows==record['expected_records'])
            result['files'].append(measured)
            totals[record['kind']]+=rows
            if record['kind']=='logs':totals['log_bytes']+=size
            if not measured['matches_source'] or measured['replication']!=1:raise ValueError('HDFS bytes/hash/count/replication mismatch')
        result.update(totals=totals,unique_event_ids=len(identities),total_bytes=sum(r['bytes'] for r in result['files']))
        new_json(evidence/(a.label+'-samples.json'),samples)
        if totals['movies']!=source['expected_movies'] or totals['logs']!=source['expected_logs'] or totals['log_bytes']!=source['expected_log_bytes'] or totals['invalid_records'] or totals['duplicate_ids']:
            raise ValueError('Full HDFS parsing counts/quality differ from source expectations')
        result['status']='PASS'
    except Exception as exc:
        result['error']=str(exc)
    result['finished_at_utc']=utcnow()
    new_json(target,result)
    print(json.dumps({key:value for key,value in result.items() if key not in ['files','fsck_log']},ensure_ascii=False,indent=2))
    return 0 if result['status']=='PASS' else 1

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--context',required=True)
    p.add_argument('--upload',action='store_true')
    p.add_argument('--label',required=True,help='NEW verification report name')
    raise SystemExit(execute(p.parse_args()))
