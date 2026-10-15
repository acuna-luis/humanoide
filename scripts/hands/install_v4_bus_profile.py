#!/usr/bin/env python3
"""Install the inspected ENI correction while control waits; never reload it.

Run from the repository root. Default --check is read-only. --install backs up
the original in Motion and atomically changes only the inspected ENI file.
"""
import argparse
import base64
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.collect_estop_available_readonly import execute

REMOTE = r'''
import base64, hashlib, json, os, pathlib, stat, sys, tempfile, datetime
namespace = {'__name__': 'profile_library'}
exec(base64.b64decode(sys.argv[1]), namespace)
install = sys.argv[2] == 'install'
target = pathlib.Path('/opt/walker/ubt_ethercat_master/bin/eni_cruzr_kw_unified_noimu.xml')
data = target.read_bytes()
if hashlib.sha256(data).hexdigest() == '678c7d6bae1608709400383d85c6e0e5edae7032b365d11977cb56bc984250e8':
    print(json.dumps(dict(installed=True, changed=False, reload_requested=False,
                          target=str(target), sha256=hashlib.sha256(data).hexdigest())))
    sys.exit(0)
fixed = namespace['prepare'](data)
cmdline = pathlib.Path('/proc/1/cmdline').read_bytes().split(b'\0')
if b'wait' not in cmdline or not any(b'rosa_control_node' in x for x in cmdline):
    raise RuntimeError('Hardware container is not waiting for control startup')
report = dict(installed=False, reloaded=False, target=str(target),
              before_sha256=hashlib.sha256(data).hexdigest(),
              after_sha256=hashlib.sha256(fixed).hexdigest())
if install:
    backup = pathlib.Path('/etc/walker/customizations/hands-v4-bus-20261015')
    backup.mkdir(parents=True, exist_ok=True)
    original = backup / (target.name + '.before')
    if original.exists():
        if original.read_bytes() != data:
            raise RuntimeError('Backup already exists with different contents')
    else:
        with original.open('xb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
    metadata = target.stat()
    fd, name = tempfile.mkstemp(prefix='.v4-bus-', dir=target.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(fixed)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(name, stat.S_IMODE(metadata.st_mode))
        os.chown(name, metadata.st_uid, metadata.st_gid)
        if target.read_bytes() != data:
            raise RuntimeError('Source changed before installation')
        os.replace(name, target)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    if target.read_bytes() != fixed:
        raise RuntimeError('Post-installation verification failed')
    report.update(installed=True, backup=str(original),
                  utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    (backup / 'receipt.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    group = p.add_mutually_exclusive_group()
    group.add_argument('--check', action='store_true')
    group.add_argument('--install', action='store_true')
    p.add_argument('--evidence', type=Path, required=True)
    args = p.parse_args()
    source = Path(__file__).with_name('prepare_v4_bus_profile.py').read_bytes()
    command = ['docker', 'exec', 'walker-motion.hw-1', 'python3', '-c', REMOTE,
               base64.b64encode(source).decode(), 'install' if args.install else 'check']
    result = execute('motion', command)
    args.evidence.mkdir(parents=True, exist_ok=True)
    (args.evidence / ('install.json' if args.install else 'install-check.json')).write_text(
        json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False))
    return result.get('returncode', 1)


if __name__ == '__main__':
    raise SystemExit(main())
