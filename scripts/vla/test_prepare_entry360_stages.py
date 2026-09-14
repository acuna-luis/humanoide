import unittest
import xml.etree.ElementTree as ET
import numpy as np
from prepare_entry360_stages import staged_path, stage_xml, check_runtime_limits, JOINT_ORDER, GROUPS


class EntryStagesTests(unittest.TestCase):
    def test_only_one_group_changes_and_reverse_restores_endpoint(self):
        a, b = np.arange(20)/1000, np.linspace(-.6, 1.2, 20)
        points, stages = staged_path(a, b)
        np.testing.assert_array_equal(points[0], a)
        np.testing.assert_array_equal(points[-1], b)
        for i, stage in enumerate(stages):
            indices = [JOINT_ORDER.index(n) for n in stage['joint_names']]
            others = [j for j in range(20) if j not in indices]
            np.testing.assert_array_equal(points[i][others], points[i+1][others])
            self.assertLessEqual(stage['peak_velocity_rad_s'], .05)
            self.assertLessEqual(stage['peak_acceleration_rad_s2'], .05)
            for reverse in (False, True):
                root = ET.fromstring(stage_xml(stage, reverse))
                self.assertEqual(len(root.findall('.//Action')), 1)
                actual = [float(v) for v in root.find('.//Action').get('joint_angles').split(';')]
                np.testing.assert_array_equal(actual, points[i if reverse else i+1][indices])

    def test_nonfinite_endpoint_rejected(self):
        with self.assertRaises(ValueError):
            staged_path(np.zeros(20), np.full(20, np.nan))

    def test_mismatched_runtime_and_out_of_limit_error_box_rejected(self):
        paths = ['/opt/walker/manipulation_platforms/share/manipulation_platforms/config/'+p
                 for p in ('cruzr_s2_robot_description.yaml', 'urdf/cruzr_s2.urdf')]
        hashes = {p:'a'*64 for p in paths}
        limits = dict(position_intersection_rad=[-.5, .5], minimum_positive_configured_velocity_rad_s=.78,
                      yaml_acceleration_rad_s2=10.)
        contract = dict(source_sha256={'/archive/runtime'+p:h for p, h in hashes.items()},
                        limits={n:limits for typ, _, names in GROUPS if typ != 'arm' for n in names})
        points, stages = staged_path(np.zeros(20), np.full(20, .49))
        self.assertTrue(check_runtime_limits(contract, hashes, points, stages, .005)['configuration_files_match_current_hashes'])
        with self.assertRaises(ValueError):
            check_runtime_limits(contract, hashes, points, stages, .02)
        with self.assertRaises(ValueError):
            check_runtime_limits(contract, dict(hashes, **{paths[0]:'b'*64}), points, stages, .005)


if __name__ == '__main__':
    unittest.main()
