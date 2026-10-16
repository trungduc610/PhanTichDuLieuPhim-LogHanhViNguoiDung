import sys,json,subprocess,hashlib
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'scripts'))
from hdfs_common import ROOT,Ledger,new_json
from common import utcnow,sha256
folder=ROOT/'evidence/dashboard-sha-checkout/20261016-37f95dc'
folder.mkdir(parents=True,exist_ok=False)
ledger=Ledger(folder)
revision=subprocess.check_output(['git','rev-parse','HEAD']).decode().strip()
release='evidence/week3-tv2/tv2-aae83326c1ab'
results=[]

def execute(argv,label,expected=0):
 code,text,record=ledger.command(argv,label,False)
 if code!=expected:raise RuntimeError(label+' unexpected exit '+str(code)+'; '+str(record))
 return text,record

def clone_mode(name,autocrlf,initial):
 clone=ROOT/'work'/('sha-'+name+'-37f95dc')
 if clone.exists():raise FileExistsError(clone)
 execute(['git','clone','--local','--no-hardlinks','--no-checkout',str(ROOT),str(clone)],name+'-clone')
 execute(['git','-C',str(clone),'config','core.autocrlf',autocrlf],name+'-autocrlf')
 execute(['git','-C',str(clone),'config','core.longpaths','true'],name+'-longpaths')
 execute(['git','-C',str(clone),'checkout','--detach',initial],name+'-checkout')
 return clone

for name,mode in [('fresh-lf','false'),('fresh-crlf','true')]:
 clone=clone_mode(name,mode,revision)
 execute([sys.executable,'-B',str(clone/'scripts/create_delivery_manifest.py'),'--verify',str(clone/release/'delivery-manifest.json')],name+'-delivery')
 execute(['node',str(clone/'dashboard/scripts/repair-data.mjs'),'--check'],name+'-check')
 execute(['node',str(clone/'dashboard/scripts/sync-data.mjs')],name+'-sync')
 results.append({'mode':name,'status':'PASS','core_autocrlf':mode,'run_id':'tv2-aae83326c1ab','manifest_files':162})

clone=clone_mode('old','true','f94fc8afdcc43454ac42700c67ae5b8b12b07cce')
execute(['git','-C',str(clone),'checkout','--detach',revision],'old-upgrade')
code,text,record=ledger.command(['node',str(clone/'dashboard/scripts/sync-data.mjs')],'old-pre-repair-sync',False)
# If this Git version already refreshed attributes, explicitly simulate the
# observed stale checkout, always inside this isolated disposable clone.
simulated=False
if code==0:
 target=clone/release/'run_status.json';data=target.read_bytes();target.write_bytes(data.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'));simulated=True
 code,text,record=ledger.command(['node',str(clone/'dashboard/scripts/sync-data.mjs')],'old-simulated-pre-repair-sync',False)
assert code!=0
assert 'SHA-256' in (record/'stderr.txt').read_text(encoding='utf-8')
execute(['node',str(clone/'dashboard/scripts/repair-data.mjs'),'--check'],'old-repair-preview',2)
execute(['node',str(clone/'dashboard/scripts/repair-data.mjs')],'old-repair')
execute(['node',str(clone/'dashboard/scripts/repair-data.mjs'),'--check'],'old-after-check')
execute(['node',str(clone/'dashboard/scripts/sync-data.mjs')],'old-after-sync')
execute([sys.executable,'-B',str(clone/'scripts/create_delivery_manifest.py'),'--verify',str(clone/release/'delivery-manifest.json')],'old-after-delivery')
backups=list((clone/'work/sha-checkout-repair').glob('*/repair.json'));assert len(backups)==1
journal=json.loads(backups[0].read_text(encoding='utf-8'));assert journal['status']=='RESTORED'
for item in journal['files']:
 saved=backups[0].parent/item['path']
 assert sha256(saved)==item['beforeSha256'] and sha256(clone/item['path'])==item['sha256']
new_json(folder/'old-checkout-restoration.json',journal)
results.append({'mode':'old-checkout','status':'PASS','core_autocrlf':'true','native_upgrade_reproduced':not simulated,'restored_files':len(journal['files']),'backup_hashes_verified':True})
# Run all unit contracts against actual committed source/data from a clean
# checkout. These tests need Node stdlib only, not node_modules.
fresh=ROOT/'work/sha-fresh-lf-37f95dc'
test_files=[str(p) for p in sorted((fresh/'dashboard/tests').glob('*.test.js'))]
text,record=execute(['node','--test',*test_files],'fresh-committed-unit-tests')
import re
count=int(re.search(r'(?:tests|test cases)\s+(\d+)',text).group(1))
new_json(folder/'acceptance.json',{'status':'PASS','checked_at_utc':utcnow(),'source_commit':revision,'tests':count,'checkouts':results,'scope':'SHA/checkout recovery and unchanged Dashboard data; no Flume/Spark/K-Means rerun','sha_validation_disabled':False})
print(json.dumps({'status':'PASS','tests':count,'checkouts':results},indent=2))
