#!/usr/bin/env python3
"""Stage reviewed writable files and SPS env on Motion, without stopping it.

Requires saved docker-diff JSON from the same intervention. Archives remain
private on Motion until copied and verified externally. No activation.
"""
import argparse
import base64
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.collect_estop_available_readonly import execute

STAGE = '/home/walker/.local/share/cruzr-pico-v4-migration-20261015'


def selected_paths(diff):
    result = []
    for line in diff.splitlines():
        if not line.startswith(('A ', 'C ')):
            continue
        path = line[2:]
        if '__pycache__' in path or '/site-packages/' in path:
            continue
        if path.startswith('/opt/walker/') and Path(path).suffix in ('.yaml', '.xml', '.json', '.bash', '.py', '.sh'):
            result.append(path)
        elif path.endswith('.motion') and (path.count('/') == 1 or path.startswith('/tmp/')):
            result.append(path)
    return sorted(set(result))


REMOTE = r'''
import base64, hashlib, json, pathlib, subprocess, sys
stage = pathlib.Path(sys.argv[1])
slot = sys.argv[2]
container = sys.argv[3]
paths = json.loads(base64.b64decode(sys.argv[4]))
stage.mkdir(mode=0o700, parents=True, exist_ok=True)
archive = stage / (slot + '.tar')
code = """
import pathlib, sys, json, tarfile
paths=json.loads(sys.argv[1])
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as tar:
 for p in paths:
  path=pathlib.Path(p)
  if path.is_file() or path.is_symlink():
   tar.add(path,arcname=str(path).lstrip('/'),recursive=False)
"""
with archive.open('xb') as f:
    subprocess.run(['docker','exec',container,'python3','-c',code,json.dumps(paths)],
                   stdout=f,check=True,timeout=60)
print(json.dumps(dict(archive=str(archive), bytes=archive.stat().st_size,
                     sha256=hashlib.sha256(archive.read_bytes()).hexdigest())))
'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence', type=Path, required=True)
    p.add_argument('--env-only', action='store_true', help='Stage SPS compose/db candidates only')
    p.add_argument('--extras-only', action='store_true', help='Stage reviewed other-motion-diffs.json')
    args = p.parse_args()
    if args.env_only:
        helper = base64.b64encode(Path(__file__).with_name('prepare_pico_v4_motion_env.py').read_bytes()).decode()
        code = r'''
import base64, hashlib, json, pathlib, sys
namespace = {'__name__':'profile_library'}
exec(base64.b64decode(sys.argv[1]), namespace)
stage = pathlib.Path(sys.argv[2])
stage.mkdir(mode=0o700, parents=True, exist_ok=True)
base = pathlib.Path('/home/walker/.config/udoke')
compose = (base/'walker/compose.yml').read_bytes()
database = (base/'db.json').read_bytes()
new_compose, new_database = namespace['prepare'](compose, database)
data = {'compose.before.yml':compose,'db.before.json':database,
        'compose.candidate.yml':new_compose,'db.candidate.json':new_database}
for name, value in data.items():
    path = stage/name
    if path.exists() and path.read_bytes() != value:
        raise RuntimeError('Existing stage differs: '+name)
    if not path.exists():
        with path.open('xb') as f: f.write(value)
    path.chmod(0o600)
print(json.dumps({name:hashlib.sha256(value).hexdigest() for name,value in data.items()}))
'''
        result = execute('motion', ['python3', '-c', code, helper, STAGE])
        (args.evidence/'env-stage-receipt.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(result))
        return result.get('returncode', 1)
    if args.extras_only:
        extra = json.loads((args.evidence/'other-motion-diffs.json').read_text())
        targets = [(name.removeprefix('walker-motion.').removesuffix('-1'), name, diff)
                   for name, diff in extra.items()]
    else:
        targets = []
        for slot, container in [('hw', 'walker-motion.hw-1'),
                                ('app', 'walker-motion.manipulation_robot_app-1')]:
            diff = json.loads((args.evidence / (slot + '-diff-before.json')).read_text())
            if diff.get('returncode') != 0:
                raise ValueError('Incomplete diff: ' + slot)
            targets.append((slot, container, diff['stdout']))
    for slot, container, diff in targets:
        paths = selected_paths(diff)
        (args.evidence / (slot + '-selected-paths.json')).write_text(json.dumps(paths, indent=2))
        if not paths:
            continue
        result = execute('motion', ['python3', '-c', REMOTE, STAGE, slot, container,
                                   base64.b64encode(json.dumps(paths).encode()).decode()])
        (args.evidence / (slot + '-stage-receipt.json')).write_text(json.dumps(result, indent=2))
        print(slot, json.dumps(result))
        if result.get('returncode') != 0:
            return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
