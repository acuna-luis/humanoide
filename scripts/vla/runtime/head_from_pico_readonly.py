#!/usr/bin/env python3
"""Admisión pasiva de cabeza desde PICO v4. No tiene cliente de acción.

Lee telemetría y reutiliza el monitor de paro de metamove_head_probe. No puede
despachar objetivos ni demuestra colisión, exclusividad o parada física.
"""
import math
import time

from metamove_head_probe import check_stop_cadence, check_stop_sample


BODY = {
    'head_yaw_joint': 0.0, 'head_pitch_joint': 0.0,
    'waist_yaw_joint': 0.0, 'lifter_pitch_1_joint': 0.0,
    'lifter_pitch_2_joint': 0.0, 'lifter_pitch_3_joint': 0.0,
    'L_shoulder_pitch_joint': 0.0, 'L_shoulder_roll_joint': -0.15,
    'L_shoulder_yaw_joint': -1.57, 'L_elbow_roll_joint': -1.57,
    'L_elbow_yaw_joint': 2.88, 'L_wrist_pitch_joint': 0.0,
    'L_wrist_roll_joint': 0.0,
    'R_shoulder_pitch_joint': 0.0, 'R_shoulder_roll_joint': -0.15,
    'R_shoulder_yaw_joint': 1.57, 'R_elbow_roll_joint': -1.57,
    'R_elbow_yaw_joint': -2.88, 'R_wrist_pitch_joint': 0.0,
    'R_wrist_roll_joint': 0.0,
}
HAND_SUFFIXES = ('thumb_swing', 'thumb_mcp', 'thumb_pip', 'index_mcp',
                 'middle_mcp', 'ring_mcp', 'little_mcp')
ACTUATOR_IDS = frozenset([1001, 1002, 11001, 11002, 11003, 11004,
                          *range(4001, 4008), *range(5001, 5008)])
JOINT_LIMIT = .02
JOINT_SPEED = .001
JOINT_DRIFT = .002
HAND_SPEED = .02
DATA_AGE_S = .5
# Valores del perfil PICO v4 verificado por hash en el wrapper; son límites de
# configuración histórica, NO límites efectivos demostrados del hardware.
_ARM_JOINTS = ('shoulder_pitch', 'shoulder_roll', 'shoulder_yaw',
               'elbow_roll', 'elbow_yaw', 'wrist_pitch', 'wrist_roll')
_ARM_MIN = (-2.8274, -1.8500, -2.8972, -2.6180, -2.88872, -1.5882, -1.9897)
_ARM_MAX = (2.8274, .0873, 2.8972, 0.0, 2.88872, 1.5882, 1.9897)
DECLARED_LIMITS = {
    **{side + '_' + name + '_joint': (lo, hi)
       for side in ('L', 'R') for name, lo, hi in zip(_ARM_JOINTS, _ARM_MIN, _ARM_MAX, strict=True)},
    'head_yaw_joint': (-1.64, 1.64), 'head_pitch_joint': (-.68, .52),
    'waist_yaw_joint': (-2.9, 2.9), 'lifter_pitch_1_joint': (-1.50, 1.50),
    'lifter_pitch_2_joint': (-2.52, 2.52), 'lifter_pitch_3_joint': (-1.50, 1.50),
}


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def joint_state(message, expected_names, *, exact=False):
    names, pos, vel = (message.get(k) for k in ('name', 'position', 'velocity'))
    if (not all(isinstance(v, list) for v in (names, pos, vel)) or
            len(names) != len(pos) or len(names) != len(vel) or
            any(not isinstance(n, str) for n in names) or len(set(names)) != len(names) or
            not set(expected_names).issubset(names) or (exact and set(names) != set(expected_names))):
        raise ValueError('joint_names_or_lengths_invalid')
    if not all(finite(v) for v in pos + vel):
        raise ValueError('joint_values_nonfinite')
    return {n: (float(p), float(v)) for n, p, v in zip(names, pos, vel, strict=True)}


def check_body(message):
    values = joint_state(message, BODY)
    if any(abs(values[n][0] - target) > JOINT_LIMIT for n, target in BODY.items()):
        raise ValueError('not_pico_v4_reference')
    if any(not lo <= values[n][0] <= hi for n, (lo, hi) in DECLARED_LIMITS.items()):
        raise ValueError('outside_declared_pico_v4_limits')
    if any(abs(values[n][1]) > JOINT_SPEED for n in BODY):
        raise ValueError('body_not_stationary')
    return {n: values[n][0] for n in BODY}


def check_hand(message, side):
    expected = [side + '_' + x for x in HAND_SUFFIXES]
    values = joint_state(message, expected, exact=True)
    if any(abs(values[n][1]) > HAND_SPEED for n in expected):
        raise ValueError('hand_not_stationary:' + side)


def check_actuators(message):
    items = message.get('act_item')
    if not isinstance(items, list):
        raise ValueError('actuators_missing')
    selected = [x for x in items if isinstance(x, dict) and x.get('id') in ACTUATOR_IDS]
    if (len(selected) != 20 or {x['id'] for x in selected} != ACTUATOR_IDS or
            any(type(x.get('error_code')) is not int or x['error_code'] != 0 or
                type(x.get('status')) is not int or x['status'] & 8 or
                x['status'] & 7 != 7 for x in selected)):
        raise ValueError('actuator_fault_disabled_or_incomplete')


def check_battery(message):
    batteries = message.get('batteries_states')
    if not isinstance(batteries, list) or len(batteries) != 2:
        raise ValueError('battery_data_missing')
    if any(not isinstance(b, dict) or not finite(b.get('batsoc')) or
           b['batsoc'] < 30 or b['batsoc'] > 100 for b in batteries):
        raise ValueError('battery_invalid_or_below_30_percent')


def source_stamp_ns(message):
    stamp = message.get('header', {}).get('stamp', {})
    sec, ns = stamp.get('sec'), stamp.get('nanosec')
    if type(sec) is not int or type(ns) is not int or sec <= 0 or not 0 <= ns < 1_000_000_000:
        raise ValueError('source_stamp_invalid')
    return sec * 1_000_000_000 + ns


def check_timing(received, now, max_age):
    if not finite(received) or not finite(now) or not 0 <= now - received <= max_age:
        raise ValueError('sample_stale_or_future')


def main():
    import json
    import rclpy
    from rclpy.qos import qos_profile_sensor_data
    from rosidl_runtime_py.utilities import get_message
    from rosidl_runtime_py.convert import message_to_ordereddict

    topics = {
        'body': '/mc/whole_joint_states', 'actuators': '/mc/actuator_state',
        'left': '/mc/left_hand/joint_states', 'right': '/mc/right_hand/joint_states',
        'estop': '/emb/estop_key_state', 'servo_stop': '/emb/servo_estop_key_state',
        'charger': '/emb/chrg_input_status', 'battery': '/emb/battery_state',
    }
    rclpy.init()
    node = rclpy.create_node('pico_v4_head_readonly_admission', enable_rosout=False,
                             start_parameter_services=False)
    samples, stop_times, stamps = {}, {'estop': [], 'servo_stop': []}, {}
    subscriptions = []
    initial = None
    stationary_since = None
    try:
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            graph = dict(node.get_topic_names_and_types())
            if all(t in graph and len(graph[t]) == 1 for t in topics.values()):
                break
            rclpy.spin_once(node, timeout_sec=.05)
        else:
            raise ValueError('required_topics_not_discovered')

        def receive(key, message):
            now = time.monotonic()
            samples[key] = (now, message_to_ordereddict(message))
            if key in stop_times:
                stop_times[key].append(now)
                stop_times[key] = stop_times[key][-4:]

        for key, topic in topics.items():
            subscriptions.append(node.create_subscription(get_message(graph[topic][0]), topic,
                lambda message, key=key: receive(key, message), qos_profile_sensor_data))

        deadline = time.monotonic() + 22
        reason = 'telemetry_not_ready'
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.02)
            try:
                now = time.monotonic()
                if set(samples) != set(topics):
                    raise ValueError('telemetry_not_ready')
                for key in ('body', 'actuators', 'left', 'right'):
                    received, data = samples[key]
                    check_timing(received, now, DATA_AGE_S)
                    stamp = source_stamp_ns(data)
                    age = (node.get_clock().now().nanoseconds - stamp) / 1e9
                    if not 0 <= age <= DATA_AGE_S:
                        raise ValueError('source_stale_or_future:' + key)
                    if key in stamps and stamp < stamps[key]:
                        raise ValueError('source_stamp_regressed:' + key)
                    stamps[key] = stamp
                for key in ('estop', 'servo_stop'):
                    check_stop_sample(samples[key][0], samples[key][1].get('data'), now)
                    if not check_stop_cadence(stop_times[key]):
                        raise ValueError('insufficient_estop_heartbeat:' + key)
                # Charger and battery messages may be event-driven; use the same
                # 6 s communications window as the existing stop observer.
                for key in ('charger', 'battery'):
                    check_timing(samples[key][0], now, 6.0)
                if samples['charger'][1].get('data') != 0:
                    raise ValueError('charger_connected_or_unknown')
                check_battery(samples['battery'][1])
                positions = check_body(samples['body'][1])
                check_actuators(samples['actuators'][1])
                check_hand(samples['left'][1], 'left')
                check_hand(samples['right'][1], 'right')
                if initial is None:
                    initial = positions
                if any(abs(positions[n] - initial[n]) > JOINT_DRIFT for n in BODY):
                    raise ValueError('body_drift_during_observation')
                stationary_since = stationary_since or now
                if now - stationary_since >= 1.0:
                    print(json.dumps({'status': 'PICO_HEAD_PASSIVE_ADMISSION_OBSERVED',
                        'movement_commands': 0, 'continuous_stop_and_joints_s': round(now-stationary_since, 3),
                        'physical_control_qualified': False,
                        'pending': ['scene_and_v4_mount', 'exclusive_control',
                                    'head_action_mode_and_stop', 'physical_supervision']}), flush=True)
                    return 0
            except (ValueError, RuntimeError, KeyError, TypeError) as exc:
                stationary_since = None
                initial = None
                reason = str(exc)
        print(json.dumps({'status': 'PICO_HEAD_PASSIVE_ADMISSION_FAILED',
                          'reason': reason, 'movement_commands': 0,
                          'physical_control_qualified': False}), flush=True)
        return 1
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    raise SystemExit(main())
