"""TV2 host runner: isolated evidence, HDFS-only jobs, no TV1 changes."""
import argparse
import json
import os
import shutil
import sys
import uuid
from pathlib import Path
from common import sha256,utcnow
from hdfs_common import ROOT,Ledger,new_json,snapshot_namespaces
from tv2_common import output_roots

TV2_FILES=['Dockerfile.tv2','compose.tv2.yaml','scripts/run_tv2.py','scripts/tv2_pipeline.py','scripts/tv2_common.py',
           'src/tv2_processing.py','src/tv2_analytics.py','src/tv2_clustering.py','scripts/tv2_spark_tests.py','tests/test_tv2_contract.py']
PROTECTED=['src/schemas.py','compose.hdfs.yaml','scripts/hdfs_source.py','scripts/run_hdfs.py','scripts/hdfs_io.py',
           'scripts/hdfs_hash_verify.py','scripts/spark_hdfs_validate.py','config/hdfs/core-site.xml',
           'config/hdfs/hdfs-site.xml','config/flume.conf','config/log4j2.xml','data/processed/movies.csv']


def run(args):
    os.chdir(ROOT)
    hdfs_context=json.loads(Path(args.hdfs_context).read_text(encoding='utf-8'))
    original_source=ROOT/hdfs_context['evidence']/'source_manifest.json'
    source=json.loads(original_source.read_text(encoding='utf-8'));snapshot_namespaces(source)
    if source['hdfs_run_id']!=hdfs_context['run_id']:raise ValueError('HDFS context/source mismatch')
    run_id='tv2-'+uuid.uuid4().hex[:12]
    evidence=ROOT/'evidence/week2-tv2'/run_id;evidence.mkdir(parents=True)
    copied_source=evidence/'source_manifest.json'
    with copied_source.open('xb') as output:output.write(original_source.read_bytes())
    seed=args.seed if args.seed is not None else source['event_manifest']['seed']
    protected={name:sha256(ROOT/name) for name in PROTECTED}
    protected[original_source.relative_to(ROOT).as_posix()]=sha256(original_source)
    context={'run_id':run_id,'hdfs_run_id':source['hdfs_run_id'],'flume_run_id':source['flume_run_id'],
      'project':hdfs_context['project'],'evidence':evidence.relative_to(ROOT).as_posix(),
      'source_manifest':copied_source.relative_to(ROOT).as_posix(),'source_manifest_sha256':sha256(copied_source),
      'hdfs_context':str(Path(args.hdfs_context)),'seed':seed,'driver_memory':args.driver_memory,
      'output_roots':output_roots(source['authority'],run_id),'started_at_utc':utcnow(),
      'protected_tv1_hashes':protected,'code_hashes':{name:sha256(ROOT/name) for name in TV2_FILES}}
    new_json(evidence/'run_context.json',context)
    ledger=Ledger(evidence,{'HDFS_RUN_ID':source['hdfs_run_id']})
    base=['docker','compose','-f','compose.hdfs.yaml','-f','compose.tv2.yaml','-p',context['project']]
    spark=base+['--profile','spark','run','--rm','--no-deps','spark']
    result={'status':'FAIL','run_id':run_id,'evidence':context['evidence'],'checks':{}}
    try:
        if shutil.which('docker') is None:raise RuntimeError('Docker CLI unavailable; no local fallback')
        ledger.command(['docker','version'],'docker-version')
        ledger.command(['docker','info','--format','{{json .}}'],'docker-info')
        ledger.command(base+['config'],'compose-tv2-config')
        code,_,_=ledger.command(['docker','image','inspect','movie-log-spark-tv2:3.5.1-numpy1.24.4'],'tv2-image',False)
        if code:ledger.command(base+['--profile','spark','build','spark'],'tv2-image-build')
        _,ps,_=ledger.command(base+['ps','--all','--format','json'],'hdfs-services')
        services={obj['Service']:obj['State'] for obj in [json.loads(line) for line in ps.splitlines() if line.startswith('{')]}
        if any(services.get(name)!='running' for name in ['namenode','datanode']):raise RuntimeError('HDFS services not running; TV2 will not fall back to local')
        _,safe,_=ledger.command(base+['exec','-T','namenode','hdfs','dfsadmin','-safemode','get'],'hdfs-safe-mode')
        if 'Safe mode is OFF' not in safe:raise RuntimeError('HDFS is in safe mode')
        ledger.command([sys.executable,'-B','-m','unittest','discover','-s','tests','-p','test_tv2*.py','-v'],'tv2-host-tests')
        ledger.command(spark+['--driver-memory','1g','scripts/tv2_spark_tests.py',
                       '--report',context['evidence']+'/spark-fixture-tests.json'],'tv2-spark-fixtures')
        for phase in ['before']:
            ledger.command(spark+['--driver-memory','1g','scripts/hdfs_hash_verify.py','--source-manifest',context['source_manifest'],
                                  '--report',context['evidence']+'/raw-'+phase+'.json'],'raw-hashes-'+phase)
        ledger.command(spark+['--driver-memory',args.driver_memory,'scripts/tv2_pipeline.py',
                              '--run-context',context['evidence']+'/run_context.json'],'tv2-full-pipeline')
        ledger.command(spark+['--driver-memory','1g','scripts/hdfs_hash_verify.py','--source-manifest',context['source_manifest'],
                              '--report',context['evidence']+'/raw-after.json'],'raw-hashes-after')
        load=lambda name:json.loads((evidence/name).read_text(encoding='utf-8'))
        before,after=load('raw-before.json'),load('raw-after.json');pipeline=load('pipeline_summary.json')
        before_files={item['uri']:(item['bytes'],item['sha256']) for item in before['files']}
        after_files={item['uri']:(item['bytes'],item['sha256']) for item in after['files']}
        result['checks']={'pipeline_pass':pipeline['status']=='PASS','raw_unchanged':before['status']==after['status']=='PASS' and before_files==after_files,
             'protected_tv1_unchanged':all(sha256(ROOT/name)==digest for name,digest in protected.items()),
             'no_local_fallback':pipeline['local_fallback'] is False,'fixtures_pass':load('spark-fixture-tests.json')['status']=='PASS'}
        if not all(result['checks'].values()):raise ValueError('Final TV2 acceptance failed: '+str(result['checks']))
        result.update(status='PASS',pipeline=pipeline)
    except Exception as exc:
        result['error']=str(exc)
    result['finished_at_utc']=utcnow();new_json(evidence/'run_status.json',result)
    print(json.dumps(result,ensure_ascii=True,indent=2),flush=True)
    return 0 if result['status']=='PASS' else 1

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--hdfs-context',required=True)
    p.add_argument('--driver-memory',default='1536m')
    p.add_argument('--seed',type=int)
    raise SystemExit(run(p.parse_args()))
