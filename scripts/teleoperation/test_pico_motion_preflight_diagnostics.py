"""Run the actual preflight shell fragments with synthetic SSH/ROS only."""
import os
from pathlib import Path
import subprocess
import unittest


SCRIPT = Path(__file__).with_name('cruzr_pico_teleop_pc.sh')
FUNCTION = SCRIPT.read_text().split('check_robot_teleop_safety() {', 1)[1].split('\ngrip_state_seen_since()', 1)[0]
CAPTURE = FUNCTION[FUNCTION.index('  local output preflight_rc=0 reason'):].rsplit('\n}', 1)[0]
INNER = FUNCTION.split("<<'INNER'\n", 1)[1].split('\nINNER\n', 1)[0]
LOG_SELECTION = FUNCTION[FUNCTION.index('latest="$('):FUNCTION.index('\n[[ -n "$latest"')]


class PreflightDiagnosticsTests(unittest.TestCase):
    def test_hardware_allowlist_survives_ssh_argument_joining(self):
        # SSH reconstructs remote arguments as shell text. No network or robot.
        remote = FUNCTION.split("<<'REMOTE'\n", 1)[1].split('\nfor container', 1)[0]
        setup = 'expected_hw_types="cruzr_s2_v1 cruzr_s2_v1_sps"\n'
        send = 'printf "%s" "${expected_hw_types// /,}"'
        token = subprocess.check_output(['bash', '-c', setup+send], text=True)
        for hardware, accepted in [('cruzr_s2_v1_sps', True), ('cruzr_s2_v1', True), ('other', False)]:
            code = remote + '\nhw_type="$TEST_HW"\n' + FUNCTION.split('[[ " $expected_hw_types "', 1)[1].split('\n[[ "$tele_device"', 1)[0]
            code = code.replace('hw_type="$TEST_HW"\n', 'hw_type="$TEST_HW"\n[[ " $expected_hw_types "', 1)
            result = subprocess.run(['bash', '-c', code, 'remote', 'ros', 'app', 'task', '30', token],
                env=dict(os.environ, TEST_HW=hardware), capture_output=True, text=True)
            self.assertEqual(result.returncode == 0, accepted, result.stdout+result.stderr)
        self.assertIn('"${expected_hw_types// /,}"', CAPTURE)

    def test_large_log_inventory_selects_newest_without_sigpipe(self):
        # Use the production pipeline with enough input to overflow pipe buffers.
        # Only find is doubled; sort/sed/cut and pipefail execute normally.
        setup = '''set -Eeuo pipefail
find() { python3 -c 'for i in range(100000): print(str(i)+" /synthetic/robot_app_"+str(i)+".log")'; }
'''
        old = LOG_SELECTION.replace("sed -n '1p'", 'head -n1')
        broken = subprocess.run(['bash', '-c', setup+old],
            capture_output=True, text=True, timeout=10)
        self.assertEqual(broken.returncode, 141, broken.stderr)
        fixed = subprocess.run(['bash', '-c', setup+LOG_SELECTION+'\nprintf "%s\\n" "$latest"'],
            capture_output=True, text=True, timeout=10)
        self.assertEqual(fixed.returncode, 0, fixed.stderr)
        self.assertEqual(fixed.stdout.strip(), '/synthetic/robot_app_99999.log')

    def test_log_inventory_failure_remains_blocking(self):
        setup = 'set -Eeuo pipefail\nfind() { return 7; }\n'
        actual = subprocess.run(['bash', '-c', setup+LOG_SELECTION+'\necho CONTINUATION_ALLOWED'],
            capture_output=True, text=True, timeout=5)
        self.assertEqual(actual.returncode, 7)
        self.assertNotIn('CONTINUATION_ALLOWED', actual.stdout)

    def capture(self, rc, output=''):
        # setsid consumes the SSH heredoc without starting SSH or a robot client.
        setup = '''set -Eeuo pipefail
motion_askpass=/unused
robot_user=unused
motion_ip=unused
motion_ros_container=unused
motion_app_container=unused
expected_teleop_task=unused
expected_hw_types=cruzr_s2_v1
minimum_battery_soc=30
setsid() { cat >/dev/null; printf '%s' "$TEST_OUTPUT"; return "$TEST_RC"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
info() { printf '%s\n' "$*"; }
check() {
'''
        return subprocess.run(['bash', '-c', setup+CAPTURE+'\n}\ncheck\necho CONTINUATION_ALLOWED\n'],
            env=dict(os.environ, TEST_RC=str(rc), TEST_OUTPUT=output),
            capture_output=True, text=True, timeout=5)

    def inner(self, fault='0'):
        # Both source and timeout are shell doubles; no ROS installation/read.
        mocks = '''source() { :; }
timeout() {
  local topic="${@: -1}"
  if [[ "$FAULT" == timeout && "$topic" == /mc/joint_states ]]; then return 124; fi
  case "$topic" in
    /emb/estop_key_state) [[ "$FAULT" == 31 ]] && echo 'data: 1' || echo 'data: 0' ;;
    /emb/servo_estop_key_state) [[ "$FAULT" == 32 ]] && echo 'data: 1' || echo 'data: 0' ;;
    /emb/battery_state)
      if [[ "$FAULT" == 33 ]]; then echo 'batsoc: 60';
      elif [[ "$FAULT" == 34 ]]; then printf 'batsoc: 29\nbatsoc: 60\n';
      else printf 'batsoc: 60\nbatsoc: 65\n'; fi ;;
    /emb/chrg_input_status) [[ "$FAULT" == 35 ]] && echo 'data: 1' || echo 'data: 0' ;;
    /sys/state/module_lock_info) [[ "$FAULT" == 36 ]] && echo 'locked: true' || echo 'locked: false' ;;
    /mc/manipulation/action/_action/status) [[ "$FAULT" == 37 ]] && echo '  status: 4' || echo '  status: 2' ;;
    /mc/joint_states)
      if [[ "$FAULT" == 38 ]]; then printf 'velocity:\n- 0.03\neffort:\n';
      else printf 'velocity:\n- 0.0\neffort:\n'; fi ;;
    *) return 90 ;;
  esac
}
'''
        return subprocess.run(['bash', '-c', mocks+INNER, 'synthetic-preflight', '30'],
            env=dict(os.environ, FAULT=fault), capture_output=True, text=True, timeout=5)

    def test_every_rejected_motion_gate_still_stops_and_reports_its_code(self):
        for rc in range(31, 39):
            with self.subTest(rc=rc):
                actual = self.inner(str(rc))
                self.assertEqual(actual.returncode, rc, actual.stdout+actual.stderr)
                presented = self.capture(actual.returncode, actual.stdout+actual.stderr)
                self.assertNotEqual(presented.returncode, 0)
                self.assertIn('MOTION_PREFLIGHT_FAILED=rc:'+str(rc), presented.stderr)
                self.assertIn('No se enviará START', presented.stderr)
                self.assertNotIn('CONTINUATION_ALLOWED', presented.stdout)

    def test_wrong_active_task_is_preserved_in_error_output(self):
        shown = self.capture(26, 'ACTIVE_TASK_ERROR=cruzr/home\n')
        self.assertIn('ACTIVE_TASK_ERROR=cruzr/home', shown.stderr)
        self.assertIn('rc:26', shown.stderr)
        self.assertNotIn('CONTINUATION_ALLOWED', shown.stdout)

    def test_timeout_names_topic_and_cannot_authorize_continuation(self):
        actual = self.inner('timeout')
        self.assertEqual(actual.returncode, 124)
        self.assertIn('MOTION_TOPIC_READ_FAILED=/mc/joint_states; rc=124', actual.stderr)
        shown = self.capture(actual.returncode, actual.stdout+actual.stderr)
        self.assertIn('/mc/joint_states', shown.stderr)
        self.assertIn('rc:124', shown.stderr)
        self.assertNotIn('CONTINUATION_ALLOWED', shown.stdout)

    def test_unknown_transport_failure_remains_blocking(self):
        shown = self.capture(255, 'ssh diagnostic\n')
        self.assertIn('ssh diagnostic', shown.stderr)
        self.assertIn('rc:255', shown.stderr)
        self.assertNotIn('CONTINUATION_ALLOWED', shown.stdout)

    def test_success_preserves_original_measurements_without_error(self):
        actual = self.inner()
        self.assertEqual(actual.returncode, 0, actual.stdout+actual.stderr)
        self.assertIn('ACTIVE_ACTIONS=1', actual.stdout)
        shown = self.capture(0, actual.stdout)
        self.assertEqual(shown.returncode, 0)
        self.assertIn('JOINT_VELOCITY=stationary', shown.stdout)
        self.assertIn('ROBOT_TELEOP_SAFETY_OK=1', shown.stdout)
        self.assertIn('CONTINUATION_ALLOWED', shown.stdout)
        self.assertNotIn('MOTION_PREFLIGHT_FAILED', shown.stdout+shown.stderr)


if __name__ == '__main__':
    unittest.main()
