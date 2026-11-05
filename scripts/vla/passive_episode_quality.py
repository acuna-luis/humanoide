"""Offline checks and explicit timestamp pairing; never import a robot client."""
import bisect
import hashlib
import json
import math
from pathlib import Path

REQUIRED = ('rgb', 'joints', 'actuators', 'force_left', 'force_right')
HAND_SUFFIXES = ('thumb_swing', 'thumb_mcp', 'thumb_pip', 'index_mcp',
                 'middle_mcp', 'ring_mcp', 'little_mcp')


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
    hands, hand_commands = _read_optional_hands(directory)
    return _report(directory, manifest, groups, malformed, invalid, clock_warnings, ends, raw_counts,
                   tolerance_ms, hands, hand_commands)


def hand_vector(message, side):
    """Preserve measured names/order and check the known seven V4 joints."""
    if not isinstance(message, dict):
        raise ValueError('Hand message must be an object')
    names, positions = message.get('name'), message.get('position')
    if (not isinstance(names, list) or not isinstance(positions, list) or not names or
            len(names) != len(positions) or
            any(not isinstance(name, str) or not name for name in names) or
            len(set(names)) != len(names)):
        raise ValueError('Invalid hand names/positions')
    if any(type(value) not in (float, int) or not math.isfinite(value) for value in positions):
        raise ValueError('Missing or nonfinite hand position')
    expected = {side+'_'+suffix for suffix in HAND_SUFFIXES}
    actual = set(names)
    if actual != expected:
        raise ValueError('Unexpected V4 joints: missing='+repr(sorted(expected-actual))+
                         ', unexpected='+repr(sorted(actual-expected)))
    return {'name': names, 'position': positions}


def _read_optional_hands(directory):
    """Index optional hand data independently: failures never corrupt base QC."""
    hands = {kind: dict(rows=[], raw_count=0, invalid=[], joint_mismatch=False,
                        remote_errors=[], clock_warnings=[], discovery=None,
                        discovered=False, ever_subscribed=False, names=None)
             for kind in ('hand_left', 'hand_right')}
    commands = {kind: dict(raw_count=0, remote_errors=[], discovery=None, discovered=False, ever_subscribed=False)
                for kind in ('hand_command_left', 'hand_command_right')}
    with (directory/'samples.jsonl').open() as stream:
        for number, line in enumerate(stream, 1):
            try:
                row = json.loads(line)
            except (ValueError, TypeError):
                # The base analyzer reports malformed JSON; do not turn it into a hand sample.
                continue
            if not isinstance(row, dict):
                continue
            kind = row.get('kind')
            if kind == 'hand_error':
                stream = row.get('stream')
                if stream in hands:
                    hands[stream]['remote_errors'].append(str(row.get('error', 'unknown')))
                elif stream in commands:
                    commands[stream]['remote_errors'].append(str(row.get('error', 'unknown')))
                continue
            if kind == 'hand_discovery':
                topics = row.get('topics')
                if not isinstance(topics, dict):
                    for info in (*hands.values(), *commands.values()):
                        info['discovered'] = True
                    continue
                for key, info in (*hands.items(), *commands.items()):
                    if isinstance(topics.get(key), dict):
                        info['discovery'] = topics[key]
                        info['discovered'] = True
                        info['ever_subscribed'] |= topics[key].get('subscribed') is True
                continue
            if kind in commands:
                commands[kind]['raw_count'] += 1
                continue
            if kind not in hands:
                continue
            info = hands[kind]
            info['raw_count'] += 1
            try:
                source = row.get('source_ns')
                if type(source) is not int or source <= 0:
                    raise ValueError('Missing source timestamp')
                if info['rows'] and source <= info['rows'][-1]['source_ns']:
                    raise ValueError('Duplicate or regressing source timestamp')
                received, monotonic = row.get('received_ns'), row.get('received_monotonic_ns')
                if type(received) is not int or type(monotonic) is not int or monotonic <= 0:
                    raise ValueError('Missing reception timestamp')
                vector = hand_vector(row.get('message'), kind[len('hand_'):])
                if info['names'] is None:
                    info['names'] = set(vector['name'])
                if set(vector['name']) != info['names']:
                    raise ValueError('Hand joint names changed during capture')
                if not -50_000_000 <= received-source <= 500_000_000:
                    info['clock_warnings'].append(dict(line=number, receipt_minus_source_ms=(received-source)/1e6))
                info['rows'].append(dict(source_ns=source, received_monotonic_ns=monotonic,
                                         sample_line=number, hand=vector))
            except (ValueError, TypeError, KeyError) as exc:
                if str(exc).startswith('Unexpected V4 joints:'):
                    info['joint_mismatch'] = True
                info['invalid'].append(f'{number}: {exc}')
    return hands, commands


def _hand_discovery_status(info):
    if not info['discovered']:
        return 'not_recorded_by_version'
    discovery = info['discovery'] or {}
    if info['ever_subscribed']:
        return 'subscribed'
    if discovery.get('observed_types'):
        return 'type_mismatch_or_unsubscribed'
    return 'not_detected_at_discovery'


def _assess_hands(hands, commands, groups, matched, manifest, ends, complete, tolerance_ms):
    results = {}
    rgb_rows = {row['png_file']: row for row in groups['rgb']}
    for kind, info in hands.items():
        rows = info['rows']
        stamps = [row['source_ns'] for row in rows]
        stamps_index = list(stamps)
        matched_count, unmatched_count, boundary_count = 0, 0, 0
        for pair in matched:
            image = rgb_rows[pair['png_file']]
            if not rows or not stamps[0] <= image['source_ns'] <= stamps[-1]:
                boundary_count += 1
                continue
            candidate = nearest(rows, stamps_index, image['source_ns'])
            source_delta = (candidate['source_ns']-image['source_ns'])/1e6
            reception_delta = (candidate['received_monotonic_ns']-image['received_monotonic_ns'])/1e6
            if abs(source_delta) > tolerance_ms or abs(reception_delta) > 500:
                unmatched_count += 1
                continue
            pair[kind] = candidate['hand']
            pair['source_delta_ms'][kind] = source_delta
            pair['reception_delta_ms'][kind] = reception_delta
            pair['source_lines'][kind] = candidate['sample_line']
            matched_count += 1
        gaps = [(b-a)/1e9 for a, b in zip(stamps, stamps[1:])]
        span = (stamps[-1]-stamps[0])/1e9 if len(stamps)>1 else 0
        count_match = bool(complete and ends[0].get('counts', {}).get(kind, 0) == info['raw_count'])
        discovery_status = _hand_discovery_status(info)
        present = info['ever_subscribed'] or info['raw_count'] > 0 or bool(info['remote_errors'])
        passed = bool(present and complete and count_match and len(rows) >= 2 and not info['invalid']
                      and not info['remote_errors'] and not info['clock_warnings']
                      and span >= .8*manifest.get('requested_seconds', 0)
                      and gaps and max(gaps) <= .5 and matched_count >= 2 and unmatched_count == 0)
        if not present:
            status = discovery_status
        elif info['joint_mismatch']:
            status = 'incomplete_or_unknown_joints'
        elif info['invalid'] or info['remote_errors'] or info['clock_warnings']:
            status = 'invalid'
        elif not info['raw_count']:
            status = 'subscribed_no_samples'
        else:
            status = 'complete' if passed else 'partial'
        results[kind] = dict(status=status, discovery_status=discovery_status,
            capture_checks_passed=passed if present else None, discovery=info['discovery'],
            raw_samples=info['raw_count'], valid_samples=len(rows),
            source_span_s=span, max_gap_s=max(gaps) if gaps else None,
            matched_frames=matched_count, unmatched_frames=unmatched_count,
            excluded_boundary_frames=boundary_count, sample_counts_match=count_match if present else None,
            invalid=info['invalid'][:30], remote_errors=info['remote_errors'][:30],
            clock_warnings=info['clock_warnings'][:30])
    command_results = {}
    for kind, info in commands.items():
        command_results[kind] = dict(discovery_status=_hand_discovery_status(info),
            discovery=info['discovery'], raw_samples=info['raw_count'],
            sample_counts_match=(ends[0].get('counts', {}).get(kind, 0) == info['raw_count']) if complete else None,
            remote_errors=info['remote_errors'][:30],
            note='Raw optional events; best-effort reception does not prove no losses; not qualified as training actions.')
    return results, command_results


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


def _report(directory, manifest, groups, malformed, invalid, clock_warnings, ends, raw_counts, tolerance_ms,
            hands, hand_commands):
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
    hand_report, hand_command_report = _assess_hands(
        hands, hand_commands, groups, matched, manifest, ends, complete, tolerance_ms)
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
        hands=hand_report, hand_commands=hand_command_report,
        limitations=['Source timestamps are retained without clock adjustment; pairing checks source and common reception time.',
            'Receipt-minus-source checks do not establish sensor synchronization or clock calibration.',
            'cmd_pos is an actuator setpoint; official training action provenance remains unqualified.',
            'No interpolation, resampling, LeRobot conversion, model training or motion is performed.',
            'Episode success and scene/task labels require operator review.'])
    (directory/'aligned.jsonl').write_text(''.join(json.dumps(row,allow_nan=False)+'\n' for row in matched))
    (directory/'quality.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report
