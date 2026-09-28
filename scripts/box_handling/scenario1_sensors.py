"""Pure checks of fresh wrist FT/joint samples and qualified empirical envelopes.

No clients, files, calibration acquisition or movement. An accepted envelope is
evidence of the measured wrist loads and joint posture only: it does not directly
measure box identity, separation from another box, or support at the destination.
Calibration must include positive AND negative conditions in evidence_reference.
This module validates the profile schema, not that referenced experiment itself.
"""
import copy
import math
import re


WINDOW_NS = 500_000_000
MIN_WINDOW_NS = 200_000_000
MAX_SAMPLE_GAP_NS = 100_000_000
MAX_WRIST_SKEW_NS = 100_000_000
MIN_SAMPLES = 5
MAX_VELOCITY_RAD_S = 0.02
# These two positions integrate wheel rotation as the robot drives; they are
# not an upper-body posture. Their measured velocities still gate stationarity.
NON_POSTURE_JOINTS = frozenset({'driving_wheel_left_joint', 'driving_wheel_right_joint'})
_PROFILE_KEYS = {'version', 'id', 'geometry_id', 'qualification', 'evidence_reference', 'stages'}
_WRIST_KEYS = {'frame_id', 'force_min', 'force_max', 'torque_min', 'torque_max',
               'max_force_span_n', 'max_torque_span_nm'}


def _keys(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(label + ': missing or unknown fields')


def _number(value, label):
    if type(value) not in (float, int):
        raise ValueError(label + ': expected finite number')
    try:
        value = float(value)
    except OverflowError as exc:
        raise ValueError(label + ': expected finite number') from exc
    if not math.isfinite(value):
        raise ValueError(label + ': expected finite number')
    return value


def _integer(value, label, allow_zero=False):
    if type(value) is not int or value < (0 if allow_zero else 1):
        raise ValueError(label + ': expected positive integer timestamp')
    return value


def _name(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + ': expected nonempty string')
    return value


def _identifier(value, label):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', value):
        raise ValueError(label + ': invalid identifier')
    return value


def _vector(value, label, length=3):
    if not isinstance(value, list) or len(value) != length:
        raise ValueError(label + ': wrong vector length')
    return [_number(item, label) for item in value]


def _names(value):
    if not isinstance(value, list) or not value:
        raise ValueError('Joint names must be a nonempty list')
    if any(not isinstance(item, str) or not item.strip() for item in value) or len(set(value)) != len(value):
        raise ValueError('Joint names missing or duplicated')
    return list(value)


def _stage_profile(stage):
    _keys(stage, {'pose', 'max_pose_error_rad', 'left', 'right'}, 'Calibration stage')
    _keys(stage['pose'], {'joint_names', 'position_rad'}, 'Calibration pose')
    names = _names(stage['pose']['joint_names'])
    if set(names) & NON_POSTURE_JOINTS:
        raise ValueError('Driving wheel positions must not appear in the calibrated body posture')
    _keys(stage['pose']['position_rad'], names, 'Calibration joint positions')
    for name in names:
        _number(stage['pose']['position_rad'][name], 'Calibration joint position')
    error = _number(stage['max_pose_error_rad'], 'Pose tolerance')
    if not 0 < error <= 0.03:
        raise ValueError('Pose tolerance must be explicit and in (0, 0.03] radians')
    for side in ('left', 'right'):
        wrist = stage[side]
        _keys(wrist, _WRIST_KEYS, 'Calibration wrist')
        _name(wrist['frame_id'], 'Calibration frame')
        for kind in ('force', 'torque'):
            low = _vector(wrist[kind + '_min'], kind + ' minimum')
            high = _vector(wrist[kind + '_max'], kind + ' maximum')
            if any(a > b or not math.isfinite(b - a) for a, b in zip(low, high)):
                raise ValueError('Calibration envelope has invalid bounds')
        for name in ('max_force_span_n', 'max_torque_span_nm'):
            if _number(wrist[name], name) <= 0:
                raise ValueError('Calibration span must be explicitly positive')


def _reject_indistinguishable_stages(held, released):
    """Compare envelopes only when their calibrated posture regions overlap."""
    held_pose, released_pose = held['pose']['position_rad'], released['pose']['position_rad']
    if set(held_pose) != set(released_pose):
        raise ValueError('Held/released calibration must cover the same joints')
    tolerance = held['max_pose_error_rad'] + released['max_pose_error_rad']
    if any(abs(held_pose[name] - released_pose[name]) > tolerance for name in held_pose):
        return  # Different poses have different gravity loads; do not compare them.
    if any(held[side]['frame_id'] != released[side]['frame_id'] for side in ('left', 'right')):
        raise ValueError('Cannot distinguish envelopes in inconsistent wrist frames')
    for side in ('left', 'right'):
        for kind in ('force', 'torque'):
            if any(a_max < b_min or b_max < a_min for a_min, a_max, b_min, b_max in zip(
                    held[side][kind + '_min'], held[side][kind + '_max'],
                    released[side][kind + '_min'], released[side][kind + '_max'])):
                return
    raise ValueError('Loaded/unloaded envelopes overlap at the same calibrated posture')


def validate_profile(profile, geometry_id, require_qualified=False):
    """Validate schema and qualification claim; never manufacture calibration.

    A pending profile is suitable for telemetry inspection only. A qualified
    profile must cite reviewed positive/negative calibration evidence; contents
    of that reference and applicability are not inferred by this pure parser.
    """
    if type(require_qualified) is not bool:
        raise ValueError('require_qualified must be boolean')
    _keys(profile, _PROFILE_KEYS, 'Sensor profile')
    if type(profile['version']) is not int or profile['version'] != 1:
        raise ValueError('Unsupported sensor profile version')
    _identifier(profile['id'], 'Sensor profile id')
    _identifier(profile['geometry_id'], 'Geometry id')
    _identifier(geometry_id, 'Expected geometry id')
    if profile['geometry_id'] != geometry_id:
        raise ValueError('Sensor profile geometry mismatch')
    if profile['qualification'] not in ('pending', 'qualified'):
        raise ValueError('Unknown sensor profile qualification')
    _keys(profile['stages'], {'held', 'released'}, 'Calibration stages')
    if profile['qualification'] == 'pending':
        if profile['evidence_reference'] is not None or any(stage is not None for stage in profile['stages'].values()):
            raise ValueError('Pending template must not contain purported calibration bounds')
        if require_qualified:
            raise ValueError('Sensor calibration qualification is pending')
        return copy.deepcopy(profile)
    _name(profile['evidence_reference'], 'Positive/negative calibration evidence reference')
    for stage in profile['stages'].values():
        _stage_profile(stage)
    _reject_indistinguishable_stages(profile['stages']['held'], profile['stages']['released'])
    return copy.deepcopy(profile)


def _timestamps(sample, written_ns, now_ns):
    stamp = _integer(sample['stamp_ns'], 'Sensor stamp')
    received = _integer(sample['received_ns'], 'Sensor receipt')
    if not stamp <= received <= written_ns <= now_ns:
        raise ValueError('Sensor timestamps are future-dated or inconsistent')
    if received - stamp > WINDOW_NS:
        raise ValueError('Sensor transport delay exceeds 0.5 seconds')
    return stamp, received


def _recent_stream(samples, kind, written_ns, now_ns, min_stamp_ns):
    if not isinstance(samples, list) or not samples:
        raise ValueError('Missing ' + kind + ' samples')
    recent = []
    previous_stamp = previous_receipt = None
    frame = names_set = None
    for sample in samples:
        if kind == 'joints':
            _keys(sample, {'stamp_ns', 'received_ns', 'names', 'position', 'velocity'}, 'Joint sample')
        else:
            _keys(sample, {'stamp_ns', 'received_ns', 'frame_id', 'force', 'torque'}, 'Wrist sample')
        stamp, received = _timestamps(sample, written_ns, now_ns)
        if previous_stamp is not None and (stamp <= previous_stamp or received < previous_receipt):
            raise ValueError('Sensor timestamps must advance')
        previous_stamp, previous_receipt = stamp, received
        if kind == 'joints':
            names = _names(sample['names'])
            if names_set is not None and set(names) != names_set:
                raise ValueError('Joint names changed during the observation window')
            names_set = set(names)
            _vector(sample['position'], 'Joint position', len(names))
            _vector(sample['velocity'], 'Joint velocity', len(names))
        else:
            current_frame = _name(sample['frame_id'], 'Wrist frame')
            if frame is not None and frame != current_frame:
                raise ValueError('Wrist frame changed during the observation window')
            frame = current_frame
            _vector(sample['force'], 'Wrist force')
            _vector(sample['torque'], 'Wrist torque')
        if stamp >= now_ns - WINDOW_NS and stamp > min_stamp_ns:
            recent.append(sample)
    if len(recent) < MIN_SAMPLES:
        raise ValueError('Need at least five fresh ' + kind + ' samples')
    if recent[-1]['stamp_ns'] - recent[0]['stamp_ns'] < MIN_WINDOW_NS:
        raise ValueError('Sensor observation window must span at least 0.2 seconds')
    if any(b['stamp_ns'] - a['stamp_ns'] > MAX_SAMPLE_GAP_NS for a, b in zip(recent, recent[1:])):
        raise ValueError('Sensor observation window contains a sampling gap over 0.1 seconds')
    return recent


def _streams(snapshot, now_ns, min_stamp_ns):
    _keys(snapshot, {'version', 'written_ns', 'ft', 'joints'}, 'Sensor snapshot')
    if type(snapshot['version']) is not int or snapshot['version'] != 1:
        raise ValueError('Unsupported sensor snapshot version')
    now_ns = _integer(now_ns, 'Current time')
    min_stamp_ns = _integer(min_stamp_ns, 'Minimum sample time', allow_zero=True)
    written_ns = _integer(snapshot['written_ns'], 'Snapshot write time')
    if min_stamp_ns > now_ns or not 0 <= now_ns - written_ns <= WINDOW_NS:
        raise ValueError('Sensor snapshot is stale or clock inconsistent')
    _keys(snapshot['ft'], {'left', 'right'}, 'Wrist streams')
    result = {side: _recent_stream(snapshot['ft'][side], side, written_ns, now_ns, min_stamp_ns)
              for side in ('left', 'right')}
    result['joints'] = _recent_stream(snapshot['joints'], 'joints', written_ns, now_ns, min_stamp_ns)
    if abs(result['left'][-1]['stamp_ns'] - result['right'][-1]['stamp_ns']) > MAX_WRIST_SKEW_NS:
        raise ValueError('Latest wrist sample skew exceeds 0.1 seconds')
    if any(abs(value) > MAX_VELOCITY_RAD_S for sample in result['joints'] for value in sample['velocity']):
        raise ValueError('Joint velocity exceeds 0.02 rad/s during sensor inspection')
    return result


def _ranges(samples, field):
    columns = list(zip(*(sample[field] for sample in samples)))
    lows, highs = [min(column) for column in columns], [max(column) for column in columns]
    spans = [b - a for a, b in zip(lows, highs)]
    if any(not math.isfinite(span) for span in spans):
        raise ValueError('Nonfinite sensor range')
    return {'min': lows, 'max': highs, 'span': spans}


def _summary(streams):
    measurements = {}
    for side in ('left', 'right'):
        samples = streams[side]
        measurements[side] = dict(frame_id=samples[0]['frame_id'], count=len(samples),
                                  first_stamp_ns=samples[0]['stamp_ns'], last_stamp_ns=samples[-1]['stamp_ns'],
                                  force_n=_ranges(samples, 'force'), torque_nm=_ranges(samples, 'torque'))
    samples = streams['joints']
    latest_positions = dict(zip(samples[-1]['names'], samples[-1]['position']))
    excluded = sorted(set(latest_positions) & NON_POSTURE_JOINTS)
    measurements['joints'] = dict(count=len(samples), first_stamp_ns=samples[0]['stamp_ns'],
                                  last_stamp_ns=samples[-1]['stamp_ns'], names=list(samples[-1]['names']),
                                  latest_position_rad=list(samples[-1]['position']),
                                  posture_excluded_joint_names=excluded,
                                  excluded_wheel_positions_rad={name: latest_positions[name] for name in excluded},
                                  max_abs_velocity_rad_s=max(abs(v) for sample in samples for v in sample['velocity']))
    measurements['latest_wrist_skew_ns'] = abs(streams['left'][-1]['stamp_ns'] - streams['right'][-1]['stamp_ns'])
    return measurements


def inspect(snapshot, now_ns, min_stamp_ns=0):
    """Inspect fresh finite telemetry at rest, without classifying a box state."""
    streams = _streams(snapshot, now_ns, min_stamp_ns)
    return dict(source='wrist_ft_joint_telemetry', inspected_ns=now_ns,
                measurements=_summary(streams), box_state_evaluated=False)


def evaluate(snapshot, profile, state, now_ns, min_stamp_ns=0):
    """Classify a qualified empirical load/pose envelope, not visual box facts."""
    if state not in ('held', 'released'):
        raise ValueError('Expected held or released sensor state')
    if not isinstance(profile, dict):
        raise ValueError('Missing qualified sensor profile')
    profile = validate_profile(profile, profile.get('geometry_id'), require_qualified=True)
    streams = _streams(snapshot, now_ns, min_stamp_ns)
    stage = profile['stages'][state]
    expected_pose = stage['pose']['position_rad']
    max_pose_error = 0.0
    for sample in streams['joints']:
        posture_names = set(sample['names']) - NON_POSTURE_JOINTS
        if posture_names != set(expected_pose):
            raise ValueError('Calibration pose must cover exactly the observed non-wheel joints')
        error = max(abs(position - expected_pose[name])
                    for name, position in zip(sample['names'], sample['position'])
                    if name not in NON_POSTURE_JOINTS)
        max_pose_error = max(max_pose_error, error)
        if error > stage['max_pose_error_rad'] + 1e-12:
            raise ValueError('Measured joints differ from the calibrated post-task posture')
    measurements = _summary(streams)
    for side in ('left', 'right'):
        calibration = stage[side]
        if measurements[side]['frame_id'] != calibration['frame_id']:
            raise ValueError('Wrist frame does not match calibration')
        for kind, unit in (('force', 'n'), ('torque', 'nm')):
            observed = measurements[side][kind + '_' + unit]
            if any(low < allowed_low or high > allowed_high for low, high, allowed_low, allowed_high in zip(
                    observed['min'], observed['max'], calibration[kind + '_min'], calibration[kind + '_max'])):
                raise ValueError('Wrist ' + kind + ' outside the calibrated ' + state + ' envelope')
            if max(observed['span']) > calibration['max_' + kind + '_span_' + unit] + 1e-12:
                raise ValueError('Wrist ' + kind + ' unstable over the observation window')
    measurements['joints']['max_calibration_pose_error_rad'] = max_pose_error
    return dict(state=state, source='wrist_ft_pose_envelope', verified_ns=now_ns,
                profile_id=profile['id'], geometry_id=profile['geometry_id'],
                evidence_reference=profile['evidence_reference'], measurements=measurements,
                directly_measured=['wrist_force', 'wrist_torque', 'joint_position', 'joint_velocity'],
                not_directly_measured=['box_identity', 'separation_from_another_box', 'destination_support'])
