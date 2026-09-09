#!/usr/bin/env python3
"""Controles reales Bash/Python con datos sintéticos y Docker simulado; sin red."""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

SCRIPTS = Path(__file__).parent
CYCLE = (SCRIPTS / 'cruzr_blue_workbin_cycle.sh').read_text()
MAP = (SCRIPTS / 'cruzr_blue_workbin_map_route.sh').read_text()


class PreflightTests(unittest.TestCase):
    def test_fast_actions_still_run_canonical_preflight(self):
        gate = CYCLE.split('  if ((FAST == 0)) || [[ "$MODE" == check', 1)[1].split('\n  case "$MODE" in', 1)[0]
        gate = 'if ((FAST == 0)) || [[ "$MODE" == check' + gate
        for mode in ['check', 'run', 'grasp', 'grasp-after-approach', 'prepare-vision',
                     'deposit-held', 'home-workbin-internal', 'verify-grasp']:
            code = ('set -euo pipefail\nFAST=1\nMODE='+mode+'\n'
                    'validate_templates() { :; }\ninfo() { :; }\n'
                    'remote_preflight() { echo FRESH_PREFLIGHT; return 47; }\n'
                    + gate + '\necho SHOULD_NOT_CONTINUE\n')
            result = subprocess.run(['bash', '-s'], input=code, text=True, capture_output=True)
            self.assertEqual(result.returncode, 47, (mode, result.stderr))
            self.assertIn('FRESH_PREFLIGHT', result.stdout)
            self.assertNotIn('SHOULD_NOT_CONTINUE', result.stdout)

    def test_canonical_actuator_gate_rejects_incomplete_or_nonfinite_samples(self):
        import base64
        code = CYCLE.split('actuator_report="$(python3 -c \'\n', 1)[1].split("\n' \"$posture_gate_b64\"", 1)[0]
        encoded = base64.b64encode((SCRIPTS/'lib/cruzr_home_posture_gate.py').read_bytes()).decode()
        ids = [1001,1002,11001,11002,11003,11004, *range(4001,4008), *range(5001,5008)]
        valid = [dict(id=i, error_code=0, status=7, position=0.5, velocity=0, cmd_pos=0.5) for i in ids]
        cases = [({'act_item':valid}, True), ({'act_item':[]}, False), ({}, False),
                 ({'act_item':valid[:-1]}, False), ({'act_item':valid+[valid[0]]}, False),
                 ({'act_item':[dict(valid[0], position=float('nan'))]+valid[1:]}, False)]
        for message, ok in cases:
            result = subprocess.run(['python3', '-c', code, encoded], input=json.dumps(message),
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode == 0, ok, result.stderr)

    def test_parallel_health_reads_all_required_and_bounded(self):
        body = CYCLE.split('safety_dir="$(mktemp -d)"', 1)[1].split("printf 'HOST=motion", 1)[0]
        body = 'safety_dir="$(mktemp -d)"' + body
        for soc, failed, charger, estop, ok in [
            ('20', '', '0', '0', True), ('19.9', '', '0', '0', False),
            ('nan', '', '0', '0', False), ('101', '', '0', '0', False),
            ('20', 'battery', '0', '0', False), ('20', 'estop', '0', '0', False),
            ('20', '', '1', '0', False), ('20', '', '0', '1', False),
            ('20', 'servo', '0', '0', False), ('20', 'chrg', '0', '0', False),
        ]:
            with self.subTest(soc=soc, failed=failed, charger=charger, estop=estop):
                code = r'''set -euo pipefail
min_soc=20
topic_once() {
  if [[ -n "$FAIL_READ" && "$1" == *"$FAIL_READ"* ]]; then return 124; fi
  case "$1" in
    *battery*) printf 'batsoc: %s\nbatsoc: 22\n' "$SOC";;
    *servo*) echo 'data: 0';;
    *estop*) printf 'data: %s\n' "$ESTOP";;
    *chrg*) printf 'data: %s\n' "$CHARGER";;
  esac
}
''' + body + '\necho ALL_HEALTH_OK\n'
                env = dict(os.environ, SOC=soc, FAIL_READ=failed, CHARGER=charger, ESTOP=estop)
                result = subprocess.run(['bash', '-s'], input=code, text=True,
                                        capture_output=True, env=env, timeout=3)
                self.assertEqual(result.returncode == 0, ok, result.stderr)
                self.assertEqual('ALL_HEALTH_OK' in result.stdout, ok)

    def test_transfer_map_check_never_loads_or_relocalizes(self):
        body = MAP.split('ensure_map_active() {', 1)[1].split("<<'REMOTE'\n", 1)[1].split('\nREMOTE\n', 1)[0]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'umap').mkdir(); (root/'user').mkdir()
            (root/'umap/umap.json').write_text('{}'); (root/'user/task.json').write_text('{}')
            body = body.replace('map_dir="/etc/walker/map/$map_name"', 'map_dir="$MOCK_ROOT"')
            body = body.replace('/tmp/cruzr_map_runtime_', str(root / 'cache_'))
            prefix = '''hostname() { echo vision; }
docker() {
  if [[ "$1" == inspect ]]; then
    if [[ "$3" == *State.Running* ]]; then echo true; else echo instance; fi
    return
  fi
  local payload="${@: -2:1}"
  printf '%s\\n' "$payload" >>"$MOCK_ROOT/actions"
  if [[ "$payload" == *get_map_name* ]]; then
    printf 'Goal accepted\\nstatus=4 "map_name" : "%s"\\n' "$ACTIVE_MAP"
  elif [[ "$payload" == *check_state* ]]; then
    printf 'Goal accepted\\nstatus=4 %s\\n' "$NAV_STATE"
  else
    echo UNEXPECTED_MUTATION >&2
    return 98
  fi
}
'''
            for active, state, map_type, ok in [('MESAS2', 'FSM_WAITNAVIGATE', 'auto', True),
                    ('OTHER', 'FSM_WAITNAVIGATE', 'auto', False),
                    ('MESAS2', 'FSM_RELOCATING', 'auto', False),
                    ('MESAS2', 'FSM_WAITNAVIGATE', 'uslam', False)]:
                (root/'actions').unlink(missing_ok=True)
                env = dict(os.environ, MOCK_ROOT=tmp, ACTIVE_MAP=active, NAV_STATE=state)
                result = subprocess.run(['bash', '-s', '--', 'nav', 'freepnc', 'MESAS2',
                                         '/action', 'Task', map_type, 'table-transfer'],
                                        input=prefix+body, env=env, text=True,
                                        capture_output=True, timeout=4)
                self.assertEqual(result.returncode == 0, ok, result.stderr)
                actions = (root/'actions').read_text()
                self.assertNotIn('map_set', actions)
                self.assertNotIn('relocation_start', actions)
                self.assertEqual(list(root.glob('cache_*')), [])

            env = dict(os.environ, MOCK_ROOT=tmp, ACTIVE_MAP='MESAS2', NAV_STATE='FSM_WAITNAVIGATE')
            result = subprocess.run(['bash','-s','--','nav','freepnc','MESAS2','/action','Task',
                                     'auto','table-transfer','f'*64], input=prefix+body,
                                    env=env,text=True,capture_output=True,timeout=4)
            self.assertEqual(result.returncode,50,result.stderr)
            self.assertIn('MAP_REFERENCE_CHANGED',result.stderr)

    def test_clamp_collector_limits_history_to_current_container(self):
        # Ejecuta el colector remoto con logs separados por un reinicio simulado.
        body = CYCLE.split('verify_clamp_log() {', 1)[1].split("<<'REMOTE'\n", 1)[1].split('\nREMOTE\n', 1)[0]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            marker = "BTree task: 'cruzr/blue_workbin_clamp_only' is start\n"
            success = marker + "left-right-arm tool's distance on base: 0 .58 0\nleft_force_base: 1 20 2\nEnd MetaClamp: clamp_cruzr_byd_large\nBTree tick succeeded\n"
            old = root/'robot_app.old.log'; old.write_text(success)
            new = root/'robot_app.new.log'; new.write_text('New Motion process\n')
            os.utime(old, (100, 100)); os.utime(new, (300, 300))
            code = 'docker() { echo "1970-01-01T00:03:20Z"; }\nsleep() { :; }\n' + body.replace('/etc/walker/log/motion', tmp)
            result = subprocess.run(['bash', '-s', '--', 'motion'], input=code, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            new.write_text(success); os.utime(new, (300, 300))
            result = subprocess.run(['bash', '-s', '--', 'motion'], input=code, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.count(marker.strip()), 1)


if __name__ == '__main__':
    unittest.main()
