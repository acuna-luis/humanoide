#!/usr/bin/env python3
"""Read-only voice inventory; copies audio and utterances to a private PC folder."""
import argparse,base64,hashlib,json,sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from collect_estop_available_readonly import execute
SCAN=r'''
import os,json,re,hashlib,base64,xml.etree.ElementTree as ET
out={'audio':[],'tts':[],'errors':[]}
for root in ['/opt/walker','/etc/walker']:
 for d,dirs,files in os.walk(root):
  dirs[:]=[x for x in dirs if x not in ['node_modules','.git','__pycache__','site-packages','log','logs']]
  for n in files:
   p=os.path.join(d,n)
   try:
    ext=os.path.splitext(n)[1].lower()
    if ext in ['.wav','.mp3','.ogg','.flac']:
     size=os.path.getsize(p)
     row={'path':p,'bytes':size}
     if size<=8000000:
      data=open(p,'rb').read();row.update(sha256=hashlib.sha256(data).hexdigest(),base64=base64.b64encode(data).decode())
     out['audio'].append(row)
    elif ext=='.xml' and os.path.getsize(p)<2000000:
     try:tree=ET.parse(p)
     except ET.ParseError:continue
     for e in tree.iter():
      if e.tag=='TtsClient' or e.get('ID')=='TtsClient':
       if e.get('tts'):out['tts'].append({'path':p,'text':e.get('tts'),'attributes':e.attrib})
   except (OSError,ValueError) as e:out['errors'].append({'path':p,'error':str(e)})
print(json.dumps(out,ensure_ascii=False))
'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 jobs=[('vision',n) for n in ['walker-voice.speech_service-1','walker-system.ae_bt_master-1','walker-system.control_center-1','walker-nav.nav_taskmanager-1','walker-voice.tts-1']]+[('motion','walker-motion.manipulation_robot_app-1')]
 def work(job):
  host,c=job;r=execute(host,['docker','exec',c,'python3','-c',SCAN]);dest=a.output/c;dest.mkdir(exist_ok=True)
  if r.get('returncode')!=0:
   (dest/'error.json').write_text(json.dumps(r));return c,{'error':r.get('stderr',r.get('error'))}
  data=json.loads(r['stdout'])
  for row in data['audio']:
   b=row.pop('base64',None)
   if b:
    f=dest/'audio'/Path(row['path']).relative_to('/');f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(base64.b64decode(b));row['local']=str(f.resolve())
  (dest/'inventory.json').write_text(json.dumps(data,ensure_ascii=False,indent=2));return c,{k:len(data[k]) for k in data}
 with ThreadPoolExecutor(max_workers=3) as pool:
  for c,r in pool.map(work,jobs):print(c,r,flush=True)
if __name__=='__main__':main()
