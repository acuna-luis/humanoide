"""Pruebas sin GPU, ROS ni conexión a robot del contrato de shadow."""
import base64
import copy
import hashlib
import unittest

from shadow_live_inference import validate_observation


class ShadowInputTests(unittest.TestCase):
    def setUp(self):
        self.train = {'task': 'test', 'state_names': [f'j{i}' for i in range(27)]}
        self.payload = b'test image bytes'
        self.row = {'schema': 'cruzr_ball_live_observation_v1', 'task': 'test',
                    'state_names': self.train['state_names'][:], 'state27': [0.0] * 27,
                    'image_source_ns': 1_000_000_000, 'joint_source_ns': 990_000_000,
                    'hand_source_ns': 991_000_000,
                    'received_monotonic_ns': {'image': 2_000_000_000, 'joint': 1_950_000_000, 'hand': 1_951_000_000},
                    'png_b64': base64.b64encode(self.payload).decode('ascii'),
                    'image_sha256': hashlib.sha256(self.payload).hexdigest()}

    def test_valid_contract(self):
        self.assertEqual(validate_observation(self.row, self.train), self.payload)

    def test_invalid_state_or_identity(self):
        for key, value in [('state27', [False] + [0.0] * 26), ('state27', [float('nan')] + [0.0] * 26),
                           ('state27', [0.0] * 26), ('task', 'other'), ('state_names', list(reversed(self.train['state_names'])))]:
            row = copy.deepcopy(self.row)
            row[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                validate_observation(row, self.train)

    def test_noncausal_or_old_and_repeated(self):
        for key, value in [('joint_source_ns', 1_000_000_001), ('hand_source_ns', 900_000_000)]:
            row = copy.deepcopy(self.row)
            row[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_observation(row, self.train)
        for value in (2_000_000_001, 1_000_000_000):
            row = copy.deepcopy(self.row)
            row['received_monotonic_ns']['joint'] = value
            with self.assertRaises(ValueError):
                validate_observation(row, self.train)
        with self.assertRaises(ValueError):
            validate_observation(self.row, self.train, 1_000_000_000)

    def test_invalid_encoded_image(self):
        for key, value in [('image_sha256', 'bad'), ('png_b64', '!!!')]:
            row = copy.deepcopy(self.row)
            row[key] = value
            with self.assertRaises(ValueError):
                validate_observation(row, self.train)


if __name__ == '__main__':
    unittest.main()
