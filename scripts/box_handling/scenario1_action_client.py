#!/usr/bin/env python3
"""Bounded native ROSA actions with JSONL evidence and targeted cancellation.

Run inside a discovered Motion container after sourcing /opt/walker/setup.bash.
This transport does not check physical readiness. Its caller must do that before
dispatch and verify measured motion after a terminal response. Cancellation and
terminal action state are never certificates of physical stopping.

Native API reference: archived rosa/action_client.py from the 2026-09-21 front
SPS audit. The installed SDK is not modified. Its goal callback loses the real
acceptance flag, and its cancel helper swaps the stored UUID; this adapter reads
the response directly and copies the UUID into its own cancel request.
Optional --serve keeps one reviewed client alive for sequential requests, and
exits permanently on failure except for an explicitly requested, fully observed
HOME MoveToGoalFailed result handed back to the supervisor. It never retries.
"""

import argparse
import ast
import hashlib
import inspect
import json
import math
from pathlib import Path
import queue
import re
import signal
import sys
import textwrap
import threading
import time

if __package__:
    from .scenario1_request_ids import RequestIds
else:
    from scenario1_request_ids import RequestIds


ENDPOINTS = {'motion': '/mc/manipulation/action',
             'navigation': '/vnav/task/command',
             'planning': '/vnav/action/planning'}
PLANNING_COMMANDS = frozenset(('set_map', 'check_state'))
TERMINAL = frozenset((4, 5, 6))
# Canonical AST of the complete classes printed in rosa-python-api.txt, audit
# 20260921T112801Z_FRONT_NATIVE_INTEGRATION_AUDIT. File SHA256:
# 9dd5847821849ba18c95dec0f69c35f2e6d95d8b3c82100b25b25608fcfd2ca9.
# Comments/formatting may differ. Any code change requires another API review.
SUPPORTED_NATIVE_CLASSES = {
    'ActionClient': '77d2049e4046f30fe875ec3d396ce177702071f80b76cbea8265d5c0640a4559',
    'ActionClientGoalHandle': '6d0df69d6e6a14e3eb2f6b6c0109a2b857b6750739c3cba0aebeda708e41fa3a',
}


def class_fingerprint(source, name):
    """Stable between Python 3.10/3.12; includes method bodies and signatures."""
    parsed = ast.parse(textwrap.dedent(source))
    classes = [item for item in parsed.body if isinstance(item, ast.ClassDef) and item.name == name]
    if len(classes) != 1:
        raise ValueError('Missing unique native class: ' + name)

    def canonical(value):
        if isinstance(value, ast.AST):
            # Python 3.12 added empty type_params fields. Nonempty parameters
            # remain significant, so code using generics does not bypass pinning.
            return {'_type': type(value).__name__, **{
                key: canonical(item) for key, item in ast.iter_fields(value)
                if key != 'type_params' or item}}
        if isinstance(value, list):
            return [canonical(item) for item in value]
        if value is Ellipsis:
            return {'_constant': 'Ellipsis'}
        return value

    raw = json.dumps(canonical(classes[0]), sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def validate_native_sources(classes, expected=SUPPORTED_NATIVE_CLASSES,
                            source_reader=inspect.getsource):
    observed = {}
    for name, cls in classes.items():
        try:
            observed[name] = class_fingerprint(source_reader(cls), name)
        except Exception as error:
            raise RuntimeError('NATIVE_API_UNREVIEWED: cannot inspect ' + name) from error
    if observed != expected:
        raise RuntimeError('NATIVE_API_UNREVIEWED: native client source changed; no goal sent. '
                           + json.dumps(observed, sort_keys=True))
    return observed


def require_callables(value, names, label):
    for name in names:
        if not callable(getattr(value, name, None)):
            raise RuntimeError('NATIVE_API_UNSUPPORTED: missing ' + label + '.' + name)


def validate_native_client(client):
    """Check native bindings and generated message helpers before dispatch."""
    require_callables(client, ('send_goal_async', 'send_result_request_async',
                              'is_action_server_ready'), 'ActionClient')
    for attribute in ('_goal_client', '_result_client', '_cancel_client'):
        require_callables(getattr(client, attribute, None),
                          ('call_async', 'get_result', 'getServiceCount'), attribute)
    for attribute in ('_feedback_reader', '_status_reader'):
        require_callables(getattr(client, attribute, None), ('getWriterCount',), attribute)
    for attribute, methods in (
            ('Goal', ('msg_from_json',)), ('Result', ('msg_to_json',)),
            ('Feedback', ('msg_to_json',)), ('CancelResponse', ('msg_to_json',))):
        message_type = getattr(client, attribute, None)
        require_callables(message_type, ('getTypeHelper',), attribute)
        require_callables(message_type.getTypeHelper(), methods, attribute + '.TypeHelper')
    response_type = getattr(getattr(client, 'SendGoalService', None), 'Response', None)
    require_callables(response_type, ('getTypeHelper',), 'SendGoalService.Response')
    require_callables(response_type.getTypeHelper(), ('msg_to_json',), 'SendGoalService.Response.TypeHelper')
    require_callables(client, ('CancelRequest',), 'ActionClient')
    try:
        client.CancelRequest().goal_info.goal_id.uuid
        if not isinstance(client._goal_handles, dict) or not isinstance(client._goal_futures, dict):
            raise ValueError('Unsupported native handle storage')
    except Exception as error:
        raise RuntimeError('NATIVE_API_UNSUPPORTED: cancel request/goal storage layout') from error


def object_json(raw):
    """Reject duplicate keys and nonfinite numbers before sending to ROSA."""
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError('Duplicate JSON key: ' + key)
            value[key] = item
        return value

    def invalid(value):
        raise ValueError('Nonfinite JSON number: ' + value)

    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
    # JSON exponents can overflow without invoking parse_constant.
    json.dumps(value, allow_nan=False)
    if not isinstance(value, dict):
        raise ValueError('Expected a JSON object')
    return value


def validate_goal(kind, raw):
    goal = object_json(raw)
    if kind not in ENDPOINTS:
        raise ValueError('Unsupported action kind')
    if kind == 'planning':
        # This native endpoint can also move the base. Only the reviewed map
        # refresh/readiness commands are admitted here, with no target or flags.
        if (set(goal) != {'command', 'map_name'}
                or not isinstance(goal['command'], str)
                or goal['command'] not in PLANNING_COMMANDS
                or goal['map_name'] != 'utars_nav_map'):
            raise ValueError('Planning goal requires only set_map/check_state and map_name utars_nav_map')
        return goal
    fields = ('task_name', 'yaml_args') if kind == 'motion' else ('command', 'arg_json')
    if set(goal) != set(fields) or any(not isinstance(goal[k], str) for k in fields):
        raise ValueError('Goal must contain exactly string fields ' + ', '.join(fields))
    if not goal[fields[0]].strip():
        raise ValueError('Empty action command')
    object_json(goal[fields[1]])
    return goal


def check_lease(path, now):
    if path is None:
        return
    lease = object_json(Path(path).read_text())
    deadline = lease.get('deadline')
    if (isinstance(deadline, bool) or not isinstance(deadline, (int, float))
            or not math.isfinite(deadline) or now >= deadline):
        raise RuntimeError('Lease missing, invalid or expired')


def result_succeeded(kind, status, result):
    if status != 4 or not isinstance(result, dict):
        return False
    if kind == 'motion':
        return result.get('state', {}).get('desc') == 'SUCCEED' and result.get(
            'state', {}).get('state') == 1101001
    if kind == 'planning':
        state = result.get('state')
        return (type(status) is int and isinstance(state, dict)
                and state.get('desc') in ('READY', 'FINISH'))
    # Navigation command semantics and measured arrival belong to the caller.
    return True


def correction_module():
    # Runtime can supply this reviewed module in memory; ordinary invocations
    # without a correction do not need to import it or create telemetry readers.
    if __package__:
        from . import scenario1_nav_correction
    else:
        import scenario1_nav_correction
    return scenario1_nav_correction


def native_client_class(base, to_string):
    """Adapt the observed native API, without treating a local handle as accepted."""
    class ObservedClient(base):
        def configure_observer(self, emit):
            self.observer = emit
            self.retired_goal_ids = set()
            self.reset_observation()

        def reset_observation(self):
            self.observed_goal_id = None
            self.accepted = False
            self.terminal = False
            self.result_pending = False
            self.result_requested_at = float('-inf')
            self.last_status = None
            self.cancel_future = None

        def retire_successful_goal(self):
            """Release only a confirmed terminal request, keeping DDS entities."""
            goal_id = self.observed_goal_id
            if (not goal_id or not self.accepted or not self.terminal
                    or self.result_pending or self.cancel_future is not None):
                raise RuntimeError('Cannot reuse an unconfirmed/interrupted action client')
            stores = [getattr(self, name, None) for name in
                      ('_goal_handles', '_goal_futures', '_result_futures', '_goal_options')]
            if not all(isinstance(value, dict) for value in stores):
                raise RuntimeError('NATIVE_API_UNSUPPORTED: persistent goal storage')
            self.retired_goal_ids.add(goal_id)
            for value in stores:
                value.pop(goal_id, None)
            self.reset_observation()

        def create_goal_request(self, goal, options=None):
            request, goal_id = super().create_goal_request(goal, options)
            if goal_id in self.retired_goal_ids:
                raise RuntimeError('Native UUID reused; request not sent')
            self.observed_goal_id = goal_id
            return request, goal_id

        def response_error(self, where, error):
            self.observer('error', goal_id=self.observed_goal_id,
                          reason=where + ': ' + str(error))

        def handle_goal_response_async(self, request, *unused):
            try:
                goal_id = to_string(request.goal_id.uuid)
                if goal_id in self.retired_goal_ids:
                    return
                if goal_id != self.observed_goal_id:
                    raise ValueError('Acceptance UUID mismatch')
                response = self._goal_client.get_result(self._goal_futures[goal_id])
                if response is None:
                    raise ValueError('Missing acceptance response')
                data = object_json(self.SendGoalService.Response.getTypeHelper().msg_to_json(response))
                if type(data.get('accepted')) is not bool:
                    raise ValueError('Malformed acceptance response')
                self.accepted = data['accepted']
                self.observer('accepted' if self.accepted else 'rejected',
                              goal_id=goal_id, accepted=self.accepted)
            except Exception as error:
                self.response_error('acceptance', error)

        def request_result(self, now):
            if self.accepted and not self.terminal and not self.result_pending:
                self.result_pending = True
                self.result_requested_at = now
                handle = self._goal_handles[self.observed_goal_id]
                self.send_result_request_async(handle.get_goal_uuid())

        def handel_result_async(self, request, *unused):
            # The misspelling is the name used by the installed native SDK.
            try:
                goal_id = to_string(request.goal_id.uuid)
                if goal_id in self.retired_goal_ids:
                    return
                if goal_id != self.observed_goal_id:
                    raise ValueError('Result UUID mismatch')
                response = self._result_client.get_result(self._result_futures[goal_id])
                self.result_pending = False
                if response is None:
                    raise ValueError('Missing result response')
                status = int(response.status)
                result = object_json(self.Result.getTypeHelper().msg_to_json(response.result))
                self.terminal = status in TERMINAL
                self.observer('result' if self.terminal else 'result_pending',
                              goal_id=goal_id, status=status, result=result)
            except Exception as error:
                self.response_error('result', error)

        def feedback_message(self, message):
            try:
                if to_string(message.goal_id.uuid) != self.observed_goal_id:
                    return
                feedback = object_json(self.Feedback.getTypeHelper().msg_to_json(message.result))
                self.observer('feedback', goal_id=self.observed_goal_id, feedback=feedback)
            except Exception as error:
                self.response_error('feedback', error)

        def status_message(self, message):
            try:
                # Native SWIG vectors expose size(); they need not be iterable.
                for index in range(message.status_list.size()):
                    item = message.status_list[index]
                    if to_string(item.goal_info.goal_id.uuid) != self.observed_goal_id:
                        continue
                    status = int(item.status)
                    if status != self.last_status:
                        self.last_status = status
                        self.observer('status', goal_id=self.observed_goal_id, status=status)
            except Exception as error:
                self.response_error('status', error)

        def cancel_own_goal(self):
            handle = self._goal_handles[self.observed_goal_id]
            request = self.CancelRequest()
            # Assignment copies the fixed UUID field. The vendor helper uses
            # swap(), which can empty the UUID stored in its local goal handle.
            request.goal_info.goal_id.uuid = handle.get_goal_uuid()
            if to_string(request.goal_info.goal_id.uuid) != self.observed_goal_id:
                raise ValueError('Cancel UUID mismatch; request not sent')
            self.cancel_future = self._cancel_client.call_async(request, self.cancel_received)

        def cancel_received(self, *unused):
            try:
                response = self._cancel_client.get_result(self.cancel_future)
                if response is None:
                    raise ValueError('Missing cancellation response')
                data = object_json(self.CancelResponse.getTypeHelper().msg_to_json(response))
                self.observer('cancel_response', goal_id=self.observed_goal_id,
                              response=data, physical_stop_verified=False)
            except Exception as error:
                self.response_error('cancellation', error)

    return ObservedClient


class RosaTransport:
    def __init__(self, kind):
        # All ROSA imports are lazy so lifecycle tests run offline on the PC.
        import rosa
        from rosa.action_client import ActionClient, ActionClientGoalHandle
        from rosa.base._ActionType import to_string
        if kind == 'motion':
            from mc_task_msgs.action import ArmTask as Action
        elif kind == 'planning':
            from vnav_task_msgs.action import VnavCommand as Action
        else:
            from unav_task_msgs.action import Task as Action
        self.rosa = rosa
        self.kind = kind
        self.correction_guard = None
        self.correction_failure = None
        self.correction_armed = False
        self.correction_readers = {}
        self.events = queue.Queue()
        require_callables(rosa, ('init', 'Node', 'spin_once', 'ok', 'shutdown'), 'rosa')
        self.api_fingerprints = validate_native_sources({
            'ActionClient': ActionClient, 'ActionClientGoalHandle': ActionClientGoalHandle})
        rosa.init()
        try:
            self.node = rosa.Node('scenario1_observed_action')
            cls = native_client_class(ActionClient, to_string)
            self.client = cls(self.node, ENDPOINTS[kind], Action)
            validate_native_client(self.client)
            self.client.configure_observer(lambda event, **data: self.events.put(dict(event=event, **data)))
            self.options = ActionClient.SendGoalOptions()
        except BaseException:
            rosa.shutdown()
            raise

    @property
    def goal_id(self):
        return self.client.observed_goal_id

    def ready(self):
        counts = [getattr(self.client, name).getServiceCount()
                  for name in ('_goal_client', '_result_client', '_cancel_client')]
        if any(count > 1 for count in counts):
            raise RuntimeError('Ambiguous native action servers; no goal sent')
        return self.client.is_action_server_ready()

    def send(self, goal):
        value = self.client.Goal.getTypeHelper().msg_from_json(json.dumps(goal, allow_nan=False))
        if value is None:
            raise ValueError('Native goal conversion failed')
        self.client.send_goal_async(value, self.options)
        if not self.goal_id:
            raise RuntimeError('Dispatch UUID unavailable')
        return self.goal_id

    def spin(self):
        if not self.rosa.ok():
            raise RuntimeError('ROSA context stopped')
        self.rosa.spin_once(self.node, 20)
        if time.monotonic() - self.client.result_requested_at >= .5:
            self.client.request_result(time.monotonic())
        time.sleep(.01)

    def drain(self):
        rows = []
        while True:
            try:
                rows.append(self.events.get_nowait())
            except queue.Empty:
                return rows

    def cancel(self):
        self.client.cancel_own_goal()

    def configure_correction(self, spec):
        if self.kind != 'navigation' or self.goal_id is not None or self.correction_guard is not None:
            raise RuntimeError('Correction requires an idle navigation client')
        self.correction_guard = correction_module().Guard(spec, requested_ns=time.time_ns())
        self.correction_failure = None
        self.correction_armed = False
        if self.correction_readers:
            return
        from rosa.base._QoS import SensorDataQoS
        from rosa.utils import resolve_message_type
        for key, topic, type_name in (
                ('map', '/nav/robot_pose', 'geometry_msgs/msg/PoseStamped'),
                ('odom', '/mc/odom', 'nav_msgs/msg/Odometry')):
            qos = SensorDataQoS()
            qos.bestEffort()
            qos.durabilityVolatile()
            qos.keepLast(5)
            self.correction_readers[key] = self.node.create_reader(
                resolve_message_type(type_name), topic, self.correction_callback(key), qos=qos)

    def correction_callback(self, key):
        # The str annotation selects JSON delivery in the inspected native SDK.
        def receive(raw: str):
            if self.correction_guard is None or self.correction_failure is not None:
                return
            try:
                self.correction_guard.add(key, object_json(raw), time.time_ns())
            except Exception as error:
                # Do not throw through the SDK or spin(): cancellation must
                # continue spinning until the active UUID has a terminal result.
                self.correction_failure = str(error)
        return receive

    def check_correction(self):
        if self.correction_failure is not None:
            raise RuntimeError('Correction telemetry failed: ' + self.correction_failure)
        if self.correction_guard is not None and self.correction_armed:
            self.correction_guard.check(time.time_ns())

    def correction_ready(self):
        self.check_correction()
        return (all(reader.getWriterCount() >= 1 for reader in self.correction_readers.values())
                and self.correction_guard.ready(time.time_ns()))

    def arm_correction(self):
        self.check_correction()
        self.correction_guard.arm(time.time_ns())
        self.correction_armed = True

    def begin_correction_settle(self):
        self.check_correction()
        self.correction_guard.begin_settle(time.time_ns())

    def correction_settled(self):
        self.check_correction()
        return self.correction_guard.settled(time.time_ns())

    def correction_snapshot(self):
        return dict(self.correction_guard.summary(),
                    publishers={key: reader.getWriterCount()
                                for key, reader in self.correction_readers.items()},
                    telemetry_failure=self.correction_failure)

    def _finish_terminal_request(self):
        goal_id = self.goal_id
        # No background ROSA spinner exists: callbacks run only in spin().
        # Any unexpected queued evidence still prevents client reuse.
        for row in self.drain():
            if row.get('goal_id') != goal_id or row['event'] not in ('status', 'feedback'):
                raise RuntimeError('Unexpected evidence while completing action request')
        self.check_correction()
        self.client.retire_successful_goal()
        self.correction_guard = None
        self.correction_failure = None
        self.correction_armed = False

    def finish_successful_request(self):
        self._finish_terminal_request()

    def finish_recoverable_home_failure(self, terminal):
        if not known_home_failure(terminal) or terminal['goal_id'] != self.goal_id:
            raise RuntimeError('Unconfirmed HOME failure cannot retire a native goal')
        self._finish_terminal_request()

    def validate_session_api(self):
        for name in ('_goal_handles', '_goal_futures', '_result_futures', '_goal_options'):
            if not isinstance(getattr(self.client, name, None), dict) or getattr(self.client, name):
                raise RuntimeError('NATIVE_API_UNSUPPORTED: initial persistent goal storage ' + name)

    def close(self):
        self.rosa.shutdown()


def run_action(transport, kind, goal, timeout, emit, interrupted=lambda: None,
               lease_file=None, clock=time.monotonic, cancel_grace=8.0):
    """Transport state machine. A late success after interruption stays failure."""
    deadline = clock() + timeout
    accepted = False
    terminal = None
    failure = None
    correction = getattr(transport, 'correction_guard', None) is not None
    last_correction_report = clock()

    def report_correction(phase):
        if correction:
            emit(event='correction_guard', goal_id=transport.goal_id,
                 phase=phase, snapshot=transport.correction_snapshot())

    def check_guards():
        reason = interrupted()
        if reason:
            raise RuntimeError(reason)
        check_lease(lease_file, clock())
        if clock() >= deadline:
            raise TimeoutError('Action deadline exceeded')
        if correction:
            transport.check_correction()

    def observe():
        nonlocal accepted, terminal
        rejected = False
        problem = None
        for row in transport.drain():
            emit(**row)
            if row.get('goal_id') != transport.goal_id:
                problem = 'Event UUID mismatch'
                continue
            if row['event'] == 'accepted':
                accepted = True
            elif row['event'] == 'rejected':
                rejected = True
            elif row['event'] == 'result':
                if row.get('status') not in TERMINAL:
                    problem = 'Nonterminal result mislabeled terminal'
                else:
                    terminal = row
            elif row['event'] == 'error':
                problem = row.get('reason', 'Native action error')
        if problem:
            raise RuntimeError(problem)
        return rejected

    try:
        if kind == 'planning':
            # Also protect in-memory callers that do not enter via CLI/session.
            validate_goal(kind, json.dumps(goal, allow_nan=False))
        if correction and (kind != 'navigation' or goal.get('command') != 'navigation_start'):
            raise ValueError('Correction is limited to navigation_start')
        if correction:
            correction_module().require_motion_qualified()
        discovery_deadline = min(deadline, clock() + 5.0)
        while not transport.ready():
            check_guards()
            if clock() >= discovery_deadline:
                raise TimeoutError('Action server unavailable')
            transport.spin()
        if correction:
            report_correction('preparing')
            readiness_deadline = min(deadline, clock() + 5.0)
            while not transport.correction_ready():
                check_guards()
                if clock() >= readiness_deadline:
                    raise TimeoutError('Correction fresh stationary telemetry unavailable')
                transport.spin()
            check_guards()
            transport.arm_correction()
            report_correction('armed')
        check_guards()
        goal_id = transport.send(goal)
        emit(event='dispatched', goal_id=goal_id, endpoint=ENDPOINTS[kind])
        acceptance_deadline = min(deadline, clock() + 5.0)
        while terminal is None:
            check_guards()
            transport.spin()
            if observe():
                return 2
            if correction and clock() - last_correction_report >= .25:
                report_correction('progress')
                last_correction_report = clock()
            if not accepted and clock() >= acceptance_deadline:
                raise TimeoutError('Acceptance unknown; do not retry')
        check_guards()
        if not accepted:
            raise RuntimeError('Terminal response without verified acceptance')
        if result_succeeded(kind, terminal['status'], terminal['result']):
            if kind == 'planning':
                validate_session_result(kind, goal, terminal)
            if correction:
                validate_session_result(kind, goal, terminal)
                transport.begin_correction_settle()
                report_correction('settling')
                settle_deadline = min(deadline, clock() + 1.5)
                while True:
                    check_guards()
                    if transport.correction_settled():
                        break
                    if clock() >= settle_deadline:
                        raise TimeoutError('Correction stationary arrival unconfirmed')
                    transport.spin()
                    # This UUID is already terminal. Only trailing feedback or
                    # status is admissible; a new result/error cannot replace it.
                    for row in transport.drain():
                        emit(**row)
                        if (row.get('goal_id') != transport.goal_id
                                or row['event'] not in ('status', 'feedback')):
                            raise RuntimeError('Unexpected action evidence while settling correction')
                report_correction('settled')
            report_correction('terminal')
            return 0
        emit(event='error', goal_id=transport.goal_id,
             reason='Action did not report successful terminal application result')
        return 2
    except Exception as error:
        failure = str(error)
        emit(event='error', goal_id=transport.goal_id, reason=failure)
        try:
            report_correction('failed')
        except Exception:
            pass  # Diagnostic serialization must never suppress cancellation.

    if transport.goal_id is None:
        return 2
    if terminal is None:
        grace_deadline = clock() + cancel_grace
        try:
            emit(event='cancel_requested', goal_id=transport.goal_id, reason=failure,
                 physical_stop_verified=False)
            transport.cancel()
        except Exception as error:
            emit(event='error', goal_id=transport.goal_id,
                 reason='Targeted cancel could not be sent: ' + str(error))
        while clock() < grace_deadline and terminal is None:
            try:
                transport.spin()
            except Exception as error:
                emit(event='error', goal_id=transport.goal_id,
                     reason='Terminal transport unavailable: ' + str(error))
                break
            try:
                if observe():
                    return 2
            except Exception as error:
                emit(event='error', goal_id=transport.goal_id,
                     reason='Terminal observation failed: ' + str(error))
    if terminal is None:
        emit(event='terminal_unknown', goal_id=transport.goal_id,
             reason='No terminal result within cancellation observation deadline',
             physical_stop_verified=False)
        return 3
    emit(event='interrupted_terminal', goal_id=transport.goal_id,
         status=terminal['status'], physical_stop_verified=False)
    return 2


SESSION_NAV_COMMANDS = frozenset(('get_map_name', 'check_state', 'map_set',
                                  'relocation_start', 'navigation_start'))

HOME_GOAL = {'task_name': 'cruzr/home', 'yaml_args': '{}'}
UNSUCCESSFUL_TERMINAL = 'Action did not report successful terminal application result'


def known_home_failure(terminal):
    if not isinstance(terminal, dict) or terminal.get('event') != 'result':
        return False
    result = terminal.get('result')
    state = result.get('state') if isinstance(result, dict) else None
    return (type(terminal.get('status')) is int and terminal['status'] == 6
            and isinstance(terminal.get('goal_id'), str) and bool(terminal['goal_id'])
            and isinstance(state, dict) and type(state.get('state')) is int
            and state['state'] == 7104050 and state.get('desc') == 'MoveToGoalFailed')


def recoverable_home_trace(kind, goal, rows, goal_id):
    """Recognize one accepted native failure, never timeout/cancel/uncertainty.

    Returning True only permits the supervisor to receive the original failure.
    It does not authorize or dispatch another action.
    """
    if kind != 'motion' or goal != HOME_GOAL or not isinstance(goal_id, str) or not goal_id:
        return False
    allowed = {'dispatched', 'accepted', 'result_pending', 'feedback', 'status', 'result', 'error'}
    if any(row.get('event') not in allowed or row.get('goal_id') != goal_id for row in rows):
        return False
    dispatched = [row for row in rows if row['event'] == 'dispatched']
    accepted = [row for row in rows if row['event'] == 'accepted']
    results = [row for row in rows if row['event'] == 'result']
    errors = [row for row in rows if row['event'] == 'error']
    if (len(dispatched) != 1 or dispatched[0].get('endpoint') != ENDPOINTS['motion']
            or len(accepted) != 1 or accepted[0].get('accepted') is not True
            or len(results) != 1 or not known_home_failure(results[0])
            or len(errors) != 1 or errors[0].get('reason') != UNSUCCESSFUL_TERMINAL):
        return False
    if not (rows.index(dispatched[0]) < rows.index(accepted[0]) < rows.index(results[0]) < rows.index(errors[0])):
        return False
    return (all(type(row.get('status')) is int and row['status'] in (1, 2, 6)
                for row in rows if row['event'] == 'status')
            and all(type(row.get('status')) is int and row['status'] in (0, 1, 2)
                    for row in rows if row['event'] == 'result_pending'))


def validate_session_request(kind, raw, seen):
    request = object_json(raw)
    required = {'request_id', 'goal', 'timeout'}
    if set(request) not in (required, required | {'correction'}, required | {'allow_home_retry'}):
        raise ValueError('Request requires request_id, goal, timeout and one optional reviewed policy')
    request_id = request['request_id']
    if (not isinstance(request_id, str)
            or re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', request_id) is None):
        raise ValueError('Invalid request_id')
    if isinstance(seen, RequestIds):
        seen.validate(request_id)
    else:
        # Keep the standalone validator's existing set-based API bounded.
        if request_id in seen:
            raise ValueError('Repeated request_id; no retry permitted')
        if len(seen) >= 256:
            raise ValueError('Session request limit reached')
    timeout = request['timeout']
    if (isinstance(timeout, bool) or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout) or timeout <= 0):
        raise ValueError('Request timeout must be finite and positive')
    goal = validate_goal(kind, json.dumps(request['goal'], allow_nan=False))
    if 'allow_home_retry' in request and (request['allow_home_retry'] is not True
                                         or kind != 'motion' or goal != HOME_GOAL):
        raise ValueError('allow_home_retry requires true and exact motion cruzr/home with yaml_args {}')
    if kind == 'navigation' and goal['command'] not in SESSION_NAV_COMMANDS:
        raise ValueError('Navigation command has no reviewed session result contract')
    if 'correction' in request:
        if kind != 'navigation' or goal['command'] != 'navigation_start':
            raise ValueError('Correction is limited to navigation_start')
        correction_module().validate_spec(request['correction'], goal=goal)
    return request_id, goal, timeout


def validate_session_result(kind, goal, terminal):
    """Application failures poison a session before another goal can be sent.

    Arrival pose, map identity and physical verification remain caller checks.
    navigation_start's historical auxiliary LOCATION_LOST is accepted only with
    its explicit success dmsg, as in scenario1_contract.validate_navigation_result.
    """
    if not terminal or not result_succeeded(kind, terminal.get('status'), terminal.get('result')):
        raise ValueError('Session request did not confirm successful terminal result')
    if kind == 'motion':
        return
    if kind == 'planning':
        validate_goal(kind, json.dumps(goal, allow_nan=False))
        # check_state can report idle FINISH after a completed navigation.
        # A new map refresh must itself confirm READY, never an old finish.
        if goal['command'] == 'set_map' and terminal['result']['state']['desc'] != 'READY':
            raise ValueError('Planning map refresh did not confirm READY')
        return  # Generic SUCCESS remains insufficient for either command.
    result = terminal['result']
    state = result.get('state')
    desc = state.get('desc') if isinstance(state, dict) else None
    if not isinstance(desc, str):
        raise ValueError('Malformed navigation application state')
    command = goal['command']
    dmsg = result.get('dmsg', '')
    if not isinstance(dmsg, str):
        raise ValueError('Malformed navigation application message')
    arrival = command == 'navigation_start' and dmsg.startswith('navigation_start SUCCEEDED')
    auxiliary_lost = desc == 'VSLAM_LOCATION_LOST' and arrival
    if re.search(r'ERROR|FAIL|ABORT|CANCEL|LOST|OBSTACLE', desc, re.I) and not auxiliary_lost:
        raise ValueError('Navigation application failure: ' + desc)
    if command == 'navigation_start' and not (arrival or desc in ('SUCCESS', 'SUCCEED')):
        raise ValueError('Navigation arrival was not confirmed')
    if command == 'get_map_name':
        value = object_json(result.get('result_json', ''))
        if not isinstance(value.get('map_name'), str):
            raise ValueError('Navigation map response is invalid')
    if command == 'check_state':
        states = re.findall(r'\bFSM_[A-Z_]+\b', dmsg)
        if len(states) != 1 or states[0] not in ('FSM_WAITNAVIGATE', 'FSM_WAITRELOCATE', 'FSM_WAITSETMAP'):
            raise ValueError('Navigation state is busy or unrecognized')
    if command == 'map_set' and desc not in ('VSLAM_LOAD_MAP_FINISHED', 'SUCCESS', 'SUCCEED'):
        raise ValueError('Map load was not confirmed')
    if command == 'relocation_start' and desc not in ('NAVIGATION_READY', 'SUCCESS', 'SUCCEED'):
        raise ValueError('Localization was not confirmed')


class SessionInput:
    """Bounded stdin reader; EOF is immediately visible during an active action."""
    def __init__(self, stream):
        self.requests = queue.Queue(maxsize=1)
        self.reason = None
        self.eof = False
        self.thread = threading.Thread(target=self.read, args=(stream,), daemon=True)
        self.thread.start()

    def read(self, stream):
        try:
            while True:
                line = stream.readline(1024 * 1024 + 1)
                if not line:
                    self.eof = True
                    self.reason = 'Request input pipe disconnected'
                    return
                if len(line) > 1024 * 1024 or not line.endswith('\n'):
                    raise ValueError('Oversized or incomplete session request')
                try:
                    self.requests.put_nowait(line)
                except queue.Full:
                    raise ValueError('Too many queued requests; session is sequential')
        except Exception as error:
            self.reason = 'Request input failed: ' + str(error)


def run_session(transport, kind, inbox, emit, interrupted=lambda: None,
                lease_file=None, clock=time.monotonic, run_one=run_action):
    """Sequential request loop; a reviewed HOME failure may be returned, never retried."""
    seen = RequestIds(legacy_limit=256)
    emit(event='session_ready', request_id=None, kind=kind)
    while True:
        request_id = None
        try:
            if interrupted():
                raise RuntimeError(interrupted())
            check_lease(lease_file, clock())
            if inbox.reason:
                if inbox.eof and inbox.requests.empty():
                    emit(event='session_closed', request_id=None, reason=inbox.reason)
                    return 0
                raise RuntimeError(inbox.reason)
            try:
                raw = inbox.requests.get(timeout=.05)
            except queue.Empty:
                transport.spin()
                for row in transport.drain():
                    # Retired UUID callbacks are filtered by the adapter.
                    raise RuntimeError(row.get('reason', 'Unexpected idle action evidence'))
                continue
            # Keep evidence correlated even if a syntactically valid ID belongs
            # to a malformed/duplicate request. Never dispatch such a request.
            candidate = object_json(raw).get('request_id')
            if isinstance(candidate, str) and re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', candidate):
                request_id = candidate
            request_id, goal, timeout = validate_session_request(kind, raw, seen)
            seen.add(request_id)
            request = object_json(raw)
            if 'correction' in request:
                transport.configure_correction(request['correction'])
            terminal = None
            trace = []

            def request_emit(**row):
                nonlocal terminal
                trace.append(row)
                if row['event'] == 'result':
                    terminal = row
                emit(request_id=request_id, **row)

            code = run_one(transport, kind, goal, timeout, request_emit,
                           interrupted=lambda: interrupted() or inbox.reason,
                           lease_file=lease_file, clock=clock)
            recoverable = (code == 2 and request.get('allow_home_retry') is True
                           and recoverable_home_trace(kind, goal, trace, transport.goal_id))
            if recoverable:
                if interrupted() or inbox.reason:
                    raise RuntimeError(interrupted() or inbox.reason)
                check_lease(lease_file, clock())
                goal_id = transport.goal_id
                transport.finish_recoverable_home_failure(terminal)
                # Recheck after retirement; a concurrent stop still poisons the session.
                if interrupted() or inbox.reason:
                    raise RuntimeError(interrupted() or inbox.reason)
                check_lease(lease_file, clock())
                emit(event='request_complete', request_id=request_id, returncode=2,
                     recoverable_home_failure=True, goal_id=goal_id)
                continue
            if code == 0:
                # Do not clear a goal before all successful-result checks pass.
                validate_session_result(kind, goal, terminal)
                if interrupted() or inbox.reason:
                    raise RuntimeError(interrupted() or inbox.reason)
                check_lease(lease_file, clock())
                transport.finish_successful_request()
            emit(event='request_complete', request_id=request_id, returncode=code)
            if code:
                return code
        except Exception as error:
            emit(event='error', request_id=request_id, goal_id=transport.goal_id, reason=str(error))
            if request_id is not None:
                emit(event='request_complete', request_id=request_id, returncode=2)
            return 2


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=tuple(ENDPOINTS), required=True)
    parser.add_argument('--goal-json')
    parser.add_argument('--timeout', type=float)
    parser.add_argument('--lease-file', type=Path)
    parser.add_argument('--serve', action='store_true', help='Sequential persistent JSONL request session')
    args = parser.parse_args(argv)
    if args.serve:
        if args.goal_json is not None or args.timeout is not None or args.lease_file is None:
            parser.error('--serve requires --lease-file and takes goals/timeouts only through stdin')
    else:
        if args.timeout is None or not math.isfinite(args.timeout) or args.timeout <= 0:
            parser.error('--timeout must be finite and positive')
        if args.goal_json is None:
            parser.error('--goal-json is required without --serve')
        try:
            goal = validate_goal(args.kind, args.goal_json)
        except ValueError as error:
            parser.error(str(error))
    stop = {'reason': None}
    output_failed = False

    def emit(**row):
        nonlocal output_failed
        if output_failed:
            return
        if args.serve:
            row.setdefault('request_id', None)
        try:
            print(json.dumps(dict(time_ns=time.time_ns(), **row), allow_nan=False), flush=True)
        except (BrokenPipeError, OSError):
            output_failed = True
            stop['reason'] = 'Evidence output pipe disconnected'

    def on_signal(number, frame):
        stop['reason'] = 'Signal ' + str(number)

    transport = None
    previous = {}
    try:
        check_lease(args.lease_file, time.monotonic())
        transport = RosaTransport(args.kind)
        if args.serve:
            transport.validate_session_api()
        emit(event='native_api', fingerprints=transport.api_fingerprints,
             reviewed_source='20260921T112801Z_FRONT_NATIVE_INTEGRATION_AUDIT')
        # Install after rosa.init(), which may install its own signal handlers.
        for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            previous[number] = signal.signal(number, on_signal)
        if args.serve:
            return run_session(transport, args.kind, SessionInput(sys.stdin), emit,
                               interrupted=lambda: stop['reason'], lease_file=args.lease_file)
        return run_action(transport, args.kind, goal, args.timeout, emit,
                          interrupted=lambda: stop['reason'], lease_file=args.lease_file)
    except Exception as error:
        emit(event='error', goal_id=transport.goal_id if transport else None, reason=str(error))
        return 2
    finally:
        if transport is not None:
            transport.close()
        for number, handler in previous.items():
            signal.signal(number, handler)


if __name__ == '__main__':
    sys.exit(main())
