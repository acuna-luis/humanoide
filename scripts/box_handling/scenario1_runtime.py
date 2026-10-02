"""Transient Motion-host supervisor for the improved scenario; no installer.

Loaded in memory by scenario1_cli. All robot commands are bounded and go through
the native client. stdin carries commands and a renewable PC heartbeat.
"""
import base64
from concurrent.futures import ThreadPoolExecutor
import fcntl
import hashlib
import json
import math
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
import urllib.request

if __package__:
    from . import scenario1_table90 as table90
    from . import scenario1_checks as checks, scenario1_contract as contract
    from . import scenario1_sensors as sensors
    from . import scenario1_dependencies as dependencies
    from . import scenario1_box_alignment as box_alignment
    from . import scenario1_perception as perception
    from . import scenario1_nav_correction as nav_correction
    from . import scenario1_resume as resume
    from . import scenario1_live_health as live_health
    from .scenario1_session import ProcessSession
    from scripts.lib.cruzr_home_posture_gate import BODY_ACTUATOR_ALIASES, classify
    from .front_sps_session import check_sps_discovery
else:
    import scenario1_table90 as table90
    import scenario1_checks as checks
    import scenario1_contract as contract
    import scenario1_sensors as sensors
    import scenario1_dependencies as dependencies
    import scenario1_box_alignment as box_alignment
    import scenario1_perception as perception
    import scenario1_nav_correction as nav_correction
    import scenario1_resume as resume
    import scenario1_live_health as live_health
    from scenario1_session import ProcessSession
    from cruzr_home_posture_gate import BODY_ACTUATOR_ALIASES, classify
    from front_sps_session import check_sps_discovery

SETUP = 'source /opt/walker/setup.bash; export ROS2CLI_DISABLE_DAEMON=1 ROSA_MIDDLE_WARE=cyclone ROSA_USE_SHM=OFF; '
ROS_SETUP = 'source /opt/ros/humble/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; '
TASKS = {'enable_vision': ('vision/enable_transport_vision_switch', 20),
         'grasp': ('local_front_box/separate_right_cruzr', 45),
         'retreat': ('cruzr/mobot_back_20', 30),
         'deposit': ('wrc_cruzr/put_cruzr_wrc_low', 120),
         'home': ('cruzr/home', 60)}


def atomic_json(path, value):
    path = Path(path)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, prefix=path.name+'.', delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(value, stream, allow_nan=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    temporary.replace(path)
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def code_command(source, arguments=()):
    code = 'import base64;exec(compile(base64.b64decode(%r),"scenario1-memory","exec"))' % base64.b64encode(source.encode()).decode()
    return ['python3', '-u', '-B', '-c', code, *arguments]


def guarded_adapter_source(root, session, guard_source):
    """Two captures at the vendor's actual perception phase, after head setup.

    The installed adapter/SDK remain untouched. Existing result deadlines still
    apply: slow/inconsistent perception fails before a pose reaches MetaClamp.
    """
    return '''import json,runpy,socket,sys,time
from pathlib import Path
root=ROOT_VALUE
session=Path(SESSION_VALUE)
sys.path.insert(0,root)
guard={}
exec(compile(GUARD_VALUE,'scenario1_perception.py','exec'),guard)
import front_sps_contract as contract
original=contract.select_report
original_position=contract.validate_position
def position_diagnostic(detail):
 entry=dict(detail,time_ns=time.time_ns())
 with (session/'selection.jsonl').open('a') as stream:
  stream.write(json.dumps(entry,allow_nan=False)+'\\n')
def observed_position(pose):
 return guard['observe_position_rejection'](original_position,pose,contract.POSITION_BOUNDS_M,position_diagnostic)
contract.validate_position=observed_position
def capture(timeout):
 if timeout<=0:raise TimeoutError('No remaining native perception budget')
 with socket.socket(socket.AF_UNIX) as conn:
  conn.settimeout(timeout)
  conn.connect(str(session/'perception.sock'))
  conn.sendall(b'capture\\n')
  with conn.makefile('rb') as stream:
   raw=stream.readline(2000001)
  if len(raw)>2000000 or not raw.endswith(b'\\n'):
   raise ValueError('Malformed second perception capture')
  result=json.loads(raw)
  if 'error' in result:raise ValueError(result['error'])
  return result['report']
def stable(report,now_ns):
 remaining=8.0-max(0,(time.time_ns()-report['request_ns'])/1e9)
 result=guard['stable_report'](report,now_ns,original,lambda:capture(remaining),time.time_ns)
 reference=session/'box-alignment-reference.json'
 if reference.exists():guard['guard_selection'](result,json.loads(reference.read_text()))
 return result
contract.select_report=stable
sys.argv=[root+'/front_sps_native.py','--session',str(session)]
runpy.run_path(root+'/front_sps_native.py',run_name='__main__')
'''.replace('ROOT_VALUE', repr(root)).replace('SESSION_VALUE', repr(str(session))).replace('GUARD_VALUE', repr(guard_source))


class Runtime:
    def __init__(self, payload, emit=None):
        self.payload = payload
        if payload.get('profile') is not None and table90.is_table90(payload['profile']):
            _, deposit_hashes = table90.validate_bundle(payload.get('deposit_bundle'))
            if any(payload.get('extra_hashes', {}).get(path) != digest
                   for path, digest in dict(deposit_hashes, **table90.CURRENT_MODEL_PINS).items()):
                raise ValueError('Table90 dependency pins are missing or changed')
            if payload.get('mode') != 'check':
                table90.require_motion_ready(payload['profile'], payload['checkpoint']['stop_after'],
                                             payload['checkpoint'].get('entry_stage', 'navigate_get1'))
        self.emit = emit or (lambda event, **values: print(json.dumps(
            dict(event=event, time_ns=time.time_ns(), **values), allow_nan=False), flush=True))
        self.commands = queue.Queue()
        self.stop = threading.Event()
        self.last_heartbeat = time.monotonic()
        self.session = None
        self.adapters = []
        self.logs = []
        self.armed = False
        self.checkpoint = payload['checkpoint']
        self.lock = None
        self.points = None
        self.container_identity = None
        self.dependency_identity = None
        self.session_deadline = None
        self.lease_lock = threading.Lock()
        self.policy = payload.get('policy', self.checkpoint.get('policy', 'ask'))
        if self.policy != self.checkpoint.get('policy', 'ask'):
            raise ValueError('Checkpoint confirmation policy differs from entrypoint')
        self.execution_profile = payload.get('execution_profile', 'standard_v1')
        if self.execution_profile != contract.execution_profile(self.checkpoint):
            raise ValueError('Checkpoint execution profile differs from entrypoint')
        self.live_monitor_enabled = False
        self.last_action_end_ns = None
        self.sensor_process = None
        self.sensor_min_stamp_ns = 0
        self.action_sessions = {}
        self.health_session = None
        self.box_association = None
        self.resume_plan = None
        self.resume_validated = False
        self.cycle_count = contract.cycle_count(payload.get('cycle_count', 1))
        self.cycle_index = 1
        if self.cycle_count > 1:
            contract.validate_checkpoint(self.checkpoint, payload['profile'])
        if self.cycle_count > 1 and (
                self.execution_profile != 'optimistic_v1' or self.policy != 'assume' or
                self.checkpoint['version'] != 2 or self.checkpoint['stop_after'] != 'verify_home' or
                self.checkpoint['completed'] or self.checkpoint['in_flight'] is not None or
                self.checkpoint['failure'] is not None or payload.get('resume_plan') is not None):
            raise ValueError('MULTI_CYCLE_REQUIRES_FRESH_FULL_OPTIMISTIC_RUN')
        self.perception_offset = 0
        self.perception_last_read = float('-inf')
        if payload.get('resume_plan') is not None:
            self.resume_plan = resume.plan_resume(payload['resume_source_checkpoint'], payload['profile'],
                                                 **payload['resume_options'])
            if self.resume_plan != payload['resume_plan'] or self.resume_plan['checkpoint'] != self.checkpoint:
                raise ValueError('RESUME_PLAN_CHANGED: origen o segmento no coinciden')

    def timed(self, label, function, *args, **kwargs):
        started = time.monotonic()
        try:
            return function(*args, **kwargs)
        finally:
            self.emit('timing', stage=self.checkpoint.get('in_flight'), operation=label,
                      elapsed_s=round(time.monotonic()-started, 6))

    def receive(self):
        try:
            for line in sys.stdin:
                message = json.loads(line)
                if message == {'command': 'heartbeat'}:
                    self.last_heartbeat = time.monotonic()
                else:
                    self.commands.put(message)
        finally:
            self.stop.set()

    def watchdog(self):
        try:
            while not self.stop.wait(0.5):
                if (time.monotonic() - self.last_heartbeat > 12 or
                        self.session_deadline is not None and time.monotonic() >= self.session_deadline):
                    self.stop.set()
                    break
                if self.armed and self.policy == 'sensors':
                    self.sensor_stream_alive()
                self.check_workers()
                if self.live_monitor_enabled:
                    self.check_live_health()
                self.write_lease()
        except BaseException as exc:
            self.stop.set()  # No silent watchdog failure; existing lease expires.
            self.emit('error', reason='WATCHDOG: '+str(exc))
        finally:
            self.stop.set()
            self.write_lease()
            if self.session:
                (self.session/'stop').touch()

    def write_lease(self):
        with self.lease_lock:
            if self.session:
                atomic_json(self.session/'control-lease.json',
                            {'deadline': 0 if self.stop.is_set() else time.monotonic()+4})

    def connected(self):
        if self.stop.is_set() or time.monotonic()-self.last_heartbeat > 12:
            raise RuntimeError('PC_HEARTBEAT_LOST: no se permiten nuevas órdenes')
        if self.session_deadline is not None and time.monotonic() >= self.session_deadline:
            self.stop.set()
            raise RuntimeError('SESSION_EXPIRED: no se permiten nuevas órdenes')
        if self.armed and any(process.poll() is not None for process in self.adapters):
            self.stop.set()
            raise RuntimeError('SPS_ADAPTER_LOST: no se permiten nuevas órdenes')
        if self.armed and self.policy == 'sensors':
            self.sensor_stream_alive()
        self.check_workers()
        if self.live_monitor_enabled:
            self.check_live_health()

    def check_workers(self):
        for worker in ([self.health_session] if self.health_session else []) + list(self.action_sessions.values()):
            if worker.failed or worker.process.poll() is not None:
                self.stop.set()
                raise RuntimeError('PERSISTENT_WORKER_LOST: no se permiten nuevas órdenes')

    def start_health(self):
        if self.health_session is not None:
            return
        self.create_session()
        arguments = ['--session', str(self.session)]
        if self.execution_profile == 'optimistic_v1':
            arguments.append('--live-health')
        command = code_command(self.payload['health_worker'], arguments)
        self.health_session = ProcessSession(['docker', 'exec', '-i', self.native_container,
            'bash', '-lc', SETUP+'exec '+shlex.join(command)],
            lambda event: self.emit('health_worker', detail=event))

    def health_request(self, command, **parameters):
        self.connected()
        self.start_health()
        rows = self.health_session.call({'command': command, **parameters}, timeout=15)
        reports = [event for event in rows if event['event'] == command+'_result']
        if len(reports) != 1:
            raise RuntimeError('HEALTH_RESULT_UNCONFIRMED')
        return reports[0]

    def check_live_health(self, *, stationary=False, after_ns=None, require_home=False):
        snapshot = json.loads((self.session/'live-health.json').read_text())
        return live_health.validate_snapshot(snapshot, now_ns=time.time_ns(),
            now_monotonic_ns=time.monotonic_ns(), stationary=stationary,
            after_ns=after_ns, require_home=require_home)

    def start_live_monitor(self):
        """Warm up once, before arming; an incomplete cache is never an OK."""
        deadline = time.monotonic()+12
        while True:
            self.connected()
            try:
                self.check_live_health()
                break
            except (FileNotFoundError, live_health.LiveHealthPending):
                if time.monotonic() >= deadline:
                    raise RuntimeError('LIVE_HEALTH_NOT_READY: no se permite armar')
                time.sleep(0.02)
        self.live_monitor_enabled = True
        self.emit('live_health_ready', execution_profile=self.execution_profile)

    def quick_health(self):
        """Use the live safety cache; wait only briefly for post-result rest."""
        if not self.live_monitor_enabled:
            raise RuntimeError('LIVE_HEALTH_NOT_ARMED: no cached success fallback')
        deadline = time.monotonic()+0.5
        while True:
            self.connected()
            try:
                report = self.check_live_health(stationary=True, after_ns=self.last_action_end_ns)
                self.emit('live_health_transition', report=report,
                          after_ns=self.last_action_end_ns)
                return
            except live_health.LiveHealthPending as exc:
                if time.monotonic() >= deadline:
                    raise RuntimeError('LIVE_HEALTH_TRANSITION_UNCONFIRMED: '+str(exc)) from exc
                time.sleep(0.01)

    def sensor_stream_alive(self):
        """During motion check stream liveness, not stationary pose envelopes."""
        if self.sensor_process is None or self.sensor_process.poll() is not None:
            raise RuntimeError('SENSOR_WORKER_LOST')
        snapshot = json.loads((self.session/'sensors.json').read_text())
        now = time.time_ns()
        stamps = [snapshot['written_ns']]
        for series in (snapshot['ft']['left'], snapshot['ft']['right'], snapshot['joints']):
            stamps.extend([series[-1]['stamp_ns'], series[-1]['received_ns']])
        if any(type(stamp) is not int or not -100_000_000 <= now-stamp <= 800_000_000 for stamp in stamps):
            raise RuntimeError('SENSOR_STREAM_STALE: se revoca la autorización de comandos')

    def create_session(self):
        if self.session is not None:
            return
        self.session = Path(tempfile.mkdtemp(prefix='cruzr-scenario1-', dir='/tmp'))
        os.chmod(self.session, 0o700)
        self.session_deadline = time.monotonic()+900
        atomic_json(self.session/'lease.json', {'deadline': self.session_deadline})
        self.write_lease()

    def start_sensors(self):
        self.create_session()
        self.command(['docker', 'exec', self.ros_container, 'test', '-d', str(self.session)])
        log = (self.session/'sensor-worker.log').open('w')
        self.logs.append(log)
        command = code_command(self.payload['sensor_worker'], ['--session', str(self.session)])
        self.sensor_process = subprocess.Popen(['docker', 'exec', self.ros_container, 'bash', '-lc',
            ROS_SETUP+'exec '+shlex.join(command)], stdout=log, stderr=subprocess.STDOUT)
        end = time.monotonic()+10
        last_error = 'No samples'
        while time.monotonic() < end:
            self.connected()
            if self.sensor_process.poll() is not None:
                error = self.session/'sensors.error'
                raise RuntimeError('SENSOR_WORKER_FAILED: '+(error.read_text() if error.exists() else 'ver sensor-worker.log'))
            try:
                snapshot = json.loads((self.session/'sensors.json').read_text())
                report = sensors.inspect(snapshot, now_ns=time.time_ns())
            except (OSError, ValueError, KeyError, TypeError) as exc:
                last_error = str(exc)
                time.sleep(0.05)
                continue
            self.emit('sensor_check', report=report, snapshot=snapshot,
                      qualification=self.payload['sensor_profile']['qualification'])
            return
        raise RuntimeError('SENSOR_PREFLIGHT_FAILED: '+last_error)

    def verify_sensors(self, state):
        # Wait only for acquisition of a post-action window. Never repeat a
        # force/pose classification after it has contradicted the expected state.
        end = time.monotonic()+0.7
        while True:
            self.connected()
            self.sensor_stream_alive()
            snapshot = json.loads((self.session/'sensors.json').read_text())
            now = time.time_ns()
            cutoff = max(self.sensor_min_stamp_ns, now-sensors.WINDOW_NS)
            windows = [[row for row in series if row['stamp_ns'] > cutoff]
                       for series in (snapshot['ft']['left'], snapshot['ft']['right'], snapshot['joints'])]
            if all(len(rows) >= sensors.MIN_SAMPLES and
                   rows[-1]['stamp_ns']-rows[0]['stamp_ns'] >= sensors.MIN_WINDOW_NS for rows in windows):
                break
            if time.monotonic() >= end:
                raise RuntimeError('SENSOR_WINDOW_INCOMPLETE: falta una ventana fresca después de la acción')
            time.sleep(0.025)
        self.emit('sensor_observation', state=state, snapshot=snapshot)
        report = sensors.evaluate(snapshot, self.payload['sensor_profile'], state=state,
            now_ns=time.time_ns(), min_stamp_ns=self.sensor_min_stamp_ns)
        # Archive the input as well as the derived report; no successful report
        # can be manufactured by a PC command or a persisted checkpoint.
        self.emit('sensor_verification', state=state, report=report, snapshot=snapshot)
        return report

    @staticmethod
    def command(args, timeout=12):
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        if result.returncode:
            raise RuntimeError('Consulta fallida rc='+str(result.returncode)+': '+str(args[:3])+' '+result.stderr[-1000:])
        return result.stdout

    def docker(self, container, args, timeout=12, native=True):
        self.connected()
        setup = SETUP if native else ROS_SETUP
        return self.command(['docker', 'exec', container, 'bash', '-lc', setup+'exec '+shlex.join(args)], timeout)

    def native(self, args, timeout=12):
        return self.docker(self.native_container, args, timeout)

    def topic(self, topic):
        # Action status is retained and changes on transitions. Forcing VOLATILE
        # loses an idle publisher's last status. Use the proven CLI auto-QoS read;
        # telemetry still requires a newly published sample.
        qos = [] if topic == '/mc/manipulation/action/_action/status' else ['--qos-durability', 'volatile']
        try:
            return self.docker(self.ros_container, ['timeout', '8', 'ros2', 'topic', 'echo', '--once',
                '--no-daemon', *qos, topic], native=False)
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError('TOPIC_READ_FAILED '+topic+': '+str(exc)) from exc

    def discover(self):
        ids = self.command(['docker', 'ps', '-q']).split()
        if not ids:
            raise RuntimeError('No hay contenedores en ejecución')
        inventory = json.loads(self.command(['docker', 'inspect', *ids]))
        found = checks.discover_containers(inventory)
        self.native_container, self.ros_container = found['native'], found['ros2']
        identity = {row['Name'].lstrip('/'): [row['Id'], row['State']['StartedAt']] for row in inventory
                    if row['Name'].lstrip('/') in found.values()}
        if self.container_identity is not None and identity != self.container_identity:
            raise RuntimeError('CONTAINER_CHANGED: requiere una nueva revisión')
        self.container_identity = identity
        self.emit('containers', native=self.native_container, ros2=self.ros_container)

    def hashes(self):
        def collect(native):
            request = dependencies.collect_request(self.payload, native)
            container = self.native_container if native else self.ros_container
            command = code_command(dependencies.collector_source(), [json.dumps(request)])
            return json.loads(self.command(['docker', 'exec', container, *command], 20))
        with ThreadPoolExecutor(max_workers=2) as pool:
            native, ros2 = list(pool.map(collect, (True, False)))
        identity = dependencies.validate_reports(self.payload, native, ros2)
        if self.dependency_identity is not None and identity != self.dependency_identity:
            raise RuntimeError('DEPENDENCY_CHANGED_DURING_RUN')
        self.dependency_identity = identity
        self.emit('dependencies', **{k: v for k, v in identity.items() if k != 'extra'})

    def health(self, require_home=False):
        started = time.time()
        report = self.health_request('health', require_home=require_home)
        checks.parse_controller_response(report['controller'])
        checks.parse_idle_status(report['status'])
        values = report['safety']
        health = checks.parse_health(values['estop'], values['servo'], values['charger'], values['battery'])
        if len(report['actuator']) != 2:
            raise RuntimeError('Se requieren dos muestras articulares nuevas')
        measurements, previous_stamp = [], None
        for sample in report['actuator']:
            stamp = sample['header']['stamp']
            if type(stamp['sec']) is not int or type(stamp['nanosec']) is not int or not 0 <= stamp['nanosec'] < 10**9:
                raise RuntimeError('Marca temporal articular inválida')
            current_stamp = stamp['sec']+stamp['nanosec']/1e9
            now = time.time()
            if not started-0.1 <= current_stamp <= now+0.5 or now-current_stamp > 2 or (
                    previous_stamp is not None and current_stamp <= previous_stamp):
                raise RuntimeError('Muestra articular antigua o repetida')
            previous_stamp = current_stamp
            measurement = dict(line.split('=', 1) for line in classify(sample, 0.02))
            if require_home and measurement['MEASURED_HOME'] != '1':
                # Only inspect axes after the strict classifier validates their
                # coverage, aliases, numeric values, faults and rest. This is a
                # diagnostic of the rejected sample, never a recovery command.
                by_id = {item['id']: item for item in sample['act_item']}
                outside = [dict(joint=name, id=axis, position_rad=by_id[axis]['position'])
                           for name, aliases in BODY_ACTUATOR_ALIASES for axis in aliases
                           if axis in by_id and abs(by_id[axis]['position']) >= 0.02]
                self.emit('home_not_measured', posture=measurement, outside_home=outside,
                          stamp=stamp, tolerance_rad=0.02, physical_commands_sent=0)
                detail = '; '.join(f"{row['joint']}({row['id']})={row['position_rad']:.6f} rad"
                                   for row in outside)
                raise RuntimeError('HOME_NOT_MEASURED: se exige HOME 20D al inicio/final; '
                                   +detail+'; límite |posición| < 0.02 rad. '
                                   'Recuperación presencial antes de repetir; sin HOME automático')
            measurements.append(measurement)
        self.emit('health', safety=health, posture=measurements, home_required=require_home)
        return report

    def forward_perception(self, *, force=False):
        """Forward existing complete JSONL records without querying perception.

        Called on the action-event thread and at shutdown, never by the watchdog.
        Partial lines stay on disk for the next feedback; offsets prevent the
        final drain from repeating measurements already shown during grasp.
        """
        if self.session is None:
            return
        now = time.monotonic()
        if not force and now-self.perception_last_read < 0.1:
            return
        self.perception_last_read = now
        try:
            with (self.session/'selection.jsonl').open('rb') as stream:
                stream.seek(self.perception_offset)
                while True:
                    line = stream.readline()
                    if not line or not line.endswith(b'\n'):
                        break
                    self.perception_offset = stream.tell()
                    try:
                        detail = json.loads(line)
                        if not isinstance(detail, dict):
                            raise ValueError('not a perception event')
                    except (ValueError, UnicodeError):
                        self.emit('perception_log_warning', reason='Registro de percepción ilegible')
                        continue
                    self.emit('perception', detail=detail)
        except FileNotFoundError:
            pass  # No perception has been requested yet.
        except OSError as exc:
            # Presentation is not a new condition for authorizing movement.
            self.emit('perception_log_warning', reason='Lectura de registro de percepción: '+str(exc))

    def action_event(self, kind, detail):
        if kind == 'motion':
            self.forward_perception(force=detail.get('event') in ('result', 'error', 'request_complete'))
        self.emit('action', kind=kind, detail=detail)

    def action(self, kind, goal, timeout, *, correction=None):
        # A session is created before preflight. Reuse each endpoint's client;
        # keep one-shot mode for isolated diagnostics without a session.
        if correction is not None:
            if kind != 'navigation' or self.session is None:
                raise RuntimeError('CORRECTION_REQUIRES_GUARDED_NAVIGATION_SESSION')
            nav_correction.validate_spec(correction, goal=goal)
            nav_correction.require_motion_qualified()
        if self.session is not None:
            self.connected()
            if kind not in self.action_sessions:
                command = code_command(self.payload['action_client'], ['--serve', '--kind', kind,
                    '--lease-file', str(self.session/'control-lease.json')])
                self.action_sessions[kind] = ProcessSession(['docker', 'exec', '-i', self.native_container,
                    'bash', '-lc', SETUP+'exec '+shlex.join(command)],
                    lambda detail: self.action_event(kind, detail))
            request = {'goal': goal, 'timeout': timeout}
            if correction is not None:
                request['correction'] = correction
            rows = self.action_sessions[kind].call(request, timeout=timeout+18)
            results = [row for row in rows if row['event'] == 'result']
            if len(results) != 1:
                raise RuntimeError('ACTION_UNCONFIRMED: resultado terminal ausente o duplicado')
            self.last_action_end_ns = time.time_ns()
            return results[0]
        return self.one_shot_action(kind, goal, timeout)

    def one_shot_action(self, kind, goal, timeout):
        self.connected()
        arguments = ['--kind', kind, '--goal-json', json.dumps(goal), '--timeout', str(timeout)]
        if self.session:
            arguments += ['--lease-file', str(self.session/'control-lease.json')]
        cmd = code_command(self.payload['action_client'], arguments)
        process = subprocess.Popen(['docker', 'exec', self.native_container, 'bash', '-lc',
            SETUP+'exec '+shlex.join(cmd)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        results = []
        lines = queue.Queue()
        def read():
            for line in process.stdout:
                lines.put(line)
            lines.put(None)
        thread = threading.Thread(target=read, daemon=True)
        thread.start()
        end = time.monotonic()+timeout+18
        try:
            while time.monotonic() < end:
                try:
                    line = lines.get(timeout=0.25)
                except queue.Empty:
                    continue
                if line is None:
                    break
                try:
                    event = json.loads(line)
                    if not isinstance(event, dict) or 'event' not in event:
                        raise ValueError('not an action event')
                except (ValueError, TypeError):
                    self.emit('native_log', text=line.rstrip()[:3000])
                    continue
                self.action_event(kind, event)
                if event['event'] == 'result':
                    results.append(event)
            else:
                raise RuntimeError('CLIENT_DEADLINE: resultado físico indeterminado')
            rc = process.wait(timeout=2)
            if rc or len(results) != 1:
                raise RuntimeError('ACTION_UNCONFIRMED: fallo/rechazo o resultado terminal ausente')
            return results[0]
        finally:
            if process.poll() is None:
                if self.session:
                    self.stop.set()
                    self.write_lease()
                process.terminate()  # Transport only; never reported as robot cancellation.
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()

    def nav(self, command, args=None, timeout=12):
        result = self.action('navigation', {'command': command, 'arg_json': json.dumps(args or {})}, timeout)
        data = result['result']
        if result['status'] != 4 or not isinstance(data, dict):
            raise RuntimeError('Consulta de navegación fallida')
        desc = data.get('state', {}).get('desc')
        if not isinstance(desc, str) or re.search(r'ERROR|FAIL|ABORT|CANCEL|LOST|OBSTACLE', desc, re.I):
            raise RuntimeError('Navegación rechazó la consulta: '+str(desc))
        return data

    def map_state(self):
        current_map = json.loads(self.nav('get_map_name')['result_json'])['map_name']
        result = self.nav('check_state')
        states = re.findall(r'\bFSM_[A-Z_]+\b', result.get('dmsg', ''))
        if len(states) != 1 or states[0] not in ('FSM_WAITNAVIGATE', 'FSM_WAITRELOCATE', 'FSM_WAITSETMAP'):
            raise RuntimeError('Navegación ocupada o estado no reconocido')
        return current_map, states[0]

    def map_points(self):
        request = urllib.request.Request('http://192.168.11.3:30023/map/get/utars_nav_map',
            data=b'{}', headers={'Content-Type': 'application/json'}, method='POST')
        response = json.loads(urllib.request.urlopen(request, timeout=8).read())
        points = checks.validate_map_points(response)
        if self.points is not None and self.points != points:
            raise RuntimeError('MAP_POINTS_CHANGED: no continuar con otro destino')
        self.points = points
        return points

    def benchmark_checks(self, count, expected_map_state):
        """Measure repeated read-only checks with the same live clients."""
        if self.payload['mode'] != 'check' or self.armed or type(count) is not int or not 1 <= count <= 5:
            raise ValueError('BENCHMARK_REQUIRES_READ_ONLY_CHECK')
        for iteration in range(1, count+1):
            self.connected()
            started = time.monotonic()
            self.timed('containers', self.discover)
            self.timed('dependencies', self.hashes)
            self.timed('health', self.health,
                       require_home=(self.resume_plan['requirements']['home'] if self.resume_plan is not None
                                     else not self.checkpoint['completed']))
            if self.execution_profile == 'optimistic_v1':
                self.timed('live_health', self.quick_health)
            if self.timed('map_state', self.map_state) != expected_map_state:
                raise RuntimeError('MAP_STATE_CHANGED_DURING_CHECK')
            if expected_map_state == ('utars_nav_map', 'FSM_WAITNAVIGATE'):
                self.timed('pose', self.read_poses)
            self.emit('check_benchmark', iteration=iteration,
                      elapsed_s=round(time.monotonic()-started, 6))

    def prepare_map(self):
        current_map, state = self.map_state()
        if (current_map, state) == ('utars_nav_map', 'FSM_WAITNAVIGATE'):
            return  # This fresh query already established readiness; no duplicate pair.
        if current_map != 'utars_nav_map' or state == 'FSM_WAITSETMAP':
            result = self.nav('map_set', {'map_name': 'utars_nav_map'}, 90)
            if result['state']['desc'] not in ('VSLAM_LOAD_MAP_FINISHED', 'SUCCESS', 'SUCCEED'):
                raise RuntimeError('Carga de mapa no confirmada')
            state = 'FSM_WAITRELOCATE'
        if state == 'FSM_WAITRELOCATE':
            result = self.nav('relocation_start', {'map_name': 'utars_nav_map', 'target_point': {'mode': 'global'}}, 90)
            if result['state']['desc'] not in ('NAVIGATION_READY', 'SUCCESS', 'SUCCEED'):
                raise RuntimeError('Localización no confirmada')
        if self.map_state() != ('utars_nav_map', 'FSM_WAITNAVIGATE'):
            raise RuntimeError('Mapa/localización no listos')

    def read_poses(self):
        """Exercise the actual arrival reader, without certifying a destination."""
        started = time.time()
        report = self.health_request('pose')
        poses = report['poses']
        if len(poses) != 2:
            raise RuntimeError('Se requieren dos poses nuevas de navegación')
        measurements, previous = [], None
        for pose in poses:
            measured = checks.validate_pose_sample(pose, started, time.time(), previous)
            previous = measured['stamp']
            measurements.append(measured)
        self.emit('pose_check', measurements=measurements,
                  publisher_count=report.get('publisher_count'), arrival_verified=False)
        return poses, started

    def check_resume_entry(self, *, refresh_health=False):
        """Read-only gates for an explicit entry; never repeats a physical task."""
        if self.resume_plan is None:
            raise RuntimeError('RESUME_PLAN_REQUIRED')
        self.resume_validated = False
        requirements = self.resume_plan['requirements']
        self.connected()
        if refresh_health:
            self.timed('resume_containers', self.discover)
            self.timed('resume_dependencies', self.hashes)
            self.timed('resume_health', self.health, require_home=requirements['home'])
            self.map_points()
        if self.map_state() != ('utars_nav_map', 'FSM_WAITNAVIGATE'):
            raise RuntimeError('RESUME_MAP_NOT_READY')
        self.create_session()
        command = code_command(self.payload['resume_worker'],
                               ['--lease-file', str(self.session/'control-lease.json')])
        output = self.timed('resume_base', self.native, command, timeout=10)
        reports = [json.loads(line) for line in output.splitlines() if line.lstrip().startswith('{')]
        if (len(reports) != 1 or reports[0].get('event') != 'resume_base_check' or
                reports[0].get('stationary') is not True or
                type(reports[0].get('publishers')) is not int or reports[0]['publishers'] != 1):
            raise RuntimeError('RESUME_BASE_NOT_STATIONARY')
        self.emit('resume_base_check', report=reports[0])
        waypoint = requirements['waypoint']
        poses, started = self.read_poses()
        if waypoint:
            measurements, outside = self.arrival_measurements(waypoint,
                self.points[waypoint]['_expected_pose'], poses, started)
            if outside:
                raise RuntimeError('RESUME_WAYPOINT_NOT_CONFIRMED: '+str(outside[0]))
            self.emit('resume_arrival', point=waypoint, measurements=measurements)
        box = requirements['box_state']
        if self.policy == 'sensors' and box in ('held', 'released'):
            # A posture without qualified references stays blocked. Never
            # relabel the operator's selection as fresh sensor evidence.
            self.verify_sensors(box)
        self.resume_validated = True
        self.emit('resume_checked', stage=self.resume_plan['stage'], requirements=requirements,
                  source_sha256=self.resume_plan['source_sha256'], physical_commands_sent=0)

    def arrival_measurements(self, point, expected, poses, started):
        """Validate both samples even when the first has a correctable residual."""
        if len(poses) != 2:
            raise RuntimeError('Se requieren dos poses nuevas de navegación')
        measurements, outside, previous = [], [], None
        for pose in poses:
            try:
                measured = checks.validate_nav_pose(pose, expected, started, time.time(), previous,
                                                   point=point)
            except checks.ArrivalOutsideTolerance as exc:
                measured = exc.measurement
                outside.append(exc)
            previous = measured['stamp']
            measurements.append(measured)
        return measurements, outside

    def correction_preflight(self, expected):
        # Never relocalize, change a map, or recover a failed action here.
        self.connected()
        self.timed('correction_containers', self.discover)
        self.timed('correction_dependencies', self.hashes)
        self.timed('correction_health', self.health, require_home=True)
        if self.map_state() != ('utars_nav_map', 'FSM_WAITNAVIGATE'):
            raise RuntimeError('GET1_CORRECTION_MAP_NOT_READY')
        self.map_points()
        if self.points['get1']['_expected_pose'] != expected:
            raise RuntimeError('MAP_POINTS_CHANGED: no continuar con otro destino')
        return self.read_poses()

    @staticmethod
    def correction_envelope(measurements):
        if any(row['distance_m'] > nav_correction.POLICY['max_initial_distance_m'] + 1e-12 or
               row['yaw_error_deg'] > nav_correction.POLICY['max_initial_yaw_deg'] + 1e-12
               for row in measurements):
            raise ValueError('Arrival outside automatic correction envelope (0.05m / 5 degrees)')

    @staticmethod
    def correction_score(measurements):
        return max(max(row['distance_m']/row['distance_tolerance_m'],
                       row['yaw_error_deg']/row['yaw_tolerance_deg']) for row in measurements)

    def correct_get1(self, expected, measurements):
        policy = nav_correction.POLICY
        deadline = time.monotonic() + policy['total_budget_s']
        self.correction_envelope(measurements)
        previous_score = None
        for attempt in range(1, policy['max_corrections']+1):
            if time.monotonic() >= deadline:
                raise RuntimeError('GET1_CORRECTION_TOTAL_BUDGET_EXCEEDED')
            poses, started = self.correction_preflight(expected)
            measurements, outside = self.arrival_measurements('get1', expected, poses, started)
            if time.monotonic() >= deadline:
                raise RuntimeError('GET1_CORRECTION_TOTAL_BUDGET_EXCEEDED')
            if not outside:
                return measurements  # Fresh measurements can settle without another command.
            self.correction_envelope(measurements)
            try:
                nav_correction.require_motion_qualified()
            except RuntimeError as error:
                self.emit('get1_correction', phase='blocked_before_dispatch',
                          measurements=measurements,
                          qualification=nav_correction.qualification_report())
                distance_mm = max(row['distance_m'] for row in measurements) * 1000
                yaw_deg = max(row['yaw_error_deg'] for row in measurements)
                raise RuntimeError('%s Llegada medida: %.2f mm / %.3f grados; '
                                   'agarre no iniciado.' % (error, distance_mm, yaw_deg)) from error
            score = self.correction_score(measurements)
            if previous_score is not None and previous_score-score < .1-1e-12:
                raise RuntimeError('GET1_CORRECTION_NO_IMPROVEMENT')
            references, previous = [], None
            for pose in poses:
                measured = checks.validate_pose_sample(pose, started, time.time(), previous)
                previous = measured['stamp']
                references.append({key: measured[key] for key in ('x', 'y', 'yaw', 'stamp_ns')})
            first, last = references
            yaw_change = abs(math.atan2(math.sin(last['yaw']-first['yaw']),
                                        math.cos(last['yaw']-first['yaw'])))
            if (math.hypot(last['x']-first['x'], last['y']-first['y']) > .005+1e-12 or
                    yaw_change > math.radians(1)+1e-12):
                raise RuntimeError('GET1_CORRECTION_POSE_UNSTABLE')
            spec = nav_correction.make_spec(expected, last, attempt)
            target = dict(expected, map_name='utars_nav_map', mode='free_nav', level=1,
                          speed={'linear': {'x': .05, 'y': .01, 'z': 0.},
                                 'angular': {'x': 0., 'y': 0., 'z': .15}})
            # The request speed is not trusted as a controller guarantee: the
            # action client independently monitors actual map/odom telemetry.
            goal = {'command': 'navigation_start', 'arg_json': json.dumps({'target_point': target})}
            if self.session is None:
                raise RuntimeError('CORRECTION_REQUIRES_GUARDED_NAVIGATION_SESSION')
            atomic_json(self.session/'get1-correction.json', dict(phase='in_flight', spec=spec))
            self.emit('get1_correction', attempt=attempt, phase='start',
                      measurements=measurements, spec=spec)
            remaining = deadline-time.monotonic()
            if remaining <= 0:
                raise RuntimeError('GET1_CORRECTION_TOTAL_BUDGET_EXCEEDED')
            result = self.action('navigation', goal, min(policy['action_timeout_s'], remaining),
                                 correction=spec)
            contract.validate_navigation_result(result)
            if self.map_state() != ('utars_nav_map', 'FSM_WAITNAVIGATE'):
                raise RuntimeError('GET1_CORRECTION_MAP_NOT_READY')
            poses, started = self.read_poses()
            measurements, outside = self.arrival_measurements('get1', expected, poses, started)
            if time.monotonic() >= deadline:
                raise RuntimeError('GET1_CORRECTION_TOTAL_BUDGET_EXCEEDED')
            atomic_json(self.session/'get1-correction.json', dict(
                phase='measured', spec=spec, measurements=measurements, within_tolerance=not outside))
            self.emit('get1_correction', attempt=attempt, phase='measured',
                      measurements=measurements, within_tolerance=not outside)
            if not outside:
                return measurements
            self.correction_envelope(measurements)
            if score-self.correction_score(measurements) < .1-1e-12:
                raise RuntimeError('GET1_CORRECTION_NO_IMPROVEMENT')
            previous_score = score
        raise RuntimeError('GET1_CORRECTION_LIMIT: no se alcanzaron 2 cm / 2 grados')

    def navigate(self, point):
        self.prepare_map()
        self.map_points()
        self.timed('pose', self.read_poses)  # Broken telemetry must block before motion.
        target = dict(self.points[point])
        expected = dict(target.pop('_expected_pose'))
        result = self.action('navigation', {'command': 'navigation_start',
            'arg_json': json.dumps({'target_point': target})}, 180)
        contract.validate_navigation_result(result)
        if self.map_state() != ('utars_nav_map', 'FSM_WAITNAVIGATE'):
            raise RuntimeError('Estado después de navegación no confirmado')
        poses, started = self.read_poses()
        measurements, outside = self.arrival_measurements(point, expected, poses, started)
        if outside:
            if point != 'get1':
                raise outside[0]
            measurements = self.correct_get1(expected, measurements)
        for measured in measurements:
            self.emit('arrival', point=point, measurement=measured)

    def stationary_base(self):
        # The persistent reader uses the exact resume odometry validator. Two
        # post-request samples are still required, without ROSA startup/shutdown
        # consuming the remaining lifetime of the just-measured box image.
        report = self.health_request('base', timeout=5)
        if (report.get('event') != 'base_result' or report.get('stationary') is not True or
                type(report.get('publishers')) is not int or report['publishers'] != 1):
            raise RuntimeError('BOX_ALIGNMENT_BASE_NOT_STATIONARY')
        self.emit('box_alignment_base', report=report)
        return report

    def capture_box(self):
        # The socket is owned by root inside the container (0600). Use that
        # existing namespace/owner without changing permissions or the worker.
        source = '''import json,socket,sys
from pathlib import Path
with socket.socket(socket.AF_UNIX) as conn:
 conn.settimeout(9)
 conn.connect(str(Path(sys.argv[1])/'perception.sock'))
 conn.sendall(b'capture\\n')
 with conn.makefile('rb') as stream:raw=stream.readline(2000001)
 if len(raw)>2000000 or not raw.endswith(b'\\n'):raise ValueError('Malformed perception reply')
 print(raw.decode(),end='')
'''
        reply = json.loads(self.native(code_command(source, [str(self.session)]), timeout=11))
        if set(reply) != {'report'}:
            raise RuntimeError('BOX_ALIGNMENT_PERCEPTION_FAILED: '+str(reply.get('error', 'invalid reply')))
        return box_alignment.observe(reply['report'], time.time_ns())

    def pose_references(self):
        poses, started = self.read_poses()
        references, previous = [], None
        for pose in poses:
            measured = checks.validate_pose_sample(pose, started, time.time(), previous)
            previous = measured['stamp']
            references.append({key: measured[key] for key in ('x', 'y', 'yaw', 'stamp_ns')})
        box_alignment.stable_base(references)
        return references

    def check_box_alignment_head(self):
        # Check this added task immediately before use, outside the persisted
        # dependency context: held/released checkpoints from earlier runs must
        # retain their original context and do not need this preparation.
        source = 'import hashlib,sys;from pathlib import Path;print(hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest())'
        actual = self.native(code_command(source, [box_alignment.HEAD_PATH])).strip()
        if actual != box_alignment.HEAD_SHA256:
            raise RuntimeError('BOX_ALIGNMENT_HEAD_TASK_CHANGED')
        self.emit('box_alignment_head_dependency', path=box_alignment.HEAD_PATH, sha256=actual)

    def capture_box_with_poses(self, history, phase):
        """Collect fresh map poses while the independent vision worker processes.

        Only capture runs on the background thread. The main thread remains
        the sole caller of the health session's sequential request protocol.
        """
        deadline = time.monotonic()+12
        with ThreadPoolExecutor(max_workers=1) as pool:
            capture = pool.submit(self.capture_box)
            while not capture.done():
                self.connected()
                if time.monotonic() >= deadline:
                    raise RuntimeError('BOX_ALIGNMENT_CAPTURE_DEADLINE')
                rows = self.pose_references()
                for row in rows:
                    box_alignment.stable_base([history[0], row])
                history.extend(rows)
                if len(history) > 256:
                    raise RuntimeError('BOX_ALIGNMENT_POSE_HISTORY_LIMIT')
            pending = capture.result()  # Failure is propagated, never recaptured.
            if time.monotonic() >= deadline:
                raise RuntimeError('BOX_ALIGNMENT_CAPTURE_DEADLINE')
        self.emit('box_alignment_capture', phase=phase, observation=pending,
                  map_samples=len(history), received_ns=time.time_ns())
        return pending

    def measure_box_for_pickup(self):
        self.box_association = None  # A previous successful capture cannot authorize this one.
        self.connected()
        self.discover()
        self.hashes()
        box_alignment.pickup_posture(self.health())
        odom_before = self.stationary_base()
        if self.map_state() != ('utars_nav_map', 'FSM_WAITNAVIGATE'):
            raise RuntimeError('BOX_ALIGNMENT_MAP_NOT_READY')
        self.map_points()
        before = self.pose_references()
        history = list(before)
        first = self.capture_box_with_poses(history, 'first')
        second = self.capture_box_with_poses(history, 'second')
        comparison = perception.validate_pair(first, second)
        after = self.pose_references()
        history.extend(after)
        matches = [box_alignment.match_pose_time(pending, history) for pending in (first, second)]
        self.emit('box_alignment_time_pair', matches=matches,
                  current_reference=after[-1], samples=len(history))
        odom_after = self.stationary_base()
        age_ns = time.time_ns()-second['stamp_ns']
        self.emit('box_alignment_freshness', image_stamp_ns=second['stamp_ns'],
                  age_ns=age_ns, max_age_ns=2_000_000_000)
        if not 0 <= age_ns <= 2_000_000_000:
            raise RuntimeError('BOX_ALIGNMENT_DETECTION_STALE_BEFORE_DISPATCH: age_ns='+str(age_ns))
        self.box_association = box_alignment.association_observation(first, second, odom_before, odom_after)
        self.emit('box_alignment', phase='observed', observation=second, stability=comparison,
                  reference=after[-1], association=self.box_association)
        return second, after[-1]

    def align_box_for_pickup(self, *, empty_entry=False):
        """Correct visual range BEFORE the native arm preparation, never retry it."""
        declared_empty = self.checkpoint['box_state'] == 'empty' or (
            empty_entry is True and self.checkpoint['in_flight'] == 'grasp')
        if not declared_empty or self.session is None:
            raise RuntimeError('BOX_ALIGNMENT_EMPTY_ENTRY_REQUIRED')
        policy = box_alignment.POLICY
        deadline = time.monotonic()+policy['total_budget_s']

        def budget():
            self.connected()
            remaining = deadline-time.monotonic()
            if remaining <= 0:
                raise RuntimeError('BOX_ALIGNMENT_TOTAL_BUDGET_EXCEEDED')
            return remaining

        # Review posture before any preparation; a rejected old grasp can have
        # arms out of HOME and must use explicit recovery, not this adjustment.
        box_alignment.pickup_posture(self.health(), observation=False)
        self.check_box_alignment_head()
        budget()
        self.emit('box_alignment', phase='prepare_head', task=box_alignment.HEAD_TASK)
        contract.validate_motion_result(self.action('motion',
            {'task_name': box_alignment.HEAD_TASK, 'yaml_args': '{}'}, min(20, budget())))
        pending, reference = self.measure_box_for_pickup()
        budget()
        anchor = self.box_association
        if anchor is None:
            raise RuntimeError('BOX_ALIGNMENT_ASSOCIATION_REQUIRED')
        total, attempt = 0., 0
        while True:
            budget()
            delta = box_alignment.displacement(pending)
            step = math.hypot(delta['x'], delta['y'])
            if step == 0:
                # This is a comparison reference, never a cached authorization.
                # The native adapter still captures twice and runs the XYZ gate.
                atomic_json(self.session/'box-alignment-reference.json', pending)
                self.emit('box_alignment', phase='ready', attempts=attempt,
                          total_requested_m=total, observation=pending)
                return
            if attempt >= policy['max_corrections'] or total+step > policy['max_total_m']+1e-12:
                raise RuntimeError('BOX_ALIGNMENT_LIMIT: no further visual correction allowed')
            attempt += 1
            old_violation = box_alignment.violation(pending)
            expected = box_alignment.target(reference, delta)
            spec = nav_correction.make_spec(expected, reference, attempt, point='box_pickup')
            target = dict(expected, map_name='utars_nav_map', mode='free_nav', level=1,
                          speed={'linear': {'x': .05, 'y': .01, 'z': 0.},
                                 'angular': {'x': 0., 'y': 0., 'z': .15}})
            goal = {'command': 'navigation_start', 'arg_json': json.dumps({'target_point': target})}
            record = dict(phase='in_flight', attempt=attempt, displacement_base_m=delta,
                          observation=pending, spec=spec, total_requested_m=total+step)
            atomic_json(self.session/'box-alignment.json', record)
            self.emit('box_alignment', **record)
            result = self.action('navigation', goal,
                min(nav_correction.POLICY['action_timeout_s'], budget()), correction=spec)
            contract.validate_navigation_result(result)
            # Success/rest still require two fresh map poses. Native navigation
            # has centimeter terminal precision; after this correspondence gate
            # the new visual measurement decides pickup or another bounded goal.
            references = self.pose_references()
            measurements = box_alignment.validate_arrival(references, expected)
            self.emit('box_alignment', phase='arrival', attempt=attempt, measurements=measurements,
                      pickup_verified=False)
            total += step
            pending, reference = self.measure_box_for_pickup()
            try:
                association = box_alignment.validate_association(anchor, self.box_association)
            except ValueError as exc:
                self.emit('box_alignment_association', passed=False, anchor=anchor,
                          current=self.box_association, reason=str(exc))
                raise
            self.emit('box_alignment_association', passed=True, measurement=association)
            atomic_json(self.session/'box-alignment.json', dict(record, phase='measured',
                observation=pending, reference=reference))
            if (box_alignment.violation(pending) > 0 and
                    old_violation-box_alignment.violation(pending) < policy['min_improvement_m']-1e-12):
                raise RuntimeError('BOX_ALIGNMENT_NO_IMPROVEMENT')

    def start_adapters(self):
        root = '/opt/cruzr-front-box/'+self.payload['bundle']['manifest']['id']
        for container, setup, filename, ready in [
            (self.ros_container, ROS_SETUP, 'front_sps_worker.py', 'worker.ready'),
            (self.native_container, SETUP, 'front_sps_native.py', 'native.ready')]:
            self.command(['docker', 'exec', container, 'test', '-d', str(self.session)])
            log = (self.session/(filename+'.log')).open('w')
            self.logs.append(log)
            command = ['python3', '-u', '-B', root+'/'+filename, '--session', str(self.session)]
            if filename == 'front_sps_native.py':
                command = code_command(guarded_adapter_source(root, self.session, self.payload['perception_guard']))
            process = subprocess.Popen(['docker', 'exec', container, 'bash', '-lc', setup+'exec '+shlex.join(command)],
                                       stdout=log, stderr=subprocess.STDOUT)
            self.adapters.append(process)
            end = time.monotonic()+12
            while not (self.session/ready).exists():
                self.connected()
                if process.poll() is not None or time.monotonic() >= end:
                    raise RuntimeError('SPS_ADAPTER_START_FAILED')
                time.sleep(0.05)

    def save(self):
        atomic_json(self.session/'checkpoint.json', self.checkpoint)
        if self.cycle_count > 1:
            directory = self.session/'cycles'/f'{self.cycle_index:04d}'
            created = not directory.exists()
            directory.mkdir(parents=True, exist_ok=True)
            atomic_json(directory/'checkpoint.json', self.checkpoint)
            if created:
                for parent in (directory.parent, self.session):
                    descriptor = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
                    try:
                        os.fsync(descriptor)
                    finally:
                        os.close(descriptor)
            if created or self.checkpoint['completed'] == list(contract.STAGES):
                atomic_json(self.session/'batch.json', dict(requested_cycles=self.cycle_count,
                    current_cycle=self.cycle_index,
                    completed_cycles=(self.cycle_index if self.checkpoint['completed'] == list(contract.STAGES)
                                      else self.cycle_index-1)))
            self.emit('checkpoint', checkpoint=self.checkpoint, cycle_index=self.cycle_index)
        else:
            self.emit('checkpoint', checkpoint=self.checkpoint)

    def next_cycle(self, message):
        if (not self.armed or self.cycle_count <= 1 or
                set(message) != {'command', 'cycle_index'} or message['command'] != 'next_cycle' or
                type(message['cycle_index']) is not int or
                message['cycle_index'] != self.cycle_index+1 or
                message['cycle_index'] > self.cycle_count):
            raise RuntimeError('NEXT_CYCLE_OUT_OF_ORDER')
        checkpoint = contract.next_cycle_checkpoint(self.checkpoint, self.payload['profile'])
        self.connected()
        self.timed('cycle_containers', self.discover)
        self.timed('cycle_dependencies', self.hashes)
        self.timed('cycle_live_health', self.quick_health)
        if self.map_state() != ('utars_nav_map', 'FSM_WAITNAVIGATE'):
            raise RuntimeError('NEXT_CYCLE_MAP_NOT_READY')
        self.map_points()  # Revalidate coordinates; never load/relocalize here.
        self.connected()
        home = self.check_live_health(stationary=True, after_ns=self.last_action_end_ns, require_home=True)
        self.emit('cycle_boundary', cycle_index=message['cycle_index'], home=home,
                  map_name='utars_nav_map', physical_commands_sent=0)
        self.checkpoint = checkpoint
        self.cycle_index = message['cycle_index']
        self.box_association = None
        self.save()
        self.emit('cycle_ready', cycle_index=self.cycle_index, cycle_count=self.cycle_count,
                  checkpoint=self.checkpoint)

    def stage(self, message):
        if not self.armed:
            raise RuntimeError('RUN_NOT_ARMED')
        if self.cycle_count > 1 and (type(message.get('cycle_index')) is not int or
                                    message['cycle_index'] != self.cycle_index):
            raise RuntimeError('STAGE_CYCLE_MISMATCH')
        stage = message['stage']
        started = time.monotonic()
        entry_box_state = self.checkpoint['box_state']
        self.checkpoint = contract.begin_stage(self.checkpoint, stage)
        self.save()  # Durable intent before an action is sent.
        try:
            self.connected()
            resume_entry = self.resume_plan is not None and not self.checkpoint['completed']
            logical_assumption = (self.policy == 'assume' and stage in ('verify_held', 'verify_released')
                                  and not resume_entry)
            if not logical_assumption:
                self.timed('containers', self.discover)
                self.timed('dependencies', self.hashes)
                if self.execution_profile == 'optimistic_v1' and not resume_entry and stage != 'verify_home':
                    self.timed('live_health', self.quick_health)
                else:
                    self.timed('health', self.health, require_home=stage == 'verify_home' or
                               bool(resume_entry and self.resume_plan['requirements']['home']))
            if resume_entry:
                # Interactive confirmation or local file checks may have taken
                # time since ready/arm. Entry conditions must still hold now.
                self.check_resume_entry()
            if self.policy == 'sensors' and stage in ('retreat', 'navigate_put1', 'deposit', 'home'):
                self.verify_sensors('released' if stage == 'home' else 'held')
            if stage.startswith('navigate_'):
                self.navigate(stage.removeprefix('navigate_'))
            elif stage in TASKS:
                if (stage == 'grasp' and self.resume_plan is not None and
                        self.resume_plan['requirements']['vision_prep'] and not self.checkpoint['completed']):
                    # A new session needs vision readiness even when entry skips
                    # enable_vision. This preparation is journaled after arming.
                    task, timeout = TASKS['enable_vision']
                    self.emit('resume_prerequisite', stage=stage, task=task)
                    contract.validate_motion_result(self.action('motion',
                        {'task_name': task, 'yaml_args': '{}'}, timeout))
                task, timeout = TASKS[stage]
                if stage == 'deposit':
                    task = self.payload.get('profile', {}).get('deposit', {}).get('task', task)
                    table90.require_motion_ready(self.payload.get('profile', {}), self.checkpoint['stop_after'], 'deposit')
                if stage == 'grasp' and self.execution_profile == 'optimistic_v1':
                    self.align_box_for_pickup(empty_entry=entry_box_state == 'empty')
                result = self.action('motion', {'task_name': task, 'yaml_args': '{}'}, timeout)
                contract.validate_motion_result(result)
                self.connected()
                self.sensor_min_stamp_ns = time.time_ns()
            elif stage not in ('verify_held', 'verify_released', 'verify_home'):
                raise RuntimeError('Unknown stage')
            verification = {}
            if stage in ('verify_held', 'verify_released'):
                state = 'held' if stage == 'verify_held' else 'released'
                if self.policy == 'ask':
                    verification['confirmed_box'] = message.get('confirmed_box')
                elif self.policy == 'assume':
                    verification.update(confirmed_box=state, verification_source='assumed')
                else:
                    verification.update(confirmed_box=state, verification_source='sensors',
                                        sensor_evidence=self.verify_sensors(state))
            elif message.get('confirmed_box') is not None:
                raise RuntimeError('Unexpected box confirmation')
            self.checkpoint = contract.complete_stage(self.checkpoint, stage,
                home_verified=stage == 'verify_home', **verification)
            self.save()
            self.emit('stage_complete', stage=stage, elapsed_s=round(time.monotonic()-started, 3),
                      logical_assumption=logical_assumption,
                      **({'cycle_index': self.cycle_index} if self.cycle_count > 1 else {}))
        except BaseException as exc:
            self.checkpoint = contract.fail_stage(self.checkpoint, stage, str(exc))
            self.save()
            raise

    def run(self):
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(sig, lambda signum, frame: self.stop.set())
        threading.Thread(target=self.receive, daemon=True).start()
        threading.Thread(target=self.watchdog, daemon=True).start()
        try:
            self.lock = open('/tmp/cruzr-front-sps.lock', 'a')
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if self.policy == 'sensors':
                sensors.validate_profile(self.payload['sensor_profile'], self.payload['profile']['id'],
                                         require_qualified=self.payload['mode'] != 'check')
            self.timed('containers', self.discover)
            self.timed('dependencies', self.hashes)
            remaining = contract.STAGES[contract.progress_index(self.checkpoint):
                                        contract.STAGES.index(self.checkpoint['stop_after'])+1]
            if self.execution_profile == 'optimistic_v1' and 'grasp' in remaining:
                self.check_box_alignment_head()
            check_sps_discovery(lambda command: subprocess.run(['docker', 'exec', self.native_container,
                'bash', '-lc', SETUP+'timeout 8 rosa '+command], capture_output=True, text=True, timeout=12))
            require_home = (self.resume_plan['requirements']['home'] if self.resume_plan is not None
                            else not self.checkpoint['completed'])
            self.timed('health', self.health, require_home=require_home)
            if self.execution_profile == 'optimistic_v1':
                self.start_live_monitor()
            points = self.map_points()
            map_name, nav_state = self.map_state()
            if (map_name, nav_state) == ('utars_nav_map', 'FSM_WAITNAVIGATE'):
                self.timed('pose', self.read_poses)
            context = dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                           containers=self.container_identity, dependencies=self.dependency_identity,
                           points=points)
            if self.execution_profile != 'standard_v1':
                context['execution_profile'] = self.execution_profile
            if self.policy == 'sensors':
                context['sensor_profile_sha256'] = hashlib.sha256(json.dumps(
                    self.payload['sensor_profile'], sort_keys=True, allow_nan=False).encode()).hexdigest()
            if self.payload.get('resume_context') is not None and context != self.payload['resume_context']:
                raise RuntimeError('RESUME_CONTEXT_CHANGED: robot reiniciado, tareas/contenedores/mapa cambiados')
            if self.policy == 'sensors':
                self.start_sensors()
            if self.resume_plan is not None:
                self.check_resume_entry()
                if self.payload['mode'] != 'check':
                    self.resume_validated = False  # Require the explicit resume handshake before arm.
            if self.payload.get('check_repetitions'):
                self.benchmark_checks(self.payload['check_repetitions'], (map_name, nav_state))
            self.emit('ready', points=points, map_name=map_name, nav_state=nav_state,
                      geometry='operator_assumed_existing', context=context)
            if self.payload['mode'] == 'check':
                if self.policy == 'sensors' and self.payload['sensor_profile']['qualification'] != 'qualified':
                    self.emit('sensor_profile_pending', reason='Referencias FT por postura sin cualificar; --run bloqueado antes de movimiento')
                    return 55
                return 0 if (map_name, nav_state) == ('utars_nav_map', 'FSM_WAITNAVIGATE') else 55
            while True:
                self.connected()
                try:
                    message = self.commands.get(timeout=0.25)
                except queue.Empty:
                    continue
                if message == {'command': 'finish'}:
                    if self.cycle_count > 1:
                        contract.next_cycle_checkpoint(self.checkpoint, self.payload['profile'])
                        if self.cycle_index != self.cycle_count:
                            raise RuntimeError('MULTI_CYCLE_INCOMPLETE')
                    return 0
                if message.get('command') == 'next_cycle':
                    self.next_cycle(message)
                    continue
                if message.get('command') == 'resume' and not self.armed:
                    if self.resume_plan is None or message['stop_after'] != self.checkpoint['stop_after']:
                        raise RuntimeError('RESUME_PLAN_REQUIRED')
                    self.check_resume_entry(refresh_health=True)
                    self.emit('resume_ready', checkpoint=self.checkpoint)
                    continue
                if message == {'command': 'arm'} and not self.armed:
                    if self.resume_plan is not None and not self.resume_validated:
                        raise RuntimeError('RESUME_ENTRY_NOT_CHECKED')
                    self.create_session()
                    remaining = contract.STAGES[contract.progress_index(self.checkpoint):
                                                contract.STAGES.index(self.checkpoint['stop_after'])+1]
                    if 'grasp' in remaining:
                        self.start_adapters()
                    self.armed = True
                    self.save()
                    self.emit('armed', remote_evidence=str(self.session))
                elif message.get('command') == 'stage':
                    self.stage(message)
                else:
                    raise RuntimeError('Unexpected supervisor command')
        except BaseException as exc:
            self.emit('error', reason=str(exc), physical_state='unconfirmed')
            return 78
        finally:
            self.stop.set()
            if self.session:
                self.write_lease()
                (self.session/'stop').touch()
                self.forward_perception(force=True)
            for worker in list(self.action_sessions.values()) + ([self.health_session] if self.health_session else []):
                worker.close()
            for process in self.adapters + ([self.sensor_process] if self.sensor_process else []):
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    self.emit('adapter_exit_unconfirmed')
            self.forward_perception(force=True)
            for log in self.logs:
                log.close()
            if self.lock:
                self.lock.close()


def main(payload):
    return Runtime(payload).run()
