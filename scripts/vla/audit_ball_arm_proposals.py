#!/usr/bin/env python3
"""Audit recorded SmolVLA ball arm proposals by name, without robot control.

The SDK order here is a historical reference, not a validated v4 runtime
contract. The seven model outputs are hypothetical positions; this program
never constructs or sends a RobotCommand and cannot enable physical control.
"""
import argparse
import json
import math
from pathlib import Path
import re
import sys


MODEL_SHA256 = 'e707eea07b58e14b979e78463b94ba75a52b1c18abf8076aebc8aa34ac77f8da'
MODEL_ORDER = (
    'R_shoulder_pitch_joint', 'R_shoulder_roll_joint', 'R_shoulder_yaw_joint',
    'R_elbow_roll_joint', 'R_elbow_yaw_joint', 'R_wrist_pitch_joint', 'R_wrist_roll_joint',
)
# Reference only: 20-axis ordering from the older clamp SDK transport.
HISTORICAL_SDK_RIGHT_ARM_ORDER = (
    'R_elbow_roll_joint', 'R_elbow_yaw_joint', 'R_shoulder_pitch_joint',
    'R_shoulder_roll_joint', 'R_shoulder_yaw_joint', 'R_wrist_pitch_joint', 'R_wrist_roll_joint',
)
MAX_LINE = 1024 * 1024
MAX_ROWS = 1000


def finite_vector(value, count):
    return (isinstance(value, list) and len(value) == count and
            all(type(x) in (int, float) and math.isfinite(x) for x in value))


def audit(rows):
    """Audit structured relay output. Derived observed values are historical only."""
    ready = done = summary = False
    previous_stamp = 0
    predictions = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('record is not an object')
        event = row.get('event')
        if summary:
            raise ValueError('record after summary')
        if event == 'model_ready':
            if (ready or predictions or row.get('model_sha256') != MODEL_SHA256 or
                    row.get('physical_control_qualified') is not False or
                    type(row.get('movement_commands')) is not int or row['movement_commands'] != 0):
                raise ValueError('unexpected model readiness or checkpoint')
            ready = True
        elif event == 'prediction':
            if not ready or done or len(predictions) >= MAX_ROWS:
                raise ValueError('unexpected prediction order or count')
            target, delta = row.get('prediction'), row.get('proposed_minus_observed_rad')
            if not finite_vector(target, 8) or not finite_vector(delta, 7):
                raise ValueError('prediction or differences are malformed or nonfinite')
            stamp, image = row.get('image_source_ns'), row.get('image_sha256')
            if (type(row.get('index')) is not int or row['index'] != len(predictions) or
                    type(stamp) is not int or stamp <= previous_stamp or
                    not isinstance(image, str) or not re.fullmatch(r'[0-9a-f]{64}', image) or
                    row.get('physical_control_qualified') is not False):
                raise ValueError('invalid index, image provenance, timestamp or qualification')
            previous_stamp = stamp
            per_name = {}
            for i, name in enumerate(MODEL_ORDER):
                observed = target[i] - delta[i]
                if not math.isfinite(observed):
                    raise ValueError('derived state is nonfinite')
                per_name[name] = {'model_index': i,
                                  'historical_sdk_right_arm_index': HISTORICAL_SDK_RIGHT_ARM_ORDER.index(name),
                                  'model_value_rad': target[i], 'recorded_difference_rad': delta[i],
                                  'derived_observed_rad': observed}
            predictions.append({'index': row['index'], 'image_source_ns': stamp, 'joints': per_name})
        elif event == 'done':
            if (not ready or done or not predictions or type(row.get('samples')) is not int or
                    row['samples'] != len(predictions) or row.get('physical_control_qualified') is not False):
                raise ValueError('invalid model completion')
            done = True
        elif event == 'summary':
            if (not done or type(row.get('predictions')) is not int or row['predictions'] != len(predictions) or
                    type(row.get('observations_sent')) is not int or row['observations_sent'] != len(predictions) or
                    type(row.get('observations_dropped')) is not int or row['observations_dropped'] < 0 or
                    type(row.get('movement_commands')) is not int or row['movement_commands'] != 0):
                raise ValueError('invalid relay summary')
            summary = True
        else:
            raise ValueError('unexpected event')
    if not (ready and done and summary):
        raise ValueError('incomplete relay output')
    differences = [(abs(item['recorded_difference_rad']), row['index'], name,
                    item['recorded_difference_rad'])
                   for row in predictions for name, item in row['joints'].items()]
    worst = max(differences)
    return {'schema': 'cruzr_ball_arm_audit_offline_v1', 'physical_control_qualified': False,
            'movement_commands': 0, 'model_sha256': MODEL_SHA256, 'samples': len(predictions),
            'model_order': list(MODEL_ORDER), 'historical_sdk_right_arm_order': list(HISTORICAL_SDK_RIGHT_ARM_ORDER),
            'largest_recorded_difference': {'absolute_rad': worst[0], 'sample': worst[1],
                                            'joint': worst[2], 'signed_rad': worst[3]},
            'limitations': ['recorded inference only; no current state, applied action, velocity, or stop evidence',
                            'historical SDK ordering is not a validated v4 contract',
                            'difference is not a movement, tracking error or safety bound',
                            'does not map or validate the hand output and cannot enable physical control'],
            'predictions': predictions}


def read_rows(path):
    with path.open('rb') as stream:
        for line in stream:
            if len(line) > MAX_LINE:
                raise ValueError('input line exceeds limit')
            yield json.loads(line)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', type=Path, metavar='LIVE_RUN_JSONL', help='audit recorded shadow output')
    mode.add_argument('--run', action='store_true', help='physical execution is blocked')
    args = parser.parse_args(argv)
    if args.run:
        print('BLOCKED: no physical controller, validated hand or stop path', file=sys.stderr)
        return 2
    try:
        report = audit(read_rows(args.check))
        print(json.dumps(report, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, OverflowError) as exc:
        print(f'AUDIT_FAILED: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
