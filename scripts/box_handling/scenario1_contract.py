"""Pure scenario-1 contracts. No ROS, filesystem writes or physical actions.

The caller must durably persist begin_stage's returned checkpoint BEFORE sending
an action, and persist completion only AFTER validating its result/postcondition.
An interrupted or failed stage cannot be resumed by this module. Operator-assumed
compatibility is an explicit assumption, never evidence of physical validation.
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
STOP_AFTER = ('verify_held', 'verify_home')
BOX_STATES = ('empty', 'held', 'released', 'unknown')
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


def validate_profile(profile, *, stop_after='verify_home'):
    """Return an independent profile copy, or block incompatible execution.

    A grasp-only run may retain a pending/incompatible deposit profile because
    no deposit is authorized. Completing the cycle requires both compatibilities.
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


def new_checkpoint(profile, *, stop_after='verify_home'):
    profile = validate_profile(profile, stop_after=stop_after)
    return dict(version=1, profile_id=profile['id'], profile_sha256=_profile_hash(profile),
                stop_after=stop_after, completed=[], in_flight=None,
                box_state='empty', failure=None)


def validate_checkpoint(checkpoint, profile=None):
    """Validate the exact ordered prefix and box-state consistency; copy on return."""
    _keys(checkpoint, _CHECKPOINT_KEYS, 'Checkpoint')
    _finite_json(checkpoint)
    cp = checkpoint
    if type(cp['version']) is not int or cp['version'] != 1:
        raise ValueError('Unsupported checkpoint version')
    _stop_after(cp['stop_after'])
    if (type(cp['profile_id']) is not str or
            re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', cp['profile_id']) is None or
            type(cp['profile_sha256']) is not str or
            re.fullmatch(r'[0-9a-f]{64}', cp['profile_sha256']) is None):
        raise ValueError('Invalid checkpoint profile identity')
    completed = cp['completed']
    limit = STAGES.index(cp['stop_after']) + 1
    if (not isinstance(completed, list) or len(completed) > limit or
            completed != list(STAGES[:len(completed)])):
        raise ValueError('Checkpoint is not a completed ordered prefix')
    expected = STAGES[len(completed)] if len(completed) < limit else None
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
        expected_box = _BOX_AFTER[len(completed) - 1] if completed else 'empty'
        if cp['in_flight'] in ('grasp', 'deposit'):
            expected_box = 'unknown'
        if cp['box_state'] != expected_box:
            raise ValueError('Box state contradicts the completed stages')
    if profile is not None:
        profile = validate_profile(profile, stop_after=cp['stop_after'])
        if cp['profile_id'] != profile['id'] or cp['profile_sha256'] != _profile_hash(profile):
            raise ValueError('Checkpoint/profile mismatch')
    return copy.deepcopy(cp)


def next_stage(checkpoint):
    cp = validate_checkpoint(checkpoint)
    if cp['failure'] is not None or cp['in_flight'] is not None:
        raise ValueError('Incomplete/failed stage requires recovery, not continuation')
    index = len(cp['completed'])
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


def complete_stage(checkpoint, stage, *, confirmed_box=None, home_verified=False):
    """Caller has validated the action; explicit postconditions gate transitions."""
    cp = validate_checkpoint(checkpoint)
    if cp['failure'] is not None or stage not in STAGES or cp['in_flight'] != stage:
        raise ValueError('Cannot complete a stage that is not in flight')
    required_box = {'verify_held': 'held', 'verify_released': 'released'}.get(stage)
    if confirmed_box != required_box:
        raise ValueError('Box postcondition missing or inappropriate for this stage')
    if type(home_verified) is not bool or home_verified != (stage == 'verify_home'):
        raise ValueError('Fresh HOME verification required only at verify_home')
    cp['completed'].append(stage)
    cp['in_flight'] = None
    cp['box_state'] = _BOX_AFTER[STAGES.index(stage)]
    return validate_checkpoint(cp)


def fail_stage(checkpoint, stage, reason):
    """Latch failure and unknown box state; never translate failure into success."""
    cp = validate_checkpoint(checkpoint)
    index = len(cp['completed'])
    if (cp['failure'] is not None or index > STAGES.index(cp['stop_after']) or
            stage != STAGES[index] or type(reason) is not str or not reason.strip()):
        raise ValueError('Invalid failed stage or reason')
    cp.update(in_flight=None, box_state='unknown', failure={'stage': stage, 'reason': reason})
    return validate_checkpoint(cp)


def resume_checkpoint(checkpoint, profile, *, confirmed_box, state_reconfirmed,
                      stop_after='verify_home'):
    """Resume only a clean verified-held/released checkpoint, after fresh checks.

    state_reconfirmed is the caller's explicit attestation of fresh runtime and
    physical checks, not a timestamp or a persisted authorization to reuse later.
    """
    cp = validate_checkpoint(checkpoint, profile)
    profile = validate_profile(profile, stop_after=stop_after)
    if state_reconfirmed is not True:
        raise ValueError('Fresh state reconfirmation required')
    if (cp['in_flight'] is not None or cp['failure'] is not None or
            not cp['completed'] or cp['completed'][-1] not in ('verify_held', 'verify_released')):
        raise ValueError('Resume requires a clean verified-held/released checkpoint')
    if cp['box_state'] not in ('held', 'released') or confirmed_box != cp['box_state']:
        raise ValueError('Current box state was not reconfirmed')
    if STAGES.index(stop_after) < len(cp['completed']) - 1:
        raise ValueError('Cannot resume before the completed checkpoint')
    cp['stop_after'] = stop_after
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
