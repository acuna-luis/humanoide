#!/usr/bin/env python3
"""Build full fixed TTS catalog from live inventories using reviewed translation tables."""
import argparse,csv,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--inventory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 tr={}
 for name in ['traducciones.tsv','traducciones_adicionales.tsv']:
  for row in csv.DictReader((ROOT/'docs/voice'/name).open(),delimiter='\t'):
   if not row.get('es') or not row.get('en'):raise ValueError(row)
   tr[row['zh']]=(row['es'],row['en'])
 def translate(t):
  if t in tr:return tr[t]
  t=t.strip().rstrip('!')
  if t in tr:return tr[t]
  position=re.fullmatch(r'位置为([一二三四十]+)，搬([大小])螺丝空料盘',t)
  if position:
   chars=position[1].split('十');nums={'':0,'一':1,'二':2,'三':3,'四':4};n=(nums[chars[0]] or 1)*10+nums[chars[1]]
   es='grandes' if position[2]=='大' else 'pequeños';en='large' if position[2]=='大' else 'small'
   return f'Posición {n}. Transportando la bandeja vacía de tornillos {es}.',f'Position {n}. Transporting the empty tray for {en} screws.'
  parts=[x for x in re.split('[,，]+',t) if x]
  if len(parts)>1:
   pairs=[translate(x) for x in parts];return tuple(' '.join(x[i] for x in pairs) for i in [0,1])
  if not re.search('[\u4e00-\u9fff]',t):return t,t
  raise ValueError(t)
 sources={}
 for f in a.inventory.glob('*/inventory.json'):
  d=json.loads(f.read_text())
  for r in d['tts']:sources.setdefault(r['text'],[]).append({'container':f.parent.name,'path':r['path']})
 rows=[];missing=[]
 for text,origins in sorted(sources.items()):
  dynamic=text.startswith('{') and text.endswith('}')
  try:es,en=('', '') if dynamic else translate(text)
  except ValueError:missing.append(text);continue
  rows.append({'id':'tts_'+hashlib.sha256(text.encode()).hexdigest()[:12],'zh':text,'es':es,'en':en,'kind':'dynamic' if dynamic else 'fixed','chinese':bool(re.search('[\u4e00-\u9fff]',text)),'sources':origins,'installed':False})
 (a.output/'untranslated.json').write_text(json.dumps(missing,ensure_ascii=False,indent=2))
 (a.output/'catalog.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
 print('rows',len(rows),'dynamic',sum(r['kind']=='dynamic' for r in rows),'missing',len(missing));print('\n'.join(missing))
if __name__=='__main__':main()
