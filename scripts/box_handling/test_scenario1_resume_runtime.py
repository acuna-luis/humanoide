"""Resume CLI/runtime boundaries with local fixtures and fake transports only."""
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import scenario1_cli as cli
from scripts.box_handling import scenario1_contract as contract
from scripts.box_handling import scenario1_resume as resume
from scripts.box_handling import scenario1_runtime as runtime
from scripts.box_handling.test_scenario1_checks import nav_pose


PROFILE = json.loads(Path(__file__).with_name('scenario1_current_geometry.json').read_text())


def source_before(stage, policy='assume', failed=False):
    cp = contract.new_checkpoint(PROFILE, policy=policy)
    for previous in contract.STAGES[:contract.STAGES.index(stage)]:
        arguments = {}
        if previous in ('verify_held', 'verify_released'):
            arguments = dict(confirmed_box='held' if previous == 'verify_held' else 'released',
                             verification_source={'assume': 'assumed', 'ask': 'operator', 'sensors': 'sensors'}[policy],
                             sensor_evidence={'fixture': 'old report'} if policy == 'sensors' else None)
        cp = contract.complete_stage(contract.begin_stage(cp, previous), previous, **arguments)
    if failed:
        cp = contract.fail_stage(contract.begin_stage(cp, stage), stage, 'synthetic interruption')
    return cp


def payload_for(stage='retreat', policy='assume', failed=False):
    source = source_before(stage, policy=policy, failed=failed)
    options = dict(stage=stage, box_state=contract.ENTRY_BOX_STATES[stage],
                   recovery_confirmed=failed or source['box_state'] == 'unknown',
                   stop_after='verify_home', policy=policy)
    plan = resume.plan_resume(source, PROFILE, **options)
    return dict(mode='run', profile=PROFILE, policy=policy, checkpoint=plan['checkpoint'],
                resume_source_checkpoint=source, resume_options=options, resume_plan=plan,
                resume_worker='# fake read-only worker')


class ResumeCliTests(unittest.TestCase):
    def write_source(self, root, *, failed=True):
        folder = root/'source'
        folder.mkdir()
        checkpoint = folder/'checkpoint.json'
        checkpoint.write_text(json.dumps(source_before('retreat', failed=failed), indent=2))
        (folder/'context.json').write_text('{}')
        return checkpoint

    def test_recovery_plan_is_offline_and_source_bytes_are_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.write_source(root)
            original = source.read_bytes()
            with patch.object(cli, 'Connection', side_effect=AssertionError('No network')), \
                    patch.object(cli, 'claim_resume', side_effect=AssertionError('No claim')), \
                    patch.object(cli.subprocess, 'run', side_effect=AssertionError('No commands')), \
                    patch.object(cli.subprocess, 'Popen', side_effect=AssertionError('No processes')), \
                    patch('sys.stdout', io.StringIO()) as output:
                self.assertEqual(cli.main(['--resume', str(source), '--from-stage', 'retreat',
                    '--box-state', 'held', '--recovery-confirmed', '--plan'], policy='assume'), 0)
            report = json.loads(output.getvalue()[output.getvalue().index('{'):])
            self.assertEqual(report['stages'], list(contract.STAGES[4:]))
            self.assertEqual(report['resume']['checkpoint']['completed'], [])
            self.assertEqual(report['resume']['checkpoint']['entry_stage'], 'retreat')
            self.assertEqual(source.read_bytes(), original)
            self.assertFalse(source.with_name(source.name+'.consumed.json').exists())
            self.assertEqual(sorted(path.name for path in root.iterdir()), ['source'])

    def test_resume_check_never_claims_arms_or_sends_stage_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.write_source(root)
            original = source.read_bytes()
            evidence = root/'check-evidence'
            payloads, instances = [], []

            class Connection:
                def __init__(self, payload, wifi, location):
                    payloads.append(copy.deepcopy(payload))
                    instances.append(self)
                    self.process = Mock()
                    self.process.wait.return_value = 0
                    self.close = Mock()
                    self.send = Mock(side_effect=AssertionError('No supervisor commands'))

                def wait(self, event):
                    if event != 'ready':
                        raise AssertionError('Read-only check must only wait for readiness')
                    return dict(context={}, map_name='utars_nav_map', nav_state='FSM_WAITNAVIGATE')

            def make_payload(mode, profile, checkpoint):
                return dict(mode=mode, profile=profile, checkpoint=checkpoint, modules=[],
                    action_client='', perception_guard='', sensor_worker='', health_worker='', resume_worker='')

            with patch.object(cli, 'Connection', Connection), \
                    patch.object(cli, 'make_payload', side_effect=make_payload), \
                    patch.object(cli, 'claim_resume', side_effect=AssertionError('No claim')), \
                    patch.object(cli.subprocess, 'run', side_effect=AssertionError('No motion lock/command')), \
                    patch.object(cli.subprocess, 'Popen', side_effect=AssertionError('No processes')), \
                    patch.object(cli, 'open', side_effect=lambda name, mode: open(root/Path(name).name, mode), create=True), \
                    patch('builtins.input', side_effect=AssertionError('No prompts')), \
                    patch('sys.stdout', io.StringIO()) as output:
                self.assertEqual(cli.main(['--resume', str(source), '--from-stage', 'retreat',
                    '--box-state', 'held', '--recovery-confirmed', '--check',
                    '--evidence-dir', str(evidence)], policy='assume'), 0)
            self.assertEqual(payloads[0]['mode'], 'check')
            self.assertEqual(payloads[0]['resume_source_checkpoint'], json.loads(original))
            self.assertEqual(payloads[0]['resume_plan']['stage'], 'retreat')
            instances[0].send.assert_not_called()
            instances[0].close.assert_called_once()
            self.assertEqual(source.read_bytes(), original)
            self.assertFalse(source.with_name(source.name+'.consumed.json').exists())
            snapshot = json.loads((evidence/'resume-source-checkpoint.json').read_text())
            self.assertEqual(snapshot, {'artifact': 'resume_source_snapshot', 'checkpoint': json.loads(original)})
            # Archiving the source must not create another executable copy.
            with self.assertRaises(ValueError):
                contract.validate_checkpoint(snapshot, PROFILE)
            with self.assertRaises(ValueError):
                resume.plan_resume(snapshot, PROFILE, stage='retreat', box_state='held', recovery_confirmed=True)
            self.assertFalse((evidence/'checkpoint.json').exists())
            self.assertIn('RESUME_CHECK_OK', output.getvalue())

    def test_mode_and_recovery_flags_are_validated_before_connection(self):
        for mode in ('--plan', '--check'):
            args = cli.parser('assume').parse_args(['--resume', 'unused.json', mode])
            self.assertFalse(cli.is_moving(args))
        self.assertTrue(cli.is_moving(cli.parser('assume').parse_args(['--resume', 'unused.json'])))
        with patch.object(cli, 'Connection', side_effect=AssertionError('No network')):
            for flags in (['--from-stage', 'retreat'], ['--box-state', 'held'], ['--recovery-confirmed']):
                with self.subTest(flags=flags), self.assertRaisesRegex(ValueError, 'requieren --resume'):
                    cli.main(['--plan', *flags], policy='assume')
            with patch('sys.stderr', io.StringIO()), self.assertRaises(SystemExit):
                cli.parser('assume').parse_args(['--resume', 'unused.json', '--from-stage', 'grasp_again'])
        with tempfile.TemporaryDirectory() as directory:
            source = self.write_source(Path(directory))
            with patch.object(cli, 'Connection', side_effect=AssertionError('No network')):
                for flags in ([], ['--box-state', 'held'], ['--recovery-confirmed']):
                    with self.subTest(flags=flags), self.assertRaisesRegex(ValueError, 'Recovery requires'):
                        cli.main(['--resume', str(source), '--plan', *flags], policy='assume')

    def test_source_change_after_readiness_blocks_claim_and_arm(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.write_source(root)
            evidence = root/'run-evidence'
            sent = []

            class Connection:
                def __init__(self, payload, wifi, location):
                    self.checkpoint = copy.deepcopy(payload['checkpoint'])
                    self.process = Mock()

                def send(self, message):
                    sent.append(copy.deepcopy(message))
                    if message['command'] != 'resume':
                        raise AssertionError('Changed source must not reach arm or stages')

                def wait(self, event):
                    if event == 'ready':
                        return dict(context={}, map_name='utars_nav_map', nav_state='FSM_WAITNAVIGATE')
                    if event == 'resume_ready':
                        changed = json.loads(source.read_text())
                        changed['failure']['reason'] = 'changed during entry preflight'
                        source.write_text(json.dumps(changed))
                        return {'checkpoint': self.checkpoint}
                    raise AssertionError('Unexpected event')

                def close(self):
                    pass

            def make_payload(mode, profile, checkpoint):
                return dict(mode=mode, profile=profile, checkpoint=checkpoint, modules=[],
                    action_client='', perception_guard='', sensor_worker='', health_worker='', resume_worker='')

            with patch.object(cli, 'Connection', Connection), \
                    patch.object(cli, 'make_payload', side_effect=make_payload), \
                    patch.object(cli, 'claim_resume', side_effect=AssertionError('Changed source cannot be consumed')), \
                    patch.object(cli.subprocess, 'run'), \
                    patch.object(cli.subprocess, 'Popen', side_effect=AssertionError('No processes')), \
                    patch.object(cli, 'open', side_effect=lambda name, mode: open(root/Path(name).name, mode), create=True), \
                    patch('sys.stdout', io.StringIO()), \
                    self.assertRaisesRegex(RuntimeError, 'RESUME_SOURCE_CHANGED'):
                cli.main(['--resume', str(source), '--from-stage', 'retreat', '--box-state', 'held',
                          '--recovery-confirmed', '--evidence-dir', str(evidence)], policy='assume')
            self.assertEqual(sent, [{'command': 'resume', 'stop_after': 'verify_home'}])
            self.assertFalse(source.with_name(source.name+'.consumed.json').exists())
            self.assertFalse((evidence/'checkpoint.json').exists())


class ResumeEntryRuntimeTests(unittest.TestCase):
    def machine(self, directory, *, stage='retreat', policy='assume', failed=False):
        events = []
        machine = runtime.Runtime(payload_for(stage, policy, failed),
            lambda event, **values: events.append(dict(event=event, **values)))
        machine.session = Path(directory)
        machine.native_container = 'offline-only'
        machine.events = events
        machine.points = {point: {'_expected_pose': {'point_x': 1., 'point_y': 2., 'point_yaw': 0.}}
                          for point in ('get1', 'put1')}
        machine.map_state = Mock(return_value=('utars_nav_map', 'FSM_WAITNAVIGATE'))
        machine.create_session = Mock()
        machine.discover = Mock()
        machine.hashes = Mock()
        machine.health = Mock()
        machine.map_points = Mock(return_value=machine.points)
        machine.action = Mock(side_effect=AssertionError('No physical action during entry checks'))
        machine.native = Mock(return_value=json.dumps(dict(event='resume_base_check', stationary=True, publishers=1)))
        machine.health_request = Mock(return_value={'poses': [nav_pose(ns=100_000_000), nav_pose(ns=200_000_000)],
                                                   'publisher_count': 2})
        machine.verify_sensors = Mock(return_value={'source': 'validated sensor fixture'})
        return machine

    def check_entry(self, machine, refresh=False):
        with patch.object(runtime.time, 'time', side_effect=[100., 100.3, 100.3, 100.3, 100.3]):
            machine.check_resume_entry(refresh_health=refresh)

    def test_clean_readonly_entry_checks_without_action_or_fabricated_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            for policy in ('ask', 'assume'):
                machine = self.machine(directory, policy=policy)
                self.check_entry(machine, refresh=True)
                self.assertTrue(machine.resume_validated)
                machine.action.assert_not_called()
                machine.verify_sensors.assert_not_called()
                machine.health.assert_called_once_with(require_home=False)
                self.assertFalse(machine.armed)
                self.assertEqual(machine.checkpoint['confirmations'], {})
                event = next(row for row in machine.events if row['event'] == 'resume_checked')
                self.assertEqual(event['physical_commands_sent'], 0)

    def test_wrong_waypoint_stale_pose_and_odometry_failure_block_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            for failure in ('wrong_waypoint', 'stale_pose', 'odom_exception', 'odom_moving', 'odom_publishers'):
                machine = self.machine(directory)
                if failure == 'wrong_waypoint':
                    machine.health_request.return_value['poses'][1] = nav_pose(x=1.020001, ns=200_000_000)
                elif failure == 'stale_pose':
                    machine.health_request.return_value['poses'][1] = nav_pose(sec=99, ns=200_000_000)
                elif failure == 'odom_exception':
                    machine.native.side_effect = RuntimeError('Stale or future odometry')
                elif failure == 'odom_moving':
                    machine.native.return_value = json.dumps(dict(event='resume_base_check', stationary=False, publishers=1))
                else:
                    machine.native.return_value = json.dumps(dict(event='resume_base_check', stationary=True, publishers=2))
                machine.resume_validated = True  # A failing refresh must revoke the prior check.
                with self.subTest(failure=failure), self.assertRaises((ValueError, RuntimeError)):
                    self.check_entry(machine)
                self.assertFalse(machine.resume_validated)
                machine.action.assert_not_called()
                machine.verify_sensors.assert_not_called()
                self.assertFalse(any(event['event'] == 'stage_complete' for event in machine.events))

    def test_sensor_policy_requires_real_fresh_verifier_success(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = self.machine(directory, policy='sensors')
            machine.verify_sensors.side_effect = ValueError('fresh sensor evidence unavailable')
            with self.assertRaisesRegex(ValueError, 'fresh sensor'):
                self.check_entry(machine)
            machine.verify_sensors.assert_called_once_with('held')
            self.assertFalse(machine.resume_validated)
            self.assertEqual(machine.checkpoint['confirmations'], {})
            machine.action.assert_not_called()
            empty = self.machine(directory, stage='grasp', policy='sensors')
            self.check_entry(empty, refresh=True)
            empty.health.assert_called_once_with(require_home=True)
            empty.verify_sensors.assert_not_called()

    def test_base_report_requires_one_integer_publisher_and_exact_stationary_boolean(self):
        with tempfile.TemporaryDirectory() as directory:
            for field, value in (('publishers', True), ('publishers', 1.0), ('publishers', '1'),
                                 ('publishers', 0), ('stationary', 1), ('stationary', 'true')):
                machine = self.machine(directory)
                report = dict(event='resume_base_check', stationary=True, publishers=1)
                report[field] = value
                machine.native.return_value = json.dumps(report)
                with self.subTest(field=field, value=value), self.assertRaisesRegex(RuntimeError, 'RESUME_BASE_NOT_STATIONARY'):
                    machine.check_resume_entry()
                machine.action.assert_not_called()
                self.assertFalse(machine.resume_validated)

    def test_map_not_ready_blocks_base_query_and_motion(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = self.machine(directory)
            machine.map_state.return_value = ('utars_nav_map', 'FSM_WAITRELOCATE')
            with self.assertRaisesRegex(RuntimeError, 'RESUME_MAP_NOT_READY'):
                machine.check_resume_entry()
            machine.native.assert_not_called()
            machine.action.assert_not_called()
            self.assertFalse(machine.resume_validated)

    def test_remote_recomputes_plan_and_rejects_tampering_before_any_action(self):
        for change in ('requirements', 'checkpoint', 'source', 'options'):
            payload = payload_for()
            if change == 'requirements':
                payload['resume_plan']['requirements']['waypoint'] = None
            elif change == 'checkpoint':
                payload['checkpoint'] = copy.deepcopy(payload['checkpoint'])
                payload['checkpoint']['entry_stage'] = 'deposit'
            elif change == 'source':
                payload['resume_source_checkpoint']['box_state'] = 'empty'
            else:
                payload['resume_options']['stage'] = 'deposit'
                payload['resume_options']['recovery_confirmed'] = True
            with self.subTest(change=change), self.assertRaises(ValueError):
                runtime.Runtime(payload)
        payload = payload_for(failed=True)
        payload['resume_options']['recovery_confirmed'] = False
        with self.assertRaisesRegex(ValueError, 'Recovery requires'):
            runtime.Runtime(payload)

    def test_stale_entry_after_earlier_readiness_blocks_grasp_and_records_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = self.machine(directory, stage='grasp')
            self.check_entry(machine)
            self.assertTrue(machine.resume_validated)
            machine.health_request.return_value['poses'][1] = nav_pose(sec=99, ns=200_000_000)
            machine.armed = True
            with patch.object(runtime.time, 'time', side_effect=[100., 100.3, 100.3]), \
                    self.assertRaisesRegex(ValueError, 'stale'):
                machine.stage({'stage': 'grasp'})
            machine.health.assert_called_once_with(require_home=True)
            machine.action.assert_not_called()
            self.assertFalse(machine.resume_validated)
            stored = json.loads((machine.session/'checkpoint.json').read_text())
            self.assertEqual(stored, machine.checkpoint)
            self.assertEqual(stored['failure']['stage'], 'grasp')
            self.assertEqual(stored['box_state'], 'unknown')
            self.assertEqual(stored['completed'], [])
            self.assertTrue(any(event['event'] == 'checkpoint' and
                                event['checkpoint']['in_flight'] == 'grasp' for event in machine.events))
            self.assertFalse(any(event['event'] == 'stage_complete' for event in machine.events))

    def test_first_assumed_verification_still_runs_health_and_entry_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            for stage in ('verify_held', 'verify_released'):
                machine = self.machine(directory, stage=stage)
                machine.armed = True
                with patch.object(runtime.time, 'time', side_effect=[100., 100.3, 100.3, 100.3, 100.3]):
                    machine.stage({'stage': stage})
                machine.discover.assert_called_once()
                machine.hashes.assert_called_once()
                machine.health.assert_called_once_with(require_home=False)
                machine.native.assert_called_once()
                machine.action.assert_not_called()
                self.assertTrue(machine.resume_validated)
                self.assertEqual(machine.checkpoint['confirmations'][stage]['source'], 'assumed')
                completed = next(event for event in machine.events if event['event'] == 'stage_complete')
                self.assertFalse(completed['logical_assumption'])


class ResumeGraspJournalTests(unittest.TestCase):
    def machine(self, directory):
        events, calls = [], []
        machine = runtime.Runtime(payload_for('grasp'),
            lambda event, **values: events.append(dict(event=event, **values)))
        machine.session = Path(directory)
        machine.discover = Mock()
        machine.hashes = Mock()
        machine.health = Mock()
        machine.events, machine.calls = events, calls

        def check_entry():
            self.assertTrue(machine.armed)
            machine.health.assert_called_once_with(require_home=True)
            persisted = json.loads((machine.session/'checkpoint.json').read_text())
            self.assertEqual(persisted, machine.checkpoint)
            self.assertEqual(persisted['in_flight'], 'grasp')
            machine.resume_validated = True

        machine.check_resume_entry = Mock(side_effect=check_entry)

        def action(kind, goal, timeout):
            self.assertTrue(machine.armed)
            machine.check_resume_entry.assert_called_once_with()
            persisted = json.loads((machine.session/'checkpoint.json').read_text())
            self.assertEqual(persisted, machine.checkpoint)
            self.assertEqual(persisted['in_flight'], 'grasp')
            self.assertEqual(persisted['completed'], [])
            self.assertEqual(persisted['box_state'], 'unknown')
            calls.append(goal['task_name'])
            self.assertTrue(any(event['event'] == 'checkpoint' and
                                event['checkpoint']['in_flight'] == 'grasp' for event in events))
            return dict(event='result', status=4, result={'state': {'desc': 'SUCCEED', 'state': 1101001}})

        machine.action = Mock(side_effect=action)
        return machine

    def test_grasp_entry_prepares_vision_only_after_arm_and_durable_intent(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = self.machine(directory)
            with self.assertRaisesRegex(RuntimeError, 'NOT_ARMED'):
                machine.stage({'stage': 'grasp'})
            machine.action.assert_not_called()
            machine.check_resume_entry.assert_not_called()
            self.assertFalse((machine.session/'checkpoint.json').exists())
            machine.armed = True
            machine.stage({'stage': 'grasp'})
            self.assertEqual(machine.calls, ['vision/enable_transport_vision_switch', 'local_front_box/separate_right_cruzr'])
            self.assertEqual(machine.checkpoint['completed'], ['grasp'])
            self.assertEqual(machine.checkpoint['confirmations'], {})
            self.assertEqual([event['stage'] for event in machine.events if event['event'] == 'stage_complete'], ['grasp'])
            self.assertTrue(any(event['event'] == 'resume_prerequisite' for event in machine.events))
            machine.check_resume_entry.assert_called_once_with()
            machine.health.assert_called_once_with(require_home=True)

    def test_vision_preparation_failure_never_sends_grasp_or_completes_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = self.machine(directory)
            machine.armed = True
            machine.action.side_effect = None
            machine.action.return_value = dict(event='result', status=6, result={'state': {'desc': 'FAILED', 'state': 0}})
            with self.assertRaises(ValueError):
                machine.stage({'stage': 'grasp'})
            machine.action.assert_called_once()
            self.assertEqual(machine.action.call_args.args[1]['task_name'], 'vision/enable_transport_vision_switch')
            self.assertEqual(machine.checkpoint['completed'], [])
            self.assertEqual(machine.checkpoint['failure']['stage'], 'grasp')
            self.assertFalse(any(event['event'] == 'stage_complete' for event in machine.events))


if __name__ == '__main__':
    unittest.main()
