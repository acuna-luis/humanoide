#!/usr/bin/env python3
"""Create a NON-QUALIFIED offline action-candidate bundle, never robot control.

The transformed motor cmd_pos is a historical-transmission hypothesis, NOT an
applied joint action. Hand labels are observational correlations, not a measured
PICO trigger. This is not a LeRobot dataset and is not qualified for training,
deployment or any publisher. Only visually reviewed candidate_success segments
are selected. Sources are read-only and output must be a new directory.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import sys

try:
    import yaml
except ImportError as exc:
    raise SystemExit('PyYAML is required to read the historical transmission snapshot') from exc

from prepare_ball_observations import RIGHT_HAND, digest, finite_vector, load_json


SNAPSHOT_SHA256 = '774d9a1e92951452ddd7e73e62e196c03894f5465ad9c13fdb98c3eca289101d'
TRANSMISSIONS_SHA256 = '7c7e0760c274c59237ca5787bc2e75096692ee92c43bcf79f61cbad2cfa0f29c'
JOINTS = ['R_shoulder_pitch_joint', 'R_shoulder_roll_joint', 'R_shoulder_yaw_joint',
          'R_elbow_roll_joint', 'R_elbow_yaw_joint', 'R_wrist_pitch_joint', 'R_wrist_roll_joint']
SPLITS = {'inspection_train', 'inspection_validation', 'inspection_test'}


def mapping(snapshot):
    if digest(snapshot) != SNAPSHOT_SHA256:
        raise ValueError('historical snapshot checksum differs from pinned evidence')
    data = load_json(snapshot)
    matches = [(k, v) for k, v in data.items() if k.endswith('/ecat_hardware/transmissions.yaml')]
    if len(matches) != 1:
        raise ValueError('historical transmissions file not unique')
    path, item = matches[0]
    text = item.get('text')
    if (not isinstance(text, str) or item.get('sha256') != TRANSMISSIONS_SHA256 or
            hashlib.sha256(text.encode()).hexdigest() != TRANSMISSIONS_SHA256):
        raise ValueError('historical transmissions checksum mismatch')
    parsed = yaml.safe_load(text)
    entries = parsed.get('transmissions', {})
    by_joint = {}
    for entry in entries.values():
        joint, actuator = entry.get('joint', {}), entry.get('actuator', {})
        name = joint.get('name')
        if name not in JOINTS:
            continue
        if name in by_joint or entry.get('type') != 'SimpleTransmission':
            raise ValueError(f'duplicate or unsupported transmission for {name}')
        reduction, offset = actuator.get('mechanicalReduction'), joint.get('offset')
        if reduction not in (-1.0, 1.0) or offset != 0.0 or actuator.get('name') != name.replace('_joint', '_motor'):
            raise ValueError(f'unexpected historical motor mapping for {name}')
        by_joint[name] = {'joint': name, 'motor': actuator['name'], 'mechanicalReduction': reduction,
                          'offset': offset, 'historical_joint_limit': joint.get('limit')}
    if set(by_joint) != set(JOINTS):
        raise ValueError('historical snapshot does not contain exactly seven right arm joints')
    return path, [by_joint[n] for n in JOINTS]


def check_sha(path, expected, description):
    if not isinstance(expected, str) or digest(path) != expected:
        raise ValueError(f'{description}: checksum mismatch')


def source_data(source, source_hashes, required_lines):
    for name in ('manifest.json', 'quality.json', 'aligned.jsonl', 'samples.jsonl'):
        check_sha(source / name, source_hashes.get(name), f'{source}/{name}')
    manifest = load_json(source / 'manifest.json')
    names = manifest.get('joint_names')
    if not isinstance(names, list) or len(names) != 20 or len(set(names)) != 20 or not set(JOINTS) <= set(names):
        raise ValueError('source joint_names must be unique 20D and include all right arm joints')
    raw = {}
    with (source / 'samples.jsonl').open(encoding='utf-8') as f:
        for lineno, line in enumerate(f, 1):
            if lineno in required_lines:
                raw[lineno] = json.loads(line)
    if set(raw) != required_lines:
        raise ValueError('source line references missing from raw sample log')
    return names, raw


def resolve_record(record, names, raw, mapping_entries, max_age_ms):
    observation = record.get('observations', {})
    state = observation.get('state20')
    command = observation.get('actuator_cmd_pos20')
    hand = observation.get('hand_right', {})
    stamp = observation.get('image_source_ns')
    if not finite_vector(state, 20) or not finite_vector(command, 20) or hand.get('name') != RIGHT_HAND or not finite_vector(hand.get('position'), 7):
        raise ValueError('missing or malformed 20D, actuator command or 7D right-hand state')
    if type(stamp) is not int:
        raise ValueError('missing image timestamp')
    lines = observation.get('source_lines', {})
    if any(type(lines.get(x)) is not int for x in ('joints', 'actuators', 'hand_right')):
        raise ValueError('missing joint, actuator or hand state source references')
    jrow, arow, hrow = (raw[lines[x]] for x in ('joints', 'actuators', 'hand_right'))
    if [jrow.get('kind'), arow.get('kind'), hrow.get('kind')] != ['joints', 'actuators', 'hand_right']:
        raise ValueError('source lines do not match declared channel types')
    jmsg, amsg, hmsg = jrow['message'], arow['message'], hrow['message']
    if len(jmsg.get('name', [])) != len(jmsg.get('position', [])) or len(set(jmsg['name'])) != len(jmsg['name']):
        raise ValueError('raw whole-joint names/positions malformed')
    raw_joints = dict(zip(jmsg['name'], jmsg['position']))
    if any(name not in raw_joints or raw_joints[name] != state[i] for i, name in enumerate(names)):
        raise ValueError('aligned 20D state differs from referenced raw joint state')
    act_items = amsg.get('act_item', [])
    if len({x.get('name') for x in act_items}) != len(act_items):
        raise ValueError('duplicate raw actuator names')
    act = {x.get('name'): x for x in act_items}
    for entry in mapping_entries:
        i, motor = names.index(entry['joint']), entry['motor']
        if motor not in act or act[motor].get('cmd_pos') != command[i]:
            raise ValueError(f'aligned cmd_pos differs from raw motor {motor}')
    if (len(hmsg.get('name', [])) != len(hmsg.get('position', [])) or
            len(set(hmsg['name'])) != len(hmsg['name'])):
        raise ValueError('raw hand state malformed')
    hand_raw = dict(zip(hmsg['name'], hmsg['position']))
    if any(hand_raw.get(name) != hand['position'][i] for i, name in enumerate(RIGHT_HAND)):
        raise ValueError('aligned hand state differs from referenced raw hand state')
    if any(type(row.get('source_ns')) is not int for row in (jrow, arow, hrow)):
        raise ValueError('raw source timestamps missing')

    target = []
    outside = []
    for entry in mapping_entries:
        # This is the vendor SimpleTransmission position hypothesis, not a
        # claim about the v4 runtime or that the motor command was applied.
        value = command[names.index(entry['joint'])] / entry['mechanicalReduction'] + entry['offset']
        target.append(value)
        limits = entry['historical_joint_limit']
        outside.append(value < limits['lower'] or value > limits['upper'])
    intent = record.get('right_hand_intent_candidate', {})
    label, intent_time, intent_line = None, None, None
    if intent.get('value') in {'open_candidate', 'grasp_hold_candidate'}:
        expected = 5 if intent['value'] == 'open_candidate' else 7
        intent_line = intent.get('source_line')
        if type(intent_line) is not int or intent_line not in raw:
            raise ValueError('missing raw command for candidate hand intent')
        crow = raw[intent_line]
        age = (stamp - crow.get('source_ns', stamp + 1)) / 1e6
        if (crow.get('kind') != 'hand_command_right' or crow['message'].get('names') != RIGHT_HAND or
                crow['message'].get('mode') != [expected] * 7 or intent.get('mode') != [expected] * 7 or
                crow.get('source_ns') != intent.get('command_source_ns') or not intent.get('provisional') or
                not 0 <= age <= max_age_ms):
            raise ValueError('candidate hand intent is not supported by a fresh past raw command')
        intent_time = crow['source_ns']
        label = 0 if expected == 5 else 1
    elif intent.get('value') != 'unknown':
        raise ValueError('invalid hand intention label')
    return {'image_source_ns': stamp, 'whole_joint_source_ns': jrow['source_ns'],
            'actuator_source_ns': arow['source_ns'], 'hand_state_source_ns': hrow['source_ns'],
            'hand_command_source_ns': intent_time, 'whole_joint_source_line': lines['joints'],
            'actuator_source_line': lines['actuators'], 'hand_state_source_line': lines['hand_right'],
            'hand_command_source_line': intent_line, 'state20': state, 'hand_right_position7': hand['position'],
            'experimental_joint_target7': target, 'experimental_hand_label': label,
            'experimental_target8': target + [label] if label is not None else None,
            'historical_position_limit_exceeded': outside,
            'candidate_is_qualified_action': False}


def prepare(input_dir, snapshot, output):
    input_dir, snapshot, output = (x.expanduser().resolve() for x in (input_dir, snapshot, output))
    if output.exists() or not output.parent.is_dir():
        raise ValueError('output must be a new directory under an existing parent')
    if output == input_dir or input_dir in output.parents or output in input_dir.parents:
        raise ValueError('output cannot overlap input bundle')
    if output == snapshot or output in snapshot.parents:
        raise ValueError('output cannot overlap historical snapshot')
    snapshot_path, entries = mapping(snapshot)
    manifest = load_json(input_dir / 'manifest.json')
    if (manifest.get('schema') != 'cruzr_ball_observations_v1' or manifest.get('training_ready') is not False or
            manifest.get('physical_control_qualified') is not False or manifest.get('has_action_column') is not False):
        raise ValueError('input bundle is not the expected unqualified observation schema')
    max_age_ms = manifest.get('command_max_age_ms')
    if not isinstance(max_age_ms, (int, float)) or isinstance(max_age_ms, bool) or not 0 < max_age_ms <= 80 or not math.isfinite(max_age_ms):
        raise ValueError('invalid observation intent freshness bound')
    segments = manifest.get('segments')
    if not isinstance(segments, list) or not segments:
        raise ValueError('input bundle has no segments')
    sources, source_splits, ids, selected = {}, {}, set(), []
    for segment in segments:
        ident, source, split = segment.get('id'), segment.get('source_dir'), segment.get('split')
        if not isinstance(ident, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', ident) or ident in ids:
            raise ValueError('segment IDs must be distinct safe identifiers')
        ids.add(ident)
        if not isinstance(source, str) or split not in SPLITS | {'unassigned'}:
            raise ValueError(f'{ident}: invalid source or split')
        source = Path(source).resolve(strict=True)
        previous = source_splits.setdefault(source, split)
        if previous != split:
            raise ValueError('same capture cannot belong to different inspection splits')
        if output == source or source in output.parents or output in source.parents:
            raise ValueError('output cannot overlap a capture')
        expected_hashes = segment.get('source_hashes')
        if not isinstance(expected_hashes, dict):
            raise ValueError('source hashes missing')
        if source in sources and sources[source]['hashes'] != expected_hashes:
            raise ValueError('conflicting source hashes')
        sources.setdefault(source, {'hashes': expected_hashes, 'lines': set()})
        if segment.get('status') != 'candidate_success':
            continue  # assisted, failed and unknown are never promoted as successes
        if split not in SPLITS:
            raise ValueError(f'{ident}: candidate must have an explicit inspection split')
        start, end = segment.get('start_frame'), segment.get('end_frame')
        if type(start) is not int or type(end) is not int or start < 0 or end < start:
            raise ValueError(f'{ident}: invalid frame bounds')
        obs_path = input_dir / ident / 'observations.jsonl'
        check_sha(obs_path, segment.get('observations_sha256'), f'{ident} observations')
        rows = []
        with obs_path.open(encoding='utf-8') as f:
            for line in f:
                rows.append(json.loads(line))
        if len(rows) != end-start+1 or [r.get('source_frame') for r in rows] != list(range(start, end+1)):
            raise ValueError(f'{ident}: missing or reordered frames')
        previous_ns = None
        for row in rows:
            n = row['source_frame']
            if row.get('png_file') != f'rgb/{n:06}.png':
                raise ValueError(f'{ident}: unexpected image path')
            image = input_dir / ident / row['png_file']
            if input_dir not in image.resolve(strict=True).parents:
                raise ValueError('image escapes input bundle')
            check_sha(image, row.get('png_sha256'), f'{ident} image {n}')
            obs = row.get('observations', {})
            if obs.get('png_file') != f'rgb/{n:06}.png':
                raise ValueError('aligned source image name mismatch')
            stamp = obs.get('image_source_ns')
            if type(stamp) is not int or (previous_ns is not None and stamp <= previous_ns):
                raise ValueError('image timestamps missing or non-increasing')
            previous_ns = stamp
            lines = obs.get('source_lines', {})
            if any(type(lines.get(k)) is not int or lines[k] <= 0 for k in ('joints', 'actuators', 'hand_right')):
                raise ValueError('source line references missing')
            sources[source]['lines'].update(lines[k] for k in ('joints', 'actuators', 'hand_right'))
            intent = row.get('right_hand_intent_candidate', {})
            if intent.get('value') in {'open_candidate', 'grasp_hold_candidate'}:
                if type(intent.get('source_line')) is not int or intent['source_line'] <= 0:
                    raise ValueError('candidate hand source line missing')
                sources[source]['lines'].add(intent['source_line'])
        selected.append((segment, source, rows))
    if not selected:
        raise ValueError('no candidate_success segments to export')
    for source, info in sources.items():
        if info['lines']:
            info['names'], info['raw'] = source_data(source, info['hashes'], info['lines'])

    prepared = []
    for segment, source, rows in selected:
        info = sources[source]
        values = [resolve_record(row, info['names'], info['raw'], entries, max_age_ms) for row in rows]
        image_gaps = [(values[i]['image_source_ns']-values[i-1]['image_source_ns'])/1e6 for i in range(1,len(values))]
        # These are absolute source timestamp separations, NOT calibrated physical latency.
        max_delta = {kind: max(abs(v[kind]-v['image_source_ns'])/1e6 for v in values)
                     for kind in ('whole_joint_source_ns', 'actuator_source_ns', 'hand_state_source_ns')}
        prepared.append((segment, source, rows, values, max(image_gaps, default=0), max_delta))
    output.mkdir()
    result = {'schema': 'cruzr_ball_candidate_targets_v1', 'task': manifest.get('task'),
        'training_ready': False, 'physical_control_qualified': False,
        'offline_experiment_only': True, 'source_observations_manifest_sha256': digest(input_dir / 'manifest.json'),
        'historical_hardware_snapshot_sha256': SNAPSHOT_SHA256, 'historical_transmissions_sha256': TRANSMISSIONS_SHA256,
        'historical_transmissions_path': snapshot_path, 'right_arm_mapping': entries,
        'state20_names_by_source': {str(k): v['names'] for k, v in sources.items() if 'names' in v},
        'state_right_hand_names': RIGHT_HAND, 'experimental_target8_order': JOINTS + ['grasp_hold_intent_candidate'],
        'target_formula': 'joint_candidate = motor_cmd_pos / historical_mechanicalReduction + historical_joint_offset',
        'hand_label_mapping': {'0': 'open_candidate_mode_5', '1': 'grasp_hold_candidate_mode_7',
                               'null': 'unknown; no 8D target supplied'},
        'limitations': ['NOT a LeRobot dataset and NOT qualified for physical control',
            'historical 2026-09-14 transmissions v1 are not verified as loaded in v4 capture on 2026-11-09',
            'motor cmd_pos is a requested, unqualified command; not an applied action',
            'hand modes are observations correlated with grip, not a measured PICO trigger or validated force',
            'source capture incomplete; timestamps/clock differences are not physical synchronization',
            'candidate_success means visual review only, not verified autonomous task success or 20 cm lift',
            'splits use capture identity, not proof of independent sessions or sufficient validation',
            'none of the selected segments establishes starting from HOME'],
        'excluded_non_candidate_segments': [{'id': s['id'], 'status': s.get('status')} for s in segments if s.get('status') != 'candidate_success'],
        'segments': []}
    for segment, source, rows, values, max_gap, max_delta in prepared:
        target = output / segment['id']
        (target / 'rgb').mkdir(parents=True)
        unknown = 0
        with (target / 'candidate_targets.jsonl').open('x', encoding='utf-8') as f:
            for row, value in zip(rows, values):
                image = input_dir / segment['id'] / row['png_file']
                dest = target / row['png_file']
                shutil.copyfile(image, dest)
                check_sha(dest, row['png_sha256'], 'copied image')
                unknown += value['experimental_hand_label'] is None
                value.update(source_frame=row['source_frame'], png_file=row['png_file'], png_sha256=row['png_sha256'])
                f.write(json.dumps(value, ensure_ascii=False, allow_nan=False)+'\n')
        result['segments'].append({'id': segment['id'], 'source_dir': str(source),
            'source_hashes': segment['source_hashes'], 'source_observations_sha256': segment['observations_sha256'],
            'status': segment['status'], 'notes': segment['notes'], 'split': segment['split'],
            'start_frame': segment['start_frame'], 'end_frame': segment['end_frame'], 'frames': len(rows),
            'unknown_hand_labels': unknown, 'max_image_gap_ms': max_gap,
            'max_abs_source_timestamp_delta_ms': max_delta,
            'historical_position_limit_exceedances': sum(sum(v['historical_position_limit_exceeded']) for v in values),
            'candidate_targets_sha256': digest(target / 'candidate_targets.jsonl')})
    with (output / 'manifest.json').open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, allow_nan=False, indent=2); f.write('\n')
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--observations', type=Path, required=True, help='existing observation bundle')
    p.add_argument('--hardware-snapshot', type=Path, required=True, help='pinned historical hardware-configs.json')
    p.add_argument('--output', type=Path, required=True, help='new output directory')
    args = p.parse_args(argv)
    try:
        result = prepare(args.observations, args.hardware_snapshot, args.output)
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr); return 1
    print(json.dumps({'output': str(args.output), 'segments': len(result['segments']),
                      'training_ready': False, 'physical_control_qualified': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
