#!/usr/bin/env python3
"""Local ASR inspection; retains uncertainty and does not claim human listening."""
import argparse,json,hashlib
from pathlib import Path
import soundfile as sf
from faster_whisper import WhisperModel

def main():
 p=argparse.ArgumentParser();p.add_argument('--inventory',type=Path,required=True);p.add_argument('--models',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 model=WhisperModel('small',device='cpu',compute_type='int8',download_root=str(a.models),cpu_threads=6)
 seen=set();rows=[]
 for r in json.loads(a.inventory.read_text())['audio']:
  if not r.get('local') or r['sha256'] in seen:continue
  seen.add(r['sha256']);info=sf.info(r['local']);row={'source':r['path'],'local':r['local'],'sha256':r['sha256'],'duration':info.duration,'method':'Whisper small automatic transcription, not human listening'}
  if info.duration>90:row['status']='long_audio_pending'
  else:
   seg,meta=model.transcribe(r['local'],language='zh',beam_size=5,vad_filter=False,condition_on_previous_text=False)
   segments=[{'text':s.text,'no_speech_prob':s.no_speech_prob,'avg_logprob':s.avg_logprob,'start':s.start,'end':s.end} for s in seg];row.update(segments=segments,text=''.join(s['text'] for s in segments),status='ASR_proposal_requires_review')
  rows.append(row);a.output.write_text(json.dumps(rows,ensure_ascii=False,indent=2));print(Path(r['path']).name,row.get('text',row['status']),flush=True)
if __name__=='__main__':main()
