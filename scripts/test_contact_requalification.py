#!/usr/bin/env python3
"""Local regressions: no robot network or process is allowed in tested modes."""
import copy
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from audit_clamp_mount_requalification import mount_bounds, reported_front_profile, reported_plate_volume, evaluate
from audit_clamp_sensor_reference import boundary_loops, rotation_residual

ROOT = Path(__file__).resolve().parents[1]


class RequalificationTests(unittest.TestCase):
    def test_retired_transition_cannot_regenerate_pass(self):
        for mode in ('--check', '--run'):
            result = subprocess.run(['bash', str(ROOT/'scripts/vla/audit_vla_ready_entry_transition_e6_1c.sh'), mode],
                                    capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 78, result.stderr)
            self.assertIn('BLOCKED_RETIRED_UNREGISTERED_CLAMP_GEOMETRY', result.stderr)
            self.assertNotIn('PASS_OFFLINE', result.stdout)
        options = ('contract', 'entry-contract', 'ready-source', 'entry-xml',
                   'recovery-xml', 'e6-1a-report', 'sdk-urdf', 'sdk-urdf-zip',
                   'document-proxy-report', 'fk-helper', 'path-helper',
                   'mesh-helper', 'geometry-helper')
        with tempfile.TemporaryDirectory(prefix='cruzr-retired-analysis-') as directory:
            output = Path(directory)/'report.json'
            command = ['python3', str(ROOT/'scripts/vla/analyze_vla_ready_entry_transition_e6_1c.py')]
            for option in options:
                command.extend(['--'+option, str(Path(directory)/'must_not_be_read')])
            command.extend(['--output', str(output)])
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 78, result.stderr)
            report = json.loads(output.read_text())
            self.assertFalse(report['gates']['offline_geometry_and_limits_pass'])
            self.assertFalse(report['physical_execution_authorized'])
            self.assertFalse(report['historical_analysis_executed'])
            before = output.read_bytes()
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_bytes(), before)

    def test_cad_boundary_and_rotation_ambiguity(self):
        a, b, c, d = (0,0,0), (.01,0,0), (.01,.01,0), (0,.01,0)
        self.assertEqual(boundary_loops([(a,b,c), (a,c,d)]),
                         [dict(center_mm=[5,5], size_mm=[10,10], closed=True)])
        points = [(math.cos(math.radians(t)), math.sin(math.radians(t)))
                  for t in (0,120,240)]
        self.assertLess(rotation_residual(points, 120), 1e-12)
        self.assertGreater(rotation_residual(points, 180), .9)
        with self.assertRaises(ValueError):
            rotation_residual([], 120)

    def test_plate_depth_and_partial_scope(self):
        d = json.loads((ROOT/'config/clamp_mount_requalification.json').read_text())['reported_dimensions']
        volume = reported_plate_volume(d)
        self.assertEqual(volume['status'], 'REPORTED_PLATE_VOLUME_NOT_FULL_TOOL')
        self.assertAlmostEqual(volume['depth_from_sensor_axis_toward_pads_m'][0], 0.059)
        self.assertEqual(volume['depth_from_sensor_axis_toward_pads_m'][1], 0.095)
        self.assertEqual(volume['plain_plate_with_pads_size_m'], [0.07, 0.1, 0.036])
        self.assertFalse(volume['support_fasteners_and_uncertainty_included'])
        self.assertFalse(volume['physical_authorized'])
        for invalid in (None, float('nan'), -0.036, True):
            altered = dict(d, plate_with_pads_thickness_m=invalid)
            self.assertEqual(reported_plate_volume(altered)['status'], 'INCOMPLETE_DEPTH')
        self.assertEqual(reported_plate_volume(dict(d, plate_with_pads_thickness_m=0.1))['status'],
                         'UNREVIEWED_DEPTH_CROSSES_SENSOR_AXIS')

    def test_reported_profile_does_not_authorize_mount(self):
        contract = json.loads((ROOT/'config/clamp_mount_requalification.json').read_text())
        profile = reported_front_profile(contract['reported_dimensions'])
        self.assertEqual(profile['status'], 'REPORTED_2D_PROFILE_ONLY')
        for got, expected in zip(profile['u_bounds_m'], [-0.035, 0.047]):
            self.assertAlmostEqual(got, expected)
        self.assertEqual(profile['v_bounds_m'], [-0.055, 0.045])
        self.assertAlmostEqual(profile['outer_width_m'], 0.082)
        self.assertFalse(profile['physical_authorized'])
        self.assertEqual(evaluate(contract)['status'], 'BLOCKED_MOUNT_INPUTS')
        d = copy.deepcopy(contract['reported_dimensions'])
        d['plate_height_directly_remeasured_m'] = 0.105
        self.assertEqual(reported_front_profile(d)['status'], 'INCONSISTENT_HEIGHT')
        d['plate_width_m'] = float('nan')
        self.assertEqual(reported_front_profile(d)['status'], 'INCOMPLETE_DIMENSIONS')

    def test_motion_entrypoints_denied_before_network(self):
        cases = [
            ('scripts/vla/install_vla_recovery_task_e6_0n.sh', ['--install-on-disk']),
            ('scripts/vla/reload_vla_recovery_task_e6_0o.sh', ['--reload']),
            ('scripts/vla/patch_vla_ready_s2_waist_e6_0p.sh', ['--apply-live']),
            ('scripts/vla/patch_vla_ready_s2_waist_e6_0p.sh', ['--restore-vendor']),
            ('scripts/vla/install_vla_ready_entry_tasks_e6_1c.sh', ['--install-on-disk']),
            ('scripts/vla/reload_vla_ready_entry_tasks_e6_1c.sh', ['--reload']),
            ('scripts/cruzr_recover_to_home.sh', ['--run', '--yes', '--fast']),
            ('scripts/vla/run_vla_ready_entry_transition_e6_1c.sh', ['--entry']),
            ('scripts/vla/run_vla_ready_entry_transition_e6_1c.sh', ['--recover-ready']),
            ('scripts/vla/run_vla_canary_physical_e6_0y.sh', ['--recover']),
            ('scripts/upgrade/cruzr_v020_boot_guard.sh', ['--run']),
        ] + [('scripts/cruzr_blue_workbin_cycle.sh', ['--'+mode, '--yes', '--fast'])
             for mode in ('run', 'grasp', 'deposit-held', 'home', 'home-workbin-internal',
                          'prepare-vision', 'grasp-after-approach')]
        with tempfile.TemporaryDirectory(prefix='cruzr-lock-test-') as temp:
            sandbox = Path(temp)
            for command in ('ssh', 'scp', 'nc', 'docker', 'rosa', 'ros2', 'systemctl', 'setsid'):
                script = sandbox / command
                script.write_text('#!/bin/sh\necho UNEXPECTED_EXTERNAL_COMMAND >&2\nexit 99\n')
                script.chmod(0o700)
            env = dict(os.environ, PATH=str(sandbox)+os.pathsep+os.environ['PATH'],
                       CRUZR_INTERNAL_ASKPASS='0', CONTACT_INCIDENT_LOCK='0',
                       CRUZR_FORCE='1', CRUZR_ALLOW_MOTION='1')
            for path, args in cases:
                with self.subTest(path=path, args=args):
                    result = subprocess.run(['bash', str(ROOT/path), *args], env=env,
                                            capture_output=True, text=True, timeout=5)
                    self.assertEqual(result.returncode, 78, result.stderr)
                    self.assertIn('CONTACT_INCIDENT_LOCK=', result.stderr)
                    self.assertNotIn('UNEXPECTED_EXTERNAL_COMMAND', result.stderr)

    def mount(self):
        return dict(parent_frame='L_sixforce_link', translation_m=[1, 0, 0],
                    rotation_matrix=[[0, -1, 0], [1, 0, 0], [0, 0, 1]],
                    local_bounds_m=[[0, 0, 0], [2, 1, 1]], uncertainty_m=0.01,
                    includes_tabs_fasteners_and_support=True)

    def test_measured_transform_not_proxy_center(self):
        self.assertEqual(mount_bounds(self.mount(), 'L'), [[-0.01, -0.01, -0.01], [1.01, 2.01, 1.01]])

    def test_unknown_and_invalid_geometry_rejected(self):
        changes = dict(translation_m=None, rotation_matrix=[[1,0,0],[0,1,0],[0,0,-1]],
                       uncertainty_m=float('nan'), includes_tabs_fasteners_and_support=False,
                       local_bounds_m=[[0,0,0],[0,1,1]], parent_frame='R_sixforce_link')
        for key, value in changes.items():
            with self.subTest(key=key):
                mount = copy.deepcopy(self.mount())
                mount[key] = value
                with self.assertRaises(ValueError):
                    mount_bounds(mount, 'L')


if __name__ == '__main__':
    unittest.main()
