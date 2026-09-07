import unittest
from audit_home_group_timing import analyze


class TimingTests(unittest.TestCase):
    def test_offsets_and_warning_not_motion_proof(self):
        report = analyze("""I2026-09-04 19:58:01.000000 BTree task: 'cruzr/home' is start
I2026-09-04 19:58:02.000000 Now move lifter in joint space to: [0 0 0] within 6 s
I2026-09-04 19:58:02.200000 Now move left_arm in joint space to: [0 0 0 0 0 0 0] within 6 s
E2026-09-04 19:58:02.201000 left_arm's 2-th position cmd: 0.11 is over of range: [-1, 0.1]
E2026-09-04 19:58:03.000000 Excessive force detected in 1-th dimension of the left ft sensor: -305.5
E2026-09-04 19:58:03.400000 BTree tick failed
I2026-09-04 19:58:05.000000 Now move head in joint space to: [0 0] within 6 s""")
        self.assertAlmostEqual(report['logged_command_start_spread_s'],.2)
        self.assertEqual(len(report['group_commands']),2)
        self.assertEqual(report['home_start']['madrid_time'],'2026-09-04T13:58:01+02:00')
        self.assertAlmostEqual(report['range_warnings']['left_arm:2']['maximum_excess_rad'],.01)
        self.assertFalse(report['actual_joint_trajectory_reconstructed'])

    def test_missing_or_interrupted_window_not_complete(self):
        for text in ('', "I2026-09-04 19:58:01.000000 BTree task: 'cruzr/home' is start\n"
                     "I2026-09-04 19:58:02.000000 BTree task: 'other' is start\n"
                     "I2026-09-04 19:58:03.000000 BTree tick succeeded"):
            self.assertEqual(analyze(text)['status'],'NO_COMPLETE_FIRST_HOME_WINDOW')


if __name__ == '__main__':
    unittest.main()
