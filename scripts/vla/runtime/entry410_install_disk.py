"""Add only the ten reviewed ENTRY410 task files; never load or execute them."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import time


def sha(data): return hashlib.sha256(data).hexdigest()


def verify_package(package):
    files = package['files']
    expected = {f'entry410_stage_{i:02d}_{d}.xml' for i in range(1, 6) for d in ('forward', 'reverse')}
    if set(files) != expected: raise ValueError('Unexpected file set')
    for name, value in files.items():
        data = base64.b64decode(value['base64'], validate=True)
        if sha(data) != value['sha256']: raise ValueError('Package file hash mismatch')
    return files


def plan(root, package):
    files = verify_package(package); registry = root/'task_list.yaml'
    if (root/'s2_bio_vla').is_symlink(): raise ValueError('Task directory symlink')
    if registry.is_symlink() or not registry.is_file(): raise ValueError('Registry missing or symlink')
    before = registry.read_bytes(); text = before.decode('utf-8')
    if sha(before) != package['expected_registry_sha256']: raise ValueError('Registry changed since planning')
    # Only append novel keys; never parse/re-serialize or rewrite existing YAML.
    for name in files:
        key = name[:-4]
        if re.search(r'(?m)^\s*[\'\"]?'+re.escape(key)+r'[\'\"]?\s*:', text):
            raise ValueError('Task key already exists: '+key)
        if (root/'s2_bio_vla'/name).exists() or (root/'s2_bio_vla'/name).is_symlink():
            raise ValueError('Destination exists: '+name)
    fragment = ''.join('\n'+name[:-4]+':\n  motion_id: "s2_bio_vla/'+name[:-4]+'"\n  json_args: \'{"Reverse": false,"TimeRatio": 1.0}\'\n  cmd: "start"\n'
                       for name in sorted(files))
    after = before+(b'' if before.endswith(b'\n') else b'\n')+fragment.encode()
    return before, after


def install(root, package, backup_root):
    # Caller must hold the operation lock and verify active E-stop beforehand.
    before, after = plan(root, package)
    backup = backup_root/('entry410-'+str(time.time_ns())); backup.mkdir(parents=True)
    registry = root/'task_list.yaml'; info = registry.stat()
    shutil.copy2(registry, backup/'task_list.yaml')
    (backup/'package.json').write_text(json.dumps(package, indent=2)+'\n')
    created = []; replaced = False
    temp = None
    try:
        directory = root/'s2_bio_vla'
        if directory.is_symlink(): raise ValueError('Task directory symlink')
        directory.mkdir(exist_ok=True)
        for name, value in package['files'].items():
            dest = directory/name
            with dest.open('xb') as stream:
                created.append(dest)
                stream.write(base64.b64decode(value['base64'], validate=True)); stream.flush(); os.fsync(stream.fileno())
            os.chmod(dest, 0o644)
            os.chown(dest, info.st_uid, info.st_gid)
        if registry.read_bytes() != before: raise RuntimeError('Concurrent registry change')
        fd, name = tempfile.mkstemp(prefix='.entry410-registry-', dir=root); temp = Path(name)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(after); stream.flush(); os.fsync(stream.fileno())
        os.chmod(temp, info.st_mode & 0o7777); os.chown(temp, info.st_uid, info.st_gid)
        if registry.read_bytes() != before: raise RuntimeError('Concurrent registry change')
        os.replace(temp, registry); replaced = True; temp = None
        if registry.read_bytes() != after: raise RuntimeError('Registry verification failed')
        for name, value in package['files'].items():
            if sha((directory/name).read_bytes()) != value['sha256']: raise RuntimeError('Installed file mismatch')
        result = dict(status='INSTALLED_ON_DISK_NOT_LOADED', backup=str(backup),
                      registry_before_sha256=sha(before), registry_after_sha256=sha(after),
                      installed_files={str(directory/n):v['sha256'] for n, v in package['files'].items()},
                      reloaded=False, motion_command_sent=False)
        (backup/'result.json').write_text(json.dumps(result, indent=2)+'\n'); return result
    except BaseException:
        # Do not overwrite an unrelated concurrent registry mutation.
        can_remove = not replaced or registry.read_bytes() == after
        if replaced and can_remove:
            fd, name = tempfile.mkstemp(prefix='.entry410-rollback-', dir=root)
            with os.fdopen(fd, 'wb') as stream: stream.write(before); stream.flush(); os.fsync(stream.fileno())
            os.chmod(name, info.st_mode & 0o7777); os.chown(name, info.st_uid, info.st_gid)
            os.replace(name, registry)
        if can_remove:
            for dest in created: dest.unlink(missing_ok=True)
        (backup/'failed.json').write_text(json.dumps(dict(rollback_possible=can_remove, manual_review_required=True))+'\n')
        raise
    finally:
        if temp is not None: temp.unlink(missing_ok=True)


if __name__ == '__main__':
    import fcntl
    import sys
    package = json.loads(base64.b64decode(sys.argv[1], validate=True))
    root = Path('/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config')
    if sys.argv[2] == 'plan':
        before, after = plan(root, package)
        print(json.dumps(dict(status='DISK_PLAN_ONLY', registry_before_sha256=sha(before), registry_after_sha256=sha(after))))
    elif sys.argv[2] == 'install':
        lock = Path('/tmp/entry410-install.lock').open('a'); fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        print(json.dumps(install(root, package, Path('/var/tmp/cruzr-entry410-backups'))))
    else: raise ValueError('Unknown mode')
