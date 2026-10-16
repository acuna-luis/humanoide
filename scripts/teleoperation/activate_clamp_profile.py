#!/usr/bin/env python3
"""Reload the reviewed clamp profile by explicit phases, retaining custom files.

Prepare only inventories/backs up. All later phases require the main E-stop
pressed, charger absent and current operator confirmation of secured arms.
Never releases E-stop or sends a HOME/start ROS request.
"""
import argparse
import json
import os
import shlex
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from scripts.collect_estop_available_readonly import execute, ROOT, HOSTS

def execute_phase(host, command):
    # Archive/recreation may exceed the diagnostic helper's 18-second bound.
    env=dict(os.environ,CRUZR_INTERNAL_ASKPASS='1',
      SSH_ASKPASS=str(ROOT/'scripts/cruzr_recover_to_home.sh'),SSH_ASKPASS_REQUIRE='force',
      DISPLAY=os.environ.get('DISPLAY',':0'))
    prefix=['setsid','-w','ssh','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=5',
      '-o','PreferredAuthentications=password','-o','PubkeyAuthentication=no',
      '-o','NumberOfPasswordPrompts=1','walker@'+HOSTS[host]]
    try:
        r=subprocess.run(prefix+[shlex.join(command)],env=env,capture_output=True,text=True,timeout=120)
        return dict(returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)
    except subprocess.TimeoutExpired:
        return dict(error='phase_timeout_inspect_before_retry')


STAGE='/home/walker/.local/share/cruzr-return-clamp-20261015/reload'
SERVICES=['motion.'+s for s in ('action_list_manager_main','ecat_err_handler_service','hw',
 'manipulation_calibration_assistance_server_node','manipulation_robot_app','mc_common',
 'rtm_receiver','t800_mc_server','vrpn_client_server_node')]
REMOTE=r'''
import hashlib,io,json,pathlib,subprocess,sys,tarfile
stage=pathlib.Path(sys.argv[1]);phase=sys.argv[2];services=json.loads(sys.argv[3])
containers=['walker-'+s+'-1' for s in services]
cc='walker-system.control_center-1'
def run(c):return subprocess.check_output(c,text=True)
def inspect(c):return json.loads(run(['docker','inspect',c]))[0]
def save(name,obj):
 p=stage/name
 with p.open('x') as f:json.dump(obj,f,indent=2)
def mounts(c):return sorted((m['Source'],m['Destination'],m['RW'],m['Type']) for m in c['Mounts'])
if phase=='prepare':
 stage.mkdir(mode=0o700,parents=True,exist_ok=False)
 originals={c:inspect(c) for c in containers};save('original.json',originals)
 manifests={}
 for c in containers:
  diff=run(['docker','diff',c]);paths=[]
  for line in diff.splitlines():
   if not line.startswith(('A ','C ')):continue
   p=line[2:];suffix=pathlib.Path(p).suffix
   if p.startswith('/opt/walker/') and suffix in ('.yaml','.xml','.json','.bash','.py','.sh') and '/site-packages/' not in p:paths.append(p)
   elif suffix=='.motion' and (p.count('/')==1 or p.startswith('/tmp/')):paths.append(p)
  manifest={}
  with tarfile.open(stage/(c+'.tar'),'w') as output:
   for p in sorted(set(paths)):
    raw=subprocess.check_output(['docker','cp',c+':'+p,'-'])
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
     members=[m for m in archive.getmembers() if m.isfile() or m.issym()]
     assert len(members)==1,'Unexpected directory backup: '+p
     member=members[0];stream=archive.extractfile(member) if member.isfile() else None
     member.name=p.lstrip('/')
     if stream:
      data=stream.read();manifest[p]=hashlib.sha256(data).hexdigest();output.addfile(member,io.BytesIO(data))
     else:output.addfile(member)
  manifests[c]=manifest
 save('manifests.json',manifests)
 save('archives.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in stage.glob('*.tar')})
 print(json.dumps({'phase':phase,'stage':str(stage),'files':sum(map(len,manifests.values())),'reloaded':False}))
 sys.exit(0)
originals=json.loads((stage/'original.json').read_text())
assert set(originals)==set(containers)
if phase=='create':
 assert all(not inspect(c)['State']['Running'] for c in containers)
 root='/home/walker/.config/udoke/walker'
 compose=['docker','compose','--project-name','walker','--project-directory',root,'-f',root+'/compose.yml']
 config=json.loads(run(compose+['config','--format','json']))
 for service in services:
  assert config['services'][service]['environment']['HW_TYPE']=='cruzr_s2_v1'
  assert not config['services'][service].get('depends_on'),'Review dependencies'
 subprocess.run(compose+['create','--no-build','--pull','never','--force-recreate',*services],check=True,timeout=60)
 for c in containers:
  old=originals[c];new=inspect(c)
  assert new['Image']==old['Image'],'Image changed'
  assert new['Config']['Cmd']==old['Config']['Cmd'],'Command changed'
  assert mounts(new)==mounts(old),'Mount changed'
  oldenv=dict(x.split('=',1) for x in old['Config']['Env']);newenv=dict(x.split('=',1) for x in new['Config']['Env'])
  assert newenv==dict(oldenv,HW_TYPE='cruzr_s2_v1'),'Extra environment drift'
 for name,sha in json.loads((stage/'archives.json').read_text()).items():
  assert hashlib.sha256((stage/name).read_bytes()).hexdigest()==sha,'Backup corrupt'
 for c in containers:
  with (stage/(c+'.tar')).open('rb') as stream:subprocess.run(['docker','cp','-a','-',c+':/'],stdin=stream,check=True)
 print(json.dumps({'phase':phase,'restored':True,'started':False}))
elif phase=='start-motion':
 for c in containers:
  assert not inspect(c)['State']['Running']
  assert dict(x.split('=',1) for x in inspect(c)['Config']['Env'])['HW_TYPE']=='cruzr_s2_v1'
 subprocess.run(['docker','start',*containers],check=True,timeout=30)
 print(json.dumps({'phase':phase,'cc_started':False}))
elif phase=='verify':
 for c,manifest in json.loads((stage/'manifests.json').read_text()).items():
  assert inspect(c)['State']['Running'],c+' is not running'
  code='import pathlib,json,hashlib,sys; m=json.loads(sys.argv[1]); bad=[p for p,h in m.items() if hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()!=h]; print(json.dumps(bad)); sys.exit(bool(bad))'
  subprocess.run(['docker','exec',c,'python3','-c',code,json.dumps(manifest)],check=True)
 print(json.dumps({'phase':phase,'files_verified':True}))
'''

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--phase',choices=['prepare','stop','create','start-motion','verify','reload-cc'],required=True)
    p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--arms-secured',action='store_true')
    a=p.parse_args();out=a.evidence/('clamp-reload-'+a.phase+'.json')
    if out.exists():p.error('Receipt already exists; preserve it')
    if a.phase!='prepare':
        if not a.arms_secured:p.error('Current operator confirmation required')
        if subprocess.run(['pgrep','-x','pico_control'],capture_output=True).returncode!=1:raise RuntimeError('PICO client active or unknown')
        for topic,value in [('estop_key_state','1'),('chrg_input_status','0')]:
            r=execute('motion',['docker','exec','walker-ros.ros2-1','bash','-lc',
              'source /opt/ros/humble/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; timeout 10 ros2 topic echo --once --no-daemon --qos-reliability reliable /emb/'+topic+' std_msgs/msg/UInt8'])
            (a.evidence/('clamp-'+a.phase+'-'+topic+'.json')).write_text(json.dumps(r,indent=2))
            if r.get('returncode')!=0 or r['stdout'].strip()!='data: '+value+'\n---':raise RuntimeError('E-stop pressed / charger absent not confirmed')
        proof=a.evidence/'backups-external-verified.json'
        if not proof.exists() or json.loads(proof.read_text()).get('verified') is not True:raise RuntimeError('External backups not verified')
    if a.phase in ('create','start-motion','verify'):
        r=execute('vision',['docker','inspect','--format','{{.State.Running}}','walker-system.control_center-1'])
        if r.get('returncode')!=0 or r['stdout'].strip()!='false':raise RuntimeError('Control Center must remain stopped')
    prerequisites={'create':'stop','start-motion':'create','verify':'start-motion','reload-cc':'verify'}
    if a.phase in prerequisites:
        previous=a.evidence/('clamp-reload-'+prerequisites[a.phase]+'.json')
        if not previous.exists():raise RuntimeError('Previous phase receipt missing')
        result=json.loads(previous.read_text())
        records=result if isinstance(result,list) else [result]
        if not all(record.get('returncode')==0 for record in records):raise RuntimeError('Previous phase did not succeed')
    if a.phase=='stop':
        commands=[('vision',['docker','stop','--time','5','walker-system.control_center-1']),
          ('motion',['docker','stop','--time','5',*['walker-'+s+'-1' for s in SERVICES]])]
        results=[]
        for host,cmd in commands:
            r=execute(host,cmd);results.append(r)
            if r.get('returncode')!=0:out.write_text(json.dumps(results,indent=2));raise RuntimeError('Stop incomplete')
        out.write_text(json.dumps(results,indent=2));print('Stopped CC/Motion; main E-stop remains pressed');return
    if a.phase=='reload-cc':
        if not (a.evidence/'clamp-reload-verify.json').exists():raise RuntimeError('Motion verification missing')
        code=r'''import json,subprocess
c='walker-system.control_center-1';root='/home/walker/.config/udoke/walker'
def inspect():return json.loads(subprocess.check_output(['docker','inspect',c]))[0]
a=inspect();assert not a['State']['Running']
cmd=['docker','compose','--project-name','walker','--project-directory',root,'-f',root+'/compose.yml']
s=json.loads(subprocess.check_output(cmd+['config','--format','json']))['services']['system.control_center']
assert s['environment']['HW_TYPE']=='cruzr_s2_v1';assert not s.get('depends_on')
subprocess.run(cmd+['create','--no-build','--pull','never','--force-recreate','system.control_center'],check=True,timeout=30)
b=inspect();assert a['Image']==b['Image'];assert a['Config']['Cmd']==b['Config']['Cmd']
def mounts(c):return sorted((m['Source'],m['Destination'],m['RW'],m['Type']) for m in c['Mounts'])
assert mounts(a)==mounts(b)
ae=dict(x.split('=',1) for x in a['Config']['Env']);be=dict(x.split('=',1) for x in b['Config']['Env']);assert be==dict(ae,HW_TYPE='cruzr_s2_v1')
subprocess.run(['docker','start',c],check=True,timeout=10)
print(json.dumps({'cc_started':True,'estop_released':False}))'''
        r=execute_phase('vision',['python3','-c',code])
    else:
        r=execute_phase('motion',['python3','-c',REMOTE,STAGE,a.phase,json.dumps(SERVICES)])
    out.write_text(json.dumps(r,indent=2));print(json.dumps(r))
    return r.get('returncode',1)

if __name__=='__main__':
    raise SystemExit(main())
