"""HOME utility tests use synthetic proof and mocked transport/processes only."""
import copy
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import scenario1_table74_home as home
from scripts.box_handling import scenario1_table74_current_release_run as released
from scripts.box_handling.test_scenario1_table74_current_release_run import (
    PROFILE, relief_proof, bundle, set_goal)
from scripts.box_handling.test_scenario1_table74_current_lower_run import proof_record
from scripts.lib.cruzr_home_posture_gate import BODY_ACTUATOR_ALIASES


UID = 'a5ca3e68-eef8-4cf6-b66a-c14aac8d2fbb'
SUCCESS = ("Conectado al robot: motion\n"
    "Sending goal: task_name=cruzr/home, yaml_args={}\n"
    "Goal accepted with ID: "+UID+"\n"
    "Result: result={'state': {'desc': 'SUCCEED', 'state': 1101001}}, status=4\n")


def opened_proof():
    parent = relief_proof()
    package = bundle(parent, 'lateral_open')
    return set_goal(proof_record(package, released.digest(parent), parent=parent), UID)


def source_files(root):
    after = root/'after'; after.mkdir(); proof = opened_proof()
    for name, value in proof.items():
        (after/name).write_text(''.join(json.dumps(e)+'\n' for e in value) if name == 'events.jsonl' else json.dumps(value))
    profile = root/'profile.json'; profile.write_text(json.dumps(PROFILE))
    return after, profile


def actuator(stamp=101, position=0.):
    return dict(header={'stamp': {'sec': stamp, 'nanosec': 0}}, act_item=[
        dict(id=ids[0], name=name, position=position, velocity=0., cmd_pos=position, status=7, error_code=0)
        for name, ids in BODY_ACTUATOR_ALIASES])


class HomeCliTests(unittest.TestCase):
    def test_standalone_home_requires_explicit_run_before_calling_physical_api(self):
        args = ['--after', '/unused/source', '--evidence-dir', '/unused/evidence']
        with patch.object(home, 'run', return_value={}) as action:
            with patch('sys.stderr', io.StringIO()), self.assertRaises(SystemExit):
                home.main(args)
            action.assert_not_called()
            self.assertEqual(home.main([*args, '--run']), 0)
            action.assert_called_once_with(Path('/unused/source'), Path('/unused/evidence'), False)


class OpeningProofTests(unittest.TestCase):
    def test_accepts_only_authentic_completed_opening(self):
        proof = opened_proof(); info = home.validate_open(proof, PROFILE)
        self.assertEqual(info['completed_stage'], 'lateral_open')
        self.assertEqual(info['goal_id'], UID)
        self.assertEqual(info['source']['profile_id'], 'scenario1_table74_preparation_v1')
        self.assertEqual(len(info['chain_bundles']), 5)
        with self.assertRaises(ValueError): home.validate_open(relief_proof(), PROFILE)
        for mutation in ('status', 'goal', 'context', 'tail', 'navigation', 'parent'):
            bad = copy.deepcopy(proof)
            if mutation == 'status': bad['trial.json']['result']['status'] = 6
            elif mutation == 'goal': bad['trial.json']['result']['goal_id'] = 'wrong'
            elif mutation == 'context': bad['context.json']['boot_id'] = 'changed'
            elif mutation == 'tail': bad['events.jsonl'].append(dict(event='armed', time_ns=100))
            elif mutation == 'navigation': bad['events.jsonl'].insert(-1,
                dict(event='action', time_ns=85, kind='navigation', detail={'event':'dispatched'}))
            else: bad['predecessor.json']['bundle.json']['review']['reference']['evidence'] = 'changed'
            with self.subTest(mutation=mutation), self.assertRaises((ValueError, KeyError)):
                home.validate_open(bad, PROFILE)

    def test_consumed_and_oversize_proofs_fail_before_connection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); after, _ = source_files(root)
            proof, info, hashes = home.load_open(after, PROFILE)
            self.assertEqual(info['goal_id'], UID); self.assertEqual(len(hashes), 7)
            (after/'trial.json.consumed.json').write_text('{}')
            with self.assertRaisesRegex(RuntimeError, 'consumed'): home.load_open(after, PROFILE)
            (after/'trial.json.consumed.json').unlink()
            with patch.object(home, 'MAX_PROOF_BYTES', 10), self.assertRaisesRegex(ValueError, '16 MiB'):
                home.load_open(after, PROFILE)


class NativeResultTests(unittest.TestCase):
    def test_requires_single_accepted_uuid_and_exact_terminal_not_final_echo(self):
        result = home.validate_result(0, SUCCESS)
        self.assertEqual(result['goal_id'], UID)
        self.assertEqual(result['status'], 4)
        for output in (SUCCESS.replace('status=4', 'status=6'),
                       SUCCESS.replace('1101001', '7104050'), SUCCESS.replace("'SUCCEED'", "'MoveToGoalFailed'"),
                       SUCCESS.replace('Goal accepted with ID: '+UID, 'Goal rejected'),
                       SUCCESS+SUCCESS, SUCCESS.replace(UID, '00000000-0000-0000-0000-000000000000'),
                       SUCCESS.replace('task_name=cruzr/home', 'task_name=another/task'),
                       SUCCESS.replace("'state': 1101001", "'state': True")):
            with self.subTest(output=output), self.assertRaises(ValueError): home.validate_result(0, output)
        for code in (1, True):
            with self.assertRaises(ValueError): home.validate_result(code, SUCCESS)


class ReaderTests(unittest.TestCase):
    def test_container_boot_identity_and_hardcoded_force_home_target_are_checked(self):
        info = home.validate_open(opened_proof(), PROFILE)
        rows = []
        for role, name in (('native', home.NATIVE_NAME), ('ros2', 'walker-ros.ros2-1')):
            rows.append(dict(Name='/'+name, Id=('a' if role=='native' else 'b')*64,
                Config=dict(Image=home.checks.EXPECTED_IMAGE_FRAGMENT if role=='native' else 'ros:humble',
                    Env=['HW_TYPE=cruzr_s2_v1'], Labels={'com.docker.compose.service':
                        'motion.manipulation_robot_app' if role=='native' else 'ros.ros2'}),
                State={'Running':True,'Paused':False,'Restarting':False,'StartedAt':'2026-10-22T10:27:22Z'}))
        expected = copy.deepcopy(info['context'])
        expected['containers'] = {row['Name'].lstrip('/'):[row['Id'],row['State']['StartedAt']] for row in rows}
        document = dict(boot_id=expected['boot_id'], inventory=rows)
        with tempfile.TemporaryDirectory() as directory:
            reader=home.Reader(Path(directory),False)
            def query(*args):return {'stdout':json.dumps(document)}
            with patch.object(reader,'query',side_effect=query):
                self.assertEqual(reader.inventory(expected,'sample')['native'],home.NATIVE_NAME)
                document['boot_id']='different'
                with self.assertRaisesRegex(RuntimeError,'boot'):reader.inventory(expected,'changed')
                document['boot_id']=expected['boot_id'];rows[0]['State']['StartedAt']='changed'
                with self.assertRaisesRegex(RuntimeError,'containers'):reader.inventory(expected,'restarted')
                rows[0]['Name']='/different-motion-name'
                with self.assertRaisesRegex(RuntimeError,'container differs'):reader.inventory(expected,'renamed')

    def test_dependency_identity_home_and_every_completed_phase_file_are_reread(self):
        info=home.validate_open(opened_proof(),PROFILE)
        payload=home.cli.make_payload('check',PROFILE,info['source'])
        plan=home.dependencies.plan_files(payload)
        vision='<root><Action ID="MetaLook" start_vision_mode="transport_vision" /></root>'
        native=dict(plan['native'],**{plan['home_path']:plan['home_direct'],
                    plan['vision_path']:home.hashlib.sha256(vision.encode()).hexdigest()})
        reports={'native':{'hashes':native,'vision_xml':vision},'ros2':{'hashes':plan['ros2']}}
        info['context']['dependencies']=home.dependencies.validate_reports(payload,reports['native'],reports['ros2'])
        pins={path:value for b in info['chain_bundles'] for path,value in b['manifest']['robot_files'].items()}
        reports['chain']={'hashes':pins}
        calls=[]
        def query(command,label):calls.append(command);return {'stdout':json.dumps(reports[label.removeprefix('files-')])}
        with tempfile.TemporaryDirectory() as directory:
            reader=home.Reader(Path(directory),False)
            with patch.object(reader,'query',side_effect=query):
                reader.files(info,payload,{'native':'app','ros2':'bridge'},'files')
                self.assertEqual(len(calls),3)
                reports['chain']['hashes']=dict(pins);reports['chain']['hashes'][next(iter(pins))]='0'*64
                with self.assertRaisesRegex(RuntimeError,'files changed'):
                    reader.files(info,payload,{'native':'app','ros2':'bridge'},'files')
                reports['chain']['hashes']=pins
                info['context']['dependencies']['home_sha256']='0'*64
                with self.assertRaisesRegex(RuntimeError,'dependency identity'):
                    reader.files(info,payload,{'native':'app','ros2':'bridge'},'files')

    def rows(self, *, home_position=0.):
        outputs = {
            'estop': 'data: 0\n', 'servo': 'data: 0\n', 'charger': 'data: 0\n',
            'battery': 'pack1:\n  batsoc: 40\npack2:\n  batsoc: 41\n', 'status': 'status_list: []\n',
            'controller': "Response(controller=[{'name': 'manipulation_controller', 'state': 'running'}, "
                "{'name': 'sdk_controller', 'state': 'initialized'}, {'name': 'vla_sdk_controller', 'state': 'initialized'}])\n"}
        def query(command, label):
            suffix = label.removeprefix('sample-')
            if suffix.startswith('actuator-'):
                index = int(suffix[-1]); stamp = 101+index
                return dict(start_ns=stamp*10**9-100, finished_ns=stamp*10**9+100,
                            returncode=0, stdout=json.dumps(actuator(stamp, home_position)), stderr='')
            return dict(start_ns=100*10**9, finished_ns=100*10**9+100,
                        returncode=0, stdout=outputs[suffix], stderr='')
        return outputs, query

    def test_fixed_fresh_health_uses_default_status_qos_and_two_measured_20d_samples(self):
        outputs, query = self.rows()
        with tempfile.TemporaryDirectory() as directory:
            reader = home.Reader(Path(directory), False)
            calls = []
            def recorded(command, label): calls.append((command,label)); return query(command,label)
            with patch.object(reader, 'query', side_effect=recorded):
                checked = reader.health({'native':'app','ros2':'bridge'}, 'sample', require_home=True)
            self.assertEqual([c['MEASURED_HOME'] for c in checked['classifications']], ['1','1'])
            status = next(command[-1] for command, label in calls if label.endswith('-status'))
            self.assertNotIn('qos-durability', status); self.assertNotIn('transient', status)
            self.assertEqual(sum(label.startswith('sample-actuator-') for _,label in calls), 2)

    def test_fault_motion_stale_repeated_and_nonhome_cannot_verify_home(self):
        for mutation in ('battery', 'charger', 'busy', 'controller', 'fault', 'moving', 'latent', 'stale', 'repeated', 'not_home'):
            outputs, base = self.rows(home_position=.1 if mutation == 'not_home' else 0.)
            if mutation == 'battery': outputs['battery'] = 'one:\n  batsoc: 19\ntwo:\n  batsoc: 80\n'
            elif mutation == 'charger': outputs['charger'] = 'data: 1\n'
            elif mutation == 'busy': outputs['status'] = '{"status_list":[{"status":2}]}'
            elif mutation == 'controller': outputs['controller'] = outputs['controller'].replace("'initialized'", "'running'", 1)
            def changed(command, label):
                row = base(command,label)
                if 'actuator-' in label:
                    sample = json.loads(row['stdout'])
                    if mutation == 'fault': sample['act_item'][0]['error_code'] = 1
                    elif mutation == 'moving': sample['act_item'][0]['velocity'] = .1
                    elif mutation == 'latent': sample['act_item'][0]['cmd_pos'] = .1
                    elif mutation == 'stale': sample['header']['stamp']['sec'] -= 4
                    elif mutation == 'repeated':
                        sample['header']['stamp']['sec'] = 101
                        row['start_ns'] = 101*10**9-100; row['finished_ns'] = 102*10**9+100
                    row['stdout'] = json.dumps(sample)
                return row
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                reader = home.Reader(Path(directory), False)
                with patch.object(reader, 'query', side_effect=changed), self.assertRaises((ValueError,RuntimeError)):
                    reader.health({'native':'app','ros2':'bridge'}, 'sample', require_home=True)


class HomeRunTests(unittest.TestCase):
    def test_recorded_recipe_authorizes_without_tty_or_question_and_keeps_immediate_and_measured_postflight(self):
        from scripts.box_handling.scenario1_table74_recipe import RecipePolicy
        policy=RecipePolicy.from_default()
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);after,profile=source_files(root);evidence=root/'automatic';reader=Mock()
            def process(command,**kwargs):
                if command[0]=='bash':return subprocess.CompletedProcess(command,0,'','')
                self.assertTrue((after/'trial.json.consumed.json').exists())
                self.assertEqual(json.loads((evidence/'home.json').read_text())['phase'],'pending')
                return subprocess.CompletedProcess(command,0,SUCCESS,'')
            with patch.object(home,'PROFILE_PATH',profile),patch.object(home.sys.stdin,'isatty',return_value=False), \
                    patch.object(home,'Reader',return_value=reader), \
                    patch.object(home.cli,'confirm',side_effect=AssertionError('No human question for exact recipe')), \
                    patch.object(home.subprocess,'run',side_effect=process)as commands, \
                    patch.object(home,'open',side_effect=lambda p,m:open(root/Path(p).name,m),create=True):
                result=home.run(after,evidence,execution_policy=policy)
            self.assertEqual([call.args[2]for call in reader.check.call_args_list],['immediate','postflight'])
            self.assertEqual(reader.check.call_args.kwargs,{'require_home':True})
            self.assertEqual(sum(call.args[0][0]!='bash'for call in commands.call_args_list),1)
            self.assertEqual(result['execution_authorization_kind'],'recorded_recipe_assumption')
            self.assertIs(result['authorization_current_physical_measurement'],False)
            self.assertIs(result['operator_confirmation_obtained'],False)
            self.assertIs(result['measured_home'],True)
            receipt=json.loads((evidence/'recipe-HOME74.json').read_text())
            self.assertEqual(receipt['authorization_kind'],'recorded_recipe_assumption')
            self.assertIs(receipt['current_physical_measurement'],False)

    def test_recorded_recipe_never_skips_fresh_gates_or_postflight_home_confirmation(self):
        from scripts.box_handling.scenario1_table74_recipe import RecipePolicy
        for failure in ('immediate','postflight'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory()as directory:
                root=Path(directory);after,profile=source_files(root);reader=Mock()
                reader.check.side_effect=RuntimeError('fresh health failed')if failure=='immediate'else[{},RuntimeError('HOME_NOT_MEASURED')]
                def process(command,**kwargs):return subprocess.CompletedProcess(command,0,''if command[0]=='bash'else SUCCESS,'')
                with patch.object(home,'PROFILE_PATH',profile),patch.object(home.sys.stdin,'isatty',return_value=False), \
                        patch.object(home,'Reader',return_value=reader),patch.object(home.cli,'confirm',side_effect=AssertionError('No question')), \
                        patch.object(home.subprocess,'run',side_effect=process)as commands, \
                        patch.object(home,'open',side_effect=lambda p,m:open(root/Path(p).name,m),create=True):
                    with self.assertRaises(RuntimeError):home.run(after,root/'automatic',execution_policy=RecipePolicy.from_default())
                self.assertEqual(commands.call_count,0 if failure=='immediate'else 2)
                self.assertEqual((after/'trial.json.consumed.json').exists(),failure=='postflight')
                record=json.loads((root/'automatic/home.json').read_text())
                self.assertEqual(record['phase'],'failed');self.assertIs(record['measured_home'],False)

    def test_fake_or_tampered_recipe_never_reaches_evidence_or_transport(self):
        from scripts.box_handling.scenario1_table74_recipe import RecipePolicy
        with patch.object(home,'load_open',side_effect=AssertionError('No source access')), \
                patch.object(home,'Reader',side_effect=AssertionError('No transport')), \
                self.assertRaises((ValueError,TypeError)):
            home.run(Path('/absent'),Path('/absent2'),execution_policy=Mock())
        policy=RecipePolicy.from_default();changed=copy.deepcopy(policy.as_dict());changed['unexpected']='tampered'
        with patch.object(RecipePolicy,'as_dict',return_value=changed), \
                patch.object(home,'load_open',side_effect=AssertionError('No source access')), \
                self.assertRaises((ValueError,TypeError)):
            home.run(Path('/absent'),Path('/absent2'),execution_policy=policy)

    def test_durable_consumption_before_exactly_one_home_then_measured_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); after, profile = source_files(root); evidence = root/'home'
            calls = []
            def process(command, **kwargs):
                calls.append(command)
                if command[0] == 'bash': return subprocess.CompletedProcess(command, 0, '', '')
                self.assertTrue((after/'trial.json.consumed.json').exists())
                self.assertEqual(json.loads((evidence/'home.json').read_text())['phase'], 'pending')
                self.assertEqual(command, [str(home.cli.ROOT/'scripts/force_home.sh'), '--wifi'])
                return subprocess.CompletedProcess(command, 0, SUCCESS, '')
            reader = Mock(); reader.check.return_value = {}
            with patch.object(home, 'PROFILE_PATH', profile), patch.object(home.sys.stdin, 'isatty', return_value=True), \
                    patch.object(home, 'Reader', return_value=reader), patch.object(home.cli, 'confirm') as confirm, \
                    patch.object(home.subprocess, 'run', side_effect=process), \
                    patch.object(home, 'open', side_effect=lambda p,m: open(root/Path(p).name,m), create=True):
                result = home.run(after, evidence, True)
            self.assertEqual(result['phase'], 'succeeded'); self.assertIs(result['measured_home'], True)
            self.assertEqual(confirm.call_args.args[1], 'HOME74')
            self.assertEqual(len(calls), 2)  # contact-lock helper + one native HOME script
            self.assertEqual([call.args[2] for call in reader.check.call_args_list], ['preflight','immediate','postflight'])
            self.assertEqual(reader.check.call_args.kwargs, {'require_home':True})

    def test_gate_or_declined_confirmation_never_consumes_or_dispatches(self):
        for failure in ('preflight','confirm','immediate'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                root=Path(directory);after,profile=source_files(root);reader=Mock()
                reader.check.side_effect = RuntimeError('preflight') if failure=='preflight' else ([{},RuntimeError('immediate')] if failure=='immediate' else None)
                with patch.object(home,'PROFILE_PATH',profile),patch.object(home.sys.stdin,'isatty',return_value=True), \
                        patch.object(home,'Reader',return_value=reader),patch.object(home.cli,'confirm',side_effect=RuntimeError('declined') if failure=='confirm' else None), \
                        patch.object(home.subprocess,'run') as process,patch.object(home,'open',side_effect=lambda p,m:open(root/Path(p).name,m),create=True):
                    with self.assertRaises(RuntimeError):home.run(after,root/'home')
                process.assert_not_called();self.assertFalse((after/'trial.json.consumed.json').exists())

    def test_native_failure_timeout_or_missing_measured_home_stays_consumed_without_retry(self):
        for outcome in ('failure','timeout','posture'):
            with self.subTest(outcome=outcome),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);after,profile=source_files(root);evidence=root/'home';reader=Mock()
                if outcome=='posture':reader.check.side_effect=[{},{},RuntimeError('HOME_NOT_MEASURED')]
                def process(command,**kwargs):
                    if command[0]=='bash':return subprocess.CompletedProcess(command,0,'','')
                    if outcome=='timeout':raise subprocess.TimeoutExpired(command,90)
                    return subprocess.CompletedProcess(command,0,SUCCESS.replace('status=4','status=6')if outcome=='failure'else SUCCESS,'')
                with patch.object(home,'PROFILE_PATH',profile),patch.object(home.sys.stdin,'isatty',return_value=True), \
                        patch.object(home,'Reader',return_value=reader),patch.object(home.cli,'confirm'), \
                        patch.object(home.subprocess,'run',side_effect=process) as commands, \
                        patch.object(home,'open',side_effect=lambda p,m:open(root/Path(p).name,m),create=True):
                    with self.assertRaises((ValueError,RuntimeError,subprocess.TimeoutExpired)):home.run(after,evidence)
                self.assertTrue((after/'trial.json.consumed.json').exists())
                self.assertEqual(sum(call.args[0][0]!='bash'for call in commands.call_args_list),1)
                record=json.loads((evidence/'home.json').read_text())
                self.assertEqual(record['phase'],'failed');self.assertIs(record['measured_home'],False)

    def test_tty_required_before_any_transport_and_top_level_import_supported(self):
        with patch.object(home.sys.stdin,'isatty',return_value=False),patch.object(home,'execute')as transport:
            with self.assertRaisesRegex(RuntimeError,'TTY'):home.run(Path('/absent'),Path('/absent2'))
        transport.assert_not_called()
        namespace={'__name__':'home_import_probe','__package__':'','__file__':home.__file__}
        exec(compile(Path(home.__file__).read_text(),'<home-import>','exec'),namespace)
        self.assertEqual(namespace['__package__'],'scripts.box_handling')


if __name__ == '__main__':unittest.main()
