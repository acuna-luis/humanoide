#!/usr/bin/env python3
"""Persistent read-only ROSA telemetry and ListControllers worker.

One node keeps telemetry readers alive. Every request collects new safety and
actuator/pose samples; action status is explicitly retained DDS state. There are
no publishers, action clients or motion services in this process.
"""
import argparse
from collections import deque
import copy
import hashlib
import json
import math
from pathlib import Path
import queue
import re
import sys
import threading
import time


TOPICS = {
    'estop': ('/emb/estop_key_state', 'std_msgs/msg/UInt8'),
    'servo': ('/emb/servo_estop_key_state', 'std_msgs/msg/UInt8'),
    'charger': ('/emb/chrg_input_status', 'std_msgs/msg/UInt8'),
    'battery': ('/emb/battery_state', 'emb_task_msgs/msg/BatteryState'),
    'actuator': ('/mc/actuator_state', 'mc_state_msgs/msg/ActuatorState'),
    'status': ('/mc/manipulation/action/_action/status', 'action_msgs/msg/GoalStatusArray'),
    'pose': ('/nav/robot_pose', 'geometry_msgs/msg/PoseStamped'),
}
CONTROLLER_SERVICE = '/mc/controller_manager/list_controllers'
CONTROLLER_TYPE = 'rosa_control_msgs/srv/ListControllers'
SAFETY = ('estop', 'servo', 'charger', 'battery')
MAX_AGE_NS = 2_000_000_000


def object_json(value):
    def pairs(items):
        result = {}
        for name, item in items:
            if name in result:
                raise ValueError('Duplicate JSON field')
            result[name] = item
        return result
    if isinstance(value, str):
        value = json.loads(value, object_pairs_hook=pairs)
    if not isinstance(value, dict):
        raise ValueError('Expected JSON object')
    json.dumps(value, allow_nan=False)
    return value


def validate_request(value):
    value = object_json(value)
    if not {'request_id', 'command'} <= set(value) or set(value) - {
            'request_id', 'command', 'require_home', 'timeout'}:
        raise ValueError('Invalid health request fields')
    if not isinstance(value['request_id'], str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}', value['request_id']):
        raise ValueError('Invalid request_id')
    if value['command'] not in ('health', 'pose'):
        raise ValueError('Unsupported read-only request')
    require_home = value.get('require_home', False)
    if type(require_home) is not bool or value['command'] == 'pose' and require_home:
        raise ValueError('Invalid require_home')
    timeout = value.get('timeout', 12)
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 12:
        raise ValueError('Request timeout must be in (0, 12] seconds')
    return dict(request_id=value['request_id'], command=value['command'],
                require_home=require_home, timeout=float(timeout))


def source_stamp_ns(message):
    try:
        stamp = message['header']['stamp']
        sec, nanosec = stamp['sec'], stamp['nanosec']
        if type(sec) is not int or type(nanosec) is not int or sec < 0 or not 0 <= nanosec < 10**9:
            raise ValueError('Invalid source timestamp')
        result = sec*10**9+nanosec
        if result <= 0:
            raise ValueError('Missing source timestamp')
        return result
    except (KeyError, TypeError) as exc:
        raise ValueError('Missing source timestamp') from exc


class Acquisition:
    """A bounded request-local collection; retained telemetry cannot satisfy it."""
    def __init__(self, request, requested_ns, requested_monotonic_ns):
        self.request = validate_request(request)
        self.requested_ns = requested_ns
        self.requested_monotonic_ns = requested_monotonic_ns
        self.safety = {}
        self.samples = deque(maxlen=2)
        self.receipts = {}
        self.last_stamp = None
        self.duplicates_ignored = 0

    def add(self, key, message, received_ns, received_monotonic_ns):
        if received_monotonic_ns <= self.requested_monotonic_ns:
            return
        message = object_json(message)
        if self.request['command'] == 'health' and key in SAFETY:
            self.safety[key] = copy.deepcopy(message)
            self.receipts[key] = received_ns
        wanted = 'actuator' if self.request['command'] == 'health' else 'pose'
        if key != wanted:
            return
        stamp = source_stamp_ns(message)
        if stamp < self.requested_ns and self.last_stamp is None:
            return  # DDS data queued before this request cannot satisfy it.
        if not 0 <= received_ns-stamp <= MAX_AGE_NS:
            raise ValueError('Stale or future '+key+' source timestamp')
        if self.last_stamp is not None and stamp <= self.last_stamp:
            # A repeated actuator packet is not a second measurement. Ignore
            # only an exact duplicate, without renewing its receipt or freshness.
            # JSON comparison preserves types (unlike Python's True == 1).
            current = json.dumps(message, sort_keys=True, separators=(',', ':'), allow_nan=False)
            previous = json.dumps(self.samples[-1], sort_keys=True, separators=(',', ':'), allow_nan=False)
            if key == 'actuator' and stamp == self.last_stamp and current == previous:
                self.duplicates_ignored += 1
                return
            reason = ('Conflicting actuator samples with identical source timestamp'
                      if key == 'actuator' and stamp == self.last_stamp
                      else 'Nonadvancing '+key+' source timestamp')
            diagnostic = dict(source_ns=stamp, previous_source_ns=self.last_stamp,
                              delta_ns=stamp-self.last_stamp, received_ns=received_ns,
                              same_payload=current == previous,
                              previous_sha256=hashlib.sha256(previous.encode()).hexdigest(),
                              current_sha256=hashlib.sha256(current.encode()).hexdigest())
            raise ValueError(reason+'; '+json.dumps(diagnostic, sort_keys=True))
        self.last_stamp = stamp
        self.samples.append(copy.deepcopy(message))
        self.receipts[wanted] = received_ns

    def complete(self, now_ns, controller=None, status=None):
        if len(self.samples) != 2:
            return None
        if any(not 0 <= now_ns-source_stamp_ns(row) <= MAX_AGE_NS for row in self.samples):
            raise ValueError('Collected source samples became stale')
        result = dict(event=self.request['command']+'_result', request_id=self.request['request_id'],
                      requested_ns=self.requested_ns, completed_ns=now_ns)
        if self.request['command'] == 'pose':
            return dict(result, poses=copy.deepcopy(list(self.samples)))
        if set(self.safety) != set(SAFETY) or controller is None or status is None:
            return None
        if any(not 0 <= now_ns-self.receipts[key] <= MAX_AGE_NS for key in SAFETY):
            raise ValueError('Collected safety samples became stale')
        return dict(result, require_home=self.request['require_home'], controller=object_json(controller),
                    status=object_json(status), status_retained=True,
                    safety=copy.deepcopy(self.safety), actuator=copy.deepcopy(list(self.samples)),
                    actuator_duplicates_ignored=self.duplicates_ignored)


def session_active(session, now):
    session = Path(session)
    if (session/'stop').exists():
        return False
    for filename in ('control-lease.json', 'lease.json'):
        deadline = object_json((session/filename).read_text()).get('deadline')
        if type(deadline) not in (int, float) or not math.isfinite(deadline):
            raise ValueError('Malformed '+filename)
        if now >= deadline:
            return False
    return True


class NativeReader:
    """Uses APIs inspected from the installed ROSA Python modules, 28-09-2026."""
    def __init__(self):
        import rosa
        from rosa.base._QoS import SensorDataQoS, ActionStatusQoS
        from rosa.utils import resolve_message_type
        self.rosa = rosa
        self.acquisition = None
        self.status = None
        self.fatal = None
        self.controller = None
        self.response_ready = threading.Event()
        rosa.init()
        try:
            self.node = rosa.Node('scenario1_health_readonly')
            self.readers = {}
            for key, (topic, type_name) in TOPICS.items():
                qos = ActionStatusQoS() if key == 'status' else SensorDataQoS()
                if key == 'status':
                    qos.reliable()
                    qos.transientLocal()
                    qos.keepLast(1)
                else:
                    qos.bestEffort()
                    qos.durabilityVolatile()
                self.readers[key] = self.node.create_reader(resolve_message_type(type_name), topic,
                                                            self.callback(key), qos=qos)
            self.client = self.node.create_client(resolve_message_type(CONTROLLER_TYPE), CONTROLLER_SERVICE)
        except BaseException:
            rosa.shutdown()
            raise

    def callback(self, key):
        # ROSA explicitly selects JSON delivery from this single str annotation.
        def receive(raw: str):
            try:
                message = object_json(raw)
                if key == 'status':
                    self.status = message
                if self.acquisition is not None:
                    self.acquisition.add(key, message, time.time_ns(), time.monotonic_ns())
            except Exception as error:
                self.fatal = error
        return receive

    def spin(self):
        if self.fatal is not None:
            raise self.fatal
        if not self.rosa.ok():
            raise RuntimeError('ROSA stopped')
        self.rosa.spin_once(self.node, 20)
        if self.fatal is not None:
            raise self.fatal

    def acquire(self, request, check_guard):
        self.acquisition = Acquisition(request, time.time_ns(), time.monotonic_ns())
        self.controller = None
        self.response_ready.clear()
        future = None
        publisher_counts = {}
        deadline = time.monotonic()+request['timeout']
        try:
            while time.monotonic() < deadline:
                check_guard()
                self.spin()
                if request['command'] == 'health':
                    count = self.client.getServiceCount()
                    if count > 1:
                        raise RuntimeError('Ambiguous ListControllers service')
                    if future is None and count == 1:
                        # ROSA requires wait_for_service to set its readiness
                        # state; getServiceCount alone does not authorize call_async.
                        # Explicit zero avoids the API's default infinite wait.
                        if not self.client.wait_service(0):
                            continue
                        check_guard()
                        if time.monotonic() >= deadline:
                            raise TimeoutError('ListControllers readiness deadline exceeded')
                        future = self.client.call_async('{}', lambda *unused: self.response_ready.set())
                        if future is None:
                            raise RuntimeError('ListControllers request failed')
                    if self.response_ready.is_set() and self.controller is None:
                        self.controller = object_json(self.client.get_result(future, json_format=True))
                    required = (*SAFETY, 'actuator', 'status')
                else:
                    required = ('pose',)
                publisher_counts = {key: self.readers[key].getWriterCount() for key in required}
                # Navigation exposes two vendor publishers on this unit. The
                # previous ROS2 pose reader required fresh advancing samples,
                # not a unique publisher. Keep health endpoint uniqueness.
                acceptable = (publisher_counts['pose'] >= 1 if request['command'] == 'pose'
                              else all(count == 1 for count in publisher_counts.values()))
                if not acceptable:
                    continue
                result = self.acquisition.complete(time.time_ns(), self.controller, self.status)
                if result is not None:
                    check_guard()
                    if request['command'] == 'pose':
                        result['publisher_count'] = publisher_counts['pose']
                    return result
            diagnostic = dict(publishers=publisher_counts, fresh_samples=len(self.acquisition.samples),
                              safety_received=sorted(self.acquisition.safety),
                              actuator_duplicates_ignored=self.acquisition.duplicates_ignored,
                              controller_received=self.controller is not None,
                              status_received=self.status is not None)
            raise TimeoutError('Fresh read-only '+request['command']+' collection timed out; '+
                               json.dumps(diagnostic, sort_keys=True))
        finally:
            self.acquisition = None

    def close(self):
        self.rosa.shutdown()


def emit(**event):
    print(json.dumps(event, allow_nan=False), flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True, type=Path)
    args = parser.parse_args(argv)
    commands = queue.Queue(maxsize=16)
    ended = threading.Event()
    errors = []
    seen = set()
    native = None
    current = None

    def receive():
        try:
            for line in sys.stdin:
                if len(line) > 4096:
                    raise ValueError('Oversized health request')
                commands.put_nowait(validate_request(line))
        except Exception as error:
            errors.append(error)
        finally:
            ended.set()

    def guard():
        if errors:
            raise errors[0]
        if ended.is_set():
            raise RuntimeError('Supervisor input closed')
        if not session_active(args.session, time.monotonic()):
            raise RuntimeError('Health worker lease expired or stop requested')

    try:
        if not session_active(args.session, time.monotonic()):
            return 0
        threading.Thread(target=receive, daemon=True).start()
        native = NativeReader()
        guard()
        emit(event='session_ready', request_id=None)
        while True:
            guard()
            native.spin()
            try:
                current = commands.get_nowait()
            except queue.Empty:
                continue
            if current['request_id'] in seen or len(seen) >= 4096:
                raise ValueError('Repeated request_id or session request limit')
            seen.add(current['request_id'])
            emit(**native.acquire(current, guard))
            emit(event='request_complete', request_id=current['request_id'], returncode=0)
            current = None
    except (Exception, KeyboardInterrupt) as error:
        request_id = current['request_id'] if current is not None else None
        emit(event='error', request_id=request_id, reason=type(error).__name__+': '+str(error))
        if current is not None:
            emit(event='request_complete', request_id=request_id, returncode=78)
        return 78
    finally:
        if native is not None:
            native.close()


if __name__ == '__main__':
    raise SystemExit(main())
