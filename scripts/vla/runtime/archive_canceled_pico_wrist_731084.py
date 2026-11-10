#!/usr/bin/env python3
"""Archive the specific 731084 canceled attempt, preserving a durable block.

A prior exact-UUID status observation must be supplied as a pinned evidence
file. --check never changes task or marker. --archive retains a permanent
RECOVERY-...-intent.json, which cooperating wrist launchers reject; archival is
not proof of physical stop, does not identify the failure and cannot enable a
new motion. No robot command or goal is sent by this utility.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

SESSION = '731084b3e4f94527a37de07297724bf1'
GOAL = '2e20ea8d-34d9-4e4d-9192-e5e0c11e921d'
JOURNAL_SHA = 'b585aebe89551b9e2854891c9e458e3156f4d69e360deaea26bb04f62348fe98'
MARKER_SHA = 'e174d2895dda0a2e0784cbb7296b2c5b7524bc31add8f28cc80255a326e8252c'
TERMINAL_EVIDENCE_SHA = '62da2f4a136218f7de18829ef2dd296b9b825714f812f60b3a6e15e09d2f6db9'
TASK_SHA = 'd4c704e6ab369d250658a596cd6a5704258accf130971d3046748a8d132b616b'
TASK_ROOT = '/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/diagnostics'
TASK_NAME = 'pico_v4_wrist_d4c704e6ab369d25.xml'
TASK_PATH = TASK_ROOT + '/' + TASK_NAME
DEVICE, INODE, DIR_DEVICE, DIR_INODE = 45, 3584597, 45, 3584589
CONTROL = Path('/var/tmp/cruzr-pico-v4-wrist-control')
LEASE_DIR = Path('/tmp/pico-wrist-live-xdhdhgsd')
APP = 'walker-motion.manipulation_robot_app-1'
ROS = 'walker-ros.ros2-1'

# Runs inside the app container; no ROS, network or physical command.
CONTAINER_ARCHIVE = r'''import hashlib,json,os,stat,sys
p=json.loads(sys.stdin.readline())
flags=os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC|getattr(os,'O_NOFOLLOW',0)
d=os.open(p['root'],flags)
try:
 s=os.fstat(d)
 if (s.st_dev,s.st_ino)!=(p['dir_dev'],p['dir_ino']): raise ValueError('directory_changed')
 fd=os.open(p['name'],os.O_RDONLY|os.O_CLOEXEC|getattr(os,'O_NOFOLLOW',0),dir_fd=d)
 try:
  s=os.fstat(fd)
  if not stat.S_ISREG(s.st_mode) or (s.st_dev,s.st_ino)!=(p['dev'],p['ino']): raise ValueError('task_identity_changed')
  with os.fdopen(fd,'rb',closefd=False) as f: raw=f.read()
  if hashlib.sha256(raw).hexdigest()!=p['sha']: raise ValueError('task_hash_changed')
 finally: os.close(fd)
 name='.'+p['name']+'.archived-'+p['session']
 try: os.stat(name,dir_fd=d,follow_symlinks=False); raise ValueError('archive_already_exists')
 except FileNotFoundError: pass
 if p['mode']=='archive':
  # Same-filesystem hard link gives a no-overwrite backup of the exact inode.
  os.link(p['name'],name,src_dir_fd=d,dst_dir_fd=d,follow_symlinks=False)
  s=os.stat(name,dir_fd=d,follow_symlinks=False)
  original=os.stat(p['name'],dir_fd=d,follow_symlinks=False)
  if (s.st_dev,s.st_ino)!=(p['dev'],p['ino']) or (original.st_dev,original.st_ino)!=(p['dev'],p['ino']): raise ValueError('archive_identity_changed')
  os.fsync(d)
  os.unlink(p['name'],dir_fd=d)
  os.fsync(d)
  fd=os.open(name,os.O_RDONLY|os.O_CLOEXEC|getattr(os,'O_NOFOLLOW',0),dir_fd=d)
  try:
   s=os.fstat(fd)
   with os.fdopen(fd,'rb',closefd=False) as f: archived=f.read()
   if (s.st_dev,s.st_ino)!=(p['dev'],p['ino']) or hashlib.sha256(archived).hexdigest()!=p['sha']: raise ValueError('archive_verification_failed')
  finally: os.close(fd)
 print(json.dumps({'mode':p['mode'],'task_sha256':p['sha'],'device':p['dev'],'inode':p['ino'],'archive_name':name}),flush=True)
finally: os.close(d)
'''


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_regular(path):
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | getattr(os, 'O_NOFOLLOW', 0))
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > 65536:
            raise ValueError('invalid_regular_file:' + path.name)
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            return stream.read(), info
    finally:
        os.close(fd)


def durable_new(path, value):
    raw = (json.dumps(value, sort_keys=True, allow_nan=False) + '\n').encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC |
                 getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(fd, 'wb') as stream:
        created = os.fstat(stream.fileno())
        if stream.write(raw) != len(raw):
            raise OSError('incomplete_durable_receipt')
        stream.flush(); os.fsync(stream.fileno())
    reread, observed = read_regular(path)
    if reread != raw or (created.st_dev,created.st_ino) != (observed.st_dev,observed.st_ino):
        raise RuntimeError('durable_receipt_readback_mismatch')
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)
    return sha(raw)


def validate_record(control, lease_dir):
    marker, marker_info = read_regular(control/'PENDING_OR_UNRESOLVED.json')
    expected = {'session_id':SESSION, 'task_path':TASK_PATH, 'task_sha256':TASK_SHA,
                'state':'intent_before_stage_or_send'}
    if json.loads(marker) != expected:
        raise ValueError('unresolved_marker_mismatch')
    mirror, mirror_info = read_regular(lease_dir/('intent-'+SESSION+'.json'))
    if mirror != marker:
        raise ValueError('mirrored_intent_mismatch')
    lease, lease_info = read_regular(lease_dir/('arm-lease-'+SESSION+'.json'))
    if json.loads(lease) != {'deadline':0.0}:
        raise ValueError('lease_not_revoked')
    events_raw, event_info = read_regular(control/('worker-events-'+SESSION+'.jsonl'))
    if sha(marker) != MARKER_SHA or sha(events_raw) != JOURNAL_SHA:
        raise ValueError('record_hash_mismatch')
    rows = [json.loads(line) for line in events_raw.splitlines()]
    if len(rows) < 8 or [r.get('event') for r in rows[:4]] != [
            'BRIDGE_READY', 'stage_receipt', 'uuid_request', 'dispatched']:
        raise ValueError('accepted_journal_sequence_mismatch')
    receipt = rows[1].get('receipt', {})
    if (rows[1].get('session_id') != SESSION or receipt.get('runtime_path') != TASK_PATH
            or receipt.get('sha256') != TASK_SHA or receipt.get('device') != DEVICE
            or receipt.get('inode') != INODE or receipt.get('directory_device') != DIR_DEVICE
            or receipt.get('directory_inode') != DIR_INODE
            or receipt.get('status') != 'STAGED_NOT_LOADED_OR_EXECUTED'
            or receipt.get('movement_commands') != 0 or rows[2].get('goal_id') != GOAL
            or rows[3].get('goal_id') != GOAL or
            not any(r.get('event') == 'accepted' and r.get('goal_id') == GOAL and
                    r.get('accepted') is True for r in rows) or
            rows[-2].get('event') != 'coordinator_failure' or
            rows[-2].get('reason') != 'RuntimeError: guard_lost_during_trial' or
            rows[-2].get('no_retry') is not True or
            rows[-1].get('event') != 'independent_cancel_unconfirmed'):
        raise ValueError('accepted_journal_receipt_mismatch')
    identities = tuple((item.st_dev,item.st_ino) for item in (mirror_info,lease_info,event_info))
    return marker, marker_info, sha(events_raw), identities


def validate_terminal_evidence(path):
    """Validate pinned historical status; never infer terminal from absence."""
    raw, _ = read_regular(Path(path))
    if sha(raw) != TERMINAL_EVIDENCE_SHA:
        raise ValueError('terminal_evidence_hash_mismatch')
    value = json.loads(raw)
    status = value['status']
    if status['returncode'] != 0 or status.get('stderr') != '':
        raise ValueError('terminal_observation_failed')
    out = status['stdout']
    lines = out.splitlines()
    if lines.count('status_list:') != 1 or lines.count('  status: 5') != 1:
        raise ValueError('terminal_status_not_exact')
    expected = [46,32,234,141,52,217,78,77,145,146,229,224,193,30,146,29]
    nums = [int(match.group(1)) for line in lines
            if (match := re.fullmatch(r'      - (\d+)', line))]
    if nums != expected or len(re.findall(r'^  status:', out, flags=re.M)) != 1:
        raise ValueError('terminal_uuid_not_exact')
    return {'goal_id':GOAL,'status':5,'evidence_sha256':TERMINAL_EVIDENCE_SHA,
            'historical_not_current':True,'physical_stop_verified':False}


def run_command(argv, *, data=None):
    proc = subprocess.run(argv, input=data, capture_output=True, timeout=15, check=False)
    if proc.returncode != 0:
        raise RuntimeError('readonly_or_archive_command_failed:' + argv[0])
    return proc.stdout


# Read-only graph checks for the ROS CLI daemon.  The command name alone is
# insufficient: daemonize.py can run an arbitrary deserialized callable.
_ROS_DAEMON_CHECK = r"""import glob,json,os,re,socket,xmlrpc.client
expected=['/usr/bin/python3','-c','from ros2cli.daemon.daemonize import main; main()',
          '--name','ros2-daemon','--ros-domain-id','0','--rmw-implementation','rmw_cyclonedds_cpp']
found=[]
for path in glob.glob('/proc/[0-9]*/cmdline'):
 try:
  raw=open(path,'rb').read().split(b'\0'); args=[x.decode() for x in raw if x]
  if args==expected:
   pid=int(path.split('/')[2]); sockets=[]
   for fd in glob.glob('/proc/'+str(pid)+'/fd/*'):
    try:
     target=os.readlink(fd)
     if re.fullmatch(r'socket:\[\d+\]',target): sockets.append(target[8:-1])
    except OSError: pass
   found.append((pid,sockets))
 except (OSError,UnicodeError): pass
if len(found)!=1: raise ValueError('daemon_identity_not_unique')
pid,sockets=found[0]
listeners=[]
for line in open('/proc/net/tcp').read().splitlines()[1:]:
 fields=line.split()
 if fields[1]=='0100007F:2CF7' and fields[3]=='0A': listeners.append(fields[9])
if len(listeners)!=1 or listeners[0] not in sockets: raise ValueError('daemon_rpc_socket_not_owned')
socket.setdefaulttimeout(3)
rpc=xmlrpc.client.ServerProxy('http://127.0.0.1:11511/ros2cli/')
methods=set(rpc.system.listMethods())
expected_methods={'count_publishers','count_subscribers','get_action_client_names_and_types_by_node',
'get_action_names_and_types','get_action_server_names_and_types_by_node','get_client_names_and_types_by_node',
'get_name','get_namespace','get_node_names_and_namespaces','get_node_names_and_namespaces_with_enclaves',
'get_publisher_names_and_types_by_node','get_publishers_info_by_topic','get_service_names_and_types',
'get_service_names_and_types_by_node','get_subscriber_names_and_types_by_node','get_subscriptions_info_by_topic',
'get_topic_names_and_types','system.listMethods','system.methodHelp','system.methodSignature','system.shutdown'}
if methods != expected_methods: raise ValueError('daemon_rpc_methods_unexpected')
name,namespace=rpc.get_name(),rpc.get_namespace()
if namespace!='/' or not re.fullmatch(r'_ros2cli_daemon_0_[0-9a-f]{32}',name): raise ValueError('daemon_node_invalid')
pubs=rpc.get_publisher_names_and_types_by_node(name,namespace)
clients=rpc.get_client_names_and_types_by_node(name,namespace)
actions=rpc.get_action_client_names_and_types_by_node(name,namespace)
if sorted(pubs)!=sorted([['/parameter_events',['rcl_interfaces/msg/ParameterEvent']],['/rosout',['rcl_interfaces/msg/Log']]]) or clients or actions:
 raise ValueError('daemon_node_controls_or_unexpected_publishers')
print(json.dumps({'pid':pid,'node':name,'rpc_socket_owned':True,'control_clients':0,
                  'action_clients':0,'publishers':['/parameter_events','/rosout'],
                  'limits':'point-in-time graph only; daemon payload is not authenticated'}))
"""


def no_observed_activity(run=run_command, *, allow_ros_daemon=False):
    names = run(['docker','ps','--format','{{.Names}}']).decode().splitlines()
    if names.count(APP) != 1 or names.count(ROS) != 1:
        raise RuntimeError('containers_not_unique')
    ros_python = 0
    for name in (APP, ROS):
        out = run(['docker','top',name,'-eo','pid,comm']).decode()
        rows = out.splitlines()
        if not rows or 'PID' not in rows[0]:
            raise ValueError('invalid_process_inventory')
        for row in rows[1:]:
            parts = row.split()
            if len(parts) != 2 or not parts[0].isdigit():
                raise ValueError('invalid_process_row')
            if parts[1].lower().startswith('python'):
                if name != ROS or not allow_ros_daemon:
                    raise RuntimeError('python_process_in_trial_container')
                ros_python += 1
    daemon = None
    if ros_python:
        if ros_python != 1:
            raise RuntimeError('multiple_ros_python_processes')
        raw = run(['docker','exec',ROS,'python3','-B','-c',_ROS_DAEMON_CHECK])
        daemon = json.loads(raw)
        if (not isinstance(daemon,dict) or daemon.get('rpc_socket_owned') is not True or
                daemon.get('control_clients') != 0 or daemon.get('action_clients') != 0 or
                daemon.get('publishers') != ['/parameter_events','/rosout']):
            raise ValueError('ros_daemon_identity_invalid')
    command = ('source /opt/ros/humble/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; '
               'timeout 7 ros2 topic echo --once --no-daemon /mc/manipulation/action/_action/status')
    status = run(['docker','exec',ROS,'bash','-lc',command]).decode()
    if not re.search(r'^status_list:', status, flags=re.M):
        raise ValueError('action_status_not_observed')
    states = [int(x) for x in re.findall(r'^\s+status:\s*(\d+)\s*$', status, flags=re.M)]
    if not states and not re.search(r'^status_list:\s*\[\]\s*$', status, flags=re.M):
        raise ValueError('action_status_unparseable')
    if any(x not in (4,5,6) for x in states):
        raise RuntimeError('active_or_unknown_action_status')
    return {'ros_cli_daemon':daemon,'observed_action_states':states,
            'does_not_establish_external_exclusivity_or_stop':True}


def container_task(mode, run=run_command):
    payload = {'root':TASK_ROOT,'name':TASK_NAME,'dev':DEVICE,'ino':INODE,
               'dir_dev':DIR_DEVICE,'dir_ino':DIR_INODE,'sha':TASK_SHA,'session':SESSION,'mode':mode}
    out = run(['docker','exec','-i',APP,'python3','-B','-c',CONTAINER_ARCHIVE],
              data=(json.dumps(payload)+'\n').encode())
    value = json.loads(out)
    expected = {'mode':mode,'task_sha256':TASK_SHA,'device':DEVICE,'inode':INODE,
                'archive_name':'.'+TASK_NAME+'.archived-'+SESSION}
    if value != expected:
        raise ValueError('task_archive_receipt_mismatch')
    return value


def recover(*, terminal_evidence, archive=False, control=CONTROL, lease_dir=LEASE_DIR,
            inspect=None, task=container_task):
    terminal = validate_terminal_evidence(terminal_evidence)
    if inspect is None:
        # Graph-verified ROS CLI daemon is tolerated for read-only check only;
        # archival retains the prior all-Python rejection.
        inspect = lambda: no_observed_activity(allow_ros_daemon=not archive)
    for root in (control, lease_dir):
        info = root.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise ValueError('private_control_directory_invalid')
    fd = os.open(control/'.trial.lock', os.O_RDWR | os.O_CLOEXEC | getattr(os,'O_NOFOLLOW',0))
    try:
        lock_info = os.fstat(fd)
        if (not stat.S_ISREG(lock_info.st_mode) or lock_info.st_uid != os.geteuid()
                or stat.S_IMODE(lock_info.st_mode) & 0o077):
            raise ValueError('trial_lock_invalid')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if any(re.fullmatch(r'RECOVERY-[0-9a-f]{32}-intent\.json', p.name)
               for p in control.iterdir()):
            raise RuntimeError('previous_recovery_requires_manual_review')
        marker, info, journal_hash, identities = validate_record(control, lease_dir)
        activity = inspect()
        check = task('check')
        if not archive:
            return {'status':'CHECKED_NO_CHANGES','terminal':terminal,'activity':activity,'task':check,
                    'movement_commands':0,'physical_stop_verified':False}
        intent_path = control/('RECOVERY-'+SESSION+'-intent.json')
        intent_sha = durable_new(intent_path, {'session_id':SESSION,'marker_sha256':sha(marker),
            'journal_sha256':journal_hash,'terminal':terminal,'task':check,'state':'before_xml_archive'})
        # The global unresolved marker remains at its original name until a
        # successful, independently re-read XML archive receipt is durable.
        archived = task('archive')
        archived_path = control/('RECOVERY-'+SESSION+'-xml-archived.json')
        durable_new(archived_path, {'session_id':SESSION,'intent_sha256':intent_sha,'task':archived})
        # Recheck journal, lease and all identities under the same lock after
        # the cross-filesystem operation; any change retains the marker/guard.
        final_activity = inspect()
        current, now_info, current_journal_hash, current_identities = validate_record(control,lease_dir)
        if (current != marker or (info.st_dev,info.st_ino)!=(now_info.st_dev,now_info.st_ino)
                or current_journal_hash != journal_hash or current_identities != identities):
            raise RuntimeError('record_changed_before_marker_archive')
        dest = control/('ARCHIVED-PENDING-'+SESSION+'.json')
        os.link(control/'PENDING_OR_UNRESOLVED.json',dest,follow_symlinks=False)
        before = os.stat(dest,follow_symlinks=False)
        again = os.stat(control/'PENDING_OR_UNRESOLVED.json',follow_symlinks=False)
        if (before.st_dev,before.st_ino)!=(info.st_dev,info.st_ino) or (again.st_dev,again.st_ino)!=(info.st_dev,info.st_ino):
            raise RuntimeError('marker_identity_changed_during_archive')
        dirfd = os.open(control,os.O_RDONLY|os.O_DIRECTORY)
        try:
            os.fsync(dirfd)
            os.unlink(control/'PENDING_OR_UNRESOLVED.json')
            try:
                os.fsync(dirfd)
            except OSError:
                # Best effort: an fsync error leaves durability uncertain.
                # Restore the marker from its exact archived inode when able.
                try:
                    os.link(dest,control/'PENDING_OR_UNRESOLVED.json',follow_symlinks=False)
                    os.fsync(dirfd)
                except OSError:
                    pass
                raise
        finally: os.close(dirfd)
        # A guard intent remains visible to every cooperating launcher until
        # the complete receipt, XML archive and archived marker are durable.
        complete_path = control/('RECOVERY-'+SESSION+'-complete.json')
        complete_sha = durable_new(complete_path, {'session_id':SESSION,
            'intent_sha256':intent_sha, 'marker_sha256':sha(marker),
            'task':archived, 'marker_archive':str(dest), 'state':'complete'})
        # Deliberately retain the incomplete-intent pathname permanently.
        # Every cooperating launcher treats it as a block until a separate,
        # reviewed recovery removes it. This utility never enables movement.
        retained, _ = read_regular(intent_path)
        if sha(retained) != intent_sha:
            raise RuntimeError('recovery_intent_changed_before_completion')
        return {'status':'ARCHIVED_WITH_RECOVERY_BLOCK_RETAINED','activity_before':activity,
                'activity_before_marker':final_activity,'task':archived,
                'marker_archive':str(dest),'complete_sha256':complete_sha,
                'movement_commands':0,'physical_stop_verified':False,
                'recovery_block_retained':str(intent_path),'model_control_qualified':False}
    finally:
        os.close(fd)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check',action='store_true')
    group.add_argument('--archive',action='store_true')
    parser.add_argument('--terminal-evidence', type=Path, required=True,
                        help='pinned prior status observation JSON for exact canceled UUID')
    args=parser.parse_args(argv)
    try:
        print(json.dumps(recover(archive=args.archive,terminal_evidence=args.terminal_evidence),ensure_ascii=False,allow_nan=False))
        return 0
    except (OSError,ValueError,KeyError,TypeError,RuntimeError,subprocess.SubprocessError) as exc:
        print('ARCHIVE_FAILED: '+str(exc),file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
