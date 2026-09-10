#!/usr/bin/env python3
"""Check/install/reload the 20-second internal HOME definition under E-stop.

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

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
from collect_estop_available_readonly import execute, ros
from cruzr_internal_home_open_path import validate_xml

CONTAINER = 'walker-motion.manipulation_robot_app-1'
XML = ROOT/'scripts/teleoperation/tasks/cruzr_internal_home_open_v3_20s.xml'
TARGET = '/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/cruzr/home.xml'
BASE_SHA = '50d819d6d6190280c6efee1dc275877362c3f7c807ec733fbc3c7ed217daed88'
NEW_SHA = '05174d2b4cf003b9b1c5274cd445b0d4faefe4276c5fbe8e59e68e6b64ee8cbe'
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
    if sha not in (BASE_SHA, NEW_SHA): raise RuntimeError('Unrecognized HOME definition; preserve and review it')
    print('ESTOP=pressed; CHARGER=disconnected; META_MOVE=expected-build')
    print('HOME_DEFINITION='+('open-v3-20s' if sha == NEW_SHA else 'vendor-direct-6s'))
    return sha


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
backup=pathlib.Path('/etc/walker/trajectory-overlays')/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'_home_open_v3')
backup.mkdir(parents=True,exist_ok=False)
shutil.copy2(target,backup/'home.before.xml')
info=target.stat()
fd,temp=tempfile.mkstemp(prefix='.home.open-v3.',dir=target.parent)
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
 'task':'cruzr/home','seconds':20,'movement_commands':0,
 'note':'Physical trial pending. Original backup restores direct HOME; no automatic rollback.'}
(backup/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(dict(manifest,backup=str(backup))))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--check',action='store_true',help='Local XML/tests only, default')
    group.add_argument('--preflight',action='store_true',help='Read-only robot inspection under E-stop')
    group.add_argument('--install',action='store_true',help='Atomic HOME replacement; arms down/empty, stable, E-stop maintained')
    group.add_argument('--reload',action='store_true',help='Restart manipulation only under E-stop; does not start Motion')
    args=parser.parse_args()
    data=XML.read_bytes(); validate_xml(data,20)
    if hashlib.sha256(data).hexdigest()!=NEW_SHA: raise RuntimeError('Unexpected local XML hash')
    if not (args.preflight or args.install or args.reload):
        subprocess.run([sys.executable,'-m','unittest',
            str(Path(__file__).with_name('test_cruzr_internal_home_open_path.py')),
            str(Path(__file__).with_name('test_cruzr_install_internal_home.py'))],check=True)
        print('LOCAL_CHECK_OK=home-open-v3-20s; MOVEMENT_COMMANDS=0; SIX_SECOND_DRAFT=not-installable')
        return
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    evidence=ROOT.parent/'Humanoide-vla-evidence'/(stamp+'_INTERNAL-HOME-CHANGE')
    evidence.mkdir(); print('EVIDENCE='+str(evidence),flush=True)
    sha=status(evidence)
    if args.preflight: return
    if args.install:
        if sha == NEW_SHA:
            print('INSTALL_NOOP=already-exact'); return
        code=ESTOP_CHECK+'\nimport sys\n'+f'cmd={repr(["docker","exec","-u","0",CONTAINER,"python3","-c",INSTALL,TARGET,BASE_SHA,NEW_SHA,base64.b64encode(data).decode()])}\n'+\
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
    (evidence/'cruzr_internal_home_open_v3_20s.xml').write_bytes(data)
    print('KEEP_ESTOP_PRESSED=1; NO_MODE_CHANGE=1; NO_AUTOMATIC_RELEASE=1')
    print('HOME is now a 20-second candidate; physical trial and startup recovery remain separate.')


if __name__ == '__main__':
    try: main()
    except (RuntimeError,ValueError,subprocess.SubprocessError) as exc:
        print('ERROR: '+str(exc),file=sys.stderr); raise SystemExit(1)
