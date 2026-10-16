#!/usr/bin/env python3
"""Restore reviewed Motion clamp environment, without reloading any process.

Accept the two individually reviewed original/SPS states; preserve unrelated
bytes. Vision CC has its own install_pico_v4_cc_env.py --rollback recipe.
"""
import argparse
import base64
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.collect_estop_available_readonly import execute

REMOTE = r'''
import base64, hashlib, json, os, pathlib, stat, sys, tempfile
ns={'__name__':'profile_library'}
exec(base64.b64decode(sys.argv[1]),ns)
mode=sys.argv[2]
s=pathlib.Path('/home/walker/.local/share/cruzr-pico-v4-migration-20261015')
a=[(s/'compose.before.yml').read_bytes(),(s/'db.before.json').read_bytes()]
b=[(s/'compose.candidate.yml').read_bytes(),(s/'db.candidate.json').read_bytes()]
assert tuple(b)==ns['prepare'](*a),'Invalid original/candidate relationship'
paths=[pathlib.Path('/home/walker/.config/udoke/walker/compose.yml'),pathlib.Path('/home/walker/.config/udoke/db.json')]
current=[p.read_bytes() for p in paths]
assert current[0] in (a[0],b[0]),'Unreviewed compose drift'
assert json.loads(current[1]) in (json.loads(a[1]),json.loads(b[1])),'Unreviewed database drift'
# uDoke rewrote JSON formatting but kept the original clamp values. Preserve it.
desired_files=[a[0],current[1] if json.loads(current[1])==json.loads(a[1]) else a[1]]
backup=pathlib.Path('/home/walker/.local/share/cruzr-return-clamp-20261015')
if mode=='install':
 backup.mkdir(mode=0o700,parents=True,exist_ok=True)
 for p,v in zip(paths,current):
  f=backup/(p.name+'.before')
  if f.exists():assert f.read_bytes()==v,'Backup differs; use explicit recovery'
  else:
   with f.open('xb') as stream:stream.write(v)
   f.chmod(0o600)
 assert [p.read_bytes() for p in paths]==current,'Changed during preparation'
 for p,v,desired in zip(paths,current,desired_files):
  if v==desired:continue
  m=p.stat();assert m.st_uid==os.getuid(),'Unexpected owner'
  fd,tmp=tempfile.mkstemp(prefix='.return-clamp-',dir=p.parent)
  try:
   with os.fdopen(fd,'wb') as stream:stream.write(desired);stream.flush();os.fsync(stream.fileno())
   os.chmod(tmp,stat.S_IMODE(m.st_mode));os.replace(tmp,p)
  finally:
   if os.path.exists(tmp):os.unlink(tmp)
 assert [p.read_bytes() for p in paths]==desired_files,'Result differs'
print(json.dumps({'mode':mode,'reloaded':False,'backup':str(backup),'files':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'clamp_configuration':paths[0].read_bytes()==a[0] and json.loads(paths[1].read_bytes())==json.loads(a[1])}))
'''

def main():
    p=argparse.ArgumentParser(description=__doc__)
    g=p.add_mutually_exclusive_group()
    g.add_argument('--check',action='store_true')
    g.add_argument('--install',action='store_true')
    p.add_argument('--evidence',type=Path,required=True)
    a=p.parse_args();mode='install' if a.install else 'check'
    output=a.evidence/('restore-clamp-'+mode+'.json')
    if output.exists():p.error('Receipt exists; preserve prior evidence')
    helper=base64.b64encode(Path(__file__).with_name('prepare_pico_v4_motion_env.py').read_bytes()).decode()
    r=execute('motion',['python3','-c',REMOTE,helper,mode])
    output.write_text(json.dumps(r,indent=2));print(json.dumps(r))
    return r.get('returncode',1)

if __name__=='__main__':
    raise SystemExit(main())
