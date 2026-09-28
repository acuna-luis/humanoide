#!/usr/bin/env python3
"""Hash-guarded voice installation and rollback under E-stop, no service restarts.

Each file is replaced atomically. A journal is persisted after every write.
Rollback requires that files still match installed hashes; unknown changes stop it.
"""
import argparse,base64,datetime,hashlib,json,os,shlex,subprocess,sys,tarfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from collect_estop_available_readonly import execute,ros,ROOT,HOSTS
HELPER=r'''
import hashlib,json,os,sys,tempfile
from pathlib import Path
root=Path(sys.argv[1]);group=sys.argv[2];mode=sys.argv[3]
rows=[r for r in json.loads((root/'plan.json').read_text()) if r['container']==group]
store=root/'receipts';store.mkdir(exist_ok=True);journal=store/(group+'.json')
old=json.loads(journal.read_text()) if journal.exists() else []
sha=lambda b:hashlib.sha256(b).hexdigest()
def current(path):return sha(path.read_bytes()) if path.exists() else None
def atomic(path,data,metadata):
 path.parent.mkdir(parents=True,exist_ok=True)
 fd,tmp=tempfile.mkstemp(prefix='.voice-',dir=path.parent)
 try:
  with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
  os.chmod(tmp,metadata['mode']);os.chown(tmp,metadata['uid'],metadata['gid']);os.replace(tmp,path)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def save():
 temp=journal.with_suffix('.tmp');temp.write_text(json.dumps(old,indent=2));os.replace(temp,journal)
if mode=='check':
 for row in rows:
  path=Path(row['target'])
  if path.is_symlink():raise SystemExit('Symlink target refused')
  if current(path)!=row['before_sha256']:raise SystemExit('BASELINE_CHANGED: '+str(path))
  if sha((root/'payload'/row['payload']).read_bytes())!=row['after_sha256']:raise SystemExit('Payload corrupt')
 print(json.dumps({'group':group,'checked':len(rows)}));sys.exit()
if mode=='rollback':
 for row in reversed(old):
  if row.get('rolled_back'):continue
  path=Path(row['target'])
  if current(path)==row['before_sha256']:
   row['rolled_back']=True;save();continue
  if current(path)!=row['after_sha256']:raise SystemExit('ROLLBACK_CONFLICT: '+str(path))
  if row['before_sha256'] is None:path.unlink()
  else:
   data=(root/'before'/row['payload']).read_bytes()
   if sha(data)!=row['before_sha256']:raise SystemExit('Backup corrupt')
   atomic(path,data,row['actual_metadata'])
   meta=row['actual_metadata'];os.utime(path,ns=(meta['atime_ns'],meta['mtime_ns']))
  if current(path)!=row['before_sha256']:raise SystemExit('Rollback readback failed')
  row['rolled_back']=True;save()
 print(json.dumps({'group':group,'rolled_back':len(old)}));sys.exit()
if old:raise SystemExit('Journal exists; inspect receipt before repeating')
for row in rows:
 path=Path(row['target'])
 if current(path)!=row['before_sha256']:raise SystemExit('BASELINE_CHANGED: '+str(path))
 if row['before_sha256'] is not None:
  st=path.stat();row['actual_metadata']={'mode':st.st_mode&0o7777,'uid':st.st_uid,'gid':st.st_gid,'mtime_ns':st.st_mtime_ns,'atime_ns':st.st_atime_ns}
  backup=root/'before'/row['payload'];backup.parent.mkdir(exist_ok=True);backup.write_bytes(path.read_bytes())
 data=(root/'payload'/row['payload']).read_bytes()
 if sha(data)!=row['after_sha256']:raise SystemExit('Payload corrupt')
 # Write intent before mutation, so interrupted updates remain auditable.
 row['intent']=True;old.append(row);save()
 atomic(path,data,row.get('actual_metadata',row['metadata']))
 if current(path)!=row['after_sha256']:raise SystemExit('Write readback failed')
 row['verified']=True;save()
print(json.dumps({'group':group,'installed':len(old)}))
'''
def require(r):
 if r.get('returncode')!=0:raise RuntimeError(r.get('stderr',r.get('error','remote failure'))+' '+r.get('stdout',''))
 return r['stdout']
def stop(evidence):
 x=execute('vision',ros('walker-ros.ros2-1','ros2 topic echo --once --no-daemon /emb/estop_key_state std_msgs/msg/UInt8'))
 with (evidence/'estop-checks.jsonl').open('a') as f:f.write(json.dumps(x)+'\n')
 if require(x).strip()!='data: 1\n---':raise RuntimeError('Main E-stop must remain pressed')
def ssh(args,**kwargs):
 env=dict(os.environ,CRUZR_INTERNAL_ASKPASS='1',SSH_ASKPASS=str(ROOT/'scripts/cruzr_recover_to_home.sh'),SSH_ASKPASS_REQUIRE='force',DISPLAY=':0')
 cmd=['setsid','-w','ssh','-T','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=5','-o','PreferredAuthentications=password','-o','PubkeyAuthentication=no','walker@'+HOSTS['vision'],shlex.join(args)]
 return subprocess.run(cmd,env=env,timeout=180,**kwargs)
def main():
 p=argparse.ArgumentParser();p.add_argument('--deployment',type=Path);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--apply',action='store_true');p.add_argument('--rollback-receipt',type=Path);a=p.parse_args();a.evidence.mkdir(parents=True,exist_ok=False)
 if a.rollback_receipt:
  receipt=json.loads(a.rollback_receipt.read_text());remote=receipt['remote'];groups=list(reversed(receipt['groups']))
 else:
  if not a.deployment:p.error('--deployment required')
  rows=json.loads((a.deployment/'plan.json').read_text());groups=list(dict.fromkeys(x['container'] for x in rows));remote='/tmp/cruzr-voice-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
 stop(a.evidence)
 inventory=execute('vision',['docker','ps','--format','{{.Names}}']);(a.evidence/'inventory.json').write_text(json.dumps(inventory,indent=2));names=require(inventory).splitlines()
 for g in groups:
  if (g if g!='HOST' else 'walker-voice.speech_service-1') not in names:raise RuntimeError('Missing container '+g)
 if not a.rollback_receipt:
  (a.deployment/'remote_helper.py').write_text(HELPER)
  archive=a.evidence/'deployment.tar.gz'
  with tarfile.open(archive,'w:gz') as t:
   for path in a.deployment.rglob('*'):
    if path.is_file():t.add(path,arcname=str(path.relative_to(a.deployment)))
  require(execute('vision',['mkdir','-m','700',remote]))
  with archive.open('rb') as f:
   x=ssh(['tar','xzf','-','-C',remote],stdin=f,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  if x.returncode:raise RuntimeError(x.stderr.decode())
  persistent='/etc/walker/voice/deployments/'+Path(remote).name
  code='import shutil;from pathlib import Path;src='+repr(remote)+';dst='+repr(persistent)+';Path(dst).parent.mkdir(parents=True,exist_ok=True);shutil.copytree(src,dst)'
  require(execute('vision',['docker','exec','-u','0','walker-voice.speech_service-1','python3','-c',code]))
  remote=persistent
  receipt={'remote':remote,'groups':groups,'applied':False,'deployment_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'movement_commands':0,'restarts':0}
  (a.evidence/'receipt.json').write_text(json.dumps(receipt,indent=2))
 def run(g,mode):
  container=g if g!='HOST' else 'walker-voice.speech_service-1'
  x=ssh(['docker','exec','-u','0',container,'python3',remote+'/remote_helper.py',remote,g,mode],capture_output=True,text=True)
  (a.evidence/(g+'-'+mode+'.json')).write_text(json.dumps({'rc':x.returncode,'stdout':x.stdout,'stderr':x.stderr},indent=2))
  if x.returncode:raise RuntimeError(x.stderr+' '+x.stdout)
  print(x.stdout,flush=True)
 if not a.rollback_receipt:
  for g in groups:run(g,'check')
  if not a.apply:print('CHECK_ONLY: staged package, no assets changed');return
 for g in groups:
  stop(a.evidence);run(g,'rollback' if a.rollback_receipt else 'apply')
 if not a.rollback_receipt:
  receipt['applied']=True;(a.evidence/'receipt.json').write_text(json.dumps(receipt,indent=2))
 # Copy journals and actual originals outside the robot for rollback persistence.
 with (a.evidence/'remote-receipts-and-originals.tar.gz').open('wb') as f:
  x=ssh(['docker','exec','-u','0','walker-voice.speech_service-1','tar','czf','-','-C',remote,'receipts','before','plan.json','remote_helper.py'],stdout=f,stderr=subprocess.PIPE)
 if x.returncode:raise RuntimeError('Receipt backup failed: '+x.stderr.decode())
 print('COMPLETE; no restarts or playback; keep E-stop pressed')
if __name__=='__main__':main()
