"""No robot connections: frame transforms, freshness and script boundary."""
import copy
import math
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.box_handling.probe_front_box import transform_poses, validate_detection


class ProbeTest(unittest.TestCase):
    def result(self):
        return {'ok': True, 'trans_outputs': {'camera_name': 'head',
            'object_name': 'workbin', 'box_pose': {'header': {
                'frame_id': 'stereo_left_rectified_optical_frame',
                'stamp': {'sec': 100, 'nanosec': 0}}, 'poses': []}}}

    def test_exact_fresh_detection_is_accepted(self):
        _, stamp = validate_detection(self.result(), 4, 100_100_000_000, 99_900_000_000)
        self.assertEqual(stamp, 100_000_000_000)

    def test_stale_future_and_previous_request_are_rejected(self):
        for now, request in ((103, 99.9), (99.9, 99.9), (101, 100.8)):
            with self.assertRaises(ValueError):
                validate_detection(self.result(), 4, int(now*1e9), int(request*1e9))

    def test_failed_goal_and_wrong_camera_or_frame_are_rejected(self):
        for field, value in (('camera_name', 'waist_front'), ('object_name', 'unknown')):
            r = self.result()
            r['trans_outputs'][field] = value
            with self.assertRaises(ValueError):
                validate_detection(r, 4, 100_100_000_000, 99_900_000_000)
        for status, ok in ((6, True), (4, False)):
            r = self.result(); r['ok'] = ok
            with self.assertRaises(ValueError):
                validate_detection(r, status, 100_100_000_000, 99_900_000_000)
        r = self.result(); r['trans_outputs']['box_pose']['header']['frame_id'] = ''
        with self.assertRaises(ValueError):
            validate_detection(r, 4, 100_100_000_000, 99_900_000_000)

    def test_rotation_translation_and_orientation_preserve_source(self):
        poses = [{'position': dict(x=1., y=0., z=2.),
                  'orientation': dict(x=0., y=0., z=0., w=1.)}]
        before = copy.deepcopy(poses)
        half = math.sqrt(.5)
        tf = {'translation': dict(x=.2, y=.3, z=.4),
              'rotation': dict(x=0., y=0., z=half, w=half)}
        p = transform_poses(poses, tf)[0]
        for k, expected in zip('xyz', (.2, 1.3, 2.4)):
            self.assertAlmostEqual(p['position'][k], expected)
        self.assertAlmostEqual(p['orientation']['z'], half)
        self.assertEqual(poses, before)
        tf['rotation']['w'] = 0.
        with self.assertRaises(ValueError):
            transform_poses(poses, tf)

    def test_default_script_stops_before_ssh_or_any_motion(self):
        script = Path(__file__).resolve().parents[1] / 'force_escenario1.sh'
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / 'external-call'
            for name in ('ssh', 'setsid', 'docker', 'rosa'):
                p = Path(tmp) / name
                p.write_text('#!/bin/sh\ntouch "'+str(marker)+'"\nexit 99\n')
                p.chmod(0o755)
            env = dict(os.environ, PATH=tmp+os.pathsep+os.environ['PATH'])
            env.pop('CRUZR_INTERNAL_ASKPASS', None)
            r = subprocess.run(['bash', str(script)], env=env, capture_output=True,
                               text=True, timeout=3)
            self.assertEqual(r.returncode, 78)
            self.assertIn('CONFIRMACION_FISICA_REQUERIDA', r.stderr)
            self.assertFalse(marker.exists())


if __name__ == '__main__':
    unittest.main()
