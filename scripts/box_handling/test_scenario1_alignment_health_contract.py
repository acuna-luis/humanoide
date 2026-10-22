"""Exercise alignment's real health contract with offline telemetry transport.

Do not replace Runtime.health or its controller/safety/20D validators: an
implicit None return used to pass the mocked orchestration tests but fail at
the first pickup_posture call on the robot.
"""
import copy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import scenario1_box_alignment as alignment
from scripts.box_handling import scenario1_contract as contract
from scripts.box_handling import scenario1_runtime as runtime
from scripts.lib.cruzr_home_posture_gate import BODY_ACTUATOR_ALIASES


PROFILE = json.loads(Path(__file__).with_name('scenario1_current_geometry.json').read_text())
SUCCESS = dict(event='result', status=4,
               result=dict(state=dict(desc='SUCCEED', state=1101001)))


class Clock:
    def __init__(self):
        self.ns = 100_000_000_000
        self.lock = threading.Lock()

    def advance(self, amount=10_000_000):
        with self.lock:
            self.ns += amount
            return self.ns

    def time_ns(self):
        with self.lock:
            return self.ns

    def time(self):
        return self.time_ns()/1e9

    monotonic = time


def stamp(ns):
    return dict(sec=ns//10**9, nanosec=ns % 10**9)


def health_report(clock, *, head=0.):
    samples = []
    for _ in range(2):
        items = []
        for _, aliases in BODY_ACTUATOR_ALIASES:
            axis = aliases[0]
            position = head if axis == 1002 else 0.
            items.append(dict(id=axis, error_code=0, status=7,
                              position=position, cmd_pos=position, velocity=0.))
        samples.append(dict(header=dict(stamp=stamp(clock.advance())), act_item=items))
    return dict(event='health_result', controller=dict(controller=[
        dict(name='manipulation_controller', state='running'),
        dict(name='sdk_controller', state='initialized'),
        dict(name='vla_sdk_controller', state='initialized')]),
        status=dict(status_list=[]),
        safety=dict(estop=dict(data=0), servo=dict(data=0), charger=dict(data=0),
                    battery=dict(batteries_states=[dict(batsoc=80.), dict(batsoc=81.)])),
        actuator=samples)


def odometry_report(clock):
    requested = clock.time_ns()
    samples = []
    for _ in range(2):
        samples.append(dict(header=dict(frame_id='odom', stamp=stamp(clock.advance())),
            child_frame_id='base_link',
            pose=dict(pose=dict(position=dict(x=0., y=0., z=0.),
                                orientation=dict(x=0., y=0., z=0., w=1.))),
            twist=dict(twist=dict(linear=dict(x=0., y=0., z=0.),
                                  angular=dict(x=0., y=0., z=0.)))))
    return dict(event='base_result', requested_ns=requested, completed_ns=clock.advance(1_000_000),
                samples=samples, stationary=True, publishers=1)


class AlignmentHealthContractTests(unittest.TestCase):
    def machine(self):
        clock = Clock()
        checkpoint = contract.new_checkpoint(PROFILE, policy='assume', execution_profile='optimistic_v1')
        for stage in ('navigate_get1', 'enable_vision'):
            checkpoint = contract.complete_stage(contract.begin_stage(checkpoint, stage), stage)
        machine = runtime.Runtime(dict(checkpoint=checkpoint, profile=PROFILE,
            execution_profile='optimistic_v1', box_alignment_attempts=7), emit=Mock())
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        machine.session = Path(directory.name)
        machine.armed = True
        machine.connected = Mock()
        # These are the hardware discovery/hash/query boundaries. Health and
        # every controller, safety, actuator, pose and association check stay real.
        machine.discover = Mock()
        machine.hashes = Mock()
        machine.check_box_alignment_head = Mock()
        machine.map_state = Mock(return_value=('utars_nav_map', 'FSM_WAITNAVIGATE'))
        machine.map_points = Mock(return_value={})
        phase = dict(head=0., health_count=0, captures=0)

        def telemetry(command, **parameters):
            if command == 'health':
                phase['health_count'] += 1
                return health_report(clock, head=phase['head'])
            if command == 'base':
                self.assertEqual(parameters, dict(timeout=5))
                return odometry_report(clock)
            if command == 'pose':
                return dict(poses=[dict(header=dict(frame_id='map', stamp=stamp(clock.advance())),
                    pose=dict(position=dict(x=1., y=2., z=0.),
                              orientation=dict(x=0., y=0., z=0., w=1.))) for _ in range(2)])
            raise AssertionError('Unexpected telemetry command: '+command)

        def capture():
            phase['captures'] += 1
            return dict(stamp_ns=clock.advance(), selection=dict(selected_pose=dict(
                position=dict(x=.75, y=0., z=.6), orientation=dict(x=0., y=0., z=0., w=1.))))

        def action(kind, goal, timeout, **options):
            self.assertEqual(kind, 'motion')
            self.assertEqual(goal, dict(task_name=alignment.HEAD_TASK, yaml_args='{}'))
            phase['head'] = -.43
            return copy.deepcopy(SUCCESS)

        machine.health_request = Mock(side_effect=telemetry)
        machine.capture_box = Mock(side_effect=capture)
        machine.action = Mock(side_effect=action)
        machine.native = Mock(side_effect=AssertionError('No hardware process in this test'))
        return machine, clock, phase

    def test_health_returns_the_original_report_after_two_real_20d_validations(self):
        machine, clock, _ = self.machine()
        report = health_report(clock)
        machine.health_request = Mock(return_value=report)
        snapshot = copy.deepcopy(report)
        with patch.object(runtime, 'time', clock):
            result = machine.health(require_home=True)
        self.assertIs(result, report)
        self.assertEqual(report, snapshot)
        machine.health_request.assert_called_once_with('health', require_home=True)
        args = machine.emit.call_args
        self.assertEqual(args.args, ('health',))
        self.assertEqual(len(args.kwargs['posture']), 2)
        self.assertTrue(all(row['ACTUATOR_BODY_COUNT'] == '20' and
                            row['ACTUATOR_ARM_COUNT'] == '14' for row in args.kwargs['posture']))

    def test_invalid_second_sample_is_rejected_before_any_health_return_or_emit(self):
        for problem in ('fault', 'velocity', 'latent_command', 'repeated_stamp', 'non_home'):
            machine, clock, _ = self.machine()
            report = health_report(clock)
            second = report['actuator'][1]
            if problem == 'fault':
                second['act_item'][-1]['error_code'] = 1
            elif problem == 'velocity':
                second['act_item'][-1]['velocity'] = .020001
            elif problem == 'latent_command':
                second['act_item'][-1]['cmd_pos'] = .010001
            elif problem == 'repeated_stamp':
                second['header']['stamp'] = copy.deepcopy(report['actuator'][0]['header']['stamp'])
            else:
                second['act_item'][-1].update(position=.03, cmd_pos=.03)
            machine.health_request = Mock(return_value=report)
            with self.subTest(problem=problem), patch.object(runtime, 'time', clock), \
                    self.assertRaises((ValueError, RuntimeError)):
                machine.health(require_home=True)
            machine.emit.assert_not_called()

    def test_real_health_supplies_both_initial_and_observation_posture_in_alignment(self):
        machine, clock, phase = self.machine()
        with patch.object(runtime, 'time', clock):
            machine.align_box_for_pickup()
        self.assertEqual(phase['health_count'], 2)
        self.assertEqual(phase['captures'], 2)
        machine.action.assert_called_once()
        self.assertEqual(machine.action.call_args.args[1]['task_name'], alignment.HEAD_TASK)
        reference = json.loads((machine.session/'box-alignment-reference.json').read_text())
        self.assertEqual(reference['selection']['selected_pose']['position']['x'], .75)

    def test_measurement_uses_real_health_return_in_observation_posture(self):
        machine, clock, phase = self.machine()
        phase['head'] = -.43
        with patch.object(runtime, 'time', clock):
            pending, reference = machine.measure_box_for_pickup()
        self.assertEqual(phase['health_count'], 1)
        self.assertEqual(phase['captures'], 2)
        self.assertEqual(pending['selection']['selected_pose']['position']['x'], .75)
        self.assertEqual((reference['x'], reference['y']), (1., 2.))
        machine.action.assert_not_called()

    def test_invalid_initial_health_blocks_head_navigation_and_native_grasp(self):
        machine, clock, phase = self.machine()
        report = health_report(clock)
        report['actuator'][1]['act_item'][-1]['error_code'] = 1
        machine.health_request = Mock(return_value=report)
        with patch.object(runtime, 'time', clock), self.assertRaisesRegex(ValueError, 'no habilitados'):
            machine.align_box_for_pickup()
        machine.action.assert_not_called()
        machine.capture_box.assert_not_called()
        self.assertEqual(phase['captures'], 0)

    def test_invalid_observation_health_blocks_capture_after_head_preparation(self):
        machine, clock, phase = self.machine()
        request = machine.health_request.side_effect
        def telemetry(command, **parameters):
            report = request(command, **parameters)
            if command == 'health' and phase['health_count'] == 2:
                report['actuator'][1]['act_item'][-1]['error_code'] = 1
            return report
        machine.health_request.side_effect = telemetry
        with patch.object(runtime, 'time', clock), self.assertRaisesRegex(ValueError, 'no habilitados'):
            machine.align_box_for_pickup()
        machine.action.assert_called_once()
        self.assertEqual(machine.action.call_args.args[1]['task_name'], alignment.HEAD_TASK)
        machine.capture_box.assert_not_called()
        self.assertFalse((machine.session/'box-alignment-reference.json').exists())


if __name__ == '__main__':
    unittest.main()
