#!/usr/bin/env python3
"""Export strictly causal failed-trial observations for offline inference only.

These are failed demonstrations from a different capture, not test successes,
and have no action labels. Never use this format for training or robot control.
"""
import argparse
import json
import math
from pathlib import Path
import shutil

from prepare_ball_candidate_targets import check_sha, source_data
from prepare_ball_observations import RIGHT_HAND, digest, finite_vector, read_source

IDS = ('toma1_370_389', 'toma1_390_414')
EXPECTED_BOUNDS = {'toma1_370_389':(370,389), 'toma1_390_414':(390,414)}
EXPECTED_SOURCE_HASHES = {
    'manifest.json':'fb76262e241c3578161c8819deaeffaa027e9ff2f5dd13e48c83d480e5228361',
    'quality.json':'c0cf7bd69ae422700dd243d44a84dd5d9e2f75a1e4caa8e8699e0322c9f915f8',
    'aligned.jsonl':'a9de6e216ffe0518e1daf5398bbcc9a5e56c4d98a94e045938eacdd1e429a2a8',
    'samples.jsonl':'d5962070113fd4e7ca0240ded6bfa95b4f953d6ef762a61e86b8733dfb1a0ec0'}
MAX_AGE_NS = 80_000_000


def verify_alignment(row, source_row, source, checksums):
    if row['observations'] != source_row or row['png_file'] != source_row.get('png_file'):
        raise ValueError('exported observation differs from original aligned row')
    original = (source / row['png_file']).resolve(strict=True)
    if source not in original.parents or checksums.get(row['png_file']) != row['png_sha256'] or digest(original) != row['png_sha256']:
        raise ValueError('source image or SHA256SUMS mismatch')


def verify_time(obs, joint, hand):
    stamp = obs['image_source_ns']
    if type(stamp) is not int:
        raise ValueError('invalid image time')
    for key, raw in (('joints', joint), ('hand_right', hand)):
        t = raw.get('source_ns')
        if type(t) is not int or not 0 <= stamp-t <= MAX_AGE_NS:
            raise ValueError('state is future or stale')
        if abs(obs['source_delta_ms'][key] - (t-stamp)/1_000_000) > 1e-9:
            raise ValueError('aligned time delta differs from source timestamp')


def verify_reception(image, joint, hand):
    stamp = image.get('received_monotonic_ns')
    if type(stamp) is not int or any(type(x.get('received_monotonic_ns')) is not int or
            not 0 <= stamp - x['received_monotonic_ns'] <= 500_000_000 for x in (joint, hand)):
        raise ValueError('state reception after image or older than 500 ms')


def prepare(bundle, output):
    bundle = bundle.resolve(strict=True)
    output = output.expanduser().resolve()
    if output.exists() or not output.parent.is_dir() or bundle in output.parents or output in bundle.parents:
        raise ValueError('output must be new, separate and have an existing parent')
    manifest = json.loads((bundle / 'manifest.json').read_text())
    if (manifest.get('schema') != 'cruzr_ball_observations_v1' or
        manifest.get('training_ready') is not False or manifest.get('physical_control_qualified') is not False or
        manifest.get('has_action_column') is not False):
        raise ValueError('unexpected source manifest')
    matches = [s for s in manifest['segments'] if s.get('id') in IDS]
    if len(matches) != 2 or {s['id'] for s in matches} != set(IDS):
        raise ValueError('failed inspection segments missing or duplicated')
    all_rows, source, hashes, lines = [], None, None, set()
    source_metadata, source_frames = None, None
    for s in matches:
        if s.get('status') != 'failed' or s.get('split') != 'inspection_test':
            raise ValueError('test segment is not explicitly marked failed')
        if (s.get('start_frame'),s.get('end_frame')) != EXPECTED_BOUNDS[s['id']] or s.get('source_hashes') != EXPECTED_SOURCE_HASHES:
            raise ValueError('test segment bounds or original capture pins differ')
        capture = Path(s['source_dir']).resolve(strict=True)
        if output == capture or capture in output.parents or output in capture.parents:
            raise ValueError('output overlaps source capture')
        if source is not None and (source != capture or hashes != s['source_hashes']):
            raise ValueError('test source differs between segments')
        source, hashes = capture, s['source_hashes']
        if source_metadata is None:
            source_metadata, source_frames, _ = read_source(source)
            if source_metadata['hashes'] != hashes:
                raise ValueError('source SHA256SUMS differs from export provenance')
        path = bundle / s['id'] / 'observations.jsonl'
        check_sha(path, s['observations_sha256'], 'observations')
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        if [r['source_frame'] for r in rows] != list(range(s['start_frame'], s['end_frame'] + 1)):
            raise ValueError('incomplete or reordered observations')
        for row in rows:
            obs = row['observations']
            verify_alignment(row, source_frames[row['source_frame']], source, source_metadata['checksums'])
            img = bundle / s['id'] / row['png_file']
            if row['png_file'] != f"rgb/{row['source_frame']:06}.png" or bundle not in img.resolve(strict=True).parents:
                raise ValueError('bad image path')
            check_sha(img, row['png_sha256'], 'image')
            if not finite_vector(obs.get('state20'), 20) or obs.get('hand_right', {}).get('name') != RIGHT_HAND or not finite_vector(obs['hand_right'].get('position'), 7):
                raise ValueError('bad observation')
            delta = obs.get('source_delta_ms', {})
            if any(not isinstance(delta.get(k), (int, float)) or not math.isfinite(delta[k]) for k in ('joints', 'hand_right')):
                raise ValueError('missing source timing')
            if any(delta[k] > 0 for k in ('joints', 'hand_right')):
                continue
            refs = obs.get('source_lines', {})
            if any(type(refs.get(k)) is not int or refs[k] <= 0 for k in ('joints', 'hand_right')):
                raise ValueError('missing state source references')
            lines.update(refs[k] for k in ('joints', 'hand_right'))
            all_rows.append((s['id'], row, img))
    names, raw = source_data(source, hashes, lines)
    wanted_images = {row['png_file'] for _,row,_ in all_rows}
    image_messages = {}
    with (source/'samples.jsonl').open(encoding='utf-8') as f:
        for line in f:
            msg = json.loads(line)
            if msg.get('kind') == 'rgb' and msg.get('png_file') in wanted_images:
                if msg['png_file'] in image_messages:
                    raise ValueError('duplicate RGB source row')
                image_messages[msg['png_file']] = msg
    if set(image_messages) != wanted_images:
        raise ValueError('RGB source row missing')
    for _, row, _ in all_rows:
        obs = row['observations']; refs = obs['source_lines']; stamp = obs['image_source_ns']
        joint, hand = raw[refs['joints']], raw[refs['hand_right']]
        image = image_messages[row['png_file']]
        if image.get('source_ns') != stamp or image.get('png_sha256') != row['png_sha256']:
            raise ValueError('image time or hash differs from RGB source row')
        verify_reception(image, joint, hand)
        if (joint['kind'] != 'joints' or hand['kind'] != 'hand_right' or
            any(type(x.get('source_ns')) is not int or x['source_ns'] > stamp for x in (joint, hand))):
            raise ValueError('noncausal or invalid raw source')
        verify_time(obs, joint, hand)
        jmsg, hmsg = joint['message'], hand['message']
        joints = dict(zip(jmsg['name'], jmsg['position']))
        hands = dict(zip(hmsg['name'], hmsg['position']))
        if any(joints.get(n) != obs['state20'][i] for i,n in enumerate(names)) or any(hands.get(n) != obs['hand_right']['position'][i] for i,n in enumerate(RIGHT_HAND)):
            raise ValueError('observation does not match raw telemetry')
    if not all_rows:
        raise ValueError('no strictly causal observations')
    output.mkdir(mode=0o700)
    result = {'schema':'cruzr_ball_failed_observations_v1', 'task':manifest['task'],
        'training_ready':False, 'physical_control_qualified':False, 'has_action_column':False,
        'purpose':'offline diagnosis only; failed demonstrations, not task successes',
        'max_nominal_age_ns':MAX_AGE_NS, 'max_received_age_ns':500_000_000,
        'source_observations_sha256':digest(bundle/'manifest.json'), 'source_capture_hashes':hashes,
        'state_names':names+RIGHT_HAND, 'records':[]}
    (output/'rgb').mkdir(mode=0o700)
    for ident, row, img in all_rows:
        dest = output/'rgb'/f"{ident}_{row['source_frame']:06}.png"
        shutil.copyfile(img, dest)
        check_sha(dest, row['png_sha256'], 'copied image')
        obs = row['observations']
        result['records'].append({'segment_id':ident, 'status':'failed', 'source_frame':row['source_frame'],
            'image':str(dest.relative_to(output)), 'image_sha256':row['png_sha256'],
            'image_source_ns':obs['image_source_ns'],
            'joint_source_ns':raw[obs['source_lines']['joints']]['source_ns'],
            'hand_source_ns':raw[obs['source_lines']['hand_right']]['source_ns'],
            'state27':obs['state20']+obs['hand_right']['position']})
    with (output/'manifest.json').open('x') as f:
        json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False); f.write('\n')
    print(f"Exported {len(all_rows)} failed-trial observations, no actions, to {output}")


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--observations', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    prepare(a.observations, a.output)
