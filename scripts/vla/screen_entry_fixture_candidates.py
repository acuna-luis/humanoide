#!/usr/bin/env python3
"""Compare archived task-0 entries against one exact fixture scenario, offline."""
import argparse
import json
import math
from pathlib import Path

import numpy as np

from prepare_vla_entry_bundle import ROOT, RobotGeometry, common, JOINT_ORDER, digest, certify_pairs, empty_recovery_waypoints
from general_home.geometry import solid_distance
from entry_local_displacement_bounds import LocalDisplacementBounds, SelectivePairDistances
from entry_directional_bounds import DirectionalSceneBounds
from entry_subdivided_scene_bounds import SubdividedSceneBounds
import rank_vla_entry_postures as ranking


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('dataset-report','review','output'):
        parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('Output must be new')
    contract_path=ROOT/'scripts/vla/runtime/cruzr_s2_vla_task0_entry_e6_1a.json'
    contract=json.loads(contract_path.read_text())
    if digest(args.dataset_report)!=contract['candidate']['dataset_entry_report_sha256']:
        parser.error('Dataset archive hash changed')
    records=ranking.validate_records(json.loads(args.dataset_report.read_text()),contract)
    review=json.loads(args.review.read_text())
    if review['joint_order']!=JOINT_ORDER or len(review['scenarios'])!=1:parser.error('Unexpected scenario')
    scenario=review['scenarios'][0]
    package=ROOT/'cruzr_s2_description_splint/cruzr_s2_description'
    model=RobotGeometry(package/'urdf/cruzr_s2_v1/cruzr_s2_v1.urdf',package,
                        dict(frame_id='base_link',complete=True,objects=scenario['scene_objects']))
    if model.manifest!=review['model_sources']:parser.error('Model changed')
    sources=[args.dataset_report,args.review,contract_path,Path(__file__),Path(ranking.__file__),Path(common.__file__),Path(common.fk.__file__),
             ROOT/'scripts/teleoperation/general_home/geometry.py',
             *[ROOT/'scripts/vla'/n for n in ('prepare_vla_entry_bundle.py','entry_local_displacement_bounds.py',
                 'entry_directional_bounds.py','entry_interval_boxes.py','entry_subdivided_scene_bounds.py')]]
    hashes={str(p.resolve()):digest(p) for p in sources}
    local=LocalDisplacementBounds(SelectivePairDistances(model,common,solid_distance),common,JOINT_ORDER)
    scene_indices=[i for i,(_,b) in enumerate(model.pairs) if b>=model.robot_count]
    rows=[]
    for r in records:
        if r['task']!=0:continue
        q=np.asarray(r['state']);tilt,_=ranking.torso_metrics(model.joints,dict(zip(JOINT_ORDER,q)))
        if tilt>5 or (q<model.lower).any() or (q>model.upper).any():continue
        d=local.selected_distances(q,scene_indices)
        rows.append(dict(episode=r['episode'],state=r['state'],torso_tilt_deg=tilt,
                         minimum_nominal_scene_lower_bound_m=float(min(d)),scene_flags=int(np.sum(d<=.002000001))))
    rows.sort(key=lambda r:r['minimum_nominal_scene_lower_bound_m'],reverse=True)
    print('UPRIGHT_ENDPOINTS',len(rows),'TOP',[(r['episode'],r['minimum_nominal_scene_lower_bound_m']) for r in rows[:3]],flush=True)
    routes=[]
    for row in rows[:3]:
        if row['scene_flags']:continue
        points=[*scenario['routes']['access']['waypoints_20d_rad'][:2],row['state']]
        bounded=SubdividedSceneBounds(DirectionalSceneBounds(local,common,JOINT_ORDER),512)
        access=certify_pairs(bounded,points,seconds=45,max_depth=10,joint_error_rad=math.radians(1))
        item=dict(episode=row['episode'],waypoints_20d_rad=points,access=access)
        print(row['episode'],'access',access['counts'],flush=True)
        if access['counts'].get('UNRESOLVED',0)==0:
            recovery=empty_recovery_waypoints(points)
            item['empty_recovery_waypoints_20d_rad']=[p.tolist() for p in recovery]
            item['empty_recovery']=certify_pairs(bounded,recovery,seconds=45,max_depth=10,joint_error_rad=math.radians(1))
            print(row['episode'],'recovery',item['empty_recovery']['counts'],flush=True)
        routes.append(item)
        # A diagnostic alternative still retains every internal nominal flag.
        if (not access['timed_out'] and access['counts'].get('UNRESOLVED',0)==0
                and access['counts'].get('MODEL_MARGIN_VIOLATION',0)<=54
                and item.get('empty_recovery',{}).get('counts',{}).get('UNRESOLVED',1)==0):break
    result=dict(scope='DATASET_ALTERNATIVE_SCREEN_ONLY',physical_approval=False,fixture_registration_qualified=False,
                height_and_image_compatibility_verified=False,shadow_compatibility_verified=False,
                stopping_or_execution_verified=False,model_sources=model.manifest,sources_sha256=hashes,
                ranked_upright_endpoints=rows,route_reviews=routes)
    if not model.source_files_unchanged() or any(digest(Path(p))!=h for p,h in hashes.items()):raise RuntimeError('Sources changed')
    with args.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')


if __name__=='__main__':main()
