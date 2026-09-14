#!/usr/bin/env python3
"""Prepare a bounded replay of one recorded VLA point. No robot transport."""
import argparse
import json
from pathlib import Path

from prepare_home_ready_access import measured_named_start
from review_entry_from_passive_state import (
    ROOT, JOINT_ORDER, RobotGeometry, common, digest, certify_pairs,
    solid_distance, LocalDisplacementBounds, SelectivePairDistances,
    DirectionalSceneBounds, SubdividedSceneBounds,
)
from runtime.cruzr_s2_vla_sdk_transport import plan_minimum_jerk


def select_point(rows, start, names, arm_names):
    """Pick the least-displacing accepted recorded first point, without clipping."""
    choices = []
    for row in rows:
        if row.get('accepted') is not True or row.get('reasons'):
            continue
        proposed = row['metrics']['first_point_positions']
        target = [float(proposed[n]) if n in arm_names else q
                  for n, q in zip(names, start, strict=True)]
        import math
        if not all(math.isfinite(q) for q in target):
            raise ValueError('Nonfinite proposal')
        delta = max(abs(a-b) for a, b in zip(start, target, strict=True))
        if 0 < delta <= .1:
            choices.append((delta, row['chunk_id'], target))
    if not choices:
        raise ValueError('No accepted unmodified first point within 0.1 rad')
    return min(choices, key=lambda item: (item[0], item[1]))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('capture', 'shadow-log', 'reference', 'output-dir'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--fraction', type=float, choices=(.25, .5, 1.), default=1.,
                   help='Fraction of bridge toward the unchanged recorded first point')
    a = p.parse_args()
    a.output_dir.mkdir(parents=True, exist_ok=False)
    start = measured_named_start(json.loads(a.capture.read_text()))
    reference = json.loads(a.reference.read_text())
    if reference['joint_order'] != JOINT_ORDER or len(reference['scenarios']) != 1:
        raise ValueError('Unexpected scene reference')
    profile_path = ROOT/'scripts/vla/runtime/cruzr_s2_vla_profile.json'
    profile = json.loads(profile_path.read_text())
    arms = profile['commanded_joint_names']
    if len(arms) != 14 or set(arms) != set(JOINT_ORDER[:14]):
        raise ValueError('Unexpected arm mapping')
    rows = [json.loads(line) for line in a.shadow_log.read_text().splitlines()]
    delta, chunk, source_target = select_point(rows, start, JOINT_ORDER, arms)
    target = [q+(end-q)*a.fraction for q, end in zip(start, source_target)]
    limits_path = ROOT/'scripts/vla/runtime/cruzr_s2_vla_canary_engineering_limits_e6_0s.json'
    limits = json.loads(limits_path.read_text())
    # Slower local commissioning envelope; unchanged 0.1 rad target bound.
    limits.update(maximum_velocity_rad_s=[.05]*14,
                  maximum_acceleration_rad_s2=[.1]*14,
                  minimum_transition_duration_seconds=4.,
                  maximum_transition_duration_seconds=4.)
    q0, q1 = dict(zip(JOINT_ORDER, start)), dict(zip(JOINT_ORDER, target))
    trajectory = plan_minimum_jerk([q0[n] for n in arms], [q1[n] for n in arms], limits)
    scene = reference['scenarios'][0]
    package = ROOT/'cruzr_s2_description_splint/cruzr_s2_description'
    base = RobotGeometry(package/'urdf/cruzr_s2_v1/cruzr_s2_v1.urdf', package,
                         dict(frame_id='base_link', complete=True, objects=scene['scene_objects']))
    if base.manifest != reference['model_sources']:
        raise ValueError('Changed geometry')
    local = LocalDisplacementBounds(SelectivePairDistances(base, common, solid_distance), common, JOINT_ORDER)
    model = SubdividedSceneBounds(DirectionalSceneBounds(local, common, JOINT_ORDER), 512)
    error = scene['routes']['access']['audit']['joint_error_scenario_rad']
    audit = certify_pairs(model, [start, target], seconds=60, max_depth=10, joint_error_rad=error)
    # Preserve every internal warning; report which also existed in the reference.
    historical = {tuple(pair['pair']) for pair in scene['routes']['access']['audit']['pairs']
                  if pair['status'] == 'MODEL_MARGIN_VIOLATION'}
    failures = [pair for pair in audit['pairs'] if pair['status'] != 'CERTIFIED_AFFINE_INTERVALS']
    new_failures = [pair for pair in failures if tuple(pair['pair']) not in historical
                    or any(n.startswith('scene:') for n in pair['pair'])
                    or pair['status'] != 'MODEL_MARGIN_VIOLATION']
    sources = [a.capture, a.shadow_log, a.reference, profile_path, limits_path,
               *sorted((ROOT/'scripts/vla').glob('*.py')),
               *sorted((ROOT/'scripts/vla/runtime').glob('*.py')),
               *sorted((ROOT/'scripts/teleoperation/general_home').glob('*.py'))]
    result = dict(schema='cruzr-entry410-recorded-vla-point-review-v1',
                  mode='recorded_first_point_replay_not_live_policy',
                  source_chunk_id=chunk, source_point_index=0,
                  source_target=source_target, bridge_fraction=a.fraction,
                  joint_order=JOINT_ORDER, arm_names=arms, start=start, target=target,
                  maximum_target_delta_rad=delta*a.fraction, duration_seconds=4.,
                  trajectory=trajectory, engineering_limits=limits,
                  geometry_audit=audit, new_or_scene_failures=new_failures,
                  historical_internal_warning_count=len(failures)-len(new_failures),
                  scene_objects=scene['scene_objects'], model_sources=base.manifest,
                  sources_sha256={str(f.resolve()): digest(f) for f in sources},
                  no_new_geometric_failures=not new_failures and not audit['timed_out'],
                  physical_approval=False, robot_commands=0)
    (a.output_dir/'review.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k: result[k] for k in ('source_chunk_id', 'maximum_target_delta_rad',
        'duration_seconds', 'historical_internal_warning_count', 'no_new_geometric_failures')}))
    print(json.dumps(audit['counts']))


if __name__ == '__main__':
    main()
