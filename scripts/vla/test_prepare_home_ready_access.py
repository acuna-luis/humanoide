import unittest
from pathlib import Path
from unittest.mock import patch

from prepare_home_ready_access import measured_start, JOINT_ORDER


class MeasuredStartTests(unittest.TestCase):
    def check_samples(self, velocities=(0, 0), positions=(0, 0), errors=(0, 0)):
        samples = [(None, {n: dict(position=q, velocity=v, error_code=e)
                          for n in JOINT_ORDER})
                   for q, v, e in zip(positions, velocities, errors)]
        with patch('prepare_home_ready_access.digest', return_value='hash'), \
             patch.object(Path, 'read_text', return_value='{"topic":"/mc/actuator_state","message":{}}\n'*2), \
             patch('prepare_home_ready_access.decode_actuators', side_effect=samples):
            return measured_start(Path('unused'), {'input_sha256': 'hash', 'issues': []})

    def test_stationary(self):
        self.assertEqual(self.check_samples(), [0]*20)

    def test_motion_anywhere_in_trace_rejected(self):
        with self.assertRaises(ValueError):
            self.check_samples(velocities=(.1, 0))

    def test_position_drift_despite_zero_velocity_rejected(self):
        with self.assertRaises(ValueError):
            self.check_samples(positions=(0, .01))

    def test_fault_rejected(self):
        with self.assertRaises(ValueError):
            self.check_samples(errors=(1, 0))

    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):
            self.check_samples(positions=(0, float('nan')))


if __name__ == '__main__':
    unittest.main()
