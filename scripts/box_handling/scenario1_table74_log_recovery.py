"""Pure admission of one completed approach whose later log audit failed.

The original failed journal remains failed. This proof authorizes only the
next precontact phase, subject to its new live context and safety checks. The
receipt records an operator assumption, never a current physical measurement.
Raw-file hashes are supplied by the bounded PC reader; this pure validator
also binds their parsed contents with a canonical proof digest.
"""
import copy
import hashlib
import json
from pathlib import PurePosixPath
import re
import uuid


AUTHORIZATION_FILE = 'recovery-authorization.json'
ALLOWED_ERROR = 'TABLE74_NATIVE_IDENTITY: expected one ordered start/end of the exact task'
_SHA256 = re.compile(r'[0-9a-f]{64}\Z')
_FAULT = re.compile(
    r'De(?:ct|tect)ionForceCollision|Collision force.*exceeded|'
    r'(?:force|wrench|collision|servo|watchdog|IK|HQP).*\b(?:failed|failure|fault|exceeded)\b|'
    r'MoveToGoalFailed|terminal_unknown|worker_exit_unconfirmed', re.I)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _modules():
    # Deferred imports allow this module to precede the remote runner modules.
    if __package__:
        from . import scenario1_contract as contract
        from . import scenario1_table74_current_trial_run as current
        from . import scenario1_table74_support_run as proof_tools
        from . import scenario1_table74_trial_run as approach
    else:
        import scenario1_contract as contract
        import scenario1_table74_current_trial_run as current
        import scenario1_table74_support_run as proof_tools
        import scenario1_table74_trial_run as approach
    return contract, current, proof_tools, approach


def _receipt(receipt, originals, files):
    fields = {'version', 'kind', 'next_stage', 'source_directory', 'source_sha256',
              'proof_sha256', 'operator_state_assumed_unchanged', 'current_physical_measurement'}
    if (not isinstance(receipt, dict) or set(receipt) != fields or
            type(receipt['version']) is not int or receipt['version'] != 1 or
            receipt['kind'] != 'table74_log_only_recovery' or receipt['next_stage'] != 'precontact' or
            receipt['operator_state_assumed_unchanged'] is not True or
            receipt['current_physical_measurement'] is not False):
        raise ValueError('TABLE74_LOG_RECOVERY_AUTHORIZATION: malformed explicit recovery receipt')
    directory = receipt['source_directory']
    if (type(directory) is not str or '\x00' in directory or
            not PurePosixPath(directory).is_absolute() or directory == '/' or
            '..' in PurePosixPath(directory).parts):
        raise ValueError('TABLE74_LOG_RECOVERY_AUTHORIZATION: source directory must be an absolute PC path')
    hashes = receipt['source_sha256']
    if (not isinstance(hashes, dict) or set(hashes) != set(files) or
            any(type(h) is not str or _SHA256.fullmatch(h) is None for h in hashes.values()) or
            type(receipt['proof_sha256']) is not str or _SHA256.fullmatch(receipt['proof_sha256']) is None or
            receipt['proof_sha256'] != digest(originals)):
        raise ValueError('TABLE74_LOG_RECOVERY_AUTHORIZATION: original proof identity differs')


def _one(rows, predicate, reason):
    matches = [(i, row) for i, row in enumerate(rows) if predicate(row)]
    if len(matches) != 1:
        raise ValueError('TABLE74_LOG_RECOVERY_PROOF: '+reason)
    return matches[0]


def _no_observed_fault(event):
    detail = event.get('detail', {})
    if not isinstance(detail, dict):
        raise ValueError('TABLE74_LOG_RECOVERY_PROOF: malformed worker detail')
    forbidden = {'error', 'terminal_unknown', 'worker_exit_unconfirmed', 'cancel_requested',
                 'cancel_response', 'interrupted_terminal', 'worker_closed'}
    if event.get('event') in forbidden or detail.get('event') in forbidden:
        raise ValueError('TABLE74_LOG_RECOVERY_PROOF: interruption or physical failure before diagnostic error')
    for row in (event, detail):
        for key in ('reason', 'text', 'error'):
            value = row.get(key)
            if isinstance(value, str) and _FAULT.search(value):
                raise ValueError('TABLE74_LOG_RECOVERY_PROOF: observed native or physical fault')
    if detail.get('event') == 'feedback':
        feedback = detail.get('feedback')
        state = feedback.get('state') if isinstance(feedback, dict) else None
        desc = state.get('desc') if isinstance(state, dict) else None
        if isinstance(desc, str) and re.search(r'ABORT|FAIL|ERROR|COLLISION|FAULT', desc, re.I):
            raise ValueError('TABLE74_LOG_RECOVERY_PROOF: observed native feedback fault')
    if event.get('event') in ('health', 'live_health_transition'):
        report = event.get('report', event)
        if not isinstance(report, dict):
            raise ValueError('TABLE74_LOG_RECOVERY_PROOF: malformed health report')
        safety = report.get('safety', {})
        if not isinstance(safety, dict) or any(type(safety.get(k)) is not int or safety[k] != 0
                for k in ('estop', 'servo_estop', 'charger') if k in safety):
            raise ValueError('TABLE74_LOG_RECOVERY_PROOF: observed stop or charger state')


def validate_proof(proof, profile):
    """Return a typed next-phase context without altering any source evidence."""
    contract, current, proof_tools, approach = _modules()
    files = proof_tools.FILES
    if not isinstance(proof, dict) or set(proof) != set(files) | {AUTHORIZATION_FILE}:
        raise ValueError('TABLE74_LOG_RECOVERY_PROOF: exactly six original files and authorization are required')
    try:
        size = len(json.dumps(proof, allow_nan=False).encode())
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError('TABLE74_LOG_RECOVERY_PROOF: non-finite or malformed proof') from exc
    if size > 32*1024*1024:
        raise ValueError('TABLE74_LOG_RECOVERY_PROOF: proof exceeds bounded size')
    originals = {name: proof[name] for name in files}
    receipt = proof[AUTHORIZATION_FILE]
    _receipt(receipt, originals, files)
    bundle = current.validate_bundle(proof['bundle.json'])
    source_record = proof['source-context.json']
    if not isinstance(source_record, dict):
        raise ValueError('TABLE74_LOG_RECOVERY_PROOF: source context is missing')
    source, original_plan = current.prepare_entry(source_record.get('checkpoint'), profile, bundle)
    if (source_record != approach.context_record(source) or
            proof['context-checkpoint.json'] != approach.context_record(source)):
        raise ValueError('TABLE74_LOG_RECOVERY_PROOF: original technical checkpoint differs')
    journal = approach.validate_journal(proof['trial.json'], bundle['manifest']['id'], original_plan['source_sha256'])
    if journal['phase'] != 'failed' or journal['error'] != ALLOWED_ERROR:
        raise ValueError('TABLE74_LOG_RECOVERY_PROOF: only the exact post-result log identity failure is eligible')
    contract.validate_motion_result(journal['result'])
    uid, rid = journal['result'].get('goal_id'), journal['result'].get('request_id')
    try:
        canonical_uid = str(uuid.UUID(uid)) == uid and uuid.UUID(uid).int != 0
    except (ValueError, TypeError, AttributeError):
        canonical_uid = False
    if not canonical_uid or type(rid) is not str or not rid:
        raise ValueError('TABLE74_LOG_RECOVERY_PROOF: native UUID or request identity is invalid')
    context = proof['context.json']
    if (not isinstance(context, dict) or set(context) !=
            {'boot_id', 'containers', 'dependencies', 'points', 'execution_profile'} or
            context['execution_profile'] != 'optimistic_v1' or
            type(context['boot_id']) is not str or not context['boot_id'] or
            any(not isinstance(context[k], dict) or not context[k] for k in ('containers', 'dependencies', 'points'))):
        raise ValueError('TABLE74_LOG_RECOVERY_PROOF: runtime identity context is missing')
    events = proof['events.jsonl']
    if not isinstance(events, list) or not 1 <= len(events) <= 20000 or any(not isinstance(e, dict) for e in events):
        raise ValueError('TABLE74_LOG_RECOVERY_PROOF: bounded original events are required')
    stamps = [e.get('time_ns') for e in events]
    if any(type(t) is not int or t <= 0 for t in stamps) or stamps != sorted(stamps):
        raise ValueError('TABLE74_LOG_RECOVERY_PROOF: source timestamps are invalid or regressed')
    error_index, error = _one(events, lambda e: e.get('event') == 'error', 'one diagnostic supervisor error is required')
    if error.get('reason') != ALLOWED_ERROR or error.get('physical_state') != 'unconfirmed':
        raise ValueError('TABLE74_LOG_RECOVERY_PROOF: supervisor error differs from the eligible diagnostic')
    active, tail = events[:error_index], events[error_index+1:]
    proof_tools.validate_shutdown_tail(tail)
    closed = [e.get('kind') if e.get('event') == 'action' else 'health_worker'
              for e in tail if e.get('detail', {}).get('event') == 'worker_closed']
    if sorted(closed) != ['health_worker', 'motion', 'navigation']:
        raise ValueError('TABLE74_LOG_RECOVERY_PROOF: all three idle workers must close once')
    allowed_events = {'containers', 'timing', 'dependencies', 'trial_dependencies', 'health_worker', 'health',
        'live_health_ready', 'action', 'pose_check', 'resume_base_check', 'resume_arrival', 'resume_checked',
        'ready', 'resume_ready', 'scenario_context', 'armed', 'trial', 'live_health_transition'}
    for event in active:
        if event.get('event') not in allowed_events:
            raise ValueError('TABLE74_LOG_RECOVERY_PROOF: unexpected activity before diagnostic error')
        _no_observed_fault(event)
    _, ready = _one(active, lambda e: e.get('event') == 'ready', 'one ready context is required')
    if ready.get('context') != context:
        raise ValueError('TABLE74_LOG_RECOVERY_PROOF: ready context differs')
    journals = [(i, e) for i, e in enumerate(active) if e.get('event') == 'trial']
    if len(journals) != 2 or journals[-1][1].get('trial') != journal:
        raise ValueError('TABLE74_LOG_RECOVERY_PROOF: original pending and failed journals are required')
    pending = journals[0][1].get('trial')
    approach.validate_journal(pending, bundle['manifest']['id'], original_plan['source_sha256'])
    if pending['phase'] != 'pending' or pending['intent_ns'] != journal['intent_ns']:
        raise ValueError('TABLE74_LOG_RECOVERY_PROOF: journal intent differs')
    motion = [(i, e['detail']) for i, e in enumerate(active)
              if e.get('event') == 'action' and e.get('kind') == 'motion']
    startup = {'session_ready', 'native_api', 'worker_log'}
    allowed = startup | {'dispatched', 'accepted', 'status', 'feedback', 'result_pending', 'result', 'request_complete'}
    if any(row.get('event') not in allowed for _, row in motion):
        raise ValueError('TABLE74_LOG_RECOVERY_PROOF: unknown native action event')
    dispatch_index, dispatch = _one(motion, lambda pair: pair[1].get('event') == 'dispatched', 'one dispatch is required')
    if any(row['event'] in startup for _, row in motion[dispatch_index:]):
        raise ValueError('TABLE74_LOG_RECOVERY_PROOF: native startup after dispatch')
    transaction = [(i, row) for i, row in motion if row['event'] not in startup]
    if any(row.get('request_id') != rid or
           (row['event'] != 'request_complete' and row.get('goal_id') != uid) for _, row in transaction):
        raise ValueError('TABLE74_LOG_RECOVERY_PROOF: native action identity is not unique')
    indexes, rows = [], {}
    for name in ('dispatched', 'accepted', 'result', 'request_complete'):
        _, (index, row) = _one(transaction, lambda pair: pair[1].get('event') == name, 'one '+name+' is required')
        indexes.append(index); rows[name] = row
    if (indexes != sorted(indexes) or rows['dispatched'].get('endpoint') != '/mc/manipulation/action' or
            rows['accepted'].get('accepted') is not True or rows['result'] != journal['result'] or
            type(rows['request_complete'].get('returncode')) is not int or rows['request_complete']['returncode'] != 0):
        raise ValueError('TABLE74_LOG_RECOVERY_PROOF: accepted successful transaction is incomplete')
    if any(type(row.get('status')) is not int or row['status'] not in (1, 2, 4)
           for _, row in transaction if row['event'] == 'status') or any(
            type(row.get('status')) is not int or row['status'] not in (0, 1, 2)
            for _, row in transaction if row['event'] == 'result_pending'):
        raise ValueError('TABLE74_LOG_RECOVERY_PROOF: cancelled, failed or malformed native status')
    for index, event in enumerate(active):
        if event.get('event') == 'action':
            if event.get('kind') not in ('motion', 'navigation') or (
                    event['kind'] == 'navigation' and index >= indexes[0]):
                raise ValueError('TABLE74_LOG_RECOVERY_PROOF: other control after approach dispatch')
            row = event['detail']
            if row.get('event') not in allowed:
                raise ValueError('TABLE74_LOG_RECOVERY_PROOF: unknown action event')
            if row.get('event') == 'accepted' and row.get('accepted') is not True:
                raise ValueError('TABLE74_LOG_RECOVERY_PROOF: rejected native action')
            if row.get('event') == 'result' and (type(row.get('status')) is not int or row['status'] != 4):
                raise ValueError('TABLE74_LOG_RECOVERY_PROOF: failed native action result')
            if row.get('event') == 'status' and (type(row.get('status')) is not int or row['status'] not in (1, 2, 4)):
                raise ValueError('TABLE74_LOG_RECOVERY_PROOF: cancelled or failed action status')
            if row.get('event') == 'result_pending' and (
                    type(row.get('status')) is not int or row['status'] not in (0, 1, 2)):
                raise ValueError('TABLE74_LOG_RECOVERY_PROOF: malformed pending action result')
        if event.get('event') == 'health_worker' and event['detail'].get('event') not in (
                'worker_log', 'session_ready', 'health_result', 'pose_result', 'request_complete'):
            raise ValueError('TABLE74_LOG_RECOVERY_PROOF: unknown health worker event')
        row = event.get('detail', {})
        if row.get('event') == 'request_complete' and (
                type(row.get('returncode')) is not int or row['returncode'] != 0):
            raise ValueError('TABLE74_LOG_RECOVERY_PROOF: worker request did not complete normally')
    times = [journal['intent_ns'], journals[0][1]['time_ns']] + [active[i]['time_ns'] for i in indexes]
    times += [journal['finished_ns'], journals[-1][1]['time_ns'], error['time_ns']]
    if any(a >= b for a, b in zip(times, times[1:])):
        raise ValueError('TABLE74_LOG_RECOVERY_PROOF: terminal does not precede failed diagnostic journal')
    if not (journals[0][0] < indexes[0] < indexes[1] < indexes[2] < indexes[3] < journals[-1][0]):
        raise ValueError('TABLE74_LOG_RECOVERY_PROOF: original event ordering differs')
    hashes = [e.get('hashes') for e in active if e.get('event') == 'trial_dependencies']
    if not hashes or any(h != bundle['manifest']['robot_files'] for h in hashes):
        raise ValueError('TABLE74_LOG_RECOVERY_PROOF: installed dependency evidence differs')
    whole_digest = digest(proof)
    planned = dict(artifact='table74_current_trial_context', executable=False,
        checkpoint=copy.deepcopy(source), stage=approach.STAGE, source_sha256=whole_digest,
        requirements=dict(box_state='held', home=False, waypoint='put1', vision_prep=False))
    return dict(source=copy.deepcopy(source), context=copy.deepcopy(context), options={}, planned=planned,
        predecessor_sha256=whole_digest, bundle_id=bundle['manifest']['id'], goal_id=uid,
        phase='approach_vendor_reference', completed_stage='approach', chain_bundles=[copy.deepcopy(bundle)],
        recovery_authorization=copy.deepcopy(receipt), diagnostic_debt=dict(original_phase='failed',
            original_error=ALLOWED_ERROR, native_log_verified=False, current_physical_measurement=False))
