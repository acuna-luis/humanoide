#!/usr/bin/env python3
"""Verify unchanged readiness logic and isolated preload guard without robot calls."""
import ast,hashlib,json,sys,tarfile,types
from pathlib import Path
build=Path(sys.argv[1])
with tarfile.open(build/'originals.tar.gz') as t:
 before=t.extractfile('etc/walker/boot/cruzr_cc_start_when_ready.py').read().decode()
 original_bytes={m.name:t.extractfile(m).read() for m in t if m.isfile()}
after=(build/'boot.after.py').read_text()
a=ast.parse(before);b=ast.parse(after)
main=next(n for n in b.body if isinstance(n,ast.FunctionDef) and n.name=='main')
guard=main.body[-2]
assert isinstance(guard,ast.Try) and 'voice_hashes' in ast.unparse(guard)
main.body.remove(guard)
assert ast.dump(a)==ast.dump(b),'Readiness/exec logic changed'
files={'/'+k:v for k,v in original_bytes.items()}
for row in json.loads((build/'deployment/plan.json').read_text()):
 files[row['target']]=(build/'deployment/payload'/row['payload']).read_bytes()
module=ast.fix_missing_locations(ast.Module(body=[guard],type_ignores=[]))
class FakePath:
 def __init__(self,name):self.name=name
 def read_bytes(self):return files[self.name]
def run():
 logs=[];env={'LD_PRELOAD':'/existing.so'}
 ns=dict(hashlib=hashlib,Path=FakePath,os=types.SimpleNamespace(environ=env),log=logs.append)
 exec(compile(module,'guard','exec'),ns)
 return env,logs
env,logs=run();assert env['LD_PRELOAD'].endswith('libvoice_cc.so:/existing.so')
files['/etc/walker/voice/control_center_es_v1/libvoice_cc.so']=b'corrupt'
env,logs=run();assert env['LD_PRELOAD']=='/existing.so' and 'native fallback' in logs[0]
print('PASS: unchanged readiness/exec AST; valid guard; corrupt adapter native fallback; no exec')
