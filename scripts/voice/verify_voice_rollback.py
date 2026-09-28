#!/usr/bin/env python3
"""Offline rollback integrity audit and restoration bundle; never writes robot.

Before any future restore, require current target == after_sha256 in the
actual installation receipt. Do not restore an entire archive over a robot.
"""
import argparse,hashlib,json,tarfile
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path);a=p.parse_args();rows=json.loads(a.plan.read_text());count=0
 if a.output:a.output.mkdir(parents=True,exist_ok=False)
 grouped={}
 for r in rows:grouped.setdefault(r['backup_archive'],[]).append(r)
 for archive,items in grouped.items():
  with tarfile.open(archive) as t:
   for r in items:
    data=t.extractfile(r['backup_member']).read()
    if hashlib.sha256(data).hexdigest()!=r['before_sha256']:raise RuntimeError('Original corrupt')
    if hashlib.sha256(Path(r['new_file']).read_bytes()).hexdigest()!=r['after_sha256']:raise RuntimeError('Replacement changed')
    if a.output:
     relative=Path(r['target'].lstrip('/'))
     if '..' in relative.parts or '/' in r['container']:raise ValueError('Unsafe target')
     out=a.output/r['container']/relative;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
    count+=1
 print('ROLLBACK_ORIGINALS_VERIFIED='+str(count)+'; ROBOT_WRITES=0')
if __name__=='__main__':main()
