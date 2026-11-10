#!/usr/bin/env python3
"""Arm supervisor for a PICO v4 wrist trial; direct arm dispatch is blocked.

The operator must be at the physical stop. Cancellation is only a request and
neither this monitor nor receipt of a cancellation proves a physical stop.
Loss of this process or its transport cannot stop an already accepted goal.
"""
import json
import math
import os
import re
import select
import sys
import time

from head_from_pico_readonly import (BODY, DECLARED_LIMITS, HAND_SUFFIXES,
    check_actuators, check_battery, check_body, check_hand, check_timing,
    joint_state, source_stamp_ns)
from metamove_head_probe import check_stop_cadence, check_stop_sample

# Independent reference: the successful earlier head task ended near -0.43.
BODY = dict(BODY, head_pitch_joint=-0.43)
ARM_AXIS = 'R_wrist_roll_joint'
ARM_STEP = 0.01
ARM_CORRIDOR_TOLERANCE = 0.003
ARM_SPEED_LIMIT = 0.03
# Installed SPS transmission file, hash pinned by the local preflight. These
# are nominal configuration limits, not proof of the values in servo memory.
SPS_ARM_LIMITS = {
    'shoulder_pitch': (-2.83, 2.83), 'shoulder_roll': (-1.86, .08),
    'shoulder_yaw': (-2.92, 2.92), 'elbow_roll': (-2.6, .02),
    'elbow_yaw': (-2.88, 2.88), 'wrist_roll': (-1.98, 1.98),
}
SPS_LIMITS = {
    **{side + '_' + joint + '_joint': limits
       for side in ('L', 'R') for joint, limits in SPS_ARM_LIMITS.items()},
    'L_wrist_pitch_joint': (-1.57, 1.6), 'R_wrist_pitch_joint': (-1.6, 1.57),
    'head_yaw_joint': (-1.65, 1.65), 'head_pitch_joint': (-.65, .51),
    'waist_yaw_joint': (-2.8, 2.8), 'lifter_pitch_1_joint': (-1.5, 1.5),
    'lifter_pitch_2_joint': (-2.5, 2.5), 'lifter_pitch_3_joint': (-1.5, 1.5),
}


def check_sps_limits(values, initial=None):
    if set(SPS_LIMITS) != set(BODY):
        raise ValueError('incomplete_sps_limit_table')
    for name, (lo, hi) in SPS_LIMITS.items():
        position = values[name][0]
        if not lo <= position <= hi:
            raise ValueError('outside_nominal_sps_limit:' + name)
        if initial is not None and name != ARM_AXIS:
            # Early warning halfway to either nominal boundary. Detection
            # latency and braking distance are unknown; this is not a guarantee.
            lower_warning = (lo + initial[name]) / 2
            upper_warning = (hi + initial[name]) / 2
            if not lower_warning <= position <= upper_warning:
                raise ValueError('approaching_nominal_sps_limit:' + name)


def check_body(message):
    values = joint_state(message, BODY)
    check_sps_limits(values)
    if any(abs(values[n][0]-target) > .02 for n, target in BODY.items()):
        raise ValueError('not_pico_v4_head_lower_reference')
    if any(not lo <= values[n][0] <= hi for n, (lo, hi) in DECLARED_LIMITS.items()):
        raise ValueError('outside_declared_pico_v4_limits')
    if any(abs(values[n][1]) > .001 for n in BODY):
        raise ValueError('body_not_stationary')
    return {n: values[n][0] for n in BODY}

LOCKED_DRIFT_RAD = .002
LOCKED_SPEED_RAD_S = .01
HAND_DRIFT_RAD = .01  # Conservative observer threshold, not a hardware limit.
# Observation thresholds only. Historical head trial peak was 0.339292 rad/s;
# these thresholds are not manufacturer limits or a certified stopping bound.
HEAD_PITCH_SPEED_RAD_S = .5
HEAD_YAW_SPEED_RAD_S = .1
SAMPLE_AGE_S = .5
STOP_AGE_S = 6.0
SUPERVISOR_HEARTBEAT_TIMEOUT_S = .6
TASK = 'move_components_json'
ACTIVE_STATUSES = frozenset((1, 2, 3))
TASK_SHA = 'bfcfc097dfefb3e81fcb2acc913d7db55545b3ea3b853b345b9ba1836c01b797'
PICO_SHA = '01a5ca8acba16bbe136a3bdbcb4a593667d672f8ee9613b98631699fc429b582'


def validate_preflight(preflight, elapsed, *, dry_run=False):
    """Validate session handoff; does not prove continuous exclusive control."""
    required = {'schema', 'task_sha256', 'pico_sha256', 'work_mode',
                'operator_confirmed', 'controller_status_writers_checked',
                'age_at_handoff_s', 'session_id', 'mode'}
    if not isinstance(preflight, dict) or set(preflight) != required:
        raise ValueError('preflight_format_invalid')
    if (preflight['schema'] != 'cruzr_head_pico_preflight_v1' or
            preflight['task_sha256'] != TASK_SHA or
            preflight['pico_sha256'] != PICO_SHA or
            preflight['work_mode'] != 'joystick' or
            preflight['mode'] != ('check' if dry_run else 'run') or
            type(preflight['operator_confirmed']) is not bool or
            (not dry_run and preflight['operator_confirmed'] is not True) or
            preflight['controller_status_writers_checked'] is not True or
            not isinstance(preflight['session_id'], str) or
            not re.fullmatch('[0-9a-f]{32}', preflight['session_id'])):
        raise ValueError('preflight_unverified')
    age = preflight['age_at_handoff_s']
    if (type(age) not in (int, float) or not math.isfinite(age) or age < 0 or
            type(elapsed) not in (int, float) or not math.isfinite(elapsed) or
            elapsed < 0 or age + elapsed > 30):
        raise ValueError('preflight_stale_or_invalid')


def motion_envelope(message, initial):
    """Validate all axes against the fixed reference, never generate targets."""
    values = joint_state(message, BODY)
    check_sps_limits(values, initial)
    for name, (lo, hi) in DECLARED_LIMITS.items():
        if not lo <= values[name][0] <= hi:
            raise ValueError('outside_declared_pico_v4_limits:' + name)
    for name in BODY:
        q, speed = values[name]
        if name == ARM_AXIS:
            if not initial[name]-ARM_CORRIDOR_TOLERANCE <= q <= initial[name]+ARM_STEP+ARM_CORRIDOR_TOLERANCE:
                raise ValueError('arm_axis_outside_trial_corridor:' + name)
            if abs(speed) > ARM_SPEED_LIMIT:
                raise ValueError('arm_axis_speed_observation_threshold:' + name)
        else:
            if abs(q-initial[name]) > LOCKED_DRIFT_RAD:
                raise ValueError('non_trial_axis_drift:' + name)
            if abs(speed) > LOCKED_SPEED_RAD_S:
                raise ValueError('non_trial_axis_moving:' + name)
    return values


def foreign_active(statuses, own_uuid=None):
    """Returns foreign active IDs; absence is NOT proof of exclusive control."""
    result = []
    for status in statuses:
        value = int(status.status)
        goal_id = bytes(status.goal_info.goal_id.uuid)
        if len(goal_id) != 16 or value not in (1, 2, 3, 4, 5, 6):
            raise ValueError('action_status_unknown_or_invalid')
        if value in ACTIVE_STATUSES and goal_id != own_uuid:
            result.append(goal_id.hex())
    return result


def own_status(statuses, own_uuid):
    for status in statuses or ():
        if bytes(status.goal_info.goal_id.uuid) == own_uuid:
            return int(status.status)
    return None


def standstill(values, *, target=False):
    if any(abs(v[1]) > .01 for v in values.values()):
        return False
    if target:
        return False  # There is no physical goal or endpoint in this check.
    return True


def physical_release_gate():
    # The safety review remains open. Never infer a release from a user flag,
    # a successful dry run, a candidate corridor or a ROS action response.
    raise RuntimeError('physical_dispatch_blocked_unqualified_arm_stop_and_trajectory')


def require_verified_stream(provenance, role, session_id):
    """Require this narrow path's bootstrap evidence, not physical approval.

    This prevents accidental use outside the validated bootstrap in trusted
    processes; it is not protection against someone controlling Python/SSH.
    """
    if (not isinstance(provenance, tuple) or len(provenance) != 4
            or provenance[0] != role or provenance[1] != session_id
            or not isinstance(session_id, str) or not re.fullmatch('[0-9a-f]{32}', session_id)
            or any(not isinstance(x, str) or not re.fullmatch('[0-9a-f]{64}', x)
                   for x in provenance[2:])):
        physical_release_gate()


class SupervisorHeartbeat:
    """Motion-local watchdog for one supervisor; a timeout is not a stop."""
    def __init__(self, session_id, guard_id):
        self.session_id, self.guard_id = session_id, guard_id
        self.sequence, self.last = -1, None

    def accept(self, command, now):
        if (not isinstance(command, dict) or set(command) != {'event', 'session_id', 'guard_id', 'sequence'}
                or command['event'] != 'supervisor_heartbeat'
                or command['session_id'] != self.session_id or command['guard_id'] != self.guard_id
                or type(command['sequence']) is not int or command['sequence'] != self.sequence + 1
                or type(now) not in (int, float) or not math.isfinite(now)
                or (self.last is not None and now < self.last)):
            raise ValueError('invalid_supervisor_heartbeat')
        self.sequence, self.last = command['sequence'], now

    def require_fresh(self, now):
        if (self.last is None or type(now) not in (int, float) or not math.isfinite(now)
                or not 0 <= now - self.last <= SUPERVISOR_HEARTBEAT_TIMEOUT_S):
            raise ValueError('supervisor_heartbeat_expired')


def motion_result_ok(response):
    """Use the native box client's terminal-success contract for ArmTask."""
    state = getattr(getattr(response, 'result', None), 'state', None)
    status = getattr(response, 'status', None)
    code = getattr(state, 'state', None)
    return (type(status) is int and status == 4 and type(code) is int and
            code == 1101001 and getattr(state, 'desc', None) == 'SUCCEED')


def build_trial_args(q):
    names = ('R_shoulder_pitch_joint', 'R_shoulder_roll_joint',
             'R_shoulder_yaw_joint', 'R_elbow_roll_joint', 'R_elbow_yaw_joint',
             'R_wrist_pitch_joint', 'R_wrist_roll_joint')
    if not isinstance(q, dict) or any(n not in q or type(q[n]) not in (float, int)
                                      or not math.isfinite(q[n]) for n in names):
        raise ValueError('invalid_arm_reference')
    target = [float(q[n]) for n in names]
    target[-1] += ARM_STEP
    lo, hi = DECLARED_LIMITS[ARM_AXIS]
    hw_lo, hw_hi = SPS_LIMITS[ARM_AXIS]
    if not max(lo, hw_lo) <= target[-1] <= min(hi, hw_hi):
        raise ValueError('trial_endpoint_outside_declared_limits')
    return {'component_names': ['right_arm'], 'goals': [target],
            'mode': 0, 'durations': [4.0]}


def main(preflight, *, dry_run, monitor_only=False, guard_can_cancel=False, verified_provenance=None):
    if type(dry_run) is not bool:
        raise ValueError('dry_run_must_be_explicit_boolean')
    if type(monitor_only) is not bool or (monitor_only and not dry_run):
        raise ValueError('continuous_monitor_requires_dry_run')
    if type(guard_can_cancel) is not bool or (guard_can_cancel and not monitor_only):
        raise ValueError('guard_cancel_requires_continuous_monitor')
    if guard_can_cancel:
        # A checked bootstrap may supervise/cancel one UUID, never dispatch.
        require_verified_stream(verified_provenance, 'guard', preflight.get('session_id'))
    if not dry_run:
        physical_release_gate()
    local_started = time.monotonic()
    validate_preflight(preflight, 0, dry_run=dry_run)
    import rclpy
    from rclpy.action import ActionClient
    from rclpy.qos import (QoSProfile, ReliabilityPolicy, DurabilityPolicy,
                           qos_profile_sensor_data)
    from rosidl_runtime_py.utilities import get_message
    from rosidl_runtime_py.convert import message_to_ordereddict
    from unique_identifier_msgs.msg import UUID
    from action_msgs.msg import GoalStatusArray
    from action_msgs.srv import CancelGoal
    from mc_task_msgs.action import ArmTask
    import uuid

    topics = {
        'body': '/mc/whole_joint_states', 'actuators': '/mc/actuator_state',
        'left': '/mc/left_hand/joint_states', 'right': '/mc/right_hand/joint_states',
        'estop': '/emb/estop_key_state', 'servo_stop': '/emb/servo_estop_key_state',
        'charger': '/emb/chrg_input_status', 'battery': '/emb/battery_state',
    }
    rclpy.init()
    node = rclpy.create_node('pico_v4_supervised_arm_check', enable_rosout=False,
                             start_parameter_services=False)
    samples, stamps, stop_times = {}, {}, {'estop': [], 'servo_stop': []}
    state = {'statuses': None, 'status_sequence': 0, 'own': None, 'transport_failed': False,
             'hand_initial': None}
    subs = []
    goal = None
    goal_future = None
    result_future = None
    dispatch_attempted = False
    cancelled = False
    fault = None
    fault_at = None
    last_report = 0.0
    result_reported = False
    uuid_cancel_requested = False
    uuid_cancel_future = None
    uuid_bytes = uuid.uuid4().bytes
    goal_uuid = UUID(uuid=list(uuid_bytes))

    # Never let a slow/disconnected observer block the ROS spinning loop. If
    # reporting fails, alert/cancel locally and continue to monitor. The remote
    # wrapper must separately warn the operator on SSH loss.
    output_fd = sys.stdout.fileno()
    os.set_blocking(output_fd, False)

    def emit(event, **fields):
        data = (json.dumps({'event': event, 'monotonic': time.monotonic(),
                            'goal_uuid': uuid_bytes.hex(), **fields},
                           allow_nan=False, separators=(',', ':')) + '\n').encode()
        try:
            if os.write(output_fd, data) != len(data):
                state['transport_failed'] = True
        except (BlockingIOError, BrokenPipeError, OSError):
            state['transport_failed'] = True

    def receive(key, msg):
        now = time.monotonic()
        samples[key] = (now, message_to_ordereddict(msg))
        if key in stop_times:
            stop_times[key].append(now)
            stop_times[key] = stop_times[key][-4:]

    def receive_status(msg):
        state['statuses'] = list(msg.status_list)
        state['status_sequence'] += 1

    def checked(initial=None):
        nonlocal last_report
        now = time.monotonic()
        if state['transport_failed']:
            raise ValueError('operator_output_transport_lost')
        if set(samples) != set(topics):
            raise ValueError('telemetry_missing')
        for key in ('body', 'actuators', 'left', 'right'):
            received, data = samples[key]
            check_timing(received, now, SAMPLE_AGE_S)
            stamp = source_stamp_ns(data)
            age = (node.get_clock().now().nanoseconds - stamp) / 1e9
            if not 0 <= age <= SAMPLE_AGE_S:
                raise ValueError('source_stale_or_future:' + key)
            if key in stamps and stamp < stamps[key]:
                raise ValueError('source_stamp_regressed:' + key)
            stamps[key] = stamp
        for key in ('estop', 'servo_stop'):
            check_stop_sample(samples[key][0], samples[key][1].get('data'), now)
            if not check_stop_cadence(stop_times[key]):
                raise ValueError('insufficient_estop_heartbeat:' + key)
        for key in ('charger', 'battery'):
            check_timing(samples[key][0], now, STOP_AGE_S)
        if samples['charger'][1].get('data') != 0:
            raise ValueError('charger_connected_or_unknown')
        check_battery(samples['battery'][1])
        check_actuators(samples['actuators'][1])
        check_hand(samples['left'][1], 'left')
        check_hand(samples['right'][1], 'right')
        hands = {}
        for side in ('left', 'right'):
            names = [side + '_' + suffix for suffix in HAND_SUFFIXES]
            values = joint_state(samples[side][1], names, exact=True)
            hands.update({name: values[name][0] for name in names})
        if state['hand_initial'] is None:
            state['hand_initial'] = hands
        elif any(abs(hands[name]-state['hand_initial'][name]) > HAND_DRIFT_RAD
                 for name in hands):
            raise ValueError('hand_axis_drift')
        if node.count_publishers('/mc/sdk/robot_command') != 0:
            raise ValueError('sdk_writer_present')
        if state['statuses'] is None:
            raise ValueError('action_status_not_observed')
        foreign = foreign_active(state['statuses'], state['own'])
        if foreign:
            raise ValueError('foreign_action_active:' + ','.join(foreign))
        if initial is None:
            q = check_body(samples['body'][1])
            values = joint_state(samples['body'][1], BODY)
        else:
            values = motion_envelope(samples['body'][1], initial)
            q = {k: values[k][0] for k in BODY}
        if now-last_report >= .1:
            emit('telemetry', position=q, velocity={k: values[k][1] for k in BODY},
                 estop=samples['estop'][1].get('data'),
                 servo_stop=samples['servo_stop'][1].get('data'))
            last_report = now
        return q, values

    def observed_standstill():
        """Observe velocities even with E-stop asserted; not an authorization."""
        try:
            now = time.monotonic()
            for key in ('body', 'left', 'right'):
                received, data = samples[key]
                check_timing(received, now, SAMPLE_AGE_S)
                stamp = source_stamp_ns(data)
                age = (node.get_clock().now().nanoseconds-stamp) / 1e9
                if not 0 <= age <= SAMPLE_AGE_S:
                    return False
            check_hand(samples['left'][1], 'left')
            check_hand(samples['right'][1], 'right')
            return standstill(joint_state(samples['body'][1], BODY))
        except (ValueError, RuntimeError, KeyError, TypeError):
            return False

    def alert(reason):
        nonlocal fault, fault_at
        if fault is None:
            fault, fault_at = reason, time.monotonic()
            emit('OPERATOR_ALERT', reason=reason,
                 instruction='Stop operation; use physical emergency stop if unsafe. No retry or HOME.',
                 physical_stop_confirmed=False)

    def request_cancel():
        nonlocal cancelled
        if goal is not None and goal.accepted and not cancelled:
            cancelled = True
            try:
                future = goal.cancel_goal_async()
                emit('cancel_requested', physical_stop_confirmed=False)
                return future
            except Exception as exc:
                emit('cancel_request_failed', reason=str(exc),
                     physical_stop_confirmed=False)
        return None

    try:
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            graph = dict(node.get_topic_names_and_types())
            if all(t in graph and len(graph[t]) == 1 for t in topics.values()):
                break
            rclpy.spin_once(node, timeout_sec=.05)
        else:
            raise RuntimeError('required_topics_not_discovered')
        for key, topic in topics.items():
            subs.append(node.create_subscription(get_message(graph[topic][0]), topic,
                lambda msg, key=key: receive(key, msg), qos_profile_sensor_data))
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE,
                         durability=DurabilityPolicy.TRANSIENT_LOCAL)
        subs.append(node.create_subscription(GoalStatusArray,
            '/mc/manipulation/action/_action/status', receive_status, qos))
        deadline = time.monotonic() + 22
        since = None
        initial = None
        last_reason = 'telemetry_not_ready'
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.02)
            try:
                q, _ = checked()
                if initial is None:
                    initial = q
                if any(abs(q[n]-initial[n]) > LOCKED_DRIFT_RAD for n in BODY):
                    raise ValueError('initial_posture_drift')
                since = since or time.monotonic()
                if time.monotonic()-since >= 1:
                    break
            except (ValueError, RuntimeError, KeyError, TypeError) as exc:
                initial, since, last_reason = None, None, str(exc)
                state['hand_initial'] = None
        else:
            emit('preflight_failed', reason=last_reason, movement_commands=0)
            return 1
        client = ActionClient(node, ArmTask, '/mc/manipulation/action')
        uuid_cancel_client = node.create_client(CancelGoal,
            '/mc/manipulation/action/_action/cancel_goal')
        deadline = time.monotonic() + 2
        while (time.monotonic() < deadline and
               (not client.server_is_ready() or
                (guard_can_cancel and not uuid_cancel_client.service_is_ready()))):
            rclpy.spin_once(node, timeout_sec=.02)
            checked()
        if not client.server_is_ready():
            emit('preflight_failed', reason='action_server_unavailable', movement_commands=0)
            return 1
        if guard_can_cancel and not uuid_cancel_client.service_is_ready():
            emit('preflight_failed', reason='cancel_service_unavailable', movement_commands=0)
            return 1
        q, _ = checked()
        if any(abs(q[n]-initial[n]) > LOCKED_DRIFT_RAD for n in BODY):
            raise ValueError('posture_changed_before_dispatch')
        validate_preflight(preflight, time.monotonic()-local_started, dry_run=dry_run)
        # A challenge/response bounds the transport delay WITHOUT comparing
        # unsynchronised host clocks. Keep spinning ROS and checking all
        # telemetry while the wrapper replies with its current inventory age.
        challenge = uuid.uuid4().hex
        started_handshake = time.monotonic()
        emit('pre_dispatch_ready', challenge=challenge,
             session_id=preflight['session_id'])
        if state['transport_failed']:
            return 1
        input_fd = sys.stdin.fileno()
        os.set_blocking(input_fd, False)
        buffer = bytearray()
        acknowledgement = None
        while time.monotonic()-started_handshake <= 3:
            rclpy.spin_once(node, timeout_sec=.01)
            checked()
            if select.select([input_fd], [], [], 0)[0]:
                try:
                    block = os.read(input_fd, 4096)
                except BlockingIOError:
                    continue
                if not block:
                    raise ValueError('pre_dispatch_handoff_closed')
                buffer.extend(block)
                if len(buffer) > 4096:
                    raise ValueError('pre_dispatch_handoff_oversize')
                if b'\n' in buffer:
                    line, extra = bytes(buffer).split(b'\n', 1)
                    if extra:
                        raise ValueError('pre_dispatch_handoff_extra_data')
                    acknowledgement = json.loads(line)
                    break
        if not isinstance(acknowledgement, dict) or set(acknowledgement) != {
                'schema', 'session_id', 'challenge', 'inventory_age_s'}:
            raise ValueError('pre_dispatch_handoff_missing_or_invalid')
        age = acknowledgement.get('inventory_age_s')
        if (acknowledgement['schema'] != 'cruzr_head_pico_handoff_v1' or
                acknowledgement['session_id'] != preflight['session_id'] or
                acknowledgement['challenge'] != challenge or
                type(age) not in (int, float) or not math.isfinite(age) or age < 0 or
                age + 3.0 > 30):
            raise ValueError('pre_dispatch_handoff_stale_or_invalid')
        q, _ = checked()
        if any(abs(q[n]-initial[n]) > LOCKED_DRIFT_RAD for n in BODY):
            raise ValueError('posture_changed_before_dispatch')
        if time.monotonic()-started_handshake > 3:
            raise ValueError('pre_dispatch_handoff_expired')
        if monitor_only:
            # This passive mode never dispatches or cancels. It publishes only
            # checked observations and learns one ROSA UUID before that client
            # sends; any other active action remains foreign. It must not be
            # mistaken for physical release or evidence of braking.
            initial = q
            emit('ARM_GUARD_READY', session_id=preflight['session_id'],
                 movement_commands=0, physical_control_qualified=False)
            buffer = bytearray()
            guard_cancel_future = None
            guard_cancel_requested = False
            guard_cancel_count = 0
            guard_first_cancel_sequence = None
            guard_first_cancel_at = None
            guard_terminal_reported = False
            guard_fault = None
            guard_fault_at = None
            guard_still_since = None
            guard_last_reminder = 0.0
            supervisor = SupervisorHeartbeat(preflight['session_id'], uuid_bytes.hex())
            while True:
                try:
                    rclpy.spin_once(node, timeout_sec=.01)
                    if guard_fault is None:
                        if guard_can_cancel and not uuid_cancel_client.service_is_ready():
                            raise ValueError('cancel_service_unavailable')
                        if guard_can_cancel and state['own'] is not None:
                            supervisor.require_fresh(time.monotonic())
                        checked(initial)
                except Exception as exc:
                    if not guard_can_cancel or state['own'] is None:
                        raise
                    if guard_fault is None:
                        guard_fault = type(exc).__name__ + ':' + str(exc)
                        guard_fault_at = time.monotonic()
                        emit('OPERATOR_ALERT', reason=guard_fault, no_retry=True,
                             physical_stop_confirmed=False)
                    # Keep spinning and monitoring even after a guard failure.
                    # No fresh telemetry is emitted, so the lease expires.
                    time.sleep(.01)
                if guard_fault is not None and not guard_cancel_requested:
                    try:
                        if uuid_cancel_client.service_is_ready():
                            request = CancelGoal.Request()
                            request.goal_info.goal_id.uuid = list(state['own'])
                            # One exact handshaken UUID, never a wildcard. Set
                            # attempted before call_async: delivery can be
                            # unknown if the call raises after sending.
                            guard_cancel_requested = True
                            guard_cancel_count = 1
                            guard_first_cancel_sequence = state['status_sequence']
                            guard_first_cancel_at = time.monotonic()
                            guard_cancel_future = uuid_cancel_client.call_async(request)
                            emit('guard_auto_cancel_requested', reason=guard_fault,
                                 physical_stop_confirmed=False)
                    except Exception as exc:
                        emit('guard_auto_cancel_delivery_unknown', reason=str(exc),
                             physical_stop_confirmed=False)
                if guard_cancel_future is not None and guard_cancel_future.done():
                    try:
                        response = guard_cancel_future.result()
                        emit('guard_cancel_response', return_code=int(response.return_code),
                             physical_stop_confirmed=False)
                    except Exception as exc:
                        emit('guard_cancel_response_unknown', reason=str(exc),
                             physical_stop_confirmed=False)
                    guard_cancel_future = None
                guard_status = own_status(state['statuses'], state['own']) if state['own'] is not None else None
                if (guard_cancel_count == 1 and state['status_sequence'] > guard_first_cancel_sequence
                        and guard_status in ACTIVE_STATUSES
                        and (guard_cancel_future is None or time.monotonic()-guard_first_cancel_at >= .5)):
                    try:
                        if uuid_cancel_client.service_is_ready():
                            request = CancelGoal.Request()
                            request.goal_info.goal_id.uuid = list(state['own'])
                            # One bounded retry of cancellation, never movement,
                            # only after a newer status shows this UUID active.
                            guard_cancel_count = 2
                            guard_cancel_future = uuid_cancel_client.call_async(request)
                            emit('guard_auto_cancel_requested', reason='own_uuid_active_after_cancel',
                                 attempt=2, physical_stop_confirmed=False)
                    except Exception as exc:
                        emit('guard_auto_cancel_delivery_unknown', reason=str(exc),
                             physical_stop_confirmed=False)
                if guard_cancel_requested and guard_status in (4, 5, 6) and not guard_terminal_reported:
                    emit('guard_terminal_observed', status=guard_status, physical_stop_confirmed=False)
                    guard_terminal_reported = True
                if guard_fault is not None:
                    # Terminal status and observed stillness are required to
                    # end a fault monitor; neither certifies braking distance.
                    if guard_status in (4, 5, 6) and observed_standstill():
                        guard_still_since = guard_still_since or time.monotonic()
                        if time.monotonic()-guard_still_since >= 1:
                            emit('guard_fault_terminal_and_still', reason=guard_fault,
                                 physical_stop_confirmed=False, no_retry=True)
                            return 1
                    else:
                        guard_still_since = None
                    if time.monotonic()-guard_last_reminder >= 5:
                        emit('UNRESOLVED_MONITORING', reason=guard_fault, no_retry=True,
                             physical_stop_confirmed=False)
                        guard_last_reminder = time.monotonic()
                    continue
                try:
                    if not select.select([input_fd], [], [], 0)[0]:
                        continue
                    try:
                        block = os.read(input_fd, 4096)
                    except BlockingIOError:
                        continue
                    if not block:
                        raise ValueError('guard_input_closed')
                    buffer.extend(block)
                    if len(buffer) > 4096:
                        raise ValueError('guard_input_oversize')
                    while b'\n' in buffer:
                        line, _, remainder = bytes(buffer).partition(b'\n')
                        buffer = bytearray(remainder)
                        command = json.loads(line)
                        if not isinstance(command, dict):
                            raise ValueError('invalid_guard_command')
                        if command.get('event') == 'supervisor_heartbeat':
                            if not guard_can_cancel:
                                raise ValueError('heartbeat_requires_cancel_mode')
                            supervisor.accept(command, time.monotonic())
                            continue
                        if command == {'event': 'stop_guard', 'session_id': preflight['session_id']}:
                            # After a UUID is handed off, never leave a live
                            # goal unmonitored merely because the host asks.
                            # Terminal status plus sampled rest are observations,
                            # not evidence of braking distance or future rest.
                            if (guard_can_cancel and state['own'] is not None and
                                    (own_status(state['statuses'], state['own']) not in (4, 5, 6)
                                     or not observed_standstill())):
                                raise ValueError('guard_stop_without_terminal_and_still')
                            emit('ARM_GUARD_STOPPED', movement_commands=0,
                                 physical_stop_confirmed=False)
                            return 0
                        if command.get('event') == 'cancel_goal_uuid':
                            if (not guard_can_cancel or guard_cancel_requested or state['own'] is None
                                    or set(command) != {'event','session_id','goal_id','challenge'}
                                    or command['session_id'] != preflight['session_id']
                                    or not isinstance(command['goal_id'], str)
                                    or not re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', command['goal_id'])
                                    or uuid.UUID(command['goal_id']).bytes != state['own']
                                    or not isinstance(command['challenge'], str)
                                    or not re.fullmatch('[0-9a-f]{32}', command['challenge'])
                                    or not uuid_cancel_client.service_is_ready()):
                                raise ValueError('invalid_guard_cancel_request')
                            request = CancelGoal.Request()
                            request.goal_info.goal_id.uuid = list(state['own'])
                            # Exactly the already handshaken UUID; never empty or
                            # wildcard. An unknown goal and an ACK do not prove rest.
                            guard_cancel_requested = True
                            guard_cancel_count = 1
                            guard_first_cancel_sequence = state['status_sequence']
                            guard_first_cancel_at = time.monotonic()
                            guard_cancel_future = uuid_cancel_client.call_async(request)
                            emit('guard_cancel_requested', session_id=command['session_id'],
                                 goal_id=command['goal_id'], challenge=command['challenge'],
                                 physical_stop_confirmed=False)
                            continue
                        if (set(command) != {'event', 'session_id', 'guard_id', 'goal_id', 'challenge'}
                                or command['event'] != 'prepare_goal_uuid'
                                or command['session_id'] != preflight['session_id']
                                or command['guard_id'] != uuid_bytes.hex()
                                or not isinstance(command['goal_id'], str)
                                or not re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', command['goal_id'])
                                or not isinstance(command['challenge'], str)
                                or not re.fullmatch('[0-9a-f]{32}', command['challenge'])
                                or state['own'] is not None):
                            raise ValueError('invalid_guard_uuid_handshake')
                        # The absence of other actions is rechecked before granting
                        # exactly one UUID; no catch-all exemption is created.
                        checked(initial)
                        if guard_can_cancel and not uuid_cancel_client.service_is_ready():
                            raise ValueError('cancel_service_unavailable')
                        if guard_can_cancel:
                            supervisor.require_fresh(time.monotonic())
                        state['own'] = uuid.UUID(command['goal_id']).bytes
                        emit('goal_uuid_ready', session_id=command['session_id'],
                             guard_id=command['guard_id'], goal_id=command['goal_id'],
                             challenge=command['challenge'])
                except Exception as exc:
                    if not guard_can_cancel or state['own'] is None:
                        raise
                    if guard_fault is None:
                        guard_fault = type(exc).__name__ + ':' + str(exc)
                        guard_fault_at = time.monotonic()
                        emit('OPERATOR_ALERT', reason=guard_fault, no_retry=True,
                             physical_stop_confirmed=False)
                    # Input/parse failure after the UUID handoff can coincide
                    # with a send. Keep ROS alive and cancel that exact UUID.
                    continue
        if dry_run:
            emit('PICO_ARM_SUPERVISED_DRY_RUN_PASSED', movement_commands=0,
                 physical_control_qualified=False)
            return 0 if not state['transport_failed'] else 1
        initial = q
        args = build_trial_args(q)
        trial_target = args['goals'][0][-1]
        request = ArmTask.Goal()
        request.task_name, request.yaml_args = TASK, json.dumps(args, allow_nan=False)
        state['own'] = uuid_bytes
        emit('dispatch', task=TASK, no_retry=True)
        if state['transport_failed']:
            return 1  # No request was sent.
        if time.monotonic()-started_handshake > 3:
            emit('preflight_failed', reason='pre_dispatch_handoff_expired',
                 movement_commands=0)
            return 1  # No request was sent.
        # Once send is attempted, even an exception cannot prove that the
        # server did not receive the goal.
        dispatched = time.monotonic()
        dispatch_attempted = True
        try:
            goal_future = client.send_goal_async(request, goal_uuid=goal_uuid)
        except Exception as exc:
            # Humble can send the request before it returns the Future. Keep
            # monitoring: lack of a Future is NOT evidence of non-delivery.
            alert('dispatch_delivery_unknown_no_future:' + str(exc))
        acceptance_deadline = dispatched + 5
        end_deadline = dispatched + 15
        cancel_future = None
        stopped_since = None
        last_reminder = 0.0
        while True:
            try:
                rclpy.spin_once(node, timeout_sec=.01)
            except Exception as exc:
                # An executor/callback error does not establish that an
                # already sent goal stopped; keep trying to observe, with no
                # resend and no automatic HOME.
                alert('executor_spin_failure:' + str(exc))
                request_cancel()
                time.sleep(.05)
                continue
            now = time.monotonic()
            try:
                _, values = checked(initial)
            except (ValueError, RuntimeError, KeyError, TypeError) as exc:
                values = None
                alert('telemetry_or_envelope:' + str(exc))
            if goal is None and goal_future is not None and goal_future.done():
                try:
                    goal = goal_future.result()
                except Exception as exc:
                    alert('goal_acceptance_exception:' + str(exc))
                if goal is not None:
                    emit('acceptance', accepted=bool(goal.accepted))
                    if not goal.accepted:
                        return 1
                    try:
                        result_future = goal.get_result_async()
                    except Exception as exc:
                        alert('result_request_failed:' + str(exc))
            if goal is None and now >= acceptance_deadline:
                alert('acceptance_unknown_no_handle')
            if goal is not None and goal.accepted and fault:
                cancel_future = request_cancel() or cancel_future
            # If send_goal_async raised after sending, a status with the exact
            # preassigned UUID can reveal the accepted goal even without a
            # Future/handle. Request cancellation for that UUID only; this is
            # not proof of stopping. Never cancel any other client's goal.
            status = own_status(state['statuses'], uuid_bytes)
            if (fault and goal is None and status in ACTIVE_STATUSES and
                    not uuid_cancel_requested and uuid_cancel_client.service_is_ready()):
                uuid_cancel_requested = True
                try:
                    request_cancel_uuid = CancelGoal.Request()
                    request_cancel_uuid.goal_info.goal_id.uuid = list(uuid_bytes)
                    uuid_cancel_future = uuid_cancel_client.call_async(request_cancel_uuid)
                    emit('cancel_uuid_requested', physical_stop_confirmed=False)
                except Exception as exc:
                    emit('cancel_uuid_request_failed', reason=str(exc),
                         physical_stop_confirmed=False)
            if uuid_cancel_future is not None and uuid_cancel_future.done():
                try:
                    response = uuid_cancel_future.result()
                    emit('cancel_uuid_response', return_code=int(response.return_code),
                         physical_stop_confirmed=False)
                except Exception as exc:
                    emit('cancel_uuid_response_failed', reason=str(exc),
                         physical_stop_confirmed=False)
                uuid_cancel_future = None
            if cancel_future is not None and cancel_future.done():
                try:
                    response = cancel_future.result()
                    emit('cancel_response', return_code=int(response.return_code),
                         physical_stop_confirmed=False)
                except Exception as exc:
                    emit('cancel_response_failed', reason=str(exc),
                         physical_stop_confirmed=False)
                cancel_future = None
            if now >= end_deadline and not fault:
                alert('action_deadline_exceeded')
            if result_future is not None and result_future.done():
                try:
                    response = result_future.result()
                    succeeded = motion_result_ok(response)
                    if not result_reported:
                        emit('action_result', status=int(response.status),
                             desc=str(response.result.state.desc),
                             state_code=int(response.result.state.state), physical_stop_confirmed=False)
                        result_reported = True
                except Exception as exc:
                    alert('action_result_exception:' + str(exc))
                    succeeded = False
                if not succeeded:
                    alert('action_not_successful')
                stable = (observed_standstill() if fault else
                          values is not None and standstill(values) and abs(values[ARM_AXIS][0] - trial_target) <= ARM_CORRIDOR_TOLERANCE)
                if stable:
                    stopped_since = stopped_since or now
                    if now-stopped_since >= 1:
                        if fault:
                            emit('fault_and_standstill_observed', reason=fault,
                                 no_retry=True, physical_stop_certified=False)
                            return 1
                        emit('ARM_SUCCEEDED_AND_STATIONARY', no_retry=True,
                             physical_stop_certified=False)
                        return 0
                else:
                    stopped_since = None
            elif fault and status in (4, 5, 6):
                # A terminal status is observational evidence, not proof that
                # cancellation caused a physical stop. Require fresh stationary
                # joint observations for at least one second before closing.
                if observed_standstill():
                    stopped_since = stopped_since or now
                    if now-stopped_since >= 1:
                        emit('terminal_status_and_standstill_observed',
                             status=status, reason=fault, no_retry=True,
                             physical_stop_certified=False)
                        return 1
                else:
                    stopped_since = None
            if fault and now-last_reminder >= 5:
                emit('UNRESOLVED_MONITORING', reason=fault, no_retry=True,
                     physical_stop_confirmed=False,
                     instruction='Operator intervention required; do not send HOME or retry.')
                last_reminder = now
    except BaseException as exc:
        if dispatch_attempted:
            try:
                alert('unexpected_exception:' + str(exc))
                request_cancel()
                emit('UNRESOLVED', reason='unexpected_exception', no_retry=True,
                     physical_stop_confirmed=False)
                # Last-resort observation after a post-dispatch failure. A
                # single interrupt requests cancellation but does not prove
                # the goal ended. A second interrupt or an unrecoverable ROS
                # failure may still terminate this process; the wrapper must
                # then report uncertainty and the operator must intervene.
                fallback_since = None
                fallback_cancel_uuid = False
                fallback_reminder = 0.0
                while True:
                    try:
                        rclpy.spin_once(node, timeout_sec=.02)
                        if goal is None and goal_future is not None and goal_future.done():
                            try:
                                goal = goal_future.result()
                                if goal is not None and not goal.accepted:
                                    emit('acceptance', accepted=False)
                                    return 1
                            except Exception as error:
                                emit('acceptance_failed', reason=str(error),
                                     physical_stop_confirmed=False)
                        request_cancel()
                        status = own_status(state['statuses'], uuid_bytes)
                        if (goal is None and status in ACTIVE_STATUSES and
                                not fallback_cancel_uuid and uuid_cancel_client.service_is_ready()):
                            fallback_cancel_uuid = True
                            cancel_request = CancelGoal.Request()
                            cancel_request.goal_info.goal_id.uuid = list(uuid_bytes)
                            uuid_cancel_client.call_async(cancel_request)
                            emit('cancel_uuid_requested', physical_stop_confirmed=False)
                        if status in (4, 5, 6) and observed_standstill():
                            fallback_since = fallback_since or time.monotonic()
                            if time.monotonic()-fallback_since >= 1:
                                emit('terminal_status_and_standstill_observed',
                                     status=status, reason='unexpected_exception',
                                     no_retry=True, physical_stop_certified=False)
                                return 1
                        else:
                            fallback_since = None
                        if time.monotonic()-fallback_reminder >= 5:
                            emit('UNRESOLVED_MONITORING', reason='unexpected_exception',
                                 no_retry=True, physical_stop_confirmed=False)
                            fallback_reminder = time.monotonic()
                    except Exception as error:
                        emit('fallback_observation_failed', reason=str(error),
                             physical_stop_confirmed=False)
                        time.sleep(.05)
            except BaseException as error:
                emit('UNRESOLVED_MONITOR_STOPPED', reason=str(error), no_retry=True,
                     physical_stop_confirmed=False,
                     instruction='Operator intervention required; do not retry or send HOME.')
        else:
            emit('preflight_failed', reason=str(exc), movement_commands=0)
        raise

    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    raise SystemExit('Direct dispatch disabled; use the reviewed session wrapper.')
