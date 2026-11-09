#!/usr/bin/env python3
"""Infer on unreviewed current-capture observations, offline and without control."""
import argparse
import importlib.metadata
import sys

from evaluate_failed_offline import run


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('test','train','checkpoint','vlm','output'): p.add_argument('--'+key,required=True)
    p.add_argument('--device',choices=('cpu','cuda'),default='cpu')
    p.add_argument('--seed',type=int,default=20261109)
    p.add_argument('--test-sha256',required=True)
    p.add_argument('--current-only',dest='offline_only',action='store_true')
    try: run(p.parse_args(),mode='current')
    except (OSError,ValueError,KeyError,TypeError,importlib.metadata.PackageNotFoundError) as exc:
        print(f'ERROR: {exc}',file=sys.stderr);sys.exit(1)
