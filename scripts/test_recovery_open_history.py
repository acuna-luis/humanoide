#!/usr/bin/env python3
"""Regresiones offline del clasificador remoto real; no conecta ni mueve."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).with_name('cruzr_recover_to_home.sh').read_text()
REMOTE = SOURCE.split("output=\"$(ssh_motion bash -s <<'REMOTE'\n", 1)[1].split('\nREMOTE\n', 1)[0]
REMOTE = re.sub(r'latest="\$\(find .*?\)"', 'latest="$1"', REMOTE, count=1, flags=re.S)


def task(name):
    return "BTree task: '%s' is start, its args: {}\n" % name


CLAMP = task('cruzr/blue_workbin_clamp_only') + 'result: FAILURE\nBTree tick failed\n'
OPEN = task('cruzr/blue_workbin_open_only')
SUCCESS = ('Start MetaClamp: byd/open_arm_cruzr\n'
           'End MetaClamp: byd/open_arm_cruzr\n'
           'meta_name: MetaClamp\n action_name: byd/open_arm_cruzr\n'
           ' result: SUCCESS\nBTree tick succeeded\n')


def classify(log):
    with tempfile.NamedTemporaryFile(mode='w') as fixture:
        fixture.write(log)
        fixture.flush()
        result = subprocess.run(['bash', '-s', '--', fixture.name], input=REMOTE,
                                text=True, capture_output=True, timeout=5)
    if result.returncode:
        raise AssertionError(result.stderr)
    return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)


class RecoveryOpenHistoryTests(unittest.TestCase):
    def test_success_after_failed_grasp(self):
        self.assertEqual(classify(CLAMP + OPEN + SUCCESS)['HISTORICAL_STATE'],
                         'opened_workbin_near_table')

    def test_start_only_does_not_release_held_classification(self):
        for ending in ['', 'Start MetaClamp: byd/open_arm_cruzr\n',
                       SUCCESS.replace('BTree tick succeeded\n', ''),
                       SUCCESS.replace('result: SUCCESS', 'result: FAILURE')]:
            with self.subTest(ending=ending):
                self.assertEqual(classify(CLAMP + OPEN + ending)['HISTORICAL_STATE'],
                                 'open_result_unverified')

    def test_missing_or_wrong_predecessor(self):
        for before in ['', task('teleoperation/cruzr_clamp_pico_teleoperation'),
                       CLAMP + task('unknown/task')]:
            self.assertEqual(classify(before + OPEN + SUCCESS)['HISTORICAL_STATE'],
                             'open_result_unverified')

    def test_later_tasks_supersede_open(self):
        for after, state in [(task('unknown/task'), 'unknown'),
                             (task('teleoperation/cruzr_clamp_pico_teleoperation'), 'teleoperated_pose'),
                             (task('cruzr/blue_workbin_clamp_only'), 'box_may_be_held'),
                             (OPEN, 'open_result_unverified')]:
            self.assertEqual(classify(CLAMP + OPEN + SUCCESS + after)['HISTORICAL_STATE'], state)

    def test_unsafe_or_cancelled_open_is_blocked(self):
        for event in ['Excessive force', 'Self collision between links',
                      'MoveToGoalFailed', 'Operation disabled unexpected',
                      'SAFEOP ERROR', 'goal canceled', 'btree_status is FAILURE']:
            self.assertEqual(classify(CLAMP + OPEN + SUCCESS + event)['HISTORICAL_STATE'],
                             'open_result_unverified')

    def test_multiple_primitives_not_accepted(self):
        self.assertEqual(classify(CLAMP + OPEN + SUCCESS + SUCCESS)['HISTORICAL_STATE'],
                         'open_result_unverified')

    def test_no_open_keeps_box_blocked(self):
        self.assertEqual(classify(CLAMP)['HISTORICAL_STATE'], 'box_may_be_held')

    def test_route_selects_retreat_and_home_only_for_completed_open(self):
        prefix = SOURCE.rsplit('\nmain\n', 1)[0]
        for state, ok in [('opened_workbin_near_table', True), ('open_result_unverified', False)]:
            code = (prefix + '\nMEASURED_HOME=0\nUNSAFE_AFTER_STATE=0\n'
                    + 'HISTORICAL_STATE=' + state + '\nselect_recovery_route\n'
                    + '[[ "$RETREAT_REQUIRED" == true && "$HOME_ACTION_REQUIRED" == true ]]\n')
            result = subprocess.run(['bash', '-s'], input=code, text=True, capture_output=True)
            self.assertEqual(result.returncode == 0, ok, result.stderr)


if __name__ == '__main__':
    unittest.main()
