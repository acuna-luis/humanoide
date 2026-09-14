#!/usr/bin/env python3
"""Prepare a source-bound ENTRY360 trial review, without execution transport."""
import argparse
import json
import math
from pathlib import Path

import numpy as np

from prepare_vla_entry_bundle import ROOT, JOINT_ORDER, digest
from general_home.trace_analysis import decode_actuators, strict_json
from general_home.planner import segment_seconds


def cubic_proposal(start, end):
    a,b=np.asarray(start,float),np.asarray(end,float)
    if a.shape!=(20,) or b.shape!=(20,) or not np.isfinite([a,b]).all():
        raise ValueError('Expected two finite 20D states')
    # Engineering proposal only, not a measured or vendor-qualified limit.
    duration=math.ceil(segment_seconds(a,b,caps=(.05,.05,1.),law='cubic-rest'))
    delta=np.abs(b-a)
    return dict(start_rad=a.tolist(),end_rad=b.tolist(),duration_seconds=duration,
        curve='q0+(q1-q0)*(3u^2-2u^3), stationary endpoints, shared progress assumed',
        proposed_velocity_cap_rad_s=.05,proposed_acceleration_cap_rad_s2=.05,
        analytical_peak_velocity_rad_s=float(1.5*delta.max()/duration) if duration else 0.,
        analytical_peak_acceleration_rad_s2=float(6*delta.max()/duration**2) if duration else 0.,
        global_jerk_bound=None,runtime_law_equivalence_verified=False,
        caps_physically_qualified=False,installable=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('review','interfaces','selection','trace','trace-analysis','output'):
        parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('Output must be new')
    review=json.loads(args.review.read_text());interfaces=json.loads(args.interfaces.read_text())
    selection=json.loads(args.selection.read_text());analysis=json.loads(args.trace_analysis.read_text())
    if (review['candidate']!='episode_000360' or review['joint_order']!=JOINT_ORDER
            or interfaces['candidate']!=review['candidate']
            or interfaces['source_sha256'][str(args.review.resolve())]!=digest(args.review)
            or selection['selected_candidate']!=review['candidate']
            or analysis['input_sha256']!=digest(args.trace) or analysis['issues']):
        parser.error('Inconsistent or invalid evidence')
    routes=review['scenarios'][0]['routes'];path=routes['access']['waypoints_20d_rad']
    candidate=next(r for r in selection['candidates'] if r['episode']==review['candidate'])
    if not np.array_equal(path[-1],candidate['state']):parser.error('Dataset endpoint mismatch')
    sample=None
    for line in args.trace.read_text().splitlines():
        record=strict_json(line)
        if record.get('topic')=='/mc/actuator_state':sample=decode_actuators(record['message'])[1]
    if sample is None:parser.error('No actuator sample')
    measured=np.array([sample[n]['position'] for n in JOINT_ORDER])
    source_files=[args.review,args.interfaces,args.selection,args.trace,args.trace_analysis,Path(__file__),
        ROOT/'scripts/teleoperation/general_home/trace_analysis.py',ROOT/'scripts/teleoperation/general_home/planner.py',
        ROOT/'scripts/vla/prepare_vla_entry_bundle.py']
    sources={str(p.resolve()):digest(p) for p in source_files}
    geometry={}
    for name,route in routes.items():
        audit=route['audit'];pairs=audit['pairs']
        geometry[name]=dict(counts=audit['counts'],timed_out=audit['timed_out'],
            scene_pairs=sum(any(n.startswith('scene:') for n in p['pair']) for p in pairs),
            certified_scene_pairs=sum(any(n.startswith('scene:') for n in p['pair']) and p['status']=='CERTIFIED_AFFINE_INTERVALS' for p in pairs),
            all_pairs_physically_qualified=False)
    proposal=cubic_proposal(path[1],path[2])
    result=dict(schema='cruzr-entry360-physical-trial-review-v1',candidate=review['candidate'],
        status='NOT_QUALIFIED_FOR_PHYSICAL_TRIAL',physical_approval=False,
        installable=False,execution_transport_present=False,sources_sha256=sources,
        geometry=geometry,interfaces=interfaces['summary'],
        passive_state=dict(samples=analysis['actuator_sample_count'],
            maximum_abs_velocity_rad_s=max(v['max_abs_velocity_rad_s'] for v in analysis['joints'].values()),
            maximum_requested_command_error_rad=max(v['max_abs_requested_command_error_rad'] for v in analysis['joints'].values()),
            maximum_start_difference_rad=float(np.max(np.abs(measured-np.asarray(path[0])))),
            joint_order=JOINT_ORDER,last_measured_q=measured.tolist(),stops=analysis['last_observed_stops'],
            validity='observation at capture time only; not a reusable motion permit'),
        vla_fixture=dict(requested_table_height_m=.8,
            inferred_training_table_height_m=candidate['inferred_support_height_m'],
            pixel_only_height_range_m=candidate['pixel_only_height_range_m'],
            total_height_error_bounded=False,compatibility_verified=False,
            relevant_to='VLA pickup compatibility, distinct from an isolated empty posture trial'),
        ready_to_entry_timing_proposal=proposal,
        blockers_for_physical_posture_trial=[
            'Actual scene registration, dimensions and angular error not bounded by the provisional 50mm scenario',
            'Moving internal interfaces sampled; complete physical correspondence/continuous qualification absent',
            'ENTRY360 runtime task/group dispatch, tracking envelope and stopping bound not validated'],
        old_runner=dict(candidate='episode_000040',suitable_for_entry360=False,modified=False),
        robot_movements=0,robot_installations=0)
    if any(digest(Path(p))!=h for p,h in sources.items()):raise RuntimeError('Evidence changed during review')
    with args.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:result[k] for k in ('status','geometry','vla_fixture','ready_to_entry_timing_proposal')}))


if __name__=='__main__':main()
