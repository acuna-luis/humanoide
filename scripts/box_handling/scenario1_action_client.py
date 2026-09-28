#!/usr/bin/env python3
"""One bounded native ROSA action with JSONL evidence and targeted cancellation.

Run inside a discovered Motion container after sourcing /opt/walker/setup.bash.
This transport does not check physical readiness. Its caller must do that before
dispatch and verify measured motion after a terminal response. Cancellation and
terminal action state are never certificates of physical stopping.

Native API reference: archived rosa/action_client.py from the 2026-09-21 front
SPS audit. The installed SDK is not modified. Its goal callback loses the real
acceptance flag, and its cancel helper swaps the stored UUID; this adapter reads
the response directly and copies the UUID into its own cancel request.
"""

import argparse
import ast
import hashlib
import inspect
import json
import math
from pathlib import Path
import queue
import signal
import sys
import textwrap
import time


ENDPOINTS = {'motion': '/mc/manipulation/action',
             'navigation': '/vnav/task/command'}
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
    # Navigation command semantics and measured arrival belong to the caller.
    return True


def native_client_class(base, to_string):
    """Adapt the observed native API, without treating a local handle as accepted."""
    class ObservedClient(base):
        def configure_observer(self, emit):
            self.observer = emit
            self.observed_goal_id = None
            self.accepted = False
            self.terminal = False
            self.result_pending = False
            self.result_requested_at = float('-inf')
            self.last_status = None
            self.cancel_future = None

        def create_goal_request(self, goal, options=None):
            request, goal_id = super().create_goal_request(goal, options)
            self.observed_goal_id = goal_id
            return request, goal_id

        def response_error(self, where, error):
            self.observer('error', goal_id=self.observed_goal_id,
                          reason=where + ': ' + str(error))

        def handle_goal_response_async(self, request, *unused):
            try:
                goal_id = to_string(request.goal_id.uuid)
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
        else:
            from unav_task_msgs.action import Task as Action
        self.rosa = rosa
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

    def close(self):
        self.rosa.shutdown()


def run_action(transport, kind, goal, timeout, emit, interrupted=lambda: None,
               lease_file=None, clock=time.monotonic, cancel_grace=8.0):
    """Transport state machine. A late success after interruption stays failure."""
    deadline = clock() + timeout
    accepted = False
    terminal = None
    failure = None

    def check_guards():
        reason = interrupted()
        if reason:
            raise RuntimeError(reason)
        check_lease(lease_file, clock())
        if clock() >= deadline:
            raise TimeoutError('Action deadline exceeded')

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
        discovery_deadline = min(deadline, clock() + 5.0)
        while not transport.ready():
            check_guards()
            if clock() >= discovery_deadline:
                raise TimeoutError('Action server unavailable')
            transport.spin()
        check_guards()
        goal_id = transport.send(goal)
        emit(event='dispatched', goal_id=goal_id, endpoint=ENDPOINTS[kind])
        acceptance_deadline = min(deadline, clock() + 5.0)
        while terminal is None:
            check_guards()
            transport.spin()
            if observe():
                return 2
            if not accepted and clock() >= acceptance_deadline:
                raise TimeoutError('Acceptance unknown; do not retry')
        check_guards()
        if not accepted:
            raise RuntimeError('Terminal response without verified acceptance')
        if result_succeeded(kind, terminal['status'], terminal['result']):
            return 0
        emit(event='error', goal_id=transport.goal_id,
             reason='Action did not report successful terminal application result')
        return 2
    except Exception as error:
        failure = str(error)
        emit(event='error', goal_id=transport.goal_id, reason=failure)

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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=tuple(ENDPOINTS), required=True)
    parser.add_argument('--goal-json', required=True)
    parser.add_argument('--timeout', type=float, required=True)
    parser.add_argument('--lease-file', type=Path)
    args = parser.parse_args(argv)
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error('--timeout must be finite and positive')
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
        emit(event='native_api', fingerprints=transport.api_fingerprints,
             reviewed_source='20260921T112801Z_FRONT_NATIVE_INTEGRATION_AUDIT')
        # Install after rosa.init(), which may install its own signal handlers.
        for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            previous[number] = signal.signal(number, on_signal)
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
