#!/usr/bin/env python3
"""Export nominally causal passive observations for isolated SmolVLA analysis.

No robot, network, ROS, target actions, or inference are used here. The output
does not qualify motion, establish sensor clock synchronization, or label success.
"""
import argparse
import json
import math
from pathlib import Path
import re
import shutil

from prepare_ball_candidate_targets import source_data
from prepare_ball_observations import RIGHT_HAND, TASK, digest, finite_vector, read_source


def prepare(capture, output):
    capture = capture.expanduser().resolve(strict=True)
    output = output.expanduser().resolve()
    if (not capture.is_dir() or output.exists() or not output.parent.is_dir() or
            output == capture or output in capture.parents or capture in output.parents):
        raise ValueError('output must be new, separate and have an existing parent')
    metadata, frames, _ = read_source(capture)
    manifest, quality = metadata['manifest.json'], metadata['quality.json']
    hand_qc = quality.get('hands', {}).get('hand_right', {})
    if (manifest.get('schema') != 'cruzr-passive-episode-v1' or
            manifest.get('training_ready') is not False or
            quality.get('capture_checks_passed') is not True or
            quality.get('training_ready') is not False or
            hand_qc.get('status') != 'complete' or hand_qc.get('capture_checks_passed') is not True):
        raise ValueError('capture or right-hand quality is not complete')
    selected, refs = [], set()
    for frame, obs in sorted(frames.items()):
        stamp = obs.get('image_source_ns')
        hand = obs.get('hand_right', {})
        if (type(stamp) is not int or not finite_vector(obs.get('state20'), 20) or
                hand.get('name') != RIGHT_HAND or not finite_vector(hand.get('position'), 7)):
            raise ValueError(f'frame {frame}: malformed image/state/hand')
        delta, reception, lines = (obs.get('source_delta_ms', {}),
                                   obs.get('reception_delta_ms', {}), obs.get('source_lines', {}))
        for kind in ('joints', 'hand_right'):
            if (not isinstance(delta.get(kind), (int, float)) or isinstance(delta[kind], bool) or
                    not math.isfinite(delta[kind]) or abs(delta[kind]) > 80 or
                    not isinstance(reception.get(kind), (int, float)) or isinstance(reception[kind], bool) or
                    not math.isfinite(reception[kind]) or abs(reception[kind]) > 500 or
                    type(lines.get(kind)) is not int or lines[kind] <= 0):
                raise ValueError(f'frame {frame}: invalid timing or source references')
        if any(delta[k] > 0 for k in ('joints', 'hand_right')):
            continue
        image = capture / obs['png_file']
        if (not re.fullmatch(r'rgb/[0-9]{6}\.png', obs['png_file']) or
                capture not in image.resolve(strict=True).parents or
                metadata['checksums'].get(obs['png_file']) != digest(image)):
            raise ValueError(f'frame {frame}: image integrity failed')
        refs.update(lines[k] for k in ('joints', 'hand_right'))
        selected.append((frame, obs, image))
    if not selected:
        raise ValueError('no nominally causal matched observations')
    names, raw = source_data(capture, metadata['hashes'], refs)
    images = {}
    with (capture / 'samples.jsonl').open(encoding='utf-8') as f:
        for line in f:
            row = json.loads(line)
            if row.get('kind') == 'rgb':
                name = row.get('png_file')
                if name in images:
                    raise ValueError('duplicate image source record')
                images[name] = row
    previous_stamp = -1
    max_age_ns = 0
    for frame, obs, _ in selected:
        stamp = obs['image_source_ns']
        if stamp <= previous_stamp:
            raise ValueError(f'frame {frame}: image stamps not increasing')
        previous_stamp = stamp
        lines = obs['source_lines']
        joint, hand = raw[lines['joints']], raw[lines['hand_right']]
        rgb = images.get(obs['png_file'], {})
        if (rgb.get('source_ns') != stamp or rgb.get('png_sha256') != metadata['checksums'][obs['png_file']] or
                type(rgb.get('received_monotonic_ns')) is not int):
            raise ValueError(f'frame {frame}: raw image reference mismatch')
        if joint.get('kind') != 'joints' or hand.get('kind') != 'hand_right':
            raise ValueError(f'frame {frame}: wrong raw source kind')
        for kind, row in (('joints', joint), ('hand_right', hand)):
            source_ns = row.get('source_ns')
            if (type(source_ns) is not int or source_ns > stamp or stamp - source_ns > 80_000_000 or
                    abs((source_ns - stamp) / 1e6 - obs['source_delta_ms'][kind]) > 0.000001):
                raise ValueError(f'frame {frame}: raw source timestamp mismatch')
            if (type(row.get('received_monotonic_ns')) is not int or
                    row['received_monotonic_ns'] > rgb['received_monotonic_ns'] or
                    rgb['received_monotonic_ns'] - row['received_monotonic_ns'] > 500_000_000):
                raise ValueError(f'frame {frame}: raw state not received before image')
            max_age_ns = max(max_age_ns, stamp - source_ns)
        for raw_row, expected_names, expected in ((joint, names, obs['state20']),
                                                  (hand, RIGHT_HAND, obs['hand_right']['position'])):
            msg = raw_row.get('message', {})
            raw_names, values = msg.get('name'), msg.get('position')
            if (not isinstance(raw_names, list) or not isinstance(values, list) or
                    len(raw_names) != len(values) or len(set(raw_names)) != len(raw_names)):
                raise ValueError(f'frame {frame}: malformed raw state names')
            by_name = dict(zip(raw_names, values))
            if any(by_name.get(name) != expected[i] for i, name in enumerate(expected_names)):
                raise ValueError(f'frame {frame}: aligned and raw state differ')
    output.mkdir(mode=0o700)
    (output / 'rgb').mkdir(mode=0o700)
    result = {'schema': 'cruzr_ball_current_observations_v1', 'task': TASK,
              'training_ready': False, 'physical_control_qualified': False, 'has_action_column': False,
              'purpose': 'offline current-capture diagnostic; outcome unreviewed',
              'source_capture_hashes': metadata['hashes'], 'state_names': names + RIGHT_HAND,
              'maximum_nominal_state_age_ns': max_age_ns,
              'limitations': ['nominal source-time ordering does not calibrate clocks or sensor latency',
                              'isolated observations are not a closed-loop rollout or physical test'],
              'records': []}
    for frame, obs, image in selected:
        dest = output / 'rgb' / f'current_capture_{frame:06}.png'
        shutil.copyfile(image, dest)
        image_hash = metadata['checksums'][obs['png_file']]
        if digest(dest) != image_hash:
            raise ValueError('copied image checksum mismatch')
        result['records'].append({'segment_id': 'current_capture', 'status': 'unreviewed',
            'source_frame': frame, 'image': str(dest.relative_to(output)), 'image_sha256': image_hash,
            'image_source_ns': obs['image_source_ns'],
            'joint_source_ns': raw[obs['source_lines']['joints']]['source_ns'],
            'hand_source_ns': raw[obs['source_lines']['hand_right']]['source_ns'],
            'state27': obs['state20'] + obs['hand_right']['position']})
    with (output / 'manifest.json').open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')
    print(f"Exported {len(selected)} observations for offline analysis, without actions: {output}")
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--capture', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    prepare(args.capture, args.output)
