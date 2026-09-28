"""Optimization regressions: fewer processes, unchanged physical-stage gates."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import scenario1_runtime as runtime
from scripts.box_handling import scenario1_contract as contract
from scripts.box_handling import scenario1_cli as cli
from scripts.box_handling.test_scenario1_runtime import PROFILE, SimulatedRuntime


class OptimizationTest(unittest.TestCase):
    def test_benchmark_cannot_arm_or_run(self):
        for mode in ('--run', '--plan', '--resume'):
            argv = [mode] + (['unused-checkpoint'] if mode == '--resume' else [])
            args = cli.parser('assume').parse_args(argv+['--benchmark-checks', '3'])
            with patch.object(cli, 'Connection', side_effect=AssertionError('No SSH')):
                with self.assertRaisesRegex(ValueError, 'sólo permite'):
                    cli._main(args)
        machine = runtime.Runtime({'checkpoint': contract.new_checkpoint(PROFILE), 'mode': 'run'})
        with self.assertRaisesRegex(ValueError, 'READ_ONLY'):
            machine.benchmark_checks(3, ('utars_nav_map', 'FSM_WAITNAVIGATE'))

    def test_benchmark_repeats_fresh_checks_without_preparing_or_navigating(self):
        machine = runtime.Runtime({'checkpoint': contract.new_checkpoint(PROFILE), 'mode': 'check'}, emit=Mock())
        for name in ('discover', 'hashes', 'health', 'read_poses'):
            setattr(machine, name, Mock())
        machine.prepare_map = Mock(side_effect=AssertionError('No map preparation'))
        machine.navigate = Mock(side_effect=AssertionError('No motion'))
        state = ('utars_nav_map', 'FSM_WAITNAVIGATE')
        machine.map_state = Mock(return_value=state)
        machine.benchmark_checks(3, state)
        for name in ('discover', 'hashes', 'health', 'map_state', 'read_poses'):
            self.assertEqual(getattr(machine, name).call_count, 3)
        machine.health.assert_called_with(require_home=True)
        machine.map_state.return_value = ('', 'FSM_WAITSETMAP')
        with self.assertRaisesRegex(RuntimeError, 'MAP_STATE_CHANGED'):
            machine.benchmark_checks(1, state)

    def test_assumption_stages_only_record_checkpoint_next_motion_still_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = SimulatedRuntime(directory)
            machine.policy = 'assume'
            machine.checkpoint = contract.new_checkpoint(PROFILE, policy='assume')
            health, discover, hashes = [], [], []
            machine.health = lambda require_home=False: health.append((machine.checkpoint['in_flight'], require_home))
            machine.discover = lambda: discover.append(machine.checkpoint['in_flight'])
            machine.hashes = lambda: hashes.append(machine.checkpoint['in_flight'])
            for stage in contract.STAGES:
                machine.stage({'stage': stage})
            checked = [stage for stage in contract.STAGES if stage not in ('verify_held', 'verify_released')]
            self.assertEqual(discover, checked)
            self.assertEqual(hashes, checked)
            self.assertEqual([stage for stage, _ in health], checked)
            self.assertEqual(health[-1], ('verify_home', True))
            self.assertEqual(machine.checkpoint['confirmations']['verify_held']['source'], 'assumed')
            self.assertEqual(machine.checkpoint['completed'], list(contract.STAGES))

    def test_failure_after_logical_assumption_still_blocks_retreat(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = SimulatedRuntime(directory)
            machine.policy = 'assume'
            machine.checkpoint = contract.new_checkpoint(PROFILE, policy='assume')
            for stage in contract.STAGES[:4]:
                machine.stage({'stage': stage})
            machine.fail_health_at = 'retreat'
            with self.assertRaisesRegex(RuntimeError, 'Health'):
                machine.stage({'stage': 'retreat'})
            self.assertNotIn('cruzr/mobot_back_20', machine.calls)
            self.assertEqual(machine.checkpoint['box_state'], 'unknown')

    def test_ready_map_queries_once_no_mutating_commands(self):
        machine = runtime.Runtime({'checkpoint': contract.new_checkpoint(PROFILE)})
        machine.map_state = Mock(return_value=('utars_nav_map', 'FSM_WAITNAVIGATE'))
        machine.nav = Mock(side_effect=AssertionError('No map mutation'))
        machine.prepare_map()
        machine.map_state.assert_called_once_with()

    def test_map_loading_still_checks_final_state(self):
        machine = runtime.Runtime({'checkpoint': contract.new_checkpoint(PROFILE)})
        machine.map_state = Mock(side_effect=[('', 'FSM_WAITSETMAP'), ('utars_nav_map', 'FSM_WAITNAVIGATE')])
        machine.nav = Mock(return_value={'state': {'desc': 'SUCCESS'}})
        machine.prepare_map()
        self.assertEqual(machine.map_state.call_count, 2)
        self.assertEqual([call.args[0] for call in machine.nav.call_args_list], ['map_set', 'relocation_start'])

    def test_actions_reuse_one_process_per_endpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = runtime.Runtime({'checkpoint': contract.new_checkpoint(PROFILE), 'action_client': '# fake'})
            machine.session = Path(directory)
            machine.native_container = 'fake'
            result = {'event': 'result', 'status': 4, 'result': {'state': {'desc': 'SUCCEED', 'state': 1101001}}}
            worker = Mock(failed=False)
            worker.process.poll.return_value = None
            worker.call.return_value = [result]
            with patch.object(runtime, 'ProcessSession', return_value=worker) as factory:
                self.assertEqual(machine.action('motion', {'task_name': 'cruzr/home'}, 60), result)
                self.assertEqual(machine.action('motion', {'task_name': 'cruzr/home'}, 60), result)
            factory.assert_called_once()
            self.assertEqual(worker.call.call_count, 2)

    def test_dead_persistent_worker_prevents_next_stage(self):
        machine = runtime.Runtime({'checkpoint': contract.new_checkpoint(PROFILE)})
        worker = Mock(failed=False)
        worker.process.poll.return_value = 78
        machine.health_session = worker
        with self.assertRaisesRegex(RuntimeError, 'PERSISTENT_WORKER_LOST'):
            machine.connected()
        self.assertTrue(machine.stop.is_set())


if __name__ == '__main__':
    unittest.main()
