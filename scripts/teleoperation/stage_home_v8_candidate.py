#!/usr/bin/env python3
"""Stage a separate v8 XML for review. Never replaces HOME, reloads or moves."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
from collect_estop_available_readonly import execute
from review_home_v8_early_roll import CANDIDATE, check_structure

CONTAINER = 'walker-motion.manipulation_robot_app-1'
BASE_SHA = '1e6e2fb7ddc598dc3793d093c283c82063507df0e53b70a18e161cab883a6f03'
META_SHA = 'bfeab1c7a295b58cd96fddd20916fc3f7fe16bd8c8ad1e77720f48aad34ccc69'
REMOTE = r'''
from pathlib import Path
import hashlib,json,os,tempfile,datetime
payload=PAYLOAD
root=Path('/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/cruzr')
base=root/'home.xml'
meta=Path('/opt/walker/manipulation_meta_tasks/lib/libmeta_move.so')
sha=lambda b:hashlib.sha256(b).hexdigest()
if sha(base.read_bytes())!=payload['base_sha'] or sha(meta.read_bytes())!=payload['meta_sha']:
 raise SystemExit('HOME/MetaMove changed; abort')
target=root/'home_v8_early_roll_CANDIDATE.xml'
data=payload['xml'].encode()
if target.exists() and target.read_bytes()!=data:raise SystemExit('Conflicting candidate; abort')
backup=Path('/etc/walker/trajectory-overlays')/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'_home_v8_candidate')
backup.mkdir(parents=True,exist_ok=False)
(backup/'home.v7.before.xml').write_bytes(base.read_bytes())
if target.exists():(backup/'candidate.before.xml').write_bytes(target.read_bytes())
else:
 fd,tmp=tempfile.mkstemp(prefix='.v8-candidate-',dir=root)
 try:
  with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
  os.chmod(tmp,0o644)
  os.link(tmp,target) # no overwrite even if another process creates the target
 finally:os.unlink(tmp)
if target.read_bytes()!=data or sha(base.read_bytes())!=payload['base_sha']:raise SystemExit('Postcheck failed')
receipt={'target':str(target),'sha256':sha(data),'backup':str(backup),'home_unchanged':True,
 'loaded':False,'physically_tested':False,'movement_commands':0,'restarts':0}
(backup/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--install-candidate',action='store_true')
    p.add_argument('--evidence',required=True,type=Path)
    a=p.parse_args()
    check_structure()
    if not a.install_candidate:
        print('LOCAL_STRUCTURE_OK; no robot access; nominal duration13.45s')
        return
    a.evidence.mkdir(parents=True,exist_ok=True)
    inventory=execute('motion',['docker','ps','--format','{{.Names}}'])
    (a.evidence/'install-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
    if inventory.get('returncode')!=0 or CONTAINER not in inventory.get('stdout','').splitlines():
        raise SystemExit('Motion container unavailable')
    before=execute('motion',['docker','exec',CONTAINER,'cat',
        '/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/cruzr/home.xml'])
    if before.get('returncode')!=0 or hashlib.sha256(before['stdout'].encode()).hexdigest()!=BASE_SHA:
        raise SystemExit('Unexpected baseline')
    (a.evidence/'remote-home.v7.before.xml').write_text(before['stdout'])
    payload={'base_sha':BASE_SHA,'meta_sha':META_SHA,'xml':CANDIDATE.read_text()}
    source=REMOTE.replace('PAYLOAD',repr(payload),1)
    result=execute('motion',['docker','exec',CONTAINER,'python3','-c',source])
    (a.evidence/'install-result.json').write_text(json.dumps(result,indent=2)+'\n')
    if result.get('returncode')!=0:raise SystemExit('Candidate installation failed: '+result.get('stderr','unknown'))
    print(result['stdout'])


if __name__=='__main__':
    main()
