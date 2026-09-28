#!/usr/bin/env python3
"""Offline Spanish WAV generation; no network, playback or robot writes."""
import argparse,hashlib,json,wave
from pathlib import Path
from piper import PiperVoice,SynthesisConfig
import av,numpy as np,soundfile as sf

def main():
 p=argparse.ArgumentParser();p.add_argument('--catalog',type=Path,required=True);p.add_argument('--model',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 voice=PiperVoice.load(str(a.model));config=SynthesisConfig(speaker_id=1,length_scale=1.08)
 manifest=[]
 for r in json.loads(a.catalog.read_text()):
  if r['kind']=='dynamic' or not r.get('es'):continue
  f=a.output/(r['id']+'.wav');raw=a.output/(r['id']+'.native.wav')
  with wave.open(str(raw),'wb') as w:voice.synthesize_wav(r['es'],w,syn_config=config)
  arrays=[]
  with av.open(str(raw)) as c:
   res=av.AudioResampler(format='s16',layout='mono',rate=16000)
   for frame in c.decode(audio=0):
    for chunk in res.resample(frame):arrays.append(chunk.to_ndarray().flatten())
   for chunk in res.resample(None):arrays.append(chunk.to_ndarray().flatten())
  data=np.concatenate(arrays);sf.write(str(f),data,16000,subtype='PCM_16')
  if len(data)<1600 or not np.any(data):raise RuntimeError('Invalid generated audio')
  manifest.append({'id':r['id'],'path':str(f.resolve()),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'seconds':len(data)/16000,'sample_rate':16000,'channels':1,'speaker_id':1,'engine':'piper','model_sha256':hashlib.sha256(a.model.read_bytes()).hexdigest()})
  print(r['id'],'OK',flush=True)
 (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2))
if __name__=='__main__':main()
