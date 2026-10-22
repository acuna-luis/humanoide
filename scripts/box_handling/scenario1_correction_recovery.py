"""Pure evidence contract for one canceled visual correction, never motion.

A validated report proves a narrowly classified terminal cancellation. It does
not prove physical stopping, authorize another goal, or clear any failed guard.
The supervisor must separately obtain fresh health, rest and visual evidence.
"""
import copy
import uuid


RECOVERY_RETURN_CODE = 4
FAILURE_CODE = 'BOX_PICKUP_NO_PROGRESS'
EVENT = 'correction_recovery_required'
_REASON = 'Correction made no significant progress'
_MARKER_FIELDS = frozenset(('event', 'version', 'code', 'goal_id', 'attempt',
                            'terminal_received_ns', 'physical_stop_verified'))
_METADATA_FIELDS = frozenset(('time_ns', 'request_id'))
_ALLOWED_EVENTS = frozenset(('dispatched', 'accepted', 'feedback', 'status',
                            'result_pending', 'result', 'error', 'cancel_requested',
                            'cancel_response', 'correction_guard',
                            'interrupted_terminal', EVENT))


class CorrectionRecoveryRequired(RuntimeError):
    """Carry classified cancellation evidence without treating it as success."""

    def __init__(self, report, channel=None):
        self.report = copy.deepcopy(report)
        self.channel = channel
        super().__init__('BOX_PICKUP_CORRECTION_RECOVERY_REQUIRED: canceled navigation; '
                         'fresh stationary verification required')


def _fail(reason):
    raise ValueError('CORRECTION_RECOVERY_INVALID: ' + reason)


def _integer(value, label, *, minimum=0, maximum=None):
    if (type(value) is not int or value < minimum or
            maximum is not None and value > maximum):
        _fail(label + ' must be an integer within its permitted range')
    return value


def _canonical_uuid(value):
    if not isinstance(value, str):
        _fail('goal_id must be a canonical UUID')
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        _fail('goal_id must be a canonical UUID')
    if str(parsed) != value:
        _fail('goal_id must be a canonical UUID')
    return parsed


def validate_recovery(request, rows):
    """Return an isolated marker only for the exact opt-in canceled outcome.

    Event order is taken from the ordered request stream. Optional receipt
    metadata does not substitute for the matching UUID, accepted cancellation
    response and terminal result. All other failures remain unrecoverable.
    """
    if not isinstance(request, dict) or request.get('allow_correction_recovery') is not True:
        _fail('explicit recovery opt-in required')
    correction, goal = request.get('correction'), request.get('goal')
    if (not isinstance(correction, dict) or correction.get('point') != 'box_pickup' or
            not isinstance(goal, dict) or goal.get('command') != 'navigation_start'):
        _fail('recovery only supports visual pickup navigation')
    attempt = _integer(correction.get('attempt'), 'attempt', minimum=1, maximum=7)
    if not isinstance(rows, list) or not rows or any(not isinstance(row, dict) for row in rows):
        _fail('ordered request evidence must be a nonempty list of objects')

    indexed = {}
    for index, row in enumerate(rows):
        event = row.get('event')
        if not isinstance(event, str) or event not in _ALLOWED_EVENTS:
            _fail('unsupported or failed event in request evidence')
        indexed.setdefault(event, []).append((index, row))
        if 'time_ns' in row:
            _integer(row['time_ns'], 'event receipt time', minimum=1)
        if 'request_id' in row and ('request_id' in request and
                                    row['request_id'] != request['request_id']):
            _fail('request identity mismatch')

    def one(event):
        entries = indexed.get(event, [])
        if len(entries) != 1:
            _fail('exactly one ' + event + ' event required')
        return entries[0]

    marker_index, marker = one(EVENT)
    if (not _MARKER_FIELDS <= marker.keys() or
            marker.keys() - (_MARKER_FIELDS | _METADATA_FIELDS)):
        _fail('unexpected or missing recovery marker fields')
    if (type(marker['version']) is not int or marker['version'] != 1 or
            marker['code'] != 'NO_PROGRESS_CANCELLED' or
            marker['physical_stop_verified'] is not False):
        _fail('invalid recovery marker classification')
    if _integer(marker['attempt'], 'marker attempt', minimum=1, maximum=7) != attempt:
        _fail('marker attempt differs from request')
    terminal_received = _integer(marker['terminal_received_ns'], 'terminal receipt', minimum=1)
    if 'time_ns' in marker and terminal_received > marker['time_ns']:
        _fail('terminal receipt is later than the recovery marker')
    goal_uuid = _canonical_uuid(marker['goal_id'])

    for row in rows:
        observed = row.get('goal_id')
        if observed != str(goal_uuid):
            # Preparing/armed snapshots precede dispatch and have no UUID yet.
            if not (row['event'] == 'correction_guard' and observed is None and
                    row.get('phase') in ('preparing', 'armed')):
                _fail('event goal identity differs from canceled goal')
        if row.get('physical_stop_verified', False) is not False:
            _fail('cancellation cannot certify physical stopping')
        if row['event'] == 'status':
            _integer(row.get('status'), 'action status', minimum=1, maximum=5)
            if row['status'] not in (1, 2, 3, 5):
                _fail('unconfirmed or conflicting action status')
        if row['event'] == 'correction_guard' and 'snapshot' in row:
            snapshot = row['snapshot']
            if (not isinstance(snapshot, dict) or snapshot.get('point') != 'box_pickup' or
                    type(snapshot.get('attempt')) is not int or snapshot['attempt'] != attempt):
                _fail('guard snapshot differs from requested correction')
            if (snapshot.get('failure') not in (None, _REASON) or
                    snapshot.get('velocity_violation') is not None or
                    snapshot.get('telemetry_failure') not in (None, _REASON)):
                _fail('guard snapshot contains another failure')

    accepted_index, accepted = one('accepted')
    if accepted.get('accepted') is not True:
        _fail('goal acceptance was not confirmed')
    error_index, error = one('error')
    if error.get('failure_code') != FAILURE_CODE or error.get('reason') != _REASON:
        _fail('failure is not the typed no-progress outcome')
    cancel_index, cancel = one('cancel_requested')
    if cancel.get('physical_stop_verified') is not False:
        _fail('cancel request must preserve unknown physical stop')
    response_index, response_row = one('cancel_response')
    response = response_row.get('response')
    if (not isinstance(response, dict) or type(response.get('return_code')) is not int or
            response['return_code'] != 0):
        _fail('cancellation response must explicitly accept cancellation')
    canceling = response.get('goals_canceling')
    if not isinstance(canceling, list) or len(canceling) != 1 or not isinstance(canceling[0], dict):
        _fail('cancellation must identify exactly one goal')
    identifier = canceling[0].get('goal_id')
    values = identifier.get('uuid') if isinstance(identifier, dict) else None
    if (not isinstance(values, list) or len(values) != 16 or
            any(type(value) is not int or not 0 <= value <= 255 for value in values) or
            uuid.UUID(bytes=bytes(values)) != goal_uuid):
        _fail('cancel acknowledgment UUID does not match canceled goal')

    result_index, result = one('result')
    interrupted_index, interrupted = one('interrupted_terminal')
    for row in (result, interrupted):
        if type(row.get('status')) is not int or row['status'] != 5:
            _fail('exactly canceled terminal status required')
    if interrupted.get('physical_stop_verified') is not False:
        _fail('terminal cancellation must preserve unknown physical stop')
    if (not accepted_index < error_index < cancel_index < response_index < marker_index or
            not cancel_index < result_index < interrupted_index < marker_index):
        _fail('cancellation evidence is out of order')
    if marker_index != len(rows)-1:
        _fail('recovery marker must close the request evidence')
    return copy.deepcopy(marker)


def _validate_retirement(marker, rows, request_id):
    """Validate the final parked-worker stream through its deliberate EOF.

    A zero process exit alone cannot hide an opaque log, contradictory terminal
    status or unrelated callback received after the recovery marker. The caller
    separately checks the process exit and post-cancellation physical telemetry.
    """
    if (not isinstance(marker, dict) or marker.get('event') != EVENT or
            type(marker.get('version')) is not int or marker['version'] != 1 or
            marker.get('code') != 'NO_PROGRESS_CANCELLED' or
            marker.get('physical_stop_verified') is not False):
        _fail('retirement requires the classified cancellation marker')
    goal_id = str(_canonical_uuid(marker.get('goal_id')))
    if not isinstance(request_id, str) or not request_id:
        _fail('retirement requires the completed request identity')
    if not isinstance(rows, list) or not rows or any(not isinstance(row, dict) for row in rows):
        _fail('retirement requires the final ordered worker stream')
    for index, row in enumerate(rows):
        if 'time_ns' in row:
            _integer(row['time_ns'], 'retirement event receipt', minimum=1)
        event = row.get('event')
        if index == len(rows)-1:
            if (event != 'session_closed' or 'request_id' not in row or
                    row['request_id'] is not None or
                    row.get('reason') != 'Request input pipe disconnected'):
                _fail('retirement must end with confirmed request-input EOF')
            continue
        if event not in ('status', 'feedback'):
            _fail('unexpected event after canceled correction')
        if row.get('goal_id') != goal_id or row.get('request_id') != request_id:
            _fail('retirement event identity mismatch')
        if row.get('physical_stop_verified', False) is not False:
            _fail('retirement cannot certify physical stopping')
        if event == 'status':
            _integer(row.get('status'), 'retirement action status', minimum=1, maximum=5)
            if row['status'] not in (1, 2, 3, 5):
                _fail('conflicting action status during retirement')
    return copy.deepcopy(rows)


def validate_retirement(marker, rows, request_id):
    """Return the isolated final stream, or reject unconfirmed retirement."""
    try:
        return _validate_retirement(marker, rows, request_id)
    except ValueError as error:
        raise ValueError('CORRECTION_RETIREMENT_INVALID: '+str(error)) from error
