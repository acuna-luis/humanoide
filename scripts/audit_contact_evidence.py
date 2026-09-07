#!/usr/bin/env python3
"""Preserve historical contact logs by read-only SSH, without ROS or Docker calls.

Writes exclusively into a new local evidence directory. No remote files,
services, permissions, modes or robot commands are changed.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
REMOTE = r'''
import glob, hashlib, io, json, os, sys, tarfile
dates = ('20260825', '20260826', '20260827', '20260828', '20260903', '20260904')
prefixes = ('robot_app.', 'rosa_control_node.', 'cc_main.', 'ecat_err_handler_service.')
paths = sorted(p for p in glob.glob('/etc/walker/log/*/*')
               if os.path.isfile(p) and not os.path.islink(p)
               and os.path.basename(p).startswith(prefixes)
               and any(d in os.path.basename(p) for d in dates))
manifest = []
with tarfile.open(fileobj=sys.stdout.buffer, mode='w|gz') as archive:
    for p in paths:
        if os.path.getsize(p) > 100_000_000:
            raise RuntimeError('Historical log exceeds bounded read: ' + p)
        with open(p, 'rb') as f:
            data = f.read()
        entry = tarfile.TarInfo(p.lstrip('/'))
        entry.size = len(data)
        archive.addfile(entry, io.BytesIO(data))
        manifest.append(dict(path=p, bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
    data = json.dumps(manifest, indent=2).encode()
    entry = tarfile.TarInfo('remote-manifest.json')
    entry.size = len(data)
    archive.addfile(entry, io.BytesIO(data))
'''

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-parent', type=Path,
                        default=ROOT.parent / 'Humanoide-vla-evidence')
    args = parser.parse_args()
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run = args.output_parent / (stamp + '_CONTACT-AUDIT')
    run.mkdir(parents=True, exist_ok=False)
    print(f'EVIDENCE_DIR={run}', flush=True)
    env = dict(os.environ, CRUZR_INTERNAL_ASKPASS='1',
               SSH_ASKPASS=str(ROOT / 'scripts/cruzr_recover_to_home.sh'),
               SSH_ASKPASS_REQUIRE='force', DISPLAY=os.environ.get('DISPLAY', ':0'))
    summary = {}
    for name, ip in (('motion', '192.168.11.2'), ('vision', '192.168.11.3')):
        archive = run / (name + '.tar.gz')
        command = ['setsid', '-w', 'ssh', '-o', 'ConnectTimeout=5',
                   '-o', 'PreferredAuthentications=password', '-o', 'PubkeyAuthentication=no',
                   '-o', 'NumberOfPasswordPrompts=1', f'walker@{ip}', 'python3 -']
        with archive.open('xb') as out:
            result = subprocess.run(command, input=REMOTE.encode(), stdout=out,
                                    stderr=subprocess.PIPE, env=env, timeout=180)
        (run / (name + '-ssh.stderr')).write_bytes(result.stderr)
        if result.returncode:
            raise RuntimeError(f'{name}: SSH failed; incomplete evidence retained')
        dest = run / name
        dest.mkdir()
        with tarfile.open(archive) as bundle:
            for member in bundle:
                path = Path(member.name)
                if not member.isfile() or path.is_absolute() or '..' in path.parts:
                    raise RuntimeError('Unexpected archive member')
                target = dest / path
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as out:
                    out.write(bundle.extractfile(member).read())
        manifest = json.loads((dest / 'remote-manifest.json').read_text())
        for entry in manifest:
            local = dest / entry['path'].lstrip('/')
            assert hashlib.sha256(local.read_bytes()).hexdigest() == entry['sha256']
        summary[name] = dict(files=len(manifest), bytes=sum(e['bytes'] for e in manifest))
        print(f'{name}: {len(manifest)} files preserved and hash-verified', flush=True)
    (run / 'collection.json').write_text(json.dumps(dict(
        collected_at_utc=stamp, remote_mutations=0, ros_calls=0, movement_commands=0,
        historical_logs_only=True, sources=summary), indent=2) + '\n')
    (run / 'collector.py').write_bytes(Path(__file__).read_bytes())
    with (run / 'evidence.sha256').open('x') as out:
        for path in sorted(run.rglob('*')):
            if path.is_file() and path.name != 'evidence.sha256':
                out.write(f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(run)}\n')

if __name__ == '__main__':
    main()
