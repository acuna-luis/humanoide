#!/usr/bin/env python3
"""Back up, compile/test, and prepare CC voice deployment; does not activate it.

Use deploy_voice_assets.py --apply separately under main E-stop.
"""
import argparse,base64,hashlib,json,shlex,sys,tarfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from collect_estop_available_readonly import execute
from deploy_voice_assets import ssh,stop,require

CC='walker-system.control_center-1'
BOOT='/etc/walker/boot/cruzr_cc_start_when_ready.py'
BINARY='/opt/walker/control_center/lib/control_center/control_center'
MESSAGES='/opt/walker/sys_task_msgs/lib/libsys_task_msgs.so'
TARGET='/etc/walker/voice/control_center_es_v1'

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--evidence',required=True,type=Path)
 p.add_argument('--audio',required=True,type=Path)
 p.add_argument('--catalog',required=True,type=Path)
 a=p.parse_args();a.evidence.mkdir(parents=True,exist_ok=False);stop(a.evidence)
 discovery=execute('vision',['docker','ps','--format','{{.Names}}'])
 (a.evidence/'discovery.json').write_text(json.dumps(discovery))
 if CC not in require(discovery).splitlines():raise RuntimeError('Missing CC')
 # Full external immediate originals; no credentials/config dump to terminal.
 with (a.evidence/'originals.tar.gz').open('wb') as f:
  r=ssh(['docker','exec',CC,'tar','czf','-','--dereference',BOOT,BINARY,MESSAGES],stdout=f,stderr=-1)
 if r.returncode:raise RuntimeError(r.stderr.decode())
 with tarfile.open(a.evidence/'originals.tar.gz') as t:
  originals={n:t.extractfile(n.lstrip('/')).read() for n in [BOOT,BINARY,MESSAGES]}
 hashes={n:hashlib.sha256(b).hexdigest() for n,b in originals.items()}
 (a.evidence/'original-hashes.json').write_text(json.dumps(hashes,indent=2))
 source=a.evidence/'source';source.mkdir()
 for f in (Path(__file__).parent/'control_center').iterdir():
  if f.suffix in ['.cpp','.hpp']: (source/f.name).write_bytes(f.read_bytes())
 rows=[r for r in json.loads(a.catalog.read_text()) if r['kind']=='fixed']
 if len(rows)!=24:raise RuntimeError('Review changed catalog')
 header='#pragma once\n#include <map>\n#include <string>\n#ifndef CC_AUDIO_ROOT\n#define CC_AUDIO_ROOT "'+TARGET+'/audio_es"\n#endif\nstatic const std::map<std::string,std::pair<std::string,std::string>> cc_catalog={\n'
 header+=''.join('{'+json.dumps(r['zh'],ensure_ascii=False)+',{'+json.dumps(r['id'])+','+json.dumps(r['en'])+'}},\n' for r in rows)+'};\n'
 (source/'catalog.hpp').write_text(header)
 remote='/tmp/'+a.evidence.name
 # Stage compiler inputs only, outside active configuration.
 files={f.name:base64.b64encode(f.read_bytes()).decode() for f in source.iterdir()}
 code='from pathlib import Path;import base64;p=Path('+repr(remote)+');p.mkdir(exist_ok=False);files='+repr(files)+';[(p/n).write_bytes(base64.b64decode(b)) for n,b in files.items()]'
 require(execute('vision',['docker','exec',CC,'python3','-c',code]))
 commands=[['g++','-std=c++17','-O2','-Wall','-Wextra','-fPIC','-shared',remote+'/voice_cc.cpp','-o',remote+'/libvoice_cc.so','-L/opt/walker/sys_task_msgs/lib','-lsys_task_msgs','-ldl'],['g++','-std=c++17','-O2',remote+'/native_test.cpp','-o',remote+'/voice_cc_native_test','-L/opt/walker/sys_task_msgs/lib','-lsys_task_msgs']]
 shell='source /opt/walker/setup.bash\nset -e\n'+'\n'.join(shlex.join(c) for c in commands)+'\nLD_PRELOAD='+shlex.quote(remote+'/libvoice_cc.so')+' '+shlex.quote(remote+'/voice_cc_native_test')
 r=ssh(['docker','exec',CC,'bash','-lc',shell],capture_output=True,text=True)
 (a.evidence/'compile-test.json').write_text(json.dumps(dict(rc=r.returncode,stdout=r.stdout,stderr=r.stderr,commands=commands),indent=2))
 print(r.stdout);print(r.stderr[-1500:])
 if r.returncode:raise RuntimeError('Native test failed')
 for name in ['libvoice_cc.so','voice_cc_native_test']:
  with (a.evidence/name).open('wb') as f:r=ssh(['docker','exec',CC,'cat',remote+'/'+name],stdout=f,stderr=-1)
  if r.returncode:raise RuntimeError('Binary backup failed')
 deployment=a.evidence/'deployment';(deployment/'payload').mkdir(parents=True)
 plan=[]
 def add(path,data,old=None,mode=0o644):
  key=hashlib.sha256(path.encode()).hexdigest();(deployment/'payload'/key).write_bytes(data)
  plan.append(dict(container='HOST',target=path,before_sha256=old,after_sha256=hashlib.sha256(data).hexdigest(),payload=key,metadata=dict(mode=mode,uid=0,gid=0)))
 for name in ['libvoice_cc.so','voice_cc_native_test']:add(TARGET+'/'+name,(a.evidence/name).read_bytes(),mode=0o755)
 for r in rows:add(TARGET+'/audio_es/'+r['id']+'.wav',(a.audio/(r['id']+'.wav')).read_bytes())
 for f in source.iterdir():add(TARGET+'/source/'+f.name,f.read_bytes())
 add(TARGET+'/catalog.json',a.catalog.read_bytes())
 guards={**hashes,**{r['target']:r['after_sha256'] for r in plan}}
 # The guard runs immediately before vendor exec, after all original readiness gates.
 # Missing/incompatible localization falls back to native speech, never skips readiness.
 block='''    # VOICE-BOOT-05: optional voice-only adapter, verified before vendor exec.
    try:
        voice_hashes = VOICE_HASHES
        if not all(hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest
                   for name, digest in voice_hashes.items()):
            raise ValueError('voice compatibility/hash mismatch')
        voice_lib = VOICE_LIB
        os.environ['LD_PRELOAD'] = voice_lib + (':' + os.environ['LD_PRELOAD'] if os.environ.get('LD_PRELOAD') else '')
        log('VOICE_CC=Spanish fixed announcements; English battery TTS')
    except (OSError, ValueError) as error:
        log('VOICE_CC=native fallback; ' + type(error).__name__)
'''.replace('VOICE_HASHES',repr({k:v for k,v in guards.items() if k!=BOOT})).replace('VOICE_LIB',repr(TARGET+'/libvoice_cc.so'))
 before=originals[BOOT].decode();needle='    os.execvp(COMMAND[0], COMMAND)'
 if before.count(needle)!=1 or 'VOICE-BOOT-05' in before:raise RuntimeError('Unexpected boot launcher')
 after=before.replace(needle,block+needle)
 compile(after,BOOT,'exec')
 if 'from pathlib import Path' not in before:raise RuntimeError('Path unavailable')
 add(BOOT,after.encode(),hashes[BOOT],0o755)
 (deployment/'plan.json').write_text(json.dumps(plan,indent=2))
 (a.evidence/'boot.after.py').write_text(after)
 (a.evidence/'recipe.py').write_bytes(Path(__file__).read_bytes())
 print('Prepared',len(plan),'files. No activation/restart/playback.')

if __name__=='__main__':main()
