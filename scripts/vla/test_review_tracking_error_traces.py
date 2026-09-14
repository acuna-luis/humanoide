"""Synthetic failure cases: offline discrepancy is never physical approval."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_tracking_error_traces import review_records, statistics
from test_home_motion_trace import trace


class TrackingTests(unittest.TestCase):
    def test_same_motor_frame_difference_keeps_bias(self):
        records = trace()
        for r in records:
            if r.get('topic') == '/mc/actuator_state':
                for v in r['message']['act_item']:
                    v['position'] = -1.0
                    v['cmd_pos'] = -1.01
        result = review_records(records)
        self.assertAlmostEqual(result['all_samples']['maximum_deg'], .5729577951308232)
        self.assertFalse(result['physical_approval'])
        self.assertFalse(result['servo_tracking_bound_qualified'])

    def test_stationary_axes_are_not_dynamic_coverage(self):
        records = trace()
        for r in records:
            if r.get('topic') == '/mc/actuator_state':
                for v in r['message']['act_item']:
                    v['velocity'] = 0.
        result = review_records(records)
        self.assertEqual(result['substantial_motion_joints'], [])
        self.assertIsNone(result['moving_frame_samples'])
        self.assertIsNone(result['joints']['head_pitch_joint']['moving_joint_samples'])

    def test_peak_is_not_hidden_by_percentile(self):
        result = statistics([.01]*1000+[.6])
        self.assertEqual(result['p99_deg'], .01)
        self.assertEqual(result['maximum_deg'], .6)
        self.assertEqual(result['samples_exceeding']['0.5'], 1)
        self.assertIsNone(statistics([]))

    def test_source_gap_is_detected_even_with_regular_receive_clock(self):
        records = trace()
        last = next(r for r in reversed(records) if r.get('topic') == '/mc/actuator_state')
        last['message']['header']['stamp']['nanosec'] += 60_000_000
        # The fixture shares this stamp with all actuators, maintaining zero skew.
        result = review_records(records)
        self.assertFalse(result['eligible_for_observed_comparison'])
        self.assertTrue(any(x.startswith('source_gap_exceeded:') for x in result['additional_quality_issues']))

    def test_faults_missing_axes_and_corruption_do_not_enter_comparison(self):
        for mode in ('fault', 'missing', 'stale', 'truncated'):
            records = copy.deepcopy(trace())
            if mode == 'fault': records[3]['message']['act_item'][0]['status'] = 8
            if mode == 'missing': records[3]['message']['act_item'].pop()
            if mode == 'stale': records[4]['message'] = copy.deepcopy(records[3]['message'])
            if mode == 'truncated': records.pop()
            with self.subTest(mode=mode):
                result = review_records(records)
                self.assertFalse(result['eligible_for_observed_comparison'])
                self.assertIsNone(result['all_samples'])


if __name__ == '__main__':
    unittest.main()
