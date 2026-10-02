"""Visual correction regressions: synthetic telemetry, no ROS/network/robot."""
import copy
import json
import math
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import scenario1_box_alignment as alignment
from scripts.box_handling import scenario1_cli as cli
from scripts.box_handling import scenario1_contract as contract
from scripts.box_handling import scenario1_nav_correction as nav
from scripts.box_handling import scenario1_runtime as runtime
from scripts.box_handling import front_sps_contract as sps
from scripts.box_handling.scenario1_console import ConsoleReporter
from scripts.box_handling.test_front_sps import report
from scripts.box_handling.test_scenario1_perception import selection
from scripts.box_handling.test_scenario1_runtime import PROFILE

SUCCESS = dict(event='result', status=4, result=dict(state=dict(desc='SUCCEED', state=1101001),
                                                   dmsg='navigation_start SUCCEEDED'))


def posture(position=0., head=-.43):
    from scripts.lib.cruzr_home_posture_gate import BODY_ACTUATOR_ALIASES
    return dict(actuator=[dict(act_item=[dict(id=aliases[0], position=head if aliases[0] == 1002 else position)
                                        for _, aliases in BODY_ACTUATOR_ALIASES])]*2)


class AlignmentPlanTests(unittest.TestCase):
    def test_map_samples_near_image_are_used_despite_processing_delay(self):
        history = [dict(x=1., y=2., yaw=0., stamp_ns=stamp) for stamp in
                   (99_900_000_000, 100_100_000_000, 101_400_000_000, 101_500_000_000)]
        result = alignment.match_pose_time(selection(stamp=100_000_000_000), history)
        self.assertEqual(result['max_delta_ns'], 100_000_000)
        self.assertEqual([row['stamp_ns'] for row in result['poses']], [99_900_000_000, 100_100_000_000])
        self.assertGreater(history[-1]['stamp_ns']-result['image_stamp_ns'], 500_000_000)

    def test_time_pairing_still_rejects_missing_far_and_nonadvancing_samples(self):
        pending = selection(stamp=100_000_000_000)
        ref = dict(x=1., y=2., yaw=0.)
        for stamps in ([], [100_000_000_000], [98_000_000_000, 98_100_000_000],
                       [99_499_999_999, 100_500_000_001], [100_000_000_000]*2,
                       [100_100_000_000, 100_000_000_000]):
            with self.subTest(stamps=stamps), self.assertRaises(ValueError):
                alignment.match_pose_time(pending, [dict(ref, stamp_ns=s) for s in stamps])
        result = alignment.match_pose_time(pending, [dict(ref, stamp_ns=s) for s in
                                                    (99_500_000_000, 100_500_000_000)])
        self.assertEqual(result['max_delta_ns'], 500_000_000)

    def test_intermediate_departure_cannot_pass_by_returning_to_initial_pose(self):
        history = [dict(x=x, y=2., yaw=0., stamp_ns=stamp) for x, stamp in
                   ((1., 99_900_000_000), (1.006, 100_000_000_000), (1., 100_100_000_000))]
        with self.assertRaisesRegex(ValueError, 'BASE_UNSTABLE'):
            alignment.match_pose_time(selection(stamp=100_000_000_000), history)

    def test_exact_archived_incident_replay_without_using_it_as_current_pose(self):
        fixture = json.loads((Path(__file__).parent/'fixtures/box_alignment_20261002.json').read_text())
        pending = selection(**fixture['position_base_link_m'])
        delta = alignment.displacement(pending)
        self.assertEqual(delta, fixture['expected_displacement_base_m'])
        self.assertEqual(alignment.target(fixture['reference_map'], delta), fixture['expected_target_map'])
        self.assertTrue(fixture['historical_not_current'])

    def test_user_example_preserves_measurement_and_adds_inside_margin(self):
        pending = selection(x=.7909, y=.0994, z=.3112)
        original = copy.deepcopy(pending)
        delta = alignment.displacement(pending)
        self.assertAlmostEqual(delta['x'], .0209)
        self.assertEqual(delta['y'], 0.)
        self.assertEqual(pending, original)
        with self.assertRaisesRegex(ValueError, 'BOX_POSITION_REJECTED'):
            sps.validate_position(pending['selection']['selected_pose'])

    def test_each_violated_axis_and_both_signs(self):
        for x, y, expected in ((.405, 0, dict(x=-.025, y=0.)),
                                (.8, 0, dict(x=.03, y=0.)),
                                (.6, -.395, dict(x=0., y=-.025)),
                                (.6, .395, dict(x=0., y=.025)),
                                (.8, .395, dict(x=.03, y=.025))):
            with self.subTest(x=x, y=y):
                delta = alignment.displacement(selection(x=x, y=y))
                for axis in 'xy':
                    self.assertAlmostEqual(delta[axis], expected[axis])

    def test_exact_limits_and_in_range_never_request_motion(self):
        for x in (.41, .6, .79):
            for y in (-.39, 0, .39):
                self.assertEqual(alignment.displacement(selection(x=x, y=y)), dict(x=0., y=0.))

    def test_z_and_large_correction_are_not_recoverable(self):
        for pending in (selection(z=0), selection(z=1.5), selection(x=.821),
                        selection(x=.82, y=.395)):
            with self.subTest(pending=pending), self.assertRaises(ValueError):
                alignment.displacement(pending)

    def test_base_displacement_rotates_into_map_preserving_yaw(self):
        ref = dict(x=1., y=2., yaw=math.pi/2, stamp_ns=100)
        goal = alignment.target(ref, dict(x=.02, y=-.01))
        self.assertAlmostEqual(goal['point_x'], 1.01)
        self.assertAlmostEqual(goal['point_y'], 2.02)
        self.assertEqual(goal['point_yaw'], ref['yaw'])

    def test_world_geometry_stays_same_after_chassis_move(self):
        before = selection(x=.7909)
        after = selection(stamp=200, x=.77)
        first = alignment.in_map(before, dict(x=1., y=2., yaw=0.))
        last = alignment.in_map(after, dict(x=1.0209, y=2., yaw=0.))
        result = runtime.perception.validate_pair(first, last)
        self.assertAlmostEqual(result['translation_m'], 0.)

    def test_observation_uses_exact_tf_and_selector_without_native_delivery(self):
        raw = report()
        raw['vision_result']['trans_outputs']['box_pose']['poses'][1]['position']['x'] = .5909
        original = copy.deepcopy(raw)
        pending = alignment.observe(raw, 100_100_000_000)
        self.assertAlmostEqual(pending['selection']['selected_pose']['position']['x'], .7909)
        self.assertFalse(pending['selection']['motion_authorized'])
        self.assertEqual(raw, original)
        with self.assertRaises(ValueError):
            sps.select_report(raw, 100_100_000_000)
        for mutate in (lambda r: r['tf_at_detection']['header']['stamp'].update(sec=99),
                       lambda r: r.update(status=6),
                       lambda r: r['tf_at_detection'].update(child_frame_id='other')):
            invalid = copy.deepcopy(raw); mutate(invalid)
            with self.assertRaises(ValueError):
                alignment.observe(invalid, 100_100_000_000)
        with self.assertRaises(ValueError):
            alignment.observe(raw, 103_000_000_000)

    def test_posture_requires_body_home_before_prep_and_head_pose_after(self):
        alignment.pickup_posture(posture(head=0), observation=False)
        alignment.pickup_posture(posture())
        for invalid in (posture(position=.03), posture(head=0)):
            with self.assertRaises(ValueError):
                alignment.pickup_posture(invalid)

    def test_new_guard_is_tighter_without_changing_get1_policy(self):
        ref = dict(x=1., y=2., yaw=0., stamp_ns=100_000_000_000)
        target = dict(point_x=1.03, point_y=2., point_yaw=0.)
        spec = nav.make_spec(target, ref, 1, point='box_pickup')
        self.assertEqual(nav.Guard(spec, 100_100_000_000).distance_tolerance_m, .005)
        self.assertEqual(nav.Guard(nav.make_spec(target, ref, 1), 100_100_000_000).distance_tolerance_m, .02)
        for invalid in (dict(spec, point='anything'), dict(spec, attempt=3)):
            with self.assertRaises(ValueError): nav.validate_spec(invalid)

    def test_archived_terminal_poses_allow_recapture_with_original_turn_window(self):
        fixture=json.loads((Path(__file__).parent/'fixtures/box_alignment_arrival_20261002.json').read_text())
        measurements=alignment.validate_arrival(fixture['post_navigation_references'],fixture['target_map'])
        self.assertAlmostEqual(measurements[0]['distance_m'],.00962952172244532)
        self.assertAlmostEqual(measurements[1]['yaw_error_deg'],.4521746747502925)
        self.assertTrue(fixture['settled'])
        self.assertTrue(fixture['historical_not_current'])
        spec=nav.make_spec(fixture['target_map'],fixture['reference_map'],1,point='box_pickup')
        self.assertEqual(nav.distance_tolerance(spec),.005)
        self.assertEqual(measurements[0]['distance_tolerance_m'],.012)

    def test_terminal_pose_distance_yaw_bounds_are_inclusive_and_not_configurable(self):
        expected=dict(point_x=0.,point_y=0.,point_yaw=0.)
        refs=[dict(x=.012,y=0.,yaw=math.radians(2.))]*2
        alignment.validate_arrival(refs,expected)
        for x,yaw in ((.012000001,0.),(0.,math.radians(2.000001))):
            with self.subTest(x=x,yaw=yaw), self.assertRaisesRegex(ValueError,'ARRIVAL_NOT_CONFIRMED'):
                alignment.validate_arrival([dict(x=x,y=0.,yaw=yaw)]*2,expected)
        with self.assertRaises(TypeError):
            alignment.POLICY['max_arrival_distance_m']=1.

    def test_terminal_pose_checks_count_finiteness_and_stability(self):
        expected=dict(point_x=0.,point_y=0.,point_yaw=0.)
        valid=dict(x=0.,y=0.,yaw=0.)
        for invalid in ([],[valid],[valid]*3,[dict(valid,x=float('nan'))]*2,
                        [dict(valid,y=True)]*2):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                alignment.validate_arrival(invalid,expected)
        with self.assertRaisesRegex(ValueError,'BASE_UNSTABLE'):
            alignment.validate_arrival([dict(valid,x=-.004),dict(valid,x=.004)],expected)

    def test_terminal_pose_yaw_wrap_uses_shortest_difference(self):
        rows=[dict(x=0.,y=0.,yaw=-math.pi+math.radians(.1))]*2
        result=alignment.validate_arrival(rows,dict(point_x=0.,point_y=0.,point_yaw=math.pi))
        self.assertAlmostEqual(result[0]['yaw_error_deg'],.1)


class AlignmentRuntimeTests(unittest.TestCase):
    def machine(self, observations):
        directory = tempfile.TemporaryDirectory(); self.addCleanup(directory.cleanup)
        checkpoint = contract.new_checkpoint(PROFILE, policy='assume', execution_profile='optimistic_v1')
        machine = runtime.Runtime(dict(checkpoint=checkpoint, execution_profile='optimistic_v1'), emit=Mock())
        machine.checkpoint = contract.complete_stage(contract.begin_stage(machine.checkpoint, 'navigate_get1'),
                                                    'navigate_get1')
        machine.checkpoint = contract.complete_stage(contract.begin_stage(machine.checkpoint, 'enable_vision'),
                                                    'enable_vision')
        machine.session = Path(directory.name)
        machine.connected = Mock()
        machine.discover = Mock(); machine.hashes = Mock(); machine.quick_health = Mock()
        machine.health = Mock(return_value=posture())
        machine.check_box_alignment_head = Mock()
        machine.action = Mock(return_value=copy.deepcopy(SUCCESS))
        machine.armed = True
        machine.live_monitor_enabled = True
        machine.measure_box_for_pickup = Mock(side_effect=observations)
        machine.pose_references = Mock(return_value=[dict(x=1.0209, y=2., yaw=0.),
                                                   dict(x=1.0209, y=2., yaw=0.)])
        return machine

    def observation(self, x=.7909, stamp=100, base_x=1., y=.1, z=.3112):
        return selection(x=x, y=y, z=z, stamp=stamp), dict(x=base_x, y=2., yaw=0., stamp_ns=stamp)

    def test_in_range_only_prepares_head_and_never_navigates(self):
        machine = self.machine([self.observation(x=.77)])
        machine.align_box_for_pickup()
        machine.action.assert_called_once()
        self.assertEqual(machine.action.call_args.args[1]['task_name'], 'cruzr/move_head_lower')
        self.assertTrue((machine.session/'box-alignment-reference.json').exists())

    def test_rejected_box_corrects_before_one_native_grasp_and_checkpoints_once(self):
        machine = self.machine([self.observation(), self.observation(x=.77, stamp=200, base_x=1.0209)])
        machine.stage(dict(stage='grasp'))
        calls = machine.action.call_args_list
        self.assertEqual(len(calls), 3)
        self.assertEqual([call.args[0] for call in calls], ['motion', 'navigation', 'motion'])
        self.assertEqual(calls[2].args[1]['task_name'], 'local_front_box/separate_right_cruzr')
        spec = calls[1].kwargs['correction']
        self.assertEqual(spec['point'], 'box_pickup')
        self.assertAlmostEqual(spec['target']['point_x'], 1.0209)
        self.assertEqual(spec['target']['point_y'], 2.)
        self.assertEqual(machine.checkpoint['completed'], ['navigate_get1', 'enable_vision', 'grasp'])
        self.assertEqual(machine.checkpoint['box_state'], 'unknown')
        self.assertEqual(json.loads((machine.session/'box-alignment.json').read_text())['phase'], 'measured')

    def test_native_failure_never_retries_or_navigates_after_it(self):
        machine = self.machine([self.observation(), self.observation(x=.77, stamp=200, base_x=1.0209)])
        machine.action.side_effect = [SUCCESS, SUCCESS, RuntimeError('WORKER_REQUEST_FAILED')]
        with self.assertRaisesRegex(RuntimeError, 'WORKER_REQUEST_FAILED'):
            machine.stage(dict(stage='grasp'))
        self.assertEqual(machine.action.call_count, 3)
        self.assertEqual(machine.checkpoint['failure']['stage'], 'grasp')
        self.assertEqual(machine.checkpoint['box_state'], 'unknown')

    def test_nav_failure_no_arrival_capture_or_grasp_retry(self):
        machine = self.machine([self.observation()])
        machine.action.side_effect = [SUCCESS, RuntimeError('guard failed')]
        with self.assertRaisesRegex(RuntimeError, 'guard failed'):
            machine.stage(dict(stage='grasp'))
        self.assertEqual(machine.action.call_count, 2)
        machine.measure_box_for_pickup.assert_called_once()
        machine.pose_references.assert_not_called()
        self.assertFalse((machine.session/'box-alignment-reference.json').exists())

    def test_wrong_arrival_blocks_recapture_and_pickup(self):
        machine = self.machine([self.observation()])
        for row in machine.pose_references.return_value:
            row['x'] += .013
        with self.assertRaisesRegex(ValueError, 'ARRIVAL_NOT_CONFIRMED'):
            machine.align_box_for_pickup()
        self.assertEqual(machine.action.call_count, 2)
        machine.measure_box_for_pickup.assert_called_once()

    def test_native_terminal_residual_recaptures_box_before_native_grasp(self):
        machine=self.machine([self.observation(),self.observation(x=.77,stamp=200,base_x=1.0309)])
        machine.pose_references.return_value=[dict(x=1.0309,y=2.,yaw=0.)]*2
        machine.stage(dict(stage='grasp'))
        self.assertEqual(machine.measure_box_for_pickup.call_count,2)
        self.assertEqual(machine.action.call_count,3) # head, navigation, native grasp
        self.assertEqual(machine.checkpoint['completed'][-1],'grasp')
        self.assertEqual(json.loads((machine.session/'box-alignment-reference.json').read_text())['stamp_ns'],200)

    def test_native_terminal_residual_with_box_still_outside_uses_second_visual_goal(self):
        machine=self.machine([self.observation(x=.795),
            self.observation(x=.7922,stamp=200,base_x=1.015),
            self.observation(x=.77,stamp=300,base_x=1.0372)])
        machine.pose_references.side_effect=[[dict(x=1.015,y=2.,yaw=0.)]*2,
                                            [dict(x=1.0372,y=2.,yaw=0.)]*2]
        machine.align_box_for_pickup()
        self.assertEqual(machine.action.call_count,3)
        requests=machine.action.call_args_list[1:]
        self.assertEqual([call.kwargs['correction']['attempt'] for call in requests],[1,2])
        self.assertAlmostEqual(requests[1].kwargs['correction']['target']['point_x'],1.0372)
        record=json.loads((machine.session/'box-alignment.json').read_text())
        self.assertAlmostEqual(record['total_requested_m'],.0472)

    def test_native_terminal_residual_never_forgives_visual_or_yaw_failure(self):
        for failure in ('yaw','identity','no_improvement'):
            after=self.observation(x=.77,stamp=200,base_x=1.0309)
            if failure=='identity':after=self.observation(x=.73,stamp=200,base_x=1.0309)
            if failure=='no_improvement':after=self.observation(x=.7908,stamp=200,base_x=1.0309)
            machine=self.machine([self.observation(),after])
            machine.pose_references.return_value=[dict(x=1.0309,y=2.,yaw=math.radians(2.001) if failure=='yaw' else 0.)]*2
            with self.subTest(failure=failure), self.assertRaises((ValueError,RuntimeError)):
                machine.stage(dict(stage='grasp'))
            self.assertEqual(machine.action.call_count,2)
            self.assertFalse((machine.session/'box-alignment-reference.json').exists())

    def test_unrecoverable_detection_never_dispatches_nav_or_grasp(self):
        for observation in (self.observation(x=.9), self.observation(z=0)):
            machine = self.machine([observation])
            with self.subTest(observation=observation), self.assertRaises(ValueError):
                machine.stage(dict(stage='grasp'))
            machine.action.assert_called_once()  # only head
            self.assertEqual(machine.checkpoint['box_state'], 'unknown')

    def test_changed_box_and_no_progress_stop_before_second_nav(self):
        for after in (self.observation(x=.7908, stamp=200, base_x=1.0209),
                      self.observation(x=.77, y=.13, stamp=200, base_x=1.0209)):
            machine = self.machine([self.observation(), after])
            with self.subTest(after=after), self.assertRaises((ValueError, RuntimeError)):
                machine.align_box_for_pickup()
            self.assertEqual(machine.action.call_count, 2)
            self.assertFalse((machine.session/'box-alignment-reference.json').exists())

    def test_health_posture_failure_before_head_dispatch(self):
        machine = self.machine([])
        for failure in (RuntimeError('health failure'), posture(position=.03)):
            machine.health.side_effect = failure if isinstance(failure, Exception) else None
            machine.health.return_value = failure
            with self.assertRaises((ValueError, RuntimeError)):
                machine.align_box_for_pickup()
        machine.action.assert_not_called()

    def test_second_adjustment_has_a_finite_budget_and_no_third(self):
        machine = self.machine([self.observation(x=.80),
            self.observation(x=.797, stamp=200, base_x=1.003)])
        machine.pose_references.return_value = [dict(x=1.03, y=2., yaw=0.)]*2
        with self.assertRaisesRegex(RuntimeError, 'BOX_ALIGNMENT_LIMIT'):
            machine.align_box_for_pickup()
        self.assertEqual(machine.action.call_count, 2)

    def test_second_measurement_can_trigger_one_more_bounded_adjustment(self):
        machine = self.machine([self.observation(x=.795),
            self.observation(x=.792, stamp=200, base_x=1.02),
            self.observation(x=.77, stamp=300, base_x=1.042)])
        machine.pose_references.side_effect = [[dict(x=1.025, y=2., yaw=0.)]*2,
                                               [dict(x=1.042, y=2., yaw=0.)]*2]
        machine.align_box_for_pickup()
        self.assertEqual(machine.action.call_count, 3)  # head and two navigation goals
        self.assertEqual([c.kwargs['correction']['attempt'] for c in machine.action.call_args_list[1:]], [1, 2])
        reference = json.loads((machine.session/'box-alignment-reference.json').read_text())
        self.assertEqual(reference['stamp_ns'], 300)

    def test_measurement_checks_health_base_map_freshness_and_pair(self):
        before = [dict(x=1., y=2., yaw=0., stamp_ns=s) for s in (99_000_000_000, 99_100_000_000)]
        after = [dict(x=1., y=2., yaw=0., stamp_ns=s) for s in (100_200_000_000, 100_300_000_000)]
        for failure in ('none', 'map', 'posture', 'base', 'time', 'unstable', 'box_pair', 'stale'):
            machine = self.machine([])
            machine.map_state = Mock(return_value=('utars_nav_map', 'FSM_WAITNAVIGATE'))
            machine.map_points = Mock()
            machine.stationary_base = Mock()
            first = self.observation(stamp=100_000_000_000)[0]
            second = self.observation(stamp=100_100_000_000)[0]
            observations = iter([first, second])
            def capture_with_poses(history, phase):
                pending = next(observations)
                if failure != 'time':
                    history.append(dict(x=1., y=2., yaw=0., stamp_ns=pending['stamp_ns']))
                return pending
            machine.capture_box_with_poses = Mock(side_effect=capture_with_poses)
            readings = copy.deepcopy([before, after])
            machine.pose_references.side_effect = readings
            if failure == 'map': machine.map_state.return_value = ('other_map', 'FSM_WAITNAVIGATE')
            if failure == 'posture': machine.health.return_value = posture(position=.03)
            if failure == 'base': machine.stationary_base.side_effect = ValueError('base moving')
            if failure == 'time':
                for r in readings[1]: r['stamp_ns'] += 1_000_000_000
            if failure == 'unstable': readings[1][1]['x'] += .006
            if failure == 'box_pair': second['selection']['selected_pose']['position']['x'] += .03
            with self.subTest(failure=failure), patch.object(runtime.time, 'time_ns',
                    return_value=103_000_000_000 if failure == 'stale' else 100_400_000_000):
                if failure == 'none':
                    result = runtime.Runtime.measure_box_for_pickup(machine)
                    self.assertEqual(result, (second, after[-1]))
                    self.assertEqual(machine.stationary_base.call_count, 2)
                else:
                    with self.assertRaises((ValueError, RuntimeError)):
                        runtime.Runtime.measure_box_for_pickup(machine)
                machine.action.assert_not_called()

    def test_capture_and_pose_reading_overlap_with_one_health_request_caller(self):
        machine = self.machine([])
        acquired = threading.Event()
        expected = self.observation(stamp=100_000_000_000)[0]
        main_ident = threading.get_ident()
        def capture():
            self.assertNotEqual(threading.get_ident(), main_ident)
            if not acquired.wait(1): raise AssertionError('Pose reads must overlap capture')
            return expected
        count = [0]
        def poses():
            self.assertEqual(threading.get_ident(), main_ident)
            count[0] += 1
            acquired.set()
            return [dict(x=1., y=2., yaw=0., stamp_ns=100_000_000_000+count[0]*10+offset)
                    for offset in (1, 2)]
        machine.capture_box = Mock(side_effect=capture)
        machine.pose_references = Mock(side_effect=poses)
        history = [dict(x=1., y=2., yaw=0., stamp_ns=99_900_000_000)]
        # Yield to the capture thread deterministically through the pose reader.
        import time
        original = machine.pose_references.side_effect
        def paced_poses():
            result = original(); time.sleep(.001); return result
        machine.pose_references.side_effect = paced_poses
        self.assertEqual(machine.capture_box_with_poses(history, 'first'), expected)
        self.assertTrue(acquired.is_set())
        machine.capture_box.assert_called_once()
        self.assertGreater(len(history), 1)

    def test_stationary_gate_uses_persistent_reader_without_native_process_start(self):
        machine = self.machine([])
        machine.native = Mock(side_effect=AssertionError('No new native process'))
        machine.health_request = Mock(return_value=dict(event='base_result',stationary=True,publishers=1))
        machine.stationary_base()
        machine.health_request.assert_called_once_with('base', timeout=5)
        machine.native.assert_not_called()
        for invalid in (dict(event='base_result',stationary=False,publishers=1),
                        dict(event='base_result',stationary=True,publishers=2),
                        dict(event='base_result',stationary=True,publishers=True),
                        dict(event='resume_base_check',stationary=True,publishers=1)):
            machine.health_request.return_value=invalid
            with self.assertRaisesRegex(RuntimeError, 'BASE_NOT_STATIONARY'):
                machine.stationary_base()

    def test_post_capture_stationary_read_preserves_freshness_without_raising_age_limit(self):
        for latency_ns in (50_000_000, 910_000_000):
            machine=self.machine([])
            machine.map_state=Mock(return_value=('utars_nav_map','FSM_WAITNAVIGATE'))
            machine.map_points=Mock()
            clock=[100_000_000_000]
            first=self.observation(stamp=101_000_000_000)[0]
            second=self.observation(stamp=103_000_000_000)[0]
            def capture(history,phase):
                pending=first if phase=='first' else second
                history.extend(dict(x=1.,y=2.,yaw=0.,stamp_ns=pending['stamp_ns']+n) for n in (0,1))
                clock[0]=pending['stamp_ns']+1_140_000_000
                return pending
            machine.capture_box_with_poses=Mock(side_effect=capture)
            reads=[0]
            def poses():
                reads[0]+=1
                if reads[0]>1: clock[0]+=180_000_000
                return [dict(x=1.,y=2.,yaw=0.,stamp_ns=clock[0]+n) for n in (1,2)]
            machine.pose_references=Mock(side_effect=poses)
            def base(*args,**kwargs):
                clock[0]+=latency_ns
                return dict(event='base_result',stationary=True,publishers=1)
            machine.health_request=Mock(side_effect=base)
            with self.subTest(latency_ns=latency_ns), patch.object(runtime.time,'time_ns',side_effect=lambda:clock[0]):
                if latency_ns==50_000_000:
                    pending,_=runtime.Runtime.measure_box_for_pickup(machine)
                    self.assertIs(pending,second)
                else:
                    with self.assertRaisesRegex(RuntimeError,'DETECTION_STALE_BEFORE_DISPATCH'):
                        runtime.Runtime.measure_box_for_pickup(machine)
            self.assertEqual(machine.health_request.call_count,2)
            machine.action.assert_not_called()

    def test_capture_error_propagates_without_retry_or_motion(self):
        machine = self.machine([])
        error = ValueError('Vision failed')
        machine.capture_box = Mock(side_effect=error)
        def paced_poses():
            import time
            time.sleep(.001)
            return [dict(x=1., y=2., yaw=0., stamp_ns=s) for s in (100_100_000_000, 100_200_000_000)]
        machine.pose_references = Mock(side_effect=paced_poses)
        history = [dict(x=1., y=2., yaw=0., stamp_ns=100_000_000_000)]
        with self.assertRaises(ValueError) as raised:
            machine.capture_box_with_poses(history, 'first')
        self.assertIs(raised.exception, error)
        machine.capture_box.assert_called_once()
        machine.action.assert_not_called()

    def test_deadline_after_measurement_prevents_dispatch(self):
        machine = self.machine([self.observation()])
        clock = [100.]
        machine.measure_box_for_pickup.side_effect = lambda: (clock.__setitem__(0, 171.) or self.observation())
        with patch.object(runtime.time, 'monotonic', side_effect=lambda: clock[0]), \
                self.assertRaisesRegex(RuntimeError, 'TOTAL_BUDGET'):
            machine.align_box_for_pickup()
        machine.action.assert_called_once()

    def test_head_failed_result_never_captures_or_navigates(self):
        machine = self.machine([])
        machine.action.return_value = dict(SUCCESS, status=6)
        with self.assertRaises(ValueError): machine.align_box_for_pickup()
        machine.measure_box_for_pickup.assert_not_called()
        machine.action.assert_called_once()


class AlignmentPayloadTests(unittest.TestCase):
    def test_health_payload_bootstraps_same_base_validator_without_ros_imports(self):
        import sys
        payload=cli.make_payload('check',PROFILE,contract.new_checkpoint(PROFILE))
        namespace={'__name__':'embedded_health_test','__package__':None}
        with patch.dict(sys.modules):
            exec(compile(payload['health_worker'],'embedded-health','exec'),namespace)
            collector=namespace['Acquisition']({'command':'base','request_id':'b'},100,100)
            self.assertEqual(collector.base.__class__.__module__,'scenario1_resume_worker')
            self.assertIsNone(collector.complete(101,publishers=1))

    def test_transient_modules_keep_context_and_sps_package_for_old_resumes(self):
        cp = contract.new_checkpoint(PROFILE, policy='assume', execution_profile='optimistic_v1')
        payload = cli.make_payload('check', PROFILE, cp)
        self.assertEqual(payload['bundle']['manifest']['id'], 'bf145fa17e1116fc')
        self.assertNotIn(cli.TASK_ROOT+'cruzr/move_head_lower.xml', payload['extra_hashes'])
        import sys, types
        with patch.dict(sys.modules):
            for name, source in payload['modules']:
                module = types.ModuleType(name); sys.modules[name] = module
                exec(compile(source, name, 'exec'), module.__dict__)
            compile(payload['action_client'], 'action-client-memory', 'exec')

    def test_head_task_pin_checked_before_movement_without_changing_context(self):
        machine = runtime.Runtime(dict(checkpoint=contract.new_checkpoint(PROFILE)), emit=Mock())
        machine.native = Mock(return_value=alignment.HEAD_SHA256+'\n')
        machine.check_box_alignment_head()
        for actual in ('different', '', alignment.HEAD_SHA256+'extra'):
            machine.native.return_value = actual
            with self.subTest(actual=actual), self.assertRaisesRegex(RuntimeError, 'HEAD_TASK_CHANGED'):
                machine.check_box_alignment_head()

    def test_console_reports_axis_sign_and_millimeters(self):
        console = ConsoleReporter()
        rows = console.render(dict(event='box_alignment', phase='in_flight', attempt=1,
                                   displacement_base_m=dict(x=.0209, y=0)))
        self.assertTrue(any('X: 20,9 mm' in row for row in rows))
        self.assertFalse(any('Y:' in row for row in rows))

    def test_console_reports_terminal_residual_as_pending_visual_measurement(self):
        rows=ConsoleReporter().render(dict(event='box_alignment',phase='arrival',attempt=1,
            measurements=[dict(distance_m=.00963,yaw_error_deg=.45)],pickup_verified=False))
        self.assertIn('9,6 mm','\n'.join(rows))
        self.assertIn('Se vuelve a medir la caja','\n'.join(rows))

    def test_native_adapter_keeps_gate_and_rejects_selection_changed_since_alignment(self):
        from scripts.box_handling.test_scenario1_perception import PositionRejectionObservationTest
        helper = PositionRejectionObservationTest()
        for moved in (False, True):
            with tempfile.TemporaryDirectory() as directory, helper.transient_adapter(directory) as namespace:
                reference = namespace['original'](report(), 100_100_000_000)
                reference['stamp_ns'] = 99_000_000_000
                (Path(directory)/'box-alignment-reference.json').write_text(json.dumps(reference))
                raw = report()
                if moved:
                    raw['vision_result']['trans_outputs']['box_pose']['poses'][1]['position']['y'] += .03
                second = copy.deepcopy(raw)
                second['vision_result']['trans_outputs']['box_pose']['header']['stamp']['nanosec'] = 100_000_000
                second['tf_at_detection']['header']['stamp']['nanosec'] = 100_000_000
                namespace['capture'] = Mock(return_value=second)
                with patch.object(runtime.time, 'time_ns', return_value=100_200_000_000):
                    if moved:
                        with self.assertRaises(ValueError): namespace['stable'](raw, 100_100_000_000)
                    else:
                        selected = namespace['stable'](raw, 100_100_000_000)
                        self.assertTrue(selected['selection']['position_gate']['passed'])
                        self.assertEqual(selected['stamp_ns'], 100_100_000_000)


if __name__ == '__main__':
    unittest.main()
