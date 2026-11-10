#!/usr/bin/env python3
"""Candidate PC launcher for one native wrist probe; physical gate is closed.

--check delegates to the passive guard/lease test. --run rejects before any
file or network access. Source bundles are prepared for review only. The remote
launcher has not been validated on the robot and cannot certify physical STOP.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import selectors
import shlex
import subprocess
import sys
import time
import uuid

import check_arm_native_bridge_live as passive
import run_head_from_pico_supervised as head
import pico_wrist_pc_heartbeat as heartbeat
import prepare_pico_wrist_native_probe as probe

ROOT = Path(__file__).resolve().parents[2]
VLA = ROOT/'scripts/vla'
RUNTIME = VLA/'runtime'
BOX = ROOT/'scripts/box_handling'
sys.path.insert(0, str(RUNTIME))
import arm_from_pico_supervised as arm
import pico_wrist_docker_launcher as docker_launch

EVIDENCE = ROOT.parent/'Humanoide-vla-evidence'/'PICO_NATIVE_WRIST_TRIAL'


def source_bundle(*, include_sources=False):
    paths = {
        'metamove_head_probe': RUNTIME/'metamove_head_probe.py',
        'head_from_pico_readonly': RUNTIME/'head_from_pico_readonly.py',
        'arm_from_pico_supervised': RUNTIME/'arm_from_pico_supervised.py',
        'scenario1_request_ids': BOX/'scenario1_request_ids.py',
        'scenario1_action_client': BOX/'scenario1_action_client.py',
        'prepare_pico_wrist_native_probe': VLA/'prepare_pico_wrist_native_probe.py',
        'arm_native_lease_bridge': VLA/'arm_native_lease_bridge.py',
        'pico_wrist_native_stage': RUNTIME/'pico_wrist_native_stage.py',
        'pico_wrist_native_worker': RUNTIME/'pico_wrist_native_worker.py',
        'pico_wrist_native_coordinator': RUNTIME/'pico_wrist_native_coordinator.py',
        'pico_wrist_pc_heartbeat': VLA/'pico_wrist_pc_heartbeat.py',
        'pico_wrist_docker_launcher': RUNTIME/'pico_wrist_docker_launcher.py',
    }
    sources = {name: (path.read_bytes().decode('utf-8'), str(path)) for name, path in paths.items()}
    guard = passive.module_code({n: sources[n] for n in
        ('metamove_head_probe', 'head_from_pico_readonly', 'arm_from_pico_supervised')})
    guard += ('import json\nprint(json.dumps({"event":"BRIDGE_READY"}),flush=True)\n'
              'session=json.loads(sys.stdin.readline())\n'
              'raise SystemExit(sys.modules["arm_from_pico_supervised"].main('
              'session,dry_run=True,monitor_only=True,guard_can_cancel=True))\n')
    worker = passive.module_code({n: sources[n] for n in (
        'metamove_head_probe', 'head_from_pico_readonly', 'arm_from_pico_supervised',
        'scenario1_request_ids', 'scenario1_action_client', 'prepare_pico_wrist_native_probe',
        'arm_native_lease_bridge', 'pico_wrist_native_stage', 'pico_wrist_native_worker')})
    worker += ('import json\nprint(json.dumps({"event":"BRIDGE_READY"}),flush=True)\n'
               'payload=json.loads(sys.stdin.readline())\n'
               'worker=sys.modules["pico_wrist_native_worker"]\n'
               'channel=worker.WorkerChannel(sys.stdin.fileno(),sys.stdout.fileno(),payload["session_id"])\n'
               'try:\n rc=worker.run(payload,channel)\n'
               'except BaseException as exc:\n'
               ' channel.emit(event="worker_error",reason=type(exc).__name__+": "+str(exc))\n rc=2\n'
               'channel.emit(event="worker_result",returncode=rc)\nraise SystemExit(rc)\n')
    host = passive.module_code(sources)
    host += ('import json\nprint(json.dumps({"event":"BRIDGE_READY"}),flush=True)\n'
             'payload=json.loads(sys.stdin.readline())\n'
             'print(json.dumps(sys.modules["pico_wrist_docker_launcher"].launch(payload),'
             'allow_nan=False),flush=True)\n')
    if include_sources:
        return host, guard, worker, sources
    return host, guard, worker


def retain_bundle_evidence(outdir, sources, host, guard, worker, manifest_raw, urdf_raw, transmissions_raw):
    """Retain exact in-memory input bytes before handoff; no review is implied."""
    artifacts = {'bundle-host.py':host.encode(), 'bundle-guard.py':guard.encode(),
                 'bundle-worker.py':worker.encode(), 'manifest.json':manifest_raw,
                 'robot.urdf':urdf_raw, 'transmissions.yaml':transmissions_raw}
    for name, (source, _) in sources.items():
        if not name.isidentifier(): raise ValueError('invalid_source_name')
        artifacts['source-'+name+'.py'] = source.encode('utf-8')
    index = {}
    for name, data in sorted(artifacts.items()):
        path = outdir/name
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC |
                     getattr(os, 'O_NOFOLLOW', 0), 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        if path.read_bytes() != data:
            raise RuntimeError('evidence_readback_mismatch:' + name)
        index[name] = hashlib.sha256(data).hexdigest()
    index_bytes = (json.dumps({'schema':'pico_wrist_bundle_evidence_v1',
        'source_origins':{name:path for name, (_, path) in sources.items()},
        'sha256':index, 'review_attested':False}, sort_keys=True, indent=2)+'\n').encode()
    fd = os.open(outdir/'bundle-evidence.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 os.O_CLOEXEC | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(index_bytes); stream.flush(); os.fsync(stream.fileno())
    if (outdir/'bundle-evidence.json').read_bytes() != index_bytes:
        raise RuntimeError('evidence_index_readback_mismatch')
    fd = os.open(outdir, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)
    return hashlib.sha256(index_bytes).hexdigest()


def verify_bundle_evidence(outdir, index_digest):
    raw = (outdir/'bundle-evidence.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != index_digest:
        raise RuntimeError('bundle_evidence_index_changed')
    index = json.loads(raw)
    for name, expected in index['sha256'].items():
        if Path(name).name != name or hashlib.sha256((outdir/name).read_bytes()).hexdigest() != expected:
            raise RuntimeError('bundle_evidence_changed:' + name)


def host_command(sentinel):
    bootstrap = ('import sys\nparts=[]\nfor line in sys.stdin:\n'
                 ' if line.rstrip("\\n")=='+repr(sentinel)+': break\n'
                 ' parts.append(line)\n'
                 'else: raise SystemExit("incomplete source")\n'
                 'exec(compile("".join(parts),"<pico-host>","exec"))\n')
    remote = ['python3', '-B', '-u', '-c', bootstrap]
    return ['setsid', '-w', 'ssh', '-T', '-o', 'StrictHostKeyChecking=yes',
            '-o', 'ConnectTimeout=5', '-o', 'TCPKeepAlive=yes',
            '-o', 'PreferredAuthentications=password', '-o', 'PubkeyAuthentication=no',
            '-o', 'NumberOfPasswordPrompts=1', 'walker@192.168.11.2', shlex.join(remote)]


def run_candidate(manifest_path, urdf_path, transmissions_path, physical_confirmed):
    # No input, filesystem, process or network operation can precede this gate.
    arm.physical_release_gate()
    if physical_confirmed is not True:
        raise RuntimeError('current_physical_confirmation_required')
    manifest_raw = manifest_path.read_bytes()
    urdf_raw = urdf_path.read_bytes()
    transmissions_raw = transmissions_path.read_bytes()
    manifest = json.loads(manifest_raw)
    urdf = urdf_raw.decode('utf-8')
    transmissions = transmissions_raw.decode('utf-8')
    probe.validate(manifest, urdf, transmissions)
    EVIDENCE.mkdir(mode=0o700, parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    outdir = EVIDENCE/('run-'+token); outdir.mkdir(mode=0o700)
    fd = os.open(EVIDENCE, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)
    host, guard, worker, sources = source_bundle(include_sources=True)
    evidence_digest = retain_bundle_evidence(outdir, sources, host, guard, worker,
                                             manifest_raw, urdf_raw, transmissions_raw)
    mode, started, _ = passive.existing.preflight()
    session = {'schema':'cruzr_head_pico_preflight_v1', 'task_sha256':passive.existing.ARM_TASK_SHA,
               'pico_sha256':head.admission.PICO_SHA, 'work_mode':mode,
               'operator_confirmed':False, 'controller_status_writers_checked':True,
               'age_at_handoff_s':time.monotonic()-started, 'session_id':token, 'mode':'check'}
    payload = {'session':session, 'manifest':manifest, 'urdf_text':urdf,
               'transmissions_text':transmissions, 'guard_source':guard,
               'worker_source':worker, 'operator_confirmed':True}
    sentinel = 'PICO_HOST_END_' + uuid.uuid4().hex
    if sentinel in host: raise RuntimeError('host_source_sentinel_collision')
    env = dict(os.environ, CRUZR_INTERNAL_ASKPASS='1', SSH_ASKPASS=str(ROOT/'scripts/cruzr_recover_to_home.sh'),
               SSH_ASKPASS_REQUIRE='force', DISPLAY=os.environ.get('DISPLAY', ':0'))
    verify_bundle_evidence(outdir, evidence_digest)
    # Evidence retention is not an independent review of these exact bytes.
    # Keep a separate fail-closed gate until a reviewed attestation protocol
    # binds this digest and the complete PC/runtime dependencies.
    raise RuntimeError('reviewed_bundle_attestation_not_implemented')
    process = subprocess.Popen(host_command(sentinel), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, env=env, bufsize=0)
    data = (host+'\n'+sentinel+'\n'+json.dumps(payload, allow_nan=False)+'\n').encode()
    docker_launch.write_stream(process.stdin.fileno(), data, 10.0)
    selector = selectors.DefaultSelector()
    for stream, label in ((process.stdout, 'stdout'), (process.stderr, 'stderr')):
        os.set_blocking(stream.fileno(), False); selector.register(stream, selectors.EVENT_READ, label)
    pump = None; preflight_ack = False; heartbeat_started = False; buffer = bytearray()
    final = None; alerted = False
    try:
        with (outdir/'host-stdout.log').open('x', encoding='utf-8') as stdout, \
             (outdir/'host-stderr.log').open('x', encoding='utf-8') as stderr:
            while selector.get_map():
                try:
                    ready = selector.select(timeout=.1)
                except KeyboardInterrupt:
                    if pump is not None: pump.close()
                    print('ALERTA: latido detenido; supervise el robot. No reintente ni envíe HOME.',
                          file=sys.stderr, flush=True)
                    alerted = True
                    continue
                if pump is not None and pump.failed.is_set() and not alerted:
                    print('ALERTA: latido al host interrumpido; estado físico incierto.',
                          file=sys.stderr, flush=True); alerted = True
                for key, _ in ready:
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj); continue
                    target = stdout if key.data == 'stdout' else stderr
                    target.write(chunk.decode('utf-8','replace')); target.flush()
                    if key.data == 'stderr':
                        sys.stderr.write(chunk.decode('utf-8','replace')); sys.stderr.flush(); continue
                    buffer.extend(chunk)
                    if len(buffer) > 1_000_000: raise RuntimeError('host_output_excessive')
                    while b'\n' in buffer:
                        line, _, rest = bytes(buffer).partition(b'\n'); buffer = bytearray(rest)
                        try: row = json.loads(line)
                        except (ValueError, UnicodeDecodeError): raise RuntimeError('host_output_invalid')
                        if not isinstance(row, dict): raise RuntimeError('host_output_invalid')
                        event = row.get('event')
                        if event == 'HOST_PREFLIGHT_READY':
                            challenge = row.get('challenge')
                            if (preflight_ack or row.get('session_id') != token or not isinstance(challenge,str)
                                    or len(challenge) != 32 or any(c not in '0123456789abcdef' for c in challenge)):
                                raise RuntimeError('host_preflight_challenge_invalid')
                            ack = {'event':'pc_preflight_ack','session_id':token,'challenge':challenge,
                                   'inventory_age_s':time.monotonic()-started}
                            docker_launch.write_stream(process.stdin.fileno(), (json.dumps(ack)+'\n').encode(), 1.0)
                            preflight_ack = True
                        elif event == 'HOST_HEARTBEAT_READY':
                            if not preflight_ack or heartbeat_started or row.get('session_id') != token:
                                raise RuntimeError('host_heartbeat_handoff_invalid')
                            pump = heartbeat.PcHeartbeatPump(process.stdin.fileno(), token)
                            heartbeat_started = True
                        elif event == 'pc_ping':
                            if pump is None:
                                raise RuntimeError('host_challenge_before_heartbeat_ready')
                            pump.submit(row)
                        elif row.get('status') == 'ACTION_SUCCEEDED_AND_POSTFLIGHT_OBSERVED':
                            final = row
                        if event not in ('BRIDGE_READY', 'pc_ping'):
                            print(json.dumps(row, ensure_ascii=False), flush=True)
        code = process.wait()
        if (code != 0 or final is None or alerted or not heartbeat_started or
                final.get('physical_stop_verified') is not False):
            raise RuntimeError('trial_result_uncertain_or_unsuccessful:' + str(outdir))
        return final
    finally:
        if pump is not None: pump.close()
        selector.close()
        # Do not kill a host that may have already accepted a goal. Loss of
        # this PC channel invalidates the heartbeat but does not prove stop.



def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true')
    group.add_argument('--run', action='store_true')
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--urdf', type=Path)
    parser.add_argument('--transmissions', type=Path)
    parser.add_argument('--physical-confirmed', action='store_true',
                        help='operator-reported current physical conditions; never opens the gate')
    args = parser.parse_args(argv)
    if args.run:
        try:
            result = run_candidate(args.manifest, args.urdf, args.transmissions, args.physical_confirmed)
            print(json.dumps(result, ensure_ascii=False, allow_nan=False))
            return 0
        except (RuntimeError, OSError, ValueError, TypeError, subprocess.SubprocessError) as exc:
            print('TRIAL_BLOCKED_OR_FAILED: ' + str(exc), file=sys.stderr)
            return 2
    if args.physical_confirmed:
        parser.error('--physical-confirmed is only supported with --run')
    parameters = ['--check']
    for option, value in (('--manifest', args.manifest), ('--urdf', args.urdf),
                          ('--transmissions', args.transmissions)):
        if value is not None:
            parameters.extend((option, str(value)))
    return passive.main(parameters)


if __name__ == '__main__':
    raise SystemExit(main())
