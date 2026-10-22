"""Recover a measured pickup reference from a clean, completed source segment.

Pure historical evidence validation: no files, clocks, clients or commands.
The returned reference replaces only the resume comparison target, never the
saved map point. Fresh odometry, health and 20 mm / 2 degree arrival checks are
still required by the caller. An assumed held boundary is not sensor evidence.
"""
import copy
import hashlib
import json
import math
import uuid

if __package__:
    from . import scenario1_contract as contract
    from . import scenario1_box_alignment as alignment
    from . import scenario1_perception as perception
else:
    import scenario1_contract as contract
    import scenario1_box_alignment as alignment
    import scenario1_perception as perception


SCHEMA = 'scenario1-aligned-pickup-reference-v1'
_MARKERS = {'ready', 'armed', 'checkpoint', 'stage_complete', 'session_finishing',
            'box_alignment', 'box_alignment_base', 'box_alignment_capture',
            'box_alignment_time_pair', 'box_alignment_freshness',
            'box_alignment_association', 'pose_check', 'arrival', 'error'}
_ACTION_EVENTS = {'dispatched', 'accepted', 'result', 'request_complete',
                  'error', 'cancel_requested', 'cancel_response',
                  'interrupted_terminal', 'terminal_unknown', 'worker_closed',
                  'worker_exit_unconfirmed', 'status', 'correction_guard'}


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _digest(value):
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _fail(reason):
    raise ValueError('RESUME_PICKUP_REFERENCE_INVALID: '+reason)


def _integer(value, label):
    if type(value) is not int or value <= 0:
        _fail(label+' must be a positive integer')
    return value


def _number(value, label):
    if type(value) not in (int, float) or not math.isfinite(value):
        _fail(label+' must be finite numeric')
    return float(value)


def _pose(value):
    if not isinstance(value, dict):
        _fail('map pose missing')
    result = {key: _number(value.get(key), 'map '+key) for key in ('x', 'y', 'yaw')}
    result['stamp_ns'] = _integer(value.get('stamp_ns'), 'map stamp')
    return result


def _one(rows, predicate, label):
    found = [row for row in rows if predicate(row)]
    if len(found) != 1:
        _fail('expected exactly one '+label)
    return found[0]


def _before(row, other):
    return row['time_ns'] < other['time_ns']


def _motion_result(rows, start, end, kind, attempt=None):
    window = [r for r in rows if start < r['time_ns'] < end
              and r['event'] == 'action' and r.get('kind') == kind]
    dispatched = _one(window, lambda r: r['detail']['event'] == 'dispatched', kind+' dispatch')
    detail = dispatched['detail']
    goal_id, request_id = detail.get('goal_id'), detail.get('request_id')
    try:
        if str(uuid.UUID(goal_id)) != goal_id:
            _fail('noncanonical native UUID')
    except (ValueError, TypeError, AttributeError):
        _fail('invalid native UUID')
    expected_endpoint = '/mc/manipulation/action' if kind == 'motion' else '/vnav/task/command'
    if detail.get('endpoint') != expected_endpoint or not isinstance(request_id, str) or not request_id:
        _fail('native endpoint/request identity differs')
    relevant = [r for r in window if r['detail'].get('request_id') == request_id]
    if any(r['detail'].get('event') in _ACTION_EVENTS and
           r['detail'].get('request_id') != request_id for r in window):
        _fail('another native request overlaps the source action')
    for row in relevant:
        d = row['detail']
        guard = d['event'] == 'correction_guard'
        if guard:
            snapshot = d.get('snapshot', {})
            if any(snapshot.get(k) is not None for k in ('failure', 'velocity_violation', 'telemetry_failure')):
                _fail('correction guard reported a fault')
        if (d['event'] != 'request_complete' and d.get('goal_id') != goal_id and
                not (guard and d.get('phase') in ('preparing', 'armed') and d.get('goal_id') is None)):
            _fail('native UUID changed')
        if d['event'] in ('error', 'cancel_requested', 'cancel_response', 'terminal_unknown',
                          'interrupted_terminal', 'worker_exit_unconfirmed'):
            _fail('native action failed or was cancelled')
        if d['event'] == 'status' and (type(d.get('status')) is not int or d['status'] not in (1, 2, 4)):
            _fail('contradictory native terminal')
    accepted = _one(relevant, lambda r: r['detail']['event'] == 'accepted', kind+' acceptance')
    result = _one(relevant, lambda r: r['detail']['event'] == 'result', kind+' result')
    complete = _one(relevant, lambda r: r['detail']['event'] == 'request_complete', kind+' completion')
    if (accepted['detail'].get('accepted') is not True or
            type(complete['detail'].get('returncode')) is not int or complete['detail']['returncode'] != 0 or
            not dispatched['time_ns'] < accepted['time_ns'] < result['time_ns'] < complete['time_ns']):
        _fail('native action has no clean ordered terminal')
    validator = contract.validate_motion_result if kind == 'motion' else contract.validate_navigation_result
    validator(result['detail'])
    if kind == 'navigation':
        terminal = _one(relevant, lambda r: r['detail'].get('event') == 'correction_guard' and
                        r['detail'].get('phase') == 'terminal', 'settled correction guard')['detail']['snapshot']
        if (terminal.get('point') != 'box_pickup' or type(terminal.get('attempt')) is not int or
                terminal['attempt'] != attempt or terminal.get('armed') is not True or
                terminal.get('settled') is not True):
            _fail('correction terminal guard lacks measured settlement')
    return goal_id


def _proof(rows):
    """Retain every navigation terminal/dispatch and every relevant marker."""
    result = []
    for row in rows:
        event = row.get('event')
        if event in _MARKERS or (event == 'action' and row.get('detail', {}).get('event') in _ACTION_EVENTS):
            result.append(copy.deepcopy(row))
        elif event == 'health_worker' and row.get('detail', {}).get('event') in ('error', 'worker_exit_unconfirmed'):
            result.append(copy.deepcopy(row))
    return result


def _derive(rows, checkpoint, context, profile):
    source = contract.validate_checkpoint(checkpoint, profile)
    if (source['box_state'] != 'held' or source['failure'] is not None or source['in_flight'] is not None or
            contract.progress_index(source) != contract.STAGES.index('retreat') or
            source['completed'][-2:] != ['grasp', 'verify_held']):
        _fail('requires a clean held boundary immediately after native grasp')
    _canonical(context)
    if not isinstance(context, dict) or set(context) != {'boot_id', 'containers', 'dependencies', 'points', 'execution_profile'}:
        _fail('source context is incomplete')
    if context['execution_profile'] != contract.execution_profile(source):
        _fail('execution profile/context mismatch')
    if not isinstance(rows, list) or not rows or len(rows) > 100000:
        _fail('source events must be a bounded nonempty list')
    previous = 0
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('event'), str):
            _fail('malformed source event')
        stamp = _integer(row.get('time_ns'), 'event timestamp')
        if stamp < previous:
            _fail('source event timestamps regressed')
        previous = stamp
    _canonical(rows)
    finish = _one(rows, lambda r: r['event'] == 'session_finishing', 'session finish')
    if finish.get('reason') != 'requested':
        _fail('source segment did not finish on request')
    active = [r for r in rows if r['time_ns'] <= finish['time_ns']]
    if any(r['event'] == 'error' or r.get('detail', {}).get('event') in
           ('error', 'worker_exit_unconfirmed', 'terminal_unknown', 'cancel_requested', 'cancel_response', 'interrupted_terminal')
           for r in active):
        _fail('source segment contains an error, cancellation or unknown result')
    ready = _one(active, lambda r: r['event'] == 'ready', 'source session readiness')
    if ready.get('context') != context or ready.get('points') != context['points'] or ready.get('map_name') != 'utars_nav_map':
        _fail('recorded source context/map differs')
    armed = _one(active, lambda r: r['event'] == 'armed', 'source arming')
    if not _before(ready, armed):
        _fail('source was not armed after readiness')
    held = _one(active, lambda r: r['event'] == 'checkpoint' and r.get('checkpoint') == source, 'matching held checkpoint')
    complete = _one(active, lambda r: r['event'] == 'stage_complete' and r.get('stage') == 'grasp', 'grasp stage completion')
    verified = _one(active, lambda r: r['event'] == 'stage_complete' and r.get('stage') == 'verify_held', 'held stage completion')
    if (complete.get('logical_assumption') is not False or
            not complete['time_ns'] < held['time_ns'] < verified['time_ns'] < finish['time_ns']):
        _fail('held boundary does not follow a native grasp completion')
    aligned = _one(active, lambda r: r['event'] == 'box_alignment' and r.get('phase') == 'ready', 'alignment readiness')
    if not armed['time_ns'] < aligned['time_ns'] < complete['time_ns']:
        _fail('alignment readiness outside grasp source segment')
    attempts = alignment.validate_max_corrections(aligned.get('attempts'))
    if aligned.get('inside_margin_m') != alignment.POLICY['inside_margin_m']:
        _fail('alignment envelope policy differs')
    requested = _number(aligned.get('total_requested_m'), 'requested alignment distance')
    if not 0 <= requested <= alignment.POLICY['max_total_m']+1e-12:
        _fail('alignment distance budget exceeded')
    observations = [r for r in active if r['event'] == 'box_alignment' and r.get('phase') == 'observed'
                    and armed['time_ns'] < r['time_ns'] < aligned['time_ns']]
    if len(observations) != attempts+1:
        _fail('alignment measurement chain incomplete')
    observed = observations[-1]
    if aligned.get('observation') != observed.get('observation') or alignment.displacement(aligned['observation']) != {'x': 0., 'y': 0.}:
        _fail('alignment ready pose is not the final in-envelope observation')
    corrections = [r for r in active if r['event'] == 'box_alignment' and r.get('phase') == 'in_flight']
    arrivals = [r for r in active if r['event'] == 'box_alignment' and r.get('phase') == 'arrival']
    if len(corrections) != attempts or len(arrivals) != attempts:
        _fail('alignment correction/arrival count differs')
    total = 0.
    for n, (correction, arrival) in enumerate(zip(corrections, arrivals), 1):
        if (type(correction.get('attempt')) is not int or correction['attempt'] != n or
                type(arrival.get('attempt')) is not int or arrival['attempt'] != n or
                not observations[n-1]['time_ns'] < correction['time_ns'] < arrival['time_ns'] < observations[n]['time_ns']):
            _fail('alignment attempt order differs')
        delta = correction.get('displacement_base_m', {})
        step = math.hypot(*(_number(delta.get(k), 'correction '+k) for k in 'xy'))
        total += step
        if not 0 < step <= alignment.POLICY['max_step_m']+1e-12 or total > alignment.POLICY['max_total_m']+1e-12:
            _fail('alignment correction distance outside fixed budget')
        if abs(_number(correction.get('total_requested_m'), 'reserved distance')-total) > 1e-12:
            _fail('alignment reservation differs')
        if (correction.get('observation') != observations[n-1]['observation'] or
                delta != alignment.displacement(correction['observation']) or
                correction.get('spec', {}).get('reference') != observations[n-1]['reference'] or
                correction['spec'].get('target') != alignment.target(observations[n-1]['reference'], delta)):
            _fail('correction target differs from the measured observation/reference')
        _motion_result(active, correction['time_ns'], arrival['time_ns'], 'navigation', attempt=n)
        measures = arrival.get('measurements')
        if not isinstance(measures, list) or len(measures) != 2:
            _fail('two correction arrival measurements required')
        for measure in measures:
            if (not 0 <= _number(measure.get('distance_m'), 'arrival distance') <= alignment.POLICY['max_arrival_distance_m']+1e-12 or
                    not 0 <= _number(measure.get('yaw_error_deg'), 'arrival yaw') <= alignment.POLICY['max_arrival_yaw_deg']+1e-12):
                _fail('correction arrival was outside tolerance')
    if abs(total-requested) > 1e-12:
        _fail('final alignment distance differs from reservations')
    captures = [r for r in active if r['event'] == 'box_alignment_capture' and r['time_ns'] < observed['time_ns']]
    if len(captures) < 2 or [r.get('phase') for r in captures[-2:]] != ['first', 'second']:
        _fail('final two visual captures missing')
    for capture in captures[-2:]:
        pending = alignment.observe(capture['observation']['detection'], capture['received_ns'])
        if pending != capture['observation']:
            _fail('visual capture differs from original detection')
    first, second = [r['observation'] for r in captures[-2:]]
    if second != observed['observation'] or perception.validate_pair(first, second) != observed.get('stability'):
        _fail('final visual stability chain differs')
    pair_rows = [r for r in active if r['event'] == 'box_alignment_time_pair' and r['time_ns'] < observed['time_ns']]
    if not pair_rows:
        _fail('final map/image correspondence missing')
    paired = pair_rows[-1]
    reference = _pose(observed.get('reference'))
    if paired.get('current_reference') != observed['reference'] or not isinstance(paired.get('matches'), list) or len(paired['matches']) != 2:
        _fail('map reference does not match final observed pair')
    for match, pending in zip(paired['matches'], (first, second)):
        if match.get('image_stamp_ns') != pending['stamp_ns'] or len(match.get('poses', [])) != 2:
            _fail('map/image match differs')
        samples = [_pose(p) for p in match['poses']]
        if samples[0]['stamp_ns'] >= samples[1]['stamp_ns'] or any(abs(p['stamp_ns']-pending['stamp_ns']) > 500_000_000 for p in samples):
            _fail('map/image match is not fresh and advancing')
        for sample in samples:
            alignment.stable_base([sample, reference])
    pose_rows = [r for r in active if r['event'] == 'pose_check' and r['time_ns'] < paired['time_ns']]
    if not pose_rows:
        _fail('final measured map samples missing')
    pose_row = pose_rows[-1]
    if type(pose_row.get('publisher_count')) is not int or pose_row['publisher_count'] != 2 or len(pose_row.get('measurements', [])) != 2:
        _fail('final map samples lack expected publisher count/pair')
    samples = [_pose(p) for p in pose_row['measurements']]
    if samples[-1] != reference or samples[0]['stamp_ns'] >= samples[1]['stamp_ns']:
        _fail('reference is not the last measured map sample')
    for sample in samples:
        if not 0 <= pose_row['time_ns']-sample['stamp_ns'] <= 500_000_000:
            _fail('final map source stamp was stale')
    alignment.stable_base(samples)
    if not second['stamp_ns'] < samples[0]['stamp_ns'] < observed['time_ns'] < aligned['time_ns']:
        _fail('reference is not from post-detection measured samples')
    if attempts:
        assoc_rows = [r for r in active if r['event'] == 'box_alignment_association' and observed['time_ns'] < r['time_ns'] < aligned['time_ns']]
        associated = _one(assoc_rows, lambda r: r.get('passed') is True, 'final same-box association')
        expected_association = alignment.validate_association(observations[0].get('association'), observed.get('association'))
        if associated.get('measurement') != expected_association:
            _fail('same-box association differs')
    goal_id = _motion_result(active, aligned['time_ns'], complete['time_ns'], 'motion')
    if any(r['event'] == 'action' and r.get('kind') in ('navigation', 'planning') and
           r.get('detail', {}).get('event') == 'dispatched' and
           aligned['time_ns'] < r['time_ns'] <= finish['time_ns'] for r in active):
        _fail('chassis/planner action occurred after alignment reference')
    return dict(schema=SCHEMA, source_checkpoint_sha256=_digest(source), source_context_sha256=_digest(context),
                profile_id=source['profile_id'], profile_sha256=source['profile_sha256'],
                map_name='utars_nav_map', waypoint='get1', resume_stage='retreat',
                expected_pose=dict(point_x=reference['x'], point_y=reference['y'], point_yaw=reference['yaw']),
                measured_pose_samples=samples, alignment_attempts=attempts,
                total_requested_m=requested, alignment_ready_ns=aligned['time_ns'],
                grasp_goal_id=goal_id, held_checkpoint_ns=held['time_ns'],
                fresh_arrival_tolerance_unchanged=True, box_state_measured=False)


def _cleanup(rows):
    """Only the known idle lease teardown may follow the requested boundary."""
    for row in rows:
        if not isinstance(row, dict) or row.get('event') not in ('action', 'health_worker'):
            _fail('unexpected event after clean source boundary')
        detail = row.get('detail', {})
        if detail.get('event') == 'worker_closed':
            if type(detail.get('returncode')) is not int or detail['returncode'] not in (0, 2, 78):
                _fail('source worker cleanup was not confirmed')
        elif detail.get('event') == 'error':
            allowed = ('Lease missing, invalid or expired' if row['event'] == 'action' else
                       'RuntimeError: Health worker lease expired or stop requested')
            if detail.get('reason') != allowed or detail.get('goal_id') is not None or detail.get('request_id') is not None:
                _fail('late source fault is not idle lease cleanup')
        else:
            _fail('new action or contradictory terminal after source boundary')


def derive_reference(rows, checkpoint, context, profile):
    """Return None for legacy input without alignment, otherwise fail closed.

    Call with the original source events; retain all navigation actions in the
    compact proof. Shutdown lease errors after the requested clean boundary do
    not retroactively turn a completed grasp into an unknown result.
    """
    if not isinstance(rows, list):
        _fail('source events must be a list')
    if not any(isinstance(row, dict) and row.get('event') == 'box_alignment' for row in rows):
        return None
    # Worker-closed summaries historically lack time_ns; relevant cleanup after
    # session_finishing is excluded, not assigned an invented source timestamp.
    finish = [i for i, r in enumerate(rows) if isinstance(r, dict) and r.get('event') == 'session_finishing']
    if len(finish) != 1:
        _fail('exactly one source session finish required')
    original, cleanup = rows[:finish[0]+1], rows[finish[0]+1:]
    _cleanup(cleanup)
    result = _derive(original, checkpoint, context, profile)
    proof = _proof(original)
    if _derive(proof, checkpoint, context, profile) != result:
        _fail('compact proof changes the derived reference')
    result.update(proof_rows=proof, proof_sha256=_digest(proof), cleanup_rows=copy.deepcopy(cleanup),
                  events_source_sha256=_digest(rows))
    return copy.deepcopy(result)


def validate_reference(reference, checkpoint, context, profile):
    """Recompute the target from the bounded proof and exact source identities."""
    if not isinstance(reference, dict) or reference.get('schema') != SCHEMA:
        _fail('unknown reference schema')
    proof = reference.get('proof_rows')
    if not isinstance(proof, list) or _digest(proof) != reference.get('proof_sha256'):
        _fail('proof hash differs')
    expected = _derive(proof, checkpoint, context, profile)
    _cleanup(reference.get('cleanup_rows', []))
    extra = {'proof_rows', 'proof_sha256', 'cleanup_rows', 'events_source_sha256'}
    if set(reference) != set(expected)|extra or any(reference[k] != v for k, v in expected.items()):
        _fail('reference differs from its source proof')
    digest = reference.get('events_source_sha256')
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        _fail('source events hash missing')
    return copy.deepcopy(reference)
