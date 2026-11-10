"""Tests de la secuencia simbólica de mano, sin dependencias del robot."""

import unittest

from ball_hand_phase_policy import BallHandPhasePolicy


class BallHandPhasePolicyTests(unittest.TestCase):
    def test_open_until_both_position_and_close_request(self):
        machine = BallHandPhasePolicy()
        self.assertEqual(machine.update(0, {})['symbolic_hand_goal'], 'open')
        self.assertEqual(machine.update(1, {'close_requested': True})['phase'], 'approach')
        self.assertEqual(machine.update(2, {'at_grasp': True})['phase'], 'approach')
        result = machine.update(3, {'at_grasp': True, 'close_requested': True})
        self.assertEqual((result['phase'], result['symbolic_hand_goal']), ('closing', 'closed'))
        self.assertIs(result['physical_control_qualified'], False)
        self.assertEqual(result['physical_commands_generated'], 0)

    def test_closed_during_lift_and_lower_even_if_release_is_requested(self):
        machine = BallHandPhasePolicy()
        machine.update(0, {'at_grasp': True, 'close_requested': True})
        for seq, signals, phase in (
            (1, {'release_requested': True, 'supported_confirmed': True}, 'closing'),
            (2, {'closed_confirmed': True}, 'grasped'),
            (3, {'release_requested': True, 'supported_confirmed': True}, 'grasped'),
            (4, {'lift_complete': True}, 'lifted'),
            (5, {'release_requested': True, 'supported_confirmed': True}, 'lifted'),
            (6, {'lower_complete': True}, 'lowered'),
            (7, {'release_requested': True}, 'lowered'),
            (8, {'supported_confirmed': True}, 'lowered'),
        ):
            result = machine.update(seq, signals)
            self.assertEqual((result['phase'], result['symbolic_hand_goal']), (phase, 'closed'))
        result = machine.update(9, {'release_requested': True, 'supported_confirmed': True})
        self.assertEqual((result['phase'], result['symbolic_hand_goal']), ('opening', 'open'))
        self.assertEqual(machine.update(10, {'open_confirmed': True})['phase'], 'complete')
        self.assertEqual(machine.update(11, {'at_grasp': True, 'close_requested': True})['phase'], 'complete')

    def test_no_skipping_phases_or_implicit_confirmation(self):
        machine = BallHandPhasePolicy()
        all_signals = {'at_grasp': True, 'close_requested': True, 'closed_confirmed': True,
                       'lift_complete': True, 'lower_complete': True, 'release_requested': True,
                       'supported_confirmed': True, 'open_confirmed': True}
        self.assertEqual(machine.update(0, all_signals)['phase'], 'closing')
        self.assertEqual(machine.update(1, {})['phase'], 'closing')
        self.assertEqual(machine.update(2, {'lower_complete': True})['phase'], 'closing')

    def test_invalid_or_duplicate_inputs_do_not_change_state(self):
        machine = BallHandPhasePolicy()
        machine.update(0, {})
        with self.assertRaises(ValueError):
            machine.update(0, {'at_grasp': True, 'close_requested': True})
        with self.assertRaises(ValueError):
            machine.update(1, {'at_grasp': 1, 'close_requested': True})
        with self.assertRaises(ValueError):
            machine.update(1, {'score': 0.9})
        self.assertEqual(machine.update(1, {})['phase'], 'approach')


if __name__ == '__main__':
    unittest.main()
