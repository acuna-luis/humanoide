"""Offline checks and explicit timestamp pairing; never import a robot client."""
import bisect
import hashlib
import json
import math
from pathlib import Path

REQUIRED = ('rgb', 'joints', 'actuators', 'force_left', 'force_right')


def vector(message, names, *, commands=False):
    if not isinstance(message,dict):
        raise ValueError('Message must be an object')
    if commands:
        rows = message.get('act_item', [])
        mapping = {}
        for row in rows:
            name = row.get('name', '')
            if name.endswith('_motor'):
                name = name[:-6]+'_joint'
            if name in mapping:
                raise ValueError('Duplicate actuator name')
            mapping[name] = row.get('cmd_pos')
    else:
        keys, values = message.get('name', []), message.get('position', [])
        if len(keys) != len(values) or len(keys) != len(set(keys)):
            raise ValueError('Invalid joint names/positions')
        mapping = dict(zip(keys, values))
    result = [mapping.get(name) for name in names]
    if any(type(v) not in (float, int) or not math.isfinite(v) for v in result):
        raise ValueError('Missing/nonfinite 20D '+('cmd_pos' if commands else 'positions'))
    return result


def wrench(message):
    value = message['wrench']
    result = [value[field][axis] for field in ('force', 'torque') for axis in 'xyz']
    if any(type(v) not in (float, int) or not math.isfinite(v) for v in result):
        raise ValueError('Invalid wrench')
    return result


def nearest(rows, stamps, stamp):
    if not rows:
        return None
    index = bisect.bisect_left(stamps, stamp)
    return min((rows[i] for i in (index-1, index) if 0 <= i < len(rows)),
               key=lambda row: abs(row['source_ns']-stamp))


def analyze(directory, tolerance_ms=80):
    directory = Path(directory)
    manifest = json.loads((directory/'manifest.json').read_text())
    names = manifest['joint_names']
    if len(names) != 20 or len(set(names)) != 20:
        raise ValueError('Expected unique 20D profile')
    groups = {key: [] for key in REQUIRED}
    malformed, clock_warnings, invalid, ends, raw_counts = [], [], [], [], {}
    last = {}
    with (directory/'samples.jsonl').open() as stream:
        # Keep only indexed metadata/vectors; raw messages remain on disk.
        lines = _checked_rows(stream, directory, names, groups, last,
                              malformed, invalid, clock_warnings, ends, raw_counts)
        for row in lines:
            row.pop('message', None)
            groups[row['kind']].append(row)
    return _report(directory, manifest, groups, malformed, invalid, clock_warnings, ends, raw_counts, tolerance_ms)


def _checked_rows(stream, directory, names, groups, last, malformed, invalid, clock_warnings, ends, raw_counts):
    for number, line in enumerate(stream, 1):
        try:
            row = json.loads(line)
            if not isinstance(row,dict):
                raise ValueError('Sample must be an object')
            kind = row.get('kind')
            if kind in (*REQUIRED, 'sdk_command'):
                raw_counts[kind] = raw_counts.get(kind, 0)+1
            if kind == 'end':
                ends.append(row)
            if kind not in groups:
                continue
            source = row.get('source_ns')
            if type(source) is not int or source <= 0:
                invalid.append(f'{number}: missing source timestamp'); continue
            if kind in last and source <= last[kind]:
                invalid.append(f'{number}: duplicate/regressing {kind} timestamp'); continue
            last[kind] = source
            age = row['received_ns']-source
            if not -50_000_000 <= age <= 500_000_000:
                clock_warnings.append(dict(line=number, kind=kind, receipt_minus_source_ms=age/1e6))
            if kind == 'joints':
                row['state20'] = vector(row['message'], names)
            elif kind == 'actuators':
                row['actuator_cmd_pos20'] = vector(row['message'], names, commands=True)
            elif kind.startswith('force_'):
                row['wrench6'] = wrench(row['message'])
            elif kind == 'rgb':
                path = directory/row['png_file']
                if path.parent != directory/'rgb' or not path.name.endswith('.png'):
                    raise ValueError('Invalid PNG path')
                data = path.read_bytes()
                if not data.startswith(b'\x89PNG\r\n\x1a\n') or hashlib.sha256(data).hexdigest() != row['png_sha256']:
                    raise ValueError('Missing/corrupt PNG')
            row['sample_line'] = number
            yield row
        except (ValueError, KeyError, TypeError, OSError) as exc:
            malformed.append(f'{number}: {exc}')


def _report(directory, manifest, groups, malformed, invalid, clock_warnings, ends, raw_counts, tolerance_ms):
    indices = {key: [row['source_ns'] for row in rows] for key, rows in groups.items()}
    matched, unmatched, boundary_frames = [], 0, 0
    limit = tolerance_ms*1e6
    coverage_start = max((rows[0]['source_ns'] for rows in groups.values() if rows), default=0)
    coverage_end = min((rows[-1]['source_ns'] for rows in groups.values() if rows), default=0)
    for image in groups['rgb']:
        if not coverage_start <= image['source_ns'] <= coverage_end:
            boundary_frames += 1
            continue
        paired = {key: nearest(groups[key], indices[key], image['source_ns']) for key in REQUIRED if key != 'rgb'}
        if any(row is None or abs(row['source_ns']-image['source_ns']) > limit or
               abs(row['received_monotonic_ns']-image['received_monotonic_ns']) > 500_000_000
               for row in paired.values()):
            unmatched += 1; continue
        matched.append(dict(png_file=image['png_file'], image_source_ns=image['source_ns'],
            state20=paired['joints']['state20'], actuator_cmd_pos20=paired['actuators']['actuator_cmd_pos20'],
            force_left6=paired['force_left']['wrench6'], force_right6=paired['force_right']['wrench6'],
            source_delta_ms={key:(row['source_ns']-image['source_ns'])/1e6 for key, row in paired.items()},
            reception_delta_ms={key:(row['received_monotonic_ns']-image['received_monotonic_ns'])/1e6 for key, row in paired.items()},
            source_lines={key:row['sample_line'] for key, row in paired.items()},
            action_semantics='actuator cmd_pos; not qualified as official teleoperation action'))
    streams = {}
    for kind, rows in groups.items():
        stamps = [row['source_ns'] for row in rows]
        gaps = [(b-a)/1e9 for a,b in zip(stamps, stamps[1:])]
        streams[kind] = dict(valid_samples=len(rows), max_gap_s=max(gaps) if gaps else None,
            source_span_s=(stamps[-1]-stamps[0])/1e9 if len(stamps)>1 else 0,
            observed_hz=(len(rows)-1)/((stamps[-1]-stamps[0])/1e9) if len(stamps)>1 else None)
    transport = manifest.get('transport', {})
    complete = len(ends) == 1 and not ends[0].get('errors') and not ends[0].get('stopped')
    counts_match = complete and all(ends[0].get('counts',{}).get(k) == raw_counts.get(k,0) for k in REQUIRED)
    span_pass = all(row['source_span_s'] >= .8*manifest.get('requested_seconds',0) for row in streams.values())
    gap_pass = all(row['max_gap_s'] is not None and row['max_gap_s'] <= (
        max(.5,3/manifest.get('fps_limit',5)) if key == 'rgb' else .5) for key,row in streams.items())
    passed = bool(complete and transport.get('returncode') == 0 and not transport.get('error') and
                  not malformed and not invalid and not clock_warnings and all(len(groups[k]) >= 2 for k in REQUIRED)
                  and len(matched) >= 2 and unmatched == 0 and counts_match and span_pass and gap_pass)
    report = dict(schema='cruzr-passive-episode-qc-v1', capture_checks_passed=passed,
        training_ready=False, task=manifest['task'], outcome='unreviewed',
        streams=streams, matched_frames=len(matched), unmatched_frames=unmatched,
        excluded_boundary_frames=boundary_frames, reception_pairing_limit_ms=500,
        identical_pixel_frames=len(groups['rgb'])-len({r['pixels_sha256'] for r in groups['rgb']}),
        pairing_tolerance_ms=tolerance_ms, malformed=malformed[:30], invalid=invalid[:30],
        clock_warnings=clock_warnings[:30], stream_complete=complete,
        sample_counts_match=counts_match, source_span_checks_passed=span_pass, gap_checks_passed=gap_pass,
        limitations=['Source timestamps are retained without clock adjustment; pairing checks source and common reception time.',
            'Receipt-minus-source checks do not establish sensor synchronization or clock calibration.',
            'cmd_pos is an actuator setpoint; official training action provenance remains unqualified.',
            'No interpolation, resampling, LeRobot conversion, model training or motion is performed.',
            'Episode success and scene/task labels require operator review.'])
    (directory/'aligned.jsonl').write_text(''.join(json.dumps(row,allow_nan=False)+'\n' for row in matched))
    (directory/'quality.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report
