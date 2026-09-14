#!/usr/bin/env python3
"""Access/recovery sensitivity to unqualified fixture fits. Offline only."""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np

from prepare_vla_entry_bundle import ROOT, RobotGeometry, JOINT_ORDER, common, certify_pairs, empty_recovery_waypoints
from general_home.geometry import solid_distance
from entry_local_displacement_bounds import LocalDisplacementBounds, SelectivePairDistances
from refine_entry_pair_distances import RefinedPairDistances
from entry_directional_bounds import DirectionalSceneBounds
from entry_subdivided_scene_bounds import SubdividedSceneBounds


def padded_objects(objects, padding_mm):
    if not math.isfinite(padding_mm) or padding_mm < 0:
        raise ValueError('Invalid exploratory padding')
    result = copy.deepcopy(objects)
    for obj in result:
        size = np.asarray(obj['size_m'], float)
        if size.shape != (3,) or not np.isfinite(size).all() or (size <= 0).any():
            raise ValueError('Invalid fixture size')
        obj['size_m'] = (size + 2*padding_mm/1000).tolist()
    return result


def profile_padding(profile):
    if (profile.get('schema') != 'cruzr-entry-scene-uncertainty-review-v1'
            or profile.get('scope') != 'OFFLINE_HYPOTHESIS_NOT_EXECUTION_CONFIGURATION'
            or profile.get('physical_approval') is not False
            or profile.get('uncertainty_bound_qualified') is not False
            or profile.get('minimum_geometric_clearance_mm') != 2.):
        raise ValueError('Unsupported or execution-qualified scene hypothesis')
    value=profile.get('scene_translation_allowance_mm')
    if type(value) not in (int,float) or not math.isfinite(value) or value<0:
        raise ValueError('Invalid scene translation allowance')
    return [float(value)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('fixture-fit', 'access-review', 'measured-joints', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--directional-bounds', action='store_true')
    parser.add_argument('--uncertainty-partition-nodes', type=int, default=0)
    parser.add_argument('--padding-mm', type=float, nargs='+')
    parser.add_argument('--scene-uncertainty-profile', type=Path)
    args = parser.parse_args()
    if args.output.exists(): parser.error('Output must be new')
    profile=None
    if args.scene_uncertainty_profile:
        if args.padding_mm is not None: parser.error('Choose a profile or explicit padding, not both')
        profile=json.loads(args.scene_uncertainty_profile.read_text())
        args.padding_mm=profile_padding(profile)
    elif args.padding_mm is None: args.padding_mm=[0.,20.,50.]
    if not 0 <= args.uncertainty_partition_nodes <= 4096:
        parser.error('Invalid partition budget')
    if args.uncertainty_partition_nodes and not args.directional_bounds:
        parser.error('Partition requires directional bounds')
    if any(not math.isfinite(x) or x < 0 for x in args.padding_mm): parser.error('Invalid padding')
    fit = json.loads(args.fixture_fit.read_text()); archived = json.loads(args.access_review.read_text())
    measured = json.loads(args.measured_joints.read_text())
    if len(set(measured['name'])) != len(measured['name']): parser.error('Duplicate measured joint')
    named = dict(zip(measured['name'], measured['position'], strict=True))
    velocity = dict(zip(measured['name'], measured['velocity'], strict=True))
    if not set(JOINT_ORDER) <= set(named): parser.error('Missing measured joint')
    start = [named[n] for n in JOINT_ORDER]
    if not np.isfinite([velocity[n] for n in JOINT_ORDER]).all() or any(abs(velocity[n]) > .001 for n in JOINT_ORDER):
        parser.error('Archived measurement not stationary')
    route = archived['routes']['via_ready']
    if route['joint_order'] != JOINT_ORDER or len(route['waypoints_20d_rad']) != 3:
        parser.error('Unexpected route')
    for name, expected in archived['model_sources'].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != expected: parser.error('Model changed')
    path = [start, *route['waypoints_20d_rad'][1:]]
    paths = dict(access=path, empty_recovery=empty_recovery_waypoints(path))
    sources = [args.fixture_fit, args.access_review, args.measured_joints, Path(__file__),
        *[ROOT/'scripts/vla'/n for n in ('prepare_vla_entry_bundle.py', 'entry_local_displacement_bounds.py',
                                       'entry_interval_boxes.py', 'refine_entry_pair_distances.py', 'entry_directional_bounds.py',
                                       'entry_subdivided_scene_bounds.py')],
        ROOT/'scripts/teleoperation/general_home/geometry.py']
    hashes = {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    if args.scene_uncertainty_profile:
        hashes[str(args.scene_uncertainty_profile.resolve())]=hashlib.sha256(args.scene_uncertainty_profile.read_bytes()).hexdigest()
    package = ROOT/'cruzr_s2_description_splint/cruzr_s2_description'
    scenarios = []
    for padding in args.padding_mm:
        objects = padded_objects([r['scene_object'] for r in fit['objects']], padding)
        base = RobotGeometry(package/'urdf/cruzr_s2_v1/cruzr_s2_v1.urdf', package,
            dict(frame_id='base_link', complete=True, objects=objects))
        model = LocalDisplacementBounds(SelectivePairDistances(base, common, solid_distance), common, JOINT_ORDER)
        if args.directional_bounds: model = DirectionalSceneBounds(model, common, JOINT_ORDER)
        if args.uncertainty_partition_nodes:
            model = SubdividedSceneBounds(model, args.uncertainty_partition_nodes)
        row = dict(padding_mm=padding, padding_is_not_verified_error_bound=True,
                   angular_registration_error_bounded=False, scene_objects=objects, routes={})
        for name, points in paths.items():
            started = time.monotonic()
            audit = certify_pairs(model, points, seconds=45, max_depth=10, joint_error_rad=math.radians(1))
            pending = [i for i, r in enumerate(audit['pairs']) if r['status'] == 'UNRESOLVED']
            if pending and not audit['timed_out']:
                selective = SelectivePairDistances(base, common, solid_distance)
                refined = LocalDisplacementBounds(RefinedPairDistances(selective, pending, solid_distance), common, JOINT_ORDER)
                if args.directional_bounds: refined = DirectionalSceneBounds(refined, common, JOINT_ORDER)
                if args.uncertainty_partition_nodes:
                    refined = SubdividedSceneBounds(refined, args.uncertainty_partition_nodes)
                audit = certify_pairs(refined, points, seconds=45, max_depth=10, joint_error_rad=math.radians(1))
            row['routes'][name] = dict(waypoints_20d_rad=[list(map(float, p)) for p in points],
                audit=audit, elapsed_seconds=time.monotonic()-started)
            print(padding, name, audit['counts'], 'timeout', audit['timed_out'], flush=True)
        scenarios.append(row)
        if not base.source_files_unchanged(): raise RuntimeError('Model changed during review')
    if any(hashlib.sha256(Path(p).read_bytes()).hexdigest() != h for p, h in hashes.items()):
        raise RuntimeError('Sources changed during review')
    result = dict(scope='UNQUALIFIED_FIXTURE_HYPOTHESES_ACCESS_AND_EMPTY_RECOVERY_ONLY',
        physical_approval=False, fixture_registration_qualified=False, scene_complete=False,
        dynamics_or_stopping_validated=False, candidate=archived['selected_candidate'],
        directional_bounds_used=args.directional_bounds,
        uncertainty_partition_nodes=args.uncertainty_partition_nodes,
        scene_uncertainty_profile=profile,
        joint_order=JOINT_ORDER, scenarios=scenarios, sources_sha256=hashes, model_sources=base.manifest)
    with args.output.open('x') as f: json.dump(result, f, indent=2); f.write('\n')


if __name__ == '__main__': main()
