#!/usr/bin/env python3
"""Contrato HOME del preflight real con Docker simulado, sin robot ni red."""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import unittest

SCRIPTS = Path(__file__).resolve().parent
CYCLE = (SCRIPTS / 'cruzr_blue_workbin_cycle.sh').read_text()
AUDITOR = (SCRIPTS / 'vla/audit_vla_live_preflight_e6_0g.sh').read_text()
TASK_ROOT = '/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config'
META_ROOT = '/opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config'
HOME = TASK_ROOT + '/cruzr/home.xml'
LIB = '/opt/walker/manipulation_meta_tasks/lib/libmeta_move.so'
PINS = dict(re.findall(r'^readonly (\w+_SHA)="([0-9a-f]{64})"$', CYCLE, re.M))


class HomeContractTests(unittest.TestCase):
    def hashes(self):
        return {
            TASK_ROOT + '/cruzr/move_head_lower.xml': PINS['HEAD_LOWER_SHA'],
            TASK_ROOT + '/transport/clamp_ready_cruzr.xml': PINS['ARMS_READY_SHA'],
            TASK_ROOT + '/cruzr/open_arm_before_home.xml': PINS['HOME_SHA'],
            HOME: PINS['OPEN_HOME_SHA'], LIB: PINS['OPEN_HOME_META_SHA'],
            META_ROOT + '/meta_clamp/clamp_cruzr_byd_large.yaml': PINS['CLAMP_META_SHA'],
            META_ROOT + '/meta_clamp/put_collision_cruzr.yaml': PINS['DEPOSIT_META_SHA'],
            META_ROOT + '/meta_clamp/byd/open_arm_cruzr.yaml': PINS['OPEN_META_SHA'],
        }

    def check(self, hashes):
        block = 'check_hash() {' + CYCLE.split('check_hash() {', 1)[1].split('\nmotion_info=', 1)[0]
        mapping = {'head_sha':'HEAD_LOWER_SHA', 'ready_sha':'ARMS_READY_SHA',
                   'home_sha':'HOME_SHA', 'direct_home_sha':'DIRECT_HOME_SHA',
                   'open_home_sha':'OPEN_HOME_SHA', 'open_home_meta_sha':'OPEN_HOME_META_SHA',
                   'clamp_meta_sha':'CLAMP_META_SHA', 'deposit_meta_sha':'DEPOSIT_META_SHA',
                   'open_meta_sha':'OPEN_META_SHA'}
        prefix = 'set -Eeuo pipefail\nmotion_container=mock\n'
        prefix += ''.join(f'{name}={shlex.quote(PINS[pin])}\n' for name,pin in mapping.items())
        prefix += '''docker() {
  [[ "$#" == 4 && "$1" == exec && "$2" == mock && "$3" == sha256sum ]] || exit 99
  python3 -c 'import json,os,sys; print(json.loads(os.environ["MOCK_HASHES"])[sys.argv[1]]+"  "+sys.argv[1])' "$4"
}
'''
        return subprocess.run(['bash', '-s'], input=prefix+block+'\necho ALL_HASHES_OK\n',
                              text=True, capture_output=True, timeout=5,
                              env=dict(os.environ, MOCK_HASHES=json.dumps(hashes)))

    def test_reviewed_overlay_and_vendor_original_recognized(self):
        for pin, label in [('OPEN_HOME_SHA', 'open-v3-20s'), ('DIRECT_HOME_SHA', 'vendor-direct-6s')]:
            hashes = self.hashes(); hashes[HOME] = PINS[pin]
            if pin == 'DIRECT_HOME_SHA':
                del hashes[LIB]  # The original does not use the relative-angle overlay contract.
            result = self.check(hashes)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('INTERNAL_HOME_VARIANT='+label, result.stdout)
            self.assertIn('ALL_HASHES_OK', result.stdout)

    def test_unknown_home_or_library_rejected(self):
        for path in (HOME, LIB):
            hashes = self.hashes(); hashes[path] = 'a'*64
            result = self.check(hashes)
            self.assertEqual(result.returncode, 24, result.stderr)
            self.assertIn('HASH_ERROR='+path, result.stdout)
            self.assertNotIn('ALL_HASHES_OK', result.stdout)

    def test_missing_home_or_library_rejected(self):
        for path in (HOME, LIB):
            hashes = self.hashes(); del hashes[path]
            result = self.check(hashes)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn('ALL_HASHES_OK', result.stdout)

    def test_other_task_and_primitive_hashes_still_required(self):
        for path in self.hashes().keys() - {HOME, LIB}:
            hashes = self.hashes(); hashes[path] = 'b'*64
            result = self.check(hashes)
            self.assertEqual(result.returncode, 24, result.stderr)
            self.assertIn('HASH_ERROR='+path, result.stdout)
            self.assertNotIn('ALL_HASHES_OK', result.stdout)

    def test_pins_match_installer_and_exact_local_xml(self):
        tree = ast.parse((SCRIPTS / 'teleoperation/cruzr_install_internal_home.py').read_text())
        values = {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body
                  if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
                  and n.targets[0].id in {'BASE_SHA','NEW_SHA','META_LIB','META_SHA'}}
        self.assertEqual(PINS['DIRECT_HOME_SHA'], values['BASE_SHA'])
        self.assertEqual(PINS['OPEN_HOME_SHA'], values['NEW_SHA'])
        self.assertEqual(PINS['OPEN_HOME_META_SHA'], values['META_SHA'])
        self.assertEqual(LIB, values['META_LIB'])
        xml = SCRIPTS / 'teleoperation/tasks/cruzr_internal_home_open_v3_20s.xml'
        self.assertEqual(hashlib.sha256(xml.read_bytes()).hexdigest(), values['NEW_SHA'])

    def test_auditor_preserves_failure_without_misdiagnosing_boot(self):
        block = '  if ! manipulation_status=' + AUDITOR.split('  if ! manipulation_status=', 1)[1].split("\n  grep -Fq 'ACTUATORS_", 1)[0]
        for message, reason in [('HASH_ERROR='+HOME+':bad', 'config-hash'),
                                ('ACTUATOR_GATE=FAULT', 'canonical-check')]:
            prefix = ('set -euo pipefail\nsnapshot="MANIPULATION_ACTION_SERVERS=1"\n'
                      'shadow_status="COMMAND_PATH_SAFE=publishers:0"\n'
                      'MANIPULATION_CHECK=canonical_fail\n'
                      'canonical_fail() { printf "%s\\n" "$MOCK_FAILURE"; return 47; }\n')
            result = subprocess.run(['bash', '-s'], input=prefix+block+'\necho SHOULD_NOT_CONTINUE\n',
                                    text=True, capture_output=True, timeout=3,
                                    env=dict(os.environ, MOCK_FAILURE=message))
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn(message, result.stdout)
            self.assertIn('PREFLIGHT_FAILURE='+reason, result.stderr)
            self.assertNotIn('WaitStartMotion', result.stderr)
            self.assertNotIn('Power/KEY1', result.stderr)
            self.assertNotIn('SHOULD_NOT_CONTINUE', result.stdout)


if __name__ == '__main__':
    unittest.main()
