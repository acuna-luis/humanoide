#!/usr/bin/env python3
"""Collect current Motion files or named joints without publishing commands."""
import argparse
import base64
import json
import os
from pathlib import Path
import shlex
import subprocess

if __package__:
    from . import scenario1_cli as cli
    from . import scenario1_table90 as table90
else:
    import scenario1_cli as cli
    import scenario1_table90 as table90


DISCOVER = '''import subprocess,json,hashlib,sys
ids=subprocess.check_output(['docker','ps','-q'],text=True).split()
rows=json.loads(subprocess.check_output(['docker','inspect',*ids],text=True))
rows=[r for r in rows if r['Config'].get('Labels',{}).get('com.docker.compose.service')=='motion.manipulation_robot_app']
if len(rows)!=1:raise RuntimeError('Motion container not unique')
row=rows[0];name=row['Name'].lstrip('/')
'''


def remote_program(mode):
    if mode == 'home':
        return DISCOVER+'''path='/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/cruzr/home.xml'
data=subprocess.check_output(['docker','exec',name,'cat',path])
print(json.dumps({'container':name,'container_id':row['Id'],'path':path,'sha256':hashlib.sha256(data).hexdigest(),'text':data.decode()}))
'''
    if mode == 'joints':
        return DISCOVER+'''r=subprocess.run(['docker','exec',name,'bash','-lc',
 'source /opt/walker/setup.bash; export ROS2CLI_DISABLE_DAEMON=1 ROSA_MIDDLE_WARE=cyclone ROSA_USE_SHM=OFF; timeout 8 rosa topic echo --once --no-daemon /mc/whole_joint_states'],capture_output=True,text=True,timeout=12)
print(json.dumps({'container':name,'container_id':row['Id'],'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr}))
raise SystemExit(r.returncode)
'''
    if mode == 'cad':
        return DISCOVER+'''subprocess.run(['docker','exec',name,'tar','-C',
 '/opt/walker/cruzr_s2_description/share/cruzr_s2_description','-cf','-','urdf','meshes'],check=True)
'''
    return DISCOVER+'paths='+repr(list(table90.CURRENT_MODEL_PINS))+'''
result={'container':name,'container_id':row['Id'],'image':row['Image'],'files':{}}
for path in paths:
 if path.endswith(('.yaml','.urdf')):
  data=subprocess.check_output(['docker','exec',name,'cat',path])
  result['files'][path]={'sha256':hashlib.sha256(data).hexdigest(),'text':data.decode()}
 else:
  result['files'][path]={'sha256':subprocess.check_output(['docker','exec',name,'sha256sum',path],text=True).split()[0]}
print(json.dumps(result))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('model', 'cad', 'joints', 'home'), default='model')
    parser.add_argument('--output', type=Path, required=True, help='New output directory')
    parser.add_argument('--wifi', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    source = remote_program(args.mode)
    (args.output/'read-source.py').write_text(source)
    command = cli.ssh_command(args.wifi)[:-1]+[shlex.join([
        'python3', '-B', '-c', 'import base64;exec(base64.b64decode('+repr(base64.b64encode(source.encode()).decode())+'))'])]
    env = dict(os.environ, CRUZR_INTERNAL_ASKPASS='1',
               SSH_ASKPASS=str(cli.ROOT/'scripts/cruzr_recover_to_home.sh'),
               SSH_ASKPASS_REQUIRE='force', DISPLAY=os.environ.get('DISPLAY', ':0'))
    with (args.output/('cad.tar' if args.mode == 'cad' else 'read.json')).open('xb') as stream:
        result = subprocess.run(command, env=env, stdout=stream, stderr=subprocess.PIPE,
                                timeout=45, start_new_session=True)
    (args.output/'stderr.txt').write_bytes(result.stderr)
    print(json.dumps(dict(mode=args.mode, returncode=result.returncode, movement_commands=0)))
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
