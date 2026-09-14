"""One bounded SDK bridge prefix; imports ROS only in main. No policy loop."""
import json
import math
import signal
import time


def check_tracking(values, expected, names, velocity_limit=.05):
    for n, q in zip(names, expected, strict=True):
        actual, velocity = values[n]
        if not all(math.isfinite(v) for v in (actual, velocity, q)):
            raise RuntimeError('Nonfinite tracking state')
        if abs(actual-q) > .005:
            raise RuntimeError('Tracking error: '+n)
        if abs(velocity) > velocity_limit:
            raise RuntimeError('Measured speed: '+n)


def check_tick(now, scheduled, previous):
    if not math.isfinite(now) or now < scheduled or now-scheduled > .03:
        raise RuntimeError('Dispatch deadline missed; no catch-up')
    if previous is not None and not 0 < now-previous <= .04:
        raise RuntimeError('Dispatch gap; no catch-up')


def check_wheels(values, reference):
    """Bound encoder drift as well as speed; tolerate observed sub-count jitter."""
    for name, (position, velocity) in values.items():
        if not all(math.isfinite(v) for v in (position, velocity, reference[name])):
            raise RuntimeError('Nonfinite wheel state')
        if abs(velocity) > .01 or abs(position-reference[name]) > .002:
            raise RuntimeError('Base encoder drift/speed: '+name+': '+str((position-reference[name], velocity)))


def check_handoff_reply(response):
    if response is None or response.success is not True:
        raise RuntimeError('VLA controller handoff failed: '+str(getattr(response, 'message', 'no response')))


def check_sdk_state(sdk, names, now, since):
    if (sdk.get('error') or sdk.get('received', -1e9) < since
            or now-sdk.get('received', -1e9) > .1
            or set(sdk.get('values', {})) != set(names)):
        raise RuntimeError('Missing/stale/invalid active SDK 20-joint feedback')
    return sdk['values']


def main(payload):
    import rclpy
    from rclpy.qos import qos_profile_sensor_data
    from rosidl_runtime_py.utilities import get_message
    from rosidl_runtime_py.convert import message_to_ordereddict
    from stage_monitor import named_values, check_stop_sample, stop_cadence_ready, check_segment_corridor
    from sdk_backend import RosSdkRobotCommandBackend
    from std_srvs.srv import Trigger
    plan = payload['plan']; names = plan['joint_order']; arms = plan['arm_names']
    aliases = payload['actuator_names']; state = {}; health = {}; stops = {}; histories = {}; sdk = {}
    rclpy.init(); node = rclpy.create_node('entry410_recorded_point_trial')
    backend = None; interrupted = False; subscriptions = []; wheel_reference = {}; sdk_required_since = None
    def emit(**row):
        print(json.dumps(row, allow_nan=False), flush=True)
    def interrupt(signum, frame):
        nonlocal interrupted
        interrupted = True
    signal.signal(signal.SIGTERM, interrupt); signal.signal(signal.SIGINT, interrupt)
    def stamped_age(m):
        age = (node.get_clock().now().nanoseconds-m.header.stamp.sec*10**9-m.header.stamp.nanosec)/1e9
        if not math.isfinite(age) or not 0 <= age <= .1:
            raise ValueError('Stale telemetry source')
    def joints(m):
        try:
            stamped_age(m)
            vals = named_values(message_to_ordereddict(m), names)
            wheel_names = ['driving_wheel_left_joint', 'driving_wheel_right_joint']
            wheel_values = named_values(message_to_ordereddict(m), wheel_names)
            if not wheel_reference:
                wheel_reference.update({n: v[0] for n, v in wheel_values.items()})
            check_wheels(wheel_values, wheel_reference)
            state.update(received=time.monotonic(), values=vals, error=None)
        except Exception as exc:
            state.update(error=str(exc))
    def actuators(m):
        try:
            stamped_age(m); seen = set()
            for item in m.act_item:
                n = aliases.get(str(item.id))
                if n is None:
                    continue
                if n in seen or item.error_code or item.status & 8 or item.status & 7 != 7:
                    raise ValueError('Actuator disabled/fault/duplicate')
                if not math.isfinite(item.position) or not math.isfinite(item.velocity):
                    raise ValueError('Nonfinite actuator')
                seen.add(n)
            if seen != set(names):
                raise ValueError('Missing actuator')
            health.update(received=time.monotonic(), error=None)
        except Exception as exc:
            health.update(error=str(exc))
    def sdk_state(m):
        try:
            stamped_age(m)
            if set(m.joint_states.name) != set(names) or len(m.joint_states.name) != len(names):
                raise ValueError('SDK feedback must contain exactly 20 reviewed joints, no wheels')
            values = named_values(message_to_ordereddict(m.joint_states), names)
            if not all(math.isfinite(x) for pair in values.values() for x in pair):
                raise ValueError('Nonfinite SDK feedback')
            sdk.update(received=time.monotonic(), values=values, error=None)
        except Exception as exc:
            sdk.update(error=str(exc))
    def scalar(topic, m):
        now = time.monotonic(); stops[topic] = (now, int(m.data))
        histories.setdefault(topic, []).append(now)
    topics = ['/emb/estop_key_state', '/emb/servo_estop_key_state', '/emb/chrg_input_status']
    def safe():
        now = time.monotonic()
        if interrupted:
            raise RuntimeError('Interrupted')
        for label, value in (('joint_state', state), ('actuator_health', health)):
            if value.get('error') or now-value.get('received', -1e9) > .1:
                raise RuntimeError('Missing/stale/invalid '+label+': '+str(value.get('error')))
        for t in topics:
            if t not in stops:
                raise RuntimeError('Missing scalar: '+t)
            try:
                check_stop_sample(*stops[t], now)
            except RuntimeError as exc:
                raise RuntimeError(t+': '+str(exc)) from exc
        if node.count_publishers('/mc/sdk/robot_command') > (1 if backend else 0):
            raise RuntimeError('Another SDK publisher appeared')
        if sdk_required_since is not None:
            sdk_values = check_sdk_state(sdk, names, now, sdk_required_since)
            if any(abs(sdk_values[n][0]-state['values'][n][0]) > .005 for n in names):
                raise RuntimeError('SDK and whole joint feedback disagree')
        return state['values']
    try:
        deadline = time.monotonic()+8
        needed = topics+['/mc/whole_joint_states', '/mc/actuator_state', '/mc/sdk/robot_state']
        while time.monotonic() < deadline:
            graph = dict(node.get_topic_names_and_types())
            if all(t in graph and len(graph[t]) == 1 for t in needed):
                break
            rclpy.spin_once(node, timeout_sec=.02)
        else:
            raise RuntimeError('Missing telemetry graph')
        for topic, callback in [('/mc/whole_joint_states', joints), ('/mc/actuator_state', actuators)]:
            subscriptions.append(node.create_subscription(get_message(graph[topic][0]), topic, callback, qos_profile_sensor_data))
        subscriptions.append(node.create_subscription(get_message(graph['/mc/sdk/robot_state'][0]),
            '/mc/sdk/robot_state', sdk_state, qos_profile_sensor_data))
        switch = node.create_client(Trigger, '/mc/motion_sdk/switch_to_vla')
        if not switch.wait_for_service(timeout_sec=2):
            raise RuntimeError('Official VLA controller handoff service unavailable')
        for topic in topics:
            subscriptions.append(node.create_subscription(get_message(graph[topic][0]), topic,
                lambda m, t=topic: scalar(t, m), qos_profile_sensor_data))
        deadline = time.monotonic()+14; stable = None; last_reason = None
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.005)
            try:
                values = safe()
                check_tracking(values, plan['start'], names, .01)
                differences = [(abs(values[n][0]-q), n) for n, q in zip(names, plan['start'])]
                if max(differences)[0] > .002:
                    raise RuntimeError('Start changed: '+str(max(differences)))
                if not all(stop_cadence_ready(histories.get(t, [])) for t in topics[:2]):
                    raise RuntimeError('Waiting for stop cadence')
                stable = time.monotonic() if stable is None else stable
                if time.monotonic()-stable >= 1:
                    break
            except RuntimeError as exc:
                stable = None
                if str(exc) != last_reason:
                    last_reason = str(exc)
                    emit(kind='admission_wait', reason=last_reason)
        else:
            raise RuntimeError('Fresh stable reviewed ENTRY unavailable; no publisher created; last reason: '+str(last_reason))
        if node.count_publishers('/mc/sdk/robot_command') != 0 or node.count_subscribers('/mc/sdk/robot_command') < 1:
            raise RuntimeError('SDK not exclusive/available')
        if payload.get('observe_only') is True:
            emit(status='ENTRY_POINT_ADMISSION_OBSERVED_NO_PUBLISHER', measured=safe(), publishers_created=0,
                 controller_handoff_pending=True, service_calls=0)
            return
        # A subscription to robot_command is not proof of an active controller.
        # This installed service switches only the 20 upper-body axes; no HOME.
        emit(kind='controller_handoff_requested', service='/mc/motion_sdk/switch_to_vla')
        safe(); future = switch.call_async(Trigger.Request()); deadline = time.monotonic()+3
        while not future.done() and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.005)
            check_tracking(safe(), plan['start'], names, .01)
        if not future.done():
            raise RuntimeError('Controller handoff outcome uncertain; inspect controller state, no retry')
        check_handoff_reply(future.result())
        switched_at = time.monotonic()
        emit(kind='controller_handoff_acknowledged', message=future.result().message)
        deadline = time.monotonic()+2; stable = None
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.005)
            values = safe(); check_tracking(values, plan['start'], names, .01)
            if max(abs(values[n][0]-q) for n, q in zip(names, plan['start'])) > .002:
                raise RuntimeError('Posture changed during controller handoff; no publisher created')
            try:
                check_sdk_state(sdk, names, time.monotonic(), switched_at)
            except RuntimeError:
                stable = None
                continue
            stable = time.monotonic() if stable is None else stable
            if time.monotonic()-stable >= .5:
                break
        else:
            raise RuntimeError('Controller did not produce stable fresh SDK feedback; no publisher created')
        sdk_required_since = switched_at
        safe()
        backend = RosSdkRobotCommandBackend(node)
        # Establish DDS discovery while sending nothing.
        end = time.monotonic()+.3
        while time.monotonic() < end:
            rclpy.spin_once(node, timeout_sec=.005); safe()
        origin = time.monotonic(); previous = None; expected = list(plan['start'])
        stage = dict(joint_order=names, start=plan['start'], end=plan['target'])
        for point in plan['trajectory']:
            scheduled = origin+point['elapsed_seconds']
            while time.monotonic() < scheduled:
                rclpy.spin_once(node, timeout_sec=min(.002, max(0., scheduled-time.monotonic())))
                safe()
            now = time.monotonic(); check_tick(now, scheduled, previous)
            values = safe(); check_tracking(values, expected, names)
            check_segment_corridor(stage, values, .005, .005)
            arm_positions = dict(zip(arms, point['positions']))
            arm_velocities = dict(zip(arms, point['velocities']))
            # Explicitly retain the six other axes claimed by this controller.
            frame = dict(joint_cmd=[dict(name=n, control_mode=2, position=arm_positions.get(n, q), velocity=arm_velocities.get(n, 0.),
                                         effort=0., v1=0., v2=0., v3=0.)
                for n, q in zip(names, plan['start'], strict=True)])
            backend.publish(frame); previous = now
            arm_positions = dict(zip(arms, point['positions']))
            expected = [arm_positions.get(n, q) for n, q in zip(names, plan['start'])]
            emit(kind='frame', index=point['index'], elapsed=now-origin,
                 expected=expected, measured=values)
        # Final setpoint is retained by Motion; no new commands, no next chunk.
        deadline = time.monotonic()+3; stable = None
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.005)
            values = safe(); check_tracking(values, plan['target'], names)
            check_segment_corridor(stage, values, .005, .005)
            if all(abs(v[1]) <= .01 for v in values.values()):
                stable = time.monotonic() if stable is None else stable
                if time.monotonic()-stable >= 1:
                    emit(status='ONE_POINT_PREFIX_SUCCEEDED_AND_SETTLED', measured=values,
                         source_chunk_id=plan['source_chunk_id'], fraction=plan['bridge_fraction'],
                         controller_left_active='vla_sdk_controller', automatic_switch_back=False)
                    return
            else:
                stable = None
        raise RuntimeError('Endpoint did not settle')
    except BaseException as exc:
        emit(status='FAILED_NO_RETRY', error=str(exc), operator_action='E-stop if motion is unexpected; inspect before any further command')
        raise
    finally:
        if backend is not None:
            backend.stop()
        node.destroy_node(); rclpy.shutdown()
