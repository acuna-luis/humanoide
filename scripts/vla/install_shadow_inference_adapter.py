#!/usr/bin/env python3
"""Check/install only the inference-only evidence adapter on Vision.

No container startup, reload, ROS or movement. Installation requires the
expected previous hash and a stopped inference container; retains a backup.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collect_estop_available_readonly import execute


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--check', action='store_true')
    modes.add_argument('--install', action='store_true')
    parser.add_argument('--expected-sha256')
    args = parser.parse_args()
    if args.install and not re.fullmatch(r'[0-9a-f]{64}', args.expected_sha256 or ''):
        parser.error('--install requires --expected-sha256 of the existing remote file')
    source = Path(__file__).with_name('runtime') / 'cruzr_s2_inference_shadow.py'
    data = source.read_bytes()
    payload = dict(install=args.install, expected=args.expected_sha256,
                   sha256=hashlib.sha256(data).hexdigest(), data=base64.b64encode(data).decode())
    code = '''
import base64,datetime,hashlib,json,os,pathlib,shutil,subprocess,tempfile
p = pathlib.Path('/home/walker/cruzr-vla/additional/safe-runtime/cruzr_s2_inference_shadow.py')
cfg = json.loads(PAYLOAD)
old = p.read_bytes()
old_sha = hashlib.sha256(old).hexdigest()
state = subprocess.check_output(['docker','inspect','--format','{{.State.Status}}','cruzr-vla-inference'],text=True).strip()
print('INFERENCE_CONTAINER='+state)
print('REMOTE_SHA256='+old_sha)
print('LOCAL_SHA256='+cfg['sha256'])
if not cfg['install']:
    raise SystemExit(0 if old_sha == cfg['sha256'] else 1)
if state not in ('exited','created'):
    raise SystemExit('Inference container must be stopped; nothing installed')
if old_sha != cfg['expected']:
    raise SystemExit('Previous hash changed; nothing installed')
data = base64.b64decode(cfg['data'],validate=True)
if hashlib.sha256(data).hexdigest() != cfg['sha256']:
    raise SystemExit('Payload checksum mismatch')
backup = p.with_name(p.name+'.backup-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
with backup.open('xb') as f:
    f.write(old)
shutil.copystat(p,backup)
fd,temporary = tempfile.mkstemp(prefix='.'+p.name+'.',dir=p.parent)
try:
    with os.fdopen(fd,'wb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    shutil.copystat(p,temporary)
    os.replace(temporary,p)
finally:
    if os.path.exists(temporary): os.unlink(temporary)
print('BACKUP='+str(backup))
print('INSTALLED_SHA256='+hashlib.sha256(p.read_bytes()).hexdigest())
'''.replace('PAYLOAD', repr(json.dumps(payload)))
    result = execute('vision', ['python3', '-c', code])
    print(result.get('stdout', ''), end='')
    print(result.get('stderr', ''), end='', file=sys.stderr)
    if 'error' in result:
        print(result['error'], file=sys.stderr)
    return result.get('returncode', 1)


if __name__ == '__main__':
    raise SystemExit(main())
