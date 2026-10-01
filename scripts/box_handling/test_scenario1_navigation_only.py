"""Navigation-only boundary tests. Fake transports; no ROS or network calls."""
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import scenario1_cli as cli
from scripts.box_handling import scenario1_contract as contract
from scripts.box_handling import scenario1_runtime as runtime
from scripts.box_handling.scenario1_resume import plan_resume


PROFILE = json.loads(Path(__file__).with_name('scenario1_current_geometry.json').read_text())


def held_checkpoint():
    checkpoint = contract.new_checkpoint(PROFILE, stop_after='verify_held', policy='assume',
                                         execution_profile='optimistic_v1')
    for stage in contract.STAGES[:4]:
        options = dict(confirmed_box='held', verification_source='assumed') if stage == 'verify_held' else {}
        checkpoint = contract.complete_stage(contract.begin_stage(checkpoint, stage), stage, **options)
    return checkpoint


class NavigationOnlyCliTests(unittest.TestCase):
    def test_offline_plan_contains_only_navigation_to_get1(self):
        with patch.object(cli, 'Connection', side_effect=AssertionError('No network')), \
                patch.object(cli.subprocess, 'run', side_effect=AssertionError('No commands')), \
                patch.object(cli.subprocess, 'Popen', side_effect=AssertionError('No processes')), \
                patch('sys.stdout', io.StringIO()) as output:
            self.assertEqual(cli.main(['--plan', '--stop-after', 'get1']), 0)
        report = json.loads(output.getvalue()[output.getvalue().index('{'):])
        self.assertEqual(report['stages'], ['navigate_get1'])
        self.assertEqual(report['automatic_retries'], 0)

    def test_put1_resume_plan_is_exact_and_does_not_consume_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'checkpoint.json'
            original = json.dumps(held_checkpoint())
            source.write_text(original)
            with patch.object(cli, 'Connection', side_effect=AssertionError('No network')), \
                    patch.object(cli.subprocess, 'run', side_effect=AssertionError('No commands')), \
                    patch.object(cli.subprocess, 'Popen', side_effect=AssertionError('No processes')), \
                    patch('sys.stdout', io.StringIO()) as output:
                self.assertEqual(cli.main(['--plan', '--resume', str(source), '--stop-after', 'put1'],
                    policy='assume', execution_profile='optimistic_v1'), 0)
            report = json.loads(output.getvalue()[output.getvalue().index('{'):])
            self.assertEqual(report['stages'], ['retreat', 'navigate_put1'])
            self.assertEqual(report['automatic_retries'], 0)
            self.assertEqual(report['resume']['checkpoint']['box_state'], 'held')
            self.assertEqual(report['resume']['checkpoint']['stop_after'], 'navigate_put1')
            self.assertEqual(source.read_text(), original)
            self.assertEqual(list(Path(directory).iterdir()), [source])

    def test_put1_resume_sends_only_retreat_and_navigation_before_clean_finish(self):
        with tempfile.TemporaryDirectory() as directory:
            root, messages = Path(directory), []
            source, evidence = root/'checkpoint.json', root/'run'
            original = json.dumps(held_checkpoint())
            source.write_text(original)
            (root/'context.json').write_text('{}')

            class OfflineConnection:
                def __init__(self, payload, wifi, location, *, console=None):
                    self.checkpoint = copy.deepcopy(payload['checkpoint'])
                    self.evidence = location
                    self.process = Mock()
                    self.process.wait.return_value = 0

                def send(self, message):
                    messages.append(copy.deepcopy(message))
                    if message['command'] == 'stage':
                        if message['stage'] not in ('retreat', 'navigate_put1'):
                            raise AssertionError('Unexpected deposit/HOME/grasp stage')
                        self.checkpoint = contract.complete_stage(
                            contract.begin_stage(self.checkpoint, message['stage']), message['stage'])
                        cli.atomic_json(self.evidence/'checkpoint.json', self.checkpoint)

                def wait(self, desired, timeout=None):
                    return dict(checkpoint=self.checkpoint, context={}, map_name='utars_nav_map',
                                nav_state='FSM_WAITNAVIGATE')

                def close(self):
                    pass

            with patch('builtins.input', side_effect=AssertionError('No prompts')), \
                    patch.object(cli, 'Connection', OfflineConnection), \
                    patch.object(cli.subprocess, 'run'), \
                    patch.object(cli.subprocess, 'Popen', side_effect=AssertionError('No processes')), \
                    patch.object(cli, 'open', side_effect=lambda name, mode: open(root/Path(name).name, mode), create=True), \
                    patch('sys.stdout', io.StringIO()) as output:
                self.assertEqual(cli.main(['--resume', str(source), '--stop-after', 'put1',
                    '--evidence-dir', str(evidence)], policy='assume', execution_profile='optimistic_v1'), 0)
            self.assertEqual(messages, [{'command': 'resume', 'stop_after': 'navigate_put1'},
                {'command': 'arm'}, {'command': 'stage', 'stage': 'retreat'},
                {'command': 'stage', 'stage': 'navigate_put1'}, {'command': 'finish'}])
            completed = json.loads((evidence/'checkpoint.json').read_text())
            self.assertEqual(completed['completed'], ['retreat', 'navigate_put1'])
            self.assertEqual(completed['box_state'], 'held')
            self.assertIsNone(completed['failure'])
            self.assertIsNone(completed['in_flight'])
            self.assertIsNone(contract.next_stage(completed))
            self.assertEqual(source.read_text(), original)
            self.assertTrue(source.with_name(source.name+'.consumed.json').is_file())
            following = plan_resume(completed, PROFILE, execution_profile='optimistic_v1')
            self.assertEqual(following['stage'], 'deposit')
            self.assertEqual(following['requirements']['waypoint'], 'put1')
            self.assertFalse(following['checkpoint']['origin']['recovery_confirmed'])
            self.assertIn('PUT1_ALCANZADO; caja sujeta', output.getvalue())
            self.assertIn('depósito no ejecutado', output.getvalue())
            self.assertNotIn('CICLO_COMPLETO_HOME_MEDIDO', output.getvalue())
            self.assertNotIn('REANUDACION_COMPLETADA_HOME_MEDIDO', output.getvalue())

    def test_noninteractive_run_sends_one_navigation_stage_then_finishes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root/'run'
            messages = []

            class OfflineConnection:
                def __init__(self, payload, wifi, location, *, console=None):
                    self.checkpoint = copy.deepcopy(payload['checkpoint'])
                    self.evidence = location
                    self.process = Mock()
                    self.process.wait.return_value = 0

                def send(self, message):
                    messages.append(copy.deepcopy(message))
                    if message['command'] == 'stage':
                        if message['stage'] != 'navigate_get1':
                            raise AssertionError('Unexpected manipulation/other navigation stage')
                        checkpoint = contract.begin_stage(self.checkpoint, message['stage'])
                        self.checkpoint = contract.complete_stage(checkpoint, message['stage'])
                        cli.atomic_json(self.evidence/'checkpoint.json', self.checkpoint)

                def wait(self, desired, timeout=None):
                    return dict(context={}, map_name='utars_nav_map', nav_state='FSM_WAITNAVIGATE')

                def close(self):
                    pass

            with patch('sys.stdin.isatty', return_value=False), \
                    patch('builtins.input', side_effect=AssertionError('No prompts')), \
                    patch.object(cli, 'Connection', OfflineConnection), \
                    patch.object(cli.subprocess, 'run'), \
                    patch.object(cli.subprocess, 'Popen', side_effect=AssertionError('No processes')), \
                    patch.object(cli, 'open', side_effect=lambda name, mode: open(root/Path(name).name, mode), create=True), \
                    patch('sys.stdout', io.StringIO()) as output:
                self.assertEqual(cli.main(['--run', '--stop-after', 'get1',
                                           '--evidence-dir', str(evidence)], policy='assume'), 0)
            self.assertEqual(messages, [{'command': 'arm'},
                                        {'command': 'stage', 'stage': 'navigate_get1'},
                                        {'command': 'finish'}])
            checkpoint = json.loads((evidence/'checkpoint.json').read_text())
            self.assertEqual(checkpoint['completed'], ['navigate_get1'])
            self.assertEqual(checkpoint['stop_after'], 'navigate_get1')
            self.assertEqual(checkpoint['box_state'], 'empty')
            self.assertEqual(checkpoint['confirmations'], {})
            self.assertIsNone(contract.next_stage(checkpoint))
            self.assertIn('GET1_ALCANZADO', output.getvalue())
            self.assertNotIn('CICLO_COMPLETO_HOME_MEDIDO', output.getvalue())
            self.assertNotIn('CAJA_SUJETA', output.getvalue())


class NavigationOnlyRuntimeTests(unittest.TestCase):
    def test_put1_resume_keeps_held_checkpoint_and_closes_without_sps_deposit_or_home(self):
        with tempfile.TemporaryDirectory() as directory:
            root, events = Path(directory), []
            source = held_checkpoint()
            options = dict(stop_after='navigate_put1', policy='assume', execution_profile='optimistic_v1')
            planned = plan_resume(source, PROFILE, **options)
            machine = runtime.Runtime(dict(mode='run', profile=PROFILE, checkpoint=planned['checkpoint'],
                policy='assume', execution_profile='optimistic_v1', resume_plan=planned,
                resume_source_checkpoint=source, resume_options=options),
                lambda event, **values: events.append(dict(event=event, **values)))
            machine.native_container = 'offline-placeholder'
            for message in ({'command': 'resume', 'stop_after': 'navigate_put1'}, {'command': 'arm'},
                            {'command': 'stage', 'stage': 'retreat'},
                            {'command': 'stage', 'stage': 'navigate_put1'}, {'command': 'finish'}):
                machine.commands.put(message)

            def create_session():
                machine.session = root/'session'
                machine.session.mkdir()

            def resume_entry(**unused):
                machine.resume_validated = True

            def retreat_only(kind, goal, timeout):
                self.assertEqual(kind, 'motion')
                self.assertEqual(goal, {'task_name': 'cruzr/mobot_back_20', 'yaml_args': '{}'})
                return dict(event='result', status=4, result={'state': {'desc': 'SUCCEED', 'state': 1101001}})

            with patch.object(runtime.threading, 'Thread'), patch.object(runtime.signal, 'signal'), \
                    patch.object(runtime, 'open', side_effect=lambda name, mode: open(root/'supervisor.lock', mode), create=True), \
                    patch.object(runtime, 'check_sps_discovery'), \
                    patch.object(runtime.subprocess, 'run', side_effect=AssertionError('No commands')), \
                    patch.object(runtime.subprocess, 'Popen', side_effect=AssertionError('No processes')), \
                    patch.multiple(machine, discover=Mock(), hashes=Mock(), health=Mock(),
                                   map_points=Mock(return_value={}),
                                   map_state=Mock(return_value=('utars_nav_map', 'FSM_WAITNAVIGATE')),
                                   read_poses=Mock(), connected=Mock(), write_lease=Mock(),
                                   start_live_monitor=Mock(), quick_health=Mock(),
                                   check_resume_entry=Mock(side_effect=resume_entry),
                                   create_session=Mock(side_effect=create_session),
                                   start_adapters=Mock(), navigate=Mock(),
                                   action=Mock(side_effect=retreat_only)):
                self.assertEqual(machine.run(), 0, events)
                machine.start_adapters.assert_not_called()
                machine.action.assert_called_once()
                machine.navigate.assert_called_once_with('put1')
            self.assertEqual(machine.checkpoint['completed'], ['retreat', 'navigate_put1'])
            self.assertEqual(machine.checkpoint['box_state'], 'held')
            self.assertIsNone(contract.next_stage(machine.checkpoint))
            self.assertTrue(machine.stop.is_set())
            self.assertTrue((machine.session/'stop').is_file())
            self.assertEqual([e['stage'] for e in events if e['event'] == 'stage_complete'],
                             ['retreat', 'navigate_put1'])
            self.assertTrue(any(e['event'] == 'session_finishing' for e in events))

    def run_supervisor(self, stop_after):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint = contract.new_checkpoint(PROFILE, stop_after=stop_after, policy='assume')
            events = []
            machine = runtime.Runtime(dict(mode='run', profile=PROFILE, checkpoint=checkpoint,
                                           policy='assume'),
                                      lambda event, **values: events.append(dict(event=event, **values)))
            machine.native_container = 'offline-placeholder'
            machine.commands.put({'command': 'arm'})
            if stop_after == 'navigate_get1':
                machine.commands.put({'command': 'stage', 'stage': 'navigate_get1'})
            machine.commands.put({'command': 'finish'})

            def create_session():
                machine.session = root/'session'
                machine.session.mkdir()

            with patch.object(runtime.threading, 'Thread'), patch.object(runtime.signal, 'signal'), \
                    patch.object(runtime, 'open', side_effect=lambda name, mode: open(root/'supervisor.lock', mode), create=True), \
                    patch.object(runtime, 'check_sps_discovery'), \
                    patch.object(runtime.subprocess, 'run', side_effect=AssertionError('No commands')), \
                    patch.object(runtime.subprocess, 'Popen', side_effect=AssertionError('No processes')), \
                    patch.multiple(machine, discover=Mock(), hashes=Mock(), health=Mock(),
                                   map_points=Mock(return_value={}),
                                   map_state=Mock(return_value=('utars_nav_map', 'FSM_WAITNAVIGATE')),
                                   read_poses=Mock(), connected=Mock(), write_lease=Mock(),
                                   create_session=Mock(side_effect=create_session),
                                   start_adapters=Mock(), navigate=Mock(),
                                   action=Mock(side_effect=AssertionError('No manipulation action'))):
                self.assertEqual(machine.run(), 0, events)
                adapters_started = machine.start_adapters.call_count
                navigation = machine.navigate.call_args_list
                health = machine.health.call_args_list
                machine.action.assert_not_called()
            return machine.checkpoint, adapters_started, navigation, health, events

    def test_get1_arms_without_adapters_and_keeps_health_checks(self):
        checkpoint, adapters_started, navigation, health, events = self.run_supervisor('navigate_get1')
        self.assertEqual(adapters_started, 0)
        self.assertEqual([call.args for call in navigation], [('get1',)])
        self.assertEqual([call.kwargs for call in health], [{'require_home': True}, {'require_home': False}])
        self.assertEqual(checkpoint['completed'], ['navigate_get1'])
        self.assertIsNone(contract.next_stage(checkpoint))
        self.assertEqual([event['stage'] for event in events if event['event'] == 'stage_complete'],
                         ['navigate_get1'])

    def test_existing_grasp_and_full_cycle_still_start_adapters_on_arm(self):
        for stop_after in ('verify_held', 'verify_home'):
            with self.subTest(stop_after=stop_after):
                checkpoint, adapters_started, navigation, health, events = self.run_supervisor(stop_after)
                self.assertEqual(adapters_started, 1)
                self.assertEqual(navigation, [])
                self.assertEqual(checkpoint['completed'], [])
                self.assertEqual([call.kwargs for call in health], [{'require_home': True}])


if __name__ == '__main__':
    unittest.main()
