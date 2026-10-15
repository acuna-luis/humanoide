#!/usr/bin/env python3
"""Copy an existing private backup directory off the robot; no control commands."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.collect_estop_available_readonly import ROOT, HOSTS


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--host', required=True, choices=HOSTS)
    p.add_argument('--source', required=True)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    source = Path(args.source)
    if not source.is_absolute() or not source.name.startswith('preupgrade-v0.2.0-'):
        raise ValueError('Expected an absolute preupgrade backup directory')
    partial = Path(str(args.output) + '.part')
    if args.output.exists() or partial.exists():
        raise ValueError('Destination exists; no overwrite')
    env = dict(os.environ, CRUZR_INTERNAL_ASKPASS='1',
        SSH_ASKPASS=str(ROOT/'scripts/cruzr_recover_to_home.sh'), SSH_ASKPASS_REQUIRE='force',
        DISPLAY=os.environ.get('DISPLAY', ':0'))
    prefix = ['setsid','-w','ssh','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=5',
        '-o','PreferredAuthentications=password','-o','PubkeyAuthentication=no',
        '-o','NumberOfPasswordPrompts=1','walker@'+HOSTS[args.host]]
    command = ['python3', '-c', '''import pathlib,subprocess,sys
p=pathlib.Path(sys.argv[1])
if (p/'STATUS').read_text().strip()!='CAPTURED_REVIEW_COVERAGE' or not (p/'SHA256SUMS').is_file():
 raise RuntimeError('Remote backup is not complete')
subprocess.run(['tar','-C',str(p.parent),'-cf','-',p.name],check=True)
''', str(source)]
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    with partial.open('xb') as f:
        partial.chmod(0o600)
        result = subprocess.run(prefix+[shlex.join(command)], env=env, stdout=f,
                                stderr=subprocess.PIPE, timeout=900)
    if result.returncode:
        raise RuntimeError('Backup transfer failed: '+result.stderr.decode(errors='replace'))
    partial.rename(args.output)
    digest = hashlib.sha256()
    with args.output.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            digest.update(block)
    receipt = dict(started=started,source=str(source),host=args.host,
                   bytes=args.output.stat().st_size,sha256=digest.hexdigest())
    args.output.with_suffix('.copy.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
