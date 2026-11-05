#!/usr/bin/env python3
"""Bounded ROS subscriptions only. Stream decoded RGB and telemetry to the PC.

Executed from stdin in an existing ROS container. No control publishers,
service/action clients or parameter updates. Collected files go to the PC.
"""
import argparse
import base64
import hashlib
import json
import queue
import signal
import struct
import threading
import time
import zlib

TOPICS = {
    'rgb': ('/sensor/camera/stereo/color/raw', 'shm_msgs/msg/Image2m'),
    'joints': ('/mc/whole_joint_states', 'sensor_msgs/msg/JointState'),
    'actuators': ('/mc/actuator_state', 'mc_state_msgs/msg/ActuatorState'),
    'force_left': ('/mc/ft_states/L_hand_ft', 'geometry_msgs/msg/WrenchStamped'),
    'force_right': ('/mc/ft_states/R_hand_ft', 'geometry_msgs/msg/WrenchStamped'),
}
OPTIONAL_COMMAND = ('/mc/sdk/robot_command', 'mc_task_msgs/msg/RobotCommand')
OPTIONAL_HANDS = {
    'hand_left': ('/mc/left_hand/joint_states', 'sensor_msgs/msg/JointState'),
    'hand_right': ('/mc/right_hand/joint_states', 'sensor_msgs/msg/JointState'),
    'hand_command_left': ('/mc/left_hand/command', 'mc_task_msgs/msg/JointCommand'),
    'hand_command_right': ('/mc/right_hand/command', 'mc_task_msgs/msg/JointCommand'),
}


def message_text(value):
    if isinstance(value, str):
        return value
    return bytes(value.data[:value.size]).decode('utf-8', errors='strict')


def source_ns(message):
    try:
        stamp = message.header.stamp
        return int(stamp.sec)*10**9+int(stamp.nanosec)
    except AttributeError:
        return None


def png_bytes(width, height, step, encoding, data):
    """Decode actual Image2m pixels including row padding; lossless PNG."""
    channels = {'rgb8': 3, 'bgr8': 3, 'mono8': 1}.get(encoding)
    if channels is None or not 0 < width <= 4096 or not 0 < height <= 4096:
        raise ValueError('Unsupported RGB encoding or dimensions')
    if not width*channels <= step <= width*channels+65536 or len(data) < step*height:
        raise ValueError('Truncated pixels or invalid step')
    rows = bytearray()
    for y in range(height):
        row = bytes(data[y*step:y*step+width*channels])
        if encoding == 'bgr8':
            rgb = bytearray(len(row))
            rgb[0::3], rgb[1::3], rgb[2::3] = row[2::3], row[1::3], row[0::3]
            row = rgb
        rows.extend(b'\0'); rows.extend(row)
    def chunk(kind, payload):
        return struct.pack('!I', len(payload))+kind+payload+struct.pack('!I', zlib.crc32(kind+payload)&0xffffffff)
    color_type = 0 if channels == 1 else 2
    return (b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('!2I5B', width, height, 8, color_type, 0, 0, 0))+
            chunk(b'IDAT', zlib.compress(rows, 1))+chunk(b'IEND', b''))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seconds', type=float, required=True)
    p.add_argument('--fps', type=float, default=5)
    p.add_argument('--telemetry-hz', type=float, default=30)
    args = p.parse_args(argv)
    if not 1 <= args.seconds <= 1800 or not .5 <= args.fps <= 15 or not 1 <= args.telemetry_hz <= 100:
        p.error('Invalid bounded capture duration/rates')
    import rclpy
    from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
    from rosidl_runtime_py.utilities import get_message
    from rosidl_runtime_py.convert import message_to_ordereddict
    rclpy.init()
    node = rclpy.create_node('cruzr_passive_episode_capture',
                             enable_rosout=False, start_parameter_services=False)
    counts, last, errors, subscriptions = {}, {}, [], []
    hand_subscriptions = {}
    image_queue = queue.Queue(maxsize=2)
    closed = threading.Event()
    output_lock = threading.Lock()
    image_drops = 0
    stopped = False
    def stop(*unused):
        nonlocal stopped
        stopped = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    def emit(row):
        text = json.dumps(row, allow_nan=False, separators=(',', ':'))
        with output_lock:
            print(text, flush=True)
    def encode_images():
        while not closed.is_set() or not image_queue.empty():
            try:
                row, pixels = image_queue.get(timeout=.1)
            except queue.Empty:
                continue
            try:
                png = png_bytes(row['width'],row['height'],row['step'],row['encoding'],pixels)
                row.update(pixels_sha256=hashlib.sha256(pixels).hexdigest(),
                           png_sha256=hashlib.sha256(png).hexdigest(),
                           png_b64=base64.b64encode(png).decode('ascii'))
                emit(row)
                counts['rgb'] += 1
            except Exception as exc:
                errors.append('rgb: '+type(exc).__name__+': '+str(exc)); stop()
            finally:
                image_queue.task_done()
    image_thread = threading.Thread(target=encode_images,daemon=True)
    image_thread.start()
    try:
        discovery_end = time.monotonic()+6
        while time.monotonic() < discovery_end and not stopped:
            rclpy.spin_once(node, timeout_sec=.05)
            graph = dict(node.get_topic_names_and_types())
            if all(graph.get(topic) == [typ] for topic, typ in TOPICS.values()):
                break
        else:
            raise RuntimeError('Required topic types missing: '+repr({k: graph.get(t) for k, (t, _) in TOPICS.items()}))
        specs = dict(TOPICS)
        if graph.get(OPTIONAL_COMMAND[0]) == [OPTIONAL_COMMAND[1]]:
            specs['sdk_command'] = OPTIONAL_COMMAND
        qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT,
                         durability=DurabilityPolicy.VOLATILE)
        def receive(kind, message):
            nonlocal image_drops
            now, wall = time.monotonic_ns(), time.time_ns()
            period = 1/args.fps if kind == 'rgb' else 1/args.telemetry_hz
            if kind not in ('sdk_command', 'hand_command_left', 'hand_command_right') and now-last.get(kind, 0) < period*1e9:
                return
            try:
                row = dict(kind=kind, source_ns=source_ns(message),
                           received_ns=wall, received_monotonic_ns=now)
                if kind == 'rgb':
                    width, height, step = int(message.width), int(message.height), int(message.step)
                    encoding = message_text(message.encoding)
                    if step*height > 32*1024*1024:
                        raise ValueError('Image exceeds bounded pixel buffer')
                    pixels = bytes(message.data[:step*height])
                    row.update(width=width, height=height, step=step, encoding=encoding,
                               frame_id=message_text(message.header.frame_id))
                    try:
                        image_queue.put_nowait((row,pixels))
                    except queue.Full:
                        image_drops += 1
                    last[kind] = now
                    return
                else:
                    row['message'] = message_to_ordereddict(message)
                emit(row)
                last[kind] = now
                counts[kind] = counts.get(kind, 0)+1
            except Exception as exc:
                error = type(exc).__name__+': '+str(exc)
                if kind in OPTIONAL_HANDS:
                    emit(dict(kind='hand_error', stream=kind, error=error,
                              received_ns=wall, received_monotonic_ns=now))
                else:
                    errors.append(kind+': '+error)
                    stop()
        for kind, (topic, typ) in specs.items():
            counts[kind] = 0
            subscriptions.append(node.create_subscription(get_message(typ), topic,
                lambda message, kind=kind: receive(kind, message), qos))
        started = time.monotonic_ns()
        emit(dict(kind='start', started_ns=time.time_ns(), started_monotonic_ns=started,
                  seconds=args.seconds, fps_limit=args.fps, telemetry_hz_limit=args.telemetry_hz,
                  topics=specs, clock='single Vision host reception clock; source stamps unmodified',
                  movement_commands=0))
        hand_graph_previous = None
        hand_discovery_at = 0.0
        def discover_hands():
            nonlocal hand_graph_previous, hand_discovery_at
            hand_discovery_at = time.monotonic()+1.0
            graph_now = dict(node.get_topic_names_and_types())
            detail = {}
            for kind, (topic, typ) in OPTIONAL_HANDS.items():
                observed = sorted(graph_now.get(topic, []))
                error = None
                if typ in observed and kind not in hand_subscriptions:
                    try:
                        hand_qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT,
                                              durability=DurabilityPolicy.VOLATILE)
                        sub = node.create_subscription(get_message(typ), topic,
                            lambda message, kind=kind: receive(kind, message), hand_qos)
                        subscriptions.append(sub)
                        hand_subscriptions[kind] = sub
                        counts[kind] = 0
                    except Exception as exc:
                        error = type(exc).__name__+': '+str(exc)
                detail[kind] = dict(topic=topic, expected_type=typ,
                    observed_types=observed, subscribed=kind in hand_subscriptions,
                    publisher_count=node.count_publishers(topic))
                if error:
                    detail[kind]['error'] = error
            if detail != hand_graph_previous:
                emit(dict(kind='hand_discovery', topics=detail, received_ns=time.time_ns(),
                          received_monotonic_ns=time.monotonic_ns()))
                hand_graph_previous = detail
        discover_hands()
        warmup_deadline = time.monotonic()+8
        deadline, ready, base_ready_at = warmup_deadline, False, None
        while not stopped and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.02)
            if time.monotonic() >= hand_discovery_at:
                discover_hands()
            if not ready and base_ready_at is None and all(counts[k] >= 2 for k in TOPICS):
                base_ready_at = time.monotonic()
                deadline = max(deadline, base_ready_at+2)
            if (not ready and base_ready_at is not None and
                    (all(counts.get(k, 0) >= 2 for k in ('hand_left', 'hand_right')) or
                     time.monotonic()-base_ready_at >= 2)):
                ready = True
                deadline = time.monotonic()+args.seconds
                emit(dict(kind='ready', received_ns=time.time_ns(),received_monotonic_ns=time.monotonic_ns(),
                          hand_samples={k: counts.get(k, 0) for k in ('hand_left', 'hand_right')}))
        if not ready:
            errors.append('Required signals never became ready during warmup')
        closed.set(); image_thread.join(timeout=5)
        if image_thread.is_alive():
            errors.append('Image encoding/transport did not drain within budget')
        emit(dict(kind='end', counts=counts, errors=errors[:30], stopped=stopped,
                  image_queue_drops=image_drops,
                  elapsed_s=(time.monotonic_ns()-started)/1e9, movement_commands=0))
        return 0 if not stopped and not errors and all(counts[k] > 1 for k in TOPICS) else 3
    finally:
        closed.set()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    raise SystemExit(main())
