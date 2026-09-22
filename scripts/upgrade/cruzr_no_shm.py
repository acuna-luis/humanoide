#!/usr/bin/env python3
"""Motion host: check/install/rollback ROSA no-SHM environment; NEVER restart.

Run through the normal authenticated SSH connection. Install requires a private
backup directory; copy it off the robot before activation. Container recreation
requires reviewing/reapplying this adaptation, like the internal HOME overlay.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

TARGETS = ('walker-motion.manipulation_robot_app-1', 'walker-motion.hw-1')
SETUP = '/opt/walker/setup.bash'
ORIGINAL_SHA = '238e522a314cd13d87d525336d670073c19abdbf4c5cccc0374ad4f4eef17d95'
BLOCK = ('\n# COMM-01-NO-SHM: reviewed Cruzr S2 v0.2.0; see project recipe.\n'
         'export ROSA_USE_SHM=OFF\n').encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def classify(data):
    if sha(data) == ORIGINAL_SHA:
        return 'original'
    if data.endswith(BLOCK) and sha(data[:-len(BLOCK)]) == ORIGINAL_SHA:
        return 'installed'
    raise ValueError('Unexpected setup.bash: review before changing it')


def transformed(data, rollback=False):
    state = classify(data)
    if rollback:
        return data[:-len(BLOCK)] if state == 'installed' else data
    return data+BLOCK if state == 'original' else data


# Atomic replacement preserves mode/ownership and checks the exact prior bytes.
# Receives data via stdin, never interpolates it into a shell command.
WRITER = '''import base64,hashlib,json,os,pathlib,stat,sys,tempfile
p=pathlib.Path(sys.argv[1]);v=json.load(sys.stdin)
if p.is_symlink():raise RuntimeError('Refuse symlink')
s=p.stat();old=p.read_bytes()
if hashlib.sha256(old).hexdigest()!=v['before']:raise RuntimeError('Concurrent change')
fd,name=tempfile.mkstemp(prefix='.comm-01-',dir=p.parent)
try:
 with os.fdopen(fd,'wb') as f:
  f.write(base64.b64decode(v['data']));f.flush();os.fsync(f.fileno())
 os.chmod(name,stat.S_IMODE(s.st_mode));os.chown(name,s.st_uid,s.st_gid)
 os.replace(name,p)
finally:
 if os.path.exists(name):os.unlink(name)
'''


def main():
    import base64
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--install', action='store_true')
    mode.add_argument('--rollback', action='store_true')
    parser.add_argument('--backup', type=Path, help='New private directory required for any write')
    args = parser.parse_args()
    if not args.check and args.backup is None:
        parser.error('--backup NEW_DIRECTORY required for mutation')
    inventory = []
    for name in TARGETS:
        info = json.loads(subprocess.check_output(['docker', 'inspect', name]))[0]
        env = dict(s.split('=', 1) for s in info['Config']['Env'] if '=' in s)
        if (not info['State']['Running'] or env.get('ROSA_MIDDLE_WARE') != 'cyclone'
                or not info['Config']['Image'].endswith(':zs2_motion-v0.2.0')):
            raise RuntimeError('Unexpected running image/middleware: '+name)
        before = subprocess.check_output(['docker', 'exec', name, 'cat', SETUP])
        state = classify(before)
        after = transformed(before, rollback=args.rollback)
        inventory.append((name, info, before, after, state))
    # Validate every target before creating backups or writing a target.
    if not args.check:
        args.backup.mkdir(mode=0o700, parents=False, exist_ok=False)
        for name, info, before, after, state in inventory:
            (args.backup/(name+'.setup.before')).write_bytes(before)
            (args.backup/(name+'.setup.after')).write_bytes(after)
            (args.backup/(name+'.inspect.json')).write_text(json.dumps(info, indent=2))
        (args.backup/'installer.py').write_bytes(Path(__file__).read_bytes())
    receipts = []
    try:
        for name, info, before, after, state in inventory:
            if not args.check and before != after:
                subprocess.run(['docker', 'exec', '--user', '0', '-i', name, 'python3', '-c', WRITER, SETUP],
                    input=json.dumps({'before':sha(before), 'data':base64.b64encode(after).decode()}).encode(),
                    check=True, timeout=10)
                actual = subprocess.check_output(['docker', 'exec', name, 'cat', SETUP])
                if actual != after:
                    raise RuntimeError('Post-write mismatch: '+name)
            receipts.append(dict(container=name, id=info['Id'], image=info['Config']['Image'],
                path=SETUP, before=sha(before), after=sha(before if args.check else after),
                installed_state=state if args.check else classify(after), restarted=False))
        print(json.dumps({'targets':receipts, 'running_processes_reloaded':False,
                          'movement_commands':0}, indent=2))
    finally:
        if not args.check:
            # A partial failure is deliberately visible and reversible by target.
            (args.backup/'receipt.json').write_text(json.dumps(receipts, indent=2)+'\n')
            entries = sorted(p for p in args.backup.iterdir() if p.is_file() and p.name != 'SHA256SUMS')
            (args.backup/'SHA256SUMS').write_text(''.join(sha(p.read_bytes())+'  '+p.name+'\n' for p in entries))


if __name__ == '__main__':
    main()
