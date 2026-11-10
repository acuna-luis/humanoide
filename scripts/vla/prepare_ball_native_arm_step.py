#!/usr/bin/env python3
"""Draft right-arm MetaMove steps from recorded or live SmolVLA shadow output.

The result is an offline JSON review, not an installed task or a robot command.
The seven-value MetaMove ordering and all limits remain unqualified on this
robot. No ROS, network, task installation, or physical execution is provided.
"""
import argparse
import ctypes
import errno
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
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


def model_wrist_candidate(row, *, urdf_text, transmissions_text, max_state_age_ns,
                          max_prediction_age_ns, min_sps_margin_rad, now_ns,
                          verified_model_sha256):
    """Prepare the existing +0.01 rad wrist probe from one model prediction.

    This deliberately discards the other six arm targets and the hand value;
    it is a one-axis clipped model action, not the policy's complete action or
    evidence of the grasp task. The positive model delta must be at least the
    fixed probe step: smaller or negative deltas are rejected, never amplified
    or reversed. PC receipt ages do not measure Vision-to-PC latency. Nothing
    here dispatches or authorizes physical VLA control.
    """
    if tuple(MODEL_ORDER) != tuple(probe.ARM) or MODEL_ORDER[-1] != probe.ARM_AXIS:
        raise ValueError('model_native_arm_order_mismatch')
    if (verified_model_sha256 != MODEL_SHA256 or not isinstance(row, dict) or
            row.get('event') != 'prediction' or row.get('physical_control_qualified') is not False):
        raise ValueError('model_wrist_checkpoint_or_prediction_invalid')
    if (type(now_ns) is not int or now_ns <= 0 or
            any(type(age) is not int or age <= 0 for age in
                (max_state_age_ns, max_prediction_age_ns))):
        raise ValueError('invalid_pc_monotonic_time_or_age')
    if (type(min_sps_margin_rad) not in (float, int) or
            not math.isfinite(min_sps_margin_rad) or min_sps_margin_rad < 0):
        raise ValueError('invalid_supplied_sps_margin')
    state = row.get('paired_state20')
    if not isinstance(state, dict):
        raise ValueError('paired_state20_required')
    stamp, prediction_stamp = state.get('received_monotonic_ns'), row.get('prediction_received_monotonic_ns')
    if (type(stamp) is not int or type(prediction_stamp) is not int or
            not 0 < stamp <= prediction_stamp <= now_ns or
            now_ns-stamp > max_state_age_ns or now_ns-prediction_stamp > max_prediction_age_ns):
        raise ValueError('pc_receipt_stale_future_or_out_of_order')
    measured = named_values(state.get('names'), state.get('positions'), state.get('velocities'))
    values, differences = row.get('prediction'), row.get('proposed_minus_observed_rad')
    if not finite_vector(values, 8) or not finite_vector(differences, 7):
        raise ValueError('prediction_or_difference_invalid')
    if (type(row.get('index')) is not int or row['index'] != 0 or
            type(row.get('image_source_ns')) is not int or row['image_source_ns'] <= 0 or
            not isinstance(row.get('image_sha256'), str) or
            not re.fullmatch('[0-9a-f]{64}', row['image_sha256'])):
        raise ValueError('model_wrist_prediction_identity_invalid')
    for i, name in enumerate(MODEL_ORDER):
        if not math.isclose(values[i]-measured[name][0], differences[i], rel_tol=1e-6, abs_tol=1e-6):
            raise ValueError('prediction_observation_mismatch:' + name)
    if values[6]-measured[probe.ARM_AXIS][0] < probe.ARM_STEP:
        raise ValueError('model_wrist_delta_not_compatible_with_positive_probe')
    message = {'name': state['names'], 'position': state['positions'], 'velocity': state['velocities']}
    # Reuse the exact preparer/validator consumed by the existing one-wrist
    # supervisor, rather than altering its fixed envelope or manifest schema.
    manifest = probe.prepare(message, urdf_text, transmissions_text)
    probe.validate(manifest, urdf_text, transmissions_text)
    for name, details in manifest['nominal_sps_transmission_limits'].items():
        if details['minimum_endpoint_margin_rad'] < min_sps_margin_rad:
            raise ValueError('sps_endpoint_margin_below_supplied_threshold:' + name)
    return {
        'event': 'model_wrist_candidate', 'schema': 'cruzr_model_wrist_candidate_v1',
        'model_sha256': MODEL_SHA256, 'image_sha256': row['image_sha256'],
        'image_source_ns': row['image_source_ns'], 'sample_index': row['index'],
        'state_received_monotonic_ns': stamp, 'prediction_received_monotonic_ns': prediction_stamp,
        'decision_monotonic_ns': now_ns, 'max_state_age_ns': max_state_age_ns,
        'max_prediction_age_ns': max_prediction_age_ns,
        'min_sps_margin_rad': min_sps_margin_rad,
        'state_age_pc_ns': now_ns-stamp, 'prediction_age_pc_ns': now_ns-prediction_stamp,
        'model_action_original': list(values), 'model_arm_deltas_rad': list(differences),
        'applied_arm_joint_order': list(probe.ARM),
        'applied_arm_target_rad': list(manifest['candidate']['target_rad']),
        'adaptation': 'hold_six_arm_axes_clip_positive_wrist_to_0.01_rad_hand_unchanged',
        'manifest': manifest, 'physical_control_qualified': False, 'physical_commands_sent': 0,
        'limitations': ['model output is reduced to one wrist axis; other six arm outputs and hand output are not executed',
                        'receipt time is on PC and does not measure Vision-to-PC latency',
                        'checkpoint identity is from the stream readiness event, not independent runtime attestation',
                        'source stream provenance and live state must be rechecked at dispatch',
                        'nominal endpoints do not establish collision, stopping or VLA enablement'],
    }


def save_model_wrist_artifact(output, result, urdf_text, transmissions_text):
    """Publish a complete one-prediction artifact atomically, without overwrite.

    Only call after the complete stream has passed ``finish``. The PNG itself
    is not retained: the artifact records the image hash and source stamp.
    A receipt hashes all exact file bytes; this establishes consistency, not a
    trusted model identity, present robot state or authority to dispatch.
    """
    if (not isinstance(result, dict) or result.get('event') != 'model_wrist_candidate'
            or result.get('physical_control_qualified') is not False
            or result.get('physical_commands_sent') != 0):
        raise ValueError('model_wrist_artifact_invalid')
    manifest = result['manifest']
    probe.validate(manifest, urdf_text, transmissions_text)
    candidate = dict(result)
    del candidate['manifest']
    candidate.setdefault('hand_scalar_uninterpreted', candidate['model_action_original'][7])
    def encoded(value):
        return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode('utf-8')
    data = {'manifest.json': encoded(manifest),
            'task.xml': manifest['candidate']['xml'].encode('utf-8'),
            'decision.json': encoded(candidate),
            'robot.urdf': urdf_text.encode('utf-8'),
            'transmissions.yaml': transmissions_text.encode('utf-8')}
    receipt = {'schema':'cruzr_model_wrist_artifact_v1', 'sha256':{k:hashlib.sha256(v).hexdigest()
               for k,v in data.items()}, 'model_sha256':result['model_sha256'],
               'image_sha256':result['image_sha256'], 'image_bytes_retained':False,
               'physical_control_qualified':False, 'physical_commands_sent':0}
    data['receipt.json'] = encoded(receipt)
    output = Path(output)
    parent = output.parent.resolve(strict=True)
    if not output.name or output.name in ('.', '..'):
        raise ValueError('invalid_wrist_output_path')
    destination = parent / output.name
    staging = Path(tempfile.mkdtemp(prefix='.'+output.name+'.tmp-', dir=parent))
    try:
        for name, raw in data.items():
            fd = os.open(staging/name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC |
                         getattr(os, 'O_NOFOLLOW', 0), 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            if (staging/name).read_bytes() != raw:
                raise RuntimeError('wrist_artifact_readback_mismatch:' + name)
        fd = os.open(staging, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        try: os.fsync(fd)
        finally: os.close(fd)
        verify_model_wrist_artifact(staging, hashlib.sha256(data['receipt.json']).hexdigest())
        # Linux renameat2(RENAME_NOREPLACE) publishes the full directory in a
        # single operation and never replaces an existing user path.
        libc = ctypes.CDLL(None, use_errno=True)
        rename = getattr(libc, 'renameat2', None)
        if rename is None:
            raise OSError(errno.ENOSYS, 'renameat2 unavailable')
        rename.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
        rename.restype = ctypes.c_int
        if rename(-100, os.fsencode(staging), -100, os.fsencode(destination), 1) != 0:
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error), str(destination))
        # After rename an fsync failure leaves the published artifact intact;
        # callers must treat its durability as uncertain and never overwrite.
        fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        try: os.fsync(fd)
        finally: os.close(fd)
    finally:
        if staging.exists():
            for name in data:
                try: (staging/name).unlink()
                except FileNotFoundError: pass
            try: staging.rmdir()
            except OSError: pass
    return {'event':'model_wrist_artifact_saved', 'path':str(destination),
            'receipt_sha256':hashlib.sha256(data['receipt.json']).hexdigest(),
            'physical_control_qualified':False, 'physical_commands_sent':0}


def verify_model_wrist_artifact(directory, expected_receipt_sha256):
    """Verify retained bytes and model-to-wrist arithmetic, without dispatch.

    The expected receipt hash must be held independently of the directory.
    Age is re-evaluated at the original decision time, not at this later call;
    this does not attest the PNG, live state, source runtime, or VLA enablement.
    """
    if (not isinstance(expected_receipt_sha256, str) or
            not re.fullmatch('[0-9a-f]{64}', expected_receipt_sha256)):
        raise ValueError('expected_receipt_sha256_required')
    directory = Path(directory)
    def read(name):
        fd = os.open(directory/name, os.O_RDONLY | os.O_CLOEXEC | getattr(os, 'O_NOFOLLOW', 0))
        with os.fdopen(fd, 'rb') as stream:
            raw = stream.read(16 * 1024 * 1024 + 1)
        if len(raw) > 16 * 1024 * 1024:
            raise ValueError('wrist_artifact_file_too_large:' + name)
        return raw
    receipt_raw = read('receipt.json')
    if hashlib.sha256(receipt_raw).hexdigest() != expected_receipt_sha256:
        raise ValueError('wrist_artifact_receipt_changed')
    receipt = json.loads(receipt_raw)
    fields = {'schema','sha256','model_sha256','image_sha256','image_bytes_retained',
              'physical_control_qualified','physical_commands_sent'}
    names = {'manifest.json','task.xml','decision.json','robot.urdf','transmissions.yaml'}
    if (not isinstance(receipt, dict) or set(receipt) != fields or
            receipt['schema'] != 'cruzr_model_wrist_artifact_v1' or
            not isinstance(receipt['sha256'], dict) or set(receipt['sha256']) != names or
            receipt['model_sha256'] != MODEL_SHA256 or receipt['image_bytes_retained'] is not False or
            receipt['physical_control_qualified'] is not False or
            type(receipt['physical_commands_sent']) is not int or receipt['physical_commands_sent'] != 0):
        raise ValueError('wrist_artifact_receipt_invalid')
    data = {name:read(name) for name in names}
    if any(not isinstance(receipt['sha256'][name], str) or
           hashlib.sha256(raw).hexdigest() != receipt['sha256'][name]
           for name,raw in data.items()):
        raise ValueError('wrist_artifact_file_changed')
    manifest, decision = json.loads(data['manifest.json']), json.loads(data['decision.json'])
    urdf, transmissions = data['robot.urdf'].decode('utf-8'), data['transmissions.yaml'].decode('utf-8')
    probe.validate(manifest, urdf, transmissions)
    if data['task.xml'] != manifest['candidate']['xml'].encode('utf-8'):
        raise ValueError('wrist_artifact_task_mismatch')
    state = manifest['input']['canonical_joint_state']
    row = {'event':'prediction', 'physical_control_qualified':False,
           'index':decision['sample_index'], 'image_source_ns':decision['image_source_ns'],
           'image_sha256':decision['image_sha256'], 'prediction':decision['model_action_original'],
           'proposed_minus_observed_rad':decision['model_arm_deltas_rad'],
           'prediction_received_monotonic_ns':decision['prediction_received_monotonic_ns'],
           'paired_state20':{'names':state['name'], 'positions':state['position'],
                             'velocities':state['velocity'],
                             'received_monotonic_ns':decision['state_received_monotonic_ns']}}
    expected = model_wrist_candidate(row, urdf_text=urdf, transmissions_text=transmissions,
        max_state_age_ns=decision['max_state_age_ns'], max_prediction_age_ns=decision['max_prediction_age_ns'],
        min_sps_margin_rad=decision['min_sps_margin_rad'], now_ns=decision['decision_monotonic_ns'],
        verified_model_sha256=receipt['model_sha256'])
    del expected['manifest']
    # LivePreview appends this unexecuted hand scalar after the candidate is built.
    expected['hand_scalar_uninterpreted'] = decision['model_action_original'][7]
    if decision != expected or decision['image_sha256'] != receipt['image_sha256']:
        raise ValueError('wrist_artifact_decision_mismatch')
    return {'status':'MODEL_WRIST_ARTIFACT_VERIFIED', 'receipt_sha256':expected_receipt_sha256,
            'task_sha256':manifest['candidate']['xml_sha256'], 'image_sha256':receipt['image_sha256'],
            'physical_control_qualified':False, 'physical_commands_sent':0,
            'limits':['source_runtime_and_image_bytes_not_attested',
                      'current_freshness_and_robot_state_not_verified',
                      'physical_vla_release_not_granted']}


class LivePreview:
    """Validate the actual relay lifecycle and emit drafts without dispatch."""

    def __init__(self, max_step_rad, duration_s, *, nominal=None, wrist_candidate=None):
        self.max_step = positive(max_step_rad, 'max_step_rad')
        self.duration = positive(duration_s, 'duration_s')
        self.nominal = nominal
        self.wrist_candidate = wrist_candidate
        if nominal is not None and wrist_candidate is not None:
            raise ValueError('incompatible_stream_modes')
        if wrist_candidate is not None and (self.max_step != probe.ARM_STEP or self.duration != probe.DURATION_S):
            raise ValueError('model_wrist_candidate_requires_fixed_probe')
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
            if self.wrist_candidate is not None and self.count:
                raise ValueError('model_wrist_candidate_requires_one_prediction')
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
            if self.wrist_candidate is not None:
                result = model_wrist_candidate(row, now_ns=time.monotonic_ns(),
                                               verified_model_sha256=MODEL_SHA256,
                                               **self.wrist_candidate)
            elif self.nominal is None:
                result = draft_joints(joints, self.count, stamp, self.max_step,
                                      self.duration, 'live_shadow_relay')
            else:
                result = checked_live_step(row, self.max_step, self.duration,
                                           now_ns=time.monotonic_ns(), **self.nominal)
            if self.wrist_candidate is None:
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
    mode.add_argument('--verify-wrist-artifact', type=Path,
                      help='verify retained one-prediction artifact without dispatch')
    parser.add_argument('--sample', type=int, default=0)
    parser.add_argument('--max-step-rad', type=float)
    parser.add_argument('--duration-s', type=float)
    parser.add_argument('--urdf', type=Path, help='optional nominal URDF for paired stream check')
    parser.add_argument('--transmissions', type=Path, help='optional nominal SPS transmissions for paired stream check')
    parser.add_argument('--max-state-age-ns', type=int, help='caller-supplied PC receipt age limit')
    parser.add_argument('--max-prediction-age-ns', type=int, help='caller-supplied PC prediction age limit')
    parser.add_argument('--min-sps-margin-rad', type=float, help='caller-supplied endpoint diagnostic margin')
    parser.add_argument('--wrist-candidate', action='store_true',
                        help='prepare exactly one model-derived positive wrist candidate; never dispatch')
    parser.add_argument('--wrist-output', type=Path,
                        help='new directory for the complete model-derived wrist artifact')
    parser.add_argument('--receipt-sha256', help='independently retained artifact receipt digest')
    args = parser.parse_args(argv)
    if args.run:
        print('BLOCKED: native arm mapping, trajectory and physical stopping remain unqualified', file=sys.stderr)
        return 2
    try:
        if args.verify_wrist_artifact is not None:
            if (args.wrist_candidate or args.wrist_output is not None or args.sample != 0 or
                    any(value is not None for value in (args.max_step_rad, args.duration_s, args.urdf,
                         args.transmissions, args.max_state_age_ns, args.max_prediction_age_ns,
                         args.min_sps_margin_rad))):
                raise ValueError('verification_mode_does_not_accept_preparation_options')
            print(json.dumps(verify_model_wrist_artifact(args.verify_wrist_artifact, args.receipt_sha256),
                             separators=(',', ':'), allow_nan=False))
            return 0
        if args.receipt_sha256 is not None:
            raise ValueError('receipt_sha256_only_supported_with_artifact_verification')
        if args.wrist_candidate != (args.wrist_output is not None):
            raise ValueError('wrist_candidate_and_output_must_be_supplied_together')
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
            wrist = None
            if args.wrist_candidate:
                if nominal is None or args.max_step_rad != probe.ARM_STEP or args.duration_s != probe.DURATION_S:
                    raise ValueError('wrist_candidate_requires_complete_nominal_inputs_and_fixed_probe')
                wrist, nominal = nominal, None
            preview = LivePreview(args.max_step_rad, args.duration_s, nominal=nominal,
                                  wrist_candidate=wrist)
            saved_candidate = None
            for raw in iter(lambda: sys.stdin.buffer.readline(1024 * 1024 + 1), b''):
                if len(raw) > 1024 * 1024 or not raw.endswith(b'\n'):
                    raise ValueError('relay line too long or incomplete')
                result = preview.accept(json.loads(raw))
                if result is not None:
                    if result.get('event') == 'model_wrist_candidate':
                        saved_candidate = result
                    else:
                        print(json.dumps(result, separators=(',', ':'), allow_nan=False), flush=True)
            preview.finish()
            if args.wrist_candidate:
                if saved_candidate is None:
                    raise ValueError('model_wrist_candidate_missing')
                receipt = save_model_wrist_artifact(args.wrist_output, saved_candidate,
                                                   wrist['urdf_text'], wrist['transmissions_text'])
                print(json.dumps(saved_candidate, separators=(',', ':'), allow_nan=False), flush=True)
                print(json.dumps(receipt, separators=(',', ':'), allow_nan=False), flush=True)
        else:
            if args.wrist_candidate:
                raise ValueError('wrist_candidate_only_supported_with_stream')
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
