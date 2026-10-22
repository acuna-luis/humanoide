"""Visual alignment orchestration with fake transport; never connects or moves."""
import copy
from contextlib import contextmanager
import json
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import front_sps_contract as sps
from scripts.box_handling import scenario1_box_alignment as alignment
from scripts.box_handling import scenario1_contract as contract
from scripts.box_handling import scenario1_runtime as runtime
from scripts.box_handling.test_scenario1_box_alignment import detection_report, selection


PROFILE = json.loads((Path(__file__).with_name('scenario1_current_geometry.json')).read_text())
SUCCESS = dict(event='result', status=4,
    result=dict(state=dict(desc='SUCCEED', state=1101001), dmsg='navigation_start SUCCEEDED'))


def posture(body=0., head=-.43):
    ids = (1001, 1002, 2001, 2002, 2003, 3001, 11001, 11002, 11003, 11004,
           *range(4001, 4008), *range(5001, 5008))
    return dict(actuator=[dict(act_item=[dict(id=i, position=head if i == 1002 else body) for i in ids])]*2)


class AlignmentRuntimeTests(unittest.TestCase):
    def observation(self, x=.7909, *, stamp=100_000_000_000, base_x=1., y=.1, z=.62):
        return selection(stamp=stamp, x=x, y=y, z=z), dict(x=base_x, y=2., yaw=0., stamp_ns=stamp)

    def machine(self, observations=(), *, attempts=7, include_option=True, execution='optimistic_v1'):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        checkpoint = contract.new_checkpoint(PROFILE, policy='assume', execution_profile=execution)
        for stage in ('navigate_get1', 'enable_vision'):
            checkpoint = contract.complete_stage(contract.begin_stage(checkpoint, stage), stage)
        payload = dict(checkpoint=checkpoint, profile=PROFILE, execution_profile=execution)
        if include_option:
            payload['box_alignment_attempts'] = attempts
        machine = runtime.Runtime(payload, emit=Mock())
        machine.session = Path(directory.name)
        machine.armed = True
        machine.live_monitor_enabled = True
        machine.connected = Mock()
        machine.discover = Mock()
        machine.hashes = Mock()
        machine.quick_health = Mock()
        machine.health = Mock(return_value=posture())
        machine.check_box_alignment_head = Mock()
        machine.action = Mock(return_value=copy.deepcopy(SUCCESS))
        values = iter(observations)
        machine.box_association = None
        def measure():
            pending, reference = next(values)
            machine.box_association = dict(frames=dict(frame_id='odom', child_frame_id='base_link'),
                observation=alignment.in_map(pending, reference), comparison_only=True)
            return pending, reference
        machine.measure_box_for_pickup = Mock(side_effect=measure)
        machine.pose_references = Mock(return_value=[dict(x=1.0209, y=2., yaw=0.)]*2)
        return machine

    def kinds(self, machine):
        return [call.args[0] for call in machine.action.call_args_list]

    def test_near_edge_correction_occurs_before_exactly_one_native_grasp(self):
        machine = self.machine([self.observation(),
            self.observation(.77, stamp=101_000_000_000, base_x=1.0209)])
        machine.stage(dict(stage='grasp'))
        self.assertEqual(self.kinds(machine), ['motion', 'navigation', 'motion'])
        calls = machine.action.call_args_list
        self.assertEqual(calls[0].args[1]['task_name'], alignment.HEAD_TASK)
        self.assertEqual(calls[2].args[1], dict(task_name='local_front_box/separate_right_cruzr', yaml_args='{}'))
        self.assertEqual(calls[1].kwargs['correction']['point'], 'box_pickup')
        self.assertEqual(machine.checkpoint['completed'], ['navigate_get1', 'enable_vision', 'grasp'])
        self.assertEqual(machine.measure_box_for_pickup.call_count, 2)
        reference = json.loads((machine.session/'box-alignment-reference.json').read_text())
        self.assertEqual(reference['stamp_ns'], 101_000_000_000)
        self.assertEqual(reference['selection']['selected_pose']['position']['x'], .77)

    def test_inside_margin_prepares_only_head_then_one_native_grasp(self):
        machine = self.machine([self.observation(.76)])
        machine.stage(dict(stage='grasp'))
        self.assertEqual(self.kinds(machine), ['motion', 'motion'])
        self.assertEqual(machine.action.call_args_list[0].args[1]['task_name'], alignment.HEAD_TASK)
        self.assertEqual(machine.action.call_args_list[1].args[1]['task_name'], runtime.TASKS['grasp'][0])
        machine.measure_box_for_pickup.assert_called_once()
        machine.pose_references.assert_not_called()

    def test_zero_and_legacy_payload_do_not_add_preparation_or_repeat_arms(self):
        for include_option in (True, False):
            machine = self.machine(attempts=0, include_option=include_option)
            with self.subTest(include_option=include_option):
                machine.stage(dict(stage='grasp'))
                machine.action.assert_called_once()
                self.assertEqual(machine.action.call_args.args[1]['task_name'], runtime.TASKS['grasp'][0])
                machine.measure_box_for_pickup.assert_not_called()
                machine.check_box_alignment_head.assert_not_called()

    def test_three_configured_corrections_are_sequential_then_grasp_once(self):
        machine = self.machine([self.observation(.81),
            self.observation(.78, stamp=101_000_000_000, base_x=1.03),
            self.observation(.777, stamp=102_000_000_000, base_x=1.044),
            self.observation(.765, stamp=103_000_000_000, base_x=1.055)], attempts=3)
        machine.pose_references.side_effect = [[dict(x=x, y=2., yaw=0.)]*2 for x in (1.03, 1.044, 1.055)]
        machine.stage(dict(stage='grasp'))
        self.assertEqual(self.kinds(machine), ['motion', 'navigation', 'navigation', 'navigation', 'motion'])
        requests = machine.action.call_args_list[1:4]
        self.assertEqual([c.kwargs['correction']['attempt'] for c in requests], [1, 2, 3])
        self.assertEqual(machine.measure_box_for_pickup.call_count, 4)
        self.assertAlmostEqual(json.loads((machine.session/'box-alignment.json').read_text())['total_requested_m'], .085)

    def test_configured_attempt_limit_stops_before_another_nav_or_grasp(self):
        machine = self.machine([self.observation(.795),
            self.observation(.78, stamp=101_000_000_000, base_x=1.015)], attempts=1)
        machine.pose_references.return_value = [dict(x=1.015, y=2., yaw=0.)]*2
        with self.assertRaisesRegex(RuntimeError, 'BOX_ALIGNMENT_LIMIT.*attempts'):
            machine.stage(dict(stage='grasp'))
        self.assertEqual(self.kinds(machine), ['motion', 'navigation'])
        self.assertEqual(machine.checkpoint['failure']['stage'], 'grasp')
        self.assertFalse((machine.session/'box-alignment-reference.json').exists())

    def test_hundred_mm_budget_stops_before_next_dispatch_without_reset(self):
        machine = self.machine([self.observation(.82),
            self.observation(.795, stamp=101_000_000_000, base_x=1.038),
            self.observation(.789, stamp=102_000_000_000, base_x=1.051),
            self.observation(.782, stamp=103_000_000_000, base_x=1.058)])
        machine.pose_references.side_effect = [[dict(x=x, y=2., yaw=0.)]*2 for x in (1.038, 1.051, 1.058)]
        with self.assertRaisesRegex(RuntimeError, 'BOX_ALIGNMENT_LIMIT.*distance'):
            machine.stage(dict(stage='grasp'))
        self.assertEqual(self.kinds(machine), ['motion', 'navigation', 'navigation', 'navigation'])
        record = json.loads((machine.session/'box-alignment.json').read_text())
        self.assertAlmostEqual(record['total_requested_m'], .094)
        self.assertFalse((machine.session/'box-alignment-reference.json').exists())

    def test_absolute_time_budget_not_restarted_after_successful_nav(self):
        machine = self.machine([self.observation(),
            self.observation(.77, stamp=101_000_000_000, base_x=1.0209)])
        clock = [100.]
        def action(kind, goal, timeout, **kwargs):
            clock[0] += 10 if kind == 'motion' else 111
            return copy.deepcopy(SUCCESS)
        machine.action.side_effect = action
        with patch.object(runtime.time, 'monotonic', side_effect=lambda: clock[0]), \
                self.assertRaisesRegex(RuntimeError, 'BOX_ALIGNMENT_TOTAL_BUDGET_EXCEEDED'):
            machine.stage(dict(stage='grasp'))
        self.assertEqual(self.kinds(machine), ['motion', 'navigation'])
        self.assertFalse((machine.session/'box-alignment-reference.json').exists())

    def test_reserves_attempt_and_length_before_navigation_even_when_it_fails(self):
        for error in (RuntimeError('Correction made no significant progress'), TimeoutError('native timeout')):
            machine = self.machine([self.observation()])
            def action(kind, goal, timeout, **kwargs):
                if kind == 'navigation':
                    record = json.loads((machine.session/'box-alignment.json').read_text())
                    self.assertEqual(record['phase'], 'in_flight')
                    self.assertEqual(record['attempt'], 1)
                    self.assertAlmostEqual(record['total_requested_m'], .0209)
                    self.assertNotIn('recover_no_progress', kwargs)
                    raise error
                return copy.deepcopy(SUCCESS)
            machine.action.side_effect = action
            with self.subTest(error=error), self.assertRaises(type(error)):
                machine.stage(dict(stage='grasp'))
            self.assertEqual(self.kinds(machine), ['motion', 'navigation'])
            machine.measure_box_for_pickup.assert_called_once()
            machine.pose_references.assert_not_called()
            self.assertFalse((machine.session/'box-alignment-reference.json').exists())

    def test_cancel_abort_or_unknown_nav_terminal_never_recaptures_or_grasps(self):
        for status in (2, 5, 6):
            machine = self.machine([self.observation()])
            machine.action.side_effect = [copy.deepcopy(SUCCESS), dict(SUCCESS, status=status)]
            with self.subTest(status=status), self.assertRaises(ValueError):
                machine.stage(dict(stage='grasp'))
            self.assertEqual(self.kinds(machine), ['motion', 'navigation'])
            machine.pose_references.assert_not_called()
            machine.measure_box_for_pickup.assert_called_once()

    def test_native_grasp_failure_never_repeats_it_or_repositions_after_it(self):
        machine = self.machine([self.observation(),
            self.observation(.77, stamp=101_000_000_000, base_x=1.0209)])
        machine.action.side_effect = [copy.deepcopy(SUCCESS), copy.deepcopy(SUCCESS), RuntimeError('native arm failure')]
        with self.assertRaisesRegex(RuntimeError, 'native arm failure'):
            machine.stage(dict(stage='grasp'))
        self.assertEqual(self.kinds(machine), ['motion', 'navigation', 'motion'])
        self.assertEqual(machine.checkpoint['failure']['stage'], 'grasp')
        self.assertEqual(machine.checkpoint['box_state'], 'unknown')

    def test_wrong_arrival_blocks_recapture_before_native_grasp(self):
        machine = self.machine([self.observation()])
        machine.pose_references.return_value = [dict(x=1.034, y=2., yaw=0.)]*2
        with self.assertRaisesRegex(ValueError, 'ARRIVAL_NOT_CONFIRMED'):
            machine.stage(dict(stage='grasp'))
        self.assertEqual(self.kinds(machine), ['motion', 'navigation'])
        machine.measure_box_for_pickup.assert_called_once()

    def test_changed_box_or_missing_visual_improvement_aborts_before_second_nav(self):
        for after in (self.observation(.7908, stamp=101_000_000_000, base_x=1.0209),
                      self.observation(.77, stamp=101_000_000_000, base_x=1.0209, y=.13)):
            machine = self.machine([self.observation(), after])
            with self.subTest(after=after), self.assertRaises((ValueError, RuntimeError)):
                machine.stage(dict(stage='grasp'))
            self.assertEqual(self.kinds(machine), ['motion', 'navigation'])
            self.assertFalse((machine.session/'box-alignment-reference.json').exists())

    def test_health_or_non_home_arms_abort_before_any_preparation(self):
        for invalid in (RuntimeError('health fault'), posture(body=.03)):
            machine = self.machine()
            if isinstance(invalid, BaseException):
                machine.health.side_effect = invalid
            else:
                machine.health.return_value = invalid
            with self.subTest(invalid=invalid), self.assertRaises((ValueError, RuntimeError)):
                machine.align_box_for_pickup()
            machine.action.assert_not_called()

    def test_unrecoverable_box_has_no_navigation_and_no_native_arm_preparation(self):
        for pending in (self.observation(.9), self.observation(z=0.)):
            machine = self.machine([pending])
            with self.subTest(pending=pending), self.assertRaises(ValueError):
                machine.stage(dict(stage='grasp'))
            machine.action.assert_called_once()
            self.assertEqual(machine.action.call_args.args[1]['task_name'], alignment.HEAD_TASK)


class FinalAdapterTests(unittest.TestCase):
    @contextmanager
    def adapter(self, directory):
        generated = runtime.guarded_adapter_source('/not-installed-for-test', directory,
            Path(__file__).with_name('scenario1_perception.py').read_text())
        with patch.dict(sys.modules, {'front_sps_contract': sps}), \
                patch.object(sps, 'select_report', sps.select_report), \
                patch.object(sps, 'validate_position', sps.validate_position), \
                patch.object(sys, 'path', list(sys.path)), patch.object(sys, 'argv', list(sys.argv)), \
                patch.object(runpy, 'run_path'):
            namespace = {}
            exec(compile(generated, 'test-guarded-alignment-adapter', 'exec'), namespace)
            yield namespace

    def reports(self):
        first = detection_report()
        first['vision_result']['trans_outputs']['box_pose']['poses'][1]['position']['x'] = .55
        second = copy.deepcopy(first)
        for header in (second['vision_result']['trans_outputs']['box_pose']['header'],
                       second['tf_at_detection']['header']):
            header['stamp']['nanosec'] = 100_000_000
        second['vision_result']['trans_outputs']['box_pose']['poses'][1]['position']['x'] = .551
        return first, second

    def test_final_adapter_recaptures_twice_and_preserves_last_original_pose(self):
        first, second = self.reports()
        reference = sps.select_report(first, 100_200_000_000)
        reference['stamp_ns'] -= 1
        original = copy.deepcopy((first, second, reference))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'box-alignment-reference.json'
            path.write_text(json.dumps(reference))
            with self.adapter(directory) as namespace, patch.object(runtime.time, 'time_ns', return_value=100_200_000_000):
                namespace['capture'] = Mock(return_value=second)
                result = namespace['stable'](first, 100_200_000_000)
                namespace['capture'].assert_called_once()
            self.assertEqual(path.read_text(), json.dumps(reference))
        self.assertEqual(result['camera_pose'], second['vision_result']['trans_outputs']['box_pose']['poses'][1])
        self.assertEqual(result['stamp_ns'], 100_100_000_000)
        self.assertAlmostEqual(result['selection']['selected_pose']['position']['x'], .751)
        self.assertEqual((first, second, reference), original)

    def test_final_adapter_rejects_changed_box_relative_to_pre_navigation_anchor(self):
        first, second = self.reports()
        reference = sps.select_report(first, 100_200_000_000)
        reference['stamp_ns'] -= 1
        reference['selection']['selected_pose']['position']['x'] = .72
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory)/'box-alignment-reference.json').write_text(json.dumps(reference))
            with self.adapter(directory) as namespace, patch.object(runtime.time, 'time_ns', return_value=100_200_000_000):
                namespace['capture'] = Mock(return_value=second)
                with self.assertRaisesRegex(ValueError, 'consistency policy'):
                    namespace['stable'](first, 100_200_000_000)

    def test_final_adapter_keeps_original_xyz_gate_after_alignment_reference(self):
        first, second = self.reports()
        reference = sps.select_report(first, 100_200_000_000)
        reference['stamp_ns'] -= 1
        second['vision_result']['trans_outputs']['box_pose']['poses'][1]['position']['x'] = .591
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory)/'box-alignment-reference.json').write_text(json.dumps(reference))
            with self.adapter(directory) as namespace, patch.object(runtime.time, 'time_ns', return_value=100_200_000_000):
                namespace['capture'] = Mock(return_value=second)
                with self.assertRaisesRegex(ValueError, 'BOX_POSITION_REJECTED'):
                    namespace['stable'](first, 100_200_000_000)


if __name__ == '__main__':
    unittest.main()
