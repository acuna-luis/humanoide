"""Synthetic failure cases; no robot access or movement."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cruzr_prepare_recovery import idle_gate, one_document, state_from_trace
from cruzr_pico_to_home_owner_gate import JOINT_ORDER
from general_home.trace_analysis import ACTUATORS, ACT_TOPIC, STOP_TOPICS


def idle_reads():
    return {k: dict(returncode=0, stdout=v) for k, v in {
        'commands': 'Type: mc_task_msgs/msg/RobotCommand\nWriter count: 0\nReader count: 2\n',
        'action': 'status_list:\n- status: 5\n---\n',
        'locks': "locked: false\nmodule_name: ''\n---\n",
    }.items()}


def stationary_trace():
    rows = [dict(kind='start', schema='cruzr-passive-motion-trace-v1',
                 received_monotonic_ns=1, movement_commands=0)]
    for topic in STOP_TOPICS:
        rows.append(dict(kind='message', topic=topic, message=dict(data=0), received_monotonic_ns=len(rows)+1))
    for sample in range(4):
        stamp = dict(sec=100, nanosec=sample*10_000_000)
        items = []
        for actuator, name in ACTUATORS.items():
            if actuator >= 11000:
                continue
            position = (-1 if name.startswith('L') else 1) * (.03 * JOINT_ORDER.index(name))
            items.append(dict(id=actuator, position=position, cmd_pos=position, velocity=0.,
                              stamp=stamp, status=7, error_code=0))
        rows.append(dict(kind='message', topic=ACT_TOPIC, received_monotonic_ns=(sample+1)*10_000_000,
                         message=dict(header=dict(stamp=stamp), act_item=items)))
    rows.append(dict(kind='end', received_monotonic_ns=41_000_000,
                     counts={ACT_TOPIC: 4, **{t: 1 for t in STOP_TOPICS}}, errors=[], movement_commands=0))
    return rows


def canonical_samples():
    return [dict(header=dict(stamp=dict(sec=100, nanosec=i)), name=JOINT_ORDER,
                 position=[(-1 if n.startswith('L') else 1)*(.03*JOINT_ORDER.index(n)) for n in JOINT_ORDER],
                 velocity=[0.]*20) for i in (10, 20)]


def state(rows, empty=True, joints=None):
    return state_from_trace(rows, empty_clamps=empty, captured_at='2026-09-11T00:00:00+00:00',
                            joint_samples=canonical_samples() if joints is None else joints)[0]


class PreparationTests(unittest.TestCase):
    def test_preserves_actual_asymmetric_joints_instead_of_substituting_pico(self):
        result = state(stationary_trace())
        self.assertEqual(result['joint_state']['name'], JOINT_ORDER)
        for name, value in zip(JOINT_ORDER, result['joint_state']['position']):
            self.assertAlmostEqual(value, (-1 if name.startswith('L') else 1)*(.03*JOINT_ORDER.index(name)))
        self.assertNotEqual(result['joint_state']['position'][0:7], result['joint_state']['position'][7:14])

    def test_yaml_trailing_separator_supported_but_second_payload_rejected(self):
        self.assertEqual(one_document('data: 0\n---\n'), {'data': 0})
        with self.assertRaises(ValueError):
            one_document('data: 0\n---\ndata: 1\n')

    def test_motor_signs_never_replace_canonical_joint_coordinates(self):
        rows = stationary_trace()
        for row in rows:
            if row.get('topic') == ACT_TOPIC:
                for item in row['message']['act_item']:
                    item['position'] *= -1
                    item['cmd_pos'] *= -1
        self.assertEqual(state(rows)['joint_state']['position'], canonical_samples()[-1]['position'])

    def test_missing_stale_moving_or_duplicate_canonical_joints_rejected(self):
        for kind in ('missing', 'stale', 'moving', 'drift', 'duplicate'):
            samples = canonical_samples()
            if kind == 'missing':
                samples = []
            elif kind == 'stale':
                samples[1]['header'] = copy.deepcopy(samples[0]['header'])
            elif kind == 'moving':
                samples[1]['velocity'][0] = .1
            elif kind == 'drift':
                samples[1]['position'][0] += .1
            else:
                samples[1]['name'] = [JOINT_ORDER[0]] * 20
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                state(stationary_trace(), joints=samples)

    def test_idle_requires_no_writers_no_running_goal_and_no_module_lock(self):
        idle_gate(idle_reads())
        for key, value in [('commands', 'Writer count: 1\n'), ('commands', 'Reader count: 0\n'),
                           ('action', 'status_list:\n- status: 2\n'), ('action', 'status_list: null\n'),
                           ('locks', "locked: true\nmodule_name: ''\n")]:
            with self.subTest(key=key, value=value):
                reads = idle_reads(); reads[key]['stdout'] = value
                with self.assertRaises(ValueError):
                    idle_gate(reads)
        reads = idle_reads(); reads['commands']['returncode'] = 124
        with self.assertRaises(ValueError):
            idle_gate(reads)

    def test_rejects_moving_faulted_disabled_or_latent_command(self):
        for key, value in [('velocity', .003), ('error_code', 1), ('status', 0), ('cmd_pos', 5.)]:
            rows = stationary_trace()
            rows[3]['message']['act_item'][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                state(rows)

    def test_rejects_pose_drift_even_if_reported_velocity_zero(self):
        rows = stationary_trace()
        rows[-2]['message']['act_item'][0]['position'] += .003
        with self.assertRaises(ValueError):
            state(rows)

    def test_rejects_stale_incomplete_or_duplicate_actuator_capture(self):
        for kind in ('stale', 'truncated', 'duplicate'):
            rows = stationary_trace()
            if kind == 'stale':
                rows[4]['message'] = copy.deepcopy(rows[3]['message'])
            elif kind == 'truncated':
                rows.pop()
            else:
                rows[3]['message']['act_item'].append(copy.deepcopy(rows[3]['message']['act_item'][0]))
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                state(rows)

    def test_no_empty_clamp_assertion_or_active_stop_rejects(self):
        with self.assertRaises(ValueError):
            state(stationary_trace(), empty=False)
        rows = stationary_trace(); rows[1]['message']['data'] = 1
        with self.assertRaises(ValueError):
            state(rows)

    def test_no_run_mode_is_available(self):
        run = subprocess.run([sys.executable, str(Path(__file__).with_name('cruzr_prepare_recovery.py')),
                              '--run', '--empty-clamps', '--output-dir', '/must-not-be-created-by-recovery-test'],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertIn('unrecognized arguments: --run', run.stderr)


if __name__ == '__main__':
    unittest.main()
