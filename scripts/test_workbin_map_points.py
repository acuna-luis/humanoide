"""Exercise the actual remote validator locally; no SSH or robot commands."""
import base64
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


SOURCE = Path(__file__).with_name('cruzr_blue_workbin_map_route.sh').read_text()
VALIDATOR = SOURCE.split('"$encoded_waypoint" <<\'PY\'\n', 1)[1].split('\nPY\n', 1)[0]
HISTORICAL = ['START', 'PASO1', 'PASO2', 'PASO 3', 'PASO4', 'FINISH']


def point(name):
    return dict(id=name, mode='logo_nav', point_x=1.0, point_y=2.0, point_yaw=0.5)


class MapPointsTests(unittest.TestCase):
    def check_map(self, points, tasks, destination):
        encoded = base64.b64encode(destination.encode()).decode() if destination else 'NONE'
        with tempfile.TemporaryDirectory() as tmp:
            files = [Path(tmp) / name for name in ['umap.json', 'task.json']]
            for file, values in zip(files, [points, tasks]):
                file.write_text(json.dumps({'target_points': values}))
            return subprocess.run(['python3', '-c', VALIDATOR, *map(str, files), encoded],
                                  capture_output=True, text=True)

    def test_transfer_with_empty_task_route(self):
        result = self.check_map([point('MESA2_PRE')], [], 'MESA2_PRE')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('MAP_POINTS_AVAILABLE=MESA2_PRE', result.stdout)

    def test_numeric_reference_needs_no_waypoints(self):
        with tempfile.TemporaryDirectory() as tmp:
            files = [Path(tmp)/name for name in ['umap.json','task.json']]
            for file in files: file.write_text('{"target_points": []}')
            result = subprocess.run(['python3','-c',VALIDATOR,*map(str,files),'POSE_ONLY'],
                                    capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('MAP_VALIDATION=taught-pose',result.stdout)

    def test_arbitrary_direct_destination(self):
        result = self.check_map([point('Mesa 1')], [], 'Mesa 1')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_mapping_marker_saved_by_ui(self):
        marker = dict(point('MESA2_PRE'), mode='', type='mapping_marker')
        self.assertEqual(self.check_map([marker], [], 'MESA2_PRE').returncode, 0)
        marker['type'] = 'unknown'
        self.assertNotEqual(self.check_map([marker], [], 'MESA2_PRE').returncode, 0)

    def test_empty_mode_alone_is_not_accepted(self):
        marker = dict(point('MESA2_PRE'), mode='')
        self.assertNotEqual(self.check_map([marker], [], 'MESA2_PRE').returncode, 0)

    def test_mapping_marker_dispatches_coordinate_goal_without_ssh(self):
        function = SOURCE.split('navigation_to_point() {', 1)[1].split('\nassert_waypoint_available()', 1)[0]
        shell = '''set -euo pipefail
info() { printf '%s\\n' "$*"; }
assert_waypoint_available() {
  printf 'WAYPOINT_NAVIGATION=free_nav\\nWAYPOINT_POSE=-0.27859741587292997 0.8867166475657804 1.6781991390323905\\n'
}
navigation_to_free_pose() { printf 'MOCK_GOAL=%s LABEL=%s\\n' "$1" "$2"; }
ssh_vision() { exit 91; }
'''
        result = subprocess.run(['bash', '-c', shell + 'navigation_to_point() {' + function
                                 + '\nnavigation_to_point MESA2_PRE TEST'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('MOCK_GOAL=-0.27859741587292997 0.8867166475657804 1.6781991390323905 LABEL=MESA2_PRE', result.stdout)

    def test_missing_destination(self):
        result = self.check_map([point('MESA1_PRE')], [], 'MESA2_PRE')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Falta el waypoint', result.stderr)

    def test_invalid_destination(self):
        for field, value in [('point_yaw', float('nan')), ('point_x', True),
                             ('point_y', None), ('mode', 'free_nav')]:
            with self.subTest(field=field):
                item = point('MESA2_PRE'); item[field] = value
                self.assertNotEqual(self.check_map([item], [], 'MESA2_PRE').returncode, 0)

    def test_duplicate_destination(self):
        self.assertNotEqual(self.check_map([point('MESA2_PRE')] * 2, [], 'MESA2_PRE').returncode, 0)

    def test_historical_route_still_required(self):
        points = [point(name) for name in HISTORICAL]
        self.assertEqual(self.check_map(points, points, '').returncode, 0)
        self.assertNotEqual(self.check_map(points, [], '').returncode, 0)


if __name__ == '__main__':
    unittest.main()
