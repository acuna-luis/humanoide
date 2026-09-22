#!/usr/bin/env python3
"""Additive installer on Motion host; stdin is the reviewed package JSON."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def main():
    bundle = json.load(sys.stdin)
    manifest = bundle['manifest']
    package_id = manifest['id']
    if len(package_id) != 16 or any(c not in '0123456789abcdef' for c in package_id):
        raise ValueError('Invalid package id')
    native = 'walker-motion.manipulation_robot_app-1'
    host_root = Path('/var/tmp/cruzr-front-box')/package_id
    container_root = '/opt/cruzr-front-box/'+package_id
    # Validate ALL dependencies and destinations before creating any task.
    for path, expected in {**manifest['dependencies'], **manifest['native_binaries']}.items():
        result = subprocess.check_output(['docker','exec',native,'sha256sum',path],text=True)
        if result.split()[0] != expected:
            raise RuntimeError('Original dependency differs: '+path)
    for path, text in bundle['tasks'].items():
        result = subprocess.run(['docker','exec',native,'cat',path],capture_output=True)
        if result.returncode == 0 and result.stdout != text.encode():
            raise RuntimeError('Destination conflict, refusing overwrite: '+path)
    host_root.mkdir(parents=True, exist_ok=True)
    for name, text in {**bundle['sources'], 'manifest.json':json.dumps(manifest,indent=2)+'\n'}.items():
        if Path(name).name != name:
            raise ValueError('Invalid source filename')
        path = host_root/name
        if path.exists() and path.read_text()!=text:
            raise RuntimeError('Immutable package conflict: '+str(path))
        if not path.exists():
            path.write_text(text)
    for container in (native, 'walker-ros.ros2-1'):
        subprocess.run(['docker','exec','--user','0',container,'mkdir','-p',container_root],check=True)
        for name in bundle['sources']:
            existing = subprocess.run(['docker','exec',container,'cat',container_root+'/'+name],capture_output=True)
            if existing.returncode == 0:
                if existing.stdout != bundle['sources'][name].encode():
                    raise RuntimeError('Container package conflict')
            else:
                subprocess.run(['docker','cp',str(host_root/name),container+':'+container_root+'/'+name],check=True)
    writer = '''import os,pathlib,sys
p=pathlib.Path(sys.argv[1]);data=sys.stdin.buffer.read()
p.parent.mkdir(parents=True,exist_ok=True)
try:
 with p.open('xb') as f:f.write(data)
except FileExistsError:
 if p.read_bytes()!=data:raise RuntimeError('Conflict')
'''
    created=[]
    for path, text in bundle['tasks'].items():
        existed=subprocess.run(['docker','exec',native,'test','-e',path]).returncode==0
        subprocess.run(['docker','exec','-i',native,'python3','-c',writer,path],
                       input=text,text=True,check=True)
        data=subprocess.check_output(['docker','exec',native,'cat',path])
        if hashlib.sha256(data).hexdigest()!=manifest['robot_files'][path]:
            raise RuntimeError('Installed task mismatch')
        if not existed:created.append(path)
    receipt_path=host_root/'install-receipt.json'
    if receipt_path.exists():
        created=sorted(set(created+json.loads(receipt_path.read_text())['created_tasks']))
    receipt={'package':str(host_root),'id':package_id,'created_tasks':created,
             'originals_overwritten':False,'restarts':0,'movement_commands':0}
    receipt_path.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))


if __name__ == '__main__':
    main()
