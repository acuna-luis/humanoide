"""Pure continuous telemetry cache for the optional optimistic executor.

Fresh data are retained, not a reusable permission bit. A technical failure is
latched for the session. Motion-health validation does not assert rest, HOME,
grasp, support or force calibration. The ordinary rest classifier is preserved
for transitions and HOME verification.
"""
from collections import deque
import copy
import json
import math

if __package__:
    from . import scenario1_checks as checks
    from scripts.lib import cruzr_home_posture_gate as home_gate
else:
    import scenario1_checks as checks
    import cruzr_home_posture_gate as home_gate


SAFETY = ('estop', 'servo', 'charger', 'battery')
PUBLISHERS = (*SAFETY, 'actuator', 'status', 'controller')
MAX_AGE_NS = 2_000_000_000
MAX_SNAPSHOT_AGE_NS = 1_000_000_000
# Passive observation on this unit (2026-09-28): the two UInt8 stop streams
# publish about every 4.49 s; they contain no source stamp. Reserve 0.508 s over
# the observed longest interval, without rewriting their actual receipts.
# This is an explicit receipt-age policy, not a physical stop-response bound.
RECEIPT_MAX_AGE_NS = {key: (5_000_000_000 if key in ('estop', 'servo') else MAX_AGE_NS)
                      for key in (*SAFETY, 'actuator', 'controller')}


class LiveHealthPending(RuntimeError):
    """Startup acquisition or a bounded post-result settling window is incomplete."""


def _integer(value, label, *, positive=True):
    if type(value) is not int or value < (1 if positive else 0):
        raise ValueError('LIVE_HEALTH_INVALID: '+label)
    return value


def _object(value):
    if not isinstance(value, dict):
        raise ValueError('LIVE_HEALTH_INVALID: expected message object')
    json.dumps(value, allow_nan=False)
    return value


def source_stamp_ns(message):
    try:
        stamp = message['header']['stamp']
        sec = _integer(stamp['sec'], 'source seconds', positive=False)
        nanosec = _integer(stamp['nanosec'], 'source nanoseconds', positive=False)
        if nanosec >= 10**9:
            raise ValueError('LIVE_HEALTH_INVALID: source nanoseconds')
        return _integer(sec*10**9+nanosec, 'source timestamp')
    except (KeyError, TypeError) as error:
        raise ValueError('LIVE_HEALTH_INVALID: missing source timestamp') from error


def _age(now, stamp, maximum, label):
    _integer(now, label+' current time')
    _integer(stamp, label+' timestamp')
    if not 0 <= now-stamp <= maximum:
        raise ValueError('LIVE_HEALTH_STALE: '+label)


def _battery(message):
    socs = []
    def collect(value):
        if isinstance(value, dict):
            for name, child in value.items():
                if name == 'batsoc':
                    if type(child) not in (int, float) or not math.isfinite(child):
                        raise ValueError('LIVE_HEALTH_BATTERY: invalid charge')
                    socs.append(child)
                else:
                    collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)
    collect(message)
    if len(socs) != 2 or any(not checks.MIN_BATTERY_SOC <= value <= 100 for value in socs):
        raise ValueError('LIVE_HEALTH_BATTERY: require two packs above minimum charge')


def _actuator_health(message):
    """Reuse the original schema helpers; omit only its rest-only predicates."""
    items = message.get('act_item')
    if not isinstance(items, list):
        raise ValueError('LIVE_HEALTH_ACTUATOR: missing act_item')
    by_id = {}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('LIVE_HEALTH_ACTUATOR: malformed actuator')
        identity = home_gate.integer(item, 'id')
        if not identity or identity in by_id:
            raise ValueError('LIVE_HEALTH_ACTUATOR: invalid or duplicate actuator')
        by_id[identity] = item
    maximum_velocity = maximum_delta = 0.0
    for logical_name, aliases in home_gate.BODY_ACTUATOR_ALIASES:
        matches = [identity for identity in aliases if identity in by_id]
        if len(matches) != 1:
            raise ValueError('LIVE_HEALTH_ACTUATOR: incomplete or ambiguous 20D '+logical_name)
        item = by_id[matches[0]]
        error_code = home_gate.integer(item, 'error_code')
        status = home_gate.integer(item, 'status')
        position = home_gate.numeric(item, 'position')
        velocity = home_gate.numeric(item, 'velocity')
        command = home_gate.numeric(item, 'cmd_pos')
        if not math.isfinite(command-position):
            raise ValueError('LIVE_HEALTH_ACTUATOR: nonfinite command difference')
        if error_code or status & 0x0008 or status & 0x0007 != 0x0007:
            raise ValueError('LIVE_HEALTH_ACTUATOR: fault or disabled actuator '+str(matches[0]))
        maximum_velocity = max(maximum_velocity, abs(velocity))
        maximum_delta = max(maximum_delta, abs(command-position))
    return dict(actuator_body_count=20, actuator_arm_count=14,
                max_abs_velocity=maximum_velocity, max_abs_command_delta=maximum_delta)


def _status(message):
    rows = message.get('status_list')
    if (not isinstance(rows, list) or any(not isinstance(row, dict) or
            type(row.get('status')) is not int or row['status'] not in (1, 2, 3, 4, 5, 6)
            for row in rows)):
        raise ValueError('LIVE_HEALTH_STATUS: malformed or unknown action status')
    return [row['status'] for row in rows]


def _validate_message(key, message):
    _object(message)
    if key in ('estop', 'servo', 'charger'):
        checks._scalar_zero(message, key)
    elif key == 'battery':
        _battery(message)
    elif key == 'actuator':
        _actuator_health(message)
        source_stamp_ns(message)
    elif key == 'controller':
        checks.parse_controller_response(message)
    elif key == 'status':
        _status(message)
    else:
        raise ValueError('LIVE_HEALTH_INVALID: unknown stream')


def _record(record, now_ns, now_monotonic_ns, label, *, retained=False):
    if not isinstance(record, dict) or set(record) != {'message', 'received_ns', 'received_monotonic_ns'}:
        raise ValueError('LIVE_HEALTH_INVALID: '+label+' record')
    maximum = max(now_ns, now_monotonic_ns) if retained else RECEIPT_MAX_AGE_NS[label]
    _age(now_ns, record['received_ns'], maximum, label+' receipt')
    _age(now_monotonic_ns, record['received_monotonic_ns'], maximum, label+' monotonic receipt')
    _validate_message(label, record['message'])
    if label == 'actuator':
        stamp = source_stamp_ns(record['message'])
        _age(record['received_ns'], stamp, MAX_AGE_NS, 'actuator source at receipt')
        _age(now_ns, stamp, MAX_AGE_NS, 'actuator source')
    return record['message']


def validate_snapshot(snapshot, *, now_ns, now_monotonic_ns, stationary=False,
                      after_ns=None, require_home=False):
    """Validate real evidence; pending never means safe or authorized to move."""
    if type(stationary) is not bool or type(require_home) is not bool or require_home and not stationary:
        raise ValueError('LIVE_HEALTH_INVALID: stationary/HOME flags')
    if after_ns is not None:
        _integer(after_ns, 'action completion', positive=False)
    fields = {'version', 'written_ns', 'written_monotonic_ns', 'error', 'safety',
              'actuator', 'status', 'controller', 'publishers', 'actuator_duplicates_ignored'}
    if not isinstance(snapshot, dict) or set(snapshot) != fields:
        raise ValueError('LIVE_HEALTH_INVALID: snapshot fields')
    if type(snapshot['version']) is not int or snapshot['version'] != 1:
        raise ValueError('LIVE_HEALTH_INVALID: snapshot version')
    _age(now_ns, snapshot['written_ns'], MAX_SNAPSHOT_AGE_NS, 'snapshot')
    _age(now_monotonic_ns, snapshot['written_monotonic_ns'], MAX_SNAPSHOT_AGE_NS, 'snapshot monotonic')
    if snapshot['error'] is not None:
        if not isinstance(snapshot['error'], str) or not snapshot['error']:
            raise ValueError('LIVE_HEALTH_INVALID: latched error')
        raise ValueError('LIVE_HEALTH_FAILED: '+snapshot['error'])
    _integer(snapshot['actuator_duplicates_ignored'], 'duplicate count', positive=False)
    safety, samples, publishers = snapshot['safety'], snapshot['actuator'], snapshot['publishers']
    if not isinstance(safety, dict) or set(safety)-set(SAFETY):
        raise ValueError('LIVE_HEALTH_INVALID: safety streams')
    if not isinstance(samples, list) or len(samples) > 2:
        raise ValueError('LIVE_HEALTH_INVALID: actuator window')
    if not isinstance(publishers, dict) or set(publishers)-set(PUBLISHERS):
        raise ValueError('LIVE_HEALTH_INVALID: publisher inventory')
    for key, count in publishers.items():
        if type(count) is not int or count < 0 or count > 1:
            raise ValueError('LIVE_HEALTH_PUBLISHERS: '+key+' is not unique')
    # Validate every available record before declaring incomplete startup.
    values = {key: _record(value, now_ns, now_monotonic_ns, key) for key, value in safety.items()}
    actuators = [_record(row, now_ns, now_monotonic_ns, 'actuator') for row in samples]
    for key in ('status', 'controller'):
        if snapshot[key] is not None:
            _record(snapshot[key], now_ns, now_monotonic_ns, key, retained=key == 'status')
    if (set(safety) != set(SAFETY) or len(samples) != 2 or snapshot['status'] is None or
            snapshot['controller'] is None or set(publishers) != set(PUBLISHERS) or
            any(value != 1 for value in publishers.values())):
        raise LiveHealthPending('LIVE_HEALTH_PENDING: incomplete startup telemetry')
    stamps = [source_stamp_ns(message) for message in actuators]
    if stamps[1] <= stamps[0]:
        raise ValueError('LIVE_HEALTH_ACTUATOR: source timestamps did not advance')
    if any(samples[1][key] < samples[0][key] for key in ('received_ns', 'received_monotonic_ns')):
        raise ValueError('LIVE_HEALTH_ACTUATOR: receipt clock regressed')
    health = checks.parse_health(*(values[key] for key in SAFETY))
    controllers = checks.parse_controller_response(snapshot['controller']['message'])
    statuses = _status(snapshot['status']['message'])
    if stationary:
        if any(value in (1, 2, 3) for value in statuses):
            # The own terminal result can arrive before DDS updates its retained
            # status. Runtime allows only its existing bounded settling window;
            # no action may start while any status is still active.
            raise LiveHealthPending('LIVE_HEALTH_PENDING: terminal action status pending')
        checks.parse_idle_status(snapshot['status']['message'])
    if after_ns is not None and any(stamp <= after_ns or row['received_ns'] <= after_ns
                                    for stamp, row in zip(stamps, samples)):
        raise LiveHealthPending('LIVE_HEALTH_PENDING: two actuator samples after the action result required')
    posture = [_actuator_health(message) for message in actuators]
    if stationary:
        if any(row['max_abs_velocity'] > .02 or row['max_abs_command_delta'] > .01 for row in posture):
            raise LiveHealthPending('LIVE_HEALTH_SETTLING: rest/command agreement not yet measured')
        posture = [dict(line.split('=', 1) for line in home_gate.classify(message, .02))
                   for message in actuators]
        if require_home and any(row['MEASURED_HOME'] != '1' for row in posture):
            raise ValueError('HOME_NOT_MEASURED: HOME 20D required')
    return dict(safety=health, posture=posture, controller=controllers, status=statuses,
                stationary_checked=stationary, home_required=require_home,
                actuator_stamps_ns=stamps, snapshot_written_ns=snapshot['written_ns'],
                safety_receipts={key: dict(age_ns=now_ns-safety[key]['received_ns'],
                    monotonic_age_ns=now_monotonic_ns-safety[key]['received_monotonic_ns'],
                    max_age_ns=RECEIPT_MAX_AGE_NS[key]) for key in SAFETY},
                source='continuous_live_telemetry', box_state_measured=False)


class LiveHealthCache:
    def __init__(self):
        self.safety = {}
        self.actuator = deque(maxlen=2)
        self.status = self.controller = None
        self.publishers = {}
        self.seen_publishers = set()
        self.error = None
        self.duplicates_ignored = 0

    def fail(self, reason):
        if self.error is None:
            self.error = str(reason) or 'unspecified live health failure'

    def add(self, key, message, received_ns, received_monotonic_ns):
        if self.error is not None:
            raise ValueError('LIVE_HEALTH_FAILED: '+self.error)
        try:
            _integer(received_ns, 'receipt')
            _integer(received_monotonic_ns, 'monotonic receipt')
            _validate_message(key, message)
            record = dict(message=copy.deepcopy(message), received_ns=received_ns,
                          received_monotonic_ns=received_monotonic_ns)
            if key == 'actuator':
                stamp = source_stamp_ns(message)
                _age(received_ns, stamp, MAX_AGE_NS, 'actuator source at receipt')
                if self.actuator:
                    previous = self.actuator[-1]
                    previous_stamp = source_stamp_ns(previous['message'])
                    if any(record[name] < previous[name] for name in ('received_ns', 'received_monotonic_ns')):
                        raise ValueError('LIVE_HEALTH_ACTUATOR: receipt clock regressed')
                    if stamp <= previous_stamp:
                        equal = json.dumps(message, sort_keys=True, allow_nan=False) == json.dumps(
                            previous['message'], sort_keys=True, allow_nan=False)
                        if stamp == previous_stamp and equal:
                            self.duplicates_ignored += 1
                            return
                        raise ValueError('LIVE_HEALTH_ACTUATOR: conflicting or nonadvancing source timestamp')
                self.actuator.append(record)
            elif key in SAFETY:
                self.safety[key] = record
            else:
                setattr(self, key, record)
        except Exception as error:
            self.fail(error)
            raise

    def set_publishers(self, publishers):
        if self.error is not None:
            raise ValueError('LIVE_HEALTH_FAILED: '+self.error)
        try:
            if not isinstance(publishers, dict) or set(publishers) != set(PUBLISHERS):
                raise ValueError('LIVE_HEALTH_PUBLISHERS: incomplete inventory')
            for key, count in publishers.items():
                if type(count) is not int or count not in (0, 1) or count == 0 and key in self.seen_publishers:
                    raise ValueError('LIVE_HEALTH_PUBLISHERS: lost or ambiguous '+key)
                if count == 1:
                    self.seen_publishers.add(key)
            self.publishers = dict(publishers)
        except Exception as error:
            self.fail(error)
            raise

    def snapshot(self, now_ns, now_monotonic_ns):
        return copy.deepcopy(dict(version=1, written_ns=now_ns, written_monotonic_ns=now_monotonic_ns,
            error=self.error, safety=self.safety, actuator=list(self.actuator),
            status=self.status, controller=self.controller, publishers=self.publishers,
            actuator_duplicates_ignored=self.duplicates_ignored))
