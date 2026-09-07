import unittest
from audit_clamp_pessimistic_path import named_arms, stages, interpolated, summarize_minima


class PathTests(unittest.TestCase):
    def test_mapping_is_named_not_meta_order(self):
        state = named_arms(list(range(14)))
        self.assertEqual(state['L_elbow_roll_joint'], 0)
        self.assertEqual(state['L_shoulder_pitch_joint'], 2)
        self.assertEqual(state['R_wrist_roll_joint'], 13)
        for bad in ([0]*13, [True]*14, [float('nan')]*14):
            with self.assertRaises(ValueError):
                named_arms(bad)

    def test_return_and_serialized_intermediate(self):
        joints = [{'name': k, 'type': 'revolute'} for k in named_arms([0]*14)]
        joints.append({'name': 'head_yaw_joint', 'type': 'revolute'})
        ready = {'arm_path_checkpoint_order': {k: [v]*14 for k, v in
                 [('staging_preposition', .1), ('waypoint_a', .2), ('ready_b', .3)]}}
        for mode, count in [('synchronous', 7), ('L_then_R', 13), ('R_then_L', 13)]:
            points = stages(joints, ready, mode)
            self.assertEqual(len(points), count)
            self.assertEqual(points[0][1], points[-1][1])
            self.assertTrue(all(state['head_yaw_joint'] == 0 for _, state in points))
        first = stages(joints, ready, 'L_then_R')[1][1]
        self.assertEqual(first['L_shoulder_pitch_joint'], .1)
        self.assertEqual(first['R_shoulder_pitch_joint'], 0)

    def test_interpolation_endpoints(self):
        values = list(interpolated({'a': 0}, {'a': 1}, 3))
        self.assertEqual(values, [(0, {'a': 0}), (.5, {'a': .5}), (1, {'a': 1})])
        with self.assertRaises(ValueError):
            list(interpolated({'a': 0}, {'b': 1}, 3))
        for value in (True, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                list(interpolated({'a': 0}, {'a': value}, 3))

    def test_clamp_pair_uses_two_radii_and_overlap_is_inconclusive(self):
        data = {'clamp_clamp': {'distance_m': .3}, 'L_body': {'distance_m': .3}}
        result = summarize_minima(data, .2)
        self.assertAlmostEqual(result['clamp_clamp']['envelope_gap_m'], -.1)
        self.assertEqual(result['clamp_clamp']['result'], 'OVERLAP_INCONCLUSIVE')
        self.assertAlmostEqual(result['L_body']['envelope_gap_m'], .1)


if __name__ == '__main__':
    unittest.main()
