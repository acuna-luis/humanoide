#!/usr/bin/env python3
"""Export manually reviewed ball episodes for offline analysis, never robot control.

This is NOT a LeRobot training dataset: actuator commands and hand control
semantics are not qualified, clocks are not calibrated, and no action column
is generated. Inputs are read only; output must be a new directory.
"""
import argparse
import bisect
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import sys


TASK = "Pick up the tennis ball with the right hand, lift it, lower it and release it."
RIGHT_HAND = ["right_thumb_swing", "right_thumb_mcp", "right_thumb_pip",
              "right_index_mcp", "right_middle_mcp", "right_ring_mcp", "right_little_mcp"]


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def finite_vector(value, size):
    return (isinstance(value, list) and len(value) == size and
            all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in value))


def load_json(path):
    with path.open(encoding='utf-8') as f:
        return json.load(f)


def iter_jsonl(path):
    with path.open(encoding='utf-8') as f:
        for lineno, line in enumerate(f, 1):
            try:
                yield lineno, json.loads(line)
            except (ValueError, TypeError) as e:
                raise ValueError(f'{path}:{lineno}: invalid JSON') from e


def load_segments(path):
    spec = load_json(path)
    if not isinstance(spec, dict) or not isinstance(spec.get('segments'), list) or not spec['segments']:
        raise ValueError('segments specification must contain a non-empty segments array')
    result, seen, source_splits = [], set(), {}
    for s in spec['segments']:
        if not isinstance(s, dict):
            raise ValueError('segment must be an object')
        ident = s.get('id')
        if not isinstance(ident, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', ident) or ident in seen:
            raise ValueError('segment ids must be distinct safe identifiers')
        seen.add(ident)
        lo, hi = s.get('start_frame'), s.get('end_frame')
        if any(isinstance(x, bool) or not isinstance(x, int) for x in (lo, hi)) or not 0 <= lo <= hi:
            raise ValueError(f'{ident}: invalid frame interval')
        if s.get('status') not in {'assisted', 'failed', 'unreviewed', 'candidate_success'}:
            raise ValueError(f'{ident}: status must be assisted, failed, unreviewed or candidate_success')
        if not isinstance(s.get('notes'), str) or not s['notes'].strip():
            raise ValueError(f'{ident}: notes must describe review and intervention')
        if not isinstance(s.get('source_dir'), str):
            raise ValueError(f'{ident}: source_dir missing')
        source = Path(s['source_dir']).expanduser().resolve(strict=True)
        if not source.is_dir():
            raise ValueError(f'{ident}: source_dir is not a directory')
        split = s.get('split', 'unassigned')
        if split not in {'unassigned', 'inspection_train', 'inspection_validation', 'inspection_test'}:
            raise ValueError(f'{ident}: invalid inspection split')
        # One original capture cannot appear in multiple splits, including unassigned.
        previous_split = source_splits.setdefault(source, split)
        if previous_split != split:
            raise ValueError(f'{ident}: source capture assigned to multiple inspection splits')
        for previous in result:
            if (previous['source'] == source and lo <= previous['end_frame'] and hi >= previous['start_frame']):
                raise ValueError(f'{ident}: overlapping intervals in same source')
        result.append(dict(s, source=source, split=split))
    return result


def read_source(source):
    checksums = {}
    with (source / 'SHA256SUMS').open(encoding='utf-8') as f:
        for line in f:
            match = re.fullmatch(r'([0-9a-f]{64})  (.+)\n?', line)
            if not match or match[2] in checksums:
                raise ValueError(f'{source}: malformed or duplicate SHA256SUMS')
            checksums[match[2]] = match[1]
    for name in ('manifest.json', 'quality.json', 'aligned.jsonl', 'samples.jsonl'):
        if checksums.get(name) != digest(source / name):
            raise ValueError(f'{source}: missing or invalid source checksum for {name}')
    metadata = {name: load_json(source / name) for name in ('manifest.json', 'quality.json')}
    frames = {}
    for lineno, row in iter_jsonl(source / 'aligned.jsonl'):
        name = row.get('png_file')
        if not isinstance(name, str) or not re.fullmatch(r'rgb/[0-9]{6}\.png', name):
            raise ValueError(f'{source}/aligned.jsonl:{lineno}: invalid image name')
        n = int(Path(name).stem)
        if n in frames:
            raise ValueError(f'{source}: duplicate aligned frame {n}')
        frames[n] = row
    commands = []
    for lineno, row in iter_jsonl(source / 'samples.jsonl'):
        if row.get('kind') != 'hand_command_right':
            continue
        stamp, msg = row.get('source_ns'), row.get('message')
        if not isinstance(stamp, int) or isinstance(stamp, bool) or not isinstance(msg, dict):
            continue
        mode, names = msg.get('mode'), msg.get('names')
        if names != RIGHT_HAND or not isinstance(mode, list) or len(mode) != 7 or any(type(x) is not int for x in mode):
            continue
        commands.append((stamp, lineno, mode))
    # Sorting does not certify clock correctness. Duplicate timestamps remain visible.
    commands.sort(key=lambda x: (x[0], x[1]))
    metadata['hashes'] = {name: digest(source / name) for name in
                          ('manifest.json', 'quality.json', 'aligned.jsonl', 'samples.jsonl')}
    metadata['checksums'] = checksums
    return metadata, frames, commands


def latest_intent(commands, times, image_ns, max_age_ms):
    """Last observed command at or before frame, never a future sample."""
    i = bisect.bisect_right(times, image_ns) - 1
    if i < 0:
        return {'value': 'unknown', 'reason': 'no_prior_command'}
    stamp, line, mode = commands[i]
    age = (image_ns - stamp) / 1e6
    if age > max_age_ms:
        return {'value': 'unknown', 'reason': 'prior_command_stale', 'age_ms': age, 'source_line': line}
    first = bisect.bisect_left(times, stamp)
    if any(other[2] != mode for other in commands[first:i]):
        return {'value': 'unknown', 'reason': 'conflicting_commands_at_same_timestamp',
                'age_ms': age, 'source_line': line}
    if mode == [5] * 7:
        value = 'open_candidate'
    elif mode == [7] * 7:
        value = 'grasp_hold_candidate'
    else:
        value = 'unknown'
    return {'value': value, 'mode': mode, 'command_source_ns': stamp,
            'age_ms': age, 'source_line': line, 'provisional': True}


def export(spec_path, output, max_age_ms):
    segments = load_segments(spec_path)
    if not math.isfinite(max_age_ms) or max_age_ms <= 0:
        raise ValueError('max command age must be positive and finite')
    out = output.expanduser().resolve()
    # Protect sources, specification and ancestors; no writing within a capture.
    for seg in segments:
        if out == seg['source'] or seg['source'] in out.parents or out in seg['source'].parents:
            raise ValueError('output cannot be a source capture or within/above one')
    if out.exists():
        raise ValueError('output already exists; refusing to overwrite')
    if not out.parent.is_dir():
        raise ValueError('output parent directory must already exist')

    sources = {}
    for segment in segments:
        source = segment['source']
        if source not in sources:
            sources[source] = read_source(source)
        metadata, frames, _ = sources[source]
        prior = None
        for n in range(segment['start_frame'], segment['end_frame'] + 1):
            if n not in frames:
                raise ValueError(f"{segment['id']}: missing aligned frame {n}")
            row = frames[n]
            stamp, hand = row.get('image_source_ns'), row.get('hand_right')
            if not isinstance(stamp, int) or isinstance(stamp, bool) or (prior is not None and stamp <= prior):
                raise ValueError(f"{segment['id']}: invalid or non-increasing image timestamp at {n}")
            prior = stamp
            if not finite_vector(row.get('state20'), 20) or not isinstance(hand, dict) or hand.get('name') != RIGHT_HAND or not finite_vector(hand.get('position'), 7):
                raise ValueError(f"{segment['id']}: incomplete/nonfinite state at {n}")
            image = source / row['png_file']
            if not image.is_file() or source not in image.resolve().parents:
                raise ValueError(f"{segment['id']}: missing or unsafe image at {n}")
            if metadata['checksums'].get(row['png_file']) != digest(image):
                raise ValueError(f"{segment['id']}: source image checksum mismatch at {n}")

    out.mkdir()  # Never overwrite; a partial directory is intentionally retained on error.
    manifest = {'schema': 'cruzr_ball_observations_v1', 'task': TASK, 'training_ready': False,
                'physical_control_qualified': False, 'has_action_column': False,
                'segments_spec_sha256': digest(spec_path), 'command_max_age_ms': max_age_ms,
                'limitations': ['observation export only; not a LeRobot training dataset',
                    'inspection splits are tentative only, and do not prove independent sessions or readiness for training',
                    'mode labels are correlations, not measured trigger or qualified control semantics',
                    'raw commands received best-effort; timestamps do not establish physical synchronization',
                    'actuator cmd_pos is motor-space and not a validated joint-space action',
                    'source captures may be incomplete and are not certified by this export',
                    '20 cm lift and safety of physical control are not validated'], 'segments': []}
    for segment in segments:
        source = segment['source']
        metadata, frames, commands = sources[source]
        times = [x[0] for x in commands]
        target = out / segment['id']
        (target / 'rgb').mkdir(parents=True)
        counts = {'open_candidate': 0, 'grasp_hold_candidate': 0, 'unknown': 0}
        with (target / 'observations.jsonl').open('x', encoding='utf-8') as f:
            for n in range(segment['start_frame'], segment['end_frame'] + 1):
                source_row = frames[n]
                src = source / source_row['png_file']
                dest = target / 'rgb' / f'{n:06}.png'
                shutil.copyfile(src, dest)
                source_hash, dest_hash = digest(src), digest(dest)
                if source_hash != dest_hash:
                    raise ValueError(f'{segment["id"]}: image copy checksum mismatch {n}')
                intent = latest_intent(commands, times, source_row['image_source_ns'], max_age_ms)
                counts[intent['value']] += 1
                record = {'source_frame': n, 'png_file': f'rgb/{n:06}.png', 'png_sha256': source_hash,
                          'observations': source_row, 'right_hand_intent_candidate': intent}
                f.write(json.dumps(record, allow_nan=False, ensure_ascii=False) + '\n')
        manifest['segments'].append({'id': segment['id'], 'source_dir': str(source),
            'source_hashes': metadata['hashes'], 'source_capture_checks_passed': metadata['quality.json'].get('capture_checks_passed'),
            'source_training_ready': metadata['quality.json'].get('training_ready'),
            'start_frame': segment['start_frame'], 'end_frame': segment['end_frame'],
            'status': segment['status'], 'notes': segment['notes'], 'split': segment['split'],
            'frame_count': segment['end_frame']-segment['start_frame']+1,
            'intention_candidate_counts': counts, 'observations_sha256': digest(target / 'observations.jsonl')})
    with (out / 'manifest.json').open('x', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')
    return manifest


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--segments', type=Path, required=True, help='JSON specification with manually reviewed segment intervals')
    p.add_argument('--output', type=Path, required=True, help='new directory; parent must already exist')
    p.add_argument('--max-command-age-ms', type=float, default=80.0, help='observation annotation freshness threshold, not a control limit')
    args = p.parse_args(argv)
    try:
        manifest = export(args.segments, args.output, args.max_command_age_ms)
    except (OSError, ValueError, KeyError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    print(json.dumps({'output': str(args.output), 'segments': len(manifest['segments']),
                      'training_ready': False, 'physical_control_qualified': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
