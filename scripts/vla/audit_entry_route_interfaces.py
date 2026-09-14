#!/usr/bin/env python3
"""Classify archived ENTRY interface flags without suppressing collision pairs."""
import argparse
import itertools
import json
import math
from pathlib import Path
import time

import fcl
import numpy as np

from prepare_vla_entry_bundle import ROOT, RobotGeometry, common, JOINT_ORDER, digest
from cruzr_pico_to_home_owner_gate import PICO_VARIANTS
from audit_home_interfaces import boundary_object, query_boundary
from audit_home_interface_sweeps import (reference_overlap_box, outside_all_boxes,
                                        relative_pose, validated_surface_contacts)


def interface_domain(path, axes, lower, upper, error_rad):
    path = np.asarray(path, float)
    if (path.ndim != 2 or path.shape[1] != len(lower) or not np.isfinite(path).all()
            or not math.isfinite(error_rad) or error_rad < 0):
        raise ValueError('Invalid route/error')
    if (path < lower).any() or (path > upper).any(): raise ValueError('Route outside limits')
    return (np.maximum(path.min(axis=0)[axes]-error_rad, np.asarray(lower)[axes]),
            np.minimum(path.max(axis=0)[axes]+error_rad, np.asarray(upper)[axes]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--steps', type=int, default=9)
    args = parser.parse_args()
    if args.output.exists() or not 3 <= args.steps <= 17: parser.error('Choose new output and 3..17 steps')
    started = time.monotonic()
    review = json.loads(args.review.read_text())
    if len(review['scenarios']) != 1 or review['joint_order'] != JOINT_ORDER:
        parser.error('Expected one scene and canonical joint order')
    route = review['scenarios'][0]['routes']['access']
    recovery = review['scenarios'][0]['routes']['empty_recovery']
    path = np.array(route['waypoints_20d_rad']+recovery['waypoints_20d_rad'])
    error = route['audit']['joint_error_scenario_rad']
    if error != recovery['audit']['joint_error_scenario_rad']: parser.error('Error scenario mismatch')
    package = ROOT/'cruzr_s2_description_splint/cruzr_s2_description'
    model = RobotGeometry(package/'urdf/cruzr_s2_v1/cruzr_s2_v1.urdf', package,
                          dict(frame_id='base_link', complete=True, objects=[]))
    if model.manifest != review['model_sources']: parser.error('Reviewed model differs')
    sources = [args.review, Path(__file__), ROOT/'scripts/vla/prepare_vla_entry_bundle.py',
               ROOT/'scripts/teleoperation/audit_home_interfaces.py',
               ROOT/'scripts/teleoperation/audit_home_interface_sweeps.py',
               ROOT/'scripts/teleoperation/cruzr_pico_to_home_owner_gate.py',
               Path(common.__file__), Path(common.fk.__file__), Path(common.internal.__file__),
               *sorted((ROOT/'scripts/teleoperation/general_home').glob('*.py'))]
    hashes = {str(p.resolve()):digest(p) for p in sources}
    flags = [r for r in route['audit']['pairs'] if r['status']=='MODEL_MARGIN_VIOLATION']
    refs = {'HOME':np.zeros(20), **{k:np.asarray(v) for k,v in PICO_VARIANTS.items()}}
    results = []
    for flag in flags:
        index = model.labels.index(flag['pair']); details = model.pair_details[index]
        a, b = [model.shapes[i] for i in model.pairs[index]]
        axes = [JOINT_ORDER.index(n) for n in details['controlling_joints']]
        row = dict(pair=flag['pair'], **details, physical_approval=False,
                   exemption_authorized=False, contains_clamp=any('hand_link' in n for n in flag['pair']))
        if not axes:
            row.update(status='RELATIVE_GEOMETRY_INVARIANT_FOR_THIS_MOTION',
                       proof='no controlled joint in relative kinematic chain; base and auxiliary states fixed')
            results.append(row); continue
        if len(axes)>2: raise ValueError('Unexpected interface chain: more than two controls')
        object_a, object_b = boundary_object(a.source_mesh), boundary_object(b.source_mesh)
        reference_boxes, reference_values = [], {}
        for name, q in refs.items():
            pose = relative_pose(model, q, a, b)
            object_b.setTransform(fcl.Transform(pose[:3,:3], pose[:3,3]))
            reference_values[name] = query_boundary(object_a, object_b, contact_limit=1)
            vertices = common.fk.apply(b.source_mesh.vertices, pose)
            reference_boxes.append(reference_overlap_box(a.source_mesh.vertices, vertices))
        lo, hi = interface_domain(path, axes, model.lower, model.upper, error)
        grid = [np.unique(np.r_[np.linspace(l,h,args.steps),path[:,axis]])
                for axis,l,h in zip(axes,lo,hi)]
        intersections = 0; minimum = float('inf'); maximum = 0.; novel = None; samples = 0
        states_intersect, states_clear = None, None
        for values in itertools.product(*grid):
            q = np.zeros(20); q[axes] = values
            pose = relative_pose(model,q,a,b)
            object_b.setTransform(fcl.Transform(pose[:3,:3],pose[:3,3]))
            result = query_boundary(object_a,object_b,contact_limit=1)
            distance = result['boundary_distance_m']; minimum=min(minimum,distance); maximum=max(maximum,distance)
            samples += 1
            if result['surface_intersection']:
                intersections += 1
                if states_intersect is None: states_intersect=list(map(float,values))
                if novel is None:
                    points, stats = validated_surface_contacts(a.source_mesh,b.source_mesh,pose,
                                                               object_a,object_b,contact_limit=64)
                    outside = outside_all_boxes(points,reference_boxes)
                    if len(outside):
                        novel = dict(joint_values_rad=list(map(float,values)),
                                     point_in_first_link_m=outside[0].tolist(), frame_id=a.link,
                                     contact_stats=stats, is_physical_contact=False,
                                     scope='sample inside rectangular route/error domain; may be off affine path')
            elif states_clear is None: states_clear=list(map(float,values))
        row.update(status='MOVING_INTERFACE_SAMPLED_NOT_PHYSICALLY_QUALIFIED',
                   domain_lower_rad=lo.tolist(),domain_upper_rad=hi.tolist(),error_rad=error,
                   sampling_scope='bounding joint rectangle of both routes plus error; not a continuous proof',
                   samples=samples,surface_intersection_samples=intersections,
                   source_boundary_distance_range_m=[minimum,maximum],
                   first_intersecting_values_rad=states_intersect,first_clear_values_rad=states_clear,
                   references=reference_values,
                   novel_contact_outside_reference_boxes=novel)
        results.append(row)
        print(json.dumps({k:row[k] for k in ('pair','samples','surface_intersection_samples','source_boundary_distance_range_m')}),flush=True)
    if not model.source_files_unchanged() or any(digest(Path(p))!=h for p,h in hashes.items()):
        raise RuntimeError('Sources changed')
    report=dict(scope='ENTRY_ROUTE_INTERFACE_DIAGNOSTIC_NOT_EXEMPTION',physical_approval=False,
        candidate=review['candidate'],joint_order=JOINT_ORDER,interfaces=results,
        summary=dict(total=len(results),invariant=sum(not r['controlling_joints'] for r in results),
                     moving=sum(bool(r['controlling_joints']) for r in results),
                     contains_clamp=sum(r['contains_clamp'] for r in results),
                     novel_cad_contacts=sum(r.get('novel_contact_outside_reference_boxes') is not None for r in results)),
        source_sha256=hashes,model_sources=model.manifest,elapsed_seconds=time.monotonic()-started,
        physical_movement=0,remote_changes=0)
    with args.output.open('x') as stream:json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(report['summary']))


if __name__ == '__main__': main()
