"""Pure runner contracts and fake Docker preflight; no SSH, ROS or player."""
import copy
from collections import Counter
import io
import json
import math
import subprocess
import threading
import unittest
from unittest.mock import patch

from scripts.box_handling import prepare_empty_arm_diagnostic as builder
from scripts.box_handling import run_empty_arm_diagnostic_remote as runner
from scripts.box_handling.test_prepare_empty_arm_diagnostic import state


def queries(round_number=1):
    source = state()
    source['header']['stamp'] = dict(sec=100, nanosec=1000*round_number)
    ids = [1001, 1002, 2001, 2002, 2003, 3001, *range(4001, 4008), *range(5001, 5008)]
    names = [n for group in runner.ORDERS.values() for n in group]
    items = [dict(id=axis, name=name.replace('_joint', '_motor'), type='ubt_standard_revolute',
                  error_code=0, status=0x27, velocity=0., position=0., cmd_pos=0., current=.1)
             for axis, name in zip(ids, names)]
    values = dict(actuators=json.dumps(dict(header=source['header'], act_item=items)),
        joints=json.dumps(source),
        controllers="Response(controller=[{'name': 'manipulation_controller', 'state': 'running'}, "
                    "{'name': 'sdk_controller', 'state': 'initialized'}, "
                    "{'name': 'vla_sdk_controller', 'state': 'initialized'}])",
        sdk_action='Action server count: 1\nAction client count: 0\n', sdk_commands='Writer count: 0\n',
        manip_status='status_list:\n- goal_info: {}\n  status: 4\n', locks="locked: false\nmodule_name: ''\n",
        estop_key_state='data: 0\n---\n', servo_estop_key_state='data: 0\n---\n',
        chrg_input_status='data: 0\n---\n', battery_state='batsoc: 80.0\n  batsoc: 81.0\n')
    return {key: dict(returncode=0, stdout=value, stderr='', completed_monotonic=1.)
            for key, value in values.items()}


class MotionValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.motion, _ = builder.prepare(state(), 'right')

    def test_builder_output_is_exactly_five_groups_and_selected_seven_axes(self):
        for arm in ('right', 'left'):
            motion, _ = builder.prepare(state(), arm)
            checked = runner.validate_motion(motion, state(), arm)
            self.assertEqual(checked['duration_s'], 22)
            self.assertEqual(checked['held_joint_count'], 13)
            self.assertEqual(checked['moving_joints'], list(runner.ORDERS[arm+'_arm']))
            self.assertAlmostEqual(checked['amplitude_deg'], 2.)
            for group in runner.ORDERS:
                self.assertEqual(len(motion[group]), 11001)
                self.assertEqual(motion[group][0]['q'], motion[group][-1]['q'])

    def test_row_count_grid_wrong_arm_and_extra_group_are_rejected(self):
        cases = [lambda m: m['right_arm'].pop(),
                 lambda m: m['right_arm'][4321].update(t=8.64201),
                 lambda m: m['head'][0].update(t=True),
                 lambda m: m.update(extra=[])]
        for mutate in cases:
            motion = copy.deepcopy(self.motion)
            mutate(motion)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                runner.validate_motion(motion, state(), 'right')
        with self.assertRaises(ValueError):
            runner.validate_motion(self.motion, state(), 'left')

    def test_no_unselected_axis_change_jitter_or_nonfinite_value_is_accepted(self):
        for group, index, delta in (('left_arm', 7000, .0001), ('right_arm', 7000, .0001),
                                     ('waist', 5000, math.nan), ('head', 5000, True)):
            motion = copy.deepcopy(self.motion)
            motion[group][index]['q'][0] = delta if type(delta) is bool or not math.isfinite(delta) else motion[group][index]['q'][0]+delta
            with self.subTest(group=group, delta=delta), self.assertRaises(ValueError):
                runner.validate_motion(motion, state(), 'right')

    def test_incomplete_moving_or_stale_initial_state_and_inexact_return_are_rejected(self):
        missing = state()
        for key in ('name', 'position', 'velocity', 'effort'):
            missing[key].pop(0)
        moving = state()
        moving['velocity'][0] = .002
        stale = state()
        stale['position'][stale['name'].index('R_wrist_roll_joint')] += .003001
        for sample in (missing, moving, stale):
            with self.subTest(sample=sample), self.assertRaises(ValueError):
                runner.validate_motion(self.motion, sample, 'right')
        motion = copy.deepcopy(self.motion)
        motion['right_arm'][-1]['q'][0] += 1e-13
        with self.assertRaisesRegex(ValueError, 'Return'):
            runner.validate_motion(motion, state(), 'right')

    def test_amplitude_above_two_degrees_is_rejected_even_with_exact_shape(self):
        motion = copy.deepcopy(self.motion)
        first = motion['right_arm'][0]['q']
        for row in motion['right_arm']:
            row['q'] = [q0+(q-q0)*1.00001 for q0, q in zip(first, row['q'])]
        with self.assertRaisesRegex(ValueError, 'Excursion'):
            runner.validate_motion(motion, state(), 'right')


class PreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.motion, _ = builder.prepare(state(), 'right')

    def invoke(self, mutate=None, *, run=False, data_mutate=None):
        calls = Counter()
        players = []
        lock = threading.Lock()
        needles = dict(actuators='/mc/actuator_state', joints='/mc/whole_joint_states',
            controllers='ListControllers', sdk_action='/mc/action/outline_sdk_play',
            sdk_commands='/mc/sdk/robot_command', manip_status='/mc/manipulation/action/_action/status',
            locks='/sys/state/module_lock_info', **{key:'/emb/'+key for key in (
                'estop_key_state', 'servo_estop_key_state', 'chrg_input_status', 'battery_state')})
        def query(command):
            matches = [key for key, needle in needles.items() if needle in command[-1]]
            self.assertEqual(len(matches), 1)
            key = matches[0]
            with lock:
                calls[key] += 1
                round_number = calls[key]
            result = queries(round_number)[key]
            if mutate:
                mutate(key, round_number, result)
            return result
        data = dict(sha256='a'*64, motion=self.motion, contract=copy.deepcopy(runner.CONTRACT))
        if data_mutate:
            data = copy.deepcopy(data)
            data_mutate(data)
        probe_result = json.dumps(data)
        def command(args, **options):
            if args[:2] == ['docker', 'ps']:
                return subprocess.CompletedProcess(args, 0, 'walker-motion.manipulation_robot_app-1\nwalker-ros.ros2-1\n', '')
            if args[:3] == ['docker', 'exec', 'walker-motion.manipulation_robot_app-1'] and args[3:5] == ['python3', '-B']:
                return subprocess.CompletedProcess(args, 0, probe_result, '')
            if args[:3] == ['docker', 'exec', 'walker-motion.manipulation_robot_app-1'] and 'exec rosa run' in args[-1]:
                players.append(args)
                return subprocess.CompletedProcess(args, 0, 'Action finished with is_finished=true, bag has been played successfully', '')
            raise AssertionError('Unexpected process '+repr(args))
        argv = ['--motion', '/tmp/candidate.motion', '--sha256', 'a'*64, '--arm', 'right']
        if run:
            argv.append('--run')
        with patch.object(runner, 'query', query), patch.object(runner.subprocess, 'run', command), \
                patch.object(runner.time, 'monotonic', return_value=1.), patch('sys.stdout', io.StringIO()) as output:
            rc = runner.main(argv)
        return rc, [json.loads(line) for line in output.getvalue().splitlines()], players

    def test_default_runs_checks_only_and_explicit_run_dispatches_exactly_once(self):
        rc, rows, players = self.invoke()
        self.assertEqual(rc, 0)
        self.assertTrue(rows[0]['all_pass'])
        self.assertFalse(players)
        rc, rows, players = self.invoke(run=True)
        self.assertEqual(rc, 0)
        self.assertEqual(len(players), 1)
        self.assertEqual([row['kind'] for row in rows], ['preflight', 'physical_start', 'player_result'])
        self.assertFalse(rows[-1]['automatic_retry'])
        self.assertFalse(rows[-1]['home_requested'])

    def test_any_failed_query_or_active_control_blocks_the_player(self):
        cases = [('controllers', dict(returncode=124)), ('sdk_action', dict(stdout='Action server count: 1\nAction client count: 1\n')),
                 ('manip_status', dict(stdout='status_list:\n- goal_info: {}\n  status: 2\n')),
                 ('estop_key_state', dict(stdout='data: 1\n')), ('chrg_input_status', dict(stdout='data: 1\n'))]
        for target, changes in cases:
            def mutate(key, round_number, result):
                if key == target:
                    result.update(changes)
            with self.subTest(target=target):
                rc, rows, players = self.invoke(mutate, run=True)
                self.assertEqual(rc, 78)
                self.assertFalse(rows[0]['all_pass'])
                self.assertFalse(players)
                self.assertEqual(len(rows), 1)

    def test_failed_first_stop_read_is_not_cleared_by_a_later_good_read(self):
        def mutate(key, round_number, result):
            if key == 'estop_key_state' and round_number == 1:
                result['stdout'] = 'data: 1\n'
        rc, rows, players = self.invoke(mutate, run=True)
        self.assertEqual(rc, 78)
        self.assertFalse(rows[0]['all_pass'])
        self.assertFalse(players)

    def test_source_nonadvance_or_regression_blocks_after_refresh(self):
        for source in (1000, 999):
            def mutate(key, round_number, result):
                if key == 'joints' and round_number == 2:
                    sample = json.loads(result['stdout'])
                    sample['header']['stamp']['nanosec'] = source
                    result['stdout'] = json.dumps(sample)
            with self.subTest(source=source):
                rc, rows, players = self.invoke(mutate, run=True)
                self.assertEqual(rc, 78)
                self.assertFalse(rows[0]['all_pass'])
                self.assertFalse(players)

    def test_invalid_source_timestamp_and_old_immediate_receipt_block(self):
        cases = (dict(sec=True), dict(sec=-1), dict(nanosec=True), dict(nanosec=10**9),
                 dict(nanosec=-1), dict(sec=0, nanosec=0))
        for changes in cases:
            def mutate(key, round_number, result):
                if key == 'actuators' and round_number == 2:
                    sample = json.loads(result['stdout'])
                    sample['header']['stamp'].update(changes)
                    result['stdout'] = json.dumps(sample)
            with self.subTest(changes=changes):
                rc, rows, players = self.invoke(mutate, run=True)
                self.assertEqual(rc, 78)
                self.assertFalse(rows[0]['all_pass'])
                self.assertFalse(players)
        def old_receipt(key, round_number, result):
            if key == 'joints' and round_number == 2:
                result['completed_monotonic'] = -4.
        rc, rows, players = self.invoke(old_receipt, run=True)
        self.assertEqual(rc, 78)
        self.assertFalse(rows[0]['all_pass'])
        self.assertFalse(players)

    def test_bad_checksum_native_contract_or_candidate_never_dispatches(self):
        changes = [lambda data: data.update(sha256='b'*64),
                   lambda data: data['contract'].update({next(iter(runner.CONTRACT)): 'b'*64}),
                   lambda data: data['motion']['left_arm'][5000]['q'].__setitem__(0, .02)]
        for mutate in changes:
            with self.subTest(mutate=mutate):
                rc, rows, players = self.invoke(run=True, data_mutate=mutate)
                self.assertEqual(rc, 78)
                self.assertFalse(rows[0]['all_pass'])
                self.assertFalse(players)

    def test_body_identity_and_typed_faults_are_checked(self):
        for change in (dict(id=9001), dict(error_code=False), dict(error_code=0.)):
            incoming = queries()
            raw = json.loads(incoming['actuators']['stdout'])
            raw['act_item'][0].update(change)
            incoming['actuators']['stdout'] = json.dumps(raw)
            checks, _ = runner.checks_for(incoming)
            with self.subTest(change=change):
                self.assertFalse(all(checks.values()))

    def test_noncanonical_path_or_checksum_is_rejected_before_any_process(self):
        for path in ('candidate.motion', '/var/tmp/candidate.motion', '/tmp/../root/test.motion',
                     '/tmp//candidate.motion', '/tmp/candidate.json'):
            with self.subTest(path=path), patch.object(runner.subprocess, 'run', side_effect=AssertionError('No process')), \
                    patch('sys.stderr', io.StringIO()), self.assertRaises(SystemExit):
                runner.main(['--motion', path, '--sha256', 'a'*64, '--arm', 'right', '--run'])


if __name__ == '__main__':
    unittest.main()
