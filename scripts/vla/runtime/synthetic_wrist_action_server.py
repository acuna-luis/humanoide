#!/usr/bin/env python3
"""ROS action server and client for an isolated cancellation diagnostic.

The endpoint is restricted to a random diagnostic namespace. This program has
no interface to robot control and its synthetic goal never leaves this server.
"""
import argparse
import json
import re
import select
import sys
import threading
import time
import uuid


ENDPOINT = re.compile(r'/codex_smolvla_diag_[0-9a-f]{32}/action\Z')
TERMINAL_PUBLISH_WINDOW_S = 2.5


def valid_endpoint(value):
    return isinstance(value, str) and ENDPOINT.fullmatch(value) is not None


def terminal_published_long_enough(started, now):
    return started is not None and now-started >= TERMINAL_PUBLISH_WINDOW_S


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--endpoint', required=True)
    parser.add_argument('--goal-id', required=True)
    args = parser.parse_args(argv)
    if not valid_endpoint(args.endpoint):
        raise ValueError('synthetic_endpoint_required')
    goal_uuid = uuid.UUID(args.goal_id)
    if str(goal_uuid) != args.goal_id or goal_uuid.int == 0:
        raise ValueError('synthetic_uuid_required')
    import rclpy
    from rclpy.action import ActionClient, ActionServer, CancelResponse, GoalResponse
    from rclpy.callback_groups import ReentrantCallbackGroup
    from rclpy.executors import MultiThreadedExecutor
    from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
    from action_msgs.msg import GoalStatusArray
    from mc_task_msgs.action import ArmTask
    from unique_identifier_msgs.msg import UUID

    def emit(event, **fields):
        print(json.dumps({'event': event, **fields}, allow_nan=False), flush=True)

    rclpy.init()
    node = rclpy.create_node('synthetic_wrist_action_' + uuid.uuid4().hex,
                             enable_rosout=False, start_parameter_services=False)
    group = ReentrantCallbackGroup()
    cancel_seen = threading.Event()
    finished = threading.Event()

    def cancel(handle):
        ident = str(uuid.UUID(bytes=bytes(handle.goal_id.uuid)))
        if ident != args.goal_id:
            emit('SYNTHETIC_FOREIGN_UUID', goal_id=ident)
            return CancelResponse.REJECT
        cancel_seen.set()
        emit('SYNTHETIC_CANCEL_ACCEPTED', goal_id=ident)
        return CancelResponse.ACCEPT

    def execute(handle):
        ident = str(uuid.UUID(bytes=bytes(handle.goal_id.uuid)))
        if ident != args.goal_id:
            handle.abort(); finished.set()
            emit('SYNTHETIC_WRONG_GOAL', goal_id=ident)
            return ArmTask.Result()
        emit('SYNTHETIC_GOAL_ACTIVE', goal_id=ident)
        deadline = time.monotonic() + 20.0
        while time.monotonic() < deadline and not handle.is_cancel_requested:
            time.sleep(.025)
        if handle.is_cancel_requested and cancel_seen.is_set():
            handle.canceled(); emit('SYNTHETIC_GOAL_CANCELED', goal_id=ident)
        else:
            handle.abort(); emit('SYNTHETIC_GOAL_TIMEOUT', goal_id=ident)
        finished.set()
        return ArmTask.Result()

    server = ActionServer(node, ArmTask, args.endpoint, execute,
        goal_callback=lambda _: GoalResponse.ACCEPT, cancel_callback=cancel,
        callback_group=group)
    client = ActionClient(node, ArmTask, args.endpoint, callback_group=group)
    qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE,
                     durability=DurabilityPolicy.TRANSIENT_LOCAL)
    initial_status = node.create_publisher(GoalStatusArray, args.endpoint+'/_action/status', qos)
    initial_status.publish(GoalStatusArray())
    executor = MultiThreadedExecutor(num_threads=3)
    executor.add_node(node)
    sent = False
    terminal_at = None
    try:
        emit('SYNTHETIC_SERVER_READY', endpoint=args.endpoint, goal_id=args.goal_id)
        deadline = time.monotonic() + 40.0
        while time.monotonic() < deadline:
            executor.spin_once(timeout_sec=.02)
            if not sent and select.select([sys.stdin], [], [], 0)[0]:
                command = sys.stdin.readline()
                if not command:
                    raise RuntimeError('synthetic_stdin_closed')
                if json.loads(command) != {'command': 'send_synthetic', 'goal_id': args.goal_id}:
                    raise ValueError('synthetic_command_invalid')
                if not client.server_is_ready():
                    raise RuntimeError('synthetic_action_not_ready')
                goal = ArmTask.Goal()
                goal.task_name, goal.yaml_args = 'diagnostic_no_motion', '{}'
                client.send_goal_async(goal, goal_uuid=UUID(uuid=list(goal_uuid.bytes)))
                sent = True
                emit('SYNTHETIC_GOAL_SENT', endpoint=args.endpoint, goal_id=args.goal_id)
            if finished.is_set():
                # Allow ActionServer to publish its terminal status/result
                # before the node is destroyed; this is not physical braking.
                if terminal_at is None:
                    terminal_at = time.monotonic()
                if terminal_published_long_enough(terminal_at,time.monotonic()):
                    return 0 if cancel_seen.is_set() else 1
        raise TimeoutError('synthetic_server_timeout')
    finally:
        server.destroy(); client.destroy(); node.destroy_node(); executor.shutdown(timeout_sec=2)
        rclpy.shutdown()


if __name__ == '__main__':
    raise SystemExit(main())
