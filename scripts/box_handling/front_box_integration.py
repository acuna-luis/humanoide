#!/usr/bin/env python3
"""Build/install/check the frontal-box adapter; --flow executes the supplied flow."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
TASK_ROOT = '/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/'
META_ROOT = '/opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config/meta_clamp/'
SNAPSHOT = ROOT/'vendor/ubtech/cruzr_s2/snapshot_20260916/motion'
FILES = ('select_front_box.py','probe_front_box.py','front_sps_contract.py',
         'front_sps_worker.py','front_sps_native.py','front_sps_session.py')


def sha(data):
    return hashlib.sha256(data.encode() if isinstance(data,str) else data).hexdigest()


def build_bundle():
    source_yaml = (SNAPSHOT/'meta_clamp/wrc/separate_right_cruzr.yaml').read_text()
    source_xml = (SNAPSHOT/'tasks/Singapore/separate_right_cruzr.xml').read_text()
    bodyback = (SNAPSHOT/'meta_clamp/wrc/separate_bodyback_cruzr.yaml').read_text()
    if source_yaml.count('\nrequest:\n') != 1 or 'special_box_name' in source_yaml:
        raise ValueError('Unexpected original YAML')
    configured_yaml = source_yaml.replace('\nrequest:\n','\nrequest:\n  special_box_name: box\n')
    tree = ET.fromstring(source_xml)
    sequence = tree.find('./BehaviorTree/Sequence')
    sequence.insert(0, ET.Element('Action', ID='MetaLook', start_vision_mode='sps_vision'))
    changed = 0
    for action in sequence.iter('Action'):
        if action.get('ID')=='MetaClamp' and action.get('name')=='wrc/separate_right_cruzr':
            action.set('name','local_front_box/separate_right_cruzr'); changed+=1
    if changed!=1:
        raise ValueError('Unexpected original task')
    ET.indent(tree,space='    ')
    check_xml = '''<root main_tree_to_execute="MainTree">
    <BehaviorTree ID="MainTree"><Sequence name="root_sequence">
        <Action ID="MetaLook" start_vision_mode="sps_vision" />
        <Action ID="MetaLook" task_type="SPS" object_name="box" object_id="0" />
    </Sequence></BehaviorTree>
</root>
'''
    tasks = {TASK_ROOT+'local_front_box/detect_only.xml':check_xml,
             TASK_ROOT+'local_front_box/separate_right_cruzr.xml':ET.tostring(tree,encoding='unicode')+'\n',
             META_ROOT+'local_front_box/separate_right_cruzr.yaml':configured_yaml}
    dependencies = {TASK_ROOT+'Singapore/separate_right_cruzr.xml':sha(source_xml),
                    META_ROOT+'wrc/separate_right_cruzr.yaml':sha(source_yaml),
                    META_ROOT+'wrc/separate_bodyback_cruzr.yaml':sha(bodyback)}
    sources = {name:(HERE/name).read_text() for name in FILES}
    package_id = sha(json.dumps({'sources':sources,'tasks':tasks},sort_keys=True))[:16]
    manifest = dict(id=package_id,sources={n:sha(t) for n,t in sources.items()},
                    dependencies=dependencies,
                    robot_files={**dependencies,**{n:sha(t) for n,t in tasks.items()}},
                    native_binaries={
                      '/opt/walker/manipulation_meta_tasks/lib/libmeta_clamp.so':'d6bc61a493f7d790150fdbd673108121f46589fef56620de4a9023dcc2ba520a',
                      '/opt/walker/manipulation_meta_tasks/lib/libmeta_look.so':'dc8a41bf3fa747ae91ce95d51d871042bbcdc5c11858ac37085a0627028063a7',
                      '/opt/walker/manipulation_perception/lib/libperception_action_client.so':'8b45c88e41eb797382d5bb7d89976e1eff60b31f931c866bf8f1ab3eb0c27421'})
    return dict(manifest=manifest,sources=sources,tasks=tasks)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--build',type=Path,metavar='NEW_DIRECTORY')
    mode.add_argument('--install',action='store_true')
    mode.add_argument('--check',action='store_true')
    mode.add_argument('--check-runtime',action='store_true',
                      help='Read-only package/discovery/controller preflight; no perception tasks')
    mode.add_argument('--flow',action='store_true',help='Read authorized scenario Bash flow from stdin')
    parser.add_argument('--wifi',action='store_true')
    args=parser.parse_args()
    bundle=build_bundle()
    if args.build:
        args.build.mkdir(parents=True,exist_ok=False)
        (args.build/'bundle.json').write_text(json.dumps(bundle,indent=2)+'\n')
        print(args.build/'bundle.json');return 0
    package='/var/tmp/cruzr-front-box/'+bundle['manifest']['id']
    ssh=['setsid','-w','ssh','-T','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=8',
         '-o','ServerAliveInterval=5','-o','ServerAliveCountMax=3',
         '-o','PreferredAuthentications=password','-o','PubkeyAuthentication=no']
    if args.wifi:ssh+=['-J','walker@192.168.42.2']
    ssh+=['walker@192.168.11.2']
    env=dict(os.environ,CRUZR_INTERNAL_ASKPASS='1',
             SSH_ASKPASS=str(ROOT/'scripts/cruzr_recover_to_home.sh'),
             SSH_ASKPASS_REQUIRE='force',DISPLAY=os.environ.get('DISPLAY',':0'))
    if args.install:
        command='python3 -c '+shlex.quote((HERE/'front_sps_install_remote.py').read_text())
        payload=json.dumps(bundle)
    else:
        command='python3 '+shlex.quote(package+'/front_sps_session.py')+' --package '+shlex.quote(package)
        if args.check:command+=' --check'
        if args.check_runtime:command+=' --check-runtime'
        payload=sys.stdin.read() if args.flow else ''
    return subprocess.run(ssh+[command],env=env,input=payload,text=True).returncode


if __name__=='__main__':
    sys.exit(main())
