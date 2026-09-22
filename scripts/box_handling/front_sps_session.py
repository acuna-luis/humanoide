#!/usr/bin/env python3
"""Motion-host supervisor: short-lived perception processes around one command."""
import argparse
import ast
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import time

NATIVE = 'walker-motion.manipulation_robot_app-1'
ROS2 = 'walker-ros.ros2-1'
TASK_ROOT = '/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/'
META_ROOT = '/opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config/meta_clamp/'
NATIVE_ENV = 'export ROSA_MIDDLE_WARE=cyclone ROSA_USE_SHM=OFF; '


def discovery_output(stdout):
    """Remove only the observed vendor INFO announcing our no-SHM override."""
    notice = (r'I\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+ '
              r'\[\d+\.\d+\] \d+ \[context_options\.cpp:\d+:operator\(\)\]: '
              r'Shared memory mode is turned off\.')
    return '\n'.join(line for line in stdout.splitlines()
                     if not re.fullmatch(notice, line))


def check_sps_discovery(query):
    """Confirm a live graph and no SPS servers, including unused endpoints.

    ROSA prints only a newline (rc=0) for an action without clients/servers.
    Accept that only when a successful, populated action list agrees.
    ``query`` runs read-only ROSA CLI commands and returns CompletedProcess.
    """
    def checked(command):
        result = query(command)
        if result.returncode or result.stderr.strip():
            raise RuntimeError('SPS discovery failed: '+command+
                               ' rc='+str(result.returncode)+
                               ' stdout='+repr(result.stdout[-2000:])+
                               ' stderr='+repr(result.stderr[-2000:]))
        return discovery_output(result.stdout)

    listing = checked('action list --no-daemon -t')
    actions = {}
    for line in listing.splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r'(/[^\s:]+)\s*:\s*([\w/]+)', line.strip())
        if not match or match[1] in actions:
            raise RuntimeError('Malformed SPS discovery action list: '+repr(line))
        actions[match[1]] = match[2]
    for name, expected in {
        '/mc/manipulation/action': 'mc_task_msgs/action/ArmTask',
        '/cv/task/transport_action': 'cv_task_msgs/action/VisionActionTask',
    }.items():
        if actions.get(name) != expected:
            raise RuntimeError('SPS discovery graph incomplete: '+name)

    evidence = {}
    for endpoint in ('/cv/task/sps_pose_action', '/cv/task/sps_select_action'):
        if endpoint in actions and actions[endpoint] != 'cv_task_msgs/action/VisionActionTask':
            raise RuntimeError('Unexpected SPS action type: '+endpoint)
        output = checked('action info --no-daemon '+endpoint)
        if not output.strip() and endpoint not in actions:
            evidence[endpoint] = 'absent'
            continue
        counts = re.findall(r'^Action server count:\s*(\d+)\s*$', output, re.M)
        if len(counts) != 1:
            raise RuntimeError('SPS discovery inconsistent: '+endpoint+' stdout='+repr(output[-2000:]))
        if int(counts[0]) != 0:
            raise RuntimeError('SPS server already exists: '+endpoint+' servers='+counts[0])
        evidence[endpoint] = 'servers=0'
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', required=True, type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--check-runtime', action='store_true',
                      help='Read-only preflight; no adapters or perception tasks')
    args = parser.parse_args()
    package = args.package.resolve()
    manifest = json.loads((package/'manifest.json').read_text())
    container_root = '/opt/cruzr-front-box/'+manifest['id']
    lockfile = open('/tmp/cruzr-front-sps.lock', 'a')
    fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def docker_script(container, setup, script, *arguments, **kwargs):
        command = ('source '+setup+'; export ROS2CLI_DISABLE_DAEMON=1; '+
                   (NATIVE_ENV if container == NATIVE else '')+'exec '+script)
        return subprocess.run(['docker', 'exec', container, 'bash', '-lc', command,
                               'front-sps', *arguments], **kwargs)

    for container in (NATIVE, ROS2):
        running = subprocess.check_output(['docker', 'inspect', '-f', '{{.State.Running}}', container], text=True)
        if running.strip() != 'true':
            raise RuntimeError('Required container is not running: '+container)
        for name, expected in manifest['sources'].items():
            data = subprocess.check_output(['docker', 'exec', container, 'cat', container_root+'/'+name])
            if hashlib.sha256(data).hexdigest() != expected:
                raise RuntimeError('Installed source mismatch: '+name)
    for path, expected in manifest['robot_files'].items():
        data = subprocess.check_output(['docker', 'exec', NATIVE, 'cat', path])
        if hashlib.sha256(data).hexdigest() != expected:
            raise RuntimeError('Task/dependency changed: '+path)
    for path, expected in manifest['native_binaries'].items():
        row = subprocess.check_output(['docker', 'exec', NATIVE, 'sha256sum', path], text=True)
        if row.split()[0] != expected:
            raise RuntimeError('Native binary changed; re-audit required')
    # Motion retains SPS clients after a check. Existing clients are expected;
    # only another SERVER would collide with this session's adapter.
    discovery = check_sps_discovery(lambda command: docker_script(
        NATIVE, '/opt/walker/setup.bash', 'timeout 8 rosa '+command,
        capture_output=True, text=True, timeout=12))
    print('FRONT_SPS_DISCOVERY='+json.dumps(discovery, sort_keys=True), flush=True)
    status = docker_script(ROS2, '/opt/ros/humble/setup.bash',
                           'timeout 8 ros2 topic echo --once --no-daemon /mc/manipulation/action/_action/status',
                           capture_output=True, text=True)
    if (status.returncode or 'status_list:' not in status.stdout or
            re.search(r'^\s*status:\s*[123]\s*$', status.stdout, re.M)):
        raise RuntimeError('Motion action busy or idle state unverified')
    inventory = docker_script(NATIVE, '/opt/walker/setup.bash',
        "timeout 7 rosa service call /mc/controller_manager/list_controllers rosa_control_msgs/srv/ListControllers '{}'",
        capture_output=True,text=True)
    marker='Response(controller='
    if inventory.returncode or inventory.stdout.count(marker)!=1:
        raise RuntimeError('Cannot verify the active controller')
    literal=inventory.stdout.split(marker,1)[1].splitlines()[0]
    if not literal.endswith(')'):
        raise RuntimeError('Malformed controller inventory')
    controllers=ast.literal_eval(literal[:-1])
    states={row['name']:row['state'] for row in controllers}
    if len(states)!=len(controllers) or any(states.get(name)!=state for name,state in
            {'manipulation_controller':'running','vla_sdk_controller':'initialized',
             'sdk_controller':'initialized'}.items()):
        raise RuntimeError('Controller change would be required; no automatic handoff')

    if args.check_runtime:
        print('CHECK_SPS_RUNTIME_OK: hashes, descubrimiento y controlador verificados; '
              'sin iniciar adaptadores ni enviar tareas.', flush=True)
        return 0

    session = Path(tempfile.mkdtemp(prefix='cruzr-front-sps-', dir='/tmp'))
    (session/'lease.json').write_text(json.dumps({'deadline':time.monotonic()+900}))
    print('FRONT_SPS_SESSION='+str(session), flush=True)
    processes, logs = [], []
    flow_process = None
    def interrupt(signum, frame):
        raise InterruptedError('Supervisor interrupted; physical completion unconfirmed')
    for sig in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(sig, interrupt)
    try:
        for container, setup, filename, ready in [
            (ROS2, '/opt/ros/humble/setup.bash', 'front_sps_worker.py', 'worker.ready'),
            (NATIVE, '/opt/walker/setup.bash', 'front_sps_native.py', 'native.ready')]:
            logfile = (session/(filename+'.log')).open('w'); logs.append(logfile)
            command = ('source '+setup+'; export ROS2CLI_DISABLE_DAEMON=1; '+
                       (NATIVE_ENV if container == NATIVE else '')+'exec python3 '+
                       shlex.quote(container_root+'/'+filename)+' --session '+shlex.quote(str(session)))
            process = subprocess.Popen(['docker','exec',container,'bash','-lc',command],
                                       stdout=logfile, stderr=subprocess.STDOUT)
            processes.append(process)
            end = time.monotonic()+12
            while not (session/ready).exists():
                if process.poll() is not None or time.monotonic() > end:
                    raise RuntimeError('Adapter startup failed; see '+str(session))
                time.sleep(0.1)
        if args.check:
            task = 'local_front_box/detect_only'
            goal = json.dumps({'task_name':task, 'yaml_args':'{}'})
            command = 'timeout 30 rosa action send_goal /mc/manipulation/action mc_task_msgs/action/ArmTask '+shlex.quote(goal)
            result = docker_script(NATIVE, '/opt/walker/setup.bash', command,
                                   capture_output=True, text=True, timeout=35)
            print(result.stdout, flush=True)
            (session/'native-task.txt').write_text(result.stdout+result.stderr)
            matches = re.findall(r'^Result: result=(.*), status=(\d+)\s*$',result.stdout,re.M)
            if result.returncode or len(matches)!=1 or matches[0][1]!='4':
                raise RuntimeError('Native detection-only task did not succeed')
            state = ast.literal_eval(matches[0][0])['state']
            if state.get('desc')!='SUCCEED' or state.get('state')!=1101001:
                raise RuntimeError('Native detection-only task returned failure')
            events = [json.loads(x) for x in (session/'selection.jsonl').read_text().splitlines()]
            selected = [x for x in events if x['event']=='selected']
            if len(selected)!=1 or any(x['event']=='failed' for x in events):
                raise RuntimeError('Expected one complete native selection transaction')
            print('NATIVE_FRONT_SELECTION='+json.dumps(selected[0]), flush=True)
            print('CHECK_SPS_OK: cliente nativo recibió la pose; sin trayectoria de agarre.', flush=True)
            return 0
        # The full flow is provided by the versioned wrapper, not stored on robot.
        flow = sys.stdin.read()
        if not flow:
            raise RuntimeError('Missing scenario flow')
        flow_process = subprocess.Popen(['docker','exec','-i','-e',
            'CRUZR_FRONT_SESSION='+str(session),'-e','ROSA_MIDDLE_WARE=cyclone',
            '-e','ROSA_USE_SHM=OFF',NATIVE,'bash','-s','--','run'],
            stdin=subprocess.PIPE,text=True)
        flow_process.communicate(flow)
        return flow_process.returncode
    finally:
        (session/'stop').write_text('stop\n')
        if flow_process is not None and flow_process.poll() is None:
            # Signal only our shell, after matching its private session token.
            # This does not establish physical cancellation of a ROSA goal.
            stop_shell = '''import os,pathlib,signal,sys
root=pathlib.Path(sys.argv[1]);p=root/'flow.pid'
if p.exists():
 pid=int(p.read_text());env=pathlib.Path('/proc')/str(pid)/'environ'
 if env.exists() and ('CRUZR_FRONT_SESSION='+str(root)).encode() in env.read_bytes().split(b'\\0'):
  os.kill(pid,signal.SIGTERM)
'''
            try:
                subprocess.run(['docker','exec',NATIVE,'python3','-c',stop_shell,str(session)],timeout=5)
            except (OSError,subprocess.TimeoutExpired):
                print('FLOW_SHELL_EXIT_UNCONFIRMED',file=sys.stderr)
            print('FLUJO_INTERRUMPIDO: confirmar parada física y caja antes de otra orden.',file=sys.stderr)
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate()
                print('ADAPTER_EXIT_UNCONFIRMED: lease expires automatically', file=sys.stderr)
        for logfile in logs:
            logfile.close()
        selection_log = session/'selection.jsonl'
        if selection_log.exists():
            for line in selection_log.read_text().splitlines():
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if entry.get('event') in ('failed', 'goal_rejected'):
                    print('FRONT_SPS_CAUSE='+json.dumps(entry, ensure_ascii=False), flush=True)
        print('FRONT_SPS_EVIDENCE='+str(session), flush=True)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print('FRONT_SPS_REJECTED: '+str(exc),file=sys.stderr)
        sys.exit(78)
