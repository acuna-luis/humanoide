"""ROS single-stage transport, sent on stdin by run_entry410_stage.py only.

Cancellation is a request, not a certified stop. No installation or reload.
"""
import base64
import hashlib
import json
import math
from pathlib import Path
import time


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
    state = {}; stops = {}; subscriptions = []; goal = None
    def emit(**row): print(json.dumps(row, allow_nan=False), flush=True)
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
                if not all(math.isfinite(v) for v in values) or item.error_code != 0:
                    raise ValueError('Invalid actuator state or hardware error')
                states[name] = values
            if set(states) != set(stage['joint_order']): raise ValueError('Missing controlled joints')
            state.update(received=now, values=states, error=None)
            emit(kind='actuator', received=now, values=states)
        except Exception as error:
            state.update(error=str(error))
    try:
        deadline = time.monotonic()+8
        topics = ['/mc/actuator_state', '/emb/estop_key_state', '/emb/servo_estop_key_state']
        while time.monotonic() < deadline:
            graph = dict(node.get_topic_names_and_types())
            if all(t in graph and len(graph[t]) == 1 for t in topics): break
            rclpy.spin_once(node, timeout_sec=.1)
        else: raise RuntimeError('Missing unique telemetry topics')
        subscriptions.append(node.create_subscription(get_message(graph[topics[0]][0]), topics[0], actuator, qos_profile_sensor_data))
        for topic in topics[1:]:
            subscriptions.append(node.create_subscription(get_message(graph[topic][0]), topic,
                lambda m, t=topic: stops.update({t: (time.monotonic(), int(m.data))}), qos_profile_sensor_data))
        def safe_state():
            now = time.monotonic()
            if state.get('error') or now-state.get('received', -1e9) > .5:
                raise RuntimeError('Missing/stale/error actuator state')
            if any(t not in stops or now-stops[t][0] > 3 or stops[t][1] != 0 for t in topics[1:]):
                raise RuntimeError('Missing/stale/active E-stop')
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
        stationary = [i for i, (a, b) in enumerate(zip(stage['start'], stage['end'])) if a == b]
        while not result.done():
            rclpy.spin_once(node, timeout_sec=.02)
            values = safe_state()
            for i, name in enumerate(stage['joint_order']):
                lo, hi = sorted((stage['start'][i], stage['end'][i]))
                tolerance = release['stationary_joint_tolerance_rad'] if i in stationary else release['position_tolerance_rad']
                if not lo-tolerance <= values[name][0] <= hi+tolerance:
                    raise RuntimeError('Measured joint outside allowed segment envelope: '+name)
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
