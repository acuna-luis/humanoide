#!/usr/bin/env python3
"""Relay a bounded passive Vision stream to an isolated SmolVLA runner.

No ROS publisher or robot control client is created. Observations are dropped
when inference is busy; a partial write is never silently spliced into another
record. Run from a trusted PC with a separately staged, pinned server runner.
"""
import argparse
import base64
import collections
import json
import math
import os
from pathlib import Path
import re
import selectors
import shlex
import signal
import subprocess
import sys
import time

from ball_arm_preview_guard import BODY_NAMES, named_values

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MAX_LINE = 12 * 1024 * 1024
MAX_PENDING_SECONDS = 2.0
MAX_COLLECTOR_UPLOAD_SECONDS = 12.0
MODEL_SHA256 = 'e707eea07b58e14b979e78463b94ba75a52b1c18abf8076aebc8aa34ac77f8da'


def line_buffer(buffers, key, block):
    buffer = buffers.setdefault(key, bytearray())
    buffer.extend(block)
    lines = []
    while b'\n' in buffer:
        line, _, remainder = buffer.partition(b'\n')
        buffer[:] = remainder
        if len(line) > MAX_LINE:
            raise ValueError('unbounded stream record')
        lines.append(line)
    if len(buffer) > MAX_LINE:
        raise ValueError('unbounded stream record')
    return lines


def emit(row):
    print(json.dumps(row, allow_nan=False, separators=(',', ':')), flush=True)


def observation_state(row):
    """Extract paired state without images; it carries no motion authority.

    The PC monotonic stamp records when the adapter consumed the joint record;
    it does not measure Vision-to-PC transport latency or synchronize clocks.
    Old observation producers may omit these fields and remain shadow-only.
    """
    new_fields = {'pc_joint_received_monotonic_ns', 'state20_velocity_rad_s'}
    present = new_fields.intersection(row)
    if not present:
        return None
    if present != new_fields:
        raise ValueError('paired_state_metadata_incomplete')
    names, values = row.get('state_names'), row.get('state27')
    stamp, velocity = row.get('pc_joint_received_monotonic_ns'), row.get('state20_velocity_rad_s')
    if (not isinstance(names, list) or len(names) != 27 or any(not isinstance(n, str) for n in names)
            or set(names[:20]) != set(BODY_NAMES)
            or len(set(names)) != 27 or not isinstance(values, list) or len(values) != 27
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in values)
            or type(stamp) is not int or stamp <= 0 or stamp > time.monotonic_ns()):
        raise ValueError('paired_state_invalid')
    if velocity is not None:
        named_values(names[:20], values[:20], velocity)
    return {'names': names[:20], 'positions': values[:20], 'velocities': velocity,
            'received_monotonic_ns': stamp}


def expected_model_sha256(args):
    """Hash del modelo esperado: el del piloto o el de --pins-file."""
    if getattr(args, 'pins_file', None):
        return json.loads(Path(args.pins_file).read_text(encoding='utf-8'))['checkpoint_files']['model.safetensors']
    return MODEL_SHA256


def server_command(args):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+@[A-Za-z0-9_.-]+', args.host):
        raise ValueError('host must be user@host without shell characters')
    paths = (args.runner, args.train, args.checkpoint)
    if any(not p.startswith('/') or '\n' in p or '\0' in p for p in paths):
        raise ValueError('remote runner and inputs must be absolute paths')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', args.volume):
        raise ValueError('invalid volume')
    remote = ['bash', args.runner, args.train, args.volume, args.checkpoint,
              args.device, str(args.seed), str(args.max_samples)]
    if getattr(args, 'pins_file', None):
        pins = json.loads(Path(args.pins_file).read_text(encoding='utf-8'))
        remote.append(base64.b64encode(json.dumps(pins, sort_keys=True).encode()).decode())
    return ['ssh', '-T', '-p', str(args.port), '-o', 'BatchMode=yes',
            '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=8',
            '-o', 'ServerAliveInterval=5', '-o', 'ServerAliveCountMax=2',
            args.host, shlex.join(remote)]


def discover_vision():
    sys.path.insert(0, str(ROOT / 'scripts'))
    from collect_estop_available_readonly import execute
    result = execute('vision', ['docker', 'ps', '--format', '{{.Names}}|{{.Image}}'])
    if result.get('returncode') != 0:
        raise RuntimeError('Vision container discovery failed')
    names = [line.split('|', 1)[0] for line in result.get('stdout', '').splitlines()
             if line.split('|', 1)[0].startswith('walker-ros.')
             and line.split('|', 1)[0].endswith('ros2-1')]
    if len(names) != 1 or not re.fullmatch(r'[A-Za-z0-9_.-]+', names[0]):
        raise RuntimeError('Vision ROS container not uniquely discovered')
    return names[0]


def collector_command(container, seconds, fps):
    shell = ('source /opt/ros/humble/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; '
             f'exec timeout --signal=TERM --kill-after=2s {seconds + 25}s '
             'python3 -B -u - ' + shlex.join(['--seconds', str(seconds),
                                               '--fps', str(fps), '--telemetry-hz', '30']))
    remote = ['docker', 'exec', '-i', container, 'bash', '-lc', shell]
    return ['ssh', '-T', '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=5',
            '-o', 'ConnectionAttempts=1', '-o', 'ServerAliveInterval=5',
            '-o', 'ServerAliveCountMax=2', '-o', 'PreferredAuthentications=password',
            '-o', 'PubkeyAuthentication=no', '-o', 'NumberOfPasswordPrompts=1',
            'walker@192.168.11.3', shlex.join(remote)]


def cleanup(process):
    if process is None:
        return
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)
    for stream in (process.stdin, process.stdout, process.stderr):
        if stream is not None and not stream.closed:
            stream.close()


def run(args):
    one_shot = getattr(args, 'one_shot', False)
    container = discover_vision()
    server = subprocess.Popen(server_command(args), stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
    source = adapter = None
    selector = selectors.DefaultSelector()
    buffers = {}
    ready = False
    sent = dropped = predictions = 0
    # One record being written and one latest waiting: no growing queue.
    current = pending = None
    collector_source = None
    sent_times = collections.OrderedDict()
    last_image_source_ns = 0
    started_capture = False
    end_seen = False
    finished_input = False
    deadline = time.monotonic() + args.startup_timeout
    try:
        for stream, tag in ((server.stdout, 'server'), (server.stderr, 'server_err')):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, tag)
        while True:
            now = time.monotonic()
            if now > deadline:
                raise TimeoutError('model startup or bounded capture/inference deadline exceeded')
            if current and now - current['arrived'] > MAX_PENDING_SECONDS:
                raise TimeoutError('observation stalled while being sent to model')
            if collector_source and now - collector_source['started'] > MAX_COLLECTOR_UPLOAD_SECONDS:
                raise TimeoutError('collector source upload stalled')
            if pending and now - pending['arrived'] > MAX_PENDING_SECONDS:
                pending = None
                dropped += 1
            if current is None and pending is not None:
                current, pending = pending, None
            if current is not None and not any(k.data == 'model_input' for k in selector.get_map().values()):
                os.set_blocking(server.stdin.fileno(), False)
                selector.register(server.stdin, selectors.EVENT_WRITE, 'model_input')
            if ((finished_input or (one_shot and sent == 1)) and current is None
                    and pending is None and not server.stdin.closed):
                server.stdin.close()
            if server.poll() is not None:
                if ready and not finished_input and not (one_shot and sent == 1):
                    raise RuntimeError('model exited before passive capture completed')
                if not selector.get_map():
                    break
            for key, _ in selector.select(.1):
                tag = key.data
                if tag == 'collector_input':
                    try:
                        count = os.write(key.fd, collector_source['bytes'][collector_source['offset']:])
                    except BrokenPipeError as exc:
                        raise RuntimeError('collector closed source input early') from exc
                    collector_source['offset'] += count
                    if collector_source['offset'] == len(collector_source['bytes']):
                        selector.unregister(key.fileobj)
                        source.stdin.close()
                        collector_source = None
                    continue
                if tag == 'model_input':
                    try:
                        count = os.write(key.fd, current['bytes'][current['offset']:])
                    except BrokenPipeError as exc:
                        raise RuntimeError('model closed input early') from exc
                    current['offset'] += count
                    if current['offset'] == len(current['bytes']):
                        sent_times[(current['image_sha256'], current['image_source_ns'])] = {
                            'arrived': current['arrived'], 'state': current['state']}
                        while len(sent_times) > 128:
                            sent_times.popitem(last=False)
                        sent += 1
                        current = None
                        selector.unregister(key.fileobj)
                    continue
                block = os.read(key.fd, 65536)
                if not block:
                    selector.unregister(key.fileobj)
                    if buffers.get(tag):
                        raise ValueError(f'truncated {tag} record')
                    if tag == 'adapter':
                        finished_input = True
                    continue
                if tag.endswith('_err'):
                    # Drain stderr without leaking image payloads or unbounded output.
                    print(f'{tag}: {block.decode("utf-8", "replace")[:2048]}', file=sys.stderr, flush=True)
                    continue
                for line in line_buffer(buffers, tag, block):
                    row = json.loads(line)
                    if tag == 'server':
                        event = row.get('event')
                        if event == 'ready':
                            if (ready or row.get('schema') != 'cruzr_ball_live_shadow_v1'
                                    or row.get('physical_control_qualified') is not False
                                    or row.get('model_sha256') != expected_model_sha256(args)):
                                raise ValueError('unexpected or duplicate model readiness')
                            ready = True
                            emit({'event': 'model_ready', 'model_sha256': row['model_sha256'],
                                  'physical_control_qualified': False, 'movement_commands': 0})
                            env = dict(os.environ, CRUZR_INTERNAL_ASKPASS='1',
                                       SSH_ASKPASS=str(ROOT / 'scripts/cruzr_recover_to_home.sh'),
                                       SSH_ASKPASS_REQUIRE='force', DISPLAY=os.environ.get('DISPLAY', ':0'))
                            source = subprocess.Popen(collector_command(container, args.seconds, args.fps),
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, bufsize=0)
                            # La instrucción la fija el dataset del modelo cargado (evento ready);
                            # sin ella (servidor del piloto) el adaptador usa la del piloto.
                            adapter_env = dict(os.environ)
                            if isinstance(row.get('task'), str) and row['task'].strip():
                                adapter_env['CRUZR_SVLA_TASK'] = row['task']
                            adapter = subprocess.Popen([sys.executable, '-B', '-u', str(HERE / 'live_ball_observation_adapter.py')],
                                stdin=source.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0,
                                env=adapter_env)
                            source.stdout.close()
                            collector_source = {'bytes': (HERE / 'passive_episode_remote.py').read_bytes(),
                                                'offset': 0, 'started': time.monotonic()}
                            if not collector_source['bytes']:
                                raise ValueError('empty collector source')
                            os.set_blocking(source.stdin.fileno(), False)
                            selector.register(source.stdin, selectors.EVENT_WRITE, 'collector_input')
                            for stream, name in ((adapter.stdout, 'adapter'), (adapter.stderr, 'adapter_err'),
                                                 (source.stderr, 'collector_err')):
                                os.set_blocking(stream.fileno(), False)
                                selector.register(stream, selectors.EVENT_READ, name)
                            started_capture = True
                            deadline = time.monotonic() + args.seconds + 60
                        elif event == 'prediction':
                            if row.get('physical_control_qualified') is not False:
                                raise ValueError('unexpected prediction qualification')
                            for name, length in (('prediction', 8), ('proposed_minus_observed_rad', 7)):
                                values = row.get(name)
                                if (not isinstance(values, list) or len(values) != length or
                                        any(type(x) not in (float, int) or not math.isfinite(x) for x in values)):
                                    raise ValueError('invalid prediction values')
                            predictions += 1
                            image_hash = row.get('image_sha256')
                            sent_observation = sent_times.pop((image_hash, row.get('image_source_ns')), None)
                            if sent_observation is None:
                                raise ValueError('prediction does not match a sent observation')
                            now_ns = time.monotonic_ns()
                            row['pc_adapter_to_prediction_seconds'] = round(now_ns / 1e9 - sent_observation['arrived'], 6)
                            if sent_observation['state'] is not None:
                                row['paired_state20'] = sent_observation['state']
                                row['prediction_received_monotonic_ns'] = now_ns
                            emit(row)
                        elif event == 'done':
                            if row.get('physical_control_qualified') is not False or row.get('samples') != predictions:
                                raise ValueError('model completion count/qualification mismatch')
                            end_seen = True
                            emit(row)
                        else:
                            raise ValueError('unexpected model event')
                    elif tag == 'adapter':
                        if not ready or row.get('schema') != 'cruzr_ball_live_observation_v1':
                            raise ValueError('unexpected observation')
                        image_hash = row.get('image_sha256')
                        if not isinstance(image_hash, str) or not re.fullmatch('[0-9a-f]{64}', image_hash):
                            raise ValueError('observation without valid image hash')
                        image_source_ns = row.get('image_source_ns')
                        if type(image_source_ns) is not int or image_source_ns <= 0:
                            raise ValueError('observation without valid source timestamp')
                        # The adapter normally enforces monotonic stamps, but
                        # validate again at this trust boundary. This prevents
                        # reusing a correlation key even after a prediction
                        # has been consumed or an observation was dropped.
                        if image_source_ns <= last_image_source_ns:
                            raise ValueError('duplicate_or_non_increasing_observation_identity')
                        last_image_source_ns = image_source_ns
                        received_pc_ns = row.get('pc_received_monotonic_ns')
                        if type(received_pc_ns) is not int or not 0 < received_pc_ns <= time.monotonic_ns():
                            raise ValueError('observation without valid PC receipt timestamp')
                        if one_shot and (sent or current is not None):
                            dropped += 1
                            continue
                        if pending is not None:
                            dropped += 1
                        pending = {'bytes': line + b'\n', 'offset': 0, 'state': observation_state(row),
                                   'arrived': received_pc_ns / 1e9, 'image_sha256': image_hash,
                                   'image_source_ns': image_source_ns}
        if not ready or not started_capture or source.wait(timeout=2) != 0 or adapter.wait(timeout=2) != 0:
            raise RuntimeError('capture or adapter did not complete successfully')
        if server.returncode != 0 or not end_seen or not predictions or sent != predictions or sent_times:
            raise RuntimeError('model did not complete with predictions')
        emit({'event': 'summary', 'observations_sent': sent, 'observations_dropped': dropped,
              'predictions': predictions, 'movement_commands': 0,
              'latency_note': 'PC adapter creation to PC prediction receipt, excludes transport from Vision; clocks not synchronized'})
    finally:
        selector.close()
        for process in (adapter, source, server):
            cleanup(process)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for option in ('host', 'runner', 'train', 'volume', 'checkpoint'):
        p.add_argument('--' + option, required=True)
    p.add_argument('--port', type=int, default=2649)
    p.add_argument('--device', choices=('cpu', 'cuda'), default='cuda')
    p.add_argument('--seed', type=int, default=20261109)
    p.add_argument('--seconds', type=int, default=20)
    p.add_argument('--fps', type=float, default=.5)
    p.add_argument('--max-samples', type=int, default=100)
    p.add_argument('--one-shot', action='store_true',
                   help='send at most one observation and drain capture before summary')
    p.add_argument('--startup-timeout', type=int, default=120)
    p.add_argument('--pins-file', help='JSON local con hashes esperados de un checkpoint distinto del piloto')
    args = p.parse_args()
    if not (1 <= args.port <= 65535 and 1 <= args.seconds <= 240 and .5 <= args.fps <= 2
            and ((args.one_shot and args.max_samples == 1) or
                 (not args.one_shot and math.ceil(args.seconds * args.fps) + 4 <= args.max_samples <= 1000))
            and 1 <= args.startup_timeout <= 120
            and 0 <= args.seed <= 2**31 - 1):
        p.error('invalid bounded parameters')
    def interrupted(signum, frame):
        raise InterruptedError(f'interrupted by signal {signum}')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        run(args)
    except (OSError, ValueError, RuntimeError, TimeoutError, subprocess.SubprocessError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        print('Capture/runner cleanup requested; verify remote process termination independently.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
