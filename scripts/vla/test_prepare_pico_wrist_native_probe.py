"""Offline tests: no robot access or physical dispatch."""
import contextlib
import hashlib
import io
import json
import math
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import yaml
from unittest.mock import patch

import prepare_pico_wrist_native_probe as subject


def state():
    return {'name': list(subject.BODY), 'position': list(subject.BODY.values()),
            'velocity': [0.0] * len(subject.BODY)}


def urdf(velocity=1.0):
    joints = ''.join('<joint name="%s" type="revolute"><limit lower="-3" upper="3" velocity="%s"/></joint>'
                     % (name, velocity) for name in subject.ARM)
    return '<robot name="test">' + joints + '</robot>'


def transmissions():
    return yaml.safe_dump({'transmissions': {n+'_trans': {'joint': {'name': n,
        'limit': {'lower': -3.0, 'upper': 3.0}}} for n in subject.BODY}})


class PicoWristPreparationTests(unittest.TestCase):
    def test_single_right_wrist_action_and_native_goal(self):
        bundle = subject.prepare(state(), urdf(), transmissions())
        c = bundle['candidate']
        actions = ET.fromstring(c['xml']).findall('.//Action')
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0].get('location'), 'right')
        self.assertEqual(actions[0].get('type'), 'arm')
        goals = [float(x) for x in actions[0].get('joint_angles').split(';')]
        self.assertEqual(goals[:-1], [subject.BODY[n] for n in subject.ARM[:-1]])
        self.assertAlmostEqual(goals[-1], subject.BODY[subject.ARM_AXIS] + .01)
        self.assertEqual(c['goal'], {'task_name': c['task_name'], 'yaml_args': '{}'})
        self.assertFalse(bundle['physical_control_qualified'])
        self.assertEqual(bundle['movement_commands'], 0)
        self.assertFalse(c['automatic_return'])
        self.assertEqual(subject.validate(bundle, urdf(), transmissions())['movement_commands'], 0)

    def test_rejects_invalid_stale_reference_and_urdf(self):
        bad = state()
        bad['position'][bad['name'].index('head_pitch_joint')] = 0
        with self.assertRaisesRegex(ValueError, 'not_pico'):
            subject.prepare(bad, urdf(), transmissions())
        bad = state(); bad['velocity'][0] = math.nan
        with self.assertRaises(ValueError):
            subject.prepare(bad, urdf(), transmissions())
        with self.assertRaisesRegex(ValueError, 'necessary_average_speed'):
            subject.prepare(state(), urdf(.001), transmissions())
        with self.assertRaisesRegex(ValueError, 'duplicate_urdf_joint'):
            subject.prepare(state(), urdf().replace('</robot>',
                '<joint name="R_wrist_roll_joint" type="revolute"/></robot>'), transmissions())

    def test_tampering_and_different_urdf_are_rejected(self):
        bundle = subject.prepare(state(), urdf(), transmissions())
        bundle['candidate']['target_rad'][-1] += .01
        with self.assertRaisesRegex(ValueError, 'bundle_mismatch'):
            subject.validate(bundle, urdf(), transmissions())
        bundle = subject.prepare(state(), urdf(), transmissions())
        with self.assertRaisesRegex(ValueError, 'bundle_mismatch'):
            subject.validate(bundle, urdf() + '\n', transmissions())
        with self.assertRaisesRegex(ValueError, 'invalid_bundle_input'):
            subject.validate({'input': None}, urdf(), transmissions())

    def test_small_sps_margin_is_visible_and_never_qualifies_execution(self):
        config = yaml.safe_load(transmissions())
        q = subject.BODY['R_elbow_yaw_joint']
        config['transmissions']['R_elbow_yaw_joint_trans']['joint']['limit']['lower'] = q - .001
        bundle = subject.prepare(state(), urdf(), yaml.safe_dump(config))
        self.assertTrue(bundle['all_endpoints_inside_nominal_sps_limits'])
        self.assertFalse(bundle['all_endpoints_satisfy_diagnostic_margin'])
        self.assertFalse(bundle['physical_control_qualified'])
        self.assertAlmostEqual(bundle['nominal_sps_transmission_limits']['R_elbow_yaw_joint']
                               ['minimum_endpoint_margin_rad'], .001)

    def test_sps_endpoint_outside_limit_is_rejected(self):
        config = yaml.safe_load(transmissions())
        q = subject.BODY['R_wrist_roll_joint']
        config['transmissions']['R_wrist_roll_joint_trans']['joint']['limit']['upper'] = q + .005
        with self.assertRaisesRegex(ValueError, 'nominal_endpoint_outside_sps_transmissions:R_wrist_roll_joint'):
            subject.prepare(state(), urdf(), yaml.safe_dump(config))
        config = yaml.safe_load(transmissions())
        q = subject.BODY['L_elbow_yaw_joint']
        config['transmissions']['L_elbow_yaw_joint_trans']['joint']['limit']['upper'] = q - .001
        with self.assertRaisesRegex(ValueError, 'nominal_endpoint_outside_sps_transmissions:L_elbow_yaw_joint'):
            subject.prepare(state(), urdf(), yaml.safe_dump(config))

    def test_run_is_blocked_before_reading_any_input(self):
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('should not read')):
            with contextlib.redirect_stderr(io.StringIO()) as error:
                self.assertEqual(subject.main(['--run']), 2)
        self.assertIn('BLOCKED', error.getvalue())

    def test_cli_preserves_crlf_hash_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / 'state.json').write_text(json.dumps(state()))
            raw = (urdf() + '\r\n').encode('utf-8')
            (base / 'robot.urdf').write_bytes(raw)
            (base / 'transmissions.yaml').write_text(transmissions())
            args = ['--transmissions', str(base / 'transmissions.yaml'), '--state', str(base / 'state.json'), '--urdf', str(base / 'robot.urdf'),
                    '--output', str(base / 'new')]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(subject.main(args), 0)
            result = json.loads((base / 'new/manifest.json').read_text())
            self.assertEqual(result['input']['urdf_sha256'], hashlib.sha256(raw).hexdigest())
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(subject.main(args), 1)


if __name__ == '__main__':
    unittest.main()
