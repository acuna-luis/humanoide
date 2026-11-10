#!/usr/bin/env python3
"""Review one seven-axis ball proposal; offline only, never controls a robot.

Limits are *inputs*, not defaults or certified physical parameters. This
module neither claims they are valid for the hardware nor produces trajectory
frames, ROS messages, publishers, services or any physical authorization.
"""

import argparse
import json
import math
from pathlib import Path
import sys

from audit_ball_arm_proposals import MODEL_ORDER

# Names only, matching the versioned 20D observation profile. No clamp-profile
# numerical limits or kinematic claims are imported for the v4 hands.
BODY_NAMES = tuple(f'{side}_{joint}_joint' for side in ('L', 'R') for joint in (
    'elbow_roll', 'elbow_yaw', 'shoulder_pitch', 'shoulder_roll', 'shoulder_yaw',
    'wrist_pitch', 'wrist_roll')) + (
        'head_pitch_joint', 'head_yaw_joint', 'lifter_pitch_1_joint',
        'lifter_pitch_2_joint', 'lifter_pitch_3_joint', 'waist_yaw_joint')


def number(value, label):
    if type(value) not in (float, int) or not math.isfinite(value):
        raise ValueError(label + ': expected a finite number')
    return float(value)


def positive(value, label):
    value = number(value, label)
    if value <= 0:
        raise ValueError(label + ': expected a positive number')
    return value


def stamp(value, label):
    if type(value) is not int or value < 0:
        raise ValueError(label + ': expected a nonnegative integer nanosecond stamp')
    return value


def named_values(names, positions, velocities):
    if (not isinstance(names, list) or len(names) != 20 or
            any(not isinstance(n, str) or not n for n in names) or len(set(names)) != 20 or
            not isinstance(positions, list) or len(positions) != 20 or
            not isinstance(velocities, list) or len(velocities) != 20 or
            set(names) != set(BODY_NAMES)):
        raise ValueError('state: expected the exact 20 body names, positions and velocities')
    return {name: (number(pos, name + ':position'), number(vel, name + ':velocity'))
            for name, pos, vel in zip(names, positions, velocities, strict=True)}


def review(state, proposal, policy, now_ns):
    """Review provided numbers in one clock domain; never authorizes motion.

    Duration bounds use a hypothetical rest-to-rest minimum-jerk interpolant:
    max |dq/dt| = 1.875 |dq|/T and max |d2q/dt2| = 10/sqrt(3) |dq|/T².
    These are mathematical bounds, not a trajectory or an actuator guarantee.
    """
    if not all(isinstance(x, dict) for x in (state, proposal, policy)):
        raise ValueError('state, proposal and policy must be objects')
    now = stamp(now_ns, 'now_ns')
    state_time = stamp(state.get('received_monotonic_ns'), 'state timestamp')
    proposal_time = stamp(proposal.get('received_monotonic_ns'), 'proposal timestamp')
    state_age = stamp(policy.get('max_state_age_ns'), 'max state age')
    proposal_age = stamp(policy.get('max_proposal_age_ns'), 'max proposal age')
    if not state_age or not proposal_age:
        raise ValueError('age limits must be positive')
    duration = positive(policy.get('preview_duration_seconds'), 'preview duration')
    measured = named_values(state.get('names'), state.get('positions'), state.get('velocities'))
    if proposal.get('names') != list(MODEL_ORDER):
        raise ValueError('proposal: unexpected model axis names or order')
    values = proposal.get('positions')
    if not isinstance(values, list) or len(values) != 7:
        raise ValueError('proposal: expected exactly seven positions')
    candidate = [number(v, 'proposal position') for v in values]
    limits = policy.get('joint_limits')
    if not isinstance(limits, dict) or set(limits) != set(MODEL_ORDER):
        raise ValueError('policy: explicitly provide all and only seven joint limits')

    reasons = []
    if state_time > now or now - state_time > state_age:
        reasons.append('state_timestamp_future_or_stale')
    if proposal_time > now or now - proposal_time > proposal_age:
        reasons.append('proposal_timestamp_future_or_stale')
    details = []
    for name, target in zip(MODEL_ORDER, candidate, strict=True):
        row = limits[name]
        if not isinstance(row, dict):
            raise ValueError(name + ': limit must be an object')
        lo = number(row.get('min_position_rad'), name + ':minimum')
        hi = number(row.get('max_position_rad'), name + ':maximum')
        if not lo < hi:
            raise ValueError(name + ': minimum must be below maximum')
        max_delta = positive(row.get('max_delta_rad'), name + ':max delta')
        max_velocity = positive(row.get('max_velocity_rad_s'), name + ':max velocity')
        max_accel = positive(row.get('max_acceleration_rad_s2'), name + ':max acceleration')
        stationary = positive(row.get('stationary_velocity_rad_s'), name + ':stationary velocity')
        pos, vel = measured[name]
        delta = target - pos
        if not math.isfinite(delta):
            raise ValueError(name + ': nonfinite difference')
        if not lo <= pos <= hi:
            reasons.append(name + ':state_outside_limits')
        if not lo <= target <= hi:
            reasons.append(name + ':proposal_outside_limits')
        if abs(vel) > stationary:
            reasons.append(name + ':state_not_stationary')
        if abs(delta) > max_delta:
            reasons.append(name + ':delta_exceeds_limit')
        try:
            # Compute minimum required time first, avoiding duration underflow.
            min_time = max(1.875 * abs(delta) / max_velocity,
                           math.sqrt((10.0 / math.sqrt(3.0)) * abs(delta) / max_accel))
        except (OverflowError, ZeroDivisionError) as exc:
            raise ValueError(name + ': invalid duration calculation') from exc
        if not math.isfinite(min_time):
            raise ValueError(name + ': nonfinite minimum time')
        if duration < min_time:
            reasons.append(name + ':duration_below_mathematical_bound')
        details.append({'name': name, 'observed_rad': pos, 'proposal_rad': target,
                        'difference_rad': delta, 'minimum_hypothetical_duration_s': min_time})
    return {'schema': 'cruzr_ball_arm_preview_guard_v1',
            'diagnostic_passed': not reasons, 'reasons': reasons, 'joints': details,
            'physical_control_qualified': False, 'physical_commands_generated': 0,
            'limitations': ['externally supplied limits are not qualified or checked against hardware',
                            'timestamps must use one monotonic clock; no clock calibration is performed',
                            'stationarity is checked for the seven right arm axes only, not the other 13',
                            'no collision, stopping, hand, scene, controller or trajectory validation',
                            'no trajectory is produced; this result cannot authorize motion']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True,
                        help='offline JSON with state, proposal, policy and now_ns')
    args = parser.parse_args(argv)
    try:
        with args.input.open(encoding='utf-8') as source:
            value = json.load(source)
        result = review(value['state'], value['proposal'], value['policy'], value['now_ns'])
        print(json.dumps(result, allow_nan=False, indent=2))
        return 0 if result['diagnostic_passed'] else 1
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as exc:
        print('PREVIEW_ERROR: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
