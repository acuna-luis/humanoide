"""Offline native preparation validation and fake preflight/action transport."""
import copy
from collections import Counter
import io
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from scripts.box_handling import prepare_native_arm_preparation as builder
from scripts.box_handling import run_native_arm_preparation_remote as runner
from scripts.box_handling.test_prepare_empty_arm_diagnostic import state, urdf
from scripts.box_handling.test_run_empty_arm_diagnostic_remote import queries


UUID = '12345678-1234-4567-89ab-123456789abc'


def bundle(arm='right'):
    xml, result = builder.prepare(state(), arm, builder.SOURCE_XML.read_text(), urdf())
    result['urdf']['sha256'] = runner.CONTRACT[next(p for p in runner.CONTRACT if p.endswith('/urdf/cruzr_s2.urdf'))]
    return result


def successful_rows():
    return [dict(event='accepted', accepted=True, goal_id=UUID),
            dict(event='status', status=2, goal_id=UUID),
            dict(event='result', goal_id=UUID, status=4,
                 result=dict(state=dict(state=1101001, desc='SUCCEED')))]


class NativePreparationContracts(unittest.TestCase):
    def test_each_arm_accepts_original_full_preparation_and_exact_measured_return(self):
        for arm in ('right', 'left'):
            candidate = bundle(arm)
            original = copy.deepcopy(candidate)
            result = runner.validate_bundle(candidate, state())
            self.assertEqual(result['arm'], arm)
            self.assertEqual(result['commanded_joint_count'], 7)
            self.assertEqual((result['preparation_duration_s'], result['return_duration_s']), (3, 6))
            self.assertEqual(result['native_preparation_rad'], list(runner.passive.NATIVE[arm]))
            self.assertEqual(candidate, original)
            self.assertFalse(result['full_grasp_reproduced'])

    def test_extra_action_other_arm_pose_duration_or_force_field_is_rejected(self):
        original = bundle()
        mutations = [lambda root: root[0][0].append(copy.deepcopy(root[0][0][0])),
                     lambda root: root[0][0][0].set('location', 'left'),
                     lambda root: root[0][0][0].set('duration', '4'),
                     lambda root: root[0][0][0].set('joint_angles', '0;0;0;0;0;0;0'),
                     lambda root: root[0][0][1].set('joint_angles', '0;0;0;0;0;0;0'),
                     lambda root: root[0][0][0].set('force', '100')]
        for mutate in mutations:
            root = ET.fromstring(original['xml'])
            mutate(root)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                runner.validate_xml(ET.tostring(root, encoding='unicode'), 'right',
                                    original['source']['initial_joint_reference_20d'])

    def test_missing_body_home_motion_and_changed_initial_reference_fail(self):
        candidate = bundle()
        bad = state()
        bad['position'][0] = .02
        moving = state()
        moving['velocity'][0] = .002
        changed = state()
        changed['position'][0] += .003001
        missing = state()
        for key in ('name', 'position', 'velocity', 'effort'):
            missing[key].pop(0)
        for sample in (bad, moving, changed, missing):
            with self.subTest(sample=sample), self.assertRaises(ValueError):
                runner.validate_bundle(candidate, sample)

    def test_bundle_task_path_hash_canonical_source_and_urdf_are_bound(self):
        mutations = [lambda b: b['candidate'].update(task_name='cruzr/home'),
                     lambda b: b['candidate'].update(runtime_path=runner.ORIGINAL),
                     lambda b: b['candidate'].update(xml_sha256='0'*64),
                     lambda b: b['urdf'].update(sha256='0'*64),
                     lambda b: b['source']['canonical_joint_state']['position'].__setitem__(0, 0.)]
        for mutate in mutations:
            value = bundle()
            mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                runner.validate_bundle(value, state())

    def test_only_unique_accepted_uuid_and_successful_terminal_are_accepted(self):
        encode = lambda rows: 'NATIVE INFO retained\n'+'\n'.join(json.dumps(row) for row in rows)
        accepted = runner.validate_result(0, encode(successful_rows()))
        self.assertEqual(accepted['goal_id'], UUID)
        self.assertEqual(accepted['native_log_lines'], ['NATIVE INFO retained'])
        self.assertFalse(accepted['physical_stop_verified'])
        cases = []
        for status in (True, 2, 5, 6):
            rows = successful_rows(); rows[-1]['status'] = status; cases.append(rows)
        rows = successful_rows(); rows[-1]['goal_id'] = 'other'; cases.append(rows)
        rows = successful_rows(); rows[-1]['result'] = None; cases.append(rows)
        rows = successful_rows(); rows[-1]['result']['state']['state'] = 1101004; cases.append(rows)
        rows = successful_rows(); rows.append(copy.deepcopy(rows[-1])); cases.append(rows)
        rows = successful_rows(); rows.append(dict(event='error', reason='late fault')); cases.append(rows)
        rows = successful_rows(); rows.append(dict(event='status', status=6, goal_id=UUID)); cases.append(rows)
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                runner.validate_result(0, encode(rows))
        with self.assertRaises(ValueError):
            runner.validate_result(2, encode(successful_rows()))


class NativePreparationPreflight(unittest.TestCase):
    def invoke(self, *, run=False, mutate_query=None, corrupt_contract=False, action_rows=None, action_rc=0):
        candidate = bundle()
        calls, actions = Counter(), []
        lock = threading.Lock()
        needles = dict(actuators='/mc/actuator_state', joints='/mc/whole_joint_states',
            controllers='ListControllers', sdk_action='/mc/action/outline_sdk_play',
            sdk_commands='/mc/sdk/robot_command', manip_status='/mc/manipulation/action/_action/status',
            locks='/sys/state/module_lock_info', **{key:'/emb/'+key for key in (
                'estop_key_state', 'servo_estop_key_state', 'chrg_input_status', 'battery_state')})
        def read(command):
            key, = [key for key, needle in needles.items() if needle in command[-1]]
            with lock:
                calls[key] += 1
                number = calls[key]
            result = queries(number)[key]
            if mutate_query:
                mutate_query(key, number, result)
            return result
        with tempfile.TemporaryDirectory(prefix='native-preparation-test-') as directory:
            support = Path(directory)
            path = support/'manifest.json'
            path.write_text(json.dumps(candidate))
            expected = dict(runner.CONTRACT, **{str(support/(name+'.py')): digest for name, digest in runner.SUPPORT.items()},
                            **{candidate['candidate']['runtime_path']: candidate['candidate']['xml_sha256']})
            if corrupt_contract:
                expected[runner.META_MOVE] = '0'*64
            def process(args, **options):
                if args[:2] == ['docker', 'ps']:
                    return subprocess.CompletedProcess(args, 0, 'walker-motion.manipulation_robot_app-1\nwalker-ros.ros2-1\n', '')
                if args[3:5] == ['python3', '-B']:
                    return subprocess.CompletedProcess(args, 0, json.dumps(expected), '')
                if args[3:5] == ['bash', '-lc'] and 'scenario1_action_client.py' in args[-1]:
                    self.assertIn('--timeout 25', args[-1])
                    self.assertNotIn('outline_sdk', args[-1])
                    actions.append(args)
                    rows = successful_rows() if action_rows is None else action_rows
                    return subprocess.CompletedProcess(args, action_rc, '\n'.join(json.dumps(row) for row in rows), '')
                raise AssertionError('No unmocked process '+repr(args))
            argv = ['--bundle', str(path), '--support-dir', str(support)]+(['--run'] if run else [])
            with patch.object(runner.passive, 'query', read), patch.object(runner.subprocess, 'run', process), \
                    patch.object(runner.time, 'monotonic', return_value=1.), patch('sys.stdout', io.StringIO()) as output:
                result = runner.main(argv)
            return result, [json.loads(line) for line in output.getvalue().splitlines()], actions

    def test_default_check_has_no_action_and_run_dispatches_only_one_native_goal(self):
        result, rows, actions = self.invoke()
        self.assertEqual(result, 0)
        self.assertTrue(rows[0]['all_pass'])
        self.assertFalse(actions)
        result, rows, actions = self.invoke(run=True)
        self.assertEqual(result, 0)
        self.assertEqual(len(actions), 1)
        self.assertEqual(rows[-1]['kind'], 'native_preparation_result')
        self.assertFalse(rows[-1]['home_requested'])

    def test_first_stop_failure_or_failed_query_or_changed_contract_never_dispatches(self):
        def first_stop(key, number, row):
            if key == 'estop_key_state' and number == 1:
                row['stdout'] = 'data: 1\n'
        def failed_query(key, number, row):
            if key == 'controllers':
                row['returncode'] = 124
        for mutation in (first_stop, failed_query):
            with self.subTest(mutation=mutation):
                result, rows, actions = self.invoke(run=True, mutate_query=mutation)
                self.assertEqual(result, 78)
                self.assertFalse(rows[0]['all_pass'])
                self.assertFalse(actions)
        result, rows, actions = self.invoke(run=True, corrupt_contract=True)
        self.assertEqual(result, 78)
        self.assertFalse(actions)

    def test_no_source_advance_or_stale_stop_receipt_never_dispatches(self):
        def frozen_source(key, number, row):
            if key == 'actuators' and number == 2:
                message = json.loads(row['stdout']); message['header']['stamp']['nanosec'] = 1000
                row['stdout'] = json.dumps(message)
        def stale_stop(key, number, row):
            if key == 'servo_estop_key_state' and number == 2:
                row['completed_monotonic'] = -4.
        for mutation in (frozen_source, stale_stop):
            with self.subTest(mutation=mutation):
                result, rows, actions = self.invoke(run=True, mutate_query=mutation)
                self.assertEqual(result, 78)
                self.assertFalse(actions)

    def test_failed_native_action_has_one_dispatch_no_retry_and_no_home(self):
        rows = successful_rows()
        rows[-1]['status'] = 6
        result, output, actions = self.invoke(run=True, action_rows=rows, action_rc=2)
        self.assertEqual(result, 78)
        self.assertEqual(len(actions), 1)
        self.assertEqual(output[-1]['kind'], 'native_preparation_failed')
        self.assertFalse(output[-1]['automatic_retry'])
        self.assertFalse(output[-1]['home_requested'])


if __name__ == '__main__':
    unittest.main()
