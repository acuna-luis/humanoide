"""Arrival-reader regressions: missing telemetry blocks before navigation."""
import copy
from contextlib import ExitStack
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import scenario1_checks as checks
from scripts.box_handling import scenario1_contract as contract
from scripts.box_handling import scenario1_runtime as runtime
from scripts.box_handling.test_scenario1_checks import nav_pose
from scripts.box_handling.test_scenario1_runtime import PROFILE


class PosePreflightTest(unittest.TestCase):
    def machine(self):
        return runtime.Runtime({'checkpoint': contract.new_checkpoint(PROFILE),
                                'profile': PROFILE, 'mode': 'check'}, emit=Mock())

    def test_fresh_telemetry_does_not_certify_arrival(self):
        pose = nav_pose(x=100, y=200)
        sample = checks.validate_pose_sample(pose, 100, 100.2)
        self.assertEqual((sample['x'], sample['y']), (100, 200))
        with self.assertRaisesRegex(ValueError, 'outside'):
            checks.validate_nav_pose(pose, {'point_x': 1, 'point_y': 2, 'point_yaw': 0},
                                     100, 100.2, point='get1')

    def test_preflight_read_requires_two_new_advancing_map_samples(self):
        machine = self.machine()
        good = [nav_pose(ns=100_000_000), nav_pose(ns=200_000_000)]
        with patch.object(runtime.time, 'time', side_effect=[100, 100.3, 100.3]):
            machine.health_request = Mock(return_value={'poses': good, 'publisher_count': 2})
            self.assertEqual(machine.read_poses(), (good, 100))
        detail = machine.emit.call_args.kwargs
        self.assertFalse(detail['arrival_verified'])
        self.assertEqual(detail['publisher_count'], 2)
        bad_frame = copy.deepcopy(good)
        bad_frame[1]['header']['frame_id'] = 'odom'
        for poses in ([good[0]], [good[0], good[0]], [nav_pose(sec=99), good[1]], bad_frame):
            machine.health_request.return_value = {'poses': poses, 'publisher_count': 2}
            with self.subTest(poses=poses), patch.object(runtime.time, 'time', side_effect=[100, 100.3, 100.3]):
                with self.assertRaises((ValueError, RuntimeError)):
                    machine.read_poses()

    def test_missing_pose_blocks_before_navigation_start(self):
        machine = self.machine()
        machine.prepare_map = Mock()
        machine.map_points = Mock()
        machine.read_poses = Mock(side_effect=RuntimeError('pose unavailable'))
        machine.action = Mock(side_effect=AssertionError('No physical goal'))
        with self.assertRaisesRegex(RuntimeError, 'pose unavailable'):
            machine.navigate('get1')
        machine.action.assert_not_called()

    def navigation_machine(self, arrivals):
        """Exercise real navigate/read_poses with in-memory transport only."""
        machine = self.machine()
        machine.prepare_map = Mock()
        machine.points = {point: {'id': point, 'mode': 'free_nav',
            'point_x': 1., 'point_y': 2., 'point_yaw': 0.,
            '_expected_pose': {'point_x': 1., 'point_y': 2., 'point_yaw': 0.}}
            for point in ('get1', 'put1')}
        machine.map_points = Mock(return_value=machine.points)
        # A corrective preflight must remain offline in these reader tests.
        machine.discover = Mock()
        machine.hashes = Mock()
        machine.health = Mock()
        machine.map_state = Mock(return_value=('utars_nav_map', 'FSM_WAITNAVIGATE'))
        machine.action = Mock(return_value={'event': 'result', 'status': 4,
            'result': {'state': {'desc': 'SUCCEED', 'state': 1101001},
                       'dmsg': 'navigation_start SUCCEEDED'}})
        reports = [
            {'poses': [nav_pose(ns=100_000_000), nav_pose(ns=200_000_000)], 'publisher_count': 2},
            {'poses': arrivals, 'publisher_count': 2},
        ]
        clock = {'now': 100.}

        def telemetry(kind):
            self.assertEqual(kind, 'pose')
            result = reports.pop(0)
            clock['now'] += .3
            return result

        machine.health_request = Mock(side_effect=telemetry)
        return machine, clock

    def assert_one_navigation_goal(self, machine, point):
        machine.action.assert_called_once()
        kind, goal, timeout = machine.action.call_args.args
        self.assertEqual((kind, goal['command'], timeout), ('navigation', 'navigation_start', 180))
        target = json.loads(goal['arg_json'])['target_point']
        self.assertEqual(target['id'], point)
        self.assertNotIn('_expected_pose', target)

    def test_navigation_22mm_requires_get1_correction_checks_but_put1_accepts(self):
        arrivals = [nav_pose(x=1.022, ns=400_000_000), nav_pose(x=1.022, ns=500_000_000)]
        for point in ('get1', 'put1'):
            with self.subTest(point=point):
                machine, clock = self.navigation_machine(arrivals)
                machine.health.side_effect = RuntimeError('correction preflight blocked')
                with patch.object(runtime.time, 'time', side_effect=lambda: clock['now']):
                    if point == 'get1':
                        with self.assertRaisesRegex(RuntimeError, 'correction preflight blocked'):
                            machine.navigate(point)
                    else:
                        machine.navigate(point)
                self.assert_one_navigation_goal(machine, point)
                self.assertEqual(machine.health_request.call_count, 2)
                arrivals_logged = [call for call in machine.emit.call_args_list if call.args[0] == 'arrival']
                self.assertEqual(len(arrivals_logged), 0 if point == 'get1' else 2)

    def test_navigation_accepts_get1_only_after_both_samples_pass(self):
        arrivals = [nav_pose(x=1.019, yaw=math.radians(1.9), ns=400_000_000),
                    nav_pose(y=2.019, yaw=math.radians(-1.9), ns=500_000_000)]
        machine, clock = self.navigation_machine(arrivals)
        with patch.object(runtime.time, 'time', side_effect=lambda: clock['now']):
            machine.navigate('get1')
        self.assert_one_navigation_goal(machine, 'get1')
        measured = [call.kwargs['measurement'] for call in machine.emit.call_args_list
                    if call.args[0] == 'arrival']
        self.assertEqual(len(measured), 2)
        self.assertLess(measured[0]['stamp_ns'], measured[1]['stamp_ns'])
        self.assertTrue(all(item['distance_m'] < .02 and item['yaw_error_deg'] < 2 for item in measured))

    def test_either_get1_sample_outside_correction_envelope_fails_without_retry(self):
        for failed_index in (0, 1):
            for kind in ('distance', 'yaw'):
                with self.subTest(failed_index=failed_index, kind=kind):
                    arrivals = [nav_pose(ns=400_000_000), nav_pose(ns=500_000_000)]
                    arguments = {'x': 1.060001} if kind == 'distance' else {'yaw': math.radians(6.0001)}
                    arrivals[failed_index] = nav_pose(ns=(failed_index+4)*100_000_000, **arguments)
                    machine, clock = self.navigation_machine(arrivals)
                    with patch.object(runtime.time, 'time', side_effect=lambda: clock['now']):
                        with self.assertRaises((ValueError, RuntimeError)):
                            machine.navigate('get1')
                    self.assert_one_navigation_goal(machine, 'get1')
                    self.assertEqual(machine.health_request.call_count, 2)
                    self.assertNotIn('stage_complete', [call.args[0] for call in machine.emit.call_args_list])

    def test_rejected_get1_latches_checkpoint_and_blocks_vision_and_grasp(self):
        arrivals = [nav_pose(ns=400_000_000), nav_pose(x=1.06, ns=500_000_000)]
        machine, clock = self.navigation_machine(arrivals)
        machine.armed = True
        for name in ('discover', 'hashes', 'health'):
            setattr(machine, name, Mock())
        with tempfile.TemporaryDirectory() as directory:
            machine.session = Path(directory)
            with patch.object(runtime.time, 'time', side_effect=lambda: clock['now']):
                with self.assertRaises((ValueError, RuntimeError)):
                    machine.stage({'stage': 'navigate_get1'})
                stored = json.loads((machine.session/'checkpoint.json').read_text())
                self.assertEqual(stored['completed'], [])
                self.assertEqual(stored['failure']['stage'], 'navigate_get1')
                self.assertIsNone(stored['in_flight'])
                self.assertEqual(stored['box_state'], 'unknown')
                for stage in ('navigate_get1', 'enable_vision', 'grasp'):
                    with self.subTest(stage=stage), self.assertRaises(ValueError):
                        machine.stage({'stage': stage})
        self.assert_one_navigation_goal(machine, 'get1')
        self.assertNotIn('stage_complete', [call.args[0] for call in machine.emit.call_args_list])

    def test_check_exercises_pose_and_fails_before_ready(self):
        machine = self.machine()
        machine.native_container = 'mock'
        for name in ('discover', 'hashes', 'health', 'map_points'):
            setattr(machine, name, Mock())
        machine.map_state = Mock(return_value=('utars_nav_map', 'FSM_WAITNAVIGATE'))
        machine.read_poses = Mock(side_effect=RuntimeError('pose unavailable'))
        machine.action = Mock(side_effect=AssertionError('No physical goal'))
        machine.start_adapters = Mock(side_effect=AssertionError('No SPS adapter'))
        with ExitStack() as stack:
            handle = stack.enter_context(tempfile.TemporaryFile())
            stack.enter_context(patch.object(runtime, 'open', return_value=handle, create=True))
            stack.enter_context(patch.object(runtime.threading, 'Thread'))
            stack.enter_context(patch.object(runtime.signal, 'signal'))
            stack.enter_context(patch.object(runtime, 'check_sps_discovery'))
            self.assertEqual(machine.run(), 78)
        machine.read_poses.assert_called_once_with()
        machine.start_adapters.assert_not_called()
        machine.action.assert_not_called()
        self.assertNotIn('ready', [call.args[0] for call in machine.emit.call_args_list])


if __name__ == '__main__':
    unittest.main()
