#!/usr/bin/env python3
"""Explain every HOME/PICO model rejection using original boundary witnesses.

Offline only. Boundary distance does not establish solid separation; this
diagnostic never exempts a pair or authorizes movement.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time

import fcl
import numpy as np

import review_clamp_trajectory_optimization as common
from cruzr_pico_to_home_owner_gate import JOINT_ORDER,PICO_VARIANTS
from general_home.geometry import RobotGeometry
from general_home.planner import Validator
from general_home.contact_witnesses import triangle_pair_witnesses


def boundary_object(mesh):
    model=fcl.BVHModel()
    model.beginModel(len(mesh.vertices),len(mesh.faces))
    model.addSubModel(np.asarray(mesh.vertices),np.asarray(mesh.faces,dtype=np.int32))
    model.endModel()
    return fcl.CollisionObject(model)


def query_boundary(a,b,contact_limit=256,source_meshes=None):
    collision=fcl.CollisionResult()
    count=fcl.collide(a,b,fcl.CollisionRequest(num_max_contacts=contact_limit,enable_contact=True),collision)
    if count:
        positions=np.array([c.pos for c in collision.contacts],dtype=float)
        if positions.ndim!=2 or positions.shape[1]!=3 or not len(positions) or not np.isfinite(positions).all():
            raise ValueError('Invalid surface contact witnesses')
        validated=False
        if source_meshes is not None:
            if len(source_meshes)!=2:
                raise ValueError('Expected both source meshes')
            triangles=[]
            for index,(obj,mesh) in enumerate(zip((a,b),source_meshes)):
                ids=np.array([c.b1 if index==0 else c.b2 for c in collision.contacts],dtype=int)
                if (ids<0).any() or (ids>=len(mesh.faces)).any():
                    raise ValueError('Invalid source triangle index')
                triangles.append(mesh.triangles[ids]@obj.getRotation().T+obj.getTranslation())
            positions=triangle_pair_witnesses(*triangles)[:contact_limit]
            validated=True
        return dict(surface_intersection=True,boundary_distance_m=0.,
            contact_witnesses_m=positions.tolist(),contact_witness_count=len(positions),
            contact_list_may_be_truncated=len(collision.contacts)>=contact_limit or len(positions)>=contact_limit,
            witness_validated_on_both_source_triangles=validated,
            witness_tolerance_m=1e-8 if validated else None,
            witness_scope=('reconstructed proximity witnesses on both source triangles; not an overlap bound'
                if validated else 'raw FCL positions; may lie outside the actual triangle intersection; not validated'))
    distance=fcl.DistanceResult()
    value=float(fcl.distance(a,b,fcl.DistanceRequest(enable_nearest_points=True),distance))
    if not np.isfinite(value) or value<0:
        raise ValueError('Invalid original-boundary distance')
    points=np.asarray(distance.nearest_points,dtype=float)
    if points.shape!=(2,3) or not np.isfinite(points).all():
        raise ValueError('Invalid nearest-point witness')
    return dict(surface_intersection=False,boundary_distance_m=value,nearest_points_m=points.tolist(),
        witness_scope='boundary only; nesting or omitted CAD surfaces may still prevent solid separation')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--package-root',type=Path,default=Path(__file__).resolve().parents[2]/'cruzr_s2_description_splint/cruzr_s2_description')
    args=parser.parse_args()
    if args.output.exists():parser.error('Choose a new output file')
    started=time.monotonic()
    sources=[Path(__file__),*Path(__file__).with_name('general_home').glob('*.py'),
        Path(common.__file__),Path(common.fk.__file__),Path(common.internal.__file__),Path(common.pico.__file__),
        Path(__file__).with_name('cruzr_pico_to_home_owner_gate.py')]
    hashes={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    model=RobotGeometry(args.package_root/'urdf/cruzr_s2_v1/cruzr_s2_v1.urdf',args.package_root,
        dict(frame_id='base_link',complete=True,objects=[]))
    raw=[boundary_object(s.source_mesh) for s in model.shapes]
    by_name={s.name:i for i,s in enumerate(model.shapes)}
    rows={};summaries={}
    for reference,q in dict(HOME=np.zeros(20),**PICO_VARIANTS).items():
        q=np.asarray(q)
        failures=Validator(model).failures(q)
        poses=common.fk.forward_kinematics(model.joints,dict(model.auxiliary,**dict(zip(JOINT_ORDER,q))))
        for shape,obj in zip(model.shapes,raw):
            p=poses[shape.link];obj.setTransform(fcl.Transform(p[:3,:3],p[:3,3]))
        entries=[]
        for failure in failures:
            first,second=[by_name[name] for name in failure['pair']]
            boundary=query_boundary(raw[first],raw[second],source_meshes=(model.shapes[first].source_mesh,model.shapes[second].source_mesh))
            if boundary['surface_intersection']:
                cause='original_CAD_surfaces_intersect'
            elif failure['separation_lower_bound_m']==0:
                cause='derived_volume_overlap_or_containment_requires_review'
            else:
                cause='positive_separation_below_required_margin'
            item=dict(failure,**boundary,cause=cause,exemption_authorized=False)
            witnesses=boundary.get('contact_witnesses_m',boundary.get('nearest_points_m'))
            if len(failure['controlling_joints'])==1 and witnesses:
                name=failure['controlling_joints'][0]
                joint=next(j for j in model.joints if j['name']==name)
                t=poses[joint['parent']]@joint['origin']
                axis=t[:3,:3]@joint['axis'];axis/=np.linalg.norm(axis)
                points=np.array(witnesses)
                v=points-t[:3,3]
                axial=v@axis;radial=np.linalg.norm(v-axial[:,None]*axis,axis=1)
                item['joint_axis_witness']=dict(joint=name,origin_in_base_m=t[:3,3].tolist(),axis_in_base=axis.tolist(),
                    axial_min_max_m=[float(axial.min()),float(axial.max())],
                    maximum_witness_radius_m=float(radial.max()),
                    scope='witness positions only; not an allowed-contact zone or full swept bound')
            entries.append(item)
        rows[reference]=entries
        summaries[reference]=dict(rejected_pairs=len(entries),causes=dict(Counter(r['cause'] for r in entries)),
            invariant_pairs=sum(not r['controlling_joints'] for r in entries),
            moving_pairs=sum(bool(r['controlling_joints']) for r in entries))
        print(json.dumps(dict(reference=reference,summary=summaries[reference])),flush=True)
    if not model.source_files_unchanged() or any(hashlib.sha256(Path(p).read_bytes()).hexdigest()!=sha for p,sha in hashes.items()):
        raise ValueError('Sources changed during audit')
    result=dict(schema='cruzr-home-interface-audit-v1',status='DIAGNOSTIC_ONLY_NO_EXEMPTIONS',references=rows,
        summary=summaries,model=model.diagnostics,source_sha256=dict(model.manifest,**hashes),
        physical_approval=False,installable=False,movement_commands=0,remote_changes=0,
        duration_seconds=time.monotonic()-started,
        limitations=['surface clearance alone does not prove volume clearance',
            'original CAD intersections are not demonstrated physical contacts',
            'witnesses do not authorize interface exclusion or margin reduction'])
    with args.output.open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')


if __name__=='__main__':main()
