#!/usr/bin/env python3
"""Run on Vision: reversible, pinned patch of normal web mapping requests.

Does not send ROS commands, reload maps, restart services or initiate mapping.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

CONTAINER = 'walker-web.web-1'
ROOT = '/usr/share/nginx/html/main/static/js/async/'
ORIGINALS = {
    '1348.3578c594.js': '21fcdd17089da3caf9c403f515930086c83337c1c423055bd4bc61dbe9480490',
    '4370.173fbc6e.js': '701589ec445cf5c3279c0ef7f2c01c276851466072c47b08411e5d8236f42fb2',
}
BEFORE = b'mapping_mode:"normal"'
AFTER = b'mapping_mode:"normal",map_type:"fusion"'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def patch(data):
    if data.count(BEFORE) != 1 or AFTER in data:
        raise ValueError('Unexpected mapping request; refusing patch')
    return data.replace(BEFORE, AFTER, 1)


def read(name):
    return subprocess.check_output(['docker', 'exec', CONTAINER, 'cat', ROOT+name], timeout=5)


def write(name, data):
    # Preserve vendor permissions, then replace this one file atomically.
    command = 'set -eu; dst="$1"; tmp="${dst}.fusion-stage-$$"; trap \'rm -f "$tmp"\' EXIT; cp -p "$dst" "$tmp"; cat > "$tmp"; mv "$tmp" "$dst"'
    subprocess.run(['docker', 'exec', '-i', CONTAINER, 'sh', '-c', command, 'patch', ROOT+name],
                   input=data, check=True, timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['check', 'apply', 'restore'])
    parser.add_argument('--backup-dir', required=True, type=Path)
    args = parser.parse_args()
    current = {name: read(name) for name in ORIGINALS}
    manifest_path = args.backup_dir/'manifest.json'
    if args.mode == 'restore':
        manifest = json.loads(manifest_path.read_text())
        desired = {name: (args.backup_dir/'before'/name).read_bytes() for name in ORIGINALS}
        for name in ORIGINALS:
            if digest(desired[name]) != ORIGINALS[name] or digest(current[name]) != manifest['after'][name]:
                raise ValueError('Backup/current hash mismatch; refusing restore')
    else:
        for name, data in current.items():
            if digest(data) != ORIGINALS[name]:
                raise ValueError('Vendor hash mismatch: '+name+'; refusing patch')
        desired = {name: patch(data) for name, data in current.items()}
        if args.mode == 'check':
            print(json.dumps({'status': 'compatible', 'before': ORIGINALS,
                              'after': {name: digest(data) for name, data in desired.items()}}))
            return
        # Do not reuse or overwrite a backup from another intervention.
        if args.backup_dir.exists():
            raise ValueError('Backup directory exists; choose a new directory')
        (args.backup_dir/'before').mkdir(parents=True)
        (args.backup_dir/'after').mkdir()
        for name in ORIGINALS:
            (args.backup_dir/'before'/name).write_bytes(current[name])
            (args.backup_dir/'after'/name).write_bytes(desired[name])
        manifest_path.write_text(json.dumps({'before': ORIGINALS,
            'after': {name: digest(data) for name, data in desired.items()}}, indent=2)+'\n')
    changed = []
    try:
        for name in ORIGINALS:
            if read(name) != current[name]:
                raise ValueError('Asset changed during intervention: '+name)
            changed.append(name)
            write(name, desired[name])
            if read(name) != desired[name]:
                raise ValueError('Write verification failed: '+name)
    except Exception:
        # Restore only files still equal to our old/new data; preserve foreign changes.
        for name in reversed(changed):
            if read(name) in (current[name], desired[name]):
                write(name, current[name])
        raise
    print(json.dumps({'status': args.mode+' verified', 'hashes':
                      {name: digest(read(name)) for name in ORIGINALS},
                      'backup': str(args.backup_dir), 'robot_commands_sent': False}))


if __name__ == '__main__':
    main()
