#!/usr/bin/env python3
"""Prove separation of CAD boundaries in finite domains, not material volumes."""
import argparse
import json
from pathlib import Path
import time

import fcl
import numpy as np

from prepare_vla_entry_bundle import ROOT, RobotGeometry, common, JOINT_ORDER, digest
from audit_home_interfaces import boundary_object, query_boundary
from audit_home_interface_sweeps import relative_pose
from entry_relative_kinematics import RelativeChain


def prove_boundary_box(query, lower, upper, weights, *, seconds=10., max_nodes=16384):
    lower,upper,weights=(np.asarray(x,float) for x in (lower,upper,weights))
    if (lower.ndim!=1 or upper.shape!=lower.shape or weights.shape!=lower.shape
            or not np.isfinite([lower,upper,weights]).all() or (lower>upper).any()
            or (weights<0).any() or seconds<=0 or not np.isfinite(seconds) or max_nodes<1):
        raise ValueError('Invalid boundary proof inputs')
    pending=[(lower,upper)];nodes=0;minimum=float('inf');deadline=time.monotonic()+seconds
    while pending:
        if nodes>=max_nodes or time.monotonic()>=deadline:
            return dict(proved=False,nodes=nodes,reason='BUDGET_EXHAUSTED',lower_bound_m=0.)
        lo,hi=pending.pop();center=(lo+hi)/2;half=(hi-lo)/2
        distance=float(query(center));nodes+=1
        if not np.isfinite(distance) or distance<0:raise ValueError('Invalid boundary distance')
        if distance<=1e-7:
            return dict(proved=False,nodes=nodes,reason='BOUNDARY_NOT_SEPARATED_AT_SAMPLE',
                        joint_values_rad=center.tolist(),lower_bound_m=0.)
        bound=distance-float(weights@half)-1e-7
        if bound>0:
            minimum=min(minimum,bound);continue
        axis=int(np.argmax(weights*half))
        if half[axis]<=1e-14:
            return dict(proved=False,nodes=nodes,reason='RESOLUTION_EXHAUSTED',lower_bound_m=0.)
        left_hi=hi.copy();left_hi[axis]=center[axis]
        right_lo=lo.copy();right_lo[axis]=center[axis]
        pending.extend(((right_lo,hi),(lo,left_hi)))
    return dict(proved=True,nodes=nodes,reason='ALL_BOUNDARY_BOXES_SEPARATED',lower_bound_m=minimum)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--interfaces',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--only-pending-from',type=Path)
    parser.add_argument('--seconds-per-pair',type=float,default=10.)
    parser.add_argument('--max-nodes',type=int,default=16384)
    parser.add_argument('--relative-chain',action='store_true',help='Equivalent relative FK, offline query optimization')
    parser.add_argument('--distance-only',action='store_true',help='Direct FCL surface distance; nonpositive values remain unproved')
    args=parser.parse_args()
    if args.output.exists():parser.error('Choose a new output')
    if not np.isfinite(args.seconds_per_pair) or not 0<args.seconds_per_pair<=180 or not 1<=args.max_nodes<=262144:
        parser.error('Invalid proof budget')
    previous=json.loads(args.interfaces.read_text())
    pending=None
    if args.only_pending_from:
        prior=json.loads(args.only_pending_from.read_text())
        if prior['source_sha256'].get(str(args.interfaces.resolve()))!=digest(args.interfaces):
            parser.error('Prior proof used different interfaces')
        pending={tuple(r['pair']) for r in prior['interfaces'] if not r['proved']}
    package=ROOT/'cruzr_s2_description_splint/cruzr_s2_description'
    model=RobotGeometry(package/'urdf/cruzr_s2_v1/cruzr_s2_v1.urdf',package,
                        dict(frame_id='base_link',complete=True,objects=[]))
    if model.manifest!=previous['model_sources']:parser.error('Model changed')
    sources=[args.interfaces,Path(__file__),ROOT/'scripts/vla/entry_relative_kinematics.py',ROOT/'scripts/teleoperation/audit_home_interfaces.py',
             ROOT/'scripts/teleoperation/audit_home_interface_sweeps.py',
             Path(common.__file__),Path(common.fk.__file__),Path(common.internal.__file__),
             *sorted((ROOT/'scripts/teleoperation/general_home').glob('*.py'))]
    hashes={str(p.resolve()):digest(p) for p in sources}
    if args.only_pending_from:
        hashes[str(args.only_pending_from.resolve())]=digest(args.only_pending_from)
    results=[]
    for row in previous['interfaces']:
        if not row['controlling_joints'] or row['surface_intersection_samples']:continue
        if pending is not None and tuple(row['pair']) not in pending:continue
        index=model.labels.index(row['pair']);a,b=[model.shapes[i] for i in model.pairs[index]]
        axes=[JOINT_ORDER.index(n) for n in row['controlling_joints']]
        weights=common.pair_radii(model.joints,a.link,a.source_mesh.bounds,b.link,b.source_mesh.bounds)
        weights=np.asarray(weights)[axes]
        object_a,object_b=boundary_object(a.source_mesh),boundary_object(b.source_mesh)
        chain=RelativeChain(model.joints,a.link,b.link,common.fk) if args.relative_chain else None
        def query(values):
            q=np.zeros(20);q[axes]=values
            pose=(chain.evaluate(dict(model.auxiliary,**dict(zip(JOINT_ORDER,q)))) if chain
                  else relative_pose(model,q,a,b))
            object_b.setTransform(fcl.Transform(pose[:3,:3],pose[:3,3]))
            if args.distance_only:
                distance=float(fcl.distance(object_a,object_b,fcl.DistanceRequest(),fcl.DistanceResult()))
                if not np.isfinite(distance):raise ValueError('Nonfinite FCL distance')
                return max(0.,distance)
            return query_boundary(object_a,object_b,contact_limit=1)['boundary_distance_m']
        started=time.monotonic()
        result=prove_boundary_box(query,row['domain_lower_rad'],row['domain_upper_rad'],weights,
                                 seconds=args.seconds_per_pair,max_nodes=args.max_nodes)
        result.update(pair=row['pair'],controlling_joints=row['controlling_joints'],
                      elapsed_seconds=time.monotonic()-started,volume_separation_proved=False,
                      physical_approval=False,margin_2mm_proved=False)
        results.append(result);print(json.dumps(result),flush=True)
    if not model.source_files_unchanged() or any(digest(Path(p))!=h for p,h in hashes.items()):
        raise RuntimeError('Sources changed')
    result=dict(scope='SOURCE_CAD_BOUNDARIES_ONLY_NOT_VOLUMES_OR_PHYSICAL_APPROVAL',
                physical_approval=False,interfaces=results,source_sha256=hashes,model_sources=model.manifest,
                seconds_per_pair=args.seconds_per_pair,max_nodes=args.max_nodes,
                relative_chain_used=args.relative_chain,distance_only_used=args.distance_only)
    with args.output.open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')


if __name__=='__main__':main()
