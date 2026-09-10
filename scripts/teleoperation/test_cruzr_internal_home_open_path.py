import sys
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cruzr_internal_home_open_path as path
from cruzr_pico_to_home_owner_gate import JOINT_ORDER


class InternalHomeTests(unittest.TestCase):
    def test_opening_preserves_all_other_angles_including_asymmetry(self):
        for start in [*path.REVIEW_STARTS.values(), [i/50 for i in range(20)]]:
            points = path.waypoints(start)
            for i in range(20):
                self.assertAlmostEqual(points[1][i]-start[i], -0.4 if i in (3, 10) else 0)
            self.assertEqual(points[2][14:], start[14:])
            self.assertEqual(points[3][3], -0.6)
            self.assertEqual(points[3][10], -0.6)
            self.assertEqual(points[-1], [0.0]*20)

    def test_xml_commands_reproduce_model_for_each_start_and_timing(self):
        for seconds in (20, 6):
            tree = path.xml_tree(seconds)
            stages = tree.findall('.//Parallel')
            self.assertEqual(len(stages), 4)
            self.assertAlmostEqual(sum(float(s[0].get('duration')) for s in stages), seconds)
            for start in path.REVIEW_STARTS.values():
                state = dict(zip(JOINT_ORDER, start))
                for stage, expected in zip(stages, path.waypoints(start)[1:]):
                    self.assertEqual(int(stage.get('threshold')), len(stage))
                    for action in stage:
                        kind, loc = action.get('type'), action.get('location')
                        if kind == 'arm':
                            side = {'left':'L', 'right':'R'}[loc]
                            names = [side+'_'+n+'_joint' for n in path.META_ARM_NAMES]
                        else:
                            names = {'head':['head_yaw_joint','head_pitch_joint'],
                                'lifter':['lifter_pitch_1_joint','lifter_pitch_2_joint','lifter_pitch_3_joint'],
                                'waist':['waist_yaw_joint']}[kind]
                        delta = 'delta_joint_angles' in action.attrib
                        values = [float(x) for x in action.get('delta_joint_angles' if delta else 'joint_angles').split(';')]
                        self.assertEqual(len(values), len(names))
                        for name, value in zip(names, values):
                            state[name] = state[name]+value if delta else value
                    self.assertEqual([state[n] for n in JOINT_ORDER], expected)

    def test_no_pico_lift_from_down(self):
        for start in [path.REVIEW_STARTS['arms_down_body_zero'], path.REVIEW_STARTS['arms_down_body_flexed']]:
            for q in path.waypoints(start):
                for i in range(14):
                    if i not in (3,10): self.assertEqual(q[i], 0)

    def test_wrong_xml_and_invalid_inputs_are_rejected(self):
        for seconds in (20, 6):
            path.validate_xml(path.xml_bytes(seconds), seconds)
        with self.assertRaises(ValueError): path.validate_xml(path.xml_bytes(6), 20)
        bad = path.xml_tree()
        bad.find('.//Parallel').set('threshold', '1')
        with self.assertRaises(ValueError): path.validate_xml(ET.tostring(bad))
        for value in (True, 0, -1, 6.0, 21):
            with self.assertRaises(ValueError): path.xml_tree(value)
        for q in ([0.0]*19, [float('nan')]*20, [True]*20):
            with self.assertRaises(ValueError): path.waypoints(q)


if __name__ == '__main__':
    unittest.main()
