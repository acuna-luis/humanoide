#!/usr/bin/env python3
"""Time-parameterize historical arm waypoints locally. No robot/ROS transport.

This is NOT a collision planner or an executable HOME task. All non-arm joints
are unspecified, never implicitly commanded to zero. No physical approval.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

ORDER = ('elbow_roll', 'elbow_yaw', 'shoulder_pitch', 'shoulder_roll',
         'shoulder_yaw', 'wrist_pitch', 'wrist_roll')
NAMES = tuple(f'{side}_{name}_joint' for side in ('L', 'R') for name in ORDER)


def positive(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError('limit_must_be_finite_positive_number')
    return value


def vector(value):
    if (not isinstance(value, list) or len(value) != 14 or
            any(type(x) not in (int, float) or not math.isfinite(x) for x in value)):
        raise ValueError('expected_14_finite_named_arm_values')
    return value


def segment(start, end, vmax, amax):
    vector(start)
    vector(end)
    positive(vmax)
    positive(amax)
    delta = [b-a for a, b in zip(start, end)]
    if not all(math.isfinite(d) for d in delta):
        raise ValueError('displacement_overflow')
    distance = max(map(abs, delta))
    # s(u)=10u^3-15u^4+6u^5. max s'=15/8, max |s''|=10/sqrt(3).
    duration = max(1.875*distance/vmax, math.sqrt((10/math.sqrt(3))*distance/amax), .001)
    duration *= 1.000001  # numerical reserve, NOT geometric or runtime margin
    if not math.isfinite(duration):
        raise ValueError('duration_overflow')
    return dict(start_rad=start, end_rad=end, duration_s=duration,
                max_velocity_rad_s=1.875*distance/duration,
                max_acceleration_rad_s2=(10/math.sqrt(3))*distance/duration**2)


def evaluate(seg, u):
    if type(u) not in (int, float) or not math.isfinite(u) or not 0 <= u <= 1:
        raise ValueError('invalid_normalized_time')
    s = u**3*(10+u*(-15+6*u))
    ds = 30*u*u*(1-u)**2
    dds = 60*u*(1-u)*(1-2*u)
    t = seg['duration_s']
    delta = [b-a for a, b in zip(seg['start_rad'], seg['end_rad'])]
    return ([a+s*d for a, d in zip(seg['start_rad'], delta)],
            [ds*d/t for d in delta], [dds*d/t**2 for d in delta])


def build(source, vmax=.15, amax=.5, direction='return'):
    if direction not in ('return', 'outbound'):
        raise ValueError('unsupported_direction')
    positive(vmax)
    positive(amax)
    path = source['arm_path_checkpoint_order']
    points = [(name, vector(path[name])) for name in
              ('ready_b', 'waypoint_a', 'staging_preposition')]
    points.append(('synthetic_arm_zero_NOT_verified_HOME', [0.0]*14))
    if direction == 'outbound':
        points.reverse()
    segments = []
    for (name, start), (target, end) in zip(points, points[1:]):
        segments.append(dict(segment(start, end, vmax, amax), source=name, target=target))
    return dict(schema='offline-home-timing-candidate-v1',
                status='HISTORICAL_ARM_TIMING_ONLY_NOT_COLLISION_VALIDATED',
                joint_names=NAMES, segments=segments,
                direction=direction,
                total_duration_s=sum(s['duration_s'] for s in segments),
                interpolation='quintic_smoothstep_stop_at_each_waypoint',
                formula='q=q0+(q1-q0)*(10*u^3-15*u^4+6*u^5); u=t/T',
                provisional_limits=dict(velocity_rad_s=vmax, acceleration_rad_s2=amax),
                initial_state_source='historical_P14_NOT_current_robot_state',
                non_arm_state=None, non_arm_policy='UNSPECIFIED_NOT_ZERO_NOT_COMMANDABLE',
                collision_validated=False, runtime_equivalence_verified=False,
                boot_home_interception_verified=False, physical_authorized=False,
                executable=False, robot_connections=0, movement_commands=0,
                limitations=['not_a_path_search_or_obstacle_avoidance_algorithm',
                             'historical_waypoints_not_proven_collision_free',
                             'no_current_20D_state_or_scene',
                             'no_position_limit_or_full_geometry_validation',
                             'no_tracking_braking_force_or_jerk_limit_validation',
                             'no_runtime_export_XML_ROS_or_vendor_execution'])


def check_position_limits(candidate, urdf_text):
    """Continuous position bounds for THIS monotone curve, not collision bounds."""
    joints = {}
    for joint in ET.fromstring(urdf_text).findall('joint'):
        name = joint.get('name')
        if name in joints:
            raise ValueError('duplicate_URDF_joint')
        joints[name] = joint
    if candidate['interpolation'] != 'quintic_smoothstep_stop_at_each_waypoint':
        raise ValueError('unsupported_interpolation')
    if tuple(candidate['joint_names']) != NAMES:
        raise ValueError('unexpected_joint_mapping')
    bounds, violations, missing = {}, [], []
    for name in NAMES:
        joint = joints.get(name)
        limit = None if joint is None else joint.find('limit')
        if joint is None or joint.get('type') != 'revolute' or limit is None:
            missing.append(name)
            continue
        try:
            low, high = float(limit.attrib['lower']), float(limit.attrib['upper'])
        except (KeyError, ValueError):
            missing.append(name)
            continue
        if not math.isfinite(low) or not math.isfinite(high) or low >= high:
            missing.append(name)
            continue
        bounds[name] = [low, high]
    for i, seg in enumerate(candidate['segments']):
        for endpoint in ('start_rad', 'end_rad'):
            for name, q in zip(NAMES, vector(seg[endpoint])):
                if name in bounds:
                    low, high = bounds[name]
                    if not low <= q <= high:
                        violations.append(dict(segment=i, endpoint=endpoint, joint=name,
                                               position_rad=q, bounds_rad=[low, high]))
    return dict(status='URDF_POSITION_BOUNDS_PASS_ONLY' if not missing and not violations
                else 'URDF_POSITION_BOUNDS_REJECTED', missing_or_invalid_limits=missing,
                violations=violations, bounds_rad=bounds,
                basis='s_prime=30*u^2*(1-u)^2>=0; every joint stays between endpoints',
                installed_runtime_limits_verified=False, collision_validated=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--historical-contract', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--urdf', type=Path, required=True)
    parser.add_argument('--direction', choices=('return', 'outbound'), default='return')
    args = parser.parse_args()
    data = args.historical_contract.read_bytes()
    result = build(json.loads(data), direction=args.direction)
    urdf = args.urdf.read_bytes()
    result['position_check'] = check_position_limits(result, urdf)
    result['source_sha256'] = {str(args.historical_contract): hashlib.sha256(data).hexdigest(),
                               str(Path(__file__)): hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    result['source_sha256'][str(args.urdf)] = hashlib.sha256(urdf).hexdigest()
    with args.output.open('x') as out:
        json.dump(result, out, indent=2, allow_nan=False)
        out.write('\n')
    print(json.dumps({'status': result['status'], 'total_duration_s': result['total_duration_s'],
                      'segment_durations_s': [s['duration_s'] for s in result['segments']],
                      'position_check': result['position_check']['status'],
                      'physical_authorized': False}))
    return 0 if result['position_check']['status'] == 'URDF_POSITION_BOUNDS_PASS_ONLY' else 3


if __name__ == '__main__':
    raise SystemExit(main())
