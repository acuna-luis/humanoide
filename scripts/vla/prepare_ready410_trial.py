#!/usr/bin/env python3
"""Bind the corrected READY access and ENTRY reviews into a local trial package."""
import argparse
import json
from pathlib import Path

from prepare_vla_entry_bundle import digest
from ready410_trial_contract import all_trial_stages


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('access-review','entry-review','reference','hardware-snapshot','output-dir'):
        p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args()
    if a.output_dir.exists():p.error('Choose a new output directory')
    values={k:str(getattr(a,k).resolve()) for k in ('access_review','entry_review','reference','hardware_snapshot')}
    sources=[Path(v) for v in values.values()]+[Path(__file__),Path(__file__).with_name('ready410_trial_contract.py'),Path(__file__).with_name('audit_ready_controller_contract.py')]
    bindings={str(f.resolve()):digest(f) for f in sources}
    a.output_dir.mkdir(parents=True)
    manifests={}
    for part in ('access','entry'):
        f=(a.output_dir/(part+'.json')).resolve();manifests[part]=str(f)
        f.write_text(json.dumps(dict(schema='cruzr-ready410-head063-trial-v1',part=part,
            bindings=bindings,**values),indent=2)+'\n')
    bundle=a.output_dir/'bundle.json'
    bundle.write_text(json.dumps(dict(schema='cruzr-ready410-head063-bundle-v1',manifests=manifests,
        manifests_sha256={v:digest(Path(v)) for v in manifests.values()},physical_approval=False),indent=2)+'\n')
    stages=all_trial_stages(bundle)
    xml_dir=a.output_dir/'xml';xml_dir.mkdir()
    for s in stages:
        (xml_dir/(s['task'].split('/')[-1]+'.xml')).write_bytes(Path(s['xml']).read_bytes())
    (a.output_dir/'READY_FOR_DISK_PLAN.json').write_text(json.dumps(dict(
        bundle=str(bundle.resolve()),bundle_sha256=digest(bundle),tasks=len(stages),
        physical_approval=False,qualification_issued=False,
        nominal_forward_seconds=sum(s['duration_seconds'] for s in stages if s['direction']=='forward')),
        indent=2)+'\n')
    print('LOCAL_TRIAL_PACKAGE_VERIFIED: 20 XML; no installation, reload or movement')


if __name__=='__main__':main()
