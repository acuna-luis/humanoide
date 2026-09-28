#!/usr/bin/env python3
"""PC entry point; --check by default, explicit supervised --run only."""
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
import subprocess
import sys
import tempfile
import threading
import time

if __package__:
    from . import scenario1_contract as contract
    from .front_box_integration import build_bundle, TASK_ROOT, META_ROOT, SNAPSHOT
else:
    import scenario1_contract as contract
    from front_box_integration import build_bundle, TASK_ROOT, META_ROOT, SNAPSHOT

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MODULES = [('cruzr_home_posture_gate', ROOT/'scripts/lib/cruzr_home_posture_gate.py'),
           ('front_sps_session', HERE/'front_sps_session.py'),
           ('scenario1_contract', HERE/'scenario1_contract.py'),
           ('scenario1_checks', HERE/'scenario1_checks.py'),
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
    return dict(mode=mode, profile=profile, checkpoint=checkpoint, bundle=bundle,
                extra_hashes=extra, home_pins=dict(accepted=[pins[n] for n in names],
                    direct=pins['DIRECT_HOME_SHA'], meta=pins['OPEN_HOME_META_SHA']),
                action_client=(HERE/'scenario1_action_client.py').read_text(),
                perception_guard=(HERE/'scenario1_perception.py').read_text(),
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
    def __init__(self, payload, wifi, evidence):
        self.evidence = evidence
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
                        self.events.put(event)
                    except (ValueError, KeyError, TypeError) as exc:
                        self.events.put(dict(event='error', reason='Protocolo remoto inválido: '+str(exc)))
        finally:
            self.events.put(dict(event='eof'))

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
            if kind == 'action':
                detail = event['detail']
                if detail['event'] in ('accepted', 'rejected', 'result', 'cancel_requested', 'terminal_unknown'):
                    print('  '+json.dumps(detail, ensure_ascii=False), flush=True)
                elif detail['event'] == 'feedback':
                    print('  Progreso: '+json.dumps(detail, ensure_ascii=False), flush=True)
            elif kind == 'arrival':
                print('  Llegada medida: '+json.dumps(event, ensure_ascii=False), flush=True)
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


def parser():
    p = argparse.ArgumentParser(prog='force_improved_scenario1.sh',
        description='Escenario 1 supervisado; conserva la geometría actual. Por defecto sólo --check.')
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true', help='Comprobaciones completas sin iniciar adaptadores ni mover')
    mode.add_argument('--plan', action='store_true', help='Mostrar perfil y etapas sin conectar al robot')
    mode.add_argument('--run', action='store_true', help='Ejecutar con confirmaciones presenciales')
    mode.add_argument('--resume', type=Path, metavar='CHECKPOINT', help='Continuar sólo desde una pausa limpia con caja verificada')
    p.add_argument('--wifi', action='store_true', help='SSH mediante 192.168.42.2')
    p.add_argument('--stop-after', choices=('grasp', 'cycle'), default='cycle', help='grasp: terminar tras confirmar caja sujeta')
    p.add_argument('--profile', type=Path, default=HERE/'scenario1_current_geometry.json')
    p.add_argument('--evidence-dir', type=Path, help='Directorio nuevo para logs y checkpoint; por defecto fuera de Git')
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    stop_after = 'verify_held' if args.stop_after == 'grasp' else 'verify_home'
    profile = contract.validate_profile(json.loads(args.profile.read_text()), stop_after=stop_after)
    checkpoint = contract.new_checkpoint(profile, stop_after=stop_after)
    if args.resume:
        if args.resume.with_name(args.resume.name+'.consumed.json').exists():
            raise RuntimeError('Este checkpoint ya fue consumido por otra reanudación')
        checkpoint = contract.validate_checkpoint(json.loads(args.resume.read_text()), profile)
        # Structural check now; a fresh physical/runtime confirmation is still required below.
        candidate = contract.resume_checkpoint(checkpoint, profile, confirmed_box=checkpoint['box_state'],
            state_reconfirmed=True, stop_after=stop_after)
        if contract.next_stage(candidate) is None:
            raise RuntimeError('La reanudación solicitada no tiene etapas pendientes')
    moving = bool(args.run or args.resume)
    if moving and not sys.stdin.isatty():
        raise RuntimeError('Se requiere un terminal y operador junto al robot')
    print('Geometría: force_escenario1.sh actual; tareas y límites del proveedor conservados.')
    if args.plan:
        print(json.dumps(dict(profile=profile, stages=list(contract.STAGES[:contract.STAGES.index(stop_after)+1]),
            physical_validation='pending', automatic_retries=0), indent=2, ensure_ascii=False))
        return 0
    if moving:
        subprocess.run(['bash', str(ROOT/'scripts/lib/cruzr_contact_motion_lock.sh'), 'improved-scenario1'], check=True)
    evidence = args.evidence_dir or ROOT.parent/'Humanoide-vla-evidence'/(
        time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())+'_IMPROVED_SCENARIO1_'+str(os.getpid()))
    evidence.mkdir(parents=True, exist_ok=False)
    os.chmod(evidence, 0o700)
    atomic_json(evidence/'profile.json', profile)
    if not args.resume:
        atomic_json(evidence/'checkpoint.json', checkpoint)
    payload = make_payload('run' if moving else 'check', profile, checkpoint)
    if args.resume:
        payload['resume_context'] = json.loads((args.resume.parent/'context.json').read_text())
    atomic_json(evidence/'source-sha256.json', {name: hashlib.sha256(source.encode()).hexdigest()
        for name, source in payload['modules']} | {
            'action_client': hashlib.sha256(payload['action_client'].encode()).hexdigest(),
            'perception_guard': hashlib.sha256(payload['perception_guard'].encode()).hexdigest(),
            'scenario1_cli': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'entrypoint': hashlib.sha256((ROOT/'scripts/force_improved_scenario1.sh').read_bytes()).hexdigest()})
    print('Evidencia: '+str(evidence), flush=True)
    connection = None
    with ExitStack() as stack:
        for name in ('/tmp/cruzr_blue_workbin_cycle.lock', '/tmp/cruzr-improved-scenario1.lock'):
            lock = stack.enter_context(open(name, 'a'))
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            connection = Connection(payload, args.wifi, evidence)
            ready = connection.wait('ready')
            atomic_json(evidence/'context.json', ready['context'])
            print('Comprobaciones técnicas completadas; mapa='+ready['map_name']+' '+ready['nav_state'], flush=True)
            if not moving:
                rc = connection.process.wait(timeout=10)
                print('CHECK_OK' if rc == 0 else 'PREPARACION_REQUERIDA: --run prepara mapa/localización después de confirmar.')
                return rc
            if args.resume:
                state = checkpoint['box_state']
                confirm('Reanudación: confirme que la caja sigue '+('sujeta, separada y estable.' if state == 'held' else 'apoyada y liberada.')+
                        ' No debe haberse ejecutado otra tarea desde el checkpoint.', 'REANUDAR')
                checkpoint = contract.resume_checkpoint(checkpoint, profile, confirmed_box=state,
                    state_reconfirmed=True, stop_after=stop_after)
                # Runtime also receives the explicitly extended stop boundary.
                connection.send({'command': 'resume', 'checkpoint': checkpoint})
                connection.wait('resume_ready')
            confirm('Confirme abrazaderas '+('vacías y robot en HOME' if not args.resume else 'en el estado indicado')+
                    ', montaje original de recogida/depósito, trayectorias libres, ruedas en navegación, '
                    'cargador desconectado, paros liberados, modo automático, ningún otro mando y persona junto al paro.', 'CONTINUAR')
            if args.resume:
                claim_resume(args.resume, evidence/'checkpoint.json')
            connection.send({'command': 'arm'})
            connection.wait('armed')
            while (stage := contract.next_stage(checkpoint)) is not None:
                message = {'command': 'stage', 'stage': stage}
                if stage == 'verify_held':
                    confirm('Compruebe caja superior separada de la inferior, sujeta estable por ambas abrazaderas y libre para retroceder.', 'SUJETA')
                    message['confirmed_box'] = 'held'
                elif stage == 'deposit':
                    confirm('Compruebe alineación, apoyo y espacio para el depósito WRC actual. Esta tarea incluye apertura de abrazaderas.', 'DEPOSITAR')
                elif stage == 'verify_released':
                    confirm('Compruebe caja apoyada y liberada, abrazaderas vacías y recorrido HOME libre.', 'LIBRE')
                    message['confirmed_box'] = 'released'
                subprocess.run(['bash', str(ROOT/'scripts/lib/cruzr_contact_motion_lock.sh'), 'improved-scenario1:'+stage], check=True)
                # Local intent prevents reuse of a stale successful checkpoint after a link loss.
                checkpoint = contract.begin_stage(checkpoint, stage)
                atomic_json(evidence/'checkpoint.json', checkpoint)
                print('Etapa: '+stage, flush=True)
                connection.send(message)
                connection.wait('stage_complete', timeout=420)
                checkpoint = contract.validate_checkpoint(json.loads((evidence/'checkpoint.json').read_text()), profile)
            connection.send({'command': 'finish'})
            rc = connection.process.wait(timeout=15)
            if rc:
                raise RuntimeError('Supervisor terminó con error')
            print('CAJA_SUJETA_VERIFICADA; ciclo pausado.' if stop_after == 'verify_held' else 'CICLO_COMPLETO_HOME_MEDIDO')
            print('Checkpoint: '+str(evidence/'checkpoint.json'))
            return 0
        finally:
            if connection:
                connection.close()


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (Exception, KeyboardInterrupt) as error:
        print('ESCENARIO_INTERRUMPIDO: '+str(error), file=sys.stderr)
        print('Sin reintento ni HOME automático. Un estado indeterminado requiere recuperación y comprobación física.', file=sys.stderr)
        raise SystemExit(78)
