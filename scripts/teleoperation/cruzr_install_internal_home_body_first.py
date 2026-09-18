#!/usr/bin/env python3
"""Check/install/reload the body-first v5 internal HOME definition under E-stop.

No action goal, StartMotion, mode switch or automatic E-stop release is sent.
The six-second draft deliberately cannot be installed with this tool.
"""
import argparse
import base64
import concurrent.futures
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
from collect_estop_available_readonly import execute, ros
from cruzr_internal_home_body_first import validate_xml

CONTAINER = 'walker-motion.manipulation_robot_app-1'
XML = ROOT/'scripts/teleoperation/tasks/cruzr_internal_home_body_first_v7_13s.xml'
TARGET = '/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/cruzr/home.xml'
BASE_SHA = '05174d2b4cf003b9b1c5274cd445b0d4faefe4276c5fbe8e59e68e6b64ee8cbe'
V4_SHA = 'e3d0656424a3611d89262ae645f127d975920fd09c437f9ef9c07725d69dc49c'
# Installed 2026-09-18 11:52 Madrid, superseded before any boot by the 18 s timing.
V5_21S_SHA = '212f3ad81120d99e857fbdea6c94548402e783f371a449ac19a07d59ef9b19fb'
V5_18S_SHA = 'adc24aba387ceb94a229db14d28668a04e7b9a64432ffa9989dd7145cc9cbf4c'
NEW_SHA = '1e6e2fb7ddc598dc3793d093c283c82063507df0e53b70a18e161cab883a6f03'
LABELS = {BASE_SHA: 'open-v3-20s', V4_SHA: 'body-first-v4-20s', V5_21S_SHA: 'body-first-v5-21s',
          V5_18S_SHA: 'body-first-v5-18s', NEW_SHA: 'body-first-v7-13s'}
HOME_GATE = ROOT/'scripts/lib/cruzr_home_posture_gate.py'
# Joint states are not published while the E-stop is pressed, so HOME is
# measured first (--measure-home, E-stop released) and --install then requires
# that record: same Motion boot, same robot_app log, no BTree task since, fresh.
POSTURE_RECORD = ROOT.parent/'Humanoide-vla-evidence'/'HOME_POSTURE_LATEST.json'
POSTURE_MAX_AGE_S = 1800
META_LIB = '/opt/walker/manipulation_meta_tasks/lib/libmeta_move.so'
META_SHA = 'bfeab1c7a295b58cd96fddd20916fc3f7fe16bd8c8ad1e77720f48aad34ccc69'


def require(result, name):
    if result.get('returncode') != 0:
        raise RuntimeError(name+': '+result.get('stderr', result.get('error', 'failed')))
    return result.get('stdout', '')


def status(evidence):
    queries = {'containers': ['docker', 'ps', '--format', '{{.Names}}'],
               'home_sha': ['docker','exec',CONTAINER,'sha256sum',TARGET],
               'meta_sha': ['docker','exec',CONTAINER,'sha256sum',META_LIB],
               'started': ['docker','inspect','--format','{{.State.StartedAt}}',CONTAINER]}
    for name in ('estop_key_state','servo_estop_key_state','chrg_input_status'):
        queries[name] = ros('walker-ros.ros2-1', 'ros2 topic echo --once --no-daemon /emb/'+name+' std_msgs/msg/UInt8')
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        jobs = {pool.submit(execute, 'motion', cmd): name for name,cmd in queries.items()}
        for job in concurrent.futures.as_completed(jobs): results[jobs[job]] = job.result()
    (evidence/'status.json').write_text(json.dumps(results, indent=2)+'\n')
    for name,result in results.items(): require(result,name)
    containers = results['containers']['stdout'].splitlines()
    if CONTAINER not in containers or 'walker-ros.ros2-1' not in containers:
        raise RuntimeError('required running containers absent')
    for name,value in (('estop_key_state',1),('servo_estop_key_state',0),('chrg_input_status',0)):
        if results[name]['stdout'].strip() != f'data: {value}\n---':
            raise RuntimeError('Require main E-stop pressed, servo stop released, charger disconnected: '+name)
    if results['meta_sha']['stdout'].split()[0] != META_SHA:
        raise RuntimeError('MetaMove build changed; review the relative-joint contract again')
    sha = results['home_sha']['stdout'].split()[0]
    if sha not in LABELS: raise RuntimeError('Unrecognized HOME definition; preserve and review it')
    print('ESTOP=pressed; CHARGER=disconnected; META_MOVE=expected-build')
    print('HOME_DEFINITION='+LABELS[sha])
    return sha


def motion_identity():
    boot = require(execute('motion', ['cat', '/proc/sys/kernel/random/boot_id']), 'boot_id').strip()
    log = require(execute('motion', ['bash', '-c', 'ls -t /etc/walker/log/motion/robot_app*.log | head -1']),
                  'robot_app_log').strip()
    counted = execute('motion', ['grep', '-ac', 'BTree task: ', log])
    if counted.get('returncode') not in (0, 1) or not counted.get('stdout', '').strip().isdigit():
        raise RuntimeError('robot_app task count unavailable')
    return {'boot_id': boot, 'robot_app_log': log, 'btree_tasks': int(counted['stdout'].strip())}


def measure_home(evidence):
    sample = require(execute('motion', ros(CONTAINER, 'rosa topic echo --once --no-daemon /mc/actuator_state', True)),
                     'actuator_state')
    gate = subprocess.run([sys.executable, str(HOME_GATE), '--home-tolerance', '0.02'],
                          input=sample, capture_output=True, text=True, timeout=10)
    (evidence/'actuator_state.json').write_text(sample)
    (evidence/'home_gate.log').write_text(gate.stdout+gate.stderr)
    if gate.returncode or 'MEASURED_HOME=1' not in gate.stdout.split():
        raise RuntimeError('Not at measured HOME (tolerance 0.02 rad): run cruzr/home and measure again '
                           'before pressing the E-stop. '+(gate.stdout+gate.stderr).strip().replace('\n', '; '))
    record = dict(motion_identity(), measured_epoch=time.time(),
                  measured_utc=dt.datetime.now(dt.timezone.utc).isoformat(), gate=gate.stdout.split())
    (evidence/'home_posture.json').write_text(json.dumps(record, indent=2)+'\n')
    POSTURE_RECORD.write_text(json.dumps(record, indent=2)+'\n')
    print('MEASURED_HOME=1; RECORD='+str(POSTURE_RECORD))


def require_recent_home(now=None):
    try:
        record = json.loads(POSTURE_RECORD.read_text())
    except (OSError, ValueError):
        raise RuntimeError('No HOME posture record: with the E-stop released and the robot at HOME, '
                           'run --measure-home, then press the E-stop and install')
    age = (time.time() if now is None else now) - float(record.get('measured_epoch', 0))
    if not 0 <= age <= POSTURE_MAX_AGE_S:
        raise RuntimeError('HOME posture record is %d s old; measure again' % age)
    current = motion_identity()
    for key in ('boot_id', 'robot_app_log', 'btree_tasks'):
        if current[key] != record.get(key):
            raise RuntimeError('Robot changed since HOME was measured (%s); measure again' % key)
    print('HOME_POSTURE=measured %d s ago; same boot; no task since' % age)


# This check is executed on the host immediately before a mutation. It does
# not call a service; an error, missing topic or non-pressed stop aborts.
ESTOP_CHECK = r'''
import subprocess
r=subprocess.run(['docker','exec','walker-ros.ros2-1','bash','-lc',
    'source /opt/ros/humble/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; timeout 7 ros2 topic echo --once --no-daemon /emb/estop_key_state std_msgs/msg/UInt8'],
    capture_output=True,text=True,timeout=10)
if r.returncode or r.stdout.strip() != 'data: 1\n---':
    raise SystemExit('E-stop is not demonstrably pressed; no change')
'''

INSTALL = r'''
import base64,datetime,hashlib,json,os,pathlib,shutil,stat,sys,tempfile
target=pathlib.Path(sys.argv[1]); expected=sys.argv[2]; new_sha=sys.argv[3]
data=base64.b64decode(sys.argv[4],validate=True)
assert hashlib.sha256(data).hexdigest()==new_sha
current=target.read_bytes()
assert hashlib.sha256(current).hexdigest()==expected, 'HOME changed since preflight'
backup=pathlib.Path('/etc/walker/trajectory-overlays')/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'_home_body_first')
backup.mkdir(parents=True,exist_ok=False)
shutil.copy2(target,backup/'home.before.xml')
info=target.stat()
fd,temp=tempfile.mkstemp(prefix='.home.body-first.',dir=target.parent)
try:
 with os.fdopen(fd,'wb') as f:
  f.write(data); f.flush(); os.fsync(f.fileno())
 os.chmod(temp,stat.S_IMODE(info.st_mode)); os.chown(temp,info.st_uid,info.st_gid)
 assert hashlib.sha256(target.read_bytes()).hexdigest()==expected
 os.replace(temp,target)
finally:
 if os.path.exists(temp): os.unlink(temp)
assert hashlib.sha256(target.read_bytes()).hexdigest()==new_sha
manifest={'target':str(target),'before_sha256':expected,'after_sha256':new_sha,
 'task':'cruzr/home','seconds':13.45,'movement_commands':0,
 'note':'Physical trial pending. Backup restores the previous reviewed HOME; no automatic rollback.'}
(backup/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(dict(manifest,backup=str(backup))))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--check',action='store_true',help='Local XML/tests only, default')
    group.add_argument('--measure-home',action='store_true',help='E-stop released: record measured HOME posture (read-only)')
    group.add_argument('--preflight',action='store_true',help='Read-only robot inspection under E-stop')
    group.add_argument('--install',action='store_true',help='Atomic HOME replacement; arms down/empty, stable, E-stop maintained')
    group.add_argument('--reload',action='store_true',help='Restart manipulation only under E-stop; does not start Motion')
    args=parser.parse_args()
    data=XML.read_bytes(); validate_xml(data,20,version=7)
    if hashlib.sha256(data).hexdigest()!=NEW_SHA: raise RuntimeError('Unexpected local XML hash')
    if not (args.preflight or args.install or args.reload or args.measure_home):
        subprocess.run([sys.executable,'-m','unittest',
            str(Path(__file__).with_name('test_cruzr_internal_home_body_first.py'))],check=True)
        print('LOCAL_CHECK_OK=home-body-first-v7-13s; MOVEMENT_COMMANDS=0; SIX_SECOND_DRAFT=not-installable')
        return
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    evidence=ROOT.parent/'Humanoide-vla-evidence'/(stamp+'_INTERNAL-HOME-CHANGE')
    evidence.mkdir(); print('EVIDENCE='+str(evidence),flush=True)
    if args.measure_home:
        measure_home(evidence); return
    sha=status(evidence)
    if args.preflight: return
    if args.install:
        if sha == NEW_SHA:
            print('INSTALL_NOOP=already-exact'); return
        require_recent_home()
        code=ESTOP_CHECK+'\nimport sys\n'+f'cmd={repr(["docker","exec","-u","0",CONTAINER,"python3","-c",INSTALL,TARGET,sha,NEW_SHA,base64.b64encode(data).decode()])}\n'+\
            "r=subprocess.run(cmd,capture_output=True,text=True,timeout=5)\nprint(r.stdout,end='')\nprint(r.stderr,end='',file=sys.stderr)\nraise SystemExit(r.returncode)\n"
    else:
        if sha != NEW_SHA: raise RuntimeError('Install reviewed HOME before reloading')
        code=ESTOP_CHECK+f'''
import sys
c={CONTAINER!r}
before=subprocess.check_output(['docker','inspect','--format','{{{{.State.StartedAt}}}}',c],text=True).strip()
r=subprocess.run(['docker','restart','--time','5',c],capture_output=True,text=True,timeout=12)
if r.returncode: raise SystemExit(r.stderr)
after=subprocess.check_output(['docker','inspect','--format','{{{{.State.StartedAt}}}}',c],text=True).strip()
assert before != after
print('MANIPULATION_RESTARTED=1; MOVEMENT_COMMANDS=0; MOTION_RECOVERY=not-attempted')
print('STARTED_BEFORE='+before+'; STARTED_AFTER='+after)
'''
    result=execute('motion',['python3','-c',code])
    (evidence/'mutation-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(require(result,'mutation'),end='')
    after=evidence/'after'; after.mkdir(); observed=status(after)
    if observed != NEW_SHA: raise RuntimeError('Post-change verification failed; keep E-stop, do not retry blindly')
    (evidence/'cruzr_internal_home_body_first_v7_13s.xml').write_bytes(data)
    print('KEEP_ESTOP_PRESSED=1; NO_MODE_CHANGE=1; NO_AUTOMATIC_RELEASE=1')
    print('HOME is now body-first v7 (13.45 s); physical trial and startup recovery remain separate.')


if __name__ == '__main__':
    try: main()
    except (RuntimeError,ValueError,subprocess.SubprocessError) as exc:
        print('ERROR: '+str(exc),file=sys.stderr); raise SystemExit(1)
