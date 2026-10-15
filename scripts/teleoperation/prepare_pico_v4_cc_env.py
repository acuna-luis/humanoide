#!/usr/bin/env python3
"""Offline CC-only HW_TYPE override, preserving every other YAML value and byte.

Prepare candidates only; never installs, recreates or moves the robot.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import yaml


def field(node, key):
    matches=[v for k,v in node.value if k.value==key]
    if len(matches)!=1:raise ValueError('Expected one YAML field: '+key)
    return matches[0]


def prepare(raw, template=False):
    text=raw.decode()
    root=yaml.compose(text)
    if template:
        env=field(field(field(root,'nodes'),'control_center'),'environment')
        expected='HW_TYPE={{env "HW_TYPE"}}'
        keys=('nodes','control_center')
    else:
        env=field(field(field(root,'services'),'system.control_center'),'environment')
        expected='HW_TYPE=cruzr_s2_v1'
        keys=('services','system.control_center')
    matches=[v for v in env.value if v.value.startswith('HW_TYPE=')]
    if len(matches)!=1 or matches[0].value!=expected:
        raise ValueError('Unrecognized CC HW_TYPE source; no transformation')
    node=matches[0]
    value='HW_TYPE=cruzr_s2_v1_sps'
    candidate=(text[:node.start_mark.index]+json.dumps(value)+text[node.end_mark.index:]).encode()
    desired=copy.deepcopy(yaml.safe_load(raw))
    entries=desired[keys[0]][keys[1]]['environment']
    entries[entries.index(expected)]=value
    if yaml.safe_load(candidate)!=desired:raise ValueError('Unexpected YAML changes')
    return candidate


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before-directory',required=True,type=Path)
    p.add_argument('--output-directory',required=True,type=Path)
    args=p.parse_args()
    args.output_directory.mkdir(mode=0o700,exist_ok=False)
    report={}
    for name,template in [('compose.yml',False),('system.metafile.yml',True)]:
        before=(args.before_directory/name).read_bytes()
        after=prepare(before,template)
        dest=args.output_directory/name;dest.write_bytes(after);dest.chmod(0o600)
        report[name]=dict(before=hashlib.sha256(before).hexdigest(),after=hashlib.sha256(after).hexdigest(),
                          only_change='control_center environment HW_TYPE')
    (args.output_directory/'manifest.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))


if __name__=='__main__':
    main()
