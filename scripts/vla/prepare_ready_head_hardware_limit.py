#!/usr/bin/env python3
"""Create a separate, freshly audited READY reference within head hardware limits."""
import argparse
import copy
import json
import math
from pathlib import Path
import time

import yaml
from prepare_home_ready_access import (ROOT, JOINT_ORDER, RobotGeometry, common, digest,
    certify_pairs, solid_distance, LocalDisplacementBounds, SelectivePairDistances,
    DirectionalSceneBounds, SubdividedSceneBounds)


def choose_pitch(old, lower, upper, error):
    if not all(math.isfinite(x) for x in (old,lower,upper,error)) or error < 0 or lower >= upper:
        raise ValueError('Invalid bounds')
    lo, hi = lower+error, upper-error
    if lo > hi:
        raise ValueError('Uncertainty does not fit hardware interval')
    if lo <= old <= hi:
        return old
    # Round inward to a centiradian, preserving the existing error enclosure.
    value = math.ceil(lo*100)/100 if old < lo else math.floor(hi*100)/100
    if not lo <= value <= hi:
        raise ValueError('No inward centiradian target fits')
    return value


def adjusted_reference(reference, lower, upper):
    result = copy.deepcopy(reference)
    if result['candidate'] != 'episode_000410' or result['joint_order'] != JOINT_ORDER or len(result['scenarios']) != 1:
        raise ValueError('Expected exact ENTRY410 scene')
    routes = result['scenarios'][0]['routes']
    access, reverse = routes['access'], routes['empty_recovery']
    if (len(access['waypoints_20d_rad']) != 3 or len(reverse['waypoints_20d_rad']) != 4
            or access['waypoints_20d_rad'][1] != reverse['waypoints_20d_rad'][1]):
        raise ValueError('Inconsistent READY references')
    error = max(r['audit']['joint_error_scenario_rad'] for r in routes.values())
    i = JOINT_ORDER.index('head_pitch_joint')
    old = access['waypoints_20d_rad'][1][i]
    new = choose_pitch(old,lower,upper,error)
    for route in (access, reverse):
        route['waypoints_20d_rad'][1][i] = new
    result['ready_head_adaptation'] = dict(old_pitch_rad=old, new_pitch_rad=new,
        hardware_limits_rad=[lower,upper], retained_error_rad=error,
        ready_only=True, entry_endpoint_unchanged=True, installed=False)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('reference','hardware-snapshot','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():p.error('Use a new output; never overwrite previous reviews')
    snapshot=json.loads(a.hardware_snapshot.read_text())
    records=[v for k,v in snapshot.items() if k.endswith('/ecat_hardware/transmissions.yaml')]
    if len(records)!=1:raise ValueError('Missing unique hardware transmissions')
    record=records[0]
    import hashlib
    if hashlib.sha256(record['text'].encode()).hexdigest()!=record['sha256']:
        raise ValueError('Snapshot hash mismatch')
    transmissions=yaml.safe_load(record['text'])['transmissions']
    limits=[v['joint']['limit'] for v in transmissions.values() if v['joint']['name']=='head_pitch_joint']
    if len(limits)!=1:raise ValueError('Missing unique head limit')
    result=adjusted_reference(json.loads(a.reference.read_text()),limits[0]['lower'],limits[0]['upper'])
    files=[a.reference,a.hardware_snapshot,Path(__file__),
           *sorted((ROOT/'scripts/vla').glob('*.py')),
           *sorted((ROOT/'scripts/teleoperation/general_home').glob('*.py'))]
    hashes={str(f.resolve()):digest(f) for f in files}
    scene=result['scenarios'][0]
    package=ROOT/'cruzr_s2_description_splint/cruzr_s2_description'
    base=RobotGeometry(package/'urdf/cruzr_s2_v1/cruzr_s2_v1.urdf',package,
                       dict(frame_id='base_link',complete=True,objects=scene['scene_objects']))
    if base.manifest!=result['model_sources']:raise ValueError('Changed model')
    local=LocalDisplacementBounds(SelectivePairDistances(base,common,solid_distance),common,JOINT_ORDER)
    model=SubdividedSceneBounds(DirectionalSceneBounds(local,common,JOINT_ORDER),512)
    for name,route in scene['routes'].items():
        started=time.monotonic()
        error=route['audit']['joint_error_scenario_rad']
        route['audit']=certify_pairs(model,route['waypoints_20d_rad'],seconds=60,max_depth=10,joint_error_rad=error)
        route['elapsed_seconds']=time.monotonic()-started
        print(json.dumps(dict(route=name,counts=route['audit']['counts'],timed_out=route['audit']['timed_out'])),flush=True)
    result.update(physical_approval=False,dynamics_or_stopping_validated=False,sources_sha256=hashes)
    if not base.source_files_unchanged() or any(digest(Path(f))!=h for f,h in hashes.items()):
        raise ValueError('Sources changed during review')
    with a.output.open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(result['ready_head_adaptation']))


if __name__=='__main__':main()
