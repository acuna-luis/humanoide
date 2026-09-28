#!/usr/bin/env python3
"""Build Spanish FILE-mode deployment from verified originals, without robot writes."""
import argparse,hashlib,json,re,tarfile,xml.etree.ElementTree as E
from pathlib import Path
from xml.sax.saxutils import escape

def main():
 p=argparse.ArgumentParser();p.add_argument('--package',type=Path,required=True);p.add_argument('--backups',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 rows=json.loads((a.package/'catalog.json').read_text());tr={r['zh']:r for r in rows if r['kind']=='fixed'}
 audio=json.loads((a.package/'audio_es/manifest.json').read_text())+json.loads((a.package/'audio_spoken_es/manifest.json').read_text());by={x['id']:x for x in audio};plan=[]
 def add(container,target,data,before,metadata):
  key=hashlib.sha256((container+':'+target).encode()).hexdigest();dest=a.output/'payload'/key;dest.parent.mkdir(exist_ok=True);dest.write_bytes(data)
  plan.append({'container':container,'target':target,'before_sha256':before,'after_sha256':hashlib.sha256(data).hexdigest(),'payload':key,'metadata':metadata})
 for x in audio:add('HOST','/etc/walker/voice/es_local_v1/'+x['id']+'.wav',Path(x['path']).read_bytes(),None,{'mode':0o644,'uid':0,'gid':0})
 # Keep English goals/catalog on the host for later dispatcher integration, no execution.
 for name in ['tts-goals-en.json','catalog.json']:
  add('HOST','/etc/walker/voice/es_local_v1/'+name,(a.package/name).read_bytes(),None,{'mode':0o644,'uid':0,'gid':0})
 for folder in a.backups.iterdir():
  if folder.name not in ['walker-voice.speech_service-1','walker-system.ae_bt_master-1','walker-system.control_center-1','walker-nav.nav_taskmanager-1']:continue
  with tarfile.open(folder/'originals.tar.gz') as tar:
   for r in json.loads((folder/'manifest.json').read_text())['files']:
    if not r['path'].endswith('.xml'):continue
    before=tar.extractfile('files/'+r['path'].lstrip('/')).read()
    try:text=before.decode();original=E.fromstring(text)
    except (UnicodeDecodeError,E.ParseError):continue
    def sub(m):
     e=E.fromstring(m[0]);s=e.get('tts')
     if s not in tr:return m[0]
     newpath='/etc/walker/voice/es_local_v1/'+tr[s]['id']+'.wav'
     tag=re.sub(r'tts="[^"]*"','tts="'+newpath+'"',m[0])
     if re.search(r'\bfile="',tag):tag=re.sub(r'\bfile="[^"]*"','file="true"',tag)
     else:tag=tag.replace('<TtsClient','<TtsClient file="true"',1)
     return tag
    after=re.sub(r'<TtsClient\b[^>]*?/>',sub,text,flags=re.S).encode()
    if before==after:continue
    changed=E.fromstring(after)
    aa=list(original.iter());bb=list(changed.iter());assert len(aa)==len(bb)
    for x,y in zip(aa,bb):
     if x.tag=='TtsClient' and x.get('tts') in tr:
      assert y.get('file')=='true';y.attrib.pop('file',None)
      if 'file' in x.attrib:y.set('file',x.get('file'))
      y.set('tts',x.get('tts'))
    for element in aa+bb:
     attrs=sorted(element.attrib.items());element.attrib.clear();element.attrib.update(attrs)
    assert E.tostring(original)==E.tostring(changed),'Non-voice XML change'
    add(folder.name,r['path'],after,r['sha256'],{k:r[k] for k in ['mode','uid','gid']})
 for r in json.loads((a.package/'audio-replacement-plan.json').read_text()):
  if r.get('new_file'):add(r['container'],r['target'],Path(r['new_file']).read_bytes(),r['before_sha256'],r['metadata'])
 (a.output/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
 print('Entries',len(plan),'new host files',sum(x['container']=='HOST' for x in plan),'replacements',sum(x['before_sha256'] is not None for x in plan))
if __name__=='__main__':main()
