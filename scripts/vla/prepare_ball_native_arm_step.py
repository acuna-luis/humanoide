#!/usr/bin/env python3
"""Draft right-arm MetaMove steps from recorded or live SmolVLA shadow output.

The result is an offline JSON review, not an installed task or a robot command.
The seven-value MetaMove ordering and all limits remain unqualified on this
robot. No ROS, network, task installation, or physical execution is provided.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import time
import xml.etree.ElementTree as ET
import yaml

from audit_ball_arm_proposals import MODEL_ORDER, MODEL_SHA256, audit, finite_vector, read_rows
from ball_arm_preview_guard import named_values
import prepare_pico_wrist_native_probe as probe


def positive(value, label):
    if type(value) not in (float, int) or not math.isfinite(value) or value <= 0:
        raise ValueError(label + ' must be a finite positive number')
    return float(value)


def draft_joints(joints, index, image_source_ns, max_step_rad, duration_s, source):
    """Clip each model difference, then draft a single right-arm XML task.

    Limits and duration are explicitly supplied experimental parameters. They
    do not certify dynamics, collisions, control handoff, stopping or freshness.
    Clipping changes the model's target and can change its task behavior.
    """
    max_step = positive(max_step_rad, 'max_step_rad')
    duration = positive(duration_s, 'duration_s')
    details = []
    for name in MODEL_ORDER:
        joint = joints[name]
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
        'model_sha256': MODEL_SHA256,
        'sample_index': index,
        'image_source_ns': image_source_ns,
        'input_source': source,
        'joint_order_hypothesis': list(MODEL_ORDER),
        'max_step_rad_experimental': max_step,
        'duration_s_experimental': duration,
        'joints': details,
        'candidate_xml': ET.tostring(root, encoding='unicode'),
        # Static analysis of the installed json_args branch indicates this
        # shape; neither the blackboard handoff nor robot execution is proven.
        'candidate_dynamic_task': {
            'task_name': 'move_components_json',
            'yaml_args_hypothesis': {
                'component_names': ['right_arm'],
                'goals': [[j['candidate_target_rad'] for j in details]],
                'mode': 0,
                'durations': [duration],
            },
        },
        'physical_control_qualified': False,
        'candidate_actions': 1,
        'physical_commands_sent': 0,
        'limitations': [
            'relay observation only; no current state, source-to-receipt latency or physical synchronization is established',
            'native MetaMove seven-axis ordering and mapping have not been validated for this hardware',
            'max step and duration are experimental inputs, not robot safety limits',
            'clipping alters the model action and does not establish task success',
            'no joint, velocity, acceleration, collision, task registration or stopping qualification',
            'dynamic task argument handoff, path planner, runtime configuration and physical stop are not verified',
            'no hand action, ROS communication, task installation or execution is performed',
        ],
    }


def draft(rows, index, max_step_rad, duration_s):
    report = audit(rows)
    if type(index) is not int or not 0 <= index < report['samples']:
        raise ValueError('sample index outside recorded shadow')
    row = report['predictions'][index]
    result = draft_joints(row['joints'], index, row['image_source_ns'],
                          max_step_rad, duration_s, 'recorded_shadow')
    # Preserve the original report fields for the documented offline interface.
    result['recorded_sample_index'] = index
    result['recorded_image_source_ns'] = row['image_source_ns']
    return result


def checked_live_step(row, max_step_rad, duration_s, *, urdf_text, transmissions_text,
                      max_state_age_ns, max_prediction_age_ns, min_sps_margin_rad, now_ns):
    """Review one paired live prediction against supplied nominal configuration.

    The timestamps must be from the same PC monotonic clock. Receipt time does
    not measure Vision-to-PC delay and cannot prove that the source is fresh.
    Reject excessive deltas; do not silently clip them. This is not a motion
    plan, controller handoff, collision/stop check or physical authorization.
    A live supervisor must recheck state before dispatch; the hand is untouched.
    """
    max_step = positive(max_step_rad, 'max_step_rad')
    duration = positive(duration_s, 'duration_s')
    if (type(now_ns) is not int or now_ns <= 0 or
            any(type(age) is not int or age <= 0 for age in (max_state_age_ns, max_prediction_age_ns))):
        raise ValueError('invalid_pc_monotonic_time_or_age')
    if (type(min_sps_margin_rad) not in (int, float) or
            not math.isfinite(min_sps_margin_rad) or min_sps_margin_rad < 0):
        raise ValueError('invalid_supplied_sps_margin')
    if not isinstance(urdf_text, str) or not isinstance(transmissions_text, str):
        raise ValueError('nominal_configuration_required')
    if tuple(MODEL_ORDER) != tuple(probe.ARM):
        raise ValueError('model_native_arm_order_mismatch')
    state = row.get('paired_state20')
    if not isinstance(state, dict):
        raise ValueError('paired_state20_required')
    state_stamp, prediction_stamp = state.get('received_monotonic_ns'), row.get('prediction_received_monotonic_ns')
    if (type(state_stamp) is not int or type(prediction_stamp) is not int or
            not 0 < state_stamp <= prediction_stamp <= now_ns or
            now_ns-state_stamp > max_state_age_ns or now_ns-prediction_stamp > max_prediction_age_ns):
        raise ValueError('pc_receipt_stale_future_or_out_of_order')
    measured = named_values(state.get('names'), state.get('positions'), state.get('velocities'))
    msg = {'name': state['names'], 'position': state['positions'], 'velocity': state['velocities']}
    # Existing PICO/v4 named reference, SPS and stationary checks; a receipt
    # is only one sample, not sustained stationarity or physical clearance.
    initial = probe.check_body(msg)
    values, differences = row.get('prediction'), row.get('proposed_minus_observed_rad')
    if not finite_vector(values, 8) or not finite_vector(differences, 7):
        raise ValueError('prediction_or_difference_invalid')
    joints = {}
    for i, name in enumerate(MODEL_ORDER):
        observed = measured[name][0]
        if not math.isclose(values[i]-observed, differences[i], rel_tol=1e-6, abs_tol=1e-6):
            raise ValueError('prediction_observation_mismatch:' + name)
        if abs(values[i]-observed) > max_step:
            raise ValueError('prediction_step_exceeds_supplied_limit:' + name)
        joints[name] = {'derived_observed_rad': observed, 'model_value_rad': values[i]}
    target = [values[i] for i in range(7)]
    urdf_limits = probe.nominal_arm_limits(urdf_text, initial, target, duration_s=duration)
    sps_limits = probe.hardware_endpoints(transmissions_text, initial, target)
    for name, detail in sps_limits.items():
        if detail['minimum_endpoint_margin_rad'] < min_sps_margin_rad:
            raise ValueError('sps_endpoint_margin_below_supplied_threshold:' + name)
    result = draft_joints(joints, row['index'], row['image_source_ns'], max_step, duration,
                          'paired_live_shadow_nominal_check')
    result['nominal_endpoint_check'] = {
        'urdf_sha256': hashlib.sha256(urdf_text.encode('utf-8')).hexdigest(),
        'transmissions_sha256': hashlib.sha256(transmissions_text.encode('utf-8')).hexdigest(),
        'arm_urdf': urdf_limits, 'body_sps': sps_limits,
        'minimum_sps_margin_supplied_rad': min_sps_margin_rad,
        'state_age_pc_ns': now_ns-state_stamp, 'prediction_age_pc_ns': now_ns-prediction_stamp,
    }
    result['limitations'].append('nominal endpoints and PC receipt age do not establish source freshness, trajectory, collision, force, or physical stopping')
    return result


class LivePreview:
    """Validate the actual relay lifecycle and emit drafts without dispatch."""

    def __init__(self, max_step_rad, duration_s, *, nominal=None):
        self.max_step = positive(max_step_rad, 'max_step_rad')
        self.duration = positive(duration_s, 'duration_s')
        self.nominal = nominal
        self.ready = self.done = self.summary = False
        self.count = self.last_stamp = 0

    def accept(self, row):
        if not isinstance(row, dict) or self.summary:
            raise ValueError('unexpected relay record')
        event = row.get('event')
        if event == 'model_ready':
            if (self.ready or row.get('model_sha256') != MODEL_SHA256 or
                    row.get('physical_control_qualified') is not False or
                    type(row.get('movement_commands')) is not int or row['movement_commands'] != 0):
                raise ValueError('model readiness or checkpoint mismatch')
            self.ready = True
            return {'event': 'native_preview_ready', 'model_sha256': MODEL_SHA256,
                    'physical_control_qualified': False, 'physical_commands_sent': 0}
        if event == 'prediction':
            if not self.ready or self.done or self.count >= 1000:
                raise ValueError('unexpected prediction')
            values, differences = row.get('prediction'), row.get('proposed_minus_observed_rad')
            stamp, digest = row.get('image_source_ns'), row.get('image_sha256')
            if (not finite_vector(values, 8) or not finite_vector(differences, 7) or
                    type(row.get('index')) is not int or row['index'] != self.count or
                    type(stamp) is not int or stamp <= self.last_stamp or
                    not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest) or
                    row.get('physical_control_qualified') is not False):
                raise ValueError('invalid prediction, provenance or sequence')
            joints = {name: {'model_value_rad': values[i],
                             'derived_observed_rad': values[i] - differences[i]}
                      for i, name in enumerate(MODEL_ORDER)}
            if self.nominal is None:
                result = draft_joints(joints, self.count, stamp, self.max_step,
                                      self.duration, 'live_shadow_relay')
            else:
                result = checked_live_step(row, self.max_step, self.duration,
                                           now_ns=time.monotonic_ns(), **self.nominal)
            result['event'] = 'native_step_preview'
            result['image_sha256'] = digest
            result['hand_scalar_uninterpreted'] = values[7]
            self.last_stamp = stamp
            self.count += 1
            return result
        if event == 'done':
            if (not self.ready or self.done or not self.count or
                    type(row.get('samples')) is not int or row['samples'] != self.count or
                    row.get('physical_control_qualified') is not False):
                raise ValueError('invalid model completion')
            self.done = True
            return None
        if event == 'summary':
            if (not self.done or type(row.get('predictions')) is not int or row['predictions'] != self.count or
                    type(row.get('observations_sent')) is not int or row['observations_sent'] != self.count or
                    type(row.get('observations_dropped')) is not int or row['observations_dropped'] < 0 or
                    type(row.get('movement_commands')) is not int or row['movement_commands'] != 0):
                raise ValueError('invalid relay summary')
            self.summary = True
            return {'event': 'native_preview_done', 'samples': self.count,
                    'physical_control_qualified': False, 'physical_commands_sent': 0}
        raise ValueError('unexpected relay event')

    def finish(self):
        if not self.summary:
            raise ValueError('incomplete relay stream')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', type=Path, metavar='SHADOW_JSONL', help='review recorded shadow output')
    mode.add_argument('--stream', action='store_true', help='review live shadow JSONL from stdin')
    mode.add_argument('--run', action='store_true', help='physical execution is blocked')
    parser.add_argument('--sample', type=int, default=0)
    parser.add_argument('--max-step-rad', type=float)
    parser.add_argument('--duration-s', type=float)
    parser.add_argument('--urdf', type=Path, help='optional nominal URDF for paired stream check')
    parser.add_argument('--transmissions', type=Path, help='optional nominal SPS transmissions for paired stream check')
    parser.add_argument('--max-state-age-ns', type=int, help='caller-supplied PC receipt age limit')
    parser.add_argument('--max-prediction-age-ns', type=int, help='caller-supplied PC prediction age limit')
    parser.add_argument('--min-sps-margin-rad', type=float, help='caller-supplied endpoint diagnostic margin')
    args = parser.parse_args(argv)
    if args.run:
        print('BLOCKED: native arm mapping, trajectory and physical stopping remain unqualified', file=sys.stderr)
        return 2
    try:
        if args.stream:
            if args.sample != 0:
                raise ValueError('--sample is only supported with --check')
            optional = (args.urdf, args.transmissions, args.max_state_age_ns,
                        args.max_prediction_age_ns, args.min_sps_margin_rad)
            nominal = None
            if any(value is not None for value in optional):
                if any(value is None for value in optional):
                    raise ValueError('complete_nominal_configuration_required')
                nominal = {'urdf_text':args.urdf.read_bytes().decode('utf-8'),
                           'transmissions_text':args.transmissions.read_bytes().decode('utf-8'),
                           'max_state_age_ns':args.max_state_age_ns,
                           'max_prediction_age_ns':args.max_prediction_age_ns,
                           'min_sps_margin_rad':args.min_sps_margin_rad}
            preview = LivePreview(args.max_step_rad, args.duration_s, nominal=nominal)
            for raw in iter(lambda: sys.stdin.buffer.readline(1024 * 1024 + 1), b''):
                if len(raw) > 1024 * 1024 or not raw.endswith(b'\n'):
                    raise ValueError('relay line too long or incomplete')
                result = preview.accept(json.loads(raw))
                if result is not None:
                    print(json.dumps(result, separators=(',', ':'), allow_nan=False), flush=True)
            preview.finish()
        else:
            if any(value is not None for value in (args.urdf, args.transmissions, args.max_state_age_ns,
                                                    args.max_prediction_age_ns, args.min_sps_margin_rad)):
                raise ValueError('nominal_check_only_supported_with_stream')
            result = draft(read_rows(args.check), args.sample, args.max_step_rad, args.duration_s)
            print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, OverflowError, yaml.YAMLError) as exc:
        print('DRAFT_ERROR: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
