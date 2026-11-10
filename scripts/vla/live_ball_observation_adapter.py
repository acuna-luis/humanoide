#!/usr/bin/env python3
"""Pair the passive Vision JSONL stream for SmolVLA shadow, never control.

Reads stdin and writes bounded observations to stdout. No ROS, network, robot
client, motion command or actuator publisher is present in this process.
Clock stamps are nominal and do not prove physical clock synchronization.
"""
import base64
from collections import deque
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import time

from prepare_ball_observations import RIGHT_HAND, TASK

PROFILE = Path(__file__).resolve().parent / 'runtime/cruzr_s2_vla_profile.json'
MAX_LINE = 48 * 1024 * 1024
MAX_SOURCE_AGE_NS = 80_000_000
MAX_RECEIPT_AGE_NS = 500_000_000


def positions(row, names, field='position'):
    msg = row.get('message')
    if not isinstance(msg, dict):
        raise ValueError('joint message missing')
    keys, values = msg.get('name'), msg.get(field)
    if (not isinstance(keys, list) or not isinstance(values, list) or len(keys) != len(values)
            or any(not isinstance(k, str) for k in keys) or len(set(keys)) != len(keys)):
        raise ValueError('joint names and positions malformed')
    mapping = dict(zip(keys, values))
    result = []
    for name in names:
        v = mapping.get(name)
        if type(v) not in (int, float) or not math.isfinite(v):
            raise ValueError('missing or nonfinite joint ' + field + ': ' + name)
        result.append(v)
    return result


def valid_stamp(value):
    return type(value) is int and value > 0


class Pairer:
    def __init__(self, joint_names):
        if (not isinstance(joint_names, list) or len(joint_names) != 20 or
                any(not isinstance(n, str) for n in joint_names) or len(set(joint_names)) != 20):
            raise ValueError('bad 20D profile joint names')
        self.joint_names = joint_names
        self.history = {'joints': deque(maxlen=256), 'hand_right': deque(maxlen=256)}
        self.started = self.ready = self.ended = False
        self.last_image_source = 0
        self.produced = self.dropped = 0

    def accept(self, row):
        if not isinstance(row, dict) or not isinstance(row.get('kind'), str):
            raise ValueError('malformed stream record')
        kind = row['kind']
        if self.ended:
            raise ValueError('record after end')
        if kind == 'start':
            if self.started or type(row.get('movement_commands')) is not int or row['movement_commands'] != 0:
                raise ValueError('invalid stream start')
            self.started = True
            return None
        if not self.started:
            raise ValueError('record before start')
        if kind == 'ready':
            if self.ready:
                raise ValueError('duplicate ready')
            self.ready = True
            return None
        if kind == 'end':
            self.ended = True
            if (type(row.get('movement_commands')) is not int or row['movement_commands'] != 0
                    or row.get('errors') != [] or row.get('stopped') is not False):
                raise ValueError('passive collector failed or was interrupted')
            return None
        if kind in self.history:
            if not valid_stamp(row.get('source_ns')) or not valid_stamp(row.get('received_monotonic_ns')):
                raise ValueError('invalid state timestamps')
            names = self.joint_names if kind == 'joints' else RIGHT_HAND
            # PC receipt time and Vision receipt time are different clocks.
            # Preserve the former separately; never subtract across machines.
            velocity = None
            message = row.get('message')
            if kind == 'joints' and isinstance(message, dict) and message.get('velocity'):
                velocity = positions(row, names, 'velocity')
            self.history[kind].append((row['source_ns'], row['received_monotonic_ns'],
                                       positions(row, names), velocity, time.monotonic_ns()))
            return None
        if kind != 'rgb' or not self.ready:
            return None
        image_ns, receipt_ns = row.get('source_ns'), row.get('received_monotonic_ns')
        if not valid_stamp(image_ns) or not valid_stamp(receipt_ns) or image_ns <= self.last_image_source:
            raise ValueError('invalid or non-increasing image timestamp')
        self.last_image_source = image_ns
        selected = {}
        for kind in ('joints', 'hand_right'):
            matches = [r for r in self.history[kind] if
                       0 <= image_ns-r[0] <= MAX_SOURCE_AGE_NS and
                       0 <= receipt_ns-r[1] <= MAX_RECEIPT_AGE_NS]
            if not matches:
                self.dropped += 1
                return None
            selected[kind] = max(matches, key=lambda r: (r[0], r[1]))
        if not isinstance(row.get('png_b64'), str) or not isinstance(row.get('png_sha256'), str):
            raise ValueError('image fields missing')
        raw = base64.b64decode(row['png_b64'], validate=True)
        if (len(raw) < 33 or raw[:8] != b'\x89PNG\r\n\x1a\n' or raw[12:16] != b'IHDR'
                or struct.unpack('!II', raw[16:24]) != (960, 576) or raw[24:26] != b'\x08\x02'
                or hashlib.sha256(raw).hexdigest() != row['png_sha256']):
            raise ValueError('unexpected RGB PNG or checksum')
        j, h = selected['joints'], selected['hand_right']
        self.produced += 1
        return {'schema': 'cruzr_ball_live_observation_v1', 'task': TASK,
                'state_names': self.joint_names + RIGHT_HAND, 'state27': j[2] + h[2],
                'image_source_ns': image_ns, 'joint_source_ns': j[0], 'hand_source_ns': h[0],
                'image_sha256': row['png_sha256'], 'png_b64': row['png_b64'],
                'received_monotonic_ns': {'image': receipt_ns, 'joint': j[1], 'hand': h[1]},
                'state20_velocity_rad_s': j[3], 'pc_joint_received_monotonic_ns': j[4],
                'remote_image_received_ns': row.get('received_ns'),
                'pc_received_monotonic_ns': time.monotonic_ns()}


def main():
    try:
        profile = json.loads(PROFILE.read_text(encoding='utf-8'))
        pairer = Pairer(profile['joint_names'])
        while True:
            line = sys.stdin.buffer.readline(MAX_LINE + 1)
            if not line:
                break
            if len(line) > MAX_LINE or not line.endswith(b'\n'):
                raise ValueError('oversized or truncated stream line')
            row = json.loads(line)
            result = pairer.accept(row)
            if result is not None:
                print(json.dumps(result, separators=(',', ':'), allow_nan=False), flush=True)
        if not pairer.ended or not pairer.ready or pairer.produced == 0:
            raise ValueError('collector ended without complete usable stream')
        print(f'OBSERVATIONS={pairer.produced} DROPPED={pairer.dropped}; no commands', file=sys.stderr)
        return 0
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as exc:
        print(f'OBSERVATION_STREAM_ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
