"""Isolated container fixtures prove volume guards; never data/Flume evidence."""
import argparse
import json
from pathlib import Path
from hdfs_common import ROOT,Ledger,new_json
from common import sha256

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence',required=True)
    a=p.parse_args()
    evidence=Path(a.evidence)
    ledger=Ledger(evidence)
    tests=[]
    cases=[
       ('nonempty_unformatted','touch /hdfs/name/fixture-marker; bash /project/scripts/hdfs_service.sh namenode','Refusing non-empty unformatted'),
       ('wrong_cluster','mkdir -p /hdfs/name/current; printf "clusterID=foreign-cluster\\n" > /hdfs/name/current/VERSION; bash /project/scripts/hdfs_service.sh namenode','Cluster ID mismatch'),
       ('invalid_role','bash /project/scripts/hdfs_service.sh invalid-role','Unknown role')]
    for name,script,expected in cases:
        argv=['docker','run','--rm','--user','0:0','--tmpfs','/hdfs/name','--mount',f'type=bind,source={ROOT},target=/project,readonly',
              '-e','HDFS_RUN_ID=hdfs-000000000000','--entrypoint','bash',
              'apache/hadoop@sha256:62a22627f35a1bbf29c721192c02fe311c93749cc43d51df01792b2ac40ff144','-c',script]
        code,text,folder=ledger.command(argv,name,False)
        passed=code==1 and expected in text and 'FORMAT_NEW_EMPTY_VOLUME' not in text
        tests.append({'name':name,'passed':passed,'exit_code':code,'commands':str(folder),
                      'fixture_only':True,'never_flume_evidence':True})
    new_json(evidence/'guard-tests.json',{'status':'PASS' if all(t['passed'] for t in tests) else 'FAIL',
        'service_script_sha256':sha256(ROOT/'scripts/hdfs_service.sh'),'tests':tests,
        'note':'Every test uses its own disposable tmpfs, never the actual NameNode/DataNode volumes.'})
    print(json.dumps(tests,ensure_ascii=False,indent=2))
    return 0 if all(t['passed'] for t in tests) else 1

if __name__=='__main__':raise SystemExit(main())
