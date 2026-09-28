"""Arrival-reader regressions: missing telemetry blocks before navigation."""
import copy
from contextlib import ExitStack
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
            checks.validate_nav_pose(pose, {'point_x': 1, 'point_y': 2, 'point_yaw': 0}, 100, 100.2)

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
