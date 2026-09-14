#!/usr/bin/env python3
"""Recompute archived ENTRY geometry from a passive measured start, offline."""
import argparse
import json
from pathlib import Path
import numpy as np
from prepare_vla_entry_bundle import ROOT, JOINT_ORDER, RobotGeometry, common, digest, certify_pairs, empty_recovery_waypoints
from general_home.geometry import solid_distance
from general_home.trace_analysis import decode_actuators, strict_json
from entry_local_displacement_bounds import LocalDisplacementBounds, SelectivePairDistances
from entry_directional_bounds import DirectionalSceneBounds
from entry_subdivided_scene_bounds import SubdividedSceneBounds


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('reference','trace','trace-analysis','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('Output must be new')
    reference=json.loads(args.reference.read_text());analysis=json.loads(args.trace_analysis.read_text())
    if (reference['joint_order']!=JOINT_ORDER or len(reference['scenarios'])!=1
            or analysis['input_sha256']!=digest(args.trace) or analysis['issues']):
        parser.error('Invalid archived evidence')
    sample=None
    for line in args.trace.read_text().splitlines():
        record=strict_json(line)
        if record.get('topic')=='/mc/actuator_state':sample=decode_actuators(record['message'])[1]
    if sample is None or any(abs(v['velocity'])>.001 or v['error_code'] for v in sample.values()):
        parser.error('Missing, moving or faulted measured state')
    start=[sample[n]['position'] for n in JOINT_ORDER]
    scene=reference['scenarios'][0]
    points=[start,*scene['routes']['access']['waypoints_20d_rad'][1:]]
    error=scene['routes']['access']['audit']['joint_error_scenario_rad']
    if error!=scene['routes']['empty_recovery']['audit']['joint_error_scenario_rad']:
        parser.error('Different archived error domains')
    package=ROOT/'cruzr_s2_description_splint/cruzr_s2_description'
    base=RobotGeometry(package/'urdf/cruzr_s2_v1/cruzr_s2_v1.urdf',package,
                       dict(frame_id='base_link',complete=True,objects=scene['scene_objects']))
    if base.manifest!=reference['model_sources']:parser.error('Model changed')
    sources=[args.reference,args.trace,args.trace_analysis,Path(__file__),Path(common.__file__),Path(common.fk.__file__),
        *[ROOT/'scripts/vla'/n for n in ('prepare_vla_entry_bundle.py','entry_local_displacement_bounds.py',
            'entry_directional_bounds.py','entry_interval_boxes.py','entry_subdivided_scene_bounds.py')],
        ROOT/'scripts/teleoperation/general_home/geometry.py',ROOT/'scripts/teleoperation/general_home/trace_analysis.py']
    hashes={str(p.resolve()):digest(p) for p in sources}
    local=LocalDisplacementBounds(SelectivePairDistances(base,common,solid_distance),common,JOINT_ORDER)
    model=SubdividedSceneBounds(DirectionalSceneBounds(local,common,JOINT_ORDER),512)
    routes={}
    for name,path in [('access',points),('empty_recovery',empty_recovery_waypoints(points))]:
        audit=certify_pairs(model,path,seconds=45,max_depth=10,joint_error_rad=error)
        routes[name]=dict(waypoints_20d_rad=[list(map(float,q)) for q in path],audit=audit)
        print(name,audit['counts'],'timeout',audit['timed_out'],flush=True)
    result=dict(scope='PASSIVE_START_PARTIAL_SCENE_AFFINE_REVIEW_ONLY',physical_approval=False,
        candidate=reference['candidate'],joint_order=JOINT_ORDER,model_sources=base.manifest,
        sources_sha256=hashes,scenarios=[dict(scene_objects=scene['scene_objects'],routes=routes)],
        scene_registration_qualified=False,stopping_qualified=False,robot_commands=0)
    if not base.source_files_unchanged() or any(digest(Path(p))!=h for p,h in hashes.items()):raise RuntimeError('Source changed')
    with args.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')


if __name__=='__main__':main()
