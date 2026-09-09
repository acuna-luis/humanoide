#!/usr/bin/env python3
"""Lee dos poses nuevas de mapa; sólo suscribe, no publica ni llama servicios."""
import math
import time


def validate_pose(message, now):
    stamp = message['header']['stamp']
    seconds, nanoseconds = stamp['sec'], stamp['nanosec']
    if type(seconds) is not int or type(nanoseconds) is not int or seconds <= 0 or not 0 <= nanoseconds < 10**9:
        raise ValueError('Sello temporal inválido')
    instant = seconds + nanoseconds / 1e9
    if not -.25 <= now - instant <= 3.0:
        raise ValueError('Pose de mapa antigua o futura')
    if message['header']['frame_id'] != 'map':
        raise ValueError('La pose no está expresada en map')
    p, q = message['pose']['position'], message['pose']['orientation']
    values = [p[k] for k in 'xyz'] + [q[k] for k in 'xyzw']
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
        raise ValueError('Pose no finita')
    if not .99 <= math.sqrt(sum(q[k]**2 for k in 'xyzw')) <= 1.01:
        raise ValueError('Cuaternión no unitario')
    if abs(q['x']) > .01 or abs(q['y']) > .01:
        raise ValueError('Pose no planar')
    yaw = math.atan2(2 * (q['w']*q['z'] + q['x']*q['y']), 1-2*(q['y']**2+q['z']**2))
    return seconds * 10**9 + nanoseconds, (p['x'], p['y'], yaw)


def main():
    import sys
    import rclpy
    from geometry_msgs.msg import PoseStamped
    from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
    rclpy.init()
    node = rclpy.create_node('cruzr_map_pose_readonly')
    state = {'stamp': None, 'pose': None, 'error': 'No llegaron dos muestras nuevas'}

    def callback(msg):
        message = dict(header=dict(stamp=dict(sec=msg.header.stamp.sec, nanosec=msg.header.stamp.nanosec),
                                   frame_id=msg.header.frame_id),
                       pose=dict(position={k: getattr(msg.pose.position, k) for k in 'xyz'},
                                 orientation={k: getattr(msg.pose.orientation, k) for k in 'xyzw'}))
        try:
            stamp, pose = validate_pose(message, time.time())  # reloj del mismo host robot
            if state['stamp'] is not None and stamp > state['stamp']:
                state['pose'] = pose
            state['stamp'] = stamp
        except (ValueError, KeyError, TypeError) as exc:
            state['error'] = str(exc)
            state['stamp'] = None

    node.create_subscription(PoseStamped, '/nav/robot_pose', callback,
        QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.VOLATILE))
    deadline = time.monotonic() + 6
    try:
        while state['pose'] is None and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.2)
        if state['pose'] is None:
            raise ValueError(state['error'])
        print(' '.join(format(v, '.12g') for v in state['pose']))
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
