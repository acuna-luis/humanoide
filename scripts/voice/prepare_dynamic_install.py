#!/usr/bin/env python3
"""Prepare the native adapter + guarded worker launcher, preserving the original ABI."""
import argparse,hashlib,json
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--native-sha',required=True);p.add_argument('--messages-sha',required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 lib=a.build/'libvoice_en.so';sha=hashlib.sha256(lib.read_bytes()).hexdigest();target='/etc/walker/voice/dynamic_en_v1';before=(a.build/'worker.before.sh').read_bytes()
 if before.count(b'rosa run ae_bt_worker ae_bt_worker')!=1:raise ValueError('Unexpected worker launcher')
 block=f'''# VOICE-EN-04: optional localization only; incompatible files fall back to native.
voice_en_lib={target}/libvoice_en.so
if [[ "$(sha256sum "$voice_en_lib" 2>/dev/null | cut -d' ' -f1)" == "{sha}" &&
      "$(sha256sum /opt/walker/task_manager/lib/libtask_manager_lib.so | cut -d' ' -f1)" == "{a.native_sha}" &&
      "$(sha256sum /opt/walker/sys_task_msgs/lib/libsys_task_msgs.so | cut -d' ' -f1)" == "{a.messages_sha}" ]]; then
    export LD_PRELOAD="$voice_en_lib${{LD_PRELOAD:+:$LD_PRELOAD}}"
else
    printf '%s\\n' '[VOICE_EN] incompatible or missing adapter; using native voice' >&2
fi
unset voice_en_lib

'''
 after=before.replace(b'rosa run ae_bt_worker ae_bt_worker',block.encode()+b'rosa run ae_bt_worker ae_bt_worker',1)
 (a.output/'worker.after.sh').write_bytes(after);rows=[]
 def add(container,path,data,old,mode=0o644):
  key=hashlib.sha256((container+':'+path).encode()).hexdigest();f=a.output/'payload'/key;f.parent.mkdir(exist_ok=True);f.write_bytes(data);rows.append({'container':container,'target':path,'before_sha256':old,'after_sha256':hashlib.sha256(data).hexdigest(),'payload':key,'metadata':{'mode':mode,'uid':0,'gid':0}})
 add('HOST',target+'/libvoice_en.so',lib.read_bytes(),None,0o755)
 add('HOST',target+'/native_test',(a.build/'native_test').read_bytes(),None,0o755)
 for f in (Path(__file__).parent/'dynamic').iterdir():
  if f.suffix in ['.cpp','.hpp']:add('HOST',target+'/source/'+f.name,f.read_bytes(),None)
 add('walker-system.ae_bt_master-1','/opt/walker/ae_master/bin/run_ae_bt_worker.sh',after,hashlib.sha256(before).hexdigest(),0o755)
 (a.output/'plan.json').write_text(json.dumps(rows,indent=2));print('Prepared entries',len(rows),'shim_sha',sha)
if __name__=='__main__':main()
