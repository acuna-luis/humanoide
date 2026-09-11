"""Offline regressions for coordinate conventions and coherent entry selection."""
import copy
import json
import math
from pathlib import Path
import unittest

import rank_vla_entry_postures as review

ROOT = Path(__file__).resolve().parents[2]


class EntryReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads((ROOT / 'scripts/vla/runtime/cruzr_s2_vla_task0_entry_e6_1a.json').read_text())
        cls.joints = review.load_joints(ROOT / 'cruzr_s2_description_splint/cruzr_s2_description/urdf/cruzr_s2_v1/cruzr_s2_v1.urdf')

    def report(self):
        records = []
        for episode, lifter in [('episode_000040', [-.8, 0., .3]),
                                ('upright', [-1., .4, .6])]:
            state = [0.] * 20
            state[16:19] = lifter
            records.append(dict(episode=episode, task=0, state=state, action=state.copy()))
        return dict(schema='cruzr-s2-vla-dataset-entry-states-v1',
                    joint_names=self.contract['joint_order'], episode_count=2,
                    frame_zero_records=records)

    def test_yaw_is_not_tilt(self):
        tilt, _ = review.torso_metrics(self.joints, {'waist_yaw_joint': 1.2})
        self.assertLess(tilt, .001)

    def test_cancelling_lifter_angles_keep_torso_upright(self):
        tilt, _ = review.torso_metrics(self.joints, dict(
            lifter_pitch_1_joint=-1., lifter_pitch_2_joint=.4, lifter_pitch_3_joint=.6))
        self.assertLess(tilt, .001)

    def test_combined_lifter_tilt_not_first_joint_angle(self):
        tilt, _ = review.torso_metrics(self.joints, dict(
            lifter_pitch_1_joint=-.8, lifter_pitch_3_joint=.3))
        self.assertAlmostEqual(tilt, math.degrees(.5), places=4)

    def test_preserves_whole_frame_and_no_authorization(self):
        report = self.report()
        original = copy.deepcopy(report)
        result = review.analyze(report, self.contract, self.joints)
        self.assertEqual(result['candidate_count'], 1)
        self.assertEqual(result['shortlist'][0]['state'], report['frame_zero_records'][1]['state'])
        self.assertFalse(result['physical_execution_authorized'])
        self.assertEqual(report, original)

    def test_joint_order_mismatch_rejected(self):
        report = copy.deepcopy(self.report())
        report['joint_names'][0:2] = report['joint_names'][1::-1]
        with self.assertRaises(ValueError):
            review.analyze(report, self.contract, self.joints)

    def test_nonfinite_partial_and_duplicate_data_rejected(self):
        for defect in ('nan', 'short', 'duplicate'):
            with self.subTest(defect=defect):
                report = self.report()
                if defect == 'nan':
                    report['frame_zero_records'][0]['action'][0] = float('nan')
                elif defect == 'short':
                    report['frame_zero_records'][0]['state'].pop()
                else:
                    report['frame_zero_records'][1]['episode'] = 'episode_000040'
                with self.assertRaises(ValueError):
                    review.analyze(report, self.contract, self.joints)

    def test_out_of_limits_upright_frame_not_shortlisted(self):
        report = self.report()
        report['frame_zero_records'][1]['state'][0] = 100.
        result = review.analyze(report, self.contract, self.joints)
        self.assertEqual(result['candidate_count'], 0)

    def test_other_tasks_are_not_substituted(self):
        report = self.report()
        report['frame_zero_records'][1]['task'] = 2
        result = review.analyze(report, self.contract, self.joints)
        self.assertEqual(result['task_episode_count'], 1)
        self.assertEqual(result['candidate_count'], 0)


if __name__ == '__main__':
    unittest.main()
