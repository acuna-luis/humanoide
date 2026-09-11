#!/usr/bin/env python3
"""Record bounded passive Motion/E-stop telemetry. Does not start or stop motion."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds',type=float,default=10.)
    parser.add_argument('--output-dir',type=Path,required=True,help='New private PC evidence directory')
    args=parser.parse_args()
    if not 1<=args.seconds<=120:parser.error('seconds must be in [1,120]')
    if args.output_dir.exists():parser.error('Output directory already exists')
    sys.path.insert(0,str(ROOT/'scripts'))
    from collect_estop_available_readonly import execute
    result=execute('motion',['docker','ps','--format','{{.Names}}|{{.Image}}'])
    if result.get('returncode')!=0:raise ValueError('Motion discovery failed: '+result.get('stderr',result.get('error','')))
    candidates=[line.split('|')[0] for line in result['stdout'].splitlines()
                if 'manipulation_robot_app' in line.split('|')[0] and 'cruzr-s2' in line]
    if len(candidates)!=1:raise ValueError('Expected one discovered Cruzr manipulation container')
    container=candidates[0]
    ros_candidates=[line.split('|')[0] for line in result['stdout'].splitlines()
                    if line.split('|')[0].endswith('ros2-1')]
    if len(ros_candidates)!=1:raise ValueError('Expected one discovered ROS 2 container')
    ros_container=ros_candidates[0]
    source=Path(__file__).with_name('general_home')/'passive_trace_remote.py'
    payload=source.read_bytes()
    env=dict(os.environ,CRUZR_INTERNAL_ASKPASS='1',SSH_ASKPASS=str(ROOT/'scripts/cruzr_recover_to_home.sh'),
             SSH_ASKPASS_REQUIRE='force',DISPLAY=os.environ.get('DISPLAY',':0'))
    # Host monotonic clock timestamps all three subscriptions. Native ROSA
    # cannot reliably read the bridged E-stop topics; use ROS 2 for those.
    remote=['python3','-u','-','--seconds',str(args.seconds),
            '--motion-container',container,'--ros-container',ros_container]
    command=['setsid','-w','ssh','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=5',
        '-o','PreferredAuthentications=password','-o','PubkeyAuthentication=no',
        '-o','NumberOfPasswordPrompts=1','walker@192.168.11.2',shlex.join(remote)]
    args.output_dir.mkdir(mode=0o700,parents=True)
    (args.output_dir/'discovery.json').write_text(json.dumps(result,indent=2))
    (args.output_dir/'passive_trace_remote.py').write_bytes(payload)
    metadata=dict(schema='cruzr-passive-motion-capture-v1',
        started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),container=container,ros_container=ros_container,
        remote_python_sha256=hashlib.sha256(payload).hexdigest(),seconds=args.seconds,
        collector_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        remote_installs=0,movement_commands=0,stopping_commands=0)
    print('PASSIVE_CAPTURE='+str(args.output_dir),flush=True)
    with (args.output_dir/'trace.jsonl').open('xb') as stdout,(args.output_dir/'stderr.log').open('xb') as stderr:
        try:
            proc=subprocess.run(command,input=payload,env=env,stdout=stdout,stderr=stderr,timeout=args.seconds+20)
            metadata['returncode']=proc.returncode
        except subprocess.TimeoutExpired:
            metadata['returncode']=124;metadata['error']='bounded_ssh_timeout'
    records=[]; parse_errors=[]
    for number,line in enumerate((args.output_dir/'trace.jsonl').read_text().splitlines(),1):
        if not line.strip():continue
        try:
            record=json.loads(line)
            if not isinstance(record,dict):raise ValueError('Expected object')
            records.append(record)
        except ValueError as exc:parse_errors.append('line '+str(number)+': '+str(exc))
    ending=records[-1] if records and records[-1].get('kind')=='end' else {}
    metadata.update(counts=ending.get('counts',{}),stream_complete=bool(ending),
                    errors=ending.get('errors',[])+parse_errors[:30])
    metadata['actuator_samples_available']=metadata['counts'].get('/mc/actuator_state',0)>1
    metadata['both_stop_topics_observed']=all(metadata['counts'].get(topic,0)>0
        for topic in ['/emb/estop_key_state','/emb/servo_estop_key_state'])
    metadata['usable_capture']=bool(metadata['returncode']==0 and metadata['stream_complete']
        and metadata['actuator_samples_available'] and metadata['both_stop_topics_observed'] and not metadata['errors'])
    metadata['physical_approval']=False
    metadata['finished_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    (args.output_dir/'capture.json').write_text(json.dumps(metadata,indent=2)+'\n')
    (args.output_dir/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n'
        for p in sorted(args.output_dir.iterdir()) if p.is_file() and p.name!='SHA256SUMS'))
    print(json.dumps(metadata))
    return 0 if metadata['usable_capture'] else 3


if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,OSError) as exc:print('ERROR: '+str(exc),file=sys.stderr);raise SystemExit(2)
