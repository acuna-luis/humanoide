"""Multiple-box supervision and durable journals, entirely offline."""
import copy
import io
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import scenario1_cli as cli
from scripts.box_handling import scenario1_contract as contract
from scripts.box_handling import scenario1_runtime as runtime
from scripts.box_handling.test_scenario1_optimistic import optimistic_machine
from scripts.box_handling.test_scenario1_runtime import PROFILE


def completed_cycle():
    checkpoint = contract.new_checkpoint(PROFILE, policy='assume', execution_profile='optimistic_v1')
    for stage in contract.STAGES:
        checkpoint = contract.begin_stage(checkpoint, stage)
        arguments = {'home_verified': stage == 'verify_home'}
        if stage in ('verify_held', 'verify_released'):
            arguments.update(confirmed_box='held' if stage == 'verify_held' else 'released',
                             verification_source='assumed')
        checkpoint = contract.complete_stage(checkpoint, stage, **arguments)
    return checkpoint


class CycleContractTests(unittest.TestCase):
    def test_reset_preserves_profile_and_clears_only_after_full_home_completion(self):
        original = completed_cycle()
        before = copy.deepcopy(original)
        following = contract.next_cycle_checkpoint(original, PROFILE)
        self.assertEqual(original, before)
        self.assertEqual(following['profile_sha256'], original['profile_sha256'])
        self.assertEqual(following['box_state'], 'empty')
        self.assertEqual(following['completed'], [])
        self.assertEqual(following['confirmations'], {})
        self.assertEqual(contract.next_stage(following), 'navigate_get1')

    def test_count_is_positive_exact_integer(self):
        for value in (0, -1, True, 4., '4', None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                contract.cycle_count(value)
        self.assertEqual(contract.cycle_count(4), 4)

    def test_partial_failed_and_inflight_cycles_cannot_reset(self):
        fresh = contract.new_checkpoint(PROFILE, policy='assume', execution_profile='optimistic_v1')
        checkpoints = [fresh, contract.begin_stage(fresh, 'navigate_get1'),
                       contract.fail_stage(fresh, 'navigate_get1', 'test failure')]
        partial = completed_cycle()
        partial['completed'].pop()
        checkpoints.append(partial)
        for cp in checkpoints:
            with self.subTest(checkpoint=cp), self.assertRaises(ValueError):
                contract.next_cycle_checkpoint(cp, PROFILE)


class CycleBoundaryTests(unittest.TestCase):
    def machine(self, directory):
        machine = optimistic_machine(directory)
        machine.cycle_count = 4
        machine.checkpoint = completed_cycle()
        machine.discover = Mock()
        machine.hashes = Mock()
        machine.quick_health = Mock()
        machine.check_live_health = Mock(return_value={'home_required': True})
        machine.map_state = Mock(return_value=('utars_nav_map', 'FSM_WAITNAVIGATE'))
        machine.map_points = Mock()
        machine.last_action_end_ns = 123
        machine.box_association = {'previous_box': True}
        machine.session_deadline = time.monotonic()+900
        return machine

    def test_boundary_reuses_session_and_checks_fresh_home_without_motion_or_relocalization(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = self.machine(directory)
            session, deadline = machine.session, machine.session_deadline
            machine.action, machine.nav, machine.health, machine.prepare_map = Mock(), Mock(), Mock(), Mock()
            machine.next_cycle({'command': 'next_cycle', 'cycle_index': 2})
            self.assertEqual(machine.cycle_index, 2)
            self.assertEqual(machine.checkpoint['completed'], [])
            self.assertIsNone(machine.box_association)
            self.assertEqual(machine.session, session)
            self.assertEqual(machine.session_deadline, deadline)
            machine.check_live_health.assert_called_once_with(stationary=True, after_ns=123, require_home=True)
            machine.quick_health.assert_called_once_with()
            for method in (machine.action, machine.nav, machine.health, machine.prepare_map):
                method.assert_not_called()
            cp = json.loads((session/'cycles/0002/checkpoint.json').read_text())
            self.assertEqual(cp, machine.checkpoint)

    def test_health_home_map_and_dependencies_fail_before_reset(self):
        for failing in ('connected', 'discover', 'hashes', 'quick_health', 'check_live_health', 'map_points', 'map_state'):
            with tempfile.TemporaryDirectory() as directory:
                machine = self.machine(directory)
                original = copy.deepcopy(machine.checkpoint)
                if failing == 'map_state':
                    machine.map_state.return_value = ('utars_nav_map', 'FSM_WAITRELOCATE')
                else:
                    setattr(machine, failing, Mock(side_effect=RuntimeError(failing+' invalid')))
                with self.subTest(failing=failing), self.assertRaises(RuntimeError):
                    machine.next_cycle({'command': 'next_cycle', 'cycle_index': 2})
                self.assertEqual(machine.checkpoint, original)
                self.assertEqual(machine.cycle_index, 1)
                self.assertFalse((machine.session/'cycles/0002').exists())
                self.assertEqual(machine.calls, [])

    def test_out_of_order_duplicate_and_past_limit_commands_block(self):
        for index in (1, 3, True, 2.):
            with tempfile.TemporaryDirectory() as directory:
                machine = self.machine(directory)
                with self.subTest(index=index), self.assertRaisesRegex(RuntimeError, 'OUT_OF_ORDER'):
                    machine.next_cycle({'command': 'next_cycle', 'cycle_index': index})
        with tempfile.TemporaryDirectory() as directory:
            machine = self.machine(directory)
            machine.cycle_index = 4
            with self.assertRaisesRegex(RuntimeError, 'OUT_OF_ORDER'):
                machine.next_cycle({'command': 'next_cycle', 'cycle_index': 5})

    def test_previous_cycle_stage_cannot_move_current_box(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = self.machine(directory)
            machine.next_cycle({'command': 'next_cycle', 'cycle_index': 2})
            with self.assertRaisesRegex(RuntimeError, 'STAGE_CYCLE_MISMATCH'):
                machine.stage({'stage': 'navigate_get1', 'cycle_index': 1})
            self.assertEqual(machine.checkpoint['completed'], [])
            self.assertEqual(machine.calls, [])

    def test_remote_rejects_partial_resumed_and_wrong_profile_batches(self):
        fresh = contract.new_checkpoint(PROFILE, policy='assume', execution_profile='optimistic_v1')
        for change in ({'cycle_count': True}, {'cycle_count': 0},
                       {'checkpoint': contract.new_checkpoint(PROFILE, stop_after='deposit',
                            policy='assume', execution_profile='optimistic_v1')},
                       {'checkpoint': completed_cycle()}, {'resume_plan': {}},
                       {'execution_profile': 'standard_v1'}):
            payload = dict(profile=PROFILE, checkpoint=fresh, execution_profile='optimistic_v1',
                           policy='assume', cycle_count=4)
            payload.update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                runtime.Runtime(payload, emit=Mock())

    def test_real_dispatch_loop_completes_four_boxes_with_one_initialization(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = optimistic_machine(directory)
            machine.armed = False
            machine.cycle_count = 4
            machine.payload['cycle_count'] = 4
            machine.payload['mode'] = 'run'
            machine.native_container = 'offline'
            machine.health = Mock()
            machine.check_live_health = Mock(return_value={'home_required': True})
            machine.map_state = Mock(return_value=('utars_nav_map', 'FSM_WAITNAVIGATE'))
            machine.map_points = Mock(return_value={})
            machine.read_poses = Mock()
            machine.start_live_monitor = Mock()
            machine.check_box_alignment_head = Mock()
            machine.start_adapters = Mock()
            machine.create_session = Mock()
            machine.commands.put({'command': 'arm'})
            for index in range(1, 5):
                if index > 1:
                    machine.commands.put({'command': 'next_cycle', 'cycle_index': index})
                for stage in contract.STAGES:
                    machine.commands.put({'command': 'stage', 'stage': stage, 'cycle_index': index})
            machine.commands.put({'command': 'finish'})
            with patch.object(runtime.threading, 'Thread'), patch.object(runtime.signal, 'signal'), \
                    patch.object(runtime, 'open', side_effect=lambda *a: open(Path(directory)/'lock', 'a'), create=True), \
                    patch.object(runtime, 'check_sps_discovery'), \
                    patch.object(runtime.subprocess, 'run', side_effect=AssertionError('No commands')):
                self.assertEqual(machine.run(), 0, machine.events)
            machine.start_live_monitor.assert_called_once_with()
            machine.start_adapters.assert_called_once_with()
            machine.check_box_alignment_head.assert_called_once_with()
            self.assertEqual(machine.align_box_for_pickup.call_count, 4)
            self.assertEqual(machine.calls.count('cruzr/home'), 4)
            self.assertEqual(machine.calls.count('get1'), 4)
            self.assertEqual(machine.calls.count('put1'), 4)
            self.assertEqual(machine.health.call_count, 5)  # initial + HOME each box
            self.assertEqual(machine.cycle_index, 4)
            self.assertEqual(machine.checkpoint['completed'], list(contract.STAGES))

    def test_finish_cannot_report_success_for_an_unfinished_batch(self):
        for completed_first in (False, True):
            with tempfile.TemporaryDirectory() as directory:
                machine = optimistic_machine(directory)
                machine.cycle_count = 4
                machine.payload.update(mode='run', cycle_count=4)
                if completed_first:
                    machine.checkpoint = completed_cycle()
                machine.native_container = 'offline'
                machine.commands.put({'command': 'finish'})
                machine.health = Mock()
                machine.read_poses = Mock()
                machine.start_live_monitor = Mock()
                machine.check_box_alignment_head = Mock()
                machine.map_state = Mock(return_value=('utars_nav_map', 'FSM_WAITNAVIGATE'))
                machine.map_points = Mock(return_value={})
                machine.action = Mock(side_effect=AssertionError('No movement'))
                with patch.object(runtime.threading, 'Thread'), patch.object(runtime.signal, 'signal'), \
                        patch.object(runtime, 'open', side_effect=lambda *a: open(Path(directory)/'lock', 'a'), create=True), \
                        patch.object(runtime, 'check_sps_discovery'), self.subTest(completed_first=completed_first):
                    self.assertEqual(machine.run(), 78)
                machine.action.assert_not_called()
                self.assertEqual(machine.calls, [])


class CycleCliTests(unittest.TestCase):
    def test_plan_four_boxes_is_offline_and_default_remains_one(self):
        for arguments, count in ((['--plan', '--cycle', '4'], 4), (['--plan'], 1)):
            with patch.object(cli, 'Connection', side_effect=AssertionError('No network')), \
                    patch('sys.stdout', io.StringIO()) as output:
                self.assertEqual(cli.main(arguments, policy='assume', execution_profile='optimistic_v1'), 0)
            plan = json.loads(output.getvalue()[output.getvalue().index('{'):])
            self.assertEqual(plan['cycle_count'], count)
            self.assertEqual(plan['stages'], list(contract.STAGES))
            self.assertTrue(plan['batch']['measured_home_between_boxes'])
            self.assertEqual(plan['batch']['session_time_limit_s'], 900)

    def test_invalid_batches_block_before_connection_or_reading_resume(self):
        for arguments in (['--run', '--cycle', '0'], ['--run', '--cycle', '-4'],
                          ['--run', '--cycle', '4', '--stop-after', 'grasp'],
                          ['--cycle', '4', '--resume', '/nonexistent/checkpoint.json']):
            with patch.object(cli, 'Connection', side_effect=AssertionError('No network')), \
                    self.subTest(arguments=arguments), self.assertRaises(ValueError):
                cli.main(arguments, policy='assume', execution_profile='optimistic_v1')

    def run_batch(self, root, *, failure_cycle=None, mismatch=False, check=False):
        instances, messages = [], []
        evidence = root/'pc'

        class OfflineConnection:
            def __init__(self, payload, wifi, location, *, console=None):
                instances.append(self)
                self.location = location
                self.process = Mock()
                self.process.wait.return_value = 0
                self.machine = optimistic_machine(root/'remote')
                self.machine.session.mkdir()
                self.machine.payload.update(payload)
                self.machine.checkpoint = copy.deepcopy(payload['checkpoint'])
                self.machine.cycle_count = payload['cycle_count']
                self.machine.check_live_health = Mock(return_value={'home_required': True})
                self.machine.map_state = Mock(return_value=('utars_nav_map', 'FSM_WAITNAVIGATE'))
                self.machine.map_points = Mock()
                self.machine.health = Mock()
                self.responses = {}
                def emit(event, **values):
                    self.responses[event] = dict(event=event, **values)
                    if event == 'checkpoint':
                        cli.atomic_json(location/'checkpoint.json', values['checkpoint'])
                self.machine.emit = emit

            def send(self, message):
                messages.append(copy.deepcopy(message))
                if message['command'] == 'next_cycle':
                    self.machine.next_cycle(message)
                elif message['command'] == 'stage':
                    saved = json.loads((self.location/'cycles'/f"{message['cycle_index']:04d}"/'checkpoint.json').read_text())
                    if saved['in_flight'] != message['stage']:
                        raise AssertionError('PC intent not persisted before motion')
                    if message['cycle_index'] == failure_cycle and message['stage'] == 'grasp':
                        self.machine.failure_task = 'local_front_box/separate_right_cruzr'
                    self.machine.stage(message)

            def wait(self, desired, timeout=None):
                if desired == 'ready':
                    return dict(context={'test': 'offline'}, map_name='utars_nav_map', nav_state='FSM_WAITNAVIGATE')
                if desired == 'armed':
                    return {}
                result = copy.deepcopy(self.responses[desired])
                if mismatch and desired == 'cycle_ready':
                    result['cycle_index'] = 4
                return result

            def close(self):
                pass

        with patch.object(cli, 'Connection', OfflineConnection), patch.object(cli.subprocess, 'run'), \
                patch.object(cli, 'open', side_effect=lambda name, mode: open(root/Path(name).name, mode), create=True), \
                patch('builtins.input', side_effect=AssertionError('No prompts')), \
                patch('sys.stdout', io.StringIO()):
            result = cli.entrypoint(['--check' if check else '--run', '--cycle', '4', '--profile',
                str(cli.HERE/'scenario1_current_geometry.json'), '--evidence-dir', str(evidence)],
                policy='assume', execution_profile='optimistic_v1')
        return result, evidence, instances, messages

    def test_four_boxes_share_one_connection_and_have_independent_resume_journals(self):
        with tempfile.TemporaryDirectory() as directory:
            result, evidence, instances, messages = self.run_batch(Path(directory))
            self.assertEqual(result, 0)
            self.assertEqual(len(instances), 1)
            self.assertEqual(len([m for m in messages if m['command'] == 'arm']), 1)
            self.assertEqual(len([m for m in messages if m['command'] == 'next_cycle']), 3)
            self.assertEqual(len([m for m in messages if m['command'] == 'stage']), 40)
            batch = json.loads((evidence/'batch.json').read_text())
            self.assertEqual(batch['completed_cycles'], 4)
            self.assertEqual(batch['status'], 'completed')
            for index in range(1, 5):
                folder = evidence/'cycles'/f'{index:04d}'
                checkpoint = contract.validate_checkpoint(json.loads((folder/'checkpoint.json').read_text()), PROFILE)
                self.assertEqual(checkpoint['completed'], list(contract.STAGES))
                self.assertEqual(checkpoint['confirmations']['verify_released']['source'], 'assumed')
                self.assertEqual(json.loads((folder/'context.json').read_text()), {'test': 'offline'})

    def test_failure_in_second_box_stops_batch_and_preserves_first_box(self):
        with tempfile.TemporaryDirectory() as directory:
            result, evidence, instances, messages = self.run_batch(Path(directory), failure_cycle=2)
            self.assertEqual(result, 78)
            batch = json.loads((evidence/'batch.json').read_text())
            self.assertEqual(batch['completed_cycles'], 1)
            self.assertEqual(batch['current_cycle'], 2)
            self.assertEqual(batch['status'], 'interrupted')
            self.assertFalse(any(m.get('cycle_index') == 3 for m in messages))
            self.assertNotIn({'command': 'finish'}, messages)
            first = json.loads((evidence/'cycles/0001/checkpoint.json').read_text())
            second = json.loads((evidence/'cycles/0002/checkpoint.json').read_text())
            self.assertEqual(first['completed'], list(contract.STAGES))
            self.assertEqual(second['failure']['stage'], 'grasp')
            self.assertEqual(second['box_state'], 'unknown')
            self.assertEqual(instances[0].machine.calls.count('cruzr/home'), 1)

    def test_wrong_cycle_acknowledgement_prevents_second_box_motion(self):
        with tempfile.TemporaryDirectory() as directory:
            result, evidence, _, messages = self.run_batch(Path(directory), mismatch=True)
            self.assertEqual(result, 78)
            self.assertFalse(any(m['command'] == 'stage' and m['cycle_index'] == 2 for m in messages))
            self.assertEqual(json.loads((evidence/'batch.json').read_text())['status'], 'interrupted')

    def test_check_with_four_cycles_never_arms_or_counts_a_box(self):
        with tempfile.TemporaryDirectory() as directory:
            result, evidence, _, messages = self.run_batch(Path(directory), check=True)
            self.assertEqual(result, 0)
            self.assertEqual(messages, [])
            batch = json.loads((evidence/'batch.json').read_text())
            self.assertEqual(batch['completed_cycles'], 0)
            self.assertEqual(batch['status'], 'checked')


if __name__ == '__main__':
    unittest.main()
