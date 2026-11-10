#!/usr/bin/env python3
"""Draft one right-arm MetaMove from recorded SmolVLA shadow output.

The result is an offline JSON review, not an installed task or a robot command.
The seven-value MetaMove ordering and all limits remain unqualified on this
robot. No ROS, network, task installation, or physical execution is provided.
"""
import argparse
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from audit_ball_arm_proposals import MODEL_ORDER, audit, read_rows


def positive(value, label):
    if type(value) not in (float, int) or not math.isfinite(value) or value <= 0:
        raise ValueError(label + ' must be a finite positive number')
    return float(value)


def draft(rows, index, max_step_rad, duration_s):
    """Clip each model difference, then draft a single right-arm XML task.

    Limits and duration are explicitly supplied experimental parameters. They
    do not certify dynamics, collisions, control handoff, stopping or freshness.
    Clipping changes the model's target and can change its task behavior.
    """
    max_step = positive(max_step_rad, 'max_step_rad')
    duration = positive(duration_s, 'duration_s')
    report = audit(rows)
    if type(index) is not int or not 0 <= index < report['samples']:
        raise ValueError('sample index outside recorded shadow')
    row = report['predictions'][index]
    details = []
    for name in MODEL_ORDER:
        joint = row['joints'][name]
        observed = joint['derived_observed_rad']
        model = joint['model_value_rad']
        delta = model - observed
        step = max(-max_step, min(max_step, delta))
        candidate = observed + step
        if not all(math.isfinite(x) for x in (observed, model, delta, step, candidate)):
            raise ValueError('nonfinite derived arm value: ' + name)
        details.append({'name': name, 'recorded_state_rad': observed,
                        'model_target_rad': model, 'clipped_step_rad': step,
                        'candidate_target_rad': candidate})

    root = ET.Element('root', {'main_tree_to_execute': 'MainTree'})
    tree = ET.SubElement(root, 'BehaviorTree', {'ID': 'MainTree'})
    sequence = ET.SubElement(tree, 'Sequence', {'name': 'root_sequence'})
    sequence.append(ET.Comment('OFFLINE DRAFT: NOT QUALIFIED FOR ROBOT EXECUTION'))
    ET.SubElement(sequence, 'Action', {
        'ID': 'MetaMove', 'type': 'arm', 'location': 'right',
        'joint_angles': ';'.join(format(j['candidate_target_rad'], '.12g') for j in details),
        'duration': format(duration, '.12g'),
    })
    return {
        'schema': 'cruzr_ball_native_right_arm_draft_v1',
        'model_sha256': report['model_sha256'],
        'recorded_sample_index': index,
        'recorded_image_source_ns': row['image_source_ns'],
        'joint_order_hypothesis': list(MODEL_ORDER),
        'max_step_rad_experimental': max_step,
        'duration_s_experimental': duration,
        'joints': details,
        'candidate_xml': ET.tostring(root, encoding='unicode'),
        'physical_control_qualified': False,
        'candidate_actions': 1,
        'physical_commands_sent': 0,
        'limitations': [
            'recorded input only; no live state, age or physical synchronization is established',
            'native MetaMove seven-axis ordering and mapping have not been validated for this hardware',
            'max step and duration are experimental inputs, not robot safety limits',
            'clipping alters the model action and does not establish task success',
            'no joint, velocity, acceleration, collision, task registration or stopping qualification',
            'no hand action, ROS communication, task installation or execution is performed',
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', type=Path, metavar='SHADOW_JSONL', help='review recorded shadow output')
    mode.add_argument('--run', action='store_true', help='physical execution is blocked')
    parser.add_argument('--sample', type=int, default=0)
    parser.add_argument('--max-step-rad', type=float)
    parser.add_argument('--duration-s', type=float)
    args = parser.parse_args(argv)
    if args.run:
        print('BLOCKED: native arm mapping, trajectory and physical stopping remain unqualified', file=sys.stderr)
        return 2
    try:
        result = draft(read_rows(args.check), args.sample, args.max_step_rad, args.duration_s)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as exc:
        print('DRAFT_ERROR: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
