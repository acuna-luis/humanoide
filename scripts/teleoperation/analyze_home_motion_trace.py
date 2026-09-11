#!/usr/bin/env python3
"""Summarize an archived passive trace; no robot connection or physical approval."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from general_home.trace_analysis import analyze, strict_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--max-gap-seconds',type=float,default=.05)
    args=parser.parse_args()
    if args.output.exists():parser.error('Output already exists')
    raw=args.input.read_bytes()
    result=analyze([strict_json(line) for line in raw.decode().splitlines() if line.strip()],args.max_gap_seconds)
    result['input_sha256']=hashlib.sha256(raw).hexdigest()
    with args.output.open('x') as f:f.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({key:result[key] for key in ['status','actuator_sample_count','last_observed_stops','issues','physical_approval']}))
    return 0 if not result['issues'] else 3


if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,OSError,TypeError) as exc:print('ERROR: '+str(exc),file=sys.stderr);raise SystemExit(2)
