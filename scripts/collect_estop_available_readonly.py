#!/usr/bin/env python3
"""Fixed diagnostic reads only; no service calls, publishers or mode changes.

Requires freshly discovered container names and active Docker on both hosts.
Never connects to PC controller WebSocket. Writes evidence only on the PC.
"""
import concurrent.futures
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[1]
HOSTS = {'motion':'192.168.11.2','vision':'192.168.11.3'}


def execute(host, command):
    env = dict(os.environ,CRUZR_INTERNAL_ASKPASS='1',
        SSH_ASKPASS=str(ROOT/'scripts/cruzr_recover_to_home.sh'),SSH_ASKPASS_REQUIRE='force',
        DISPLAY=os.environ.get('DISPLAY',':0'))
    prefix = ['setsid','-w','ssh','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=5',
        '-o','PreferredAuthentications=password','-o','PubkeyAuthentication=no',
        '-o','NumberOfPasswordPrompts=1','walker@'+HOSTS[host]]
    start=dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        p=subprocess.run(prefix+[shlex.join(command)],env=env,capture_output=True,text=True,timeout=18)
        return dict(start_utc=start,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
    except subprocess.TimeoutExpired:
        return dict(start_utc=start,error='bounded_ssh_timeout')


def ros(container, command, native=False):
    setup='/opt/walker/setup.bash' if native else '/opt/ros/humble/setup.bash'
    shell='source '+setup+'; export ROS2CLI_DISABLE_DAEMON=1; timeout 7 '+command
    return ['docker','exec',container,'bash','-lc',shell]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--supplement',action='store_true',help='Only auxiliary reads after primary inventory')
    args=parser.parse_args()
    out=ROOT.parent/'Humanoide-vla-evidence'/(dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_ESTOP-AVAILABLE')
    out.mkdir(exist_ok=False)
    for host in HOSTS:
        state=execute(host,['systemctl','is-active','docker.service'])
        if state.get('returncode')!=0 or state.get('stdout','').strip()!='active':
            raise RuntimeError('Docker not active; no activation attempted: '+host)
    m='walker-motion.manipulation_robot_app-1'
    r='walker-ros.ros2-1'
    queries={}
    for host in HOSTS:
        queries[(host,'container_metadata')]=['docker','ps','-a','--format','{{.Names}}\t{{.Status}}']
        queries[(host,'clock')]=['date','-Is']
    for topic in ['estop_key_state','servo_estop_key_state','battery_state','chrg_input_status']:
        queries[('motion',topic)]=ros(r,'ros2 topic echo --once --no-daemon /emb/'+topic)
    queries[('motion','topics')]=ros(m,'rosa topic list',True)
    queries[('motion','actuators')]=ros(m,'rosa topic echo --once --no-daemon /mc/actuator_state',True)
    queries[('motion','joints')]=ros(m,'rosa topic echo --once --no-daemon --qos-reliability best_effort /mc/whole_joint_states',True)
    queries[('motion','action_server')]=ros(m,'rosa action info /mc/manipulation/action',True)
    queries[('motion','command_topic')]=ros(m,'rosa topic info /mc/sdk/robot_command',True)
    queries[('motion','action_status')]=ros(r,'ros2 topic echo --once --no-daemon /mc/manipulation/action/_action/status')
    for host,names in [('motion',['walker-motion.hw-1',m]),('vision',['walker-system.control_center-1'])]:
        for name in names:
            queries[(host,'log_'+name)]=['docker','logs','--tail','1500',name]
    for host,name in [('motion','cruzr-vla-control'),('vision','cruzr-vla-inference')]:
        queries[(host,'vla_state')]=['docker','inspect','--format',
            '{{.State.Status}} restart={{.HostConfig.RestartPolicy.Name}} started={{.State.StartedAt}} finished={{.State.FinishedAt}}',name]
    queries[('vision','netdata_health')]=['docker','inspect','--format','{{json .State.Health}}','walker-monitor.netdata-1']
    if args.supplement:
        queries={
            ('motion','actuator_graph'):ros(m,'rosa topic info /mc/actuator_state',True),
            ('motion','head_joints'):ros(m,'rosa topic echo --once --no-daemon --qos-reliability best_effort /mc/head/joint_states',True),
            ('motion','services'):ros(m,'rosa service list',True),
            ('motion','module_locks'):ros(m,'rosa topic echo --once --no-daemon /sys/state/module_lock_info',True),
            ('motion','walker_mode'):ros(m,'rosa topic echo --once --no-daemon /sys/state/walker_mode',True),
            ('vision','camera_info'):ros(r,'ros2 topic echo --once --no-daemon /sensor/camera/stereo_left/image/info'),
            ('vision','power'):ros(r,'ros2 topic echo --once --no-daemon /emb/emb_power_state'),
            ('vision','cc_latest'):['docker','exec','walker-system.control_center-1','tail','-n','180','/etc/walker/log/system/cc_main.latest.log'],
            ('motion','ros_setup'):['docker','exec',m,'test','-f','/opt/walker/setup.bash'],
        }
    results={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        jobs={pool.submit(execute,host,cmd):(host,key,cmd) for (host,key),cmd in queries.items()}
        for job in concurrent.futures.as_completed(jobs):
            host,key,cmd=jobs[job]
            data=job.result();data['command']=cmd
            results[host+'/'+key]=data
            print(host+'/'+key, data.get('returncode',data.get('error')),flush=True)
    report=dict(scope='bounded subscriptions and host/container diagnostic reads',queries=results,
        movement_commands=0,remote_configuration_changes=0,service_calls=0,
        physical_authorized=False,continuous_monitor=False)
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'collector.py').write_bytes(Path(__file__).read_bytes())
    (out/'evidence.sha256').write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n'
        for p in sorted(out.iterdir()) if p.is_file()))
    print(out)


if __name__=='__main__':
    main()
