import unittest
import numpy as np
import refine_home_ready_witnesses as audit


class WitnessTests(unittest.TestCase):
    def setUp(self):
        self.joints = [dict(name=s+'_'+n+'_joint', type='revolute')
                       for s in ('L', 'R') for n in audit.screen.ORDER]
        self.joints += [dict(name=n, type='revolute') for n in ('head_pitch_joint', 'head_yaw_joint')]
        self.points = audit.screen.stages()

    def test_staging(self):
        q = audit.witness_state(self.joints, self.points, dict(stage=0, fraction=1.,
             schedule='simultaneous', head_hypothesis='head_pitch_joint'))
        self.assertEqual(q['L_shoulder_roll_joint'], -.6)
        self.assertEqual(q['R_shoulder_roll_joint'], -.6)
        self.assertEqual(q['head_pitch_joint'], -.65)

    def test_bad_schedule(self):
        with self.assertRaises(ValueError):
            audit.witness_state(self.joints, self.points, dict(stage=0, fraction=.5,
                schedule='unknown', head_hypothesis='head_pitch_joint'))

    def test_candidate_explicit_and_reversible(self):
        candidate = audit.head_hold_candidate(self.joints, self.points)
        self.assertFalse(candidate['physical_authorized'])
        self.assertIsNone(candidate['durations'])
        self.assertEqual(candidate['waypoints'], list(reversed(candidate['waypoints'])))
        for q, expected in zip(candidate['waypoints'], self.points):
            self.assertEqual(q['head_pitch_joint'], 0.)
            self.assertEqual(q['head_yaw_joint'], 0.)
            np.testing.assert_array_equal([q[s+'_'+n+'_joint'] for s in ('L', 'R')
                for n in audit.screen.ORDER], expected)


if __name__ == '__main__':
    unittest.main()
