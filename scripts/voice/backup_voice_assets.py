#!/usr/bin/env python3
"""Read-only complete audio and voice-text file snapshots with verified tar metadata."""
import argparse,hashlib,json,os,shlex,subprocess,sys,tarfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from collect_estop_available_readonly import execute,HOSTS,ROOT
REMOTE=r'''
import os,re,json,hashlib,tarfile,sys,io
files=[];errors=[]
for root in ['/opt/walker','/etc/walker']:
 for d,dirs,names in os.walk(root):
  dirs[:]=[x for x in dirs if x not in ['log','logs','node_modules','site-packages','__pycache__','.git','loki','loglect','service_log','backups']]
  for n in names:
   p=os.path.join(d,n)
   try:
    audio=n.lower().endswith(('.wav','.mp3','.flac','.ogg'))
    text=n.lower().endswith(('.xml','.yaml','.yml','.json','.ini','.cfg','.toml','.py','.i','.action'))
    if not audio and not (text and os.path.getsize(p)<4000000):continue
    data=open(p,'rb').read()
    if not audio:
     s=data.decode('utf-8',errors='ignore')
     if not re.search(r'Tts|tts|speech|Speech|voice|Voice|audio|Audio|[\u4e00-\u9fff]',s):continue
    st=os.stat(p);files.append({'path':p,'sha256':hashlib.sha256(data).hexdigest(),'size':len(data),'mode':st.st_mode&0o7777,'uid':st.st_uid,'gid':st.st_gid,'mtime_ns':st.st_mtime_ns,'symlink':os.readlink(p) if os.path.islink(p) else None})
   except OSError as e:errors.append({'path':p,'error':str(e)})
# The TTS server executable lives outside /opt/walker in its container.
p='/usr/local/bin/tts'
if os.path.isfile(p):
 data=open(p,'rb').read();st=os.stat(p)
 files.append({'path':p,'sha256':hashlib.sha256(data).hexdigest(),'size':len(data),'mode':st.st_mode&0o7777,'uid':st.st_uid,'gid':st.st_gid,'mtime_ns':st.st_mtime_ns,'symlink':os.readlink(p) if os.path.islink(p) else None})
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz',dereference=True) as tar:
 for row in files:
  tar.add(row['path'],arcname='files/'+row['path'].lstrip('/'),recursive=False)
 data=json.dumps({'files':files,'errors':errors},ensure_ascii=False,indent=2).encode();info=tarfile.TarInfo('manifest.json');info.size=len(data);tar.addfile(info,io.BytesIO(data))
'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 jobs=[('vision',c) for c in ['walker-voice.speech_service-1','walker-system.ae_bt_master-1','walker-system.control_center-1','walker-nav.nav_taskmanager-1','walker-voice.tts-1']]+[('motion','walker-motion.manipulation_robot_app-1')]
 for host,c in jobs:
  d=a.output/c;d.mkdir();info=execute(host,['docker','inspect',c]);(d/'docker-inspect.private.json').write_text(json.dumps(info,indent=2))
  if info.get('returncode')!=0:raise RuntimeError('Container unavailable')
  env=dict(os.environ,CRUZR_INTERNAL_ASKPASS='1',SSH_ASKPASS=str(ROOT/'scripts/cruzr_recover_to_home.sh'),SSH_ASKPASS_REQUIRE='force',DISPLAY=':0')
  cmd=['setsid','-w','ssh','-T','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=5','-o','PreferredAuthentications=password','-o','PubkeyAuthentication=no','walker@'+HOSTS[host],shlex.join(['docker','exec',c,'python3','-c',REMOTE])]
  archive=d/'originals.tar.gz'
  with archive.open('xb') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.PIPE,env=env,timeout=180)
  if r.returncode:raise RuntimeError(r.stderr.decode())
  with tarfile.open(archive) as tar:
   manifest=json.load(tar.extractfile('manifest.json'))
   for row in manifest['files']:
    data=tar.extractfile('files/'+row['path'].lstrip('/')).read()
    if hashlib.sha256(data).hexdigest()!=row['sha256']:raise RuntimeError('File changed while snapshotting: '+row['path'])
  (d/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
  (d/'archive.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  originals.tar.gz\n')
  print(c,'verified_files',len(manifest['files']),'errors',len(manifest['errors']),flush=True)
if __name__=='__main__':main()
