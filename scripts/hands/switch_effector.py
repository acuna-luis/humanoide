#!/usr/bin/env python3
"""Bidirectional, supervised clamp/v4 profile switch. Default is read-only --check."""
import argparse
import ast
import base64
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tarfile
import time
import threading
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.collect_estop_available_readonly import HOSTS
from scripts.hands.effector_profile_config import PROFILES, GUARD_SHA, ENI_SHA, plan_files
from scripts.hands.prepare_v4_bus_profile import SOURCE_SHA256
from scripts.lib.cruzr_home_posture_gate import classify
from scripts.teleoperation.check_pico_v4_hand_states import validate as validate_hand


class Transport:
    def __init__(self, evidence):
        self.evidence = evidence
        self.sequence = 0
        self.lock = threading.Lock()
        self.ros_container = None

    def run(self, host, command, timeout=120):
        with self.lock:
            self.sequence += 1
            name = '%03d-%s' % (self.sequence, host)
        env = dict(os.environ, CRUZR_INTERNAL_ASKPASS='1',
                   SSH_ASKPASS=str(ROOT/'scripts/cruzr_recover_to_home.sh'),
                   SSH_ASKPASS_REQUIRE='force', DISPLAY=os.environ.get('DISPLAY', ':0'))
        prefix = ['setsid', '-w', 'ssh', '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=5',
                  '-o', 'PreferredAuthentications=password', '-o', 'PubkeyAuthentication=no',
                  '-o', 'NumberOfPasswordPrompts=1', 'walker@'+HOSTS[host]]
        self.save(name+'-pending.json', {'host': host, 'started_utc': dt.datetime.now(dt.timezone.utc).isoformat()})
        try:
            result = subprocess.run(prefix+[shlex.join(command)], env=env, capture_output=True,
                                    text=True, timeout=timeout)
        except subprocess.TimeoutExpired as error:
            raise RuntimeError('SSH timeout: inspect the saved phase before any retry') from error
        record = {'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
        self.save(name+'-result.json', record)
        if result.returncode:
            raise RuntimeError('Remote operation failed; private details: '+str(self.evidence/(name+'-result.json')))
        return result.stdout

    def save(self, name, data):
        with (self.evidence/name).open('x') as stream:
            json.dump(data, stream, indent=2)

    def remote(self, host, phase, session, profile, **extra):
        request = dict(host=host, phase=phase, session=session, profile=profile, **extra)
        modules = {
            'effector_profile_config': (ROOT/'scripts/hands/effector_profile_config.py').read_text(),
            'effector_bus': (ROOT/'scripts/hands/prepare_v4_bus_profile.py').read_text(),
        }
        payload = base64.b64encode(json.dumps(modules).encode()).decode()
        backend = base64.b64encode((ROOT/'scripts/hands/effector_profile_remote.py').read_bytes()).decode()
        code = """import sys,types,json,base64
for name,source in json.loads(base64.b64decode(sys.argv[1])).items():
 m=types.ModuleType(name);sys.modules[name]=m;exec(source,m.__dict__)
source=base64.b64decode(sys.argv[2]);sys.argv=[sys.argv[0],sys.argv[3]]
exec(compile(source,'effector_profile_remote.py','exec'),{'__name__':'__main__'})
"""
        text = self.run(host, ['python3', '-c', code, payload, backend, json.dumps(request)])
        rows = [row[len('EFFECTOR_JSON='):] for row in text.splitlines() if row.startswith('EFFECTOR_JSON=')]
        if len(rows) != 1:
            raise RuntimeError('Incomplete remote phase receipt')
        return json.loads(rows[0])


def json_message(text):
    # ROSA prepends log lines; only a standalone JSON-object start is accepted.
    for match in re.finditer(r'(?m)^\{', text):
        try:
            return json.JSONDecoder().raw_decode(text[match.start():])[0]
        except ValueError:
            continue
    raise ValueError('No complete JSON message')


def controller_states(text):
    marker = 'ListControllers.Response(controller='
    if marker not in text:
        raise ValueError('Missing controller response')
    value = text.split(marker, 1)[1].strip()
    if not value.endswith(')'):
        raise ValueError('Incomplete controller response')
    rows = ast.literal_eval(value[:-1])
    if not isinstance(rows, list) or len({r['name'] for r in rows}) != len(rows):
        raise ValueError('Ambiguous controller list')
    return {r['name']: r['state'] for r in rows}


def verify_backup(data, digest):
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError('External backup checksum mismatch')
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        names = archive.getnames()
        if len(names) != len(set(names)) or any(n.startswith('/') or '..' in Path(n).parts for n in names):
            raise ValueError('Unsafe/ambiguous backup members')
        hashes = json.load(archive.extractfile('session/archives.json'))
        originals = json.load(archive.extractfile('session/original.json'))
        if set(hashes) != {s+'.tar' for s in originals}:
            raise ValueError('Incomplete container archive coverage')
        for name, expected in hashes.items():
            if hashlib.sha256(archive.extractfile('session/'+name).read()).hexdigest() != expected:
                raise ValueError('Inner archive checksum mismatch')
    return len(hashes)


def native(transport, container, command):
    shell = 'source /opt/walker/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; timeout 12 '+command
    return transport.run('motion', ['docker', 'exec', container, 'bash', '-lc', shell], 20)


def pose(transport, snapshot):
    container = snapshot['motion']['containers']['motion.manipulation_robot_app']['Id']
    text = native(transport, container,
                  'rosa topic echo --once --no-daemon --qos-reliability best_effort /mc/actuator_state')
    message = json_message(text)
    report = classify(message, .02)
    if 'MEASURED_HOME=1' not in report:
        raise RuntimeError('Measured body posture is not HOME')
    stamp = message['header']['stamp']
    stamp_ns = stamp['sec']*1_000_000_000+stamp['nanosec']
    now_ns = int(transport.run('motion', ['date', '+%s%N']).strip())
    if not 0 <= now_ns-stamp_ns <= 2_000_000_000:
        raise RuntimeError('HOME sample is not fresh')
    return report, stamp_ns


def safety(transport, pressed):
    # Concurrent, fresh subscriptions avoid three separate 4.5-second acquisition windows.
    source = r"""import json,time,rclpy
from rclpy.qos import QoSProfile,ReliabilityPolicy,DurabilityPolicy
from std_msgs.msg import UInt8
rclpy.init();node=rclpy.create_node('effector_switch_readonly_safety')
seen={};qos=QoSProfile(depth=1,reliability=ReliabilityPolicy.RELIABLE,durability=DurabilityPolicy.VOLATILE)
subscriptions=[]
for topic in ('estop_key_state','servo_estop_key_state','chrg_input_status'):
 subscriptions.append(node.create_subscription(UInt8,'/emb/'+topic,lambda msg,t=topic:seen.update({t:(msg.data,time.monotonic())}),qos))
deadline=time.monotonic()+8
try:
 while len(seen)<3 and time.monotonic()<deadline:rclpy.spin_once(node,timeout_sec=.1)
 if len(seen)!=3 or any(time.monotonic()-stamp>5 for value,stamp in seen.values()):raise RuntimeError('Fresh safety collection incomplete')
 print('SAFETY_JSON='+json.dumps({t:v[0] for t,v in seen.items()}))
finally:node.destroy_node();rclpy.shutdown()
"""
    if not transport.ros_container:
        raise RuntimeError('ROS container has not been discovered')
    shell='source /opt/ros/humble/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; timeout 11 python3 -c '+shlex.quote(source)
    text=transport.run('motion',['docker','exec',transport.ros_container,'bash','-lc',shell],18)
    rows=[l[len('SAFETY_JSON='):] for l in text.splitlines() if l.startswith('SAFETY_JSON=')]
    if len(rows)!=1:raise RuntimeError('Missing safety receipt')
    actual=json.loads(rows[0])
    expected={'estop_key_state':1 if pressed else 0,'servo_estop_key_state':0,'chrg_input_status':0}
    if actual!=expected:raise RuntimeError('Unexpected safety state: '+json.dumps(actual))


def battery(transport):
    command = ('source /opt/ros/humble/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; '
               'timeout 10 ros2 topic echo --once --no-daemon /emb/battery_state')
    text = transport.run('motion', ['docker', 'exec', transport.ros_container, 'bash', '-lc', command], 18)
    values = [float(x) for x in re.findall(r'(?m)^\s*batsoc:\s*([0-9.]+)\s*$', text)]
    if len(values) != 2 or any(not 20 <= value <= 100 for value in values):
        raise RuntimeError('Require both battery packs at or above 20 percent')
    return values


def snapshots(transport, session, profile):
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {h: pool.submit(transport.remote, h, 'snapshot', session, profile) for h in HOSTS}
        result = {h: f.result() for h, f in futures.items()}
    transport.ros_container = result['motion']['ros_container']
    return result


def loaded(snapshot, profile):
    return all(dict(x.split('=', 1) for x in c['Config']['Env']).get('HW_TYPE') == PROFILES[profile]
               for host in snapshot.values() for c in host['containers'].values())


def prompt(text, expected):
    if input(text+'\nEscriba exactamente '+expected+': ').strip() != expected:
        raise RuntimeError('Operator did not confirm; no further phases executed')


def wait_ready(transport, cc, started, seconds=180):
    deadline = time.monotonic()+seconds
    while time.monotonic() < deadline:
        text = transport.run('vision', ['docker', 'logs', '--since', started, '--tail', '180', cc], 18)
        if '-> Fault' in text or 'unexpected_hardware' in text:
            raise RuntimeError('Startup fault before E-stop release')
        if 'WaitEStopRelease' in text:
            return
        time.sleep(3)
    raise RuntimeError('Startup did not reach WaitEStopRelease in time')


def verify(transport, session, profile, seconds=120):
    deadline = time.monotonic()+seconds
    last = None
    while time.monotonic() < deadline:
        try:
            current = snapshots(transport, session, profile)
            if not loaded(current, profile):
                raise RuntimeError('Requested profile not loaded on both hosts')
            for host,data in current.items():
                original_files={n:base64.b64decode(v) for n,v in data['files'].items()}
                if plan_files(host,original_files,profile,data.get('extra',{}).get('global_hw_type'))!=original_files:
                    raise RuntimeError('Persistent profile sources differ from the loaded target')
            if not all(c['State']['Running'] and c['RestartCount'] == 0
                       for h in current.values() for c in h['containers'].values()):
                raise RuntimeError('A recreated container is stopped/restarting')
            safety(transport, False)
            first, t1 = pose(transport, current)
            second, t2 = pose(transport, current)
            if t2 <= t1:
                raise RuntimeError('Body timestamps did not advance')
            app = current['motion']['containers']['motion.manipulation_robot_app']['Id']
            rows = controller_states(native(transport, app,
                "rosa service call /mc/controller_manager/list_controllers rosa_control_msgs/srv/ListControllers '{}'"))
            if any(rows.get(name) != 'running' for name in ('force_torque_sensor_controller', 'manipulation_controller')):
                raise RuntimeError('Required body controllers not running')
            if profile == 'clamp' and 'dexterous_hand_controller' in rows:
                raise RuntimeError('Hand controller still present in clamp profile')
            if profile == 'v4':
                if rows.get('dexterous_hand_controller') != 'running':
                    raise RuntimeError('v4 hand controller not running')
                # Installed native v4 topics are checked by the existing passive reader.
                source = (ROOT/'scripts/teleoperation/check_pico_v4_hand_states.py').read_text()
                code = 'source /opt/ros/humble/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; timeout 12 python3 -c '+shlex.quote(source)
                text = transport.run('motion', ['docker', 'exec', transport.ros_container, 'bash', '-lc', code], 18)
                if 'V4_HAND_STATES_OK=' not in text:
                    raise RuntimeError('Fresh v4 states unavailable')
            return {'profile': profile, 'body_home': second, 'controllers': rows,
                    'v4_states_verified': profile == 'v4', 'body_stamps_advanced': True}
        except (RuntimeError, ValueError, KeyError) as error:
            last = str(error)
            print('Verificación pendiente: '+last, flush=True)
            time.sleep(3)
    raise RuntimeError('Final verification failed: '+str(last))


def activate(transport, session, profile, journal):
    safety(transport, True)
    journal('start-motion')
    transport.remote('motion', 'start', session, profile)
    safety(transport, True)
    journal('start-cc')
    started = transport.run('vision', ['date', '-u', '+%Y-%m-%dT%H:%M:%SZ']).strip()
    transport.remote('vision', 'start', session, profile)
    current = snapshots(transport, session, profile)
    cc = current['vision']['containers']['system.control_center']['Id']
    journal('wait-estop')
    wait_ready(transport, cc, started)
    safety(transport, True)
    print('SISTEMA_PREPARADO=WaitEStopRelease', flush=True)
    prompt('Sistema preparado. Con brazos estables, retire soportes del recorrido y libere el paro principal. '
           'Puede iniciar HOME automáticamente; persona junto al paro.', 'PARO LIBERADO')
    journal('verify')
    result = verify(transport, session, profile)
    transport.save('verified.json', result)
    for host in HOSTS:transport.remote(host,'complete',session,profile)
    print('PERFIL_Y_HOME_VERIFICADOS='+profile)
    return 0


def resume_stopped(transport, folder, profile):
    """Resume only a stopped, already recreated pair; never reinstall/recreate."""
    folder = folder.resolve(strict=True)
    plan = json.loads((folder/'plan.json').read_text())
    session = plan['session']
    if plan['target'] != profile or not re.fullmatch(r'[0-9]{8}T[0-9]{6}Z-[a-f0-9]{8}', session):
        raise RuntimeError('Recovery session/target mismatch')
    required = {'phase-recreate-motion.json','phase-recreate-vision.json','interrupted.json'}
    if not required.issubset({p.name for p in folder.iterdir()}) or any(folder.glob('phase-start-*.json')):
        raise RuntimeError('Resume requires both recreation phases and no attempted start; inspect this session manually')
    staged = {}
    originals = {}
    for host in HOSTS:
        data = (folder/(host+'-backup.tar.gz')).read_bytes()
        receipt = json.loads((folder/(host+'-backup-verified.json')).read_text())
        verify_backup(data, receipt['sha256'])
        with tarfile.open(fileobj=io.BytesIO(data)) as archive:
            originals[host] = json.load(archive.extractfile('session/original.json'))
            staged[host] = {m.name.split('/')[1]:hashlib.sha256(archive.extractfile(m).read()).hexdigest()
                            for m in archive.getmembers() if m.isfile() and m.name.count('/') == 1}
    transport.save('resume-plan.json', {'source':str(folder),'session':session,'target':profile,
                                      'expected_staged_files':staged})
    current = snapshots(transport,session,profile)
    expected = {'session':session,'profile':profile}
    if any(h.get('active_session') != expected for h in current.values()):
        raise RuntimeError('Both original active session markers must match')
    if not loaded(current,profile) or any(c['State']['Running'] for h in current.values() for c in h['containers'].values()):
        raise RuntimeError('Resume requires all target containers already recreated and stopped')
    if profile == 'v4' and current['vision']['extra']['guard_sha256'] != GUARD_SHA:
        raise RuntimeError('Unreviewed boot guard')
    for host,h in current.items():
        hashes = {n:hashlib.sha256(base64.b64decode(v)).hexdigest() for n,v in h['files'].items()}
        if hashes != plan['hashes'][host]:raise RuntimeError('Installed sources differ from the original plan')
        if set(h['containers']) != set(originals[host]):raise RuntimeError('Container coverage differs')
        if any(c['Id'] == originals[host][s]['Id'] for s,c in h['containers'].items()):
            raise RuntimeError('A service was not recreated; manual review required')
    if subprocess.run(['pgrep','-x','pico_control'],capture_output=True).returncode != 1:
        raise RuntimeError('PICO controller active or process check unavailable')
    # Prove remote stage matches the external backup and contract before any writes.
    requests = {h:dict(expected_ids={s:c['Id'] for s,c in current[h]['containers'].items()},
                       expected_staged_files=staged[h]) for h in HOSTS}
    for host in HOSTS:transport.remote(host,'validate',session,profile,**requests[host])
    print('EVIDENCIA='+str(transport.evidence),flush=True)
    prompt('Reanudación: mismo hardware instalado, manos vacías, recorrido despejado, cargador desconectado, '
           'otros mandos detenidos y persona junto al paro.', 'CONDICIONES COMPROBADAS')
    prompt('Mantenga los brazos asegurados contra caída y el paro principal pulsado, servos liberado.', 'BRAZOS ASEGURADOS')
    safety(transport,True)
    battery(transport)
    def journal(phase):
        transport.save('phase-'+phase+'.json',{'phase':phase,'session':session,'target':profile})
        print('FASE='+phase,flush=True)
    # Motion's restoration succeeded previously; verify it without overwriting again.
    journal('verify-stopped-motion')
    transport.remote('motion','verify-stopped',session,profile,**requests['motion'])
    safety(transport,True)
    journal('restore-vision')
    restoration = transport.remote('vision','restore',session,profile,**requests['vision'])
    transport.save('vision-restoration.json',restoration)
    return activate(transport,session,profile,journal)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--to', required=True, choices=PROFILES)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--apply', action='store_true')
    mode.add_argument('--verify', action='store_true')
    parser.add_argument('--finish-session', help='With --verify only: close a reviewed interrupted session after HOME/files verification')
    parser.add_argument('--secured-recovery', action='store_true', help='Recovery with secured arms when HOME telemetry is unavailable')
    parser.add_argument('--resume-from', type=Path, help='Original evidence folder: resume only after both hosts were recreated and remain stopped')
    parser.add_argument('--evidence', type=Path)
    args = parser.parse_args(argv)
    if args.finish_session and (not args.verify or not re.fullmatch(r'[0-9]{8}T[0-9]{6}Z-[a-f0-9]{8}',args.finish_session)):
        parser.error('--finish-session requires --verify and the exact saved session ID')
    if args.secured_recovery and not args.apply:
        parser.error('--secured-recovery only applies to --apply')
    if args.resume_from and not (args.apply and args.secured_recovery):
        parser.error('--resume-from requires --apply --secured-recovery')
    if args.apply and not sys.stdin.isatty():
        parser.error('--apply requires an interactive terminal and physical confirmations')
    session = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]
    folder = args.evidence or ROOT.parent/'Humanoide-vla-evidence'/('EFFECTOR-'+session)
    folder.mkdir(mode=0o700, parents=True, exist_ok=False)
    transport = Transport(folder)
    def journal(phase):
        transport.save('phase-'+phase+'.json', {'phase': phase, 'session': session, 'target': args.to})
        print('FASE='+phase, flush=True)
    try:
        if args.resume_from:
            return resume_stopped(transport,args.resume_from,args.to)
        journal('inventory')
        before = snapshots(transport, session, args.to)
        candidates = {h: plan_files(h, {n: base64.b64decode(v) for n, v in data['files'].items()}, args.to, data.get('extra',{}).get('global_hw_type'))
                      for h, data in before.items()}
        if args.to == 'v4':
            if before['vision']['extra']['guard_sha256'] != GUARD_SHA:
                raise RuntimeError('Unreviewed CC boot guard; inspect compatibility before selecting SPS')
            if before['motion']['extra']['eni_sha256'] not in (ENI_SHA, SOURCE_SHA256):
                raise RuntimeError('Unreviewed v4 ENI; inspect the installed version')
        files_match = all(candidates[h][n] == base64.b64decode(before[h]['files'][n]) for h in HOSTS for n in candidates[h])
        transport.save('plan.json', {'target': args.to, 'loaded': loaded(before, args.to), 'files_match': files_match,
                        'session': session, 'remote_stage': '/home/walker/.local/share/cruzr-effector-switch/'+session,
                        'hashes': {h: {n: hashlib.sha256(v).hexdigest() for n, v in files.items()} for h, files in candidates.items()}})
        print('Perfil solicitado: '+args.to+'; procesos coinciden: '+str(loaded(before, args.to))+'; archivos coinciden: '+str(files_match))
        print('EVIDENCIA='+str(folder))
        if args.verify:
            if args.finish_session and not files_match:raise RuntimeError('Target files do not match; cannot close an interrupted session')
            result = verify(transport, session, args.to)
            transport.save('verified.json', result)
            if args.finish_session:
                expected={'session':args.finish_session,'profile':args.to}
                if any(h.get('active_session') not in (None,expected) for h in before.values()):raise RuntimeError('Interrupted session/target mismatch')
                for host in HOSTS:
                    if before[host].get('active_session') is not None:transport.remote(host,'complete',args.finish_session,args.to)
            print('PERFIL_Y_HOME_VERIFICADOS='+args.to)
            return 0
        if not args.apply:
            print('SOLO_LECTURA=1; para cambiar use --apply con el hardware correspondiente instalado.')
            return 0
        if any(d.get('active_session') for d in before.values()):
            raise RuntimeError('Interrupted session exists: inspect evidence before any new --apply')
        if loaded(before, args.to) and files_match:
            result = verify(transport, session, args.to)
            transport.save('verified.json', result)
            print('PERFIL_Y_HOME_VERIFICADOS='+args.to+'; sin recarga innecesaria')
            return 0
        if subprocess.run(['pgrep', '-x', 'pico_control'], capture_output=True).returncode != 1:
            raise RuntimeError('PICO controller active or process check unavailable')
        print('El montaje/retirada debe haberse hecho con alimentación apagada. No cambie físicamente efectores ahora.')
        prompt('Confirme: hardware '+args.to+' instalado (clamp admite muñecas vacías), sin objeto, recorrido libre, '
               'cargador desconectado, otros mandos detenidos y persona junto al paro.', 'CONDICIONES COMPROBADAS')
        if args.secured_recovery:
            prompt('Recuperación: asegurar los brazos contra caída/golpe antes de retirar control.', 'BRAZOS ASEGURADOS')
        else:
            pose(transport, before)  # Requires original HOME/rest/fault classifier before asking for E-stop.
        battery(transport)
        prompt('Pulse y mantenga el paro principal; deje liberado el de servos.', 'PARO PRINCIPAL PULSADO')
        safety(transport, True)
        journal('backup')
        for host in HOSTS:
            transport.remote(host, 'backup', session, args.to,
                expected_files={n:hashlib.sha256(base64.b64decode(v)).hexdigest() for n,v in before[host]['files'].items()},
                expected_ids={name:c['Id'] for name,c in before[host]['containers'].items()})
            bundle = transport.remote(host, 'export', session, args.to)
            data = base64.b64decode(bundle['base64'])
            count = verify_backup(data, bundle['sha256'])
            (folder/(host+'-backup.tar.gz')).write_bytes(data)
            transport.save(host+'-backup-verified.json', {'archives': count, 'sha256': bundle['sha256']})
        # Freeze both hosts first, then recheck safety between every mutation phase.
        for host in ('vision', 'motion'):
            safety(transport, True)
            journal('stop-'+host)
            transport.remote(host, 'stop', session, args.to)
        for host in HOSTS:
            safety(transport, True)
            journal('install-'+host)
            transport.remote(host, 'install', session, args.to,
                             files={n: base64.b64encode(v).decode() for n, v in candidates[host].items()})
        for host in HOSTS:
            safety(transport, True)
            journal('recreate-'+host)
            transport.remote(host, 'recreate', session, args.to)
        return activate(transport,session,args.to,journal)
    except (Exception, KeyboardInterrupt) as error:
        transport.save('interrupted.json', {'error_type': type(error).__name__, 'message': str(error),
                       'automatic_retry': False, 'automatic_home': False})
        print('CAMBIO_INTERRUMPIDO: '+str(error), file=sys.stderr)
        if args.apply:
            print('Sin reintento de control ni HOME automático. No libere el paro para probar. Evidencia: '+str(folder), file=sys.stderr)
        else:
            print('Comprobación no superada; sin cambios ni movimientos. Evidencia: '+str(folder), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
