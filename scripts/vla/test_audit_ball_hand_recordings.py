"""Pruebas puras de auditoría de comandos de mano grabados."""
import hashlib
import io
import json
import unittest

from audit_ball_hand_recordings import analyze, RIGHT_HAND, FIELDS


def command(mode, torque):
    msg = {'names': RIGHT_HAND, 'mode': [mode] * 7}
    msg.update({field: [0.0] * 7 for field in FIELDS})
    msg['torque'] = torque
    return {'kind': 'hand_command_right', 'message': msg}


def stream(rows):
    return ''.join(json.dumps(row) + '\n' for row in rows).encode()


class RecordingAuditTests(unittest.TestCase):
    def test_counts_and_shared_torque_across_different_modes(self):
        rows = [{'kind': 'hand_right'}, command(5, [1.1] * 7), command(7, [1.1] * 7),
                command(7, [0.0] * 7)]
        data = stream(rows)
        result = analyze(io.BytesIO(data))
        self.assertEqual(result['samples_sha256'], hashlib.sha256(data).hexdigest())
        self.assertEqual(result['right_hand_state_messages'], 1)
        self.assertEqual(result['right_hand_command_messages'], 3)
        self.assertEqual(result['invalid_commands'], 0)
        self.assertEqual(len(result['shared_torque_vectors']), 1)
        self.assertEqual(result['shared_torque_vectors'][0]['counts'], [1, 1])
        self.assertFalse(result['physical_control_qualified'])
        self.assertEqual(result['physical_commands_generated'], 0)

    def test_bad_fields_are_counted_without_becoming_evidence(self):
        invalid = command(5, [0.0] * 7)
        invalid['message']['torque'][0] = float('nan')
        result = analyze(io.BytesIO(stream([invalid])))
        self.assertEqual(result['invalid_commands'], 1)
        self.assertEqual(result['mode_counts'], [])

    def test_empty_acceleration_is_recorded_without_inventing_values(self):
        row = command(7, [1.1] * 7)
        row['message']['acceleration'] = []
        result = analyze(io.BytesIO(stream([row])))
        self.assertEqual(result['acceleration_length_counts'], {'0': 1})
        self.assertEqual(result['invalid_commands'], 0)
        self.assertFalse(result['physical_control_qualified'])

    def test_malformed_or_truncated_records_are_rejected(self):
        for data in (b'{}', b'[]\n', b'{\n'):
            with self.subTest(data=data), self.assertRaises(ValueError):
                analyze(io.BytesIO(data))


if __name__ == '__main__':
    unittest.main()
