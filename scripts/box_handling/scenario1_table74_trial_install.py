#!/usr/bin/env python3
"""Install/check/remove immutable trial phase files; never dispatch robot actions.

The local CLI defaults to check. Remote Python receives source modules and the
request through stdin, not shell arguments. No ROS, restart or mode operations
exist here. An installed approach or support phase is not an autorun task.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

try:
    from . import scenario1_deposit_install as files
    from . import scenario1_table74_trial as trial
    from . import scenario1_table74_support as support
except ImportError:
    import scenario1_deposit_install as files
    import scenario1_table74_trial as trial
    import scenario1_table74_support as support


EVIDENCE_ROOT = Path('/var/tmp/cruzr-table74-trial')
LOCK_PATH = Path('/tmp/cruzr-front-sps.lock')
WRITE_SOURCE = files.WRITE_SOURCE
READ_SOURCE = '''import hashlib,json,os,pathlib,stat,sys
q=json.loads(sys.stdin.read());out={'dependencies':{},'targets':{}}
def read(path,optional=False):
 p=pathlib.Path(path)
 if not p.is_absolute() or any(x.is_symlink() for x in (p,*p.parents)):
  raise RuntimeError('Read path is not absolute or contains a symlink')
 try:fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
 except FileNotFoundError:
  if optional:return None
  raise
 with os.fdopen(fd,'rb') as f:
  if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):raise RuntimeError('Not a regular file')
  data=f.read(33554433)
  if len(data)>33554432:raise RuntimeError('Read file exceeds bound')
 return data
for p in q['dependencies']:
 data=read(p);item={'sha256':hashlib.sha256(data).hexdigest()}
 if p in q['text_sources']:item['text']=data.decode('utf-8')
 out['dependencies'][p]=item
for p in q['targets']:
 data=read(p,True)
 out['targets'][p]=None if data is None else hashlib.sha256(data).hexdigest()
print(json.dumps(out))
'''

REMOVE_SOURCE = '''import hashlib,json,os,pathlib,stat,sys
q=json.loads(sys.stdin.read());opened=[];removed=[]
try:
 for path,expected in q['targets'].items():
  p=pathlib.Path(path)
  if any(x.is_symlink() for x in (p,*p.parents)):raise RuntimeError('Rollback path is a symlink')
  if not p.exists():continue
  directory=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
  try:
   fd=os.open(p.name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=directory)
   with os.fdopen(fd,'rb') as f:
    info=os.fstat(f.fileno())
    if not stat.S_ISREG(info.st_mode):raise RuntimeError('Rollback target is not regular')
    if hashlib.sha256(f.read()).hexdigest()!=expected:raise RuntimeError('Rollback checksum changed')
   opened.append((path,p.name,directory,info.st_dev,info.st_ino))
  except BaseException:
   os.close(directory);raise
 for path,name,directory,dev,ino in opened:
  current=os.stat(name,dir_fd=directory,follow_symlinks=False)
  if not stat.S_ISREG(current.st_mode) or (current.st_dev,current.st_ino)!=(dev,ino):
   raise RuntimeError('Rollback target changed during verification')
  os.unlink(name,dir_fd=directory);os.fsync(directory);removed.append(path)
 print(json.dumps({'removed':removed}))
finally:
 for _,_,directory,_,_ in opened:os.close(directory)
'''


def _builder(bundle):
    """Select only versioned trusted builders; bundle data never names code."""
    if not isinstance(bundle, dict) or not isinstance(bundle.get('manifest'), dict):
        raise ValueError('Invalid trial phase manifest')
    phase = bundle['manifest'].get('phase')
    if phase == 'approach_only':
        return trial
    if phase == 'support_only':
        return support
    raise ValueError('Unknown trial phase; only approach_only/support_only are supported')


def _validate(bundle):
    checked = _builder(bundle).validate_bundle(bundle)
    return checked['manifest']['id'], {p: files.sha(t) for p, t in checked['tasks'].items()}


def _no_links(path):
    path = Path(path)
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise RuntimeError('Evidence/lock path contains a symlink')


def read_live(run, container, bundle):
    """Verify original bytes, binary pin, rebuilt bundle and every destination."""
    _, hashes = _validate(bundle)
    builder = _builder(bundle)
    sources = [builder.SOURCE_XML_PATH, builder.SOURCE_YAML_PATH]
    raw = run(['docker', 'exec', '-i', container, 'python3', '-c', READ_SOURCE],
              data=json.dumps(dict(dependencies=list(builder.DEPENDENCIES),
                                   text_sources=sources, targets=list(hashes))))
    result = files.object_json(raw)
    if set(result) != {'dependencies', 'targets'} or set(result['dependencies']) != set(builder.DEPENDENCIES):
        raise RuntimeError('Incomplete live dependency inventory')
    for path, expected in builder.DEPENDENCIES.items():
        entry = result['dependencies'][path]
        expected_keys = {'sha256', 'text'} if path in sources else {'sha256'}
        if not isinstance(entry, dict) or set(entry) != expected_keys or entry['sha256'] != expected:
            raise RuntimeError('Original dependency changed: '+path)
        if path in sources and (type(entry['text']) is not str or files.sha(entry['text']) != expected):
            raise RuntimeError('Live source text/checksum mismatch: '+path)
    rebuilt = builder.build_bundle(bundle['review']['reference'],
        result['dependencies'][sources[0]]['text'], result['dependencies'][sources[1]]['text'])
    if files.compact(rebuilt) != files.compact(bundle):
        raise RuntimeError('Bundle differs from the live-source reconstruction')
    observed = result['targets']
    if not isinstance(observed, dict) or set(observed) != set(hashes):
        raise RuntimeError('Incomplete destination inventory')
    if any(observed[p] not in (None, expected) for p, expected in hashes.items()):
        raise RuntimeError('Destination conflict; refusing overwrite/remove')
    return result


def _same_container(run, expected):
    if files.discover_motion(files.inventory(run)) != expected:
        raise RuntimeError('Container changed during trial file operation')


def _receipt(path, bundle, container, identity, hashes):
    _no_links(path)
    value = files.object_json(path.read_text())
    expected = dict(id=bundle['manifest']['id'], bundle_sha256=files.sha(files.canonical(bundle)),
                    container=container, container_identity=identity, task_hashes=hashes,
                    original_dependencies=_builder(bundle).DEPENDENCIES,
                    phase=bundle['manifest']['phase'])
    if any(value.get(k) != v for k, v in expected.items()):
        raise RuntimeError('Existing receipt identity/container/hash mismatch')
    if value.get('status') not in ('installing', 'installed', 'installation_failed',
                                   'rolling_back', 'rollback_failed', 'rolled_back'):
        raise RuntimeError('Invalid existing receipt status')
    before = value.get('before')
    if not isinstance(before, dict) or set(before) != set(hashes) or any(
            before[p] not in (None, hashes[p]) for p in hashes):
        raise RuntimeError('Invalid original destination record')
    for key in ('created_files', 'unconfirmed_created_files', 'attempted_files'):
        paths = value.get(key)
        if not isinstance(paths, list) or len(paths) != len(set(paths)) or any(p not in hashes for p in paths):
            raise RuntimeError('Invalid receipt destination list')
    owned = set(value['created_files']) | set(value['unconfirmed_created_files'])
    if any(before[p] is not None or p not in value['attempted_files'] for p in owned):
        raise RuntimeError('Receipt claims files that were not absent before installation')
    return value


def _lock(path):
    _no_links(path)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    stream = os.fdopen(fd, 'a')
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise RuntimeError('Trial file-operation lock is not regular')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return stream
    except BaseException:
        stream.close()
        raise


def operate(bundle, *, operation='check', run=files.command,
            evidence_root=EVIDENCE_ROOT, lock_path=LOCK_PATH):
    if operation not in ('check', 'install', 'rollback'):
        raise ValueError('Unknown trial file operation')
    package_id, hashes = _validate(bundle)
    builder, phase = _builder(bundle), bundle['manifest']['phase']
    with _lock(lock_path):
        container, identity = files.discover_motion(files.inventory(run))
        expected_container = (container, identity)
        observed = read_live(run, container, bundle)
        _same_container(run, expected_container)
        if operation == 'check':
            return dict(status='checked', id=package_id, phase=phase,
                        container=container, container_identity=identity,
                        observed=observed['targets'], dependencies=builder.DEPENDENCIES,
                        movement_commands=0, restarts=0,
                        installed=all(observed['targets'][p] == digest for p, digest in hashes.items()))
        root, package = Path(evidence_root), Path(evidence_root)/package_id
        for path in (root, package):
            _no_links(path)
        receipt_path = package/'install-receipt.json'
        _no_links(receipt_path)
        previous = _receipt(receipt_path, bundle, container, identity, hashes) if receipt_path.exists() else None
        for name, value in (('bundle.json', bundle), ('manifest.json', bundle['manifest']),
                            ('originals.json', observed['dependencies'])):
            path = package/name
            _no_links(path)
            if path.exists() and path.read_text() != files.canonical(value):
                raise RuntimeError('Immutable evidence conflict before file operation')
        if operation == 'rollback':
            if previous is None:
                raise RuntimeError('Rollback requires an existing installation receipt')
            receipt = previous
            eligible = set(receipt['created_files']) | set(receipt['unconfirmed_created_files'])
            # All targets and dependencies have been verified before the first deletion.
            removal = {p: hashes[p] for p in sorted(eligible, key=lambda p: (not p.endswith('.xml'), p))}
            receipt.update(status='rolling_back', rollback_attempted_files=list(removal))
            files.write_json(receipt_path, receipt)
            try:
                _same_container(run, expected_container)
                result = files.object_json(run(['docker', 'exec', '-i', container, 'python3', '-c', REMOVE_SOURCE],
                                               data=json.dumps({'targets': removal})))
                if set(result) != {'removed'} or not isinstance(result['removed'], list) or any(p not in removal for p in result['removed']):
                    raise RuntimeError('Invalid rollback removal receipt')
                after = read_live(run, container, bundle)
                if any(after['targets'][p] is not None for p in removal):
                    raise RuntimeError('Rollback target still exists')
                _same_container(run, expected_container)
                receipt.update(status='rolled_back', removed_files=sorted(set(receipt.get('removed_files', [])) | set(result['removed'])))
                files.write_json(receipt_path, receipt)
                return receipt
            except BaseException as error:
                receipt.update(status='rollback_failed', error=type(error).__name__+': '+str(error))
                files.write_json(receipt_path, receipt)
                raise
        package.mkdir(parents=True, exist_ok=True)
        for name, value in (('bundle.json', bundle), ('manifest.json', bundle['manifest']),
                            ('originals.json', observed['dependencies'])):
            files.write_json(package/name, value, immutable=True)
        receipt = previous or dict(version=1, id=package_id, task_name=bundle['task_name'],
            phase=phase, bundle_sha256=files.sha(files.canonical(bundle)),
            manifest_sha256=files.sha(files.canonical(bundle['manifest'])), container=container,
            container_identity=identity, package=str(package), before=observed['targets'],
            task_hashes=hashes, original_dependencies=builder.DEPENDENCIES,
            created_files=[], unconfirmed_created_files=[], attempted_files=[],
            originals_overwritten=False, movement_commands=0, restarts=0,
            loaded='not_verified', physical_validation='pending')
        receipt.update(status='installing', error=None)
        files.write_json(receipt_path, receipt)
        try:
            for path in sorted(hashes, key=lambda p: (not p.endswith('.yaml'), p)):
                _same_container(run, expected_container)
                read_live(run, container, bundle)
                if path not in receipt['attempted_files']:
                    receipt['attempted_files'].append(path)
                if receipt['before'][path] is None and path not in receipt['created_files']:
                    if path not in receipt['unconfirmed_created_files']:
                        receipt['unconfirmed_created_files'].append(path)
                files.write_json(receipt_path, receipt)  # Durable uncertainty BEFORE dispatch.
                result = files.object_json(run(['docker', 'exec', '-i', container, 'python3', '-c', WRITE_SOURCE, path],
                                               data=bundle['tasks'][path]))
                if set(result) != {'created', 'sha256'} or type(result['created']) is not bool or result['sha256'] != hashes[path]:
                    raise RuntimeError('Installed file receipt/hash mismatch')
                if result['created']:
                    if receipt['before'][path] is not None:
                        raise RuntimeError('Previously existing target disappeared during installation')
                    if path not in receipt['created_files']:
                        receipt['created_files'].append(path)
                if path in receipt['unconfirmed_created_files']:
                    # A previous lost response remains ownership evidence when exact bytes exist.
                    if not result['created'] and path not in receipt['created_files']:
                        receipt['created_files'].append(path)
                    receipt['unconfirmed_created_files'].remove(path)
                files.write_json(receipt_path, receipt)
            after = read_live(run, container, bundle)
            if any(after['targets'][p] != expected for p, expected in hashes.items()):
                raise RuntimeError('Installed task missing at verification')
            _same_container(run, expected_container)
            receipt.update(status='installed', rollback_remove_only_if_sha256_matches={
                p: hashes[p] for p in receipt['created_files']})
            files.write_json(receipt_path, receipt)
            return receipt
        except BaseException as error:
            receipt.update(status='installation_failed', error=type(error).__name__+': '+str(error),
                rollback_remove_only_if_sha256_matches={p: hashes[p] for p in
                    set(receipt['created_files']) | set(receipt['unconfirmed_created_files'])})
            files.write_json(receipt_path, receipt)
            raise


def install_bundle(bundle, **kwargs):
    return operate(bundle, operation='install', **kwargs)


def rollback_bundle(bundle, **kwargs):
    return operate(bundle, operation='rollback', **kwargs)


def remote_source(request=None):
    """Embed reviewed modules, including discovery's source, without repo imports."""
    directory = Path(__file__).parent
    names = ('scenario1_deposit', 'scenario1_deposit_install',
             'scenario1_table74_trial', 'scenario1_table74_support',
             'scenario1_table74_trial_install')
    sources = {name: (directory/(name+'.py')).read_text() for name in names}
    checks = (directory/'scenario1_checks.py').read_text()
    code = 'import sys,types,json\n_sources='+repr(sources)+'\n_checks='+repr(checks)+'\n'
    code += ('for _name,_source in _sources.items():\n'
             ' _module=types.ModuleType(_name);sys.modules[_name]=_module\n'
             ' if _name=="scenario1_deposit_install":_module._CHECKS_SOURCE=_checks\n'
             ' exec(compile(_source,_name+"_in_memory","exec"),_module.__dict__)\n')
    if request is not None:
        code += ('_request='+repr(request)+'\n'
                 'try:\n'
                 ' _result=sys.modules["scenario1_table74_trial_install"].operate(**_request)\n'
                 ' print(json.dumps(_result,allow_nan=False),flush=True)\n'
                 'except Exception as _error:\n'
                 ' print(json.dumps({"status":"file_operation_failed","error":str(_error),"movement_commands":0,"restarts":0}),flush=True)\n'
                 ' raise SystemExit(78)\n')
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--check', action='store_true')
    group.add_argument('--install', action='store_true')
    group.add_argument('--rollback', action='store_true')
    parser.add_argument('--bundle', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.bundle.stat().st_size > 2*1024*1024:
            raise ValueError('Trial bundle too large')
        bundle = files.object_json(args.bundle.read_text())
        _validate(bundle)
        root = Path(__file__).resolve().parents[2]
        env = dict(os.environ, CRUZR_INTERNAL_ASKPASS='1',
            SSH_ASKPASS=str(root/'scripts/cruzr_recover_to_home.sh'), SSH_ASKPASS_REQUIRE='force',
            DISPLAY=os.environ.get('DISPLAY', ':0'))
        command = ['setsid', '-w', 'ssh', '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=5',
                   '-o', 'PreferredAuthentications=password', '-o', 'PubkeyAuthentication=no',
                   '-o', 'NumberOfPasswordPrompts=1', 'walker@192.168.11.2', 'python3 -']
        operation = 'rollback' if args.rollback else 'install' if args.install else 'check'
        result = subprocess.run(command, input=remote_source(dict(bundle=bundle, operation=operation)),
                                env=env, text=True, capture_output=True, timeout=180)
        sys.stdout.write(result.stdout)
        if result.returncode:
            sys.stderr.write(result.stderr[-1600:])
        return result.returncode
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(json.dumps(dict(status='file_operation_failed', error=str(error), movement_commands=0)), flush=True)
        return 78


if __name__ == '__main__':
    raise SystemExit(main())
