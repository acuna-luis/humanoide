#!/usr/bin/env python3
"""Build a non-executable geometric preview of one SmolVLA arm proposal.

All limits and timestamps are external inputs; none is qualified here.  This
program creates no ROS messages, publishers, or controller transitions.  Its
output is not a motion plan and must never be sent to a robot.
"""

import argparse
import json
import math
from pathlib import Path
import sys

from audit_ball_arm_proposals import MODEL_ORDER
from ball_arm_preview_guard import BODY_NAMES, named_values, positive, review


def preview(value):
    if not isinstance(value, dict):
        raise ValueError('input must be an object')
    state = value['state']
    proposal = value['proposal']
    policy = value['policy']
    result = review(state, proposal, policy, value['now_ns'])
    count = value.get('sample_count')
    if type(count) is not int or not 2 <= count <= 1001:
        raise ValueError('sample_count must be an integer between 2 and 1001')
    stationary = positive(value.get('locked_stationary_velocity_rad_s'),
                          'locked stationary velocity')
    measured = named_values(state['names'], state['positions'], state['velocities'])
    reasons = list(result['reasons'])
    for name in BODY_NAMES:
        if name not in MODEL_ORDER and abs(measured[name][1]) > stationary:
            reasons.append(name + ':locked_state_not_stationary')

    output = {
        'schema': 'cruzr_ball_arm_trajectory_preview_v1',
        'preview_generated': False,
        'physical_control_qualified': False,
        'physical_commands_generated': 0,
        'reasons': reasons,
        'joint_names': list(BODY_NAMES),
        'samples': [],
        'limitations': [
            'not an executable trajectory and no physical control is authorized',
            'caller-supplied limits and timestamps are not qualified against the robot',
            'no calibration, collision, perception, controller or stop validation',
            'continuous collision and tracking are not established by finite samples',
            'same-clock freshness is assumed, never measured across machines',
        ],
    }
    if reasons:
        return output

    duration = positive(policy['preview_duration_seconds'], 'preview duration')
    targets = dict(zip(MODEL_ORDER, proposal['positions'], strict=True))
    # A common scalar interpolation preserves the coupled joint-space segment.
    # Locked axes remain at the observed state; this is only a geometric model.
    for index in range(count):
        u = index / (count - 1)
        blend = u**3 * (10.0 + u * (-15.0 + 6.0 * u))
        positions = []
        for name in BODY_NAMES:
            start = measured[name][0]
            target = targets.get(name, start)
            pos = start + (target - start) * blend
            if not math.isfinite(pos):
                raise ValueError(name + ': nonfinite preview position')
            positions.append(pos)
        output['samples'].append({'relative_time_s': duration * u,
                                  'positions_rad': positions})
    output['preview_generated'] = True
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True,
                        help='offline JSON; output is printed to stdout only')
    args = parser.parse_args(argv)
    try:
        with args.input.open(encoding='utf-8') as stream:
            result = preview(json.load(stream))
        print(json.dumps(result, allow_nan=False, indent=2))
        return 0 if result['preview_generated'] else 1
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as exc:
        print('PREVIEW_ERROR: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
