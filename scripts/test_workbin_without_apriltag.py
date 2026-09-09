#!/usr/bin/env python3
"""Variante sin tags: planes y flujo real con todos los hijos simulados."""
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))
import test_workbin_table_transfer as fixtures
from lib.cruzr_table_drop_profile import validate, offset, approach_steps, record, remaining_steps, forward_distance

SCRIPTS = Path(__file__).parent


def example(distance=1.0):
    return dict(version=1, capture_method='volatile-stamped-v2', map_name='MESAS2', map_type='uslam', map_fingerprint='a'*64,
                drop_pose_m_rad=[1., 2., 0.], approach_distance_m=distance,
                position_tolerance_m=.05, yaw_tolerance_rad=.05,
                recorded_at_utc='2026-09-09T10:00:00+00:00')


class ProfileTests(unittest.TestCase):
    def test_remaining_plan_and_recomputed_distance(self):
        data = example()
        steps = remaining_steps(data, [.053, 2.019, -.025])
        self.assertAlmostEqual(sum(x[0] for x in steps), .947)
        self.assertEqual(steps[-1][1], [1., 2., 0.])
        self.assertAlmostEqual(forward_distance(data, [.48,2.,0.], [1.,2.,0.]), .52)
        for current in [[-.01,2.,0.], [1.01,2.,0.], [.1,2.06,0.],
                        [.1,2.,.06], [.1,2.04,.04], [.95,2.,0.], [float('nan'),2.,0.]]:
            with self.subTest(current=current), self.assertRaises(ValueError):
                remaining_steps(data, current)
        for current in [[.98,2.,0.], [.1,2.,0.], [.5,2.06,0.]]:
            with self.assertRaises(ValueError): forward_distance(data, current, [1.,2.,0.])

    def test_units_and_rotated_staging(self):
        data = example(); data['drop_pose_m_rad'] = [1., 2., math.pi/2]
        valid = validate(data, 'MESAS2', 'uslam')
        self.assertAlmostEqual(offset(valid['drop_pose_m_rad'], 1.)[0], 1.)
        self.assertAlmostEqual(offset(valid['drop_pose_m_rad'], 1.)[1], 1.)
        steps = approach_steps(valid)
        self.assertEqual([s[0] for s in steps], [.5, .5])
        self.assertEqual(steps[-1][1], valid['drop_pose_m_rad'])

    def test_segments_preserve_distance_and_primitive_limits(self):
        for distance in [.1, .2, .6, .61, 1., 1.08, 1.2]:
            data = validate(example(distance), 'MESAS2', 'uslam')
            steps = approach_steps(data)
            self.assertAlmostEqual(sum(s[0] for s in steps), distance)
            self.assertTrue(all(.1 <= s[0] <= .6 for s in steps))
            self.assertEqual(steps[-1][1], data['drop_pose_m_rad'])

    def test_invalid_or_unrecorded_profiles_rejected(self):
        for key, value in [('version', True), ('map_name', 'OTHER'), ('map_type', 'fusion'),
                ('map_fingerprint', None), ('map_fingerprint', 'short'),
                ('drop_pose_m_rad', None), ('drop_pose_m_rad', [1,2,90]),
                ('drop_pose_m_rad', [float('nan'),2,0]), ('drop_pose_m_rad', [True,2,0]),
                ('approach_distance_m', 0), ('approach_distance_m', 1.21),
                ('position_tolerance_m', .13), ('yaw_tolerance_rad', .15),
                ('position_tolerance_m', float('nan')), ('recorded_at_utc', '')]:
            with self.subTest(key=key, value=value):
                data = example(); data[key] = value
                with self.assertRaises(ValueError): validate(data, 'MESAS2', 'uslam')
        with self.assertRaises(ValueError): validate(example(), 'MESAS2', 'auto')

    def test_record_requires_unambiguous_actual_report(self):
        report = 'MAP_POSE_FRESHNESS=volatile-stamped-v2\nMAP_FINGERPRINT='+'a'*64+'\nMAP_POSE_REFERENCE=1 2 0\n'
        self.assertEqual(record(report, 'MESAS2', 'uslam', .5)['drop_pose_m_rad'], [1,2,0])
        for bad in [report.replace('MAP_POSE_REFERENCE', 'OTHER'), report+report,
                    report.replace('1 2 0', '1 2 nan')]:
            with self.assertRaises(ValueError): record(bad, 'MESAS2', 'uslam', .5)


class WithoutTagsFlowTests(unittest.TestCase):
    calls = fixtures.TransferTests.calls
    keys = fixtures.TransferTests.keys
    run_flow = fixtures.TransferTests.run_flow

    def setUp(self):
        fixtures.TransferTests.setUp(self)
        (self.root/'lib').mkdir()
        (self.root/'lib/cruzr_table_drop_profile.py').write_text((SCRIPTS/'lib/cruzr_table_drop_profile.py').read_text())
        self.profile = self.root/'mesa2.json'
        self.profile.write_text(json.dumps(example()))
        self.env.update(CRUZR_MAP_NAME='MESAS2', CRUZR_MAP_TYPE='uslam', CRUZR_MESA2_PROFILE=str(self.profile))
        # El flujo debe funcionar incluso sin el script AprilTag instalado.
        (self.root/'cruzr_apriltag_mesa2_align.sh').unlink()

    def test_resume_inside_corridor_only_advances_remaining_distance(self):
        result = self.run_flow('--without-apriltag', '--resume-held-approach', '--yes', MOCK_POSE='0.1 2 0')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('carry:--grasp-only', self.keys())
        self.assertNotIn('carry:--retreat-only', self.keys())
        self.assertNotIn('map:--navigate-map-pose', self.keys())
        advances = [float(c['args'][1]) for c in self.calls() if c['key']=='carry:--advance-held-distance']
        self.assertAlmostEqual(sum(advances), .9)
        self.assertIn('cycle:--deposit-held', self.keys())

    def test_resume_outside_corridor_never_moves(self):
        result = self.run_flow('--without-apriltag', '--resume-held-approach', '--yes', MOCK_POSE='0.1 2.1 0')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('carry:--advance-held-distance', self.keys())
        self.assertNotIn('cycle:--deposit-held', self.keys())

    def test_check_has_no_apriltag_dependency(self):
        result = self.run_flow('--without-apriltag', '--check', '--fast')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.keys(), ['map:--measure-map-reference', 'cargo:--check'])
        self.assertEqual(self.calls()[0]['fingerprint'], 'a'*64)

    def test_full_flow_uses_taught_pose_and_checks_each_step(self):
        result = self.run_flow('--without-apriltag', '--run', '--yes', '--fast')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(any(key.startswith('align:') for key in self.keys()))
        self.assertEqual(self.keys(), ['map:--measure-map-reference', 'cargo:--check',
            'carry:--grasp-only', 'carry:--retreat-only', 'cargo:--enable',
            'map:--navigate-map-pose', 'cargo:--restore', 'map:--check-map-pose',
            'carry:--advance-held-distance', 'map:--check-map-pose',
            'carry:--advance-held-distance', 'map:--check-map-pose',
            'cycle:--deposit-held', 'home:--run'])
        poses = [c['args'][1] for c in self.calls() if c['key']=='map:--check-map-pose']
        self.assertEqual(poses, ['0 2 0', '0.5 2 0', '1 2 0'])
        nav = next(c for c in self.calls() if c['key']=='map:--navigate-map-pose')
        self.assertEqual(nav['args'][1], '0 2 0')

    def test_stage_held_stops_at_taught_premesa(self):
        result = self.run_flow('--without-apriltag', '--stage-held', '--yes')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.keys()[-2:], ['cycle:--verify-grasp','map:--check-map-pose'])
        self.assertNotIn('carry:--advance-held-distance', self.keys())
        self.assertNotIn('cycle:--deposit-held', self.keys())

    def test_resume_modes_preserve_phase_without_regrasp(self):
        for mode, retreat, navigation in [('resume-held',0,0), ('resume-held-navigation',0,1),
                                         ('resume-held-from-mesa1',1,1)]:
            self.events.unlink(missing_ok=True)
            result = self.run_flow('--without-apriltag', '--'+mode, '--yes')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn('carry:--grasp-only', self.keys())
            self.assertEqual(self.keys().count('carry:--retreat-only'), retreat)
            self.assertEqual(self.keys().count('map:--navigate-map-pose'), navigation)

    def test_bad_profile_fails_before_connection(self):
        for data in [None, dict(example(), map_name='OTHER'), dict(example(), map_fingerprint=None)]:
            self.events.unlink(missing_ok=True)
            self.profile.write_text(json.dumps(data))
            result = self.run_flow('--without-apriltag', '--run', '--yes')
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(self.keys(), [])

    def test_pose_mismatch_before_approach_does_not_advance_or_deposit(self):
        result = self.run_flow('--without-apriltag', '--resume-held', '--yes',
                               failures={'map:--check-map-pose':42})
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('carry:--advance-held-distance', self.keys())
        self.assertNotIn('cycle:--deposit-held', self.keys())

    def test_failed_advance_does_not_repeat_or_deposit(self):
        result = self.run_flow('--without-apriltag', '--resume-held', '--yes',
                               failures={'carry:--advance-held-distance':42})
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.keys().count('carry:--advance-held-distance'), 1)
        self.assertNotIn('cycle:--deposit-held', self.keys())
        self.assertNotIn('home:--run', self.keys())

    def test_navigation_failure_restores_and_stops(self):
        result = self.run_flow('--without-apriltag', '--run', '--yes',
                               failures={'map:--navigate-map-pose':37})
        self.assertEqual(result.returncode, 37)
        self.assertEqual(self.keys()[-1], 'cargo:--restore')
        self.assertNotIn('carry:--advance-held-distance', self.keys())

    def test_pose_mismatch_after_advance_blocks_remaining_motion(self):
        for occurrence in [2, 3]:
            self.events.unlink(missing_ok=True)
            result = self.run_flow('--without-apriltag', '--resume-held', '--yes',
                failures={'map:--check-map-pose':42},
                MOCK_FAILURE_AT=json.dumps({'map:--check-map-pose':occurrence}))
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(self.keys().count('carry:--advance-held-distance'), occurrence-1)
            self.assertNotIn('cycle:--deposit-held', self.keys())
            self.assertNotIn('home:--run', self.keys())

    def test_wrapper_defaults_to_check_without_tags(self):
        path = self.root/'cruzr_blue_workbin_table_transfer_no_tag.sh'
        path.write_text((SCRIPTS/path.name).read_text()); path.chmod(0o755)
        result = subprocess.run([str(path)], env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.keys(), ['map:--measure-map-reference', 'cargo:--check'])

    def test_teach_reads_and_records_only_without_overwrite(self):
        self.profile.unlink()
        result = self.run_flow('--teach-mesa2', '--approach-distance','1.0')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.keys(), ['map:--measure-map-reference'])
        saved = json.loads(self.profile.read_text())
        self.assertEqual(saved['drop_pose_m_rad'], [1,2,0])
        self.assertEqual(saved['map_fingerprint'], 'a'*64)
        self.events.unlink()
        result = self.run_flow('--teach-mesa2','--approach-distance','1.0')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.keys(), [])

    def test_teach_missing_distance_fails_before_connection(self):
        self.profile.unlink()
        result = self.run_flow('--teach-mesa2')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.keys(), [])

    def test_overwrite_keeps_exact_backup_and_records_new_reference(self):
        original = self.profile.read_bytes()
        result = self.run_flow('--teach-mesa2', '--approach-distance', '.5', '--overwrite-mesa2')
        self.assertEqual(result.returncode, 0, result.stderr)
        backups = list(self.root.glob('mesa2.json.bak.*'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)
        self.assertEqual(json.loads(self.profile.read_text())['approach_distance_m'], .5)
        self.assertEqual(self.keys(), ['map:--measure-map-reference'])

    def test_failed_capture_preserves_original_reference(self):
        original = self.profile.read_bytes()
        result = self.run_flow('--teach-mesa2', '--approach-distance', '.5', '--overwrite-mesa2',
                               failures={'map:--measure-map-reference': 42})
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.profile.read_bytes(), original)
        self.assertEqual(list(self.root.glob('mesa2.json.bak.*')), [])

    def test_overwrite_rejects_symlink_before_connection(self):
        target = self.root/'original.json'
        self.profile.rename(target)
        self.profile.symlink_to(target)
        result = self.run_flow('--teach-mesa2', '--approach-distance', '.5', '--overwrite-mesa2')
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.profile.is_symlink())
        self.assertEqual(self.keys(), [])

    def test_wrong_flags_fail_before_connection(self):
        for args in [('--without-apriltag','--fluid'), ('--approach-distance','.5'),
                     ('--without-apriltag', '--check', '--overwrite-mesa2'),
                     ('--mesa2-profile',str(self.profile))]:
            result = self.run_flow(*args)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(self.keys(), [])


class DirectMapReferenceTests(unittest.TestCase):
    def run_reference(self, mode, current='1 2 0', nav_status=0):
        source = (SCRIPTS/'cruzr_blue_workbin_map_route.sh').read_text()
        check = 'assert_near_pose() {' + source.split('assert_near_pose() {',1)[1].split('\nverify_start_area()',1)[0]
        function = 'run_direct_map_reference() {' + source.split('run_direct_map_reference() {',1)[1].split('\nrun_cycle()',1)[0]
        code = """set -euo pipefail
info() { echo "$*"; }
die() { echo "$*" >&2; exit 1; }
ensure_map_active() { echo MAP_CHECK; }
map_preflight() { echo HEALTH_CHECK; }
grasp_args() { echo ACTUATOR_CHECK; }
require_wireless_run() { :; }
read_stable_map_pose() { echo "$MOCK_CURRENT"; }
navigation_to_free_pose() { echo "NAV_GOAL=$1"; return "$MOCK_NAV_STATUS"; }
stop_navigation() { echo NAV_STOP; }
DIRECT_MAP_POSE='1 2 0'
POSE_POSITION_TOLERANCE=.05
POSE_YAW_TOLERANCE=.05
YES=1
""" + check + function + '\nrun_direct_map_reference\necho FINISHED\n'
        return subprocess.run(['bash','-s'], input=code, env=dict(os.environ, MODE=mode,
            MOCK_CURRENT=current, MOCK_NAV_STATUS=str(nav_status)), text=True, capture_output=True)

    def test_measure_and_check_do_not_navigate(self):
        for mode in ['measure-map-reference','check-map-pose']:
            result = self.run_reference(mode)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertNotIn('NAV_GOAL=',result.stdout)

    def test_goal_once_and_post_navigation_pose_verified(self):
        result = self.run_reference('navigate-map-pose')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout.count('NAV_GOAL='),1)
        self.assertIn('TAUGHT_MAP_POSE_VERIFIED=',result.stdout)
        result = self.run_reference('navigate-map-pose',current='1.5 2 0')
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(result.stdout.count('NAV_GOAL='),1)
        self.assertIn('NAV_STOP',result.stdout)
        self.assertNotIn('FINISHED',result.stdout)

    def test_navigation_failure_or_invalid_pose_never_passes(self):
        result = self.run_reference('navigate-map-pose',nav_status=42)
        self.assertEqual(result.returncode,42)
        self.assertIn('NAV_STOP',result.stdout)
        for pose in ['nan 2 0','1 2', '1 2 0.3']:
            result = self.run_reference('check-map-pose',current=pose)
            self.assertNotEqual(result.returncode,0)
            self.assertNotIn('FINISHED',result.stdout)

    def test_unstable_pose_or_read_failure_propagates_through_substitution(self):
        source = (SCRIPTS/'cruzr_blue_workbin_map_route.sh').read_text()
        check = 'assert_near_pose() {' + source.split('assert_near_pose() {',1)[1].split('\nverify_start_area()',1)[0]
        stable = 'read_stable_map_pose() {' + source.split('read_stable_map_pose() {',1)[1].split('\nrun_direct_map_reference()',1)[0]
        with tempfile.TemporaryDirectory() as tmp:
            samples = Path(tmp)/'samples'
            samples.write_text('1 2 0\n1.02 2 0\n1 2 0\n')
            reader = 'read_map_localization_pose() { head -n1 "$SAMPLES"; sed -i "1d" "$SAMPLES"; }\n'
            code = 'set -euo pipefail\n'+reader+check+stable+'\nvalue="$(read_stable_map_pose)"\necho ACCEPTED\n'
            result = subprocess.run(['bash','-s'], input=code, env=dict(os.environ,SAMPLES=str(samples)),
                                    text=True,capture_output=True)
            self.assertNotEqual(result.returncode,0)
            self.assertNotIn('ACCEPTED',result.stdout)
            code = code.replace(reader, 'read_map_localization_pose() { echo "1 2 0"; return 42; }\n')
            result = subprocess.run(['bash','-s'], input=code,text=True,capture_output=True)
            self.assertEqual(result.returncode,42)
            self.assertNotIn('ACCEPTED',result.stdout)

    def test_bad_numeric_target_rejected_before_connection(self):
        for pose in ['nan 2 0', '1 2 90', '1 2', '1 2 3 4']:
            result = subprocess.run(['bash',str(SCRIPTS/'cruzr_blue_workbin_map_route.sh'),
                                     '--navigate-map-pose',pose], text=True,capture_output=True,timeout=2)
            self.assertNotEqual(result.returncode,0)
            self.assertNotIn('Conexión:',result.stdout)


if __name__ == '__main__':
    unittest.main()
