#!/usr/bin/env python3
"""Supervised PC launcher for one native wrist probe.

--check delegates to the integrated passive test. --run requires the isolated
verified loader and current operator confirmation. The remote launcher has not
been validated on the robot and cannot certify physical STOP.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shlex
import subprocess
import sys
import time
import uuid

import check_arm_native_bridge_live as passive
import run_head_from_pico_supervised as head
import pico_wrist_pc_heartbeat as heartbeat
import pico_wrist_verified_stream as verified_stream
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
        'pico_wrist_trial_admission': VLA/'pico_wrist_trial_admission.py',
        'pico_wrist_native_coordinator': RUNTIME/'pico_wrist_native_coordinator.py',
        'pico_wrist_pc_heartbeat': VLA/'pico_wrist_pc_heartbeat.py',
        'pico_wrist_verified_stream': VLA/'pico_wrist_verified_stream.py',
        'pico_wrist_docker_launcher': RUNTIME/'pico_wrist_docker_launcher.py',
    }
    sources = {name: (path.read_bytes().decode('utf-8'), str(path)) for name, path in paths.items()}
    guard = passive.module_code({n: sources[n] for n in
        ('metamove_head_probe', 'head_from_pico_readonly', 'arm_from_pico_supervised')})
    guard += ('import json\nprint(json.dumps({"event":"BRIDGE_READY"}),flush=True)\n'
              'session=json.loads(sys.stdin.readline())\n'
              'raise SystemExit(sys.modules["arm_from_pico_supervised"].main('
              'session,dry_run=True,monitor_only=True,guard_can_cancel=True,'
              'verified_provenance=globals().get("__pico_verified_stream__")))\n')
    worker = passive.module_code({n: sources[n] for n in (
        'metamove_head_probe', 'head_from_pico_readonly', 'arm_from_pico_supervised',
        'scenario1_request_ids', 'scenario1_action_client', 'prepare_pico_wrist_native_probe',
        'arm_native_lease_bridge', 'pico_wrist_native_stage', 'pico_wrist_native_worker')})
    worker += ('import json,os\nprint(json.dumps({"event":"BRIDGE_READY"}),flush=True)\n'
               'payload=json.loads(sys.stdin.readline())\n'
               'worker=sys.modules["pico_wrist_native_worker"]\n'
               'event_fd=worker.isolate_event_stdout()\n'
               'channel=worker.WorkerChannel(sys.stdin.fileno(),event_fd,payload["session_id"])\n'
               'try:\n rc=worker.run(payload,channel,verified_provenance=globals().get("__pico_verified_stream__"))\n'
               'except BaseException as exc:\n'
               ' channel.emit(event="worker_error",reason=type(exc).__name__+": "+str(exc))\n rc=2\n'
               'channel.emit(event="worker_result",returncode=rc)\n'
               'os.close(event_fd)\nraise SystemExit(rc)\n')
    host = passive.module_code(sources)
    host += ('import json\nprint(json.dumps({"event":"BRIDGE_READY"}),flush=True)\n'
             'payload=json.loads(sys.stdin.readline())\n'
             'print(json.dumps(sys.modules["pico_wrist_docker_launcher"].launch(payload,verified_provenance=globals().get("__pico_verified_stream__")),'
             'allow_nan=False),flush=True)\n')
    if include_sources:
        return host, guard, worker, sources
    return host, guard, worker


def controlled_pc_sources():
    """Snapshot direct project-controlled PC inputs; not the full runtime."""
    paths = {
        'trial_launcher': VLA/'run_pico_wrist_native_trial.py',
        'verified_pc_loader': VLA/'verified_pico_wrist_pc_loader.py',
        'review_binding': VLA/'pico_wrist_review_binding.py',
        'full_passive_check': VLA/'check_pico_wrist_full_passive.py',
        'bridge_check': VLA/'check_arm_native_bridge_live.py',
        'arm_preflight': VLA/'check_arm_from_pico_supervised.py',
        'head_launcher': VLA/'run_head_from_pico_supervised.py',
        'head_admission': VLA/'head_from_pico_check.py',
        'estop_reader': ROOT/'scripts/collect_estop_available_readonly.py',
        'pico_cc_mode': ROOT/'scripts/teleoperation/pico_cc_mode.py',
        'askpass_script': ROOT/'scripts/cruzr_recover_to_home.sh',
    }
    return {name: (path.read_bytes(), str(path)) for name, path in paths.items()}


def retain_bundle_evidence(outdir, sources, host, guard, worker, manifest_raw, urdf_raw, transmissions_raw,
                           *, pc_sources=None):
    """Retain exact in-memory input bytes before handoff; no review is implied."""
    artifacts = {'bundle-host.py':host.encode(), 'bundle-guard.py':guard.encode(),
                 'bundle-worker.py':worker.encode(), 'manifest.json':manifest_raw,
                 'robot.urdf':urdf_raw, 'transmissions.yaml':transmissions_raw}
    for name, (source, _) in sources.items():
        if not name.isidentifier(): raise ValueError('invalid_source_name')
        artifacts['source-'+name+'.py'] = source.encode('utf-8')
    pc_sources = pc_sources or {}
    for name, (source, _) in pc_sources.items():
        if not name.isidentifier() or not isinstance(source, bytes): raise ValueError('invalid_pc_source')
        artifacts['pc-source-'+name] = source
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
        'pc_source_origins':{name:path for name, (_, path) in pc_sources.items()},
        'sha256':index, 'review_status':'not_reviewed',
        'coverage':'controlled_sources_only_runtime_and_loaded_code_not_attested'},
        sort_keys=True, indent=2)+'\n').encode()
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


def host_command(sentinel, *, verified=None):
    if verified is None:
        # The existing passive path does not dispatch or start the worker.
        bootstrap = ('import sys\nparts=[]\nfor line in sys.stdin:\n'
                     ' if line=='+repr(sentinel+'\n')+': break\n'
                     ' parts.append(line)\n'
                     'else: raise SystemExit("incomplete source")\n'
                     'exec(compile("".join(parts),"<pico-host>","exec"))\n')
    else:
        bootstrap = verified_stream.build_bootstrap(
            verified['source_size'], sentinel, verified['source_sha256'],
            verified['payload_sha256'], verified['session_id'], role='host')
    remote = ['python3', '-B', '-u', '-c', bootstrap]
    return ['setsid', '-w', 'ssh', '-T', '-o', 'StrictHostKeyChecking=yes',
            '-o', 'ConnectTimeout=5', '-o', 'TCPKeepAlive=yes',
            '-o', 'PreferredAuthentications=password', '-o', 'PubkeyAuthentication=no',
            '-o', 'NumberOfPasswordPrompts=1', 'walker@192.168.11.2', shlex.join(remote)]


class HostStartUncertain(RuntimeError):
    """Keep the exact host process when bootstrap delivery is uncertain."""
    def __init__(self, process, phase, cause, *, source_may_have_executed,
                 local_cleanup_observed=False):
        self.process = process
        self.phase = phase
        self.source_may_have_executed = source_may_have_executed
        self.local_cleanup_observed = local_cleanup_observed
        super().__init__('host_start_uncertain:' + phase + ':' + type(cause).__name__)


def start_host_streamed(command, source, sentinel, payload, env):
    """Start one host bootstrap; never signal a potentially active process."""
    if sentinel in source:
        raise ValueError('host_source_sentinel_collision')
    payload_bytes = (json.dumps(payload, allow_nan=False)+'\n').encode()
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, env=env, bufsize=0)
    try:
        # No sentinel has been attempted, so the bootstrap cannot execute the
        # supplied source even if this write completed before an interrupt.
        docker_launch.write_stream(process.stdin.fileno(), (source+'\n').encode(), 10.0)
    except BaseException as exc:
        reaped = False
        try:
            docker_launch._reap_unstarted_bootstrap(process)
            reaped = True
        except BaseException:
            pass
        raise HostStartUncertain(process, 'source', exc, source_may_have_executed=False,
                                 local_cleanup_observed=reaped) from exc
    try:
        # Even a raised write may have delivered the complete sentinel before
        # an interrupt was delivered. Never kill or close this process here.
        docker_launch.write_stream(process.stdin.fileno(), (sentinel+'\n').encode(), 10.0)
    except BaseException as exc:
        raise HostStartUncertain(process, 'sentinel', exc, source_may_have_executed=True) from exc
    try:
        docker_launch.write_stream(process.stdin.fileno(), payload_bytes, 10.0)
    except BaseException as exc:
        raise HostStartUncertain(process, 'payload', exc, source_may_have_executed=True) from exc
    return process


def safe_alert(message):
    try:
        print(message, file=sys.stderr, flush=True)
    except BaseException:
        pass


def observe_uncertain_host(process, outdir, phase):
    """Keep observing the exact SSH process; its exit does not prove a stop."""
    safe_alert('ALERTA: entrega al host incierta; supervise el robot. No reintente ni envíe HOME.')
    streams = {}
    for stream, label in ((process.stdout, 'stdout'), (process.stderr, 'stderr')):
        while stream is not None:
            try:
                os.set_blocking(stream.fileno(), False)
                streams[stream] = label
                break
            except KeyboardInterrupt:
                safe_alert('ALERTA: continúa la preparación de observación; estado incierto.')
            except (OSError, ValueError):
                safe_alert('ALERTA: canal '+label+' no observable; estado incierto.')
                break
    last_notice = float('-inf')
    logs = {}
    opened = []
    for label in ('stdout', 'stderr'):
        while True:
            try:
                logs[label] = (outdir/('uncertain-host-'+label+'.log')).open('x', encoding='utf-8')
                opened.append(logs[label])
                break
            except KeyboardInterrupt:
                safe_alert('ALERTA: continúa la preparación de observación; estado incierto.')
            except OSError:
                logs[label] = None
                safe_alert('ALERTA: no se pudo guardar '+label+'; la observación continúa.')
                break
    while True:
            try:
                if not streams and process.poll() is not None:
                    break
                for stream, label in list(streams.items()):
                    try:
                        block = os.read(stream.fileno(), 65536)
                    except BlockingIOError:
                        continue
                    except (OSError, ValueError):
                        streams.pop(stream, None)
                        continue
                    if not block:
                        streams.pop(stream, None)
                        continue
                    target = logs[label]
                    if target is not None:
                        try:
                            target.write(block.decode('utf-8', 'replace')); target.flush()
                        except (OSError, ValueError):
                            logs[label] = None
                            safe_alert('ALERTA: fallo al guardar '+label+'; la observación continúa.')
                now = time.monotonic()
                if process.poll() is None and now-last_notice >= 5:
                    safe_alert('ALERTA: host todavía en observación ('+phase+'); estado físico incierto.')
                    last_notice = now
                time.sleep(.1)
            except (KeyboardInterrupt, OSError):
                safe_alert('ALERTA: continúa la observación; no reintente ni envíe HOME.')
    for log in opened:
        try: log.close()
        except (OSError, ValueError, KeyboardInterrupt):
            safe_alert('ALERTA: fallo al cerrar log; estado físico incierto.')
    raise RuntimeError('host_delivery_uncertain_no_retry_physical_stop_unconfirmed')


def verify_candidate_binding(binding_path, binding_sha256, manifest_raw, urdf_raw, transmissions_raw,
                             *, source_snapshot=None, pc_snapshot=None):
    """Compare exact candidate inputs with a retained review; never authorize motion."""
    if binding_path is None or binding_sha256 is None:
        raise ValueError('binding_and_binding_sha256_required')
    # Local import avoids a module-import cycle: the binding utility calls the
    # launcher's source snapshot helpers but never dispatches a robot goal.
    import pico_wrist_review_binding as binding
    return binding.compare_candidate_inputs(binding_path, binding_sha256, manifest_raw,
        urdf_raw, transmissions_raw, source_snapshot=source_snapshot, pc_snapshot=pc_snapshot)


class SuccessEvidence:
    """Validate the coordinator's ordered success evidence for this session."""
    def __init__(self, session):
        self.session = session
        self.phase = 0
        self.goal_id = None

    def accept(self, row):
        event = row.get('event')
        if event == 'stage_receipt':
            if self.phase != 0 or row.get('session_id') != self.session:
                raise RuntimeError('invalid_stage_sequence')
            self.phase = 1
        elif event == 'uuid_request':
            goal = row.get('goal_id')
            if (self.phase != 1 or row.get('session_id') != self.session or
                    not isinstance(goal, str) or not re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', goal)):
                raise RuntimeError('invalid_uuid_sequence')
            self.goal_id = goal; self.phase = 2
        elif event in ('dispatched', 'accepted', 'result'):
            expected = {'dispatched': 2, 'accepted': 3, 'result': 4}[event]
            if self.phase != expected or row.get('goal_id') != self.goal_id:
                raise RuntimeError('invalid_action_sequence')
            if event == 'accepted' and row.get('accepted') is not True:
                raise RuntimeError('invalid_action_acceptance')
            if event == 'result':
                result = row.get('result')
                state = result.get('state') if isinstance(result, dict) else None
                if row.get('status') != 4 or not isinstance(state, dict) or state.get('desc') != 'SUCCEED' or state.get('state') != 1101001:
                    raise RuntimeError('invalid_action_result')
            self.phase += 1
        elif event == 'worker_finished':
            if self.phase != 5 or row.get('session_id') != self.session:
                raise RuntimeError('invalid_worker_finished')
            self.phase = 6
        elif event == 'worker_result':
            if self.phase != 6 or type(row.get('returncode')) is not int or row['returncode'] != 0:
                raise RuntimeError('invalid_worker_result')
            self.phase = 7
        elif event == 'postflight_settled':
            if self.phase != 7 or row.get('physical_stop_verified') is not False:
                raise RuntimeError('invalid_postflight')
            self.phase = 8
        elif row.get('status') == 'ACTION_SUCCEEDED_AND_POSTFLIGHT_OBSERVED':
            if self.phase != 8 or row.get('goal_id') != self.goal_id or row.get('physical_stop_verified') is not False:
                raise RuntimeError('invalid_terminal_success')
            self.phase = 9
        elif event in ('feedback', 'status', 'result_pending'):
            if self.phase not in (3, 4) or row.get('goal_id') != self.goal_id:
                raise RuntimeError('invalid_intermediate_action_event')



def run_candidate(manifest_path, urdf_path, transmissions_path, physical_confirmed,
                  *, binding_path=None, binding_sha256=None, verified_pc=None):
    # Only the isolated loader that imported this module from verified bytes
    # may use this one-wrist path. This is not a VLA control authorization.
    if (not isinstance(verified_pc, dict) or set(verified_pc) != {'finder','files','index_raw','binding_raw'}
            or verified_pc['finder'] is not globals().get('__loader__')):
        arm.physical_release_gate()
        raise RuntimeError('verified_pc_context_required')
    finder = verified_pc['finder']
    try:
        retained = finder.verified_artifacts
        candidate_code = finder.modules['run_pico_wrist_native_trial'][0]
        bound_entrypoint = any(item is run_candidate.__code__ for item in candidate_code.co_consts)
        same_artifacts = (len(retained) == 3 and retained[0] is verified_pc['files'] and
                          retained[1] is verified_pc['index_raw'] and retained[2] is verified_pc['binding_raw'])
    except (AttributeError, KeyError, TypeError):
        bound_entrypoint = same_artifacts = False
    if (not sys.flags.isolated or finder not in sys.meta_path or not bound_entrypoint or not same_artifacts):
        raise RuntimeError('verified_pc_context_required')
    if physical_confirmed is not True:
        raise RuntimeError('current_physical_confirmation_required')
    files = verified_pc['files']
    manifest_raw, urdf_raw, transmissions_raw = (files['manifest.json'], files['robot.urdf'],
                                                 files['transmissions.yaml'])
    manifest = json.loads(manifest_raw)
    urdf = urdf_raw.decode('utf-8')
    transmissions = transmissions_raw.decode('utf-8')
    probe.validate(manifest, urdf, transmissions)
    source_snapshot = source_bundle(include_sources=True)
    pc_sources = controlled_pc_sources()
    bound = verify_candidate_binding(binding_path, binding_sha256, manifest_raw, urdf_raw,
                                     transmissions_raw, source_snapshot=source_snapshot,
                                     pc_snapshot=pc_sources)
    # Re-read and authenticate the same index bytes before using the expected
    # digests; a later file replacement cannot choose the transmitted source.
    index_raw = verified_pc['index_raw']
    if hashlib.sha256(index_raw).hexdigest() != bound['bundle_evidence_sha256']:
        raise ValueError('bundle_evidence_index_changed_during_handoff')
    binding_hashes = json.loads(index_raw)['sha256']
    if hashlib.sha256(verified_pc['binding_raw']).hexdigest() != binding_sha256:
        raise ValueError('verified_pc_binding_mismatch')
    EVIDENCE.mkdir(mode=0o700, parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    outdir = EVIDENCE/('run-'+token); outdir.mkdir(mode=0o700)
    fd = os.open(EVIDENCE, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)
    host, guard, worker, sources = source_snapshot
    evidence_digest = retain_bundle_evidence(outdir, sources, host, guard, worker,
                                             manifest_raw, urdf_raw, transmissions_raw,
                                             pc_sources=pc_sources)
    mode, started, _ = passive.existing.preflight()
    session = {'schema':'cruzr_head_pico_preflight_v1', 'task_sha256':passive.existing.ARM_TASK_SHA,
               'pico_sha256':head.admission.PICO_SHA, 'work_mode':mode,
               'operator_confirmed':False, 'controller_status_writers_checked':True,
               'age_at_handoff_s':time.monotonic()-started, 'session_id':token, 'mode':'check'}
    payload = {'session':session, 'manifest':manifest, 'urdf_text':urdf,
               'transmissions_text':transmissions, 'guard_source':guard,
               'worker_source':worker, 'operator_confirmed':True,
               'source_digests': {'guard': binding_hashes['bundle-guard.py'],
                                  'worker': binding_hashes['bundle-worker.py']}}
    sentinel = 'PICO_HOST_END_' + uuid.uuid4().hex
    if sentinel in host: raise RuntimeError('host_source_sentinel_collision')
    env = dict(os.environ, CRUZR_INTERNAL_ASKPASS='1', SSH_ASKPASS=str(ROOT/'scripts/cruzr_recover_to_home.sh'),
               SSH_ASKPASS_REQUIRE='force', DISPLAY=os.environ.get('DISPLAY', ':0'))
    verify_bundle_evidence(outdir, evidence_digest)
    # Hashes cover project bytes only; they do not attest external libraries,
    # physical clearance, robot runtime or braking.
    if hashlib.sha256(host.encode('utf-8')).hexdigest() != binding_hashes['bundle-host.py']:
        raise ValueError('reviewed_host_source_mismatch')
    encoded_payload = json.dumps(payload, allow_nan=False).encode('utf-8')
    verified_host = {'source_size':len(host.encode('utf-8')),
                     'source_sha256':binding_hashes['bundle-host.py'],
                     'payload_sha256':hashlib.sha256(encoded_payload).hexdigest(),
                     'session_id':token}
    try:
        process = start_host_streamed(host_command(sentinel, verified=verified_host), host, sentinel, payload, env)
    except HostStartUncertain as exc:
        if exc.source_may_have_executed or not exc.local_cleanup_observed:
            observe_uncertain_host(exc.process, outdir, exc.phase)
        raise RuntimeError('host_bootstrap_not_started_no_retry') from exc
    return supervise_started_host(process, token, started, outdir)


def supervise_started_host(process, token, started, outdir):
    """Supervise an existing host; retain observation on any unexpected failure."""
    selector = None
    pump = None; preflight_ack = False; heartbeat_started = False; buffer = bytearray()
    final = None; alerted = False
    evidence = SuccessEvidence(token)
    try:
        selector = selectors.DefaultSelector()
        for stream, label in ((process.stdout, 'stdout'), (process.stderr, 'stderr')):
            os.set_blocking(stream.fileno(), False); selector.register(stream, selectors.EVENT_READ, label)
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
                        else:
                            evidence.accept(row)
                            if row.get('status') == 'ACTION_SUCCEEDED_AND_POSTFLIGHT_OBSERVED':
                                final = row
                        if event not in ('BRIDGE_READY', 'pc_ping'):
                            print(json.dumps(row, ensure_ascii=False), flush=True)
        code = process.wait()
        if (code != 0 or final is None or evidence.phase != 9 or alerted or not heartbeat_started or
                final.get('physical_stop_verified') is not False):
            raise RuntimeError('trial_result_uncertain_or_unsuccessful:' + str(outdir))
        return final
    except BaseException as exc:
        # Stop renewal first; if the host could have received a goal, retain
        # the same process and keep observing rather than silently abandoning it.
        if pump is not None:
            try: pump.close()
            except BaseException: safe_alert('ALERTA: fallo al detener latido; estado incierto.')
            pump = None
        if selector is not None:
            try: selector.close()
            except BaseException: safe_alert('ALERTA: fallo al cerrar selector; estado incierto.')
            selector = None
        safe_alert('ALERTA: supervisión PC interrumpida ('+type(exc).__name__+'); resultado físico incierto.')
        return observe_uncertain_host(process, outdir, 'runtime')
    finally:
        if pump is not None: pump.close()
        if selector is not None: selector.close()
        # Never signal or mistake a host exit for physical stopping.



def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true')
    group.add_argument('--run', action='store_true')
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--urdf', type=Path)
    parser.add_argument('--transmissions', type=Path)
    parser.add_argument('--binding', type=Path,
                        help='optional local technical-review binding for --check; required for a future run')
    parser.add_argument('--binding-sha256', help='recorded digest of that binding')
    parser.add_argument('--physical-confirmed', action='store_true',
                        help='current operator-reported physical conditions; other checks remain required')
    args = parser.parse_args(argv)
    if args.run:
        try:
            result = run_candidate(args.manifest, args.urdf, args.transmissions, args.physical_confirmed,
                                   binding_path=args.binding, binding_sha256=args.binding_sha256)
            print(json.dumps(result, ensure_ascii=False, allow_nan=False))
            return 0
        except (RuntimeError, OSError, ValueError, TypeError, subprocess.SubprocessError) as exc:
            print('TRIAL_BLOCKED_OR_FAILED: ' + str(exc), file=sys.stderr)
            return 2
    if args.physical_confirmed:
        parser.error('--physical-confirmed is only supported with --run')
    if args.binding is not None or args.binding_sha256 is not None:
        try:
            if any(value is None for value in (args.binding, args.binding_sha256,
                                               args.manifest, args.urdf, args.transmissions)):
                raise ValueError('binding_digest_and_all_candidate_inputs_required')
            result = verify_candidate_binding(args.binding, args.binding_sha256,
                args.manifest.read_bytes(), args.urdf.read_bytes(), args.transmissions.read_bytes())
            print(json.dumps({'status': 'BINDING_BYTES_MATCH',
                              'binding_sha256': result['binding_sha256'],
                              'physical_control_qualified': False,
                              'movement_commands': 0}, ensure_ascii=False, allow_nan=False), flush=True)
        except (OSError, RuntimeError, ValueError, TypeError, KeyError) as exc:
            print('BINDING_CHECK_FAILED: ' + str(exc), file=sys.stderr)
            return 1
    parameters = ['--check']
    for option, value in (('--manifest', args.manifest), ('--urdf', args.urdf),
                          ('--transmissions', args.transmissions)):
        if value is not None:
            parameters.extend((option, str(value)))
    # Delayed import avoids the full check's intentional reference to this
    # launcher's host bootstrap helpers. It never creates an action goal.
    import check_pico_wrist_full_passive as full_passive
    return full_passive.main(parameters)


if __name__ == '__main__':
    raise SystemExit(main())
