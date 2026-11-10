#!/usr/bin/env python3
"""Archive only the known pre-UUID failed wrist attempt; never command motion.

Run on the Motion host with its normal user. ``--check`` is read-only apart
from locking the existing lock file. ``--archive`` first records durable
intent, archives the exact XML in its existing container filesystem, records
the result and only then archives the unresolved marker. A durable recovery
intent blocks cooperating launchers until a completion receipt is durable.
The two filesystems cannot be updated atomically. A marker fsync error triggers
best-effort restoration and may leave its presence or durability uncertain.
Never run this during another controller session.

The lock excludes only cooperating wrist launchers.  Checking processes and
last action status cannot establish exclusivity against external clients or
prove physical stopping.  The user must establish current physical conditions.
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

SESSION = 'ccfbd5afa50744649c4d9982601013ae'
TASK_SHA = 'd4c704e6ab369d250658a596cd6a5704258accf130971d3046748a8d132b616b'
TASK_ROOT = '/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/diagnostics'
TASK_NAME = 'pico_v4_wrist_d4c704e6ab369d25.xml'
TASK_PATH = TASK_ROOT + '/' + TASK_NAME
DEVICE, INODE, DIR_DEVICE, DIR_INODE = 45, 3584590, 45, 3584589
CONTROL = Path('/var/tmp/cruzr-pico-v4-wrist-control')
LEASE_DIR = Path('/tmp/pico-wrist-live-3k5e3w2k')
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
    rows = [json.loads(line) for line in events_raw.splitlines()]
    if len(rows) != 3 or [r.get('event') for r in rows] != ['BRIDGE_READY','stage_receipt','coordinator_failure']:
        raise ValueError('journal_not_expected_pre_uuid_failure')
    receipt = rows[1].get('receipt', {})
    if (rows[1].get('session_id') != SESSION or receipt.get('runtime_path') != TASK_PATH
            or receipt.get('sha256') != TASK_SHA or receipt.get('device') != DEVICE
            or receipt.get('inode') != INODE or receipt.get('directory_device') != DIR_DEVICE
            or receipt.get('directory_inode') != DIR_INODE
            or receipt.get('status') != 'STAGED_NOT_LOADED_OR_EXECUTED'
            or receipt.get('movement_commands') != 0 or rows[2].get('no_retry') is not True
            or not str(rows[2].get('reason','')).startswith('JSONDecodeError:')):
        raise ValueError('journal_receipt_mismatch')
    identities = tuple((item.st_dev,item.st_ino) for item in (mirror_info,lease_info,event_info))
    return marker, marker_info, sha(events_raw), identities


def run_command(argv, *, data=None):
    proc = subprocess.run(argv, input=data, capture_output=True, timeout=15, check=False)
    if proc.returncode != 0:
        raise RuntimeError('readonly_or_archive_command_failed:' + argv[0])
    return proc.stdout


def no_observed_activity(run=run_command):
    names = run(['docker','ps','--format','{{.Names}}']).decode().splitlines()
    if names.count(APP) != 1 or names.count(ROS) != 1:
        raise RuntimeError('containers_not_unique')
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
                raise RuntimeError('python_process_in_trial_container')
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
    return {'no_python_in_trial_containers':True,'observed_action_states':states,
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


def recover(*, archive=False, control=CONTROL, lease_dir=LEASE_DIR,
            inspect=no_observed_activity, task=container_task):
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
            return {'status':'CHECKED_NO_CHANGES','activity':activity,'task':check,
                    'movement_commands':0,'physical_stop_verified':False}
        intent_path = control/('RECOVERY-'+SESSION+'-intent.json')
        intent_sha = durable_new(intent_path, {'session_id':SESSION,'marker_sha256':sha(marker),
            'journal_sha256':journal_hash,'task':check,'state':'before_xml_archive'})
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
        retained, retained_info = read_regular(intent_path)
        if sha(retained) != intent_sha:
            raise RuntimeError('recovery_intent_changed_before_completion')
        old_intent = control/('RECOVERY-'+SESSION+'-intent-archived.json')
        os.link(intent_path,old_intent,follow_symlinks=False)
        pinned = os.stat(old_intent,follow_symlinks=False)
        current = os.stat(intent_path,follow_symlinks=False)
        expected = (retained_info.st_dev,retained_info.st_ino)
        if (pinned.st_dev,pinned.st_ino) != expected or (current.st_dev,current.st_ino) != expected:
            raise RuntimeError('recovery_intent_identity_changed')
        dirfd = os.open(control,os.O_RDONLY|os.O_DIRECTORY)
        try:
            os.fsync(dirfd)
            os.unlink(intent_path)
            os.fsync(dirfd)
        finally: os.close(dirfd)
        return {'status':'ARCHIVED_ONE_FAILED_STAGE','activity_before':activity,
                'activity_before_marker':final_activity,'task':archived,
                'marker_archive':str(dest),'complete_sha256':complete_sha,
                'movement_commands':0,'physical_stop_verified':False}
    finally:
        os.close(fd)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check',action='store_true')
    group.add_argument('--archive',action='store_true')
    args=parser.parse_args(argv)
    try:
        print(json.dumps(recover(archive=args.archive),ensure_ascii=False,allow_nan=False))
        return 0
    except (OSError,ValueError,KeyError,TypeError,RuntimeError,subprocess.SubprocessError) as exc:
        print('ARCHIVE_FAILED: '+str(exc),file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
