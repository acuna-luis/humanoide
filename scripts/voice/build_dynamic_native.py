#!/usr/bin/env python3
"""Compile and test the voice adapter on native ARM; no playback, ROS goals or restart."""
import argparse,base64,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from collect_estop_available_readonly import execute

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--remote-dir',required=True);a=p.parse_args();a.evidence.mkdir(parents=True,exist_ok=False)
 files={f.name:base64.b64encode(f.read_bytes()).decode() for f in (Path(__file__).parent/'dynamic').iterdir() if f.suffix in ['.cpp','.hpp']}
 code='from pathlib import Path;import base64;root=Path('+repr(a.remote_dir)+');root.mkdir(parents=True,exist_ok=False);files='+repr(files)+';[(root/n).write_bytes(base64.b64decode(b)) for n,b in files.items()]'
 x=execute('vision',['docker','exec','walker-system.ae_bt_master-1','python3','-c',code]);(a.evidence/'stage.json').write_text(json.dumps(x,indent=2))
 if x.get('returncode')!=0:raise RuntimeError(x)
 compile_code=r'''
from pathlib import Path
import subprocess,json,os
root=Path(ROOT)
incs=[]
for base in ['/opt/walker','/opt/rosa','/opt/ubt_3rdparty']:
 for d,dirs,files in os.walk(base):
  if d.count('/')-base.count('/')>4:dirs[:]=[];continue
  if Path(d).name=='include':incs+=['-I'+d];dirs[:]=[]
base=['g++','-std=c++17','-O2']+incs
commands=[base+['-fPIC','-shared',str(root/'voice_en.cpp'),'-o',str(root/'libvoice_en.so'),'-L/opt/walker/sys_task_msgs/lib','-lsys_task_msgs','-ldl'],base+[str(root/'native_test.cpp'),'-o',str(root/'native_test'),'-L/opt/walker/sys_task_msgs/lib','-lsys_task_msgs','-ldl']]
for command in commands:
 r=subprocess.run(command,capture_output=True,text=True,timeout=80);print(json.dumps({'command':command,'rc':r.returncode,'stdout':r.stdout,'stderr':r.stderr}),flush=True)
 if r.returncode:raise SystemExit(r.returncode)
env=dict(os.environ,LD_PRELOAD=str(root/'libvoice_en.so'))
r=subprocess.run([str(root/'native_test')],env=env,capture_output=True,text=True,timeout=20);print(json.dumps({'test_rc':r.returncode,'stdout':r.stdout,'stderr':r.stderr}),flush=True);raise SystemExit(r.returncode)
'''.replace('ROOT',repr(a.remote_dir),1)
 # Long native compilation via SSH runner from deployment utility.
 from deploy_voice_assets import ssh
 import shlex
 shell='source /opt/walker/setup.bash; python3 -c '+shlex.quote(compile_code)
 x=ssh(['docker','exec','walker-system.ae_bt_master-1','bash','-lc',shell],capture_output=True,text=True)
 (a.evidence/'compile-test.json').write_text(json.dumps({'rc':x.returncode,'stdout':x.stdout,'stderr':x.stderr},indent=2))
 
 for line in x.stdout.splitlines():
  try:
   event=json.loads(line);print(json.dumps({k:v for k,v in event.items() if k!='command'}))
  except ValueError:print(line)
 print(x.stderr[-1000:])
 if x.returncode:raise SystemExit(x.returncode)
if __name__=='__main__':main()
