"""Bounded get1 correction regression tests; transport and telemetry are synthetic."""
import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import scenario1_contract as contract
from scripts.box_handling import scenario1_runtime as runtime
from scripts.box_handling.test_scenario1_checks import nav_pose
from scripts.box_handling.test_scenario1_runtime import PROFILE


SUCCESS = {'event': 'result', 'status': 4,
           'result': {'state': {'desc': 'SUCCEED', 'state': 1101001},
                      'dmsg': 'navigation_start SUCCEEDED'}}
EXPECTED = {'point_x': 1., 'point_y': 2., 'point_yaw': 0.}


def pair(distance=0., yaw_deg=0.):
    sample = dict(x=1.+distance, y=2., yaw=math.radians(yaw_deg))
    return [copy.deepcopy(sample), copy.deepcopy(sample)]


class NavigationCorrectionTests(unittest.TestCase):
    def machine(self, samples):
        machine = runtime.Runtime(dict(mode='run', profile=PROFILE,
            checkpoint=contract.new_checkpoint(PROFILE, stop_after='navigate_get1', policy='assume')),
            emit=Mock())
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        machine.session = Path(directory.name)
        machine.points = {name: dict(map_name='utars_nav_map', mode='logo_nav', id=name,
                                    _expected_pose=copy.deepcopy(EXPECTED))
                          for name in ('get1', 'put1')}
        machine.prepare_map = Mock()
        machine.map_points = Mock(return_value=machine.points)
        machine.map_state = Mock(return_value=('utars_nav_map', 'FSM_WAITNAVIGATE'))
        machine.discover = Mock()
        machine.hashes = Mock()
        machine.health = Mock()
        machine.action = Mock(return_value=copy.deepcopy(SUCCESS))
        clock = {'wall': 100., 'monotonic': 100.}
        reports = copy.deepcopy(samples)

        def telemetry(kind):
            self.assertEqual(kind, 'pose')
            if not reports:
                raise AssertionError('Unexpected extra pose query or correction attempt')
            result = []
            for index, values in enumerate(reports.pop(0)):
                stamp_ns = round((clock['wall']+.1*(index+1))*1e9)
                pose = nav_pose(sec=stamp_ns//1_000_000_000, ns=stamp_ns%1_000_000_000,
                                **{name: value for name, value in values.items()
                                   if name in ('x', 'y', 'yaw')})
                if 'frame' in values:
                    pose['header']['frame_id'] = values['frame']
                if 'stamp_ns' in values:
                    stamp = values['stamp_ns']
                    pose['header']['stamp'] = dict(sec=stamp//1_000_000_000, nanosec=stamp%1_000_000_000)
                result.append(pose)
            clock['wall'] += .3
            clock['monotonic'] += .3
            return {'poses': result, 'publisher_count': 2}

        machine.health_request = Mock(side_effect=telemetry)
        return machine, clock

    def navigate(self, machine, clock, point='get1'):
        with patch.object(runtime.time, 'time', side_effect=lambda: clock['wall']), \
                patch.object(runtime.time, 'monotonic', side_effect=lambda: clock['monotonic']), \
                patch.object(runtime.subprocess, 'run', side_effect=AssertionError('No subprocesses')), \
                patch.object(runtime.subprocess, 'Popen', side_effect=AssertionError('No subprocesses')):
            machine.navigate(point)

    def assert_correction_goal(self, call, attempt):
        kind, goal, timeout = call.args
        self.assertEqual((kind, goal['command'], timeout), ('navigation', 'navigation_start', 30))
        target = json.loads(goal['arg_json'])['target_point']
        self.assertEqual({name: target[name] for name in EXPECTED}, EXPECTED)
        self.assertEqual((target['mode'], target['map_name'], target['level']),
                         ('free_nav', 'utars_nav_map', 1))
        self.assertEqual(target['speed'], {'linear': {'x': .05, 'y': .01, 'z': 0.},
                                          'angular': {'x': 0., 'y': 0., 'z': .15}})
        self.assertNotIn('_expected_pose', target)
        spec = call.kwargs['correction']
        self.assertEqual(spec['attempt'], attempt)
        self.assertEqual(spec['target'], EXPECTED)
        self.assertEqual(spec['point'], 'get1')

    def test_normal_arrival_adds_no_correction_checks_or_goals(self):
        machine, clock = self.machine([pair(.3), pair(.005)])
        self.navigate(machine, clock)
        machine.action.assert_called_once()
        machine.discover.assert_not_called()
        machine.hashes.assert_not_called()
        machine.health.assert_not_called()
        self.assertEqual(machine.map_points.call_count, 1)
        self.assertEqual(machine.health_request.call_count, 2)
        self.assertEqual(machine.action.call_args.kwargs, {})

    def test_permission_enables_validation_without_claiming_physical_qualification(self):
        report = runtime.nav_correction.qualification_report()
        self.assertIs(report['motion_enabled'], True)
        self.assertEqual(report['status'], 'enabled_for_validation')
        self.assertEqual(report['physical_validation'], 'pending')
        runtime.nav_correction.require_motion_qualified()

    def test_one_correction_uses_same_target_after_fresh_preflight(self):
        machine, clock = self.machine([pair(.3), pair(.03), pair(.03), pair(.005)])
        frozen_points = copy.deepcopy(machine.points)
        self.navigate(machine, clock)
        self.assertEqual(machine.action.call_count, 2)
        self.assert_correction_goal(machine.action.call_args_list[1], 1)
        reference = machine.action.call_args_list[1].kwargs['correction']['reference']
        self.assertEqual({name: reference[name] for name in ('x', 'y', 'yaw')},
                         {'x': 1.03, 'y': 2., 'yaw': 0.})
        self.assertGreater(reference['stamp_ns'], 100_700_000_000)
        machine.discover.assert_called_once_with()
        machine.hashes.assert_called_once_with()
        machine.health.assert_called_once_with(require_home=True)
        self.assertEqual(machine.points, frozen_points)
        self.assertEqual(machine.map_points.call_count, 2)
        self.assertEqual(machine.health_request.call_count, 4)

    def test_fresh_pose_already_within_tolerance_avoids_extra_motion(self):
        machine, clock = self.machine([pair(.3), pair(.03), pair(.005)])
        self.navigate(machine, clock)
        machine.action.assert_called_once()
        machine.health.assert_called_once_with(require_home=True)
        self.assertEqual(machine.health_request.call_count, 3)

    def test_two_corrections_require_improvement_and_reuse_same_destination(self):
        machine, clock = self.machine([pair(.3), pair(.04), pair(.04),
                                       pair(.03), pair(.03), pair(.005)])
        self.navigate(machine, clock)
        self.assertEqual(machine.action.call_count, 3)
        for attempt in (1, 2):
            self.assert_correction_goal(machine.action.call_args_list[attempt], attempt)
        self.assertEqual(machine.health.call_count, 2)
        self.assertEqual(machine.health_request.call_count, 6)

    def test_insufficient_improvement_prevents_second_correction(self):
        machine, clock = self.machine([pair(.3), pair(.04), pair(.04), pair(.039), pair(.039)])
        with self.assertRaises((ValueError, RuntimeError)):
            self.navigate(machine, clock)
        self.assertEqual(machine.action.call_count, 2)

    def test_second_correction_progress_accounts_for_yaw(self):
        machine, clock = self.machine([pair(.3), pair(0, 4), pair(0, 4),
                                       pair(0, 2.8), pair(0, 2.8), pair(0, 1)])
        self.navigate(machine, clock)
        self.assertEqual(machine.action.call_count, 3)
        self.assert_correction_goal(machine.action.call_args_list[2], 2)

    def test_distance_improvement_without_worst_error_improvement_is_insufficient(self):
        machine, clock = self.machine([pair(.3), pair(.04, 4), pair(.04, 4),
                                       pair(.025, 4), pair(.025, 4)])
        with self.assertRaises((ValueError, RuntimeError)):
            self.navigate(machine, clock)
        self.assertEqual(machine.action.call_count, 2)

    def test_two_attempt_limit_never_dispatches_a_third_correction(self):
        machine, clock = self.machine([pair(.3), pair(.049), pair(.049),
                                       pair(.035), pair(.035), pair(.023)])
        with self.assertRaises((ValueError, RuntimeError)):
            self.navigate(machine, clock)
        self.assertEqual(machine.action.call_count, 3)

    def test_put1_residual_never_enables_correction(self):
        machine, clock = self.machine([pair(.3), pair(.06)])
        with self.assertRaises(ValueError):
            self.navigate(machine, clock, 'put1')
        machine.action.assert_called_once()
        machine.health.assert_not_called()

    def test_get1_residual_outside_entry_limits_never_corrects(self):
        for distance, yaw in ((.05001, 0), (0, 5.001)):
            with self.subTest(distance=distance, yaw=yaw):
                machine, clock = self.machine([pair(.3), pair(distance, yaw)])
                with self.assertRaises((ValueError, RuntimeError)):
                    self.navigate(machine, clock)
                machine.action.assert_called_once()

    def test_entry_envelope_boundaries_allow_one_bounded_attempt(self):
        machine, clock = self.machine([pair(.3), pair(.05, 5), pair(.05, 5), pair(.005, 1)])
        self.navigate(machine, clock)
        self.assertEqual(machine.action.call_count, 2)
        self.assert_correction_goal(machine.action.call_args_list[1], 1)

    def test_invalid_post_navigation_telemetry_is_not_a_correctable_residual(self):
        for key, value in (('frame', 'odom'), ('stamp_ns', 90_000_000_000), ('x', float('nan'))):
            samples = pair(.03)
            samples[1][key] = value
            with self.subTest(key=key):
                machine, clock = self.machine([pair(.3), samples])
                with self.assertRaises(ValueError):
                    self.navigate(machine, clock)
                machine.action.assert_called_once()
                machine.health.assert_not_called()

    def test_unstable_correction_entry_pair_never_dispatches(self):
        for distance, yaw in ((.006, 0), (0, 1.01)):
            entry = pair(.03)
            entry[1]['x'] += distance
            entry[1]['yaw'] += math.radians(yaw)
            with self.subTest(distance=distance, yaw=yaw):
                machine, clock = self.machine([pair(.3), pair(.03), entry])
                with self.assertRaises((ValueError, RuntimeError)):
                    self.navigate(machine, clock)
                machine.action.assert_called_once()

    def test_initial_action_failure_does_not_retry_or_read_arrival(self):
        machine, clock = self.machine([pair(.3)])
        machine.action.return_value = dict(event='result', status=6, result={})
        with self.assertRaises((ValueError, RuntimeError)):
            self.navigate(machine, clock)
        machine.action.assert_called_once()
        machine.health.assert_not_called()
        self.assertEqual(machine.health_request.call_count, 1)

    def test_map_state_or_waypoint_change_blocks_correction(self):
        for kind in ('state', 'points', 'mutated_coordinates'):
            machine, clock = self.machine([pair(.3), pair(.03)])
            if kind == 'state':
                machine.map_state.side_effect = [('utars_nav_map', 'FSM_WAITNAVIGATE'),
                                                 ('other_map', 'FSM_WAITNAVIGATE')]
            elif kind == 'points':
                machine.map_points.side_effect = [machine.points, RuntimeError('MAP_POINTS_CHANGED')]
            else:
                def mutate_target():
                    if machine.map_points.call_count > 1:
                        machine.points['get1']['_expected_pose']['point_x'] += .02
                    return machine.points
                machine.map_points.side_effect = mutate_target
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                self.navigate(machine, clock)
            machine.action.assert_called_once()

    def test_correction_guard_or_action_failure_is_never_retried(self):
        for failure in (RuntimeError('correction guard lost telemetry'),
                        dict(event='result', status=6, result={})):
            machine, clock = self.machine([pair(.3), pair(.03), pair(.03)])
            machine.action.side_effect = [copy.deepcopy(SUCCESS), failure]
            with self.subTest(failure=repr(failure)), self.assertRaises((ValueError, RuntimeError)):
                self.navigate(machine, clock)
            self.assertEqual(machine.action.call_count, 2)

    def test_total_budget_expiration_blocks_correction_dispatch(self):
        machine, clock = self.machine([pair(.3), pair(.03), pair(.03)])
        machine.health.side_effect = lambda **kwargs: clock.update(monotonic=clock['monotonic']+71)
        with self.assertRaises((ValueError, RuntimeError)):
            self.navigate(machine, clock)
        machine.action.assert_called_once()

    def test_successful_get1_correction_finishes_navigation_only_checkpoint(self):
        machine, clock = self.machine([pair(.3), pair(.03), pair(.03), pair(.005)])
        machine.armed = True
        machine.connected = Mock()
        with tempfile.TemporaryDirectory() as directory:
            machine.session = Path(directory)
            with patch.object(runtime.time, 'time', side_effect=lambda: clock['wall']), \
                    patch.object(runtime.time, 'monotonic', side_effect=lambda: clock['monotonic']):
                machine.stage({'stage': 'navigate_get1'})
                self.assertEqual(machine.checkpoint['completed'], ['navigate_get1'])
                self.assertEqual(machine.checkpoint['box_state'], 'empty')
                self.assertIsNone(contract.next_stage(machine.checkpoint))
                with self.assertRaises(ValueError):
                    machine.stage({'stage': 'enable_vision'})
        self.assertEqual(machine.action.call_count, 2)
        self.assertTrue(all(call.args[0] == 'navigation' for call in machine.action.call_args_list))

    def test_correction_guard_failure_persists_failed_checkpoint_and_blocks_following_stages(self):
        machine, clock = self.machine([pair(.3), pair(.03), pair(.03)])
        machine.checkpoint = contract.new_checkpoint(PROFILE, policy='assume')
        machine.armed = True
        machine.connected = Mock()
        correction_records = []

        def action(kind, goal, timeout, **kwargs):
            if 'correction' in kwargs:
                record = json.loads((machine.session/'get1-correction.json').read_text())
                self.assertEqual(record['phase'], 'in_flight')
                self.assertEqual(record['spec'], kwargs['correction'])
                correction_records.append(record)
                raise RuntimeError('correction guard lost telemetry; cancellation unconfirmed')
            return copy.deepcopy(SUCCESS)

        machine.action.side_effect = action
        with patch.object(runtime.time, 'time', side_effect=lambda: clock['wall']), \
                patch.object(runtime.time, 'monotonic', side_effect=lambda: clock['monotonic']):
            with self.assertRaisesRegex(RuntimeError, 'guard lost telemetry'):
                machine.stage({'stage': 'navigate_get1'})
            stored = json.loads((machine.session/'checkpoint.json').read_text())
            self.assertEqual(stored['completed'], [])
            self.assertEqual(stored['failure']['stage'], 'navigate_get1')
            self.assertEqual(stored['box_state'], 'unknown')
            self.assertIsNone(stored['in_flight'])
            for stage in ('navigate_get1', 'enable_vision', 'grasp'):
                with self.subTest(stage=stage), self.assertRaises(ValueError):
                    machine.stage({'stage': stage})
        self.assertEqual(len(correction_records), 1)
        self.assertEqual(machine.action.call_count, 2)
        self.assertNotIn('stage_complete', [call.args[0] for call in machine.emit.call_args_list])

    def test_full_cycle_can_enable_vision_only_after_two_corrected_arrival_samples(self):
        for second_sample_valid in (True, False):
            arrived = pair(.005)
            if not second_sample_valid:
                arrived[1]['frame'] = 'odom'
            machine, clock = self.machine([pair(.3), pair(.03), pair(.03), arrived])
            machine.checkpoint = contract.new_checkpoint(PROFILE, policy='assume')
            machine.armed = True
            machine.connected = Mock()
            with self.subTest(second_sample_valid=second_sample_valid), \
                    patch.object(runtime.time, 'time', side_effect=lambda: clock['wall']), \
                    patch.object(runtime.time, 'monotonic', side_effect=lambda: clock['monotonic']):
                if second_sample_valid:
                    machine.stage({'stage': 'navigate_get1'})
                    self.assertEqual(sum(call.args[0] == 'arrival' for call in machine.emit.call_args_list), 2)
                    machine.stage({'stage': 'enable_vision'})
                    self.assertEqual(machine.checkpoint['completed'], ['navigate_get1', 'enable_vision'])
                    self.assertEqual(machine.action.call_count, 3)
                    kind, goal, _ = machine.action.call_args.args
                    self.assertEqual(kind, 'motion')
                    self.assertEqual(goal['task_name'], 'vision/enable_transport_vision_switch')
                else:
                    with self.assertRaises(ValueError):
                        machine.stage({'stage': 'navigate_get1'})
                    self.assertNotIn('arrival', [call.args[0] for call in machine.emit.call_args_list])
                    with self.assertRaises(ValueError):
                        machine.stage({'stage': 'enable_vision'})
                    self.assertEqual(machine.checkpoint['completed'], [])
                    self.assertEqual(machine.action.call_count, 2)

class DisabledCorrectionTests(unittest.TestCase):
    """The production permission remains revocable without bypassing its gates."""
    machine = NavigationCorrectionTests.machine
    navigate = NavigationCorrectionTests.navigate

    def setUp(self):
        report = dict(runtime.nav_correction.qualification_report(), motion_enabled=False,
                      status='blocked', reason_code='GET1_CORRECTION_UNQUALIFIED',
                      reason='synthetic revoked permission')
        disabled = patch.object(runtime.nav_correction, 'qualification_report', return_value=report)
        disabled.start()
        self.addCleanup(disabled.stop)

    def test_disabled_report_keeps_real_permission_gate_blocking(self):
        report = runtime.nav_correction.qualification_report()
        self.assertIs(report['motion_enabled'], False)
        self.assertEqual(report['status'], 'blocked')
        with self.assertRaisesRegex(RuntimeError, 'GET1_CORRECTION_UNQUALIFIED'):
            runtime.nav_correction.require_motion_qualified()

    def test_residual_never_sends_second_goal_or_writes_correction_intent(self):
        machine, clock = self.machine([pair(.3), pair(.03), pair(.03)])
        with self.assertRaisesRegex(RuntimeError, 'GET1_CORRECTION_UNQUALIFIED'):
            self.navigate(machine, clock)
        machine.action.assert_called_once()
        self.assertEqual(machine.action.call_args.args[0], 'navigation')
        self.assertEqual(machine.action.call_args.kwargs, {})
        machine.health.assert_called_once_with(require_home=True)
        self.assertEqual(machine.health_request.call_count, 3)
        self.assertFalse((machine.session/'get1-correction.json').exists())

    def test_qualification_failure_is_durable_and_blocks_vision_and_grasp(self):
        machine, clock = self.machine([pair(.3), pair(.03), pair(.03)])
        machine.checkpoint = contract.new_checkpoint(PROFILE, policy='assume')
        machine.armed = True
        machine.connected = Mock()
        with patch.object(runtime.time, 'time', side_effect=lambda: clock['wall']), \
                patch.object(runtime.time, 'monotonic', side_effect=lambda: clock['monotonic']), \
                patch.object(runtime.subprocess, 'run', side_effect=AssertionError('No subprocesses')), \
                patch.object(runtime.subprocess, 'Popen', side_effect=AssertionError('No subprocesses')):
            with self.assertRaisesRegex(RuntimeError, 'GET1_CORRECTION_UNQUALIFIED'):
                machine.stage({'stage': 'navigate_get1'})
            for next_stage in ('navigate_get1', 'enable_vision', 'grasp'):
                with self.subTest(next_stage=next_stage), self.assertRaises(ValueError):
                    machine.stage({'stage': next_stage})
        stored = json.loads((machine.session/'checkpoint.json').read_text())
        self.assertEqual(stored, machine.checkpoint)
        self.assertEqual(stored['completed'], [])
        self.assertEqual(stored['failure']['stage'], 'navigate_get1')
        self.assertIn('GET1_CORRECTION_UNQUALIFIED', stored['failure']['reason'])
        self.assertIsNone(stored['in_flight'])
        self.assertEqual(stored['box_state'], 'unknown')
        machine.action.assert_called_once()
        self.assertFalse((machine.session/'get1-correction.json').exists())
        self.assertFalse(any(call.args[0] == 'stage_complete' for call in machine.emit.call_args_list))

    def test_normal_or_freshly_settled_arrival_still_needs_no_correction(self):
        for readings, expected_reads in (([pair(.3), pair(.005)], 2),
                                         ([pair(.3), pair(.03), pair(.005)], 3)):
            with self.subTest(expected_reads=expected_reads):
                machine, clock = self.machine(readings)
                self.navigate(machine, clock)
                machine.action.assert_called_once()
                self.assertEqual(machine.health_request.call_count, expected_reads)
                self.assertEqual(sum(call.args[0] == 'arrival' for call in machine.emit.call_args_list), 2)
                self.assertFalse((machine.session/'get1-correction.json').exists())

    def test_runtime_action_blocks_before_creating_or_using_native_session(self):
        machine, _ = self.machine([])
        target = dict(EXPECTED, map_name='utars_nav_map', mode='free_nav')
        goal = {'command': 'navigation_start', 'arg_json': json.dumps({'target_point': target})}
        spec = runtime.nav_correction.make_spec(EXPECTED,
            {'x': 1.03, 'y': 2., 'yaw': 0., 'stamp_ns': 100_000_000_000}, 1)
        for session_exists in (False, True):
            worker = Mock()
            machine.action_sessions = {'navigation': worker} if session_exists else {}
            with self.subTest(session_exists=session_exists), \
                    patch.object(runtime, 'ProcessSession', side_effect=AssertionError('No session creation')) as process, \
                    patch.object(runtime.subprocess, 'Popen', side_effect=AssertionError('No processes')), \
                    self.assertRaisesRegex(RuntimeError, 'GET1_CORRECTION_UNQUALIFIED'):
                runtime.Runtime.action(machine, 'navigation', goal, 15, correction=spec)
            process.assert_not_called()
            worker.call.assert_not_called()


if __name__ == '__main__':
    unittest.main()
