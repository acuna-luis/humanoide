#!/usr/bin/env python3
"""Ejecuta el orquestador Bash con procesos hijos simulados: cero red/ROS."""
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import unittest

SOURCE = Path(os.environ.get('TRANSFER_TEST_SOURCE', Path(__file__).with_name('cruzr_blue_workbin_table_transfer.sh')))
NAMES = {
    'carry': 'cruzr_blue_workbin_carry_back.sh',
    'cycle': 'cruzr_blue_workbin_cycle.sh',
    'map': 'cruzr_blue_workbin_map_route.sh',
    'align': 'cruzr_apriltag_mesa2_align.sh',
    'home': 'cruzr_recover_to_home.sh',
    'cargo': 'cruzr_cargo_perception_profile.sh',
}
MOCK = r'''#!/usr/bin/env python3
import json, os, pathlib, sys, time
name = json.loads(os.environ['MOCK_NAMES'])[pathlib.Path(sys.argv[0]).name]
args = sys.argv[1:]
key = name + ':' + args[0]
with open(os.environ['MOCK_EVENTS'], 'a') as stream:
    stream.write(json.dumps({'key': key, 'args': args, 'context': os.getenv('CRUZR_ROUTE_CONTEXT'),
        'cached': os.getenv('CRUZR_TRANSFER_PREFLIGHT_DONE'), 'timeout': os.getenv('CRUZR_NAV_TIMEOUT_SECONDS'), 'fingerprint': os.getenv('CRUZR_EXPECTED_MAP_FINGERPRINT')})+'\n')
if key == os.getenv('MOCK_PAUSE'):
    time.sleep(float(os.getenv('MOCK_SLEEP', '0.3')))
with open(os.environ['MOCK_EVENTS']) as stream:
    occurrence = sum(json.loads(line)['key'] == key for line in stream)
failure_at = json.loads(os.getenv('MOCK_FAILURE_AT', '{}')).get(key, occurrence)
if key in json.loads(os.getenv('MOCK_FAILURES', '{}')) and occurrence == failure_at:
    print(os.getenv('MOCK_ERROR', 'MOCK_FAILURE'))
    sys.exit(json.loads(os.environ['MOCK_FAILURES'])[key])
if key == 'map:--measure-map-reference':
    print('MAP_POSE_FRESHNESS=volatile-stamped-v2')
    print('MAP_FINGERPRINT=' + os.getenv('MOCK_FINGERPRINT', 'a'*64))
    print('MAP_POSE_REFERENCE=' + os.getenv('MOCK_POSE', '1 2 0'))
if key == 'map:--check-map-pose':
    print('TAUGHT_MAP_POSE_VERIFIED=' + args[1])
if key == 'cargo:--check':
    print('CARGO_PERCEPTION_PROFILE=' + os.getenv('MOCK_PROFILE', 'disabled'))
print('MOCK_OK=' + key, flush=True)
'''


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.script = self.root / SOURCE.name
        source = SOURCE.read_text().replace('/tmp/cruzr_blue_workbin_table_transfer.lock',
                                            str(self.root / 'transfer.lock'))
        self.script.write_text(source)
        self.script.chmod(0o755)
        for filename in NAMES.values():
            path = self.root / filename
            path.write_text(MOCK)
            path.chmod(0o755)
        self.events = self.root / 'events.jsonl'
        self.env = dict(os.environ, MOCK_NAMES=json.dumps({v:k for k,v in NAMES.items()}),
                        MOCK_EVENTS=str(self.events), TMPDIR=str(self.root))
        # Si por error apareciera una conexión directa en el orquestador, falla.
        bin_dir = self.root / 'bin'; bin_dir.mkdir()
        for name in ['ssh', 'rosa', 'ros2', 'docker', 'nc']:
            tool = bin_dir / name
            tool.write_text('#!/bin/sh\necho UNEXPECTED_NETWORK >&2\nexit 99\n')
            tool.chmod(0o755)
        self.env['PATH'] = str(bin_dir) + os.pathsep + self.env['PATH']

    def calls(self):
        return [json.loads(line) for line in self.events.read_text().splitlines()] if self.events.exists() else []

    def keys(self):
        return [call['key'] for call in self.calls()]

    def run_flow(self, *args, failures=None, **env):
        merged = dict(self.env, MOCK_FAILURES=json.dumps(failures or {}), **env)
        return subprocess.run([str(self.script), *args], env=merged, text=True,
                              input='', capture_output=True, timeout=8)

    def test_default_and_fast_check_do_not_move(self):
        for args in [(), ('--check', '--fast'), ('--check', '--fluid')]:
            self.events.unlink(missing_ok=True)
            result = self.run_flow(*args)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self.keys(), ['map:--check', 'align:--check', 'cargo:--check'])
            self.assertTrue(all('--fast' not in call['args'] for call in self.calls()))

    def test_full_sequence_and_live_logs(self):
        result = self.run_flow('--run', '--yes')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.keys(), ['map:--check', 'align:--check', 'cargo:--check',
            'carry:--grasp-only', 'carry:--retreat-only', 'cargo:--enable',
            'map:--navigate-waypoint-backoff', 'cargo:--restore', 'align:--coarse-held',
            'align:--align-held', 'cycle:--deposit-held', 'home:--run'])
        nav = next(call for call in self.calls() if 'navigate' in call['key'])
        self.assertEqual(nav['args'][1:3], ['MESA2_PRE', '1.08'])
        self.assertEqual(nav['timeout'], '120')
        self.assertTrue(all(call['timeout'] is None for call in self.calls() if call != nav))
        log = next(self.root.glob('cruzr-table-transfer.*/NAVIGATE_MESA2.log'))
        self.assertIn('MOCK_OK=map:', log.read_text())
        self.assertIn('TABLE_TRANSFER_COMPLETED=', result.stdout)

    def test_fast_and_fluid_keep_fresh_checks_and_full_deposit(self):
        for option in ['--fast', '--fluid']:
            self.events.unlink(missing_ok=True)
            result = self.run_flow('--run', '--yes', option,
                                   CRUZR_TRANSFER_PREFLIGHT_DONE='1', CRUZR_DRIVE_PREFLIGHT_DONE='1')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(all(call['cached'] is None for call in self.calls()))
            self.assertTrue(all(call['context'] == 'table-transfer' for call in self.calls()))
            for call in self.calls():
                if call['key'].endswith('--check') or call['key'] == 'cycle:--deposit-held':
                    self.assertNotIn('--fast', call['args'])

    def test_stage_held_stops_before_any_approach(self):
        result = self.run_flow('--stage-held', '--yes')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.keys()[-2:], ['cycle:--verify-grasp', 'align:--check-visible'])
        for forbidden in ['align:--coarse-held', 'align:--align-held', 'cycle:--deposit-held', 'home:--run']:
            self.assertNotIn(forbidden, self.keys())

    def test_resume_modes_do_not_repeat_grasp_or_retreat(self):
        for mode, retreat, navigation in [('resume-held', 0, 0),
                ('resume-held-navigation', 0, 1), ('resume-held-from-mesa1', 1, 1)]:
            self.events.unlink(missing_ok=True)
            result = self.run_flow('--'+mode, '--yes')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn('carry:--grasp-only', self.keys())
            self.assertEqual(self.keys().count('carry:--retreat-only'), retreat)
            self.assertEqual(self.keys().count('map:--navigate-waypoint-backoff'), navigation)
            self.assertEqual(self.keys().count('align:--coarse-held'), 1)

    def test_every_stage_failure_blocks_later_motion(self):
        sequence = ['map:--check', 'align:--check', 'cargo:--check',
            'carry:--grasp-only', 'carry:--retreat-only', 'cargo:--enable',
            'map:--navigate-waypoint-backoff', 'cargo:--restore', 'align:--coarse-held',
            'align:--align-held', 'cycle:--deposit-held', 'home:--run']
        for i, failed in enumerate(sequence):
            with self.subTest(failed=failed):
                self.events.unlink(missing_ok=True)
                result = self.run_flow('--run', '--yes', failures={failed: 42})
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('TABLE_TRANSFER_COMPLETED=', result.stdout)
                self.assertEqual(self.keys()[:i+1], sequence[:i+1])
                self.assertTrue(all(key == 'cargo:--restore' for key in self.keys()[i+1:]), self.keys())

    def test_restore_failure_stays_pending_and_cleanup_retries(self):
        result = self.run_flow('--run', '--yes', failures={'cargo:--restore': 40})
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.keys().count('cargo:--restore'), 2)
        self.assertNotIn('align:--coarse-held', self.keys())
        self.assertIn('restauración de percepción pendiente', result.stderr)

    def test_start_obstacle_does_not_add_half_meter_or_change_destination(self):
        result = self.run_flow('--run', '--yes', failures={'map:--navigate-waypoint-backoff': 37},
                               MOCK_ERROR='START_ONOBSTACLE 7218011')
        self.assertEqual(result.returncode, 37)
        self.assertEqual(self.keys().count('carry:--retreat-only'), 1)
        self.assertEqual(self.keys().count('map:--navigate-waypoint-backoff'), 1)
        self.assertNotIn('map:--navigate-waypoint', self.keys())
        self.assertIn('no se añade otro retroceso', result.stderr)

    def test_existing_perception_transaction_does_not_start_grasp(self):
        for profile in ['lidar-transit-enabled', 'restored-pending-cleanup', 'unknown']:
            self.events.unlink(missing_ok=True)
            result = self.run_flow('--run', '--yes', MOCK_PROFILE=profile)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(self.keys(), ['map:--check', 'align:--check', 'cargo:--check'])

    def test_imperfect_grasp_and_partial_deposit_are_reported_as_uncertain(self):
        for key, text in [('carry:--grasp-only', 'parcialmente apoyada'),
                          ('cycle:--deposit-held', 'Depósito interrumpido')]:
            self.events.unlink(missing_ok=True)
            result = self.run_flow('--run', '--yes', failures={key: 1})
            self.assertIn(text, result.stderr)
            self.assertNotIn('home:--run', self.keys())

    def test_conflicting_modes_and_cancelled_confirmation(self):
        result = self.run_flow('--run', '--check', '--yes')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.keys(), [])
        result = self.run_flow('--run')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.keys(), ['map:--check', 'align:--check', 'cargo:--check'])

    def test_term_during_navigation_restores_without_later_motion(self):
        env = dict(self.env, MOCK_PAUSE='map:--navigate-waypoint-backoff', MOCK_SLEEP='0.5')
        with subprocess.Popen([str(self.script), '--run', '--yes'], env=env,
                              text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              start_new_session=True) as process:
            deadline = time.monotonic() + 4
            while 'map:--navigate-waypoint-backoff' not in self.keys():
                if time.monotonic() > deadline:
                    process.kill(); self.fail('No llegó a navegación simulada')
                time.sleep(0.01)
            process.send_signal(signal.SIGTERM)
            _, err = process.communicate(timeout=4)
        self.assertEqual(process.returncode, 143, err)
        self.assertIn('cargo:--restore', self.keys())
        self.assertNotIn('align:--coarse-held', self.keys())


if __name__ == '__main__':
    unittest.main()
