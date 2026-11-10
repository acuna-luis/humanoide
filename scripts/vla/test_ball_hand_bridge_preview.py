"""Pruebas de enlace simbólico: ninguna prueba controla el robot."""

import unittest

from ball_hand_bridge_preview import BallHandBridgePreview


def record(sequence, stamp, signals, score=0.9):
    digest = 'a' * 64
    return {
        'sequence': sequence,
        'prediction': {'event': 'prediction', 'image_source_ns': stamp,
                       'image_sha256': digest, 'prediction': [0.0] * 7 + [score]},
        'phase_evidence': {'image_source_ns': stamp, 'image_sha256': digest,
                           'signals': signals},
    }


class BallHandBridgePreviewTests(unittest.TestCase):
    def test_model_score_alone_does_not_close(self):
        bridge = BallHandBridgePreview()
        row = bridge.update(record(0, 1, {}, 0.99))
        self.assertEqual(row['simulated_hand_label'], 'open')
        self.assertEqual(row['model_hand_scalar_uninterpreted'], 0.99)
        self.assertIs(row['physical_control_qualified'], False)
        self.assertEqual(row['physical_commands_generated'], 0)

    def test_hold_until_lowered_and_supported_even_if_model_says_open(self):
        bridge = BallHandBridgePreview()
        rows = [
            ({'at_grasp': True, 'close_requested': True}, 'closing', 'closed'),
            ({'closed_confirmed': True}, 'grasped', 'closed'),
            ({'release_requested': True, 'supported_confirmed': True}, 'grasped', 'closed'),
            ({'lift_complete': True}, 'lifted', 'closed'),
            ({'lower_complete': True}, 'lowered', 'closed'),
            ({'release_requested': True}, 'lowered', 'closed'),
            ({'release_requested': True, 'supported_confirmed': True}, 'opening', 'open'),
        ]
        for index, (signals, phase, label) in enumerate(rows):
            result = bridge.update(record(index, index + 1, signals, score=0.01))
            self.assertEqual((result['simulated_phase'], result['simulated_hand_label']), (phase, label))

    def test_mismatch_or_bad_values_rejected_without_advancing(self):
        bridge = BallHandBridgePreview()
        bridge.update(record(0, 1, {}))
        row = record(1, 2, {'at_grasp': True, 'close_requested': True})
        row['phase_evidence']['image_sha256'] = 'b' * 64
        with self.assertRaises(ValueError):
            bridge.update(row)
        row = record(1, 2, {})
        row['phase_evidence']['image_source_ns'] = True
        with self.assertRaises(ValueError):
            bridge.update(row)
        row = record(1, 2, {})
        row['prediction']['prediction'][0] = float('nan')
        with self.assertRaises(ValueError):
            bridge.update(row)
        self.assertEqual(bridge.update(record(1, 2, {}))['simulated_phase'], 'approach')
        with self.assertRaises(ValueError):
            bridge.update(record(2, 2, {}))
        with self.assertRaises(ValueError):
            bridge.update(record(2, 3, {'at_grasp': 1}))
        self.assertEqual(bridge.update(record(2, 3, {}))['simulated_phase'], 'approach')


if __name__ == '__main__':
    unittest.main()
