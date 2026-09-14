"""ROS single-stage transport, sent on stdin by run_entry410_stage.py only.

Cancellation is a request, not a certified stop. No installation or reload.
"""
import base64
import hashlib
import json
import math
from pathlib import Path
import time


def named_values(message, required):
    """Joint coordinates by declared names; actuator encoder signs are not inferred."""
    names = message['name']
    if (len(names) != len(set(names)) or len(names) != len(message['position'])
            or len(names) != len(message['velocity'])):
        raise ValueError('Duplicate names or inconsistent joint-state arrays')
    all_values = {n: [float(q), float(v)] for n, q, v in
                  zip(names, message['position'], message['velocity'])}
    if any(n not in all_values or not all(math.isfinite(v) for v in all_values[n]) for n in required):
        raise ValueError('Missing or nonfinite required named joints')
    return {n: all_values[n] for n in required}


# Application communication timeout, NOT a physical stopping-time bound.
# v0.2.0 repeats unchanged E-stop values about every 4.5 s; changes are events.
STOP_STATE_TIMEOUT_S = 6.0


def check_stop_sample(received, value, now):
    # A reported stop always rejects immediately, independently of its age.
    if value != 0:
        raise RuntimeError('E-stop active or invalid')
    age = now - received
    if not math.isfinite(age) or not 0 <= age <= STOP_STATE_TIMEOUT_S:
        raise RuntimeError('Missing/stale E-stop communication')


def stop_cadence_ready(history, maximum_gap=STOP_STATE_TIMEOUT_S):
    """Require repeated observations within the communication timeout."""
    if len(history) < 2:
        return False
    gaps = [b-a for a, b in zip(history, history[1:])]
    if any(not math.isfinite(g) or g < 0 or g > maximum_gap for g in gaps):
        raise RuntimeError('E-stop state channel cannot meet monitor cadence; no dispatch')
    return True


def check_segment_corridor(stage, values, moving_tolerance, stationary_tolerance):
    """Require one common progress value, within the reviewed affine corridor.

    Independent joint boxes admit off-path poses. Intersect the progress
    intervals instead; this tests spatial consistency, not tracking in time
    or physical stopping distance.
    """
    if any(not math.isfinite(t) or t <= 0 for t in (moving_tolerance, stationary_tolerance)):
        raise ValueError('Invalid corridor tolerance')
    low, high = 0.0, 1.0
    for name, start, end in zip(stage['joint_order'], stage['start'], stage['end'], strict=True):
        q = values[name][0]
        if not all(math.isfinite(x) for x in (q, start, end)):
            raise RuntimeError('Nonfinite segment state')
        delta = end-start
        if delta == 0:
            if abs(q-start) > stationary_tolerance:
                raise RuntimeError('Stationary joint left corridor: '+name)
        else:
            a, b = sorted(((q-start-moving_tolerance)/delta, (q-start+moving_tolerance)/delta))
            low, high = max(low, a), min(high, b)
            if low > high:
                raise RuntimeError('Measured joints do not share progress on reviewed segment')
    return low, high


def main(payload):
    import rclpy
    from rclpy.action import ActionClient
    from rclpy.qos import qos_profile_sensor_data
    from rosidl_runtime_py.utilities import get_message
    from mc_task_msgs.action import ArmTask
    stage, release = payload['stage'], payload['release']
    # The host launcher checks loaded task identity inside Motion first; ROS
    # messages and rclpy belong to walker-ros.ros2-1, not the native Motion image.
    rclpy.init(); node = rclpy.create_node('entry410_single_stage_trial')
    state = {}; health = {}; stops = {}; stop_history = {}; subscriptions = []; goal = None
    def emit(**row): print(json.dumps(row, allow_nan=False), flush=True)
    def stop_message(topic, message):
        now = time.monotonic()
        stops[topic] = (now, int(message.data))
        stop_history.setdefault(topic, []).append(now)
    def actuator(message):
        now = time.monotonic(); states = {}; ids = payload['actuator_names']
        try:
            stamp = message.header.stamp.sec*1_000_000_000+message.header.stamp.nanosec
            age = (node.get_clock().now().nanoseconds-stamp)/1e9
            if not 0 <= age <= .5: raise ValueError('Stale actuator source stamp')
            for item in message.act_item:
                name = ids.get(str(item.id))
                if name is None: continue
                if name in states: raise ValueError('Duplicate actuator alias')
                values = [float(item.position), float(item.velocity)]
                if (not all(math.isfinite(v) for v in values) or item.error_code != 0
                        or item.status & 8 or item.status & 7 != 7):
                    raise ValueError('Invalid actuator state or hardware error')
                states[name] = values
            if set(states) != set(stage['joint_order']): raise ValueError('Missing controlled joints')
            health.update(received=now, error=None)
            emit(kind='actuator_health', received=now, healthy=True)
        except Exception as error:
            health.update(error=str(error))
    def joint_state(message):
        now = time.monotonic()
        try:
            stamp = message.header.stamp.sec*1_000_000_000+message.header.stamp.nanosec
            age = (node.get_clock().now().nanoseconds-stamp)/1e9
            if not 0 <= age <= .5:
                raise ValueError('Stale named joint-state source stamp')
            values = named_values(dict(name=list(message.name), position=list(message.position),
                velocity=list(message.velocity)), stage['joint_order'])
            state.update(received=now, values=values, error=None)
            emit(kind='named_joint_state', received=now, source_stamp_ns=stamp, values=values)
        except Exception as error:
            state.update(error=str(error))
    try:
        deadline = time.monotonic()+8
        topics = ['/mc/actuator_state', '/emb/estop_key_state', '/emb/servo_estop_key_state']
        named_topic = '/mc/whole_joint_states'
        while time.monotonic() < deadline:
            graph = dict(node.get_topic_names_and_types())
            if all(t in graph and len(graph[t]) == 1 for t in topics+[named_topic]): break
            rclpy.spin_once(node, timeout_sec=.1)
        else: raise RuntimeError('Missing unique telemetry topics')
        subscriptions.append(node.create_subscription(get_message(graph[topics[0]][0]), topics[0], actuator, qos_profile_sensor_data))
        subscriptions.append(node.create_subscription(get_message(graph[named_topic][0]), named_topic, joint_state, qos_profile_sensor_data))
        for topic in topics[1:]:
            subscriptions.append(node.create_subscription(get_message(graph[topic][0]), topic,
                lambda m, t=topic: stop_message(t, m), qos_profile_sensor_data))
        def safe_state():
            now = time.monotonic()
            if state.get('error') or now-state.get('received', -1e9) > .5:
                raise RuntimeError('Missing/stale/error named joint state')
            if health.get('error') or now-health.get('received', -1e9) > .5:
                raise RuntimeError('Missing/stale/error actuator health')
            for t in topics[1:]:
                if t not in stops: raise RuntimeError('Missing E-stop state')
                check_stop_sample(*stops[t], now)
            return state['values']
        def at_endpoint(endpoint):
            values = safe_state()
            return all(abs(values[n][0]-q) <= release['position_tolerance_rad']
                       and abs(values[n][1]) <= release['velocity_tolerance_rad_s']
                       for n, q in zip(stage['joint_order'], endpoint))
        def settled(endpoint, timeout):
            end = time.monotonic()+timeout; since = None
            while time.monotonic() < end:
                rclpy.spin_once(node, timeout_sec=.02)
                try: matches = at_endpoint(endpoint)
                except RuntimeError: matches = False
                since = (since if since is not None else time.monotonic()) if matches else None
                if since is not None and time.monotonic()-since >= .5: return True
            return False
        # One recent value is not evidence that a state-change topic provides
        # a continuous heartbeat. Test compatibility while still stationary.
        cadence_deadline = time.monotonic()+2*STOP_STATE_TIMEOUT_S+2
        while time.monotonic() < cadence_deadline:
            rclpy.spin_once(node, timeout_sec=.02)
            if all(stop_cadence_ready(stop_history.get(t, [])) for t in topics[1:]):
                break
        else:
            raise RuntimeError('Insufficient E-stop cadence evidence; no dispatch')
        if not settled(stage['start'], 8): raise RuntimeError('Measured start not stable at required 20D endpoint')
        client = ActionClient(node, ArmTask, '/mc/manipulation/action')
        if not client.wait_for_server(timeout_sec=2): raise RuntimeError('Action server absent')
        safe_state()
        request = ArmTask.Goal(); request.task_name = stage['task']; request.yaml_args = '{}'
        emit(kind='dispatch', task=stage['task'])
        future = client.send_goal_async(request)
        deadline = time.monotonic()+5
        while not future.done() and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.02)
        if not future.done(): raise RuntimeError('Acceptance unknown; do not retry; operator stop required')
        goal = future.result()
        if not goal.accepted: raise RuntimeError('Goal rejected')
        result = goal.get_result_async(); deadline = time.monotonic()+stage['duration_seconds']+10
        while not result.done():
            rclpy.spin_once(node, timeout_sec=.02)
            values = safe_state()
            check_segment_corridor(stage, values, release['position_tolerance_rad'],
                                   release['stationary_joint_tolerance_rad'])
            if time.monotonic() > deadline: raise RuntimeError('Action deadline exceeded')
        response = result.result()
        if response.status != 4: raise RuntimeError('Action did not succeed')
        if getattr(getattr(response.result, 'state', None), 'desc', None) != 'SUCCEED':
            raise RuntimeError('Motion result did not explicitly report SUCCEED')
        if not settled(stage['end'], 5): raise RuntimeError('Target not settled')
        emit(status='SINGLE_STAGE_SUCCEEDED_AND_SETTLED', task=stage['task'])
    except BaseException as error:
        emit(status='FAILED_NO_RETRY', reason=str(error), cancellation_is_not_certified_stop=True)
        if goal is not None and goal.accepted:
            cancellation = goal.cancel_goal_async()
            deadline = time.monotonic()+2
            while not cancellation.done() and time.monotonic() < deadline:
                rclpy.spin_once(node, timeout_sec=.02)
            emit(kind='cancel_request', response_received=cancellation.done())
        raise
    finally:
        node.destroy_node(); rclpy.shutdown()


if __name__ == '__main__':
    main(json.loads(base64.b64decode(PAYLOAD_B64, validate=True)))
