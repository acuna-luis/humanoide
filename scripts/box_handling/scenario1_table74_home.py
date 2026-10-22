#!/usr/bin/env python3
"""One HOME after an authenticated completed table74 lateral opening.

The source opening journal is durably consumed before one force_home.sh call.
No retry, reset, navigation, mode change or alternate HOME command is offered.
Success requires its native terminal AND two new measured complete 20D HOME
samples; it never follows from the opening result alone.
The default remains supervised. A caller may instead supply the exact pinned
recorded-recipe policy; that assumption never replaces live technical gates.
"""
import ast
import concurrent.futures
from contextlib import ExitStack
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
import uuid

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = 'scripts.box_handling'

if __package__:
    from . import scenario1_cli as cli
    from . import scenario1_checks as checks
    from . import scenario1_dependencies as dependencies
    from . import scenario1_table74_current_release as release
    from . import scenario1_table74_current_release_run as released
    from scripts.lib.cruzr_home_posture_gate import classify
else:
    import scenario1_cli as cli
    import scenario1_checks as checks
    import scenario1_dependencies as dependencies
    import scenario1_table74_current_release as release
    import scenario1_table74_current_release_run as released
    from cruzr_home_posture_gate import classify


PROFILE_PATH = Path(__file__).with_name('scenario1_table74_preparation.json')
NATIVE_NAME = 'walker-motion.manipulation_robot_app-1'  # force_home.sh contract
MAX_PROOF_BYTES = 16 * 1024 * 1024
HOME_TIMEOUT = 90
_WRAPPER = '''import json,subprocess,sys,time
command=json.loads(sys.argv[1]);start=time.time_ns()
try:
 p=subprocess.run(command,capture_output=True,text=True,timeout=9)
 result=dict(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
except subprocess.TimeoutExpired:
 result=dict(returncode=124,stdout='',stderr='bounded diagnostic query timeout')
print(json.dumps(dict(result,start_ns=start,finished_ns=time.time_ns())))
'''
_INVENTORY = '''import json,pathlib,subprocess
ids=subprocess.run(['docker','ps','-q'],capture_output=True,text=True,check=True,timeout=3).stdout.split()
if not ids:raise ValueError('No running containers')
rows=json.loads(subprocess.run(['docker','inspect',*ids],capture_output=True,text=True,check=True,timeout=4).stdout)
print(json.dumps(dict(boot_id=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),inventory=rows)))
'''


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def validate_open(proof, profile):
    """Authenticate completed opening without admitting it as another release."""
    if not isinstance(proof, dict) or set(proof) != set(released.FILES) | {'predecessor.json'}:
        raise ValueError('HOME requires the complete completed-opening proof chain')
    bundle = release.validate_bundle(proof['bundle.json'])
    if bundle['review']['reference']['stage'] != 'lateral_open':
        raise ValueError('HOME requires completed lateral opening, not support or pin relief')
    parent, admitted = released.validate_entry(proof['predecessor.json'], profile, bundle)
    info, goal = released._completed_trial(proof, profile, admitted, release.validate_bundle, parent)
    chain = parent['chain_bundles'] + [bundle]
    if len(chain) > 6:
        raise ValueError('Opening proof exceeds the bounded phase chain')
    info.update(chain_bundles=chain, predecessor_sha256=digest(proof),
                bundle_id=bundle['manifest']['id'], goal_id=goal, completed_stage='lateral_open')
    return info


def load_open(after, profile):
    after = Path(after)
    if (after/'trial.json.consumed.json').exists():
        raise RuntimeError('Opening journal already consumed; HOME retry is prohibited')
    raw = {}
    for name in (*released.FILES, 'predecessor.json'):
        path = after/name
        if path.stat().st_size > MAX_PROOF_BYTES:
            raise ValueError('Opening proof file exceeds 16 MiB')
        value = path.read_bytes()
        if len(value) > MAX_PROOF_BYTES:
            raise ValueError('Opening proof changed beyond size bound')
        raw[name] = value
    if sum(map(len, raw.values())) > 32*1024*1024:
        raise ValueError('Opening proof aggregate exceeds 32 MiB')
    proof = {name: ([json.loads(line) for line in value.decode().splitlines() if line.strip()]
                   if name == 'events.jsonl' else json.loads(value)) for name, value in raw.items()}
    return proof, validate_open(proof, profile), {name: hashlib.sha256(value).hexdigest() for name, value in raw.items()}


def execute(command, wifi=False):
    """Bounded SSH diagnostic read; commands are fixed by this module."""
    target = '192.168.42.2' if wifi else '192.168.11.2'
    env = dict(os.environ, CRUZR_INTERNAL_ASKPASS='1',
        SSH_ASKPASS=str(cli.ROOT/'scripts/cruzr_recover_to_home.sh'), SSH_ASKPASS_REQUIRE='force',
        DISPLAY=os.environ.get('DISPLAY', ':0'))
    process = subprocess.run(['setsid', '-w', 'ssh', '-T', '-o', 'StrictHostKeyChecking=yes',
        '-o', 'ConnectTimeout=5', '-o', 'ConnectionAttempts=1', '-o', 'PreferredAuthentications=password',
        '-o', 'PubkeyAuthentication=no', '-o', 'NumberOfPasswordPrompts=1', 'walker@'+target,
        shlex.join(['python3', '-B', '-c', _WRAPPER, json.dumps(command)])],
        env=env, capture_output=True, text=True, timeout=18)
    if process.returncode:
        raise RuntimeError('HOME diagnostic transport failed; no retry: '+process.stderr[-500:])
    row = json.loads(process.stdout)
    if (not isinstance(row, dict) or type(row.get('returncode')) is not int or row['returncode'] != 0 or
            type(row.get('start_ns')) is not int or type(row.get('finished_ns')) is not int or
            not 0 < row['start_ns'] <= row['finished_ns'] or
            row['finished_ns']-row['start_ns'] > 10_000_000_000):
        raise RuntimeError('HOME diagnostic read failed or timed out')
    return row


def _json_output(text):
    if type(text) is not str or len(text.encode()) > MAX_PROOF_BYTES:
        raise ValueError('Diagnostic JSON output invalid or oversized')
    start = text.find('{')
    if start < 0:
        raise ValueError('Diagnostic output has no JSON object')
    result, end = json.JSONDecoder().raw_decode(text[start:])
    if text[start+end:].strip() or not isinstance(result, dict):
        raise ValueError('Diagnostic JSON output has trailing data')
    return result


def _native(container, command, *, ros2=False):
    setup = '/opt/ros/humble/setup.bash' if ros2 else '/opt/walker/setup.bash'
    return ['docker', 'exec', container, 'bash', '-lc',
        'source '+setup+'; export ROS2CLI_DISABLE_DAEMON=1; timeout 7 '+shlex.join(command)]


class Reader:
    """Record every fixed read locally, compare live context and collect rest."""
    def __init__(self, evidence, wifi):
        self.evidence, self.wifi, self.sequence = Path(evidence), wifi, 0

    def query(self, command, label):
        # No shared sequence is mutated from the parallel workers.
        row = execute(command, self.wifi)
        cli.atomic_json(self.evidence/(label+'.json'), dict(command=command, result=row))
        return row

    def inventory(self, expected, label):
        document = _json_output(self.query(['python3', '-B', '-c', _INVENTORY], label)['stdout'])
        found = checks.discover_containers(document['inventory'])
        if found['native'] != NATIVE_NAME:
            raise RuntimeError('force_home.sh native container differs from discovered Motion; no dispatch')
        actual = {row['Name'].lstrip('/'): [row['Id'], row['State']['StartedAt']]
                  for row in document['inventory'] if row['Name'].lstrip('/') in found.values()}
        if document['boot_id'] != expected['boot_id'] or actual != expected['containers']:
            raise RuntimeError('HOME source boot or containers changed')
        return found

    def files(self, info, payload, found, label):
        reports = {}
        for role, native in (('native', True), ('ros2', False)):
            request = dependencies.collect_request(payload, native)
            row = self.query(['docker', 'exec', found[role], 'python3', '-B', '-c',
                dependencies.collector_source(), json.dumps(request)], label+'-'+role)
            reports[role] = _json_output(row['stdout'])
        identity = dependencies.validate_reports(payload, reports['native'], reports['ros2'])
        if identity != info['context']['dependencies']:
            raise RuntimeError('HOME source dependency identity changed')
        pins = {}
        for bundle in info['chain_bundles']:
            for path, value in bundle['manifest']['robot_files'].items():
                if path in pins and pins[path] != value:
                    raise ValueError('Conflicting completed-phase dependency pins')
                pins[path] = value
        request = dict(paths=sorted(pins), text_paths=[])
        row = self.query(['docker', 'exec', found['native'], 'python3', '-B', '-c',
            dependencies.collector_source(), json.dumps(request)], label+'-chain')
        if _json_output(row['stdout']) != {'hashes': pins}:
            raise RuntimeError('Completed opening or predecessor files changed')

    def health(self, found, label, *, require_home=False):
        queries = {}
        for key, topic in (('estop', 'estop_key_state'), ('servo', 'servo_estop_key_state'),
                           ('charger', 'chrg_input_status'), ('battery', 'battery_state')):
            queries[key] = _native(found['ros2'], ['ros2', 'topic', 'echo', '--once', '--no-daemon',
                '--qos-durability', 'volatile', '/emb/'+topic], ros2=True)
        # Preserve proven auto-QoS. Do not force transient_local or VOLATILE
        # onto this retained status publisher; freshness comes from new reads.
        queries['status'] = _native(found['ros2'], ['ros2', 'topic', 'echo', '--once', '--no-daemon',
            '/mc/manipulation/action/_action/status'], ros2=True)
        queries['controller'] = _native(found['native'], ['rosa', 'service', 'call',
            '/mc/controller_manager/list_controllers', 'rosa_control_msgs/srv/ListControllers', '{}'])
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            future = {pool.submit(self.query, command, label+'-'+key): key for key, command in queries.items()}
            rows = {future[job]: job.result() for job in concurrent.futures.as_completed(future)}
        safety = checks.parse_health(*(rows[key]['stdout'] for key in ('estop', 'servo', 'charger', 'battery')))
        controller = checks.parse_controller_response(rows['controller']['stdout'])
        status = checks.parse_idle_status(rows['status']['stdout'])
        samples, classifications, previous = [], [], None
        for index in range(2):
            row = self.query(_native(found['native'], ['rosa', 'topic', 'echo', '--once',
                '--qos-reliability', 'best_effort', '/mc/actuator_state']), label+'-actuator-'+str(index))
            sample = _json_output(row['stdout'])
            stamp = sample.get('header', {}).get('stamp', {})
            sec, ns = stamp.get('sec'), stamp.get('nanosec')
            if type(sec) is not int or sec < 0 or type(ns) is not int or not 0 <= ns < 10**9:
                raise ValueError('HOME actuator source timestamp invalid')
            stamp_ns = sec*10**9+ns
            if (not row['start_ns'] <= stamp_ns <= row['finished_ns']+500_000_000 or
                    row['finished_ns']-stamp_ns > 2_000_000_000 or previous is not None and stamp_ns <= previous):
                raise RuntimeError('HOME actuator sample stale or repeated')
            previous = stamp_ns
            result = checks.validate_actuators(sample, classify)
            if require_home and result['MEASURED_HOME'] != '1':
                raise RuntimeError('HOME terminal succeeded but complete 20D HOME is not measured')
            samples.append(sample); classifications.append(result)
        return dict(safety=safety, controllers=controller, idle_status=status,
                    actuator=samples, classifications=classifications)

    def check(self, info, payload, label, *, require_home=False):
        found = self.inventory(info['context'], label+'-inventory')
        self.files(info, payload, found, label+'-files')
        health = self.health(found, label+'-health', require_home=require_home)
        self.inventory(info['context'], label+'-final-inventory')
        cli.atomic_json(self.evidence/(label+'-verified.json'), health)
        return health


def validate_result(returncode, stdout):
    """Require one identified accepted HOME and one explicit successful result."""
    if type(returncode) is not int or returncode != 0 or type(stdout) is not str or len(stdout.encode()) > MAX_PROOF_BYTES:
        raise ValueError('force_home.sh failed or returned oversized output')
    accepted = re.findall(r'^Goal accepted with ID: ([0-9a-fA-F-]+)\s*$', stdout, re.MULTILINE)
    results = re.findall(r'^Result: (.+)$', stdout, re.MULTILINE)
    sends = re.findall(r'^Sending goal: (.+)$', stdout, re.MULTILINE)
    if len(accepted) != 1 or len(results) != 1 or sends != ['task_name=cruzr/home, yaml_args={}']:
        raise ValueError('HOME lacks one unambiguous send, accepted UUID and result')
    try:
        uid = uuid.UUID(accepted[0])
        if uid.int == 0 or accepted[0].lower() not in (str(uid), uid.hex):
            raise ValueError('Malformed accepted UUID')
        match = re.fullmatch(r'result=(.+), status=([0-9]+)', results[0])
        if match is None:
            raise ValueError('Malformed native result line')
        result = ast.literal_eval(match[1]); status = int(match[2])
        state = result['state']
        if type(state) is not dict or status != 4 or type(state['state']) is not int or state['state'] != 1101001 or state['desc'] != 'SUCCEED':
            raise ValueError('Unsuccessful native HOME status/application')
    except (ValueError, TypeError, SyntaxError, KeyError, AttributeError) as exc:
        raise ValueError('HOME native terminal is not confirmed successful') from exc
    if stdout.index('Goal accepted with ID:') >= stdout.index('Result:'):
        raise ValueError('HOME native output order invalid')
    return dict(goal_id=str(uid), status=status, result=result)


def run(after: Path, evidence: Path, wifi=False, execution_policy=None):
    """Authorize exactly one HOME after complete opening and current checks."""
    if type(wifi) is not bool:
        raise ValueError('wifi must be an explicit boolean')
    if execution_policy is not None:
        # This utility runs on the PC. Keep recipe imports out of embedded
        # remote Runtime modules, and admit no arbitrary authorize-like object.
        from .scenario1_table74_recipe import assert_policy
        assert_policy(execution_policy)
    elif not sys.stdin.isatty():
        raise RuntimeError('HOME74 requires a physical operator and TTY confirmation')
    after, evidence = Path(after), Path(evidence)
    profile = json.loads(PROFILE_PATH.read_text())
    proof, info, hashes = load_open(after, profile)
    payload = cli.make_payload('check', profile, info['source'])
    evidence.mkdir(parents=True, exist_ok=False, mode=0o700)
    cli.atomic_json(evidence/'predecessor.json', proof)
    cli.atomic_json(evidence/'context.json', info['context'])
    home_script = cli.ROOT/'scripts/force_home.sh'
    script_hash = hashlib.sha256(home_script.read_bytes()).hexdigest()
    command = [str(home_script)] + (['--wifi'] if wifi else [])
    cli.atomic_json(evidence/'command.json', dict(command=command, sha256=script_hash, automatic_retry=False))
    reader = Reader(evidence, wifi)
    record = dict(artifact='table74_home_after_opening', version=1, phase='checking',
        source_sha256=info['predecessor_sha256'], source_goal_id=info['goal_id'],
        intent_ns=None, finished_ns=None, result=None, measured_home=False,
        automatic_retry=False, error=None)
    if execution_policy is not None:
        record.update(execution_authorization_kind='recorded_recipe_assumption',
            authorization_current_physical_measurement=False,
            operator_confirmation_obtained=False, execution_policy=execution_policy.as_dict())
    journal = evidence/'home.json'
    with ExitStack() as stack:
        for path in ('/tmp/cruzr_blue_workbin_cycle.lock', '/tmp/cruzr-improved-scenario1.lock'):
            lock = stack.enter_context(open(path, 'a'))
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            if execution_policy is None:
                reader.check(info, payload, 'preflight')
                cli.confirm('Confirme ambas abrazaderas VACÍAS y pines libres, caja completamente apoyada y estable, '
                    'recorrido completo de HOME despejado sin caja/mesa/personas/cables, efector correcto, robot estable '
                    'y ruedas inmovilizadas, cargador desconectado, ambos paros liberados, otros mandos detenidos '
                    'y una persona junto al paro. HOME74 envía una sola tarea nativa y no reintenta.', 'HOME74')
            else:
                execution_policy.authorize('HOME74', evidence)
            def unchanged():
                fresh, _, fresh_hashes = load_open(after, profile)
                if fresh != proof or fresh_hashes != hashes or hashlib.sha256(home_script.read_bytes()).hexdigest() != script_hash:
                    raise RuntimeError('HOME source or force_home.sh changed after preflight')
            unchanged()
            reader.check(info, payload, 'immediate')
            unchanged()
            record.update(phase='pending', intent_ns=time.time_ns())
            cli.atomic_json(journal, record)
            subprocess.run(['bash', str(cli.ROOT/'scripts/lib/cruzr_contact_motion_lock.sh'),
                'table74-home-after-open'], check=True, start_new_session=True, timeout=15)
            unchanged()
            cli.claim_resume(after/'trial.json', journal)
            process = subprocess.run(command, capture_output=True, text=True, timeout=HOME_TIMEOUT)
            cli.atomic_json(evidence/'native-result.json', dict(returncode=process.returncode,
                stdout=process.stdout, stderr=process.stderr))
            record['result'] = validate_result(process.returncode, process.stdout)
            reader.check(info, payload, 'postflight', require_home=True)
            record.update(phase='succeeded', finished_ns=time.time_ns(), measured_home=True)
            cli.atomic_json(journal, record)
            print('HOME74_MEASURED=1; dos muestras20D nuevas, sin reintento ni navegación.')
            return record
        except BaseException as exc:
            record.update(phase='failed', finished_ns=time.time_ns(), error=str(exc) or type(exc).__name__)
            cli.atomic_json(journal, record)
            raise


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--after', type=Path, required=True)
    parser.add_argument('--evidence-dir', type=Path, required=True)
    parser.add_argument('--wifi', action='store_true')
    parser.add_argument('--run', action='store_true', required=True,
                        help='Explicitly request the single supervised HOME; no action without this flag')
    args = parser.parse_args(argv)
    run(args.after, args.evidence_dir, args.wifi)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
