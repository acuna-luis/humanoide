"""Transient Motion-host supervisor for the improved scenario; no installer.

Loaded in memory by scenario1_cli. All robot commands are bounded and go through
the native client. stdin carries commands and a renewable PC heartbeat.
"""
import ast
import base64
from concurrent.futures import ThreadPoolExecutor
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
import urllib.request
import xml.etree.ElementTree as ET

if __package__:
    from . import scenario1_checks as checks, scenario1_contract as contract
    from scripts.lib.cruzr_home_posture_gate import classify
    from .front_sps_session import check_sps_discovery, discovery_output
else:
    import scenario1_checks as checks
    import scenario1_contract as contract
    from cruzr_home_posture_gate import classify
    from front_sps_session import check_sps_discovery, discovery_output

TASK_ROOT = '/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/'
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
 return guard['stable_report'](report,now_ns,original,lambda:capture(remaining),time.time_ns)
contract.select_report=stable
sys.argv=[root+'/front_sps_native.py','--session',str(session)]
runpy.run_path(root+'/front_sps_native.py',run_name='__main__')
'''.replace('ROOT_VALUE', repr(root)).replace('SESSION_VALUE', repr(str(session))).replace('GUARD_VALUE', repr(guard_source))


class Runtime:
    def __init__(self, payload, emit=None):
        self.payload = payload
        self.emit = emit or (lambda event, **values: print(json.dumps(dict(event=event, **values), allow_nan=False), flush=True))
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
                self.write_lease()
        except BaseException:
            self.stop.set()  # No silent watchdog failure; existing lease expires.
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

    @staticmethod
    def command(args, timeout=12):
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        if result.returncode:
            raise RuntimeError('Consulta fallida: '+str(args[:3])+' '+result.stderr[-1000:])
        return result.stdout

    def docker(self, container, args, timeout=12, native=True):
        self.connected()
        setup = SETUP if native else ROS_SETUP
        return self.command(['docker', 'exec', container, 'bash', '-lc', setup+'exec '+shlex.join(args)], timeout)

    def native(self, args, timeout=12):
        return self.docker(self.native_container, args, timeout)

    def topic(self, topic):
        return self.docker(self.ros_container, ['timeout', '8', 'ros2', 'topic', 'echo', '--once',
            '--no-daemon', '--qos-durability', 'volatile', topic], native=False)

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
        bundle = self.payload['bundle']
        root = '/opt/cruzr-front-box/'+bundle['manifest']['id']
        expected = dict(bundle['manifest']['robot_files'], **bundle['manifest']['native_binaries'])
        expected.update(self.payload['extra_hashes'])
        for container in (self.native_container, self.ros_container):
            files = {root+'/'+name: sha for name, sha in bundle['manifest']['sources'].items()}
            if container == self.native_container:
                files.update(expected)
            output = self.command(['docker', 'exec', container, 'sha256sum', *files], 20)
            observed = {}
            for line in output.splitlines():
                sha, path = line.split(maxsplit=1)
                observed[path] = sha
            if observed != files:
                raise RuntimeError('DEPENDENCY_CHANGED: paquete SPS/tarea/biblioteca no coincide')
        home_path = TASK_ROOT+'cruzr/home.xml'
        home_hash = self.command(['docker', 'exec', self.native_container, 'sha256sum', home_path]).split()[0]
        pins = self.payload['home_pins']
        if home_hash not in pins['accepted']:
            raise RuntimeError('HOME no reconocido por el contrato actual')
        if home_hash != pins['direct']:
            library = '/opt/walker/manipulation_meta_tasks/lib/libmeta_move.so'
            if self.command(['docker', 'exec', self.native_container, 'sha256sum', library]).split()[0] != pins['meta']:
                raise RuntimeError('Biblioteca HOME no reconocida')
        vision = self.command(['docker', 'exec', self.native_container, 'cat', TASK_ROOT+'vision/enable_transport_vision_switch.xml'])
        tree = ET.fromstring(vision)
        actions = list(tree.iter('Action'))
        if len(actions) != 1 or actions[0].attrib != {'ID': 'MetaLook', 'start_vision_mode': 'transport_vision'}:
            raise RuntimeError('Prerrequisito de visión distinto del contrato MetaLook esperado')
        identity = dict(sps_package=bundle['manifest']['id'], home_sha256=home_hash,
                        vision_sha256=hashlib.sha256(vision.encode()).hexdigest(), extra=self.payload['extra_hashes'])
        if self.dependency_identity is not None and identity != self.dependency_identity:
            raise RuntimeError('DEPENDENCY_CHANGED_DURING_RUN')
        self.dependency_identity = identity
        self.emit('dependencies', sps_package=bundle['manifest']['id'], home_sha256=home_hash,
                  vision_sha256=hashlib.sha256(vision.encode()).hexdigest())

    def health(self, require_home=False):
        self.connected()
        controller = self.native(['timeout', '7', 'rosa', 'service', 'call',
            '/mc/controller_manager/list_controllers', 'rosa_control_msgs/srv/ListControllers', '{}'])
        checks.parse_controller_response(controller)
        checks.parse_idle_status(self.topic('/mc/manipulation/action/_action/status'))
        topics = ['/emb/estop_key_state', '/emb/servo_estop_key_state', '/emb/chrg_input_status', '/emb/battery_state']
        with ThreadPoolExecutor(max_workers=4) as pool:
            samples = list(pool.map(self.topic, topics))
        health = checks.parse_health(*samples)
        measurements = []
        previous_stamp = None
        for _ in range(2):
            started = time.time()
            sample = json.loads(discovery_output(self.native(['timeout', '8', 'rosa', 'topic', 'echo',
                '--once', '--no-daemon', '--qos-reliability', 'best_effort', '--qos-durability', 'volatile', '/mc/actuator_state',
                'mc_state_msgs/msg/ActuatorState'])))
            stamp = sample['header']['stamp']
            if type(stamp['sec']) is not int or type(stamp['nanosec']) is not int or not 0 <= stamp['nanosec'] < 10**9:
                raise RuntimeError('Marca temporal articular inválida')
            current_stamp = stamp['sec']+stamp['nanosec']/1e9
            now = time.time()
            if not started-0.1 <= current_stamp <= now+0.5 or now-current_stamp > 2 or (
                    previous_stamp is not None and current_stamp <= previous_stamp):
                raise RuntimeError('Muestra articular antigua o repetida')
            previous_stamp = current_stamp
            report = dict(line.split('=', 1) for line in classify(sample, 0.02))
            if require_home and report['MEASURED_HOME'] != '1':
                raise RuntimeError('HOME_NOT_MEASURED: se exige HOME 20D al inicio/final')
            measurements.append(report)
        self.emit('health', safety=health, posture=measurements, home_required=require_home)

    def action(self, kind, goal, timeout):
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
                self.emit('action', kind=kind, detail=event)
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

    def prepare_map(self):
        current_map, state = self.map_state()
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

    def navigate(self, point):
        self.prepare_map()
        self.map_points()
        target = dict(self.points[point])
        expected = target.pop('_expected_pose')
        result = self.action('navigation', {'command': 'navigation_start',
            'arg_json': json.dumps({'target_point': target})}, 180)
        contract.validate_navigation_result(result)
        if self.map_state() != ('utars_nav_map', 'FSM_WAITNAVIGATE'):
            raise RuntimeError('Estado después de navegación no confirmado')
        previous = None
        for _ in range(2):
            started = time.time()
            pose = json.loads(discovery_output(self.native(['timeout', '7', 'rosa', 'topic', 'echo',
                '--once', '--no-daemon', '--qos-durability', 'volatile', '/nav/robot_pose'])))
            measured = checks.validate_nav_pose(pose, expected, started, time.time(), previous)
            previous = measured['stamp']
            self.emit('arrival', point=point, measurement=measured)

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
        self.emit('checkpoint', checkpoint=self.checkpoint)

    def stage(self, message):
        if not self.armed:
            raise RuntimeError('RUN_NOT_ARMED')
        stage = message['stage']
        self.checkpoint = contract.begin_stage(self.checkpoint, stage)
        self.save()  # Durable intent before an action is sent.
        try:
            self.connected()
            self.discover()
            self.hashes()
            self.health(require_home=stage == 'verify_home')
            if stage.startswith('navigate_'):
                self.navigate(stage.removeprefix('navigate_'))
            elif stage in TASKS:
                task, timeout = TASKS[stage]
                result = self.action('motion', {'task_name': task, 'yaml_args': '{}'}, timeout)
                contract.validate_motion_result(result)
            elif stage not in ('verify_held', 'verify_released', 'verify_home'):
                raise RuntimeError('Unknown stage')
            self.checkpoint = contract.complete_stage(self.checkpoint, stage,
                confirmed_box=message.get('confirmed_box'), home_verified=stage == 'verify_home')
            self.save()
            self.emit('stage_complete', stage=stage)
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
            self.discover()
            self.hashes()
            check_sps_discovery(lambda command: subprocess.run(['docker', 'exec', self.native_container,
                'bash', '-lc', SETUP+'timeout 8 rosa '+command], capture_output=True, text=True, timeout=12))
            self.health(require_home=not self.checkpoint['completed'])
            points = self.map_points()
            map_name, nav_state = self.map_state()
            context = dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                           containers=self.container_identity, dependencies=self.dependency_identity,
                           points=points)
            if self.payload.get('resume_context') is not None and context != self.payload['resume_context']:
                raise RuntimeError('RESUME_CONTEXT_CHANGED: robot reiniciado, tareas/contenedores/mapa cambiados')
            self.emit('ready', points=points, map_name=map_name, nav_state=nav_state,
                      geometry='operator_assumed_existing', context=context)
            if self.payload['mode'] == 'check':
                return 0 if (map_name, nav_state) == ('utars_nav_map', 'FSM_WAITNAVIGATE') else 55
            while True:
                self.connected()
                try:
                    message = self.commands.get(timeout=0.25)
                except queue.Empty:
                    continue
                if message == {'command': 'finish'}:
                    return 0
                if message.get('command') == 'resume' and not self.armed:
                    proposed = contract.validate_checkpoint(message['checkpoint'], self.payload['profile'])
                    resumed = contract.resume_checkpoint(self.checkpoint, self.payload['profile'],
                        confirmed_box=self.checkpoint['box_state'], state_reconfirmed=True,
                        stop_after=proposed['stop_after'])
                    if proposed != resumed:
                        raise RuntimeError('Invalid resume checkpoint')
                    self.checkpoint = resumed
                    self.emit('resume_ready')
                    continue
                if message == {'command': 'arm'} and not self.armed:
                    self.session = Path(tempfile.mkdtemp(prefix='cruzr-scenario1-', dir='/tmp'))
                    os.chmod(self.session, 0o700)
                    self.session_deadline = time.monotonic()+900
                    atomic_json(self.session/'lease.json', {'deadline': self.session_deadline})
                    self.write_lease()
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
                selection = self.session/'selection.jsonl'
                if selection.exists():
                    for line in selection.read_text().splitlines():
                        self.emit('perception', detail=json.loads(line))
            for process in self.adapters:
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    self.emit('adapter_exit_unconfirmed')
            for log in self.logs:
                log.close()
            if self.lock:
                self.lock.close()


def main(payload):
    return Runtime(payload).run()
