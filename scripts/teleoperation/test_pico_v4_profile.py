import math
import os
from pathlib import Path
import subprocess
import unittest

from scripts.teleoperation.check_pico_v4_hand_states import SUFFIXES, validate
from scripts.teleoperation.prepare_pico_v4_motion_env import prepare
from scripts.teleoperation.stage_pico_v4_migration import selected_paths

ROOT = Path(__file__).resolve().parent


class V4ProfileTests(unittest.TestCase):
    def test_sps_environment_preserves_other_fields_and_bytes(self):
        compose = b'services:\n  motion.mc_common:\n    environment:\n      - HW_TYPE=cruzr_s2_v1\n      - TELE_DEVICE=pico\n'
        database = b'{"envs":{"HW_TYPE":"cruzr_s2_v1","MC_SCENE":""},"untouched":42}'
        new_compose, new_db = prepare(compose, database)
        self.assertEqual(new_compose, compose.replace(b'HW_TYPE=cruzr_s2_v1', b'HW_TYPE=cruzr_s2_v1_sps'))
        self.assertEqual(new_db, database.replace(b'"cruzr_s2_v1"', b'"cruzr_s2_v1_sps"'))

    def test_sps_environment_rejects_unknown_or_ambiguous_sources(self):
        compose = b'services:\n  motion.mc_common:\n    environment:\n      - HW_TYPE=cruzr_s2_v1\n'
        database = b'{"envs":{"HW_TYPE":"cruzr_s2_v1"}}'
        for source, db in [
            (compose.replace(b'cruzr_s2_v1', b'other'), database),
            (compose + b'      - HW_TYPE=cruzr_s2_v1\n', database),
            (compose, database.replace(b'cruzr_s2_v1', b'other')),
        ]:
            with self.subTest(source=source, db=db), self.assertRaises(ValueError):
                prepare(source, db)

    def test_migration_retains_patches_and_motion_without_python_caches(self):
        diff = '\n'.join([
            'C /opt/walker/setup.bash',
            'C /opt/walker/task/config/home.xml',
            'A /prueba.motion',
            'A /tmp/prueba.motion',
            'A /opt/walker/lib/site-packages/foo/__pycache__/test.pyc',
            'C /etc/walker/log/test.log',
            'D /opt/walker/task/config/old.xml',
        ])
        self.assertEqual(selected_paths(diff), [
            '/opt/walker/setup.bash', '/opt/walker/task/config/home.xml',
            '/prueba.motion', '/tmp/prueba.motion'])

    def test_full_v4_states_accept_joint_reordering(self):
        for side in ('left', 'right'):
            names = [side + '_' + x for x in reversed(SUFFIXES)]
            validate(side, names, [0.] * 7, [0.] * 7)

    def test_reject_wrong_model_incomplete_and_nonfinite_states(self):
        names = ['left_' + x for x in SUFFIXES]
        faults = [
            (names[:-1], [0.] * 6, [0.] * 6),
            (names[:-1] + [names[0]], [0.] * 7, [0.] * 7),
            (names, [0.] * 6, [0.] * 7),
            (names, [0.] * 7, []),
            (names, [math.nan] + [0.] * 6, [0.] * 7),
            (names, [0.] * 7, [math.inf] + [0.] * 6),
            (names, [0.] * 7, [.021] + [0.] * 6),
        ]
        for args in faults:
            with self.subTest(args=args), self.assertRaises(ValueError):
                validate('left', *args)

    def profile(self, effector):
        return subprocess.run(['bash', '-c',
            'set -eu; source "$1"; printf "%s\\n" "$required_arm" '
            '"$expected_motion_hand" "$expected_teleop_task" "$arms_only_config_sha256"',
            'test', str(ROOT / 'pico_effector_profile.sh')],
            env=dict(os.environ, PICO_EFFECTOR=effector), capture_output=True, text=True)

    def test_separate_clamp_and_v4_profiles(self):
        clamp, v4 = self.profile('clamp'), self.profile('v4')
        self.assertEqual(clamp.returncode, 0, clamp.stderr)
        self.assertEqual(v4.returncode, 0, v4.stderr)
        self.assertEqual(clamp.stdout.splitlines()[:2], ['clamp', 'clamp'])
        self.assertEqual(v4.stdout.splitlines()[:2], ['hand', 'v4'])
        self.assertNotEqual(clamp.stdout.splitlines()[2:], v4.stdout.splitlines()[2:])

    def test_hand_reader_sources_ros_with_optional_variables_unset(self):
        source = (ROOT / 'cruzr_pico_teleop_pc.sh').read_text()
        fragment = source.split('check_v4_hand_states() {', 1)[1].split("<<'INNER'\n", 1)[1].split('\nexport ROS2CLI_DISABLE_DAEMON', 1)[0]
        # Simulate ROS setup's optional variable expansion, with no ROS/network.
        mock = 'source() { test -z "$AMENT_TRACE_SETUP_FILES"; }\n'
        env = dict(os.environ)
        env.pop('AMENT_TRACE_SETUP_FILES', None)
        result = subprocess.run(['bash', '-c', mock+fragment+'\n[[ $- == *u* ]]'],
            env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)

    def test_unknown_effector_cannot_start(self):
        self.assertNotEqual(self.profile('v3').returncode, 0)

    def test_wrapper_rejects_full_body_and_legacy_modes_before_any_connection(self):
        for mode in ('--teleoperate-full', '--all-controls', '--gate-only'):
            r = subprocess.run(['bash', str(ROOT / 'probar_pico_v4.sh'), mode],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 2)
            self.assertIn('no admitida', r.stderr)


if __name__ == '__main__':
    unittest.main()
