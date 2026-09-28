#!/usr/bin/env python3
"""Prepare English XML copies and a hash-pinned rollback plan. No robot writes."""
import argparse,hashlib,json,re,tarfile,xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape

def main():
 p=argparse.ArgumentParser();p.add_argument('--package',type=Path,required=True);p.add_argument('--backups',type=Path,required=True);a=p.parse_args()
 rows=json.loads((a.package/'catalog.json').read_text());tr={r['zh']:r['en'] for r in rows if r['kind']!='dynamic'};plan=[]
 for folder in sorted(a.backups.iterdir()):
  if not (folder/'manifest.json').exists():continue
  manifest=json.loads((folder/'manifest.json').read_text());archive=folder/'originals.tar.gz'
  with tarfile.open(archive) as tar:
   for row in manifest['files']:
    if not row['path'].endswith('.xml'):continue
    before=tar.extractfile('files/'+row['path'].lstrip('/')).read()
    try:text=before.decode('utf-8');original=ET.fromstring(text)
    except (UnicodeDecodeError,ET.ParseError):continue
    def sub(m):
     s=ET.fromstring('<x tts="'+m[1]+'"/>').get('tts')
     if s not in tr:return m[0]
     return 'tts="'+escape(tr[s],{'"':'&quot;'})+'"'
    new=re.sub(r'tts="([^"]*)"',sub,text).encode()
    if new==before:continue
    changed=ET.fromstring(new)
    for t in [original,changed]:
     for e in t.iter():
      if 'tts' in e.attrib:e.attrib['tts']='IGNORED_TRANSLATED_LITERAL'
    if ET.tostring(original)!=ET.tostring(changed):raise RuntimeError('Non-text modification')
    dest=a.package/'xml_en'/folder.name/row['path'].lstrip('/');dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(new)
    plan.append({'container':folder.name,'target':row['path'],'before_sha256':row['sha256'],'after_sha256':hashlib.sha256(new).hexdigest(),'new_file':str(dest.resolve()),'backup_archive':str(archive.resolve()),'backup_member':'files/'+row['path'].lstrip('/'),'metadata':{k:row[k] for k in ['mode','uid','gid','mtime_ns','symlink']},'installed':False})
 (a.package/'replacement-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
 goals={r['id']:{'type':1,'is_break':True,'file_path':'','text':r['en'],'speaker':'','speed':50,'volume':80,'pitch':50,'language':'en','format':'wav','need_save':False} for r in rows if r['kind']!='dynamic'}
 (a.package/'tts-goals-en.json').write_text(json.dumps(goals,ensure_ascii=False,indent=2))
 print('Review copies and rollback entries',len(plan))
if __name__=='__main__':main()
