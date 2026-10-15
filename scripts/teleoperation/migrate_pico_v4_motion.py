#!/usr/bin/env python3
"""Explicit supervised SPS migration phases. Never releases E-stop or starts PICO.

Run inventory first; stop -> install_pico_v4_motion_env -> create -> restore ->
start-motion -> verify-files -> start-cc. Main E-stop must remain pressed.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.collect_estop_available_readonly import ROOT, HOSTS
from scripts.teleoperation.stage_pico_v4_migration import STAGE

SERVICES = ['motion.' + n for n in ('action_list_manager_main','ecat_err_handler_service',
    'hw','manipulation_calibration_assistance_server_node','manipulation_robot_app',
    'mc_common','rtm_receiver','t800_mc_server','vrpn_client_server_node')]
CONTAINERS = ['walker-'+n+'-1' for n in SERVICES]
COMPOSE = ['docker','compose','--project-name','walker','--project-directory',
           '/home/walker/.config/udoke/walker','-f','/home/walker/.config/udoke/walker/compose.yml']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', required=True, choices=('inventory','stop','create','restore',
                        'start-motion','verify-files','start-cc'))
    parser.add_argument('--evidence', required=True, type=Path)
    parser.add_argument('--rollback', action='store_true', help='Create from staged original env after explicit env rollback')
    args = parser.parse_args()
    out = args.evidence
    def run(host, command, slot):
        env = dict(os.environ,CRUZR_INTERNAL_ASKPASS='1',
            SSH_ASKPASS=str(ROOT/'scripts/cruzr_recover_to_home.sh'),SSH_ASKPASS_REQUIRE='force',
            DISPLAY=os.environ.get('DISPLAY',':0'))
        prefix=['setsid','-w','ssh','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=5',
                '-o','PreferredAuthentications=password','-o','PubkeyAuthentication=no',
                '-o','NumberOfPasswordPrompts=1','walker@'+HOSTS[host]]
        result = subprocess.run(prefix+[shlex.join(command)],env=env,capture_output=True,text=True,timeout=120)
        receipt=dict(started=dt.datetime.now(dt.timezone.utc).isoformat(),host=host,
                     command=command,returncode=result.returncode,stdout=result.stdout,stderr=result.stderr)
        (out/('migration-'+slot+'.json')).write_text(json.dumps(receipt,indent=2))
        if result.returncode:
            raise RuntimeError(slot+': '+result.stderr[-2000:]+result.stdout[-2000:])
        return result.stdout
    def metadata():
        return json.loads(run('motion',['docker','inspect',*CONTAINERS],args.phase+'-inspect'))
    if args.phase == 'inventory':
        if (out/'migration-original-containers.json').exists():
            raise ValueError('Original inventory already exists; preserve it')
        data=metadata()
        summary={c['Name'].lstrip('/'):dict(image=c['Image'],running=c['State']['Running']) for c in data}
        if not all(c['running'] for c in summary.values()):
            raise RuntimeError('Expected nine currently active Motion services')
        (out/'migration-original-containers.json').write_text(json.dumps(summary,indent=2))
        print('Nine active Motion containers inventoried; no changes')
        return
    proof=json.loads((out/'migration-backups-verified.json').read_text())
    if not all(proof.get(k) is True for k in ('motion','vision','selected')):
        raise ValueError('External backup verification incomplete')
    # Independent fresh safety reads, not a cached permission bit.
    for topic,expected in [('estop_key_state','1'),('chrg_input_status','0')]:
        command='source /opt/ros/humble/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; timeout 10 ros2 topic echo /emb/'+topic+' std_msgs/msg/UInt8 --once --no-daemon --qos-reliability reliable --qos-durability volatile'
        text=run('motion',['docker','exec','walker-ros.ros2-1','bash','-lc',command],args.phase+'-'+topic)
        if text.strip() != 'data: '+expected+'\n---':
            raise RuntimeError('Required main E-stop pressed / charger absent not confirmed')
    original=json.loads((out/'migration-original-containers.json').read_text())
    data=metadata()
    if any(c['Image'] != original[c['Name'].lstrip('/')]['image'] for c in data):
        raise RuntimeError('Image changed; review compatibility before continuing')
    if args.phase == 'stop':
        run('vision',['docker','stop','--time','5','walker-system.control_center-1'],'stop-cc')
        run('motion',['docker','stop','--time','5',*CONTAINERS],'stop-motion')
    else:
        cc=run('vision',['docker','inspect','--format','{{.State.Running}}','walker-system.control_center-1'],args.phase+'-cc')
        if cc.strip() != 'false':
            raise RuntimeError('Control Center must remain stopped during migration')
        if args.phase in ('create','restore') and any(c['State']['Running'] for c in data):
            raise RuntimeError('Motion containers must remain stopped')
        if args.phase == 'create':
            version='before' if args.rollback else 'candidate'
            code='import pathlib,sys; s=pathlib.Path(sys.argv[1]); v=sys.argv[2]; assert (s/("compose."+v+".yml")).read_bytes()==pathlib.Path("/home/walker/.config/udoke/walker/compose.yml").read_bytes(); assert (s/("db."+v+".json")).read_bytes()==pathlib.Path("/home/walker/.config/udoke/db.json").read_bytes()'
            run('motion',['python3','-c',code,STAGE,version],'create-env-check')
            run('motion',COMPOSE+['create','--no-build','--pull','never','--force-recreate',*SERVICES],'create')
        elif args.phase == 'restore':
            code='''import hashlib,pathlib,subprocess,sys
s=pathlib.Path(sys.argv[1])
for slot,container,expected in [('hw','walker-motion.hw-1',sys.argv[2]),('app','walker-motion.manipulation_robot_app-1',sys.argv[3])]:
 p=s/(slot+'.tar')
 assert hashlib.sha256(p.read_bytes()).hexdigest()==expected
 with p.open('rb') as f:subprocess.run(['docker','cp','-a','-',container+':/'],stdin=f,check=True)
print('Reviewed files restored; no container started')
'''
            hashes=[json.loads(json.loads((out/(slot+'-stage-receipt.json')).read_text())['stdout'])['sha256'] for slot in ('hw','app')]
            run('motion',['python3','-c',code,STAGE,*hashes],'restore')
        elif args.phase == 'start-motion':
            if not (out/'migration-restore.json').exists():
                raise RuntimeError('Restoration receipt missing')
            run('motion',['docker','start',*CONTAINERS],'start-motion')
        elif args.phase == 'verify-files':
            code='''import hashlib,json,pathlib,subprocess,sys,tarfile
s=pathlib.Path(sys.argv[1]); result={}
for slot,container in [('hw','walker-motion.hw-1'),('app','walker-motion.manipulation_robot_app-1')]:
 with tarfile.open(s/(slot+'.tar')) as t:
  expected={('/'+m.name):hashlib.sha256(t.extractfile(m).read()).hexdigest() for m in t.getmembers() if m.isfile()}
 check='import hashlib,json,pathlib,sys; d=json.loads(sys.argv[1]); bad=[p for p,h in d.items() if hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()!=h]; print(json.dumps(dict(files=len(d),bad=bad))); sys.exit(bool(bad))'
 result[slot]=subprocess.check_output(['docker','exec',container,'python3','-c',check,json.dumps(expected)],text=True).strip()
print(json.dumps(result))
'''
            run('motion',['python3','-c',code,STAGE],'verify-files')
        elif args.phase == 'start-cc':
            verified=json.loads((out/'migration-verify-files.json').read_text())
            if verified['returncode'] != 0:
                raise RuntimeError('Restored file verification not successful')
            if not all(c['State']['Running'] for c in data):
                raise RuntimeError('Motion service not running')
            run('vision',['docker','start','walker-system.control_center-1'],'start-cc')
    print('Completed phase '+args.phase+'; E-stop remains pressed, no PICO START')


if __name__ == '__main__':
    main()
