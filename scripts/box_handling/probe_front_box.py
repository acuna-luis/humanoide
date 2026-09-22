#!/usr/bin/env python3
"""Perception-only ROS 2 probe, streamed to the existing ROS container.

Uses a single fresh transport/head/grasp result and TF at its exact stamp.
No manipulation/nav client, controller switch, vision enable or file install.
The vendor vision server may save its usual diagnostic images.
"""
import json
import math
import sys
import time

if __package__:
    from .select_front_box import select_front_box
else:
    from select_front_box import select_front_box


def quaternion_product(a, b):
    x, y, z, w = a
    X, Y, Z, W = b
    return [w*X+x*W+y*Z-z*Y, w*Y-x*Z+y*W+z*X,
            w*Z+x*Y-y*X+z*W, w*W-x*X-y*Y-z*Z]


def transform_poses(poses, transform):
    """Rigid camera→base transform; preserves all candidate measurements."""
    q = [transform['rotation'][k] for k in 'xyzw']
    t = [transform['translation'][k] for k in 'xyz']
    if not all(math.isfinite(v) for v in q+t):
        raise ValueError('Nonfinite TF')
    if abs(sum(v*v for v in q)-1) > 1e-5:
        raise ValueError('Nonunit TF rotation')
    result = []
    for pose in poses:
        p = [pose['position'][k] for k in 'xyz']
        rotated = quaternion_product(quaternion_product(q, p+[0.0]),
                                     [-q[0], -q[1], -q[2], q[3]])
        orientation = quaternion_product(q, [pose['orientation'][k] for k in 'xyzw'])
        result.append({'position': dict(zip('xyz', [rotated[i]+t[i] for i in range(3)])),
                       'orientation': dict(zip('xyzw', orientation))})
    return result


def validate_detection(result, status, now_ns, request_ns):
    if status != 4 or result.get('ok') is not True:
        raise ValueError('Vision did not finish with status=4 / ok=true')
    out = result['trans_outputs']
    if out['camera_name'] != 'head' or out['object_name'] != 'workbin':
        raise ValueError('Unexpected camera or object type')
    header = out['box_pose']['header']
    if header['frame_id'] != 'stereo_left_rectified_optical_frame':
        raise ValueError('Unexpected detection frame')
    stamp = header['stamp']
    stamp_ns = stamp['sec']*10**9 + stamp['nanosec']
    if stamp_ns <= 0 or not 0 <= now_ns-stamp_ns <= 2*10**9:
        raise ValueError('Detection is stale or future-dated')
    # Allow only the most recent camera frame already in flight at the request.
    if stamp_ns < request_ns-500_000_000:
        raise ValueError('Detection predates this request')
    return out['box_pose'], stamp_ns


def main():
    # ROS dependencies are deliberately absent from the offline selection code.
    import rclpy
    from rclpy.action import ActionClient
    from rclpy.time import Time
    from tf2_ros import Buffer, TransformListener
    from cv_task_msgs.action import VisionActionTask
    from rosidl_runtime_py.convert import message_to_ordereddict

    rclpy.init()
    node = rclpy.create_node('front_box_perception_probe')
    buffer = Buffer()
    listener = TransformListener(buffer, node)
    client = ActionClient(node, VisionActionTask, '/cv/task/transport_action')
    handle = None
    terminal = False

    def wait(future, seconds):
        end = time.monotonic()+seconds
        while not future.done() and time.monotonic() < end:
            rclpy.spin_once(node, timeout_sec=0.05)
        if not future.done():
            raise TimeoutError('Perception response timeout; completion not established')
        return future.result()

    try:
        if not client.wait_for_server(timeout_sec=4.0):
            raise RuntimeError('Transport perception action unavailable')
        # Buffer TF before acquiring a detection; never fall back to latest TF.
        end = time.monotonic()+2.0
        while time.monotonic() < end:
            rclpy.spin_once(node, timeout_sec=0.05)
        goal = VisionActionTask.Goal()
        goal.task_type = 'transport'
        goal.trans_inputs.camera_name = 'head'
        goal.trans_inputs.task_stage = 'grasp'
        goal.trans_inputs.box_size.x = 0.603
        goal.trans_inputs.box_size.y = 0.397
        goal.trans_inputs.box_size.z = 0.22
        request_ns = node.get_clock().now().nanoseconds
        handle = wait(client.send_goal_async(goal), 4.0)
        if not handle.accepted:
            raise RuntimeError('Perception goal rejected')
        print('VISION_GOAL_ID='+bytes(handle.goal_id.uuid).hex(), flush=True)
        response = wait(handle.get_result_async(), 15.0)
        terminal = True
        result = message_to_ordereddict(response.result)
        poses, stamp_ns = validate_detection(result, response.status,
                                            node.get_clock().now().nanoseconds,
                                            request_ns)
        stamp = Time(nanoseconds=stamp_ns)
        source = poses['header']['frame_id']
        end = time.monotonic()+2.0
        while not buffer.can_transform('base_link', source, stamp):
            if time.monotonic() >= end:
                raise RuntimeError('No exact-time camera→base_link TF; no latest-TF fallback')
            rclpy.spin_once(node, timeout_sec=0.05)
        tf = message_to_ordereddict(buffer.lookup_transform('base_link', source, stamp))
        detection = {'frame_id': 'base_link',
                     'poses': transform_poses(poses['poses'], tf['transform'])}
        try:
            selection = select_front_box(detection)
        except ValueError as exc:
            print('FRONT_BOX_REJECTED_REPORT='+json.dumps(dict(
                goal_id=bytes(handle.goal_id.uuid).hex(), vision_result=result,
                tf_at_detection=tf, base_link_candidates=detection,
                selection_error=str(exc), movement_commands=0), allow_nan=False), flush=True)
            raise
        report = {'goal_id': bytes(handle.goal_id.uuid).hex(),
                  'vision_result': result, 'tf_at_detection': tf,
                  'base_link_candidates': detection, 'selection': selection,
                  'native_integration': False, 'movement_commands': 0}
        print('FRONT_BOX_REPORT='+json.dumps(report, allow_nan=False), flush=True)
        p = selection['selected_pose']['position']
        print('CAJA_FRONTAL: indice=%d; X=%.4fm Y=%.4fm Z=%.4fm; angulo=%.3fgrados'
              % (selection['selected_index'], p['x'], p['y'], p['z'],
                 selection['horizontal_bearing_deg']))
        print('SOLO_DIAGNOSTICO: sin agarre; alcance/IK e integración MetaClamp pendientes.')
        return 0
    except Exception as exc:
        print('FRONT_CHECK_REJECTED: '+str(exc), file=sys.stderr, flush=True)
        if handle is not None and handle.accepted and not terminal:
            try:
                canceled = wait(handle.cancel_goal_async(), 2.0)
                print('VISION_CANCEL_RESPONSE='+str(canceled.return_code), file=sys.stderr)
            except Exception as cancel_error:
                print('VISION_CANCEL_UNCONFIRMED: '+str(cancel_error), file=sys.stderr)
            print('VISION_TERMINAL_UNCONFIRMED: no asumir que terminó por el timeout.',
                  file=sys.stderr)
        return 2
    finally:
        client.destroy()
        listener.unregister()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    sys.exit(main())
