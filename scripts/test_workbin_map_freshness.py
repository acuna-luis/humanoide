"""Regresiones de pose retenida y resultado de navegación contradictorio."""
import copy
from pathlib import Path
import subprocess
import unittest
from lib.cruzr_map_pose_gate import validate_pose
from lib.cruzr_table_drop_profile import validate, record


class FreshPoseTests(unittest.TestCase):
    def sample(self):
        return dict(header=dict(stamp=dict(sec=100, nanosec=100000000), frame_id='map'),
                    pose=dict(position=dict(x=1., y=2., z=0.), orientation=dict(x=0., y=0., z=0., w=1.)))

    def test_valid_fresh_pose(self):
        self.assertEqual(validate_pose(self.sample(), 100.2), (100100000000, (1., 2., 0.)))

    def test_old_and_future_stamps_rejected(self):
        for now in [100.1 + 17000, 104., 99.]:
            with self.assertRaises(ValueError): validate_pose(self.sample(), now)

    def test_bad_geometry_and_frame_rejected(self):
        for section, key, value in [('position', 'x', float('nan')),
                                    ('position', 'y', True), ('orientation', 'w', 0.),
                                    ('orientation', 'x', .2)]:
            msg = self.sample(); msg['pose'][section][key] = value
            with self.assertRaises(ValueError): validate_pose(msg, 100.2)
        msg = self.sample(); msg['header']['frame_id'] = 'odom'
        with self.assertRaises(ValueError): validate_pose(msg, 100.2)

    def test_reference_without_fresh_capture_is_rejected(self):
        report = 'MAP_POSE_FRESHNESS=volatile-stamped-v2\nMAP_FINGERPRINT='+'a'*64+'\nMAP_POSE_REFERENCE=1 2 0\n'
        data = record(report, 'MESAS2', 'uslam', 1.)
        del data['capture_method']
        with self.assertRaises(ValueError): validate(data, 'MESAS2', 'uslam')
        with self.assertRaises(ValueError): record(report.replace('MAP_POSE_FRESHNESS=', 'OTHER='), 'MESAS2', 'uslam', 1.)


class NavigationResultTests(unittest.TestCase):
    def result(self, desc, status=4):
        return "Goal accepted with ID: test\nResult: result=" + repr(dict(
            dmsg='navigation_start SUCCEEDED ,change to FSM_WaitNavigate',
            state=dict(desc=desc, state=0))) + ', status=' + str(status)

    def check(self, output):
        source = Path(__file__).with_name('cruzr_blue_workbin_map_route.sh').read_text()
        function = 'validate_navigation_result() {' + source.split('validate_navigation_result() {', 1)[1].split('\nnavigation_to_free_pose()', 1)[0]
        return subprocess.run(['bash', '-c', function+'\nvalidate_navigation_result "$1"', 'test', output],
                              capture_output=True, text=True)

    def test_vendor_status4_does_not_mask_nested_error(self):
        for desc in ['VSLAM_MAP_DIR_ERROR', 'PLANNING_FAIL', 'LOCATION_LOST', 'START_ONOBSTACLE']:
            self.assertNotEqual(self.check(self.result(desc)).returncode, 0)

    def test_normal_result_and_malformed_results(self):
        self.assertEqual(self.check(self.result('PLANNING_FINISH')).returncode, 0)
        for output in [self.result('PLANNING_FINISH', 6), '', self.result('READY')+'\n'+self.result('READY')]:
            self.assertNotEqual(self.check(output).returncode, 0)

    def arrival(self, current='1 2 0', map_type='uslam', desc='VSLAM_MAP_DIR_ERROR', read_status=0):
        source = Path(__file__).with_name('cruzr_blue_workbin_map_route.sh').read_text()
        functions = 'validate_navigation_result() {' + source.split('validate_navigation_result() {', 1)[1].split('\nnavigation_to_free_pose()', 1)[0]
        check = 'assert_near_pose() {' + source.split('assert_near_pose() {', 1)[1].split('\nverify_start_area()', 1)[0]
        code = '''set -euo pipefail
MODE=navigate-map-pose
MAP_TYPE="$2"
POSE_POSITION_TOLERANCE=.05
POSE_YAW_TOLERANCE=.05
info() { echo "$*"; }
read_stable_map_pose() { echo "$3"; return "$4"; }
'''.replace('echo "$3"; return "$4";', 'echo "$MOCK_CURRENT"; return "$MOCK_STATUS";')
        code += 'MOCK_CURRENT="$3"\nMOCK_STATUS="$4"\n'+check+functions+'\nvalidate_free_navigation_arrival "$1" "1 2 0"\n'
        return subprocess.run(['bash','-c',code,'test',self.result(desc),map_type,current,str(read_status)],capture_output=True,text=True)

    def test_uslam_auxiliary_requires_arrival(self):
        good = self.arrival()
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertIn('NAV_AUXILIARY_WARNING=', good.stdout)
        for current in ['1.1 2 0', '1 2 .1', 'nan 2 0']:
            self.assertNotEqual(self.arrival(current=current).returncode, 0)
        self.assertNotEqual(self.arrival(read_status=42).returncode, 0)

    def test_auxiliary_exception_never_applies_to_fusion_or_other_errors(self):
        for map_type in ['auto','fusion']:
            self.assertNotEqual(self.arrival(map_type=map_type).returncode, 0)
        for desc in ['PLANNING_FAIL','LOCATION_LOST','START_ONOBSTACLE','VSLAM_OTHER_ERROR']:
            self.assertNotEqual(self.arrival(desc=desc).returncode, 0)


if __name__ == '__main__':
    unittest.main()
