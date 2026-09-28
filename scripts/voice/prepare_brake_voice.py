#!/usr/bin/env python3
"""Back up and prepare a voice-only backend adapter; no activation or playback."""
import argparse,base64,hashlib,json,shlex,sys,tarfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from collect_estop_available_readonly import execute
from deploy_voice_assets import ssh,stop,require
C='walker-system.backend_service-1'
ENTRY='/opt/walker/entrypoint.sh'
BIN='/opt/walker/backend_service/lib/backend_service/backend_service_vision'
MSG='/opt/walker/sys_task_msgs/lib/libsys_task_msgs.so'
TARGET='/etc/walker/voice/brake_es_v1'
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--audio',type=Path,required=True);a=p.parse_args();a.evidence.mkdir(parents=True,exist_ok=False);stop(a.evidence)
 r=execute('vision',['docker','ps','--format','{{.Names}}']);(a.evidence/'containers.json').write_text(json.dumps(r));assert C in require(r).splitlines()
 r=execute('vision',['docker','inspect','--format','{{json .Mounts}}',C]);(a.evidence/'mounts.json').write_text(json.dumps(r))
 for m in json.loads(require(r)):
  if ENTRY==m['Destination'] or ENTRY.startswith(m['Destination'].rstrip('/')+'/'):raise RuntimeError('Entrypoint is shared; review scope')
 with (a.evidence/'originals.tar.gz').open('wb') as f:r=ssh(['docker','exec',C,'tar','czf','-','--dereference',ENTRY,BIN,MSG],stdout=f,stderr=-1)
 if r.returncode:raise RuntimeError('Backup failed')
 with tarfile.open(a.evidence/'originals.tar.gz') as t:old={n:t.extractfile(n.lstrip('/')).read() for n in [ENTRY,BIN,MSG]}
 sha=lambda b:hashlib.sha256(b).hexdigest()
 (a.evidence/'original-hashes.json').write_text(json.dumps({n:sha(b) for n,b in old.items()},indent=2))
 src=Path(__file__).parent/'backend';remote='/tmp/'+a.evidence.name
 files={f.name:base64.b64encode(f.read_bytes()).decode() for f in src.iterdir() if f.suffix in ['.cpp','.hpp']}
 code='from pathlib import Path;import base64;p=Path('+repr(remote)+');p.mkdir(exist_ok=False);files='+repr(files)+';[(p/n).write_bytes(base64.b64decode(b)) for n,b in files.items()]'
 require(execute('vision',['docker','exec',C,'python3','-c',code]))
 commands=[['g++','-std=c++17','-O2','-fPIC','-shared',remote+'/brake_voice.cpp','-o',remote+'/libbrake_voice.so','-L/opt/walker/sys_task_msgs/lib','-lsys_task_msgs','-ldl'],['g++','-std=c++17','-O2',remote+'/native_test.cpp','-o',remote+'/brake_voice_native_test','-L/opt/walker/sys_task_msgs/lib','-lsys_task_msgs']]
 shell='source /opt/walker/setup.bash\nset -e\n'+'\n'.join(shlex.join(c) for c in commands)+'\nLD_PRELOAD='+shlex.quote(remote+'/libbrake_voice.so')+' '+shlex.quote(remote+'/brake_voice_native_test')
 r=ssh(['docker','exec',C,'bash','-lc',shell],capture_output=True,text=True);(a.evidence/'compile-test.json').write_text(json.dumps(dict(rc=r.returncode,stdout=r.stdout,stderr=r.stderr,commands=commands),indent=2));print(r.stdout,r.stderr)
 if r.returncode:raise RuntimeError('Native test failed')
 for n in ['libbrake_voice.so','brake_voice_native_test']:
  with (a.evidence/n).open('wb') as f:r=ssh(['docker','exec',C,'cat',remote+'/'+n],stdout=f,stderr=-1)
  if r.returncode:raise RuntimeError('Binary transfer failed')
 d=a.evidence/'deployment';(d/'payload').mkdir(parents=True);rows=[]
 def add(group,target,data,before=None,mode=0o644):
  key=sha(target.encode());(d/'payload'/key).write_bytes(data);rows.append(dict(container=group,target=target,before_sha256=before,after_sha256=sha(data),payload=key,metadata=dict(mode=mode,uid=0,gid=0)))
 for n in ['libbrake_voice.so','brake_voice_native_test']:add('HOST',TARGET+'/'+n,(a.evidence/n).read_bytes(),mode=0o755)
 add('HOST',TARGET+'/brake_locked.wav',a.audio.read_bytes())
 for f in src.iterdir():
  if f.suffix in ['.cpp','.hpp']:add('HOST',TARGET+'/source/'+f.name,f.read_bytes())
 checks={BIN:sha(old[BIN]),MSG:sha(old[MSG]),**{r['target']:r['after_sha256'] for r in rows}}
 condition=' &&\n     '.join('[[ "$(sha256sum '+shlex.quote(n)+' 2>/dev/null | cut -d\' \' -f1)" == '+shlex.quote(h)+' ]]' for n,h in checks.items())
 block='# VOICE-BRAKE-07: exact utterance only; native fallback on incompatibility.\nif '+condition+'; then\n export LD_PRELOAD='+shlex.quote(TARGET+'/libbrake_voice.so')+'"${LD_PRELOAD:+:$LD_PRELOAD}"\nelse\n printf "%s\\n" "[VOICE_BRAKE] incompatible assets; native voice retained" >&2\nfi\n'
 before=old[ENTRY].decode();needle='eval "$cmd"'
 if before.count(needle)!=1 or 'VOICE-BRAKE-07' in before:raise RuntimeError('Unexpected entrypoint')
 after=before.replace(needle,block+needle)
 assert after.replace(block,'')==before
 (a.evidence/'entrypoint.after.sh').write_text(after)
 add(C,ENTRY,after.encode(),sha(old[ENTRY]),0o755)
 (d/'plan.json').write_text(json.dumps(rows,indent=2));(a.evidence/'recipe.py').write_bytes(Path(__file__).read_bytes())
 print('Prepared',len(rows),'files; no service restart/activation.')
if __name__=='__main__':main()
