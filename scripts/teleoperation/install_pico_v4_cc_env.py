#!/usr/bin/env python3
"""Install CC-only SPS env override with original backups; no reload or motion.

Pinned to the reviewed Vision config in this intervention. Default --check
only reads. --install updates compose plus its metafile source. --rollback
restores the exact originals. Container recreation is a separate operation.
"""
import argparse
import base64
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from scripts.collect_estop_available_readonly import execute

REMOTE=r'''
import base64,hashlib,json,os,pathlib,stat,sys,tempfile
ns={'__name__':'cc_profile_library'}
exec(base64.b64decode(sys.argv[1]),ns)
mode=sys.argv[2]
root=pathlib.Path('/home/walker/.config/udoke/walker')
stage=pathlib.Path('/home/walker/.local/share/cruzr-pico-v4-cc-20261015')
items=[(root/'compose.yml','compose.yml',False,'47ec176b30008d652814321780319d45c177fc6e48e7b91366c5e6871b9d785a','b5658b0237225f001e41bc84fafa3f5620d7314b952212624ca1de06bd0fd127'),
 (root/'.metafiles/system.metafile.yml','system.metafile.yml',True,'cdec690e783e57d9e562d4f41d53146abe7f79eab345bb4a3dd3506ef44fde7b','052db6d7e3ceb29a4cf2938b18e90d198a330bba1405299210cc9f74c088f725')]
prepared=[]
for target,name,template,original_sha,candidate_sha in items:
 current=target.read_bytes(); current_sha=hashlib.sha256(current).hexdigest()
 if current_sha not in (original_sha,candidate_sha):raise RuntimeError('Unreviewed config drift: '+str(target))
 backup=stage/(name+'.before')
 original=current if current_sha==original_sha else backup.read_bytes()
 if hashlib.sha256(original).hexdigest()!=original_sha:raise RuntimeError('Backup hash mismatch')
 candidate=ns['prepare'](original,template)
 if hashlib.sha256(candidate).hexdigest()!=candidate_sha:raise RuntimeError('Candidate hash mismatch')
 desired=original if mode=='rollback' else candidate
 prepared.append((target,name,current,original,candidate,desired))
if mode!='check':
 stage.mkdir(mode=0o700,parents=True,exist_ok=True)
 for target,name,current,original,candidate,desired in prepared:
  for suffix,data in [('before',original),('candidate',candidate)]:
   f=stage/(name+'.'+suffix)
   if f.exists() and f.read_bytes()!=data:raise RuntimeError('Backup stage drift')
   if not f.exists():
    with f.open('xb') as stream:stream.write(data)
    f.chmod(0o600)
 # Check ownership and both files before any replacement.
 if any(target.stat().st_uid!=os.getuid() for target,_,_,_,_,_ in prepared):raise RuntimeError('Unexpected file owner')
 if any(target.read_bytes()!=current for target,_,current,_,_,_ in prepared):raise RuntimeError('Config changed during preparation')
 for target,name,current,original,candidate,desired in prepared:
  if current==desired:continue
  metadata=target.stat()
  if metadata.st_uid!=os.getuid():raise RuntimeError('Unexpected file owner')
  fd,temp=tempfile.mkstemp(prefix='.pico-v4-',dir=target.parent)
  try:
   with os.fdopen(fd,'wb') as stream:stream.write(desired);stream.flush();os.fsync(stream.fileno())
   os.chmod(temp,stat.S_IMODE(metadata.st_mode));os.replace(temp,target)
  finally:
   if os.path.exists(temp):os.unlink(temp)
print(json.dumps(dict(mode=mode,reloaded=False,states={str(target):dict(sha256=hashlib.sha256(target.read_bytes()).hexdigest(),state='sps' if target.read_bytes()==candidate else 'original') for target,_,_,_,candidate,_ in prepared})))
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    group=p.add_mutually_exclusive_group()
    group.add_argument('--install',action='store_true')
    group.add_argument('--rollback',action='store_true')
    group.add_argument('--check',action='store_true')
    p.add_argument('--evidence',required=True,type=Path)
    args=p.parse_args()
    mode='install' if args.install else 'rollback' if args.rollback else 'check'
    helper=base64.b64encode(Path(__file__).with_name('prepare_pico_v4_cc_env.py').read_bytes()).decode()
    output=args.evidence/('cc-env-'+mode+'.json')
    if output.exists():raise RuntimeError('Evidence receipt exists; use a new evidence directory')
    result=execute('vision',['python3','-c',REMOTE,helper,mode])
    output.write_text(json.dumps(result,indent=2));print(json.dumps(result))
    return result.get('returncode',1)


if __name__=='__main__':
    raise SystemExit(main())
