"""Causal pairing and failure cases for the shadow-only stream adapter."""
import base64
import hashlib
import json
from pathlib import Path
import unittest

from live_ball_observation_adapter import Pairer, PROFILE, RIGHT_HAND
from passive_episode_remote import png_bytes


class LivePairingTests(unittest.TestCase):
    def setUp(self):
        self.names = json.loads(PROFILE.read_text())['joint_names']
        self.p = Pairer(self.names)
        self.p.accept({'kind': 'start', 'movement_commands': 0})
        self.p.accept({'kind': 'ready'})
        self.image = png_bytes(960, 576, 2880, 'rgb8', bytes(960 * 576 * 3))

    def state(self, kind, stamp, receipt, names=None, values=None):
        names = names or (self.names if kind == 'joints' else RIGHT_HAND)
        values = values if values is not None else [0.0] * len(names)
        message = {'name': names, 'position': values}
        if kind == 'joints':
            message['velocity'] = [0.0] * len(names)
        return {'kind': kind, 'source_ns': stamp, 'received_monotonic_ns': receipt,
                'message': message}

    def frame(self, stamp=1_000_000_000, receipt=2_000_000_000):
        return {'kind': 'rgb', 'source_ns': stamp, 'received_monotonic_ns': receipt,
                'png_b64': base64.b64encode(self.image).decode(),
                'png_sha256': hashlib.sha256(self.image).hexdigest()}

    def test_pairs_only_states_received_before_image(self):
        self.p.accept(self.state('joints', 980_000_000, 1_980_000_000, values=[1.0]*20))
        self.p.accept(self.state('hand_right', 990_000_000, 1_990_000_000, values=[2.0]*7))
        # Encoding runs on another thread: this sample arrived after the image
        # despite having an older source stamp and being printed first.
        self.p.accept(self.state('joints', 995_000_000, 2_010_000_000, values=[3.0]*20))
        out = self.p.accept(self.frame())
        self.assertEqual(out['state27'], [1.0]*20 + [2.0]*7)
        self.assertEqual(out['received_monotonic_ns']['joint'], 1_980_000_000)
        self.assertEqual(out['joint_source_ns'], 980_000_000)
        self.assertEqual(out['state20_velocity_rad_s'], [0.0]*20)
        self.assertGreater(out['pc_joint_received_monotonic_ns'], 0)

    def test_missing_velocity_preserves_shadow_but_not_a_velocity_claim(self):
        joint = self.state('joints', 980_000_000, 1_980_000_000)
        del joint['message']['velocity']
        self.p.accept(joint)
        self.p.accept(self.state('hand_right', 990_000_000, 1_990_000_000))
        self.assertIsNone(self.p.accept(self.frame())['state20_velocity_rad_s'])

    def test_nonfinite_velocity_is_not_replaced_by_zero(self):
        joint = self.state('joints', 980_000_000, 1_980_000_000)
        joint['message']['velocity'][0] = float('nan')
        with self.assertRaisesRegex(ValueError, 'velocity'):
            self.p.accept(joint)

    def test_skips_future_and_stale_states(self):
        self.p.accept(self.state('joints', 919_999_999, 1_990_000_000))
        self.p.accept(self.state('hand_right', 1_000_000_001, 1_990_000_000))
        self.assertIsNone(self.p.accept(self.frame()))
        self.assertEqual(self.p.dropped, 1)

    def test_rejects_missing_duplicate_and_nonfinite_states(self):
        for names, values in ((self.names[:-1], [0.0]*19),
                              (self.names + [self.names[0]], [0.0]*21),
                              (self.names, [float('nan')] + [0.0]*19),
                              (self.names, [False] + [0.0]*19)):
            with self.assertRaises(ValueError):
                self.p.accept(self.state('joints', 1, 1, names, values))

    def test_rejects_tampered_image_and_non_increasing_stamp(self):
        self.p.accept(self.state('joints', 980_000_000, 1_980_000_000))
        self.p.accept(self.state('hand_right', 980_000_000, 1_980_000_000))
        broken = self.frame(); broken['png_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            self.p.accept(broken)
        with self.assertRaises(ValueError):
            self.p.accept(self.frame())

    def test_requires_valid_collector_lifecycle(self):
        p = Pairer(self.names)
        with self.assertRaises(ValueError): p.accept({'kind': 'ready'})
        p.accept({'kind': 'start', 'movement_commands': 0})
        with self.assertRaises(ValueError):
            p.accept({'kind': 'end', 'movement_commands': 0, 'errors': ['bad'], 'stopped': False})


if __name__ == '__main__':
    unittest.main()
