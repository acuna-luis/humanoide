"""Passive 32 Hz telemetry evidence; never authorizes or protects movement."""
import argparse
import hashlib
import json
import math
import signal
import time


TOPICS = (
    ('/mc/actuator_state', 'mc_state_msgs/msg/ActuatorState'),
    ('/mc/whole_joint_states', 'sensor_msgs/msg/JointState'),
    ('/emb/estop_key_state', 'std_msgs/msg/UInt8'),
    ('/emb/servo_estop_key_state', 'std_msgs/msg/UInt8'),
)
ALIASES = ((1001,), (1002,), (2001, 11004), (2002, 11003),
           (2003, 11002), (3001, 11001),
           *((axis,) for axis in range(4001, 4008)),
           *((axis,) for axis in range(5001, 5008)))


def finite(value, label):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('Nonfinite or nonnumeric '+label)
    return value


def source_ns(message):
    value = message['header']['stamp']
    sec, ns = value['sec'], value['nanosec']
    if type(sec) is not int or sec < 0 or type(ns) is not int or not 0 <= ns < 10**9:
        raise ValueError('Invalid source timestamp')
    result = sec*10**9+ns
    if result <= 0:
        raise ValueError('Missing source timestamp')
    return result


def validate(topic, message):
    if not isinstance(message, dict):
        raise ValueError('Message must be an object')
    json.dumps(message, allow_nan=False)
    if topic.startswith('/emb/'):
        if type(message.get('data')) is not int or not 0 <= message['data'] <= 255:
            raise ValueError('Invalid UInt8 stop value')
        # UInt8 has no source stamp. Receipt is evidence only, not a source time.
        return dict(source_stamp_ns=None, stop_value=message['data'])
    stamp = source_ns(message)
    if topic == '/mc/whole_joint_states':
        names = message['name']
        if (not isinstance(names, list) or not names or any(not isinstance(n, str) or not n for n in names)
                or len(set(names)) != len(names)):
            raise ValueError('Invalid joint names')
        for key in ('position', 'velocity', 'effort'):
            values = message[key]
            if not isinstance(values, list) or (len(values) != len(names) and not (key != 'position' and not values)):
                raise ValueError('Invalid joint '+key+' length')
            for value in values:
                finite(value, 'joint '+key)
        return dict(source_stamp_ns=stamp, joint_count=len(names))
    items = message['act_item']
    if not isinstance(items, list):
        raise ValueError('Missing actuators')
    by_id = {}
    for item in items:
        axis = item.get('id')
        if type(axis) is not int or axis <= 0 or axis in by_id:
            raise ValueError('Invalid or duplicate actuator id')
        by_id[axis] = item
    body = []
    for aliases in ALIASES:
        found = [axis for axis in aliases if axis in by_id]
        if len(found) != 1:
            raise ValueError('Incomplete or ambiguous 20D coverage: '+repr(aliases))
        item = by_id[found[0]]
        for key in ('error_code', 'status'):
            if type(item.get(key)) is not int or item[key] < 0:
                raise ValueError('Invalid actuator '+key)
        row = dict(id=found[0], name=item.get('name'), error_code=item['error_code'], status=item['status'])
        for key in ('position', 'cmd_pos', 'velocity', 'current'):
            row[key] = finite(item.get(key), 'actuator '+key)
        row['command_error_rad'] = finite(row['cmd_pos']-row['position'], 'command error')
        body.append(row)
    return dict(source_stamp_ns=stamp, body_count=len(body), body=body)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=float, default=40.)
    args = parser.parse_args(argv)
    if not math.isfinite(args.seconds) or not 0 < args.seconds <= 120:
        parser.error('--seconds must be in (0,120]')
    import rosa
    from rosa.base._QoS import SensorDataQoS
    from rosa.utils import resolve_message_type
    counts = {topic: dict(received=0, emitted=0, invalid=0, repeated_source=0,
                         regressing_source=0) for topic, _ in TOPICS}
    previous = {}
    last_emit = {}
    readers = {}
    stopped = [False]

    def emit(value, received_ns=None, received_monotonic_ns=None):
        print(json.dumps(dict(received_ns=time.time_ns() if received_ns is None else received_ns,
            received_monotonic_ns=time.monotonic_ns() if received_monotonic_ns is None else received_monotonic_ns,
            **value), allow_nan=False, separators=(',', ':')), flush=True)

    def callback(topic):
        def receive(raw: str):
            wall, mono = time.time_ns(), time.monotonic_ns()
            counts[topic]['received'] += 1
            try:
                message = json.loads(raw)
                derived = validate(topic, message)
                stamp = derived['source_stamp_ns']
                old = previous.get(topic)
                relation = 'unstamped' if stamp is None else 'first' if old is None else (
                    'advancing' if stamp > old else 'repeated' if stamp == old else 'regressing')
                if relation == 'repeated':
                    counts[topic]['repeated_source'] += 1
                if relation == 'regressing':
                    counts[topic]['regressing_source'] += 1
                if stamp is not None:
                    previous[topic] = stamp
                # Never throttle either stop; retain every received transition.
                if not topic.startswith('/emb/') and mono-last_emit.get(topic, 0) < 31_250_000:
                    return
                last_emit[topic] = mono
                counts[topic]['emitted'] += 1
                emit(dict(kind='message', topic=topic, message=message, derived=derived,
                    source_relation=relation, source_age_ns=None if stamp is None else wall-stamp), wall, mono)
            except Exception as exc:
                counts[topic]['invalid'] += 1
                emit(dict(kind='validation_error', topic=topic, reason=type(exc).__name__+': '+str(exc),
                    raw=raw), wall, mono)
        return receive

    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, lambda *unused: stopped.__setitem__(0, True))
    rosa.init()
    try:
        node = rosa.Node('cruzr_empty_arm_trace_readonly')
        for topic, typename in TOPICS:
            qos = SensorDataQoS()
            qos.bestEffort()
            qos.durabilityVolatile()
            qos.keepLast(1)
            readers[topic] = node.create_reader(resolve_message_type(typename), topic, callback(topic), qos=qos)
        emit(dict(kind='start', seconds=args.seconds, max_emit_hz=32, topics=dict(TOPICS),
                  movement_commands=0, configuration_changes=0, passive_evidence_only=True))
        begin, next_counts = time.monotonic(), time.monotonic()
        while rosa.ok() and not stopped[0] and time.monotonic()-begin < args.seconds:
            rosa.spin_once(node, 5)
            if time.monotonic() >= next_counts:
                emit(dict(kind='publishers', counts={topic: reader.getWriterCount() for topic, reader in readers.items()}))
                next_counts = time.monotonic()+1.
        return 0
    finally:
        rosa.shutdown()
        emit(dict(kind='end', counts=counts, signal_received=stopped[0], movement_commands=0,
                  passive_evidence_only=True, active_protection_claimed=False))


if __name__ == '__main__':
    raise SystemExit(main())
