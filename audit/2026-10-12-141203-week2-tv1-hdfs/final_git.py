"""Record final git state; no index/commit mutations."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from hdfs_common import Ledger,new_json
from common import utcnow
evidence=ROOT/'evidence/week2-hdfs/hdfs-385a18d3f03a'
ledger=Ledger(evidence)
records=[]
for label,argv in [('final-git-revision',['git','rev-parse','HEAD']),
                   ('final-git-status',['git','status','--porcelain=v1']),
                   ('final-git-diff-stat',['git','diff','--stat']),
                   ('final-git-diff',['git','diff','--no-ext-diff'])]:
    code,text,folder=ledger.command(argv,label)
    records.append({'command':str(folder/'finished.json'),'exit_code':code})
new_json(evidence/'git-final.json',{'checked_at_utc':utcnow(),'commands':records,
                                  'note':'Tracked modifications were already present at baseline. Week 2 adds new files only; final-artifact check verifies every baseline file byte-for-byte.'})
