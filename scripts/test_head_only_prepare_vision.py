#!/usr/bin/env python3
"""Head-only mode admission and dispatch, with no robot, network or real locks."""
import os
from pathlib import Path
import subprocess
import unittest


SCRIPT = Path(__file__).with_name('cruzr_blue_workbin_cycle.sh')
SOURCE = SCRIPT.read_text()


def function(name):
    marker = name + '() {'
    return marker + SOURCE.split(marker, 1)[1].split('\n}\n', 1)[0] + '\n}\n'


class HeadOnlyTests(unittest.TestCase):
    def compatibility(self, mode, hardware):
        return subprocess.run(
            ['bash', '-s', '--', mode, hardware],
            input=function('hardware_compatible') +
                  'hardware_compatible "$1" "$2" cruzr_s2_v1\n',
            capture_output=True, text=True, timeout=3)

    def test_clamp_and_sps_are_accepted_for_both_head_modes(self):
        for mode in ('check-head', 'prepare-vision'):
            for hw in ('cruzr_s2_v1', 'cruzr_s2_v1_sps'):
                with self.subTest(mode=mode, hw=hw):
                    self.assertEqual(self.compatibility(mode, hw).returncode, 0)

    def test_sps_is_rejected_for_every_other_mode(self):
        modes = ('check', 'install', 'run', 'grasp', 'verify-grasp',
                 'deposit-held', 'check-open-only', 'open-only', 'home',
                 'home-workbin-internal', 'measure-box', 'measure-box-fast',
                 'grasp-after-approach', '', 'unknown')
        for mode in modes:
            with self.subTest(mode=mode):
                self.assertNotEqual(self.compatibility(mode, 'cruzr_s2_v1_sps').returncode, 0)
                self.assertEqual(self.compatibility(mode, 'cruzr_s2_v1').returncode, 0)

    def test_unknown_hardware_is_rejected(self):
        for mode in ('check-head', 'prepare-vision', 'run'):
            for hw in ('', 'unknown', 'cruzr_s2_v1_sps_extra'):
                with self.subTest(mode=mode, hw=hw):
                    self.assertNotEqual(self.compatibility(mode, hw).returncode, 0)

    def dispatch(self, mode, hardware='cruzr_s2_v1_sps', fail_preflight=False,
                 answer='BAJAR CABEZA\n', yes=0):
        # Run the actual dispatcher and confirmation, replacing external work.
        main = function('main').replace(
            '  exec 9>"/tmp/cruzr_blue_workbin_cycle.lock"',
            '  : # no real lock in this offline test')
        code = '''set -Eeuo pipefail
MODE="$TEST_MODE"; FAST=0; YES="$TEST_YES"; FLUID_MODE=0
HEAD_LOWER_TASK=cruzr/move_head_lower
require_local_tools() { :; }
flock() { :; }
select_connection() { echo MOCK_CONNECTION; }
validate_templates() { echo MOCK_TEMPLATE_VALIDATION; }
remote_preflight() {
  echo MOCK_PREFLIGHT
  [[ "$TEST_FAIL_PREFLIGHT" != 1 ]] || return 47
  hardware_compatible "$MODE" "$TEST_HW" cruzr_s2_v1
}
install_templates() { echo UNEXPECTED_INSTALL; return 91; }
run_motion_task() { echo "MOCK_GOAL=$1,$2"; }
'''
        code += ''.join(function(n) for n in ('die', 'info', 'hardware_compatible',
                                              'confirm_head_only'))
        code += main + '\nmain\n'
        return subprocess.run(
            ['bash', '-c', code], input=answer, capture_output=True, text=True,
            timeout=3, env=dict(os.environ, TEST_MODE=mode, TEST_HW=hardware,
                                TEST_FAIL_PREFLIGHT=str(int(fail_preflight)),
                                TEST_YES=str(yes)))

    def test_check_head_performs_full_preflight_without_install_or_motion(self):
        result = self.dispatch('check-head')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('MOCK_TEMPLATE_VALIDATION', result.stdout)
        self.assertIn('MOCK_PREFLIGHT', result.stdout)
        self.assertIn('HEAD_CHECK_OK:', result.stdout)
        self.assertNotIn('MOCK_GOAL=', result.stdout)
        self.assertNotIn('UNEXPECTED_INSTALL', result.stdout)

    def test_preparation_dispatches_only_head_after_specific_confirmation(self):
        result = self.dispatch('prepare-vision')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('BAJADA ÚNICA DE CABEZA', result.stdout)
        self.assertNotIn('EJECUTAR CICLO', result.stdout)
        self.assertEqual([s for s in result.stdout.splitlines() if s.startswith('MOCK_GOAL=')],
                         ['MOCK_GOAL=cruzr/move_head_lower,15'])
        self.assertNotIn('UNEXPECTED_INSTALL', result.stdout)

    def test_failed_preflight_or_unknown_hardware_never_dispatches(self):
        for mode in ('check-head', 'prepare-vision'):
            for changes in ({'fail_preflight': True}, {'hardware': 'unknown'}):
                with self.subTest(mode=mode, changes=changes):
                    result = self.dispatch(mode, **changes)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn('MOCK_GOAL=', result.stdout)

    def test_declined_head_confirmation_never_dispatches(self):
        result = self.dispatch('prepare-vision', answer='NO\n')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('MOCK_GOAL=', result.stdout)

    def test_existing_yes_flag_still_dispatches_only_head(self):
        result = self.dispatch('prepare-vision', answer='', yes=1)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count('MOCK_GOAL='), 1)

    def test_fast_is_rejected_before_connection_for_both_modes(self):
        for mode in ('--check-head', '--prepare-vision'):
            result = subprocess.run(['bash', str(SCRIPT), mode, '--fast'],
                                    capture_output=True, text=True, timeout=3)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('no admiten --fast', result.stderr)
            self.assertNotIn('Conexión:', result.stdout)


if __name__ == '__main__':
    unittest.main()
