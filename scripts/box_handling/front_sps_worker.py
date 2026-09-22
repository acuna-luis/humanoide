#!/usr/bin/env python3
"""ROS2 transport/TF worker for the native SPS adapter. No motion clients."""
import argparse
import json
import os
from pathlib import Path
import socket
import time

from probe_front_box import validate_detection


def main():
    import rclpy
    from rclpy.action import ActionClient
    from rclpy.time import Time
    from tf2_ros import Buffer, TransformListener
    from cv_task_msgs.action import VisionActionTask
    from rosidl_runtime_py.convert import message_to_ordereddict

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    args = parser.parse_args()
    rclpy.init()
    node = rclpy.create_node('front_sps_transport_worker')
    buffer = Buffer()
    listener = TransformListener(buffer, node)
    client = ActionClient(node, VisionActionTask, '/cv/task/transport_action')
    server = socket.socket(socket.AF_UNIX)
    server.bind(str(args.session/'perception.sock'))
    os.chmod(args.session/'perception.sock', 0o600)
    server.listen(1)
    server.settimeout(0.05)
    failed = False

    def wait(future, end):
        while not future.done() and time.monotonic() < end:
            rclpy.spin_once(node, timeout_sec=0.02)
        if not future.done():
            raise TimeoutError('Perception deadline exceeded')
        return future.result()

    def capture():
        nonlocal failed
        handle, terminal = None, False
        try:
            if failed:
                raise RuntimeError('Worker failure latched; start a new reviewed session')
            if not client.wait_for_server(timeout_sec=0.5):
                raise RuntimeError('Transport perception unavailable')
            goal = VisionActionTask.Goal()
            goal.task_type = 'transport'
            goal.trans_inputs.camera_name = 'head'
            goal.trans_inputs.task_stage = 'grasp'
            goal.trans_inputs.box_size.x = 0.603
            goal.trans_inputs.box_size.y = 0.397
            goal.trans_inputs.box_size.z = 0.22
            request_ns = node.get_clock().now().nanoseconds
            end = time.monotonic()+7
            handle = wait(client.send_goal_async(goal), min(end, time.monotonic()+2))
            if not handle.accepted:
                raise RuntimeError('Transport perception rejected')
            response = wait(handle.get_result_async(), end)
            terminal = True
            result = message_to_ordereddict(response.result)
            poses, stamp_ns = validate_detection(result, response.status,
                                                 node.get_clock().now().nanoseconds,
                                                 request_ns)
            stamp = Time(nanoseconds=stamp_ns)
            source = poses['header']['frame_id']
            while not buffer.can_transform('base_link', source, stamp):
                if time.monotonic() >= end:
                    raise RuntimeError('Exact-time TF unavailable')
                rclpy.spin_once(node, timeout_sec=0.02)
            tf = message_to_ordereddict(buffer.lookup_transform('base_link', source, stamp))
            return dict(status=response.status, vision_result=result,
                        request_ns=request_ns, tf_at_detection=tf,
                        goal_id=bytes(handle.goal_id.uuid).hex())
        except Exception:
            failed = True
            if handle is not None and handle.accepted and not terminal:
                try:
                    response = wait(handle.cancel_goal_async(), time.monotonic()+0.5)
                    print('CANCEL_RESPONSE='+str(response.return_code), flush=True)
                except Exception:
                    print('PERCEPTION_CANCELLATION_UNCONFIRMED', flush=True)
            raise

    try:
        warmup = time.monotonic()+2
        while time.monotonic() < warmup:
            rclpy.spin_once(node, timeout_sec=0.05)
        (args.session/'worker.ready').write_text('ready\n')
        deadline = json.loads((args.session/'lease.json').read_text())['deadline']
        while (rclpy.ok() and not (args.session/'stop').exists()
               and time.monotonic() < deadline):
            rclpy.spin_once(node, timeout_sec=0.02)
            try:
                conn, _ = server.accept()
            except socket.timeout:
                continue
            with conn:
                conn.settimeout(1)
                request = conn.recv(64)
                if request != b'capture\n':
                    payload = {'error': 'Invalid worker request'}
                else:
                    try:
                        payload = {'report': capture()}
                    except Exception as exc:
                        payload = {'error': str(exc)}
                conn.sendall(json.dumps(payload, allow_nan=False).encode()+b'\n')
    finally:
        server.close()
        client.destroy()
        listener.unregister()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
