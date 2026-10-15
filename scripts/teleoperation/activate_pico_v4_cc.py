#!/usr/bin/env python3
"""Recreate only CC with reviewed SPS env, while main E-stop remains pressed.

No Motion restart, E-stop release, HOME or PICO START. --check is read-only.
Physical support of arms is required because recovery is outside measured HOME.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from scripts.collect_estop_available_readonly import execute

REMOTE=r'''
import json,os,pathlib,subprocess,sys
mode=sys.argv[1]
container='walker-system.control_center-1'
root='/home/walker/.config/udoke/walker'
cmd=['docker','compose','--project-name','walker','--project-directory',root,'-f',root+'/compose.yml']
def inspect():return json.loads(subprocess.check_output(['docker','inspect',container]))[0]
before=inspect()
env=dict(os.environ)
old_env=dict(s.split('=',1) for s in before['Config']['Env'])
if 'DISPLAY' in old_env:env['DISPLAY']=old_env['DISPLAY']
config=json.loads(subprocess.check_output(cmd+['config','--format','json'],env=env))
service=config['services']['system.control_center']
assert not service.get('depends_on'),'Dependencies must not be recreated'
assert service['environment']['HW_TYPE']=='cruzr_s2_v1_sps'
assert service['command']==before['Config']['Cmd'],'Boot guard command changed'
if mode=='activate':
 subprocess.run(['docker','stop','--time','5',container],check=True,timeout=12)
 subprocess.run(cmd+['create','--no-build','--pull','never','--force-recreate','system.control_center'],env=env,check=True,timeout=30)
 after=inspect()
 assert after['Image']==before['Image'],'Image changed; do not start'
 assert after['Config']['Cmd']==before['Config']['Cmd'],'Command changed; do not start'
 def mounts(c):return sorted((m['Source'],m['Destination'],m['RW'],m['Type']) for m in c['Mounts'])
 assert mounts(after)==mounts(before),'Mounts changed; do not start'
 new_env=dict(s.split('=',1) for s in after['Config']['Env'])
 expected=dict(old_env,HW_TYPE='cruzr_s2_v1_sps')
 assert new_env==expected,'Extra environment change; do not start'
 subprocess.run(['docker','start',container],check=True,timeout=15)
else:after=before
print(json.dumps(dict(mode=mode,before_id=before['Id'],after_id=after['Id'],image=after['Image'],
 hw_type=dict(s.split('=',1) for s in after['Config']['Env']).get('HW_TYPE'),
 motion_restarted=False,estop_released=False,pico_started=False)))
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--activate',action='store_true')
    p.add_argument('--check',action='store_true')
    p.add_argument('--estop-arms-secured',action='store_true')
    p.add_argument('--evidence',type=Path,required=True)
    args=p.parse_args()
    if args.activate:
        if not args.estop_arms_secured:p.error('Confirm operator has secured arms and pressed main E-stop')
        proof=json.loads((args.evidence/'migration-backups-verified.json').read_text())
        if not all(proof.get(k) is True for k in ['motion','vision','selected']):raise RuntimeError('External backups not verified')
        if subprocess.run(['pgrep','-x','pico_control'],capture_output=True).returncode!=1:raise RuntimeError('PICO client running or unknown')
        r=execute('motion',['docker','exec','walker-ros.ros2-1','bash','-lc','source /opt/ros/humble/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; timeout 10 ros2 topic echo /emb/estop_key_state std_msgs/msg/UInt8 --once --no-daemon --qos-reliability reliable --qos-durability volatile'])
        (args.evidence/'cc-activation-estop.json').write_text(json.dumps(r,indent=2))
        if r.get('returncode')!=0 or r['stdout'].strip()!='data: 1\n---':raise RuntimeError('Fresh main E-stop pressed not confirmed')
    mode='activate' if args.activate else 'check'
    path=args.evidence/('cc-profile-'+mode+'.json')
    if path.exists():raise RuntimeError('Receipt already exists; preserve prior result')
    r=execute('vision',['python3','-c',REMOTE,mode])
    path.write_text(json.dumps(r,indent=2));print(json.dumps(r))
    return r.get('returncode',1)


if __name__=='__main__':
    raise SystemExit(main())
