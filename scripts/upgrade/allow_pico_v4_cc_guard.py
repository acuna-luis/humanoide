#!/usr/bin/env python3
"""Add the verified SPS identifier to CC readiness guard; preserve all other bytes.

The live voice adapter is retained. Requires CC stopped for installation.
No start/restart, E-stop release or control commands are issued.
"""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from scripts.collect_estop_available_readonly import execute

REMOTE=r'''
import hashlib,json,os,pathlib,stat,subprocess,sys,tempfile
mode=sys.argv[1]
target=pathlib.Path('/etc/walker/boot/cruzr_cc_start_when_ready.py')
stage=pathlib.Path('/etc/walker/boot/backups/pico-v4-20261015')
sha='ff9e119846c89ecc8ed3a3682c6d513abd4956cd2dff1af24da3ef932092184a'
old=b"if os.environ.get('HW_TYPE') != 'cruzr_s2_v1':"
new=b"if os.environ.get('HW_TYPE') not in ('cruzr_s2_v1', 'cruzr_s2_v1_sps'):"
current=target.read_bytes()
if hashlib.sha256(current).hexdigest()==sha:
 original=current
else:
 original=(stage/'guard.before.py').read_bytes()
 if hashlib.sha256(original).hexdigest()!=sha:raise RuntimeError('Original guard differs')
if original.count(old)!=1:raise RuntimeError('Expected one hardware predicate')
candidate=original.replace(old,new)
compile(candidate,str(target),'exec')
if current not in (original,candidate):raise RuntimeError('Unreviewed guard drift')
if mode!='check':
 running=subprocess.check_output(['docker','inspect','--format','{{.State.Running}}','walker-system.control_center-1'],text=True).strip()
 if running!='false':raise RuntimeError('Stop CC before updating its guard')
 stage.mkdir(mode=0o700,parents=True,exist_ok=True)
 backup=stage/'guard.before.py'
 if not backup.exists():backup.write_bytes(original);backup.chmod(0o600)
 if backup.read_bytes()!=original:raise RuntimeError('Backup mismatch')
 desired=original if mode=='rollback' else candidate
 if current!=desired:
  metadata=target.stat();fd,tmp=tempfile.mkstemp(prefix='.sps-guard-',dir=target.parent)
  try:
   with os.fdopen(fd,'wb') as f:f.write(desired);f.flush();os.fsync(f.fileno())
   os.chmod(tmp,stat.S_IMODE(metadata.st_mode));os.chown(tmp,metadata.st_uid,metadata.st_gid)
   if target.read_bytes()!=current:raise RuntimeError('Guard changed during preparation')
   os.replace(tmp,target)
  finally:
   if os.path.exists(tmp):os.unlink(tmp)
print(json.dumps(dict(mode=mode,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),sps_allowed=target.read_bytes()==candidate,voice_adapter_preserved=True,reloaded=False)))
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    group=p.add_mutually_exclusive_group()
    group.add_argument('--install',action='store_true')
    group.add_argument('--rollback',action='store_true')
    group.add_argument('--check',action='store_true')
    p.add_argument('--evidence',type=Path,required=True)
    args=p.parse_args();mode='install' if args.install else 'rollback' if args.rollback else 'check'
    target=args.evidence/('cc-guard-'+mode+'.json')
    if target.exists():raise RuntimeError('Receipt already exists')
    r=execute('vision',['sudo','-n','python3','-c',REMOTE,mode])
    target.write_text(json.dumps(r,indent=2));print(json.dumps(r));return r.get('returncode',1)


if __name__=='__main__':
    raise SystemExit(main())
