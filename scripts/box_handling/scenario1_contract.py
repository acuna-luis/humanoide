"""Pure scenario-1 contracts. No ROS, filesystem writes or physical actions.

The caller must durably persist begin_stage's returned checkpoint BEFORE sending
an action, and persist completion only AFTER validating its result/postcondition.
The legacy resume API accepts only clean box-verification boundaries. Explicit
recovery plans use v3 segments and retain their source provenance separately.
Operator-assumed compatibility is never evidence of physical validation.
"""
import ast
import copy
import hashlib
import json
import math
import re


STAGES = (
    'navigate_get1', 'enable_vision', 'grasp', 'verify_held', 'retreat',
    'navigate_put1', 'deposit', 'verify_released', 'home', 'verify_home',
)
STOP_AFTER = ('navigate_get1', 'verify_held', 'verify_home')
BOX_STATES = ('empty', 'held', 'released', 'unknown')
CONFIRMATION_POLICIES = ('ask', 'assume', 'sensors')
_VERIFICATION_SOURCES = {'ask': 'operator', 'assume': 'assumed', 'sensors': 'sensors'}
_BOX_VERIFICATIONS = {'verify_held': 'held', 'verify_released': 'released'}
COMPATIBILITY = ('verified', 'operator_assumed_existing', 'pending', 'incompatible')
_ACCEPTED_COMPATIBILITY = ('verified', 'operator_assumed_existing')
_TASKS = {
    'grasp': 'local_front_box/separate_right_cruzr',
    'deposit': 'wrc_cruzr/put_cruzr_wrc_low',
}
_BOX_AFTER = (
    'empty', 'empty', 'unknown', 'held', 'held', 'held', 'unknown',
    'released', 'released', 'released',
)
_CHECKPOINT_KEYS = {
    'version', 'profile_id', 'profile_sha256', 'stop_after', 'completed',
    'in_flight', 'box_state', 'failure',
}
_CHECKPOINT_V2_KEYS = _CHECKPOINT_KEYS | {'policy', 'confirmations'}
_CHECKPOINT_V3_KEYS = _CHECKPOINT_V2_KEYS | {'entry_stage', 'entry_box_state', 'origin'}
ENTRY_BOX_STATES = dict(zip(STAGES, ('empty', 'empty', 'empty', 'held', 'held',
                                    'held', 'held', 'released', 'released', 'released')))
_ORIGIN_KEYS = {'source_sha256', 'source_next_stage', 'source_failure', 'source_in_flight',
                'requested_stage', 'explicit_state', 'recovery_confirmed',
                'skipped_stages', 'repeated_stages'}


def _entry_index(cp):
    return STAGES.index(cp['entry_stage']) if cp['version'] == 3 else 0


def _progress_index(cp):
    return _entry_index(cp) + len(cp['completed'])


def _validate_origin(origin, entry_stage):
    """Validate the recorded plan, not the physical truth of an acknowledgement."""
    _keys(origin, _ORIGIN_KEYS, 'Resume origin')
    if (type(origin['source_sha256']) is not str or
            re.fullmatch(r'[0-9a-f]{64}', origin['source_sha256']) is None):
        raise ValueError('Invalid resume source hash')
    following = origin['source_next_stage']
    if following is not None and following not in STAGES:
        raise ValueError('Invalid source next stage')
    requested = origin['requested_stage']
    if requested is not None and requested != entry_stage:
        raise ValueError('Requested resume stage differs from segment entry')
    if requested is None and following != entry_stage:
        raise ValueError('Implicit resume must enter at the source next stage')
    for key in ('explicit_state', 'recovery_confirmed'):
        if type(origin[key]) is not bool:
            raise ValueError('Resume acknowledgement fields must be booleans')
    failed, active = origin['source_failure'], origin['source_in_flight']
    if active is not None and (following is None or active != following):
        raise ValueError('Invalid source in-flight stage')
    if failed is not None:
        _keys(failed, {'stage', 'reason'}, 'Source failure')
        if (following is None or failed['stage'] != following or active is not None or
                type(failed['reason']) is not str or not failed['reason'].strip()):
            raise ValueError('Invalid source failure')
    source_index = STAGES.index(following) if following is not None else len(STAGES)
    entry_index = STAGES.index(entry_stage)
    skipped = list(STAGES[source_index:entry_index]) if entry_index > source_index else []
    repeated = list(STAGES[entry_index:source_index]) if entry_index < source_index else []
    if origin['skipped_stages'] != skipped or origin['repeated_stages'] != repeated:
        raise ValueError('Resume skipped/repeated stages contradict the requested segment')
    if ((failed is not None or active is not None or entry_stage != following) and
            not (origin['explicit_state'] and origin['recovery_confirmed'])):
        raise ValueError('Recovery requires explicit box state and confirmation')


def _keys(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError(label + ': missing or unknown fields')


def _finite_json(value):
    """Reject NaN/Infinity and non-JSON objects, including nested result data."""
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if isinstance(value, list):
        for child in value:
            _finite_json(child)
        return
    if isinstance(value, dict) and all(type(key) is str for key in value):
        for child in value.values():
            _finite_json(child)
        return
    raise ValueError('Nonfinite or non-JSON value')


def _stop_after(value):
    if value not in STOP_AFTER:
        raise ValueError('Unknown stop_after')


def _policy(value):
    if type(value) is not str or value not in CONFIRMATION_POLICIES:
        raise ValueError('Unknown confirmation policy')


def _box_evidence(policy, box, source, sensor_evidence):
    """Record provenance; the runtime must validate actual fresh sensor reports.

    An assumption remains an assumption even if the state machine permits the
    next stage. This contract cannot establish freshness or sensor validity.
    """
    _policy(policy)
    if source != _VERIFICATION_SOURCES[policy]:
        raise ValueError('Box evidence source does not match confirmation policy')
    if policy == 'sensors':
        if not isinstance(sensor_evidence, dict) or not sensor_evidence:
            raise ValueError('Sensor policy requires a nonempty validated sensor report')
        _finite_json(sensor_evidence)
    elif sensor_evidence is not None:
        raise ValueError('Operator/assumed evidence cannot be labeled as sensor measurements')
    return dict(box_state=box, source=source, sensor_evidence=copy.deepcopy(sensor_evidence))


def validate_profile(profile, *, stop_after='verify_home'):
    """Return an independent profile copy, or block incompatible execution.

    A get1-only or grasp-only run may retain a pending/incompatible deposit
    profile because no deposit is authorized. Completing the cycle requires both
    compatibilities. The existing grasp/profile restrictions remain unchanged.
    """
    _stop_after(stop_after)
    _keys(profile, {'id', 'box_size_m', 'intended_use', 'grasp', 'deposit'}, 'Profile')
    _finite_json(profile)
    if (type(profile['id']) is not str or
            re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', profile['id']) is None):
        raise ValueError('Invalid profile id')
    if profile['intended_use'] != 'separate_nested_box':
        raise ValueError('Unsupported intended use')
    size = profile['box_size_m']
    if (not isinstance(size, list) or len(size) != 3 or
            any(type(v) not in (int, float) for v in size) or
            size != [0.603, 0.397, 0.220]):
        raise ValueError('Profile requires exact box_size_m [0.603, 0.397, 0.220]')
    for phase, task in _TASKS.items():
        item = profile[phase]
        _keys(item, {'task', 'compatibility'}, phase)
        if item['task'] != task:
            raise ValueError('Unsupported ' + phase + ' task')
        if item['compatibility'] not in COMPATIBILITY:
            raise ValueError('Unknown ' + phase + ' compatibility')
        if (phase == 'grasp' or stop_after == 'verify_home') and (
                item['compatibility'] not in _ACCEPTED_COMPATIBILITY):
            raise ValueError(phase + ' compatibility does not permit this run')
    return copy.deepcopy(profile)


def _profile_hash(profile):
    return hashlib.sha256(json.dumps(profile, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def new_checkpoint(profile, *, stop_after='verify_home', policy='ask'):
    profile = validate_profile(profile, stop_after=stop_after)
    _policy(policy)
    return dict(version=2, profile_id=profile['id'], profile_sha256=_profile_hash(profile),
                stop_after=stop_after, completed=[], in_flight=None,
                box_state='empty', failure=None, policy=policy, confirmations={})


def new_resume_checkpoint(profile, *, entry_stage, entry_box_state, origin,
                          stop_after='verify_home', policy='assume'):
    """Create an empty execution segment without inventing completed stages."""
    cp = new_checkpoint(profile, stop_after=stop_after, policy=policy)
    cp.update(version=3, entry_stage=entry_stage, entry_box_state=entry_box_state,
              origin=copy.deepcopy(origin), box_state=entry_box_state)
    return validate_checkpoint(cp, profile)


def validate_checkpoint(checkpoint, profile=None):
    """Validate an exact prefix (v1/v2) or real contiguous segment (v3)."""
    if (not isinstance(checkpoint, dict) or type(checkpoint.get('version')) is not int
            or checkpoint['version'] not in (1, 2, 3)):
        raise ValueError('Unsupported checkpoint version')
    _keys(checkpoint, {1: _CHECKPOINT_KEYS, 2: _CHECKPOINT_V2_KEYS,
                      3: _CHECKPOINT_V3_KEYS}[checkpoint['version']],
          'Checkpoint')
    _finite_json(checkpoint)
    cp = checkpoint
    _stop_after(cp['stop_after'])
    if (type(cp['profile_id']) is not str or
            re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', cp['profile_id']) is None or
            type(cp['profile_sha256']) is not str or
            re.fullmatch(r'[0-9a-f]{64}', cp['profile_sha256']) is None):
        raise ValueError('Invalid checkpoint profile identity')
    completed = cp['completed']
    limit = STAGES.index(cp['stop_after']) + 1
    if cp['version'] == 3:
        if cp['entry_stage'] not in STAGES:
            raise ValueError('Invalid resume segment entry stage')
        if cp['entry_box_state'] != ENTRY_BOX_STATES[cp['entry_stage']]:
            raise ValueError('Resume entry box state contradicts its stage')
        _validate_origin(cp['origin'], cp['entry_stage'])
    start = _entry_index(cp)
    if (not isinstance(completed, list) or start >= limit or start + len(completed) > limit or
            completed != list(STAGES[start:start+len(completed)])):
        raise ValueError('Checkpoint is not a completed ordered prefix')
    if cp['version'] >= 2:
        _policy(cp['policy'])
        required = set(completed) & set(_BOX_VERIFICATIONS)
        _keys(cp['confirmations'], required, 'Box evidence records')
        for stage, record in cp['confirmations'].items():
            _keys(record, {'box_state', 'source', 'sensor_evidence'}, 'Box evidence record')
            if record['box_state'] != _BOX_VERIFICATIONS[stage]:
                raise ValueError('Box evidence contradicts its verification stage')
            _box_evidence(cp['policy'], record['box_state'], record['source'], record['sensor_evidence'])
    index = start + len(completed)
    expected = STAGES[index] if index < limit else None
    if cp['in_flight'] is not None and cp['in_flight'] != expected:
        raise ValueError('Invalid in-flight stage')
    if cp['box_state'] not in BOX_STATES:
        raise ValueError('Unknown box state')
    if cp['failure'] is not None:
        _keys(cp['failure'], {'stage', 'reason'}, 'Failure')
        if (expected is None or cp['failure']['stage'] != expected or
                type(cp['failure']['reason']) is not str or not cp['failure']['reason'].strip() or
                cp['in_flight'] is not None or cp['box_state'] != 'unknown'):
            raise ValueError('Invalid failed checkpoint')
    else:
        expected_box = _BOX_AFTER[index - 1] if completed else cp.get('entry_box_state', 'empty')
        if cp['in_flight'] in ('grasp', 'deposit'):
            expected_box = 'unknown'
        if cp['box_state'] != expected_box:
            raise ValueError('Box state contradicts the completed stages')
    if profile is not None:
        profile = validate_profile(profile, stop_after=cp['stop_after'])
        if cp['profile_id'] != profile['id'] or cp['profile_sha256'] != _profile_hash(profile):
            raise ValueError('Checkpoint/profile mismatch')
    return copy.deepcopy(cp)


def progress_index(checkpoint):
    """Absolute next-stage index; v3 completed contains only its real segment."""
    return _progress_index(validate_checkpoint(checkpoint))


def next_stage(checkpoint):
    cp = validate_checkpoint(checkpoint)
    if cp['failure'] is not None or cp['in_flight'] is not None:
        raise ValueError('Incomplete/failed stage requires recovery, not continuation')
    index = _progress_index(cp)
    return None if index > STAGES.index(cp['stop_after']) else STAGES[index]


def begin_stage(checkpoint, stage):
    """Return the checkpoint that MUST be persisted before executing this stage."""
    cp = validate_checkpoint(checkpoint)
    if stage not in STAGES or next_stage(cp) != stage:
        raise ValueError('Stage is not the next permitted stage')
    cp['in_flight'] = stage
    if stage in ('grasp', 'deposit'):
        cp['box_state'] = 'unknown'
    return cp


def complete_stage(checkpoint, stage, *, confirmed_box=None, home_verified=False,
                   verification_source='operator', sensor_evidence=None):
    """Record completed action/postcondition without upgrading its evidence.

    Existing callers retain interactive ``ask`` behavior. Sensor callers must
    supply their freshly validated report; setting a boolean cannot create a
    sensor record. Non-box stages have no box-verification source to override.
    """
    cp = validate_checkpoint(checkpoint)
    if cp['failure'] is not None or stage not in STAGES or cp['in_flight'] != stage:
        raise ValueError('Cannot complete a stage that is not in flight')
    required_box = _BOX_VERIFICATIONS.get(stage)
    if confirmed_box != required_box:
        raise ValueError('Box postcondition missing or inappropriate for this stage')
    if type(home_verified) is not bool or home_verified != (stage == 'verify_home'):
        raise ValueError('Fresh HOME verification required only at verify_home')
    if required_box is not None:
        record = _box_evidence(cp.get('policy', 'ask'), required_box,
                               verification_source, sensor_evidence)
        if cp['version'] >= 2:
            cp['confirmations'][stage] = record
    elif verification_source != 'operator' or sensor_evidence is not None:
        raise ValueError('Box evidence is only appropriate at box verification stages')
    cp['completed'].append(stage)
    cp['in_flight'] = None
    cp['box_state'] = _BOX_AFTER[STAGES.index(stage)]
    return validate_checkpoint(cp)


def fail_stage(checkpoint, stage, reason):
    """Latch failure and unknown box state; never translate failure into success."""
    cp = validate_checkpoint(checkpoint)
    index = _progress_index(cp)
    if (cp['failure'] is not None or index > STAGES.index(cp['stop_after']) or
            stage != STAGES[index] or type(reason) is not str or not reason.strip()):
        raise ValueError('Invalid failed stage or reason')
    cp.update(in_flight=None, box_state='unknown', failure={'stage': stage, 'reason': reason})
    return validate_checkpoint(cp)


def resume_checkpoint(checkpoint, profile, *, confirmed_box, state_reconfirmed,
                      stop_after='verify_home', policy='ask',
                      verification_source='operator', sensor_evidence=None):
    """Resume a clean held/released checkpoint under its unchanged policy.

    state_reconfirmed is the caller's explicit attestation of fresh runtime and
    physical checks, not a timestamp or a persisted authorization to reuse later.
    Legacy v1 checkpoints belong to ``ask``. A v2 sensor checkpoint needs a fresh
    validated sensor report on resume. Assumed evidence is never automatically
    promoted to operator or sensor evidence. The last box record is refreshed
    with the new reconfirmation; callers retain prior journal/checkpoint evidence.
    """
    cp = validate_checkpoint(checkpoint, profile)
    profile = validate_profile(profile, stop_after=stop_after)
    _policy(policy)
    if cp.get('policy', 'ask') != policy:
        raise ValueError('Resume cannot change the checkpoint confirmation policy')
    if state_reconfirmed is not True:
        raise ValueError('Fresh state reconfirmation required')
    if (cp['in_flight'] is not None or cp['failure'] is not None or
            not cp['completed'] or cp['completed'][-1] not in ('verify_held', 'verify_released')):
        raise ValueError('Resume requires a clean verified-held/released checkpoint')
    if cp['box_state'] not in ('held', 'released') or confirmed_box != cp['box_state']:
        raise ValueError('Current box state was not reconfirmed')
    record = _box_evidence(policy, confirmed_box, verification_source, sensor_evidence)
    if STAGES.index(stop_after) < _progress_index(cp) - 1:
        raise ValueError('Cannot resume before the completed checkpoint')
    cp['stop_after'] = stop_after
    if cp['version'] >= 2:
        cp['confirmations'][cp['completed'][-1]] = record
    return validate_checkpoint(cp, profile)


def _result(payload):
    """Accept structured client output; support legacy one-result text for tests/tools."""
    if isinstance(payload, str):
        matches = re.findall(r'^Result: result=(.*), status=(\d+)\s*$', payload, re.M)
        if len(matches) != 1:
            raise ValueError('Expected exactly one terminal result')
        try:
            payload = dict(event='result', status=int(matches[0][1]),
                           result=ast.literal_eval(matches[0][0]))
        except (SyntaxError, ValueError) as exc:
            raise ValueError('Malformed terminal result') from exc
    _finite_json(payload)
    if (not isinstance(payload, dict) or payload.get('event') != 'result' or
            type(payload.get('status')) is not int or payload['status'] != 4):
        raise ValueError('A successful terminal result status=4 is required')
    result = payload.get('result')
    if (not isinstance(result, dict) or not isinstance(result.get('state'), dict) or
            type(result['state'].get('desc')) is not str):
        raise ValueError('Malformed result state')
    return copy.deepcopy(result)


def validate_motion_result(payload):
    result = _result(payload)
    state = result['state']
    if (state['desc'] != 'SUCCEED' or type(state.get('state')) is not int or
            state['state'] != 1101001):
        raise ValueError('Motion did not confirm SUCCEED/1101001')
    return result


def validate_navigation_result(payload):
    result = _result(payload)
    desc = result['state']['desc']
    dmsg = result.get('dmsg', '')
    if type(dmsg) is not str:
        raise ValueError('Invalid navigation message')
    arrival = dmsg.startswith('navigation_start SUCCEEDED')
    auxiliary_lost = desc == 'VSLAM_LOCATION_LOST' and arrival
    if ((re.search(r'ERROR|FAIL|ABORT|CANCEL|LOST|OBSTACLE', desc, re.I) and
         not auxiliary_lost) or not (desc in ('SUCCESS', 'SUCCEED') or arrival)):
        raise ValueError('Navigation arrival was not confirmed')
    return result
