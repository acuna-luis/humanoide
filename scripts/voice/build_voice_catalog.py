#!/usr/bin/env python3
"""Build local voice catalog and English XML copies; never modifies vendor/robot."""
import argparse,csv,hashlib,json,re,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 rows=list(csv.DictReader((ROOT/'docs/voice/traducciones.tsv').open(),delimiter='\t'));translations={r['zh']:r for r in rows};found={};sources={}
 for f in sorted((ROOT/'vendor/ubtech/cruzr_s2/snapshot_20260916/vision').rglob('*.xml')):
  try:tree=ET.parse(f)
  except ET.ParseError:continue
  for e in tree.iter():
   if (e.tag=='TtsClient' or e.get('ID')=='TtsClient') and e.get('tts'):
    text=e.get('tts');found.setdefault(text,[]).append(str(f.relative_to(ROOT)));sources[str(f.relative_to(ROOT))]=hashlib.sha256(f.read_bytes()).hexdigest()
 catalog=[]
 for text,paths in sorted(found.items()):
  dynamic=text.startswith('{') and text.endswith('}')
  if not dynamic and text not in translations:raise RuntimeError('Missing translation: '+text)
  row=dict(translations.get(text,{'zh':text,'es':'','en':''}),id='tts_'+hashlib.sha256(text.encode()).hexdigest()[:12],kind='dynamic' if dynamic else 'fixed',sources=sorted(set(paths)),installed=False)
  catalog.append(row)
 # Boot text is locally controlled and already English. Spanish is a proposed replacement.
 catalog.append({'id':'boot_ready','kind':'boot','zh':'','es':'Comprobaciones de arranque completadas. Listo para liberar el paro de emergencia.','en':'Ready to release the emergency stop.','sources':['scripts/upgrade/cruzr_boot_voice.py'],'installed':False})
 (a.output/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
 (a.output/'source-hashes.json').write_text(json.dumps(sources,indent=2)+'\n')
 goals={r['id']:{'type':1,'is_break':True,'file_path':'','text':r['en'],'speaker':'','speed':50,'volume':80,'pitch':50,'language':'en','format':'wav','need_save':False} for r in catalog if r['en']}
 (a.output/'tts-goals-en.json').write_text(json.dumps(goals,ensure_ascii=False,indent=2)+'\n')
 # Only translate explicit tts literals; preserve variables and all robot commands.
 from xml.sax.saxutils import escape
 copies=0
 for source in sources:
  f=ROOT/source;s=f.read_text()
  def replacement(m):
   raw=m.group(1)
   try:text=ET.fromstring('<x tts="'+raw+'"/>').get('tts')
   except ET.ParseError:return m.group(0)
   if text not in translations:return m.group(0)
   return 'tts="'+escape(translations[text]['en'],{'"':'&quot;'})+'"'
  changed=re.sub(r'tts="([^"]*)"',replacement,s)
  if changed!=s:
   dest=a.output/'xml_en'/f.relative_to(ROOT/'vendor/ubtech/cruzr_s2/snapshot_20260916/vision');dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(changed);copies+=1
 print(json.dumps({'fixed':sum(x['kind']=='fixed' for x in catalog),'dynamic':sum(x['kind']=='dynamic' for x in catalog),'boot':1,'english_xml_copies':copies}))
if __name__=='__main__':main()
