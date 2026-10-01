#!/usr/bin/env python3
"""PC entry point with fixed ask/assume/sensors wrappers; --check by default."""
import argparse
import base64
from contextlib import ExitStack
import fcntl
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import threading
import time

if __package__:
    from . import scenario1_contract as contract
    from . import scenario1_sensors as sensors
    from . import scenario1_nav_correction as nav_correction
    from . import scenario1_resume as resume
    from .scenario1_console import ConsoleReporter, stage_label
    from .front_box_integration import build_bundle, TASK_ROOT, META_ROOT, SNAPSHOT
else:
    import scenario1_contract as contract
    import scenario1_sensors as sensors
    import scenario1_nav_correction as nav_correction
    import scenario1_resume as resume
    from scenario1_console import ConsoleReporter, stage_label
    from front_box_integration import build_bundle, TASK_ROOT, META_ROOT, SNAPSHOT

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MODULES = [('cruzr_home_posture_gate', ROOT/'scripts/lib/cruzr_home_posture_gate.py'),
           ('front_sps_session', HERE/'front_sps_session.py'),
           ('scenario1_contract', HERE/'scenario1_contract.py'),
           ('scenario1_checks', HERE/'scenario1_checks.py'),
           ('scenario1_live_health', HERE/'scenario1_live_health.py'),
           ('scenario1_sensors', HERE/'scenario1_sensors.py'),
           ('scenario1_dependencies', HERE/'scenario1_dependencies.py'),
           ('scenario1_session', HERE/'scenario1_session.py'),
           ('scenario1_nav_correction', HERE/'scenario1_nav_correction.py'),
           ('scenario1_resume', HERE/'scenario1_resume.py'),
           ('scenario1_cycle_lease', HERE/'scenario1_cycle_lease.py'),
           ('scenario1_request_ids', HERE/'scenario1_request_ids.py'),
           ('scenario1_runtime', HERE/'scenario1_runtime.py')]
BOOTSTRAP = '''import json,sys,types
payload=json.loads(sys.stdin.readline())
for name,source in payload.pop('modules'):
 module=types.ModuleType(name);sys.modules[name]=module
 exec(compile(source,name+'.py','exec'),module.__dict__)
raise SystemExit(sys.modules['scenario1_runtime'].main(payload))
'''


def atomic_json(path, value):
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, prefix=path.name+'.', delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def claim_resume(source, destination):
    """Consume the old clean checkpoint BEFORE any continued physical stage."""
    marker = source.with_name(source.name+'.consumed.json')
    with marker.open('x') as stream:
        json.dump({'continued_in': str(destination), 'time_ns': time.time_ns()}, stream)
        stream.flush()
        os.fsync(stream.fileno())
    descriptor = os.open(marker.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class StageStop:
    """Keep SSH and its heartbeat alive until the current stage is journaled."""
    def __init__(self, enabled):
        self.enabled = enabled
        self.requested = False

    def request(self, signum=None, frame=None):
        first = not self.requested
        self.requested = True
        if first:
            os.write(2, ('\nCtrl+C: terminaré la etapa actual y guardaré la retoma. '
                         'No es una parada de emergencia.\n').encode())

    def __enter__(self):
        if self.enabled:
            self.previous = signal.signal(signal.SIGINT, self.request)
        return self

    def __exit__(self, *exc):
        if self.enabled:
            signal.signal(signal.SIGINT, self.previous)


def should_pause(checkpoint, stop_requested):
    # These close the preceding physical stage without dispatching movement.
    return bool(stop_requested and contract.next_stage(checkpoint) not in
                ('verify_held', 'verify_released', 'verify_home'))


def finish_connection(connection):
    connection.send({'command': 'finish'})
    if connection.process.wait(timeout=15):
        raise RuntimeError('Supervisor terminó con error')


def report_pause(wrapper, checkpoint_path, checkpoint, cycle, *, args=None, resume_plan=None):
    stage = resume_plan['stage'] if resume_plan else contract.next_stage(checkpoint)
    print('PAUSA_COMPLETADA; siguiente='+str(stage or 'ciclo terminado'), flush=True)
    print('Checkpoint: '+str(checkpoint_path))
    if stage is not None:
        command = ['./scripts/'+wrapper, *(['--cycle'] if cycle else []), '--resume', str(checkpoint_path.resolve())]
        if args is not None:
            if args.profile.resolve() != (HERE/'scenario1_current_geometry.json').resolve():
                command += ['--profile', str(args.profile.resolve())]
            if args.wifi:
                command += ['--wifi']
            if args.stop_after != 'cycle':
                command += ['--stop-after', args.stop_after]
            if resume_plan:
                print('Origen sin consumir; preparación detenida antes de armar.')
                for flag, value in (('--from-stage', args.from_stage), ('--box-state', args.box_state)):
                    if value:
                        command += [flag, value]
                if args.recovery_confirmed:
                    command += ['--recovery-confirmed']
        print('Retomar: '+shlex.join(command))


def make_payload(mode, profile, checkpoint):
    bundle = build_bundle()
    extra = {}
    for relative in ('tasks/cruzr/mobot_back_20.xml', 'tasks/wrc_cruzr/put_cruzr_wrc_low.xml',
                     'meta_clamp/wrc/put_cruzr_wrc_low.yaml', 'meta_clamp/wrc/open_arm_cruzr.yaml'):
        prefix, name = relative.split('/', 1)
        extra[(TASK_ROOT if prefix == 'tasks' else META_ROOT)+name] = hashlib.sha256((SNAPSHOT/relative).read_bytes()).hexdigest()
    # Reuse reviewed HOME contracts, including user edits; never import shell secrets.
    pins = dict(re.findall(r'^readonly (\w+_SHA)="([a-f0-9]{64})"$',
                          (ROOT/'scripts/cruzr_blue_workbin_cycle.sh').read_text(), re.M))
    names = ['DIRECT_HOME_SHA', 'BODY_FIRST_HOME_SHA', 'BODY_FIRST_V5_HOME_SHA',
             'EARLY_ROLL_V8_HOME_SHA', 'BODY_FIRST_V7_HOME_SHA', 'OPEN_HOME_SHA']
    # The action worker runs in a separate native container/process. Carry its
    # pure telemetry guard in memory too; importing on the supervisor is not enough.
    guard_source = (HERE/'scenario1_nav_correction.py').read_text()
    ids_source = (HERE/'scenario1_request_ids.py').read_text()
    ids_loader = ("_ids=types.ModuleType('scenario1_request_ids')\n"
                  "sys.modules['scenario1_request_ids']=_ids\n"
                  'exec(compile('+repr(ids_source)+",'scenario1_request_ids.py','exec'),_ids.__dict__)\n")
    action_source = ('import sys,types\n'+ids_loader+
                    "_guard=types.ModuleType('scenario1_nav_correction')\n"
                    "sys.modules['scenario1_nav_correction']=_guard\n"
                    'exec(compile('+repr(guard_source)+",'scenario1_nav_correction.py','exec'),_guard.__dict__)\n"+
                    (HERE/'scenario1_action_client.py').read_text())
    # The independent health process needs the same pure validators as the
    # supervisor. This introduces no ROS writers or persistent installation.
    health_dependencies = [(name, path) for name, path in MODULES
                           if name in ('cruzr_home_posture_gate', 'scenario1_checks',
                                       'scenario1_live_health', 'scenario1_request_ids')]
    health_source = ('import sys,types\n'
                     'for _name,_source in '+repr([(name, path.read_text())
                                                   for name, path in health_dependencies])+':\n'
                     ' _module=types.ModuleType(_name);sys.modules[_name]=_module\n'
                     ' exec(compile(_source,_name+".py","exec"),_module.__dict__)\n'+
                     (HERE/'scenario1_health_worker.py').read_text())
    return dict(mode=mode, profile=profile, checkpoint=checkpoint, bundle=bundle,
                extra_hashes=extra, home_pins=dict(accepted=[pins[n] for n in names],
                    direct=pins['DIRECT_HOME_SHA'], meta=pins['OPEN_HOME_META_SHA']),
                action_client=action_source,
                perception_guard=(HERE/'scenario1_perception.py').read_text(),
                sensor_worker=(HERE/'scenario1_sensor_worker.py').read_text(),
                health_worker=health_source,
                resume_worker=(HERE/'scenario1_resume_worker.py').read_text(),
                modules=[(name, path.read_text()) for name, path in MODULES])


def ssh_command(wifi):
    command = ['ssh', '-T', '-o', 'BatchMode=no', '-o', 'StrictHostKeyChecking=yes',
               '-o', 'ConnectTimeout=8', '-o', 'ConnectionAttempts=1',
               '-o', 'ServerAliveInterval=5', '-o', 'ServerAliveCountMax=2',
               '-o', 'PreferredAuthentications=password', '-o', 'PubkeyAuthentication=no',
               '-o', 'NumberOfPasswordPrompts=1']
    if wifi:
        command += ['-J', 'walker@192.168.42.2']
    code = 'import base64;exec(base64.b64decode(%r))' % base64.b64encode(BOOTSTRAP.encode()).decode()
    command += ['walker@192.168.11.2', shlex.join(['python3', '-u', '-B', '-c', code])]
    return command


class Connection:
    def __init__(self, payload, wifi, evidence, *, console=None):
        self.evidence = evidence
        self.console = console if console is not None else ConsoleReporter()
        self.events = queue.Queue()
        self.write_lock = threading.Lock()
        self.closed = threading.Event()
        env = dict(os.environ, CRUZR_INTERNAL_ASKPASS='1',
                   SSH_ASKPASS=str(ROOT/'scripts/cruzr_recover_to_home.sh'),
                   SSH_ASKPASS_REQUIRE='force', DISPLAY=os.environ.get('DISPLAY', ':0'))
        self.process = subprocess.Popen(ssh_command(wifi), stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
            start_new_session=True, bufsize=1)
        self.send(payload)
        self.threads = [threading.Thread(target=self.read, daemon=True),
                        threading.Thread(target=self.errors, daemon=True),
                        threading.Thread(target=self.heartbeat, daemon=True)]
        for thread in self.threads:
            thread.start()

    def send(self, value):
        with self.write_lock:
            self.process.stdin.write(json.dumps(value, allow_nan=False)+'\n')
            self.process.stdin.flush()

    def read(self):
        try:
            with (self.evidence/'events.jsonl').open('a') as log:
                for line in self.process.stdout:
                    log.write(line)
                    log.flush()
                    try:
                        event = json.loads(line)
                        if not isinstance(event, dict) or not isinstance(event.get('event'), str):
                            raise ValueError('Malformed supervisor event')
                        if event['event'] == 'checkpoint':
                            contract.validate_checkpoint(event['checkpoint'])
                            atomic_json(self.evidence/'checkpoint.json', event['checkpoint'])
                        self.present(event)
                        self.events.put(event)
                    except (ValueError, KeyError, TypeError) as exc:
                        error = dict(event='error', reason='Protocolo remoto inválido: '+str(exc))
                        self.present(error)
                        self.events.put(error)
        finally:
            self.events.put(dict(event='eof'))

    def present(self, event):
        # Presentation never consumes events or changes validation/control. Keep
        # this in the reader so late cancellation events remain visible in close().
        try:
            lines = self.console.render(event)
        except Exception:
            lines = ['  Aviso: no se pudo resumir un evento; consulte events.jsonl.']
        for line in lines:
            try:
                print(line, flush=True)
            except (OSError, ValueError):
                # A closed output pipe must not prevent journaling/checkpoints.
                break

    def errors(self):
        with (self.evidence/'ssh.log').open('w') as log:
            for line in self.process.stderr:
                log.write(line)
                log.flush()

    def heartbeat(self):
        while not self.closed.wait(2):
            try:
                self.send({'command': 'heartbeat'})
            except (OSError, ValueError):
                return

    def wait(self, desired, timeout=240):
        end = time.monotonic()+timeout
        while time.monotonic() < end:
            try:
                event = self.events.get(timeout=min(1, max(0.01, end-time.monotonic())))
            except queue.Empty:
                continue
            kind = event['event']
            if kind == 'error':
                raise RuntimeError(event.get('reason', 'Fallo remoto'))
            if kind == 'eof':
                raise RuntimeError('Conexión terminada antes de confirmar '+desired)
            if kind == desired:
                return event
        raise RuntimeError('Plazo agotado esperando '+desired+'; estado físico no confirmado')

    def close(self):
        self.closed.set()
        try:
            with self.write_lock:
                self.process.stdin.close()
        except (OSError, ValueError):
            pass
        try:
            self.process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=2)
        for thread in self.threads[:2]:
            thread.join(timeout=2)


def confirm(prompt, token):
    print(prompt, flush=True)
    answer = input('Escriba '+token+' para continuar: ')
    if answer != token:
        raise RuntimeError('Confirmación no recibida; no se enviará la siguiente etapa')


ENTRYPOINTS = {'ask': 'ask_improved_scenario1.sh', 'assume': 'force_improved_scenario1.sh',
              'sensors': 'force_improved_scenario1_autochecked.sh'}


def entrypoint_name(policy, execution_profile='standard_v1'):
    if execution_profile == 'optimistic_v1' and policy == 'assume':
        return 'optimistic_scenario1.sh'
    if execution_profile != 'standard_v1':
        raise ValueError('Unsupported execution profile or confirmation policy')
    return ENTRYPOINTS[policy]


class SensorCalibrationPending(ValueError):
    pass


def parser(policy='ask', execution_profile='standard_v1'):
    p = argparse.ArgumentParser(prog=entrypoint_name(policy, execution_profile),
        description='Escenario 1; política '+policy+'. Conserva la geometría actual. Por defecto sólo --check.')
    p.set_defaults(policy=policy, execution_profile=execution_profile)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true', help='Comprobaciones completas sin iniciar adaptadores SPS ni mover')
    mode.add_argument('--plan', action='store_true', help='Mostrar perfil y etapas sin conectar al robot')
    mode.add_argument('--run', action='store_true', help='Ejecutar '+('con confirmaciones presenciales' if policy == 'ask' else 'sin preguntas'))
    if execution_profile == 'optimistic_v1':
        p.add_argument('--cycle', action='store_true',
                       help='Repetir ciclos en la misma sesión; implica ejecución salvo --plan/--check. Ctrl+C termina la etapa y pausa')
    p.add_argument('--resume', type=Path, metavar='CHECKPOINT',
                   help='Reanudar desde un checkpoint; combinar con --plan o --check para no mover')
    p.add_argument('--from-stage', choices=contract.STAGES,
                   help='Etapa de entrada al reanudar; por defecto, la siguiente del checkpoint')
    p.add_argument('--box-state', choices=('empty', 'held', 'released'),
                   help='Estado físico actual: empty=vacías; held=sujeta, separada y estable; released=apoyada y liberada')
    p.add_argument('--recovery-confirmed', action='store_true',
                   help='Confirma recuperación física y recorrido aptos para la etapa elegida tras fallo/interrupción o salto; no omite comprobaciones')
    p.add_argument('--verbose', action='store_true',
                   help='Mostrar todos los eventos técnicos en consola; events.jsonl siempre conserva el detalle completo')
    p.add_argument('--wifi', action='store_true', help='SSH mediante 192.168.42.2')
    p.add_argument('--benchmark-checks', type=int, choices=range(1, 6), default=0, metavar='N',
                   help='Sólo con --check: medir de 1 a 5 rondas adicionales de consultas sin mover')
    p.add_argument('--stop-after', choices=('get1', 'grasp', 'put1', 'cycle'), default='cycle',
                   help='get1: sólo navegar y medir llegada; grasp: terminar tras confirmar caja sujeta; '
                        'put1: llegar con la caja sujeta y detenerse antes del depósito')
    p.add_argument('--profile', type=Path, default=HERE/'scenario1_current_geometry.json')
    if policy == 'sensors':
        p.add_argument('--sensor-profile', type=Path, default=HERE/'scenario1_sensor_profile.json',
                       help='Referencias FT por postura; --run requiere perfil cualificado')
    p.add_argument('--evidence-dir', type=Path, help='Directorio nuevo para logs y checkpoint; por defecto fuera de Git')
    return p


def is_moving(args):
    return bool(args.run or args.resume or getattr(args, 'cycle', False)) and not (args.check or args.plan)


def _main(args, stop=None):
    if stop is None:
        return run_args(args)
    policy = args.policy
    execution_profile = getattr(args, 'execution_profile', 'standard_v1')
    wrapper = entrypoint_name(policy, execution_profile)
    moving = is_moving(args)
    cycle = getattr(args, 'cycle', False)
    if cycle and (execution_profile != 'optimistic_v1' or args.stop_after != 'cycle'):
        raise ValueError('--cycle requiere optimistic y un ciclo completo; no admite --stop-after get1/grasp/put1')
    if not args.resume and (args.from_stage or args.box_state or args.recovery_confirmed):
        raise ValueError('--from-stage, --box-state y --recovery-confirmed requieren --resume CHECKPOINT')
    if args.benchmark_checks and (moving or args.plan):
        raise ValueError('--benchmark-checks sólo permite comprobaciones de lectura')
    stop_after = {'get1': 'navigate_get1', 'grasp': 'verify_held',
                  'put1': 'navigate_put1', 'cycle': 'verify_home'}[args.stop_after]
    profile = contract.validate_profile(json.loads(args.profile.read_text()), stop_after=stop_after)
    checkpoint = contract.new_checkpoint(profile, stop_after=stop_after, policy=policy,
                                         execution_profile=execution_profile)
    sensor_profile = None
    if policy == 'sensors':
        sensor_profile = sensors.validate_profile(json.loads(args.sensor_profile.read_text()),
            profile['id'])
        if moving and sensor_profile['qualification'] != 'qualified':
            raise SensorCalibrationPending('Sensor calibration qualification is pending')
    resume_plan = None
    source_checkpoint = None
    if args.resume:
        if args.resume.with_name(args.resume.name+'.consumed.json').exists():
            raise RuntimeError('Este checkpoint ya fue consumido por otra reanudación')
        source_checkpoint = contract.validate_checkpoint(json.loads(args.resume.read_text()), profile)
        if args.from_stage is None and contract.progress_index(source_checkpoint) > contract.STAGES.index(stop_after):
            raise RuntimeError('La reanudación solicitada no tiene etapas pendientes')
        resume_options = dict(stage=args.from_stage, box_state=args.box_state,
                              recovery_confirmed=args.recovery_confirmed, stop_after=stop_after, policy=policy,
                              execution_profile=execution_profile)
        resume_plan = resume.plan_resume(source_checkpoint, profile, **resume_options)
        checkpoint = resume_plan['checkpoint']
    if moving and policy == 'ask' and not sys.stdin.isatty():
        raise RuntimeError('Se requiere un terminal y operador junto al robot')
    home_retry_remaining = int(
        execution_profile == 'optimistic_v1' and 'home_retry' not in checkpoint and
        not checkpoint.get('home_retry_blocked', False) and
        contract.progress_index(checkpoint) <= contract.STAGES.index('home') <=
        contract.STAGES.index(stop_after))
    print('Geometría: force_escenario1.sh actual; tareas y límites del proveedor conservados.')
    print('Confirmación: '+{'ask': 'operador', 'assume': 'sin preguntas; sujeción/liberación asumidas tras éxito técnico',
                          'sensors': 'sin preguntas; ventanas FT y postura con referencias cualificadas'}[policy])
    if execution_profile == 'optimistic_v1':
        print('Optimista: salud recibida continuamente; sin repetir la adquisición completa entre etapas. '
              'Se conservan errores, reposo, límites de caja, llegada y HOME medido.')
        if home_retry_remaining:
            print('HOME: un único reintento tras MoveToGoalFailed confirmado, con nueva comprobación de salud y reposo; '
                  'sin reintento ante timeout, cancelación o fallo de comunicación.')
        else:
            print('HOME: sin reintento automático disponible en este segmento.')
    correction_status = nav_correction.qualification_report()
    if correction_status['motion_enabled']:
        approach = format(nav_correction.POLICY['max_approach_angular_speed_rad_s'], '.2f').replace('.', ',')
        alignment = format(nav_correction.POLICY['max_angular_speed_rad_s'], '.2f').replace('.', ',')
        print('Llegada get1: 2 cm / 2 grados; hasta '+str(nav_correction.POLICY['max_corrections'])+
              ' ajustes supervisados. Giro medido: máximo '+approach+' rad/s al aproximar y '+alignment+
              ' rad/s sólo junto al destino. Validación física pendiente.')
    else:
        print('Llegada get1: 2 cm / 2 grados. Ajuste bloqueado: '+correction_status['reason'])
    if args.plan:
        print(json.dumps(dict(profile=profile, stages=list(contract.STAGES[contract.progress_index(checkpoint):contract.STAGES.index(stop_after)+1]),
            policy=policy, execution_profile=execution_profile,
            continuous_cycle=cycle,
            interstage_health=('live_snapshot_and_fresh_stationary_actuators'
                               if execution_profile == 'optimistic_v1' else 'full_acquisition'),
            sensor_qualification=sensor_profile['qualification'] if sensor_profile else None,
            physical_validation='pending', automatic_retries=home_retry_remaining,
            home_retry=dict(stage='home', remaining=home_retry_remaining,
                            max_retries_per_cycle=1 if execution_profile == 'optimistic_v1' else 0,
                            terminal_status=6, code=7104050, desc='MoveToGoalFailed',
                            fresh_health_and_stationary_required=True),
            get1_correction=dict(nav_correction.qualification_report(), policy=dict(nav_correction.POLICY)),
            resume=resume_plan), indent=2, ensure_ascii=False))
        return 0
    if moving:
        subprocess.run(['bash', str(ROOT/'scripts/lib/cruzr_contact_motion_lock.sh'), 'improved-scenario1'], check=True,
                       start_new_session=True)
    evidence = args.evidence_dir or ROOT.parent/'Humanoide-vla-evidence'/(
        time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())+
        ('_OPTIMISTIC_SCENARIO1_' if execution_profile == 'optimistic_v1' else '_IMPROVED_SCENARIO1_')+str(os.getpid()))
    evidence.mkdir(parents=True, exist_ok=False)
    os.chmod(evidence, 0o700)
    atomic_json(evidence/'profile.json', profile)
    if not args.resume:
        atomic_json(evidence/'checkpoint.json', checkpoint)
    payload = make_payload('run' if moving else 'check', profile, checkpoint)
    payload['policy'] = policy
    payload['execution_profile'] = execution_profile
    payload['cycle'] = cycle
    payload['check_repetitions'] = args.benchmark_checks
    if sensor_profile is not None:
        payload['sensor_profile'] = sensor_profile
        atomic_json(evidence/'sensor-profile.json', sensor_profile)
    if args.resume:
        payload['resume_context'] = json.loads((args.resume.parent/'context.json').read_text())
        payload['resume_source_checkpoint'] = source_checkpoint
        payload['resume_options'] = resume_options
        payload['resume_plan'] = resume_plan
        atomic_json(evidence/'resume-source-checkpoint.json',
                    dict(artifact='resume_source_snapshot', checkpoint=source_checkpoint))
        atomic_json(evidence/'resume-plan.json', resume_plan)
        atomic_json(evidence/'resume-source.json', dict(path=str(args.resume.resolve()),
            checkpoint_sha256=resume_plan['source_sha256'], context=payload['resume_context']))
    atomic_json(evidence/'source-sha256.json', {name: hashlib.sha256(source.encode()).hexdigest()
        for name, source in payload['modules']} | {
            'action_client': hashlib.sha256(payload['action_client'].encode()).hexdigest(),
            'perception_guard': hashlib.sha256(payload['perception_guard'].encode()).hexdigest(),
            'sensor_worker': hashlib.sha256(payload['sensor_worker'].encode()).hexdigest(),
            'health_worker': hashlib.sha256(payload['health_worker'].encode()).hexdigest(),
            'resume_worker': hashlib.sha256(payload['resume_worker'].encode()).hexdigest(),
            'scenario1_console': hashlib.sha256((HERE/'scenario1_console.py').read_bytes()).hexdigest(),
            'scenario1_cli': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'entrypoint': hashlib.sha256((ROOT/'scripts'/wrapper).read_bytes()).hexdigest()})
    print('Evidencia: '+str(evidence), flush=True)
    connection = None
    with ExitStack() as stack:
        for name in ('/tmp/cruzr_blue_workbin_cycle.lock', '/tmp/cruzr-improved-scenario1.lock'):
            lock = stack.enter_context(open(name, 'a'))
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            connection = Connection(payload, args.wifi, evidence, console=ConsoleReporter(verbose=args.verbose))
            ready = connection.wait('ready')
            atomic_json(evidence/'context.json', ready['context'])
            print('Comprobaciones técnicas completadas; mapa='+ready['map_name']+' '+ready['nav_state'], flush=True)
            if not moving:
                rc = connection.process.wait(timeout=10)
                if policy == 'sensors' and sensor_profile['qualification'] != 'qualified':
                    print('SENSORES_PENDIENTES: faltan referencias cualificadas por postura; --run no ejecutará movimientos.')
                print(('RESUME_CHECK_OK; origen sin consumir, sin movimiento.' if args.resume else 'CHECK_OK')
                      if rc == 0 else 'PREPARACION_REQUERIDA: revise eventos; mapa/localización o referencias de sensores pendientes.')
                return rc
            if stop.requested:
                finish_connection(connection)
                # A resume source is still unconsumed until arm below.
                report_pause(wrapper, args.resume or evidence/'checkpoint.json',
                             source_checkpoint if args.resume else checkpoint, cycle, args=args, resume_plan=resume_plan)
                return 0
            if args.resume:
                state = checkpoint['box_state']
                if policy == 'ask':
                    confirm('Reanudación en '+resume_plan['stage']+': confirme '+
                            {'held': 'caja sujeta, separada y estable.', 'released': 'caja apoyada y liberada.',
                             'empty': 'abrazaderas vacías.'}[state]+
                            ' La postura y el recorrido deben ser adecuados para esta etapa.', 'REANUDAR')
                connection.send({'command': 'resume', 'stop_after': stop_after})
                checkpoint = contract.validate_checkpoint(connection.wait('resume_ready')['checkpoint'], profile)
            if policy == 'ask':
                confirm('Confirme abrazaderas '+('vacías y robot en HOME' if not args.resume else 'en el estado indicado')+
                    ', montaje original de recogida/depósito, trayectorias libres, ruedas en navegación, '
                    'cargador desconectado, paros liberados, modo automático, ningún otro mando y persona junto al paro.', 'CONTINUAR')
            if args.resume:
                current = contract.validate_checkpoint(json.loads(args.resume.read_text()), profile)
                if resume.plan_resume(current, profile, **resume_options) != resume_plan:
                    raise RuntimeError('RESUME_SOURCE_CHANGED: no consumir ni ejecutar otro checkpoint')
            if stop.requested:
                finish_connection(connection)
                report_pause(wrapper, args.resume or evidence/'checkpoint.json',
                             source_checkpoint if args.resume else checkpoint, cycle, args=args, resume_plan=resume_plan)
                return 0
            if args.resume:
                claim_resume(args.resume, evidence/'checkpoint.json')
            connection.send({'command': 'arm'})
            connection.wait('armed')
            cycle_number = 1
            while True:
                stage = contract.next_stage(checkpoint)
                if stage is None:
                    if not cycle:
                        break
                    # Wrapped history is evidence, never another executable checkpoint.
                    atomic_json(evidence/('cycle-%06d.json' % cycle_number),
                                dict(artifact='completed_cycle', cycle_number=cycle_number, checkpoint=checkpoint))
                    connection.send({'command': 'next_cycle', 'cycle_number': cycle_number+1})
                    ready = connection.wait('cycle_ready')
                    if ready['cycle_number'] != cycle_number+1:
                        raise RuntimeError('Número de ciclo remoto inesperado')
                    checkpoint = contract.validate_checkpoint(ready['checkpoint'], profile)
                    if checkpoint != contract.new_checkpoint(profile, policy=policy, execution_profile=execution_profile):
                        raise RuntimeError('Inicio de ciclo remoto inesperado')
                    atomic_json(evidence/'checkpoint.json', checkpoint)
                    cycle_number += 1
                    print('Ciclo '+str(cycle_number)+' preparado; siguiente=get1.', flush=True)
                    stage = contract.next_stage(checkpoint)
                if should_pause(checkpoint, stop.requested):
                    break
                message = {'command': 'stage', 'stage': stage}
                if policy == 'ask' and stage == 'verify_held':
                    confirm('Compruebe caja superior separada de la inferior, sujeta estable por ambas abrazaderas y libre para retroceder.', 'SUJETA')
                    message['confirmed_box'] = 'held'
                elif policy == 'ask' and stage == 'deposit':
                    confirm('Compruebe alineación, apoyo y espacio para el depósito WRC actual. Esta tarea incluye apertura de abrazaderas.', 'DEPOSITAR')
                elif policy == 'ask' and stage == 'verify_released':
                    confirm('Compruebe caja apoyada y liberada, abrazaderas vacías y recorrido HOME libre.', 'LIBRE')
                    message['confirmed_box'] = 'released'
                subprocess.run(['bash', str(ROOT/'scripts/lib/cruzr_contact_motion_lock.sh'), 'improved-scenario1:'+stage],
                               check=True, start_new_session=True)
                if should_pause(checkpoint, stop.requested):
                    break
                # Local intent prevents reuse of a stale successful checkpoint after a link loss.
                checkpoint = contract.begin_stage(checkpoint, stage)
                atomic_json(evidence/'checkpoint.json', checkpoint)
                print('Etapa '+str(contract.STAGES.index(stage)+1)+'/'+str(len(contract.STAGES))+
                      ': '+stage_label(stage), flush=True)
                connection.send(message)
                connection.wait('stage_complete', timeout=420)
                checkpoint = contract.validate_checkpoint(json.loads((evidence/'checkpoint.json').read_text()), profile)
            finish_connection(connection)
            if stop.requested:
                report_pause(wrapper, evidence/'checkpoint.json', checkpoint, cycle, args=args)
                return 0
            if stop_after == 'navigate_get1':
                print('GET1_ALCANZADO; prueba de navegación terminada, sin agarre.')
            elif stop_after == 'navigate_put1':
                print('PUT1_ALCANZADO; caja sujeta (evidencia: '+policy+
                      '); depósito no ejecutado. Sesión finalizada antes de deposit.')
            elif args.resume and stop_after == 'verify_home':
                print('REANUDACION_COMPLETADA_HOME_MEDIDO; desde='+resume_plan['stage']+
                      '; evidencia de caja: '+policy)
            else:
                print(('CAJA_SUJETA_'+('ASUMIDA' if policy == 'assume' else 'VERIFICADA')+'; ciclo pausado.')
                      if stop_after == 'verify_held' else 'CICLO_COMPLETO_HOME_MEDIDO; evidencia de caja: '+policy)
            print('Checkpoint: '+str(evidence/'checkpoint.json'))
            return 0
        finally:
            if connection:
                connection.close()


def main(argv=None, *, policy='ask', execution_profile='standard_v1'):
    return run_args(parser(policy, execution_profile).parse_args(argv))


def run_args(args):
    with StageStop(is_moving(args) and args.execution_profile == 'optimistic_v1') as stop:
        return _main(args, stop)


def entrypoint(argv=None, *, policy='ask', execution_profile='standard_v1'):
    """Report read-only failures without implying an interrupted movement."""
    args = parser(policy, execution_profile).parse_args(argv)
    try:
        return run_args(args)
    except SensorCalibrationPending:
        print('SENSORES_SIN_CUALIFICAR: faltan referencias de fuerza/par por postura para distinguir sujeción y liberación.', file=sys.stderr)
        print('No se conectó al robot ni se envió movimiento. --check permite inspeccionar la telemetría; '
              '--sensor-profile requiere un perfil cualificado.', file=sys.stderr)
        return 78
    except (Exception, KeyboardInterrupt) as error:
        if is_moving(args):
            print('ESCENARIO_INTERRUMPIDO: '+str(error), file=sys.stderr)
            print('Sin nuevos intentos ni HOME automático. Un estado indeterminado requiere recuperación y comprobación física.', file=sys.stderr)
        else:
            print('CHECK_FALLIDO: '+str(error), file=sys.stderr)
            print('No se envió ninguna orden de movimiento.', file=sys.stderr)
        return 78


if __name__ == '__main__':
    raise SystemExit(entrypoint())
