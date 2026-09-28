#!/usr/bin/env python3
"""Additive deposit-task installer: files only, no ROS commands or restart.

The CLI sends remote_source() to the Motion host with a reviewed bundle on
stdin. The source includes the current pure container-discovery contract, so
the remote host needs only Python's standard library and Docker.
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
import tempfile
import xml.etree.ElementTree as ET


TASK_ROOT = '/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/'
META_ROOT = '/opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config/meta_clamp/'
NAMESPACE = 'local_scenario1_deposit/'
BUILDER_VERSION = 2
DEPENDENCIES = {
    TASK_ROOT+'wrc_cruzr/put_cruzr_wrc_low.xml': '579b862962e0ee07a423c92517c29b5ecad80b4929961aac2fae6a0240fa0f78',
    META_ROOT+'wrc/put_cruzr_wrc_low.yaml': '8aeb0a24a3149c7676f481219299ec85bb872d6b17ad93605a6e461776909ff5',
    META_ROOT+'wrc/open_arm_cruzr.yaml': 'c41bd1d88379c2012ee44639142fb5b55c1d58decd6a75851c8e17763778e37b',
}


def sha(value):
    return hashlib.sha256(value.encode('utf-8') if isinstance(value, str) else value).hexdigest()


def object_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON field')
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=pairs)
    if not isinstance(value, dict):
        raise ValueError('Expected JSON object')
    json.dumps(value, allow_nan=False)
    return value


def canonical(value):
    return json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n'


def compact(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def validate_bundle(bundle):
    if not isinstance(bundle, dict) or set(bundle) != {'task_name', 'tasks', 'dependencies', 'manifest', 'review'}:
        raise ValueError('Invalid deposit bundle fields')
    manifest = bundle['manifest']
    fields = {'version', 'id', 'task_name', 'config_sha256', 'dependencies', 'robot_files', 'physical_validation'}
    if not isinstance(manifest, dict) or set(manifest) != fields or type(manifest['version']) is not int or manifest['version'] != 1:
        raise ValueError('Invalid deposit manifest')
    identity = manifest['id']
    if not isinstance(identity, str) or not re.fullmatch('[0-9a-f]{64}', identity):
        raise ValueError('Invalid immutable package identity')
    config_sha = manifest['config_sha256']
    if not isinstance(config_sha, str) or not re.fullmatch('[0-9a-f]{64}', config_sha):
        raise ValueError('Invalid profile checksum')
    task_name = NAMESPACE+identity
    if bundle['task_name'] != task_name or manifest['task_name'] != task_name:
        raise ValueError('Task name does not match immutable package identity')
    if manifest['physical_validation'] != 'pending':
        raise ValueError('Installer cannot certify physical validation')
    if not isinstance(bundle['review'], dict) or bundle['review'].get('ready') is not True:
        raise ValueError('Deposit geometry review is not ready')
    review = bundle['review']
    if (not isinstance(review.get('config'), dict) or review.get('missing') != []
            or review.get('physical_validation') != 'pending'):
        raise ValueError('Incomplete deposit review record')
    if sha(compact(review['config'])) != config_sha or sha(compact({
            'builder_version': BUILDER_VERSION, 'config': review['config'],
            'dependencies': DEPENDENCIES})) != identity:
        raise ValueError('Manifest identity does not match the reviewed configuration')
    if bundle['dependencies'] != DEPENDENCIES or manifest['dependencies'] != DEPENDENCIES:
        raise ValueError('Unreviewed deposit dependencies')
    tasks = bundle['tasks']
    expected = {META_ROOT+task_name+'.yaml', TASK_ROOT+task_name+'.xml'}
    if not isinstance(tasks, dict) or set(tasks) != expected:
        raise ValueError('Task paths must be the two immutable deposit destinations')
    for value in tasks.values():
        if not isinstance(value, str) or not value or len(value.encode('utf-8')) > 262144:
            raise ValueError('Invalid or oversized task content')
    hashes = {path: sha(value) for path, value in tasks.items()}
    if manifest['robot_files'] != dict(DEPENDENCIES, **hashes):
        raise ValueError('Manifest does not match exact task contents')
    tree = ET.fromstring(tasks[TASK_ROOT+task_name+'.xml'])
    structure = [(item.tag, item.attrib) for item in tree.iter()]
    if structure != [('root', {'main_tree_to_execute': 'MainTree'}),
                     ('BehaviorTree', {'ID': 'MainTree'}),
                     ('Sequence', {'name': 'root_sequence'}),
                     ('Action', {'ID': 'MetaClamp', 'name': task_name}),
                     ('Action', {'ID': 'MetaClamp', 'name': 'wrc/open_arm_cruzr'})]:
        raise ValueError('Deposit XML does not preserve the reviewed two-action sequence')
    canonical(bundle)  # Also rejects nonfinite values in review metadata.
    return identity, hashes


def discovery_source():
    # Present only when running this module in the versioned PC workspace.
    return (Path(__file__).with_name('scenario1_checks.py')).read_text()


def remote_source():
    return '_CHECKS_SOURCE = '+repr(discovery_source())+'\n'+Path(__file__).read_text()


build_remote_source = remote_source


def discover_motion(inventory):
    source = globals().get('_CHECKS_SOURCE')
    if source is None:
        source = discovery_source()
    scope = {}
    exec(compile(source, 'scenario1_checks_in_memory', 'exec'), scope)
    names = scope['discover_containers'](inventory)
    native = names['native']
    rows = [row for row in inventory if row['Name'].lstrip('/') == native]
    if len(rows) != 1 or rows[0]['Config'].get('Labels', {}).get('com.docker.compose.service') not in (
            'motion.manipulation_robot_app', 'manipulation_robot_app'):
        raise ValueError('Deposit installation requires an exact Motion Compose service label')
    row = rows[0]
    identity = {key: row.get(key) for key in ('Id', 'Image')}
    identity['started_at'] = row['State'].get('StartedAt')
    if not all(isinstance(value, str) and value for value in identity.values()):
        raise ValueError('Incomplete container identity')
    return native, identity


READ_SOURCE = '''import hashlib,json,pathlib,sys
request=json.loads(sys.stdin.read());result={}
for path in request['dependencies']:
 result[path]=hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
for path in request['targets']:
 p=pathlib.Path(path)
 if p.is_symlink() or p.parent.is_symlink():raise RuntimeError('Deposit destination is a symlink')
 if p.exists():
  if not p.is_file():raise RuntimeError('Deposit destination is not a regular file')
  result[path]=hashlib.sha256(p.read_bytes()).hexdigest()
 else:result[path]=None
print(json.dumps(result))
'''


WRITE_SOURCE = '''import hashlib,json,os,pathlib,sys,uuid
p=pathlib.Path(sys.argv[1]);data=sys.stdin.buffer.read()
p.parent.mkdir(exist_ok=True)
directory=os.open(str(p.parent),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
temporary='.'+p.name+'.'+uuid.uuid4().hex
created=False
def existing():
 fd=os.open(p.name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=directory)
 with os.fdopen(fd,'rb') as stream:return stream.read()
try:
 fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644,dir_fd=directory)
 with os.fdopen(fd,'wb') as stream:
  stream.write(data);stream.flush();os.fsync(stream.fileno())
 try:
  os.link(temporary,p.name,src_dir_fd=directory,dst_dir_fd=directory,follow_symlinks=False)
  created=True
 except FileExistsError:
  if existing()!=data:raise RuntimeError('Destination conflict; refusing overwrite')
 if existing()!=data:raise RuntimeError('Installed content mismatch')
 os.fsync(directory)
 print(json.dumps({'created':created,'sha256':hashlib.sha256(data).hexdigest()}))
finally:
 try:os.unlink(temporary,dir_fd=directory)
 except FileNotFoundError:pass
 os.close(directory)
'''


def command(args, *, data=None, timeout=20):
    result = subprocess.run(args, input=data, text=True, capture_output=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError('Deposit file operation failed (rc='+str(result.returncode)+'): '+result.stderr[-800:])
    return result.stdout


def inventory(run):
    ids = run(['docker', 'ps', '-q']).split()
    if not ids:
        raise RuntimeError('No running containers')
    return json.loads(run(['docker', 'inspect', *ids]))


def read_files(run, container, tasks):
    raw = run(['docker', 'exec', '-i', container, 'python3', '-c', READ_SOURCE],
              data=json.dumps({'dependencies': list(DEPENDENCIES), 'targets': list(tasks)}))
    result = object_json(raw)
    if set(result) != set(DEPENDENCIES) | set(tasks):
        raise RuntimeError('Incomplete dependency/destination inventory')
    for path, expected in DEPENDENCIES.items():
        if result[path] != expected:
            raise RuntimeError('Original dependency changed: '+path)
    for path, expected in tasks.items():
        if result[path] not in (None, expected):
            raise RuntimeError('Destination conflict; refusing overwrite: '+path)
    return result


def write_json(path, value, *, immutable=False):
    text = canonical(value)
    if path.is_symlink():
        raise RuntimeError('Evidence destination is a symlink')
    if immutable:
        try:
            with path.open('x') as stream:
                stream.write(text); stream.flush(); os.fsync(stream.fileno())
        except FileExistsError:
            if path.read_text() != text:
                raise RuntimeError('Immutable evidence conflict')
    else:
        with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            try:
                stream.write(text); stream.flush(); os.fsync(stream.fileno())
                temporary.replace(path)
            finally:
                temporary.unlink(missing_ok=True)
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def install_bundle(bundle, *, run=command,
                   evidence_root=Path('/var/tmp/cruzr-scenario1-deposit'),
                   lock_path=Path('/tmp/cruzr-front-sps.lock')):
    identity, tasks = validate_bundle(bundle)
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'a') as lock:
        if not stat.S_ISREG(os.fstat(lock.fileno()).st_mode):
            raise RuntimeError('Installation lock is not a regular file')
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        container, container_identity = discover_motion(inventory(run))
        before = read_files(run, container, tasks)
        root = Path(evidence_root)
        package = root/identity
        if root.is_symlink() or package.is_symlink():
            raise RuntimeError('Evidence package directory is a symlink')
        for name, value in (('bundle.json', bundle), ('manifest.json', bundle['manifest'])):
            path = package/name
            if path.is_symlink() or path.exists() and path.read_text() != canonical(value):
                raise RuntimeError('Immutable evidence conflict before installation')
        receipt_path = package/'install-receipt.json'
        created = set()
        if receipt_path.is_symlink():
            raise RuntimeError('Receipt destination is a symlink')
        if receipt_path.exists():
            old = object_json(receipt_path.read_text())
            if old.get('id') != identity or old.get('manifest_sha256') != sha(canonical(bundle['manifest'])):
                raise RuntimeError('Existing receipt identity mismatch')
            prior_created = old.get('created_files')
            if not isinstance(prior_created, list) or not all(isinstance(p, str) and p in tasks for p in prior_created):
                raise RuntimeError('Invalid existing receipt destinations')
            created.update(prior_created)
        if discover_motion(inventory(run)) != (container, container_identity):
            raise RuntimeError('Container changed before installation')
        # All originals/destinations are checked before creating task/evidence files.
        package.mkdir(parents=True, exist_ok=True)
        write_json(package/'bundle.json', bundle, immutable=True)
        write_json(package/'manifest.json', bundle['manifest'], immutable=True)
        receipt = dict(id=identity, task_name=bundle['task_name'], container=container,
                       container_identity=container_identity, status='installing',
                       manifest_sha256=sha(canonical(bundle['manifest'])),
                       package=str(package), created_files=sorted(created),
                       task_hashes=tasks, original_dependencies=DEPENDENCIES,
                       originals_overwritten=False, movement_commands=0, restarts=0,
                       loaded='not_verified', physical_validation='pending',
                       before={path: before[path] for path in tasks}, attempted_files=[])
        write_json(receipt_path, receipt)
        try:
            for path in sorted(tasks, key=lambda value: (not value.endswith('.yaml'), value)):
                receipt['attempted_files'].append(path)
                write_json(receipt_path, receipt)  # Durable intent, including a lost writer response.
                result = object_json(run(['docker', 'exec', '-i', container, 'python3', '-c', WRITE_SOURCE, path],
                                         data=bundle['tasks'][path]))
                if set(result) != {'created', 'sha256'} or type(result['created']) is not bool or result['sha256'] != tasks[path]:
                    raise RuntimeError('Installed file receipt/hash mismatch')
                if result['created']:
                    created.add(path)
                receipt['created_files'] = sorted(created)
                write_json(receipt_path, receipt)
            observed = read_files(run, container, tasks)
            if any(observed[path] != expected for path, expected in tasks.items()):
                raise RuntimeError('Installed task missing at verification')
            if discover_motion(inventory(run)) != (container, container_identity):
                raise RuntimeError('Container changed during installation')
            receipt['status'] = 'installed'
            receipt['rollback_remove_only_if_sha256_matches'] = {path: tasks[path] for path in sorted(created)}
            write_json(receipt_path, receipt)
            return receipt
        except BaseException as error:
            receipt['status'] = 'installation_failed'
            receipt['error'] = type(error).__name__+': '+str(error)
            receipt['created_files'] = sorted(created)
            uncertain = {path for path in receipt['attempted_files'] if before[path] is None} - created
            receipt['unconfirmed_created_files'] = sorted(uncertain)
            receipt['rollback_remove_only_if_sha256_matches'] = {
                path: tasks[path] for path in sorted(created | uncertain)}
            write_json(receipt_path, receipt)
            raise


def main(argv=None):
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    try:
        raw = sys.stdin.read(2*1024*1024+1)
        if len(raw) > 2*1024*1024:
            raise ValueError('Deposit bundle too large')
        receipt = install_bundle(object_json(raw))
        print(json.dumps(receipt, allow_nan=False), flush=True)
        return 0
    except Exception as error:
        print(json.dumps({'status': 'installation_failed', 'error': str(error),
                          'movement_commands': 0, 'restarts': 0}), flush=True)
        return 78


if __name__ == '__main__':
    raise SystemExit(main())
