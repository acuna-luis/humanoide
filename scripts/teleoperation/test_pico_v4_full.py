"""Offline tests for the v4 full-body gates; never connect to the robot."""
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
GATE = HERE / 'cruzr_pico_teleop_pc.sh'
WRAPPER = HERE / 'probar_pico_v4_full.sh'
TEXT = GATE.read_text()
PROFILE_FUNCTION = TEXT.split('check_robot_teleop_profile_loaded() {', 1)[1].split('\ncheck_v4_hand_states()', 1)[0]
REMOTE = PROFILE_FUNCTION.split("<<'REMOTE'\n", 1)[1].split('\nREMOTE\n', 1)[0]
CLEANUP = TEXT.split('cleanup_v4_full() {', 1)[1].split('\nassert_v4_full_control_available()', 1)[0].rsplit('\n}', 1)[0]
AVAILABILITY = TEXT.split('assert_v4_full_control_available() {', 1)[1].split('\nrun_official_teleop()', 1)[0].rsplit('\n}', 1)[0]
RUN = TEXT.split('run_official_teleop() {', 1)[1].split('\nabort_gate()', 1)[0].rsplit('\n}', 1)[0]
PASSIVE = TEXT.split('backend_passive_state_json() {', 1)[1].split('\nbackend_detect_json()', 1)[0]
PASSIVE_PY = PASSIVE.split("<<'PY'\n", 1)[1].split('\nPY\n', 1)[0]
FULL_SHA = '48d2ee0f61ab3dddaceec31e7468d0a764ef0900b2e09b687281b5e02465e74e'
TASK = 'teleoperation/cruzr_v4_pico_teleoperation'


class FullProfile(unittest.TestCase):
    def remote(self, sha=FULL_SHA, hand='v4', waist='1', leg='2', task=TASK, running='true'):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / 'robot_app.log'
            log.write_text(f"BTree task: '{task}' is start\nHand type: {hand}\nWaist tele mode: {waist}\nLeg tele mode: {leg}\n")
            mocks = '''docker() {
  if [[ "$1" == inspect ]]; then echo "$MOCK_RUNNING";
  elif [[ "$1" == exec ]]; then printf '%s  config\\n' "$MOCK_SHA";
  else return 99; fi
}
find() { printf '1 %s\\n' "$MOCK_LOG"; }
'''
            return subprocess.run(['bash', '-c', mocks+REMOTE, 'synthetic', 'app', 'config', FULL_SHA,
                                   TASK, 'vendor-full-body-v4', '1', '2', 'v4'],
                env=dict(os.environ, MOCK_SHA=sha, MOCK_LOG=str(log), MOCK_RUNNING=running),
                text=True, capture_output=True, timeout=5)

    def test_matching_vendor_v4_modes_pass(self):
        result = self.remote()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('hand:v4,waist:1,leg:2', result.stdout)

    def test_wrong_hash_hand_modes_task_or_stopped_container_reject(self):
        cases = [dict(sha='wrong'), dict(hand='clamp'), dict(waist='0'), dict(leg='0'),
                 dict(task='teleoperation/cruzr_clamp_pico_teleoperation'), dict(running='false')]
        for case in cases:
            with self.subTest(case=case):
                result = self.remote(**case)
                self.assertNotEqual(result.returncode, 0, result.stdout+result.stderr)
                self.assertNotIn('FULL_BODY_LOADED=', result.stdout)

    def test_vendor_and_overlay_differ_only_by_two_modes(self):
        profile = (HERE / 'pico_effector_profile.sh').read_text()
        self.assertIn(FULL_SHA, profile)
        self.assertIn('expected_teleop_task="'+TASK+'"', profile)
        install = (HERE / 'install_cruzr_pico_arms_only.sh').read_text()
        self.assertIn("'s/^    waist_mode: 1$/    waist_mode: 0/'", install)
        self.assertIn("'s/^    leg_mode: 2$/    leg_mode: 0/'", install)

    def test_original_clamp_full_not_exposed_as_v4(self):
        env = dict(os.environ, PICO_EFFECTOR='v4')
        result = subprocess.run(['bash', str(GATE), '--teleoperate-full'], env=env,
                                text=True, capture_output=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Modo no habilitado para manos v4', result.stderr)
        result = subprocess.run(['bash', str(GATE), '--check-v4-full'], env=dict(os.environ, PICO_EFFECTOR='clamp'),
                                text=True, capture_output=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('requiere manos v4', result.stderr)

    def test_prepare_restore_and_start_fail_without_terminal(self):
        for option in ('--prepare-full', '--restore-arms-only', '--teleoperate'):
            with self.subTest(option=option):
                result = subprocess.run(['bash', str(WRAPPER), option], stdin=subprocess.DEVNULL,
                    text=True, capture_output=True, timeout=5)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('terminal local', result.stderr)

    @unittest.skipUnless(shutil.which('script'), 'requires script(1) for a synthetic terminal')
    def test_prepare_and_restore_reject_active_ui_before_config_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            mock_bash = Path(tmp) / 'bash'
            calls = Path(tmp) / 'calls'
            mock_bash.write_text('''#!/bin/sh
printf '%s\\n' "$2" >> "$MOCK_CALLS"
if [ "$2" = --check-v4-control-available ]; then
  echo 'ERROR: UI activa o estado desconocido' >&2
  exit 1
fi
exit 0
''')
            mock_bash.chmod(0o755)
            env = dict(os.environ, PATH=tmp+os.pathsep+os.environ['PATH'], MOCK_CALLS=str(calls))
            for option, confirmation in (
                ('--prepare-full', 'PREPARAR V4 FULL SIN RECARGAR NI MOVER'),
                ('--restore-arms-only', 'RESTAURAR V4 ARMS ONLY SIN RECARGAR NI MOVER')):
                with self.subTest(option=option):
                    if calls.exists(): calls.unlink()
                    cmd = '/bin/bash '+shlex.quote(str(WRAPPER))+' '+option
                    result = subprocess.run([shutil.which('script'), '-q', '-e', '-c', cmd, '/dev/null'],
                        input=confirmation+'\n', env=env, text=True, capture_output=True, timeout=5)
                    self.assertNotEqual(result.returncode, 0, result.stdout+result.stderr)
                    self.assertIn('UI activa', result.stdout)
                    self.assertEqual(calls.read_text().splitlines(), ['--check-v4-control-available'])


class OwnershipAndSafety(unittest.TestCase):
    def cleanup(self, committed):
        mocks = '''official_v4_start_committed="$STATE"
stop_motion_safety_monitor() { echo OUR_MONITOR_STOPPED; }
stop_pico_camera() { echo OUR_CAMERA_STOPPED; }
cleanup_official_teleop() { echo OFFICIAL_STOP_CALLED; }
info() { echo "$*"; }
cleanup_v4_full() {
'''
        return subprocess.run(['bash', '-c', mocks+CLEANUP+'\n}\ncleanup_v4_full\n'],
            env=dict(os.environ, STATE=str(committed)), text=True, capture_output=True, timeout=5)

    def test_prestart_rejection_never_stops_other_client(self):
        result = self.cleanup(0)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('OUR_CAMERA_STOPPED', result.stdout)
        self.assertNotIn('OFFICIAL_STOP_CALLED', result.stdout)
        self.assertIn('V4_FULL_PRESTART_NO_CONTROL_SENT', result.stdout)

    def test_after_committed_start_retains_official_stop(self):
        result = self.cleanup(1)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('OFFICIAL_STOP_CALLED', result.stdout)

    def availability(self, pgrep_rc=1, ui_rc=3, operation='1'):
        mocks = '''set -Eeuo pipefail
ui_unit=mock-ui
pgrep() { return "$PGREP_RC"; }
systemctl() { return "$UI_RC"; }
backend_passive_state_json() {
  [[ "$PICO_PASSIVE_REQUIRE_EXPLICIT_STOP" == 1 ]] || return 90
  printf '{"content":{"operation_type":%s}}' "$OPERATION"
}
die() { printf 'ERROR: %s\\n' "$*" >&2; exit 1; }
assert_v4_full_control_available() {
'''
        return subprocess.run(['bash', '-c', mocks+AVAILABILITY+'\n}\nassert_v4_full_control_available\necho PASS\n'],
            env=dict(os.environ, PGREP_RC=str(pgrep_rc), UI_RC=str(ui_rc), OPERATION=operation),
            text=True, capture_output=True, timeout=5)

    def test_available_only_when_no_client_ui_inactive_and_explicit_stop(self):
        self.assertEqual(self.availability().returncode, 0)
        for item in (dict(pgrep_rc=0), dict(pgrep_rc=2), dict(ui_rc=0), dict(ui_rc=4),
                     dict(operation='2'), dict(operation='null')):
            with self.subTest(item=item):
                result = self.availability(**item)
                self.assertNotEqual(result.returncode, 0, result.stdout+result.stderr)
                self.assertNotIn('PASS', result.stdout)

    def test_strict_passive_parser_requires_explicit_operation(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / 'backend.log'
            env = dict(os.environ, BACKEND_LOG=str(log), BACKEND_START_TS='2026-11-05:10:00:00',
                       PICO_PASSIVE_REQUIRE_EXPLICIT_STOP='1')
            prefix = '2026-11-05:10:00:01.000 Send message to client: '
            for content, ok in (("{}", False), ('{"operation_type":1}', True),
                                ('{"operation_type":2}', True)):
                with self.subTest(content=content):
                    log.write_text(prefix+'{"type":"detect","content":'+content+'}\n')
                    result = subprocess.run([sys.executable, '-c', PASSIVE_PY], env=env,
                                            text=True, capture_output=True, timeout=5)
                    self.assertEqual(result.returncode == 0, ok, result.stdout+result.stderr)
                    if not ok: self.assertIn('No explicit current backend operation state', result.stderr)

    def test_full_route_contains_motion_safety_gates_and_no_bypass(self):
        run = TEXT.split('run_official_teleop() {', 1)[1].split('\nabort_gate()', 1)[0]
        for expected in ('check_robot_v4_full_loaded', 'check_robot_teleop_safety',
                         'check_v4_hand_states', 'start_motion_safety_monitor',
                         'motion_safety_monitor_ok', 'check_controller_inputs_neutral',
                         'assert_v4_full_control_available', 'robot_link_runtime_ok',
                         'official_v4_start_committed=1', 'cleanup_v4_full'):
            self.assertIn(expected, run)
        self.assertIn('[[ "$robot_link_kind" == "wifi" ]]', run)
        self.assertIn('thumbstick', run)
        self.assertIn('No se recargará el modo ni se enviará movimiento', WRAPPER.read_text())
        self.assertGreaterEqual(run.count('check_robot_v4_full_loaded'), 2)

    def test_final_profile_rejection_does_not_start_or_stop_another_client(self):
        # Execute the real gate with local shell doubles. The only altered line
        # substitutes a synthetic terminal so no ROS/SSH/controller is opened.
        run = RUN.replace('[[ -t 0 && -t 1 ]] ||', 'true ||', 1)
        with tempfile.TemporaryDirectory() as tmp:
            backend_log = Path(tmp) / 'backend.log'
            backend_log.write_text('synthetic\n')
            mocks = '''set -Eeuo pipefail
official_teleop_seconds=120 allow_bimanual=1 official_cleanup_done=0
official_v4_start_committed=0 robot_link_kind=wifi ui_unit=unused
pico_effector=v4 effector_description=manos_v4 expected_motion_hand=v4
required_arm=hand pico_control_executable=mock_pico backend_log="$MOCK_LOG"
profile_checks=0
die() { echo "ERROR $*" >&2; exit 1; }
info() { echo "$*"; }
check_robot_v4_full_loaded() {
  profile_checks=$((profile_checks+1))
  if ((profile_checks == 2)); then die 'synthetic final profile mismatch'; fi
}
check_robot_full_body_loaded() { die 'wrong profile'; }
check_robot_arms_only_loaded() { die 'wrong profile'; }
assert_v4_full_control_available() { :; }
wait_for_pico_tracking_ready() { :; }
check_pc() { :; }
systemctl() { return 3; }
start_pico_camera() { :; }
check_robot_teleop_safety() { :; }
check_v4_hand_states() { :; }
start_motion_safety_monitor() { :; }
stop_motion_safety_monitor() { echo OWN_MONITOR_STOP; }
stop_pico_camera() { echo OWN_CAMERA_STOP; }
cleanup_official_teleop() { echo OTHER_CLIENT_STOP; }
mock_pico() { echo FAKE_START; }
cleanup_v4_full() {
''' + CLEANUP + '\n}\nrun_official_teleop() {\n' + run + '\n}\nrun_official_teleop vendor-full-body-v4\n'
            result = subprocess.run(['bash', '-c', mocks],
                input='INICIAR TELEOPERACION OFICIAL DE CUERPO COMPLETO\n',
                env=dict(os.environ, MOCK_LOG=str(backend_log)), text=True,
                capture_output=True, timeout=5)
        self.assertNotEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertIn('synthetic final profile mismatch', result.stderr)
        self.assertIn('V4_FULL_PRESTART_NO_CONTROL_SENT', result.stdout)
        self.assertNotIn('OTHER_CLIENT_STOP', result.stdout)
        self.assertNotIn('FAKE_START', result.stdout)


if __name__ == '__main__':
    unittest.main()
