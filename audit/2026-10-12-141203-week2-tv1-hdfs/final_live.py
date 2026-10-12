"""Final read-only runtime receipts; private project only."""
import json
import re
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from hdfs_common import Ledger,compose,new_json
from common import utcnow,sha256
evidence=ROOT/'evidence/week2-hdfs/hdfs-385a18d3f03a'
context=json.loads((evidence/'context.json').read_text(encoding='utf-8'))
ledger=Ledger(evidence,{'HDFS_RUN_ID':context['run_id']})
base=compose(context['project'])
records={}
for label,argv in [
    ('final-docker-info',['docker','info']),
    ('final-context',['docker','context','show']),
    ('final-spark-image',['docker','image','inspect','apache/spark:3.5.1']),
    ('final-ps',base+['ps','--all','--format','json']),
    ('final-compose',base+['config']),
    ('final-list',base+['exec','-T','namenode','hdfs','dfs','-ls','-R','/movie-log']),
    ('final-du',base+['exec','-T','namenode','hdfs','dfs','-du','-s','/movie-log/raw']),
    ('final-report',base+['exec','-T','namenode','hdfs','dfsadmin','-report']),
    ('final-safe',base+['exec','-T','namenode','hdfs','dfsadmin','-safemode','get']),
    ('final-fsck',base+['exec','-T','namenode','hdfs','fsck','/movie-log','-files','-blocks','-locations']),
    ('final-logs',base+['logs','--timestamps','--no-color']),
]:
    code,text,folder=ledger.command(argv,label)
    records[label]={'command':str(folder/'finished.json'),'stdout':str(folder/'stdout.txt'),'exit_code':code}
    if label=='final-report':
        # dfsadmin omits the entire Dead datanodes section when its count is 0.
        dead=re.search(r'Dead datanodes \((\d+)\)',text)
        assert 'Live datanodes (1)' in text and (int(dead.group(1)) if dead else 0)==0
    if label=='final-safe':assert 'Safe mode is OFF' in text
    if label=='final-fsck':assert 'is HEALTHY' in text and 'Total blocks (validated):\t16' in text
new_json(evidence/'final-runtime.json',{'status':'PASS','checked_at_utc':utcnow(),'run_id':context['run_id'],'verification_source_sha256':sha256(__file__),'commands':records})
print('PASS: final live runtime/list/bytes/blocks receipts saved')
