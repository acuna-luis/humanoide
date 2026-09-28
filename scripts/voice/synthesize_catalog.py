#!/usr/bin/env python3
"""Synthesize catalog on PC using Edge TTS; never plays or installs on robot."""
import argparse,asyncio,json,hashlib
from pathlib import Path
import edge_tts,av,numpy as np,soundfile as sf
async def main():
 p=argparse.ArgumentParser();p.add_argument('--catalog',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 rows=json.loads(a.catalog.read_text());sem=asyncio.Semaphore(4);results=[]
 async def one(row,lang,voice):
  async with sem:
   out=a.output/lang;out.mkdir(exist_ok=True);mp3=out/(row['id']+'.mp3');wav=out/(row['id']+'.wav')
   for attempt in range(3):
    try:
     if not mp3.exists() or mp3.stat().st_size==0:await asyncio.wait_for(edge_tts.Communicate(row[lang],voice,rate='-5%').save(str(mp3)),timeout=45)
     arrays=[]
     with av.open(str(mp3)) as c:
      res=av.AudioResampler(format='s16',layout='mono',rate=16000)
      for frame in c.decode(audio=0):
       for f in res.resample(frame):arrays.append(f.to_ndarray().flatten())
      for f in res.resample(None):arrays.append(f.to_ndarray().flatten())
     data=np.concatenate(arrays);sf.write(str(wav),data,16000,subtype='PCM_16')
     if len(data)<1600 or np.max(np.abs(data.astype(np.int32)))==0:raise ValueError('Empty or silent audio')
     result={'id':row['id'],'lang':lang,'voice':voice,'text':row[lang],'wav':str(wav.resolve()),'mp3':str(mp3.resolve()),'seconds':len(data)/16000,'sample_rate':16000,'channels':1,'sha256':hashlib.sha256(wav.read_bytes()).hexdigest(),'listened':False};results.append(result);print(row['id'],lang,'OK',flush=True);return
    except Exception as e:
     if attempt==2:results.append({'id':row['id'],'lang':lang,'error':str(e)});return
     await asyncio.sleep(2)
 await asyncio.gather(*(one(r,lang,voice) for r in rows if r['kind']!='dynamic' for lang,voice in [('es','es-ES-ElviraNeural'),('en','en-GB-SoniaNeural')]))
 (a.output/'manifest.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
 if any('error' in r for r in results):raise SystemExit('Some synthesis failed; inspect manifest')
if __name__=='__main__':asyncio.run(main())
