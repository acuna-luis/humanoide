#!/usr/bin/env python3
"""Reconstruct one recorded passive observation for offline-only inference.

Uses original Vision timestamps and images. Does not imply current state,
clock calibration, target actions or physical-control qualification.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import sys

from live_ball_observation_adapter import MAX_LINE, PROFILE, Pairer
from prepare_ball_observations import read_source


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def prepare(capture, output, sha256sums_hash):
    capture = capture.resolve(strict=True)
    if output.is_symlink():
        raise ValueError('output cannot be a symlink')
    output = output.parent.resolve(strict=True) / output.name
    if (not capture.is_dir() or output.exists() or output.is_symlink() or not output.parent.is_dir() or
            capture == output or capture in output.parents or output in capture.parents):
        raise ValueError('output must be new, outside capture, and have an existing parent')
    if not re.fullmatch(r'[0-9a-f]{64}', sha256sums_hash) or digest(capture / 'SHA256SUMS') != sha256sums_hash:
        raise ValueError('capture checksum list differs')
    metadata, _, _ = read_source(capture)
    quality = metadata['quality.json']
    if (metadata['manifest.json'].get('schema') != 'cruzr-passive-episode-v1' or
            metadata['manifest.json'].get('training_ready') is not False or
            quality.get('capture_checks_passed') is not True or
            quality.get('training_ready') is not False or
            quality.get('hands', {}).get('hand_right', {}).get('capture_checks_passed') is not True):
        raise ValueError('capture/right hand QC is incomplete')
    profile = json.loads(PROFILE.read_text(encoding='utf-8'))
    if metadata['manifest.json'].get('joint_names') != profile['joint_names']:
        raise ValueError('joint order differs from the current offline adapter profile')
    pairer = Pairer(profile['joint_names'])
    with (capture / 'samples.jsonl').open('rb') as stream:
        for line in stream:
            if len(line) > MAX_LINE:
                raise ValueError('source line exceeds bound')
            row = json.loads(line)
            if row.get('kind') == 'rgb' and pairer.ready:
                name = row.get('png_file')
                if not isinstance(name, str) or not re.fullmatch(r'rgb/[0-9]{6}\.png', name):
                    raise ValueError('invalid recorded image path')
                image = (capture / name).resolve(strict=True)
                if capture not in image.parents:
                    raise ValueError('image resolves outside capture')
                payload = image.read_bytes()
                if (len(payload) > 5 * 1024 * 1024 or
                        hashlib.sha256(payload).hexdigest() != metadata['checksums'].get(name) or
                        hashlib.sha256(payload).hexdigest() != row.get('png_sha256')):
                    raise ValueError('recorded image integrity mismatch')
                row['png_b64'] = base64.b64encode(payload).decode('ascii')
            observation = pairer.accept(row)
            if observation is not None:
                # Pairer uses a present PC monotonic time for live transport. It
                # would falsely imply freshness for a historical replay; omit it.
                observation.pop('pc_received_monotonic_ns', None)
                observation['source_status'] = 'historical_recording_not_live'
                observation['physical_control_qualified'] = False
                with output.open('x', encoding='utf-8') as dest:
                    json.dump(observation, dest, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
                    dest.write('\n')
                print('historical_sample_sha256=' + digest(output))
                print('historical_image_sha256=' + observation['image_sha256'])
                print('No current state or physical control is implied.')
                return
    raise ValueError('no usable paired observation in recording')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--capture-sha256sums', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        prepare(args.capture, args.output, args.capture_sha256sums)
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as exc:
        print('HISTORICAL_INPUT_ERROR: ' + str(exc), file=sys.stderr)
        sys.exit(1)
