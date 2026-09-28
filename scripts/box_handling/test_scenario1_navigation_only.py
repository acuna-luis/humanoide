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


PROFILE = json.loads(Path(__file__).with_name('scenario1_current_geometry.json').read_text())


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
