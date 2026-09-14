#!/usr/bin/env python3
"""Generate and review offline ENTRY360 stage drafts; no installation or transport."""
import argparse
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np

from prepare_vla_entry_bundle import ROOT, JOINT_ORDER, RobotGeometry, common, digest, certify_pairs
from general_home.geometry import solid_distance
from entry_local_displacement_bounds import LocalDisplacementBounds, SelectivePairDistances
from entry_directional_bounds import DirectionalSceneBounds
from entry_subdivided_scene_bounds import SubdividedSceneBounds

GROUPS = [
    ('head', 'single', ['head_yaw_joint', 'head_pitch_joint']),
    ('waist', 'single', ['waist_yaw_joint']),
    ('lifter', 'single', ['lifter_pitch_1_joint', 'lifter_pitch_2_joint', 'lifter_pitch_3_joint']),
    *[('arm', side, [f'{prefix}_{joint}_joint' for joint in
                     ('shoulder_pitch', 'shoulder_roll', 'shoulder_yaw', 'elbow_roll', 'elbow_yaw', 'wrist_pitch', 'wrist_roll')])
      for side, prefix in [('left', 'L'), ('right', 'R')]],
]


def staged_path(start, end):
    a, b = np.asarray(start, float), np.asarray(end, float)
    if a.shape != (20,) or b.shape != (20,) or not np.isfinite([a, b]).all():
        raise ValueError('Expected finite 20D endpoints')
    points = [a.copy()]; stages = []
    for typ, location, names in GROUPS:
        indices = [JOINT_ORDER.index(n) for n in names]
        q = points[-1].copy(); q[indices] = b[indices]
        delta = float(np.max(np.abs(q-points[-1])))
        duration = max(1, math.ceil(max(1.5*delta/.05, math.sqrt(6*delta/.05))))
        stages.append(dict(type=typ, location=location, joint_names=names,
                           joint_angles_rad=q[indices].tolist(), duration_seconds=duration,
                           peak_velocity_rad_s=1.5*delta/duration,
                           peak_acceleration_rad_s2=6*delta/duration**2,
                           start_20d_rad=points[-1].tolist(), end_20d_rad=q.tolist()))
        points.append(q)
    if not np.array_equal(points[-1], b):
        raise ValueError('Incomplete group mapping')
    return points, stages


def stage_xml(stage, reverse=False):
    root = ET.Element('root', main_tree_to_execute='MainTree')
    root.append(ET.Comment('OFFLINE DRAFT ONLY. Runtime mapping, settling, tracking and stopping remain unqualified.'))
    bt = ET.SubElement(root, 'BehaviorTree', ID='MainTree')
    angles = ([stage['start_20d_rad'][JOINT_ORDER.index(n)] for n in stage['joint_names']]
              if reverse else stage['joint_angles_rad'])
    ET.SubElement(bt, 'Action', ID='MetaMove', type=stage['type'], location=stage['location'],
                  duration=str(stage['duration_seconds']), joint_angles='; '.join(format(v, '.17g') for v in angles))
    ET.indent(root)
    return ET.tostring(root, encoding='unicode')+'\n'


def check_runtime_limits(contract, runtime_hashes, points, stages, error):
    expected = {n for typ, _, names in GROUPS if typ != 'arm' for n in names}
    if set(contract['limits']) != expected or not np.isfinite(error) or error < 0:
        raise ValueError('Expected all six body/head limits and a finite error domain')
    for suffix in ('/manipulation_platforms/config/cruzr_s2_robot_description.yaml',
                   '/manipulation_platforms/config/urdf/cruzr_s2.urdf'):
        observed = [(p, h) for p, h in runtime_hashes.items() if p.endswith(suffix)]
        if len(observed) != 1:
            raise ValueError('Missing current runtime file hash')
        path, value = observed[0]
        archived = [h for p, h in contract['source_sha256'].items() if p.endswith('/runtime'+path)]
        if archived != [value]:
            raise ValueError('Current runtime configuration differs from reviewed source')
    rows = {}
    for name, limits in contract['limits'].items():
        i = JOINT_ORDER.index(name)
        lo, hi = np.asarray(points)[:, i].min()-error, np.asarray(points)[:, i].max()+error
        allowed = limits['position_intersection_rad']
        if lo < allowed[0] or hi > allowed[1]:
            raise ValueError(f'Planned error domain exceeds configured position limits: {name}')
        stage = next(s for s in stages if name in s['joint_names'])
        if (stage['peak_velocity_rad_s'] > limits['minimum_positive_configured_velocity_rad_s']
                or stage['peak_acceleration_rad_s2'] > limits['yaml_acceleration_rad_s2']):
            raise ValueError(f'Proposal exceeds configured dynamic limits: {name}')
        rows[name] = dict(planned_interval_with_error_rad=[float(lo), float(hi)], configured_interval_rad=allowed)
    return dict(configuration_files_match_current_hashes=True, checked_joints=rows,
                loaded_configuration_verified=False, physical_tracking_or_stopping_verified=False,
                scope='Six body/head axes; arm limits remain those of the geometric model')


def main(expected_candidate='episode_000360'):
    parser = argparse.ArgumentParser(description='Prepare offline stages for '+expected_candidate+'; no execution transport.')
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--runtime-contract', type=Path, required=True)
    parser.add_argument('--runtime-hashes', type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error('Choose a new directory')
    reference = json.loads(args.reference.read_text())
    if expected_candidate not in ('episode_000360', 'episode_000410'):
        parser.error('Unsupported candidate')
    if reference['candidate'] != expected_candidate or reference['joint_order'] != JOINT_ORDER or len(reference['scenarios']) != 1:
        parser.error('Expected exact reference for '+expected_candidate)
    scene = reference['scenarios'][0]
    original = scene['routes']['access']['waypoints_20d_rad']
    if len(original) != 3:
        parser.error('Expected measured-start, READY, ENTRY360')
    points, stages = staged_path(original[1], original[2])
    error = scene['routes']['access']['audit']['joint_error_scenario_rad']
    runtime_hashes = {}
    for line in args.runtime_hashes.read_text().splitlines():
        value, path = line.split(maxsplit=1)
        if path in runtime_hashes or len(value) != 64:
            parser.error('Invalid runtime hash listing')
        runtime_hashes[path] = value
    configured_limits = check_runtime_limits(json.loads(args.runtime_contract.read_text()), runtime_hashes,
                                            points, stages, error)
    package = ROOT/'cruzr_s2_description_splint/cruzr_s2_description'
    base = RobotGeometry(package/'urdf/cruzr_s2_v1/cruzr_s2_v1.urdf', package,
                         dict(frame_id='base_link', complete=True, objects=scene['scene_objects']))
    if base.manifest != reference['model_sources']:
        parser.error('Model changed')
    files = [args.reference, args.runtime_contract, args.runtime_hashes, Path(__file__), Path(common.__file__), Path(common.fk.__file__),
             *[ROOT/'scripts/vla'/n for n in ('prepare_vla_entry_bundle.py', 'entry_local_displacement_bounds.py',
                 'entry_directional_bounds.py', 'entry_interval_boxes.py', 'entry_subdivided_scene_bounds.py')],
             *sorted((ROOT/'scripts/teleoperation/general_home').glob('*.py'))]
    if expected_candidate == 'episode_000410':
        files.append(ROOT/'scripts/vla/prepare_entry410_stages.py')
    hashes = {str(p.resolve()): digest(p) for p in files}
    local = LocalDisplacementBounds(SelectivePairDistances(base, common, solid_distance), common, JOINT_ORDER)
    model = SubdividedSceneBounds(DirectionalSceneBounds(local, common, JOINT_ORDER), 512)
    audit = certify_pairs(model, points, seconds=60, max_depth=10, joint_error_rad=error)
    result = dict(schema='cruzr-entry'+expected_candidate[-3:]+'-stages-offline-v1', candidate=expected_candidate,
                  status='DRAFT_NOT_APPROVED_FOR_INSTALLATION_OR_MOVEMENT', physical_approval=False,
                  robot_transport=False, installable=False, joint_order=JOINT_ORDER, stages=stages,
                  nominal_one_way_seconds=sum(s['duration_seconds'] for s in stages),
                  access_waypoints_20d_rad=[q.tolist() for q in points],
                  return_waypoints_20d_rad=[q.tolist() for q in points[::-1]],
                  geometry_audit=audit, reverse_uses_identical_geometric_segments=True,
                  configured_limits_check=configured_limits,
                  initial_HOME_to_READY_included=False, final_READY_to_HOME_included=False,
                  group_joint_order_runtime_verified=False, model_sources=base.manifest,
                  stages_require_fresh_measured_full_state_and_settled_endpoint=True,
                  endpoint_settling_and_stopping_limits_qualified=False, sources_sha256=hashes)
    if not base.source_files_unchanged() or any(digest(Path(p)) != h for p, h in hashes.items()):
        raise RuntimeError('Source changed')
    args.output_dir.mkdir(parents=True)
    for i, stage in enumerate(stages):
        for direction in ('forward', 'reverse'):
            (args.output_dir/f'DRAFT_{i+1:02d}_{stage["type"]}_{stage["location"]}_{direction}.xml').write_text(stage_xml(stage, direction == 'reverse'))
    result['drafts_sha256'] = {p.name: digest(p) for p in sorted(args.output_dir.glob('*.xml'))}
    (args.output_dir/'review.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(status=result['status'], nominal_one_way_seconds=result['nominal_one_way_seconds'],
                         counts=audit['counts'], timed_out=audit['timed_out']), indent=2))


if __name__ == '__main__':
    main()
