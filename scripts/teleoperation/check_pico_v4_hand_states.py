#!/usr/bin/env python3
"""Read-only v4 JointState gate. Two advancing samples per hand, no publishers."""
import json
import math
import time

SUFFIXES = ('thumb_swing', 'thumb_mcp', 'thumb_pip', 'index_mcp',
            'middle_mcp', 'ring_mcp', 'little_mcp')


def validate(side, names, positions, velocities):
    expected = {side + '_' + name for name in SUFFIXES}
    if len(names) != 7 or set(names) != expected:
        raise ValueError(side + ': expected the seven v4 joint names')
    if len(positions) != 7 or len(velocities) != 7:
        raise ValueError(side + ': incomplete position/velocity data')
    if not all(math.isfinite(v) for v in [*positions, *velocities]):
        raise ValueError(side + ': non-finite joint data')
    if any(abs(v) > .02 for v in velocities):
        raise ValueError(side + ': hand is not stationary')


def main():
    import rclpy
    from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
    from sensor_msgs.msg import JointState
    rclpy.init()
    node = rclpy.create_node('pico_v4_hands_readonly_preflight')
    seen = {side: [] for side in ('left', 'right')}
    errors = []
    qos = QoSProfile(depth=5, reliability=ReliabilityPolicy.BEST_EFFORT,
                     durability=DurabilityPolicy.VOLATILE)

    def callback(side, msg):
        try:
            validate(side, list(msg.name), list(msg.position), list(msg.velocity))
            stamp = msg.header.stamp.sec * 1_000_000_000 + msg.header.stamp.nanosec
            if stamp <= 0:
                raise ValueError(side + ': missing timestamp')
            if seen[side] and stamp < seen[side][-1]:
                raise ValueError(side + ': timestamp moved backwards')
            if not seen[side] or stamp > seen[side][-1]:
                seen[side].append(stamp)
                seen[side] = seen[side][-2:]
        except ValueError as error:
            errors.append(str(error))

    subscriptions = [node.create_subscription(
        JointState, '/mc/' + side + '_hand/joint_states',
        lambda msg, side=side: callback(side, msg), qos) for side in seen]
    deadline = time.monotonic() + 8
    try:
        while time.monotonic() < deadline and not errors:
            rclpy.spin_once(node, timeout_sec=.1)
            if all(len(samples) == 2 for samples in seen.values()):
                print('V4_HAND_STATES_OK=' + json.dumps(seen))
                return 0
        print('V4_HAND_STATES_NOT_READY=' + json.dumps(
            dict(samples=seen, errors=errors,
                 next_step='Load the native v4 finger controllers before START')))
        return 1
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    raise SystemExit(main())
