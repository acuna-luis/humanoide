"""Continuous-run pause/resume contracts; no ROS, network, or physical actions.

A requested pause closes only the non-motion postcondition belonging to the
current action. The runtime/CLI integration tests exercise signal delivery;
these cases keep the persisted state machine and resume requirements explicit.
"""
import copy
import unittest

from scripts.box_handling import scenario1_contract as contract
from scripts.box_handling import scenario1_cli as cli
from scripts.box_handling.scenario1_resume import plan_resume
from scripts.box_handling.test_scenario1_contract import profile


PROFILE = profile()
EXECUTION = 'optimistic_v1'
POSTCONDITIONS = {'grasp': 'verify_held', 'deposit': 'verify_released',
                  'home': 'verify_home'}


def fresh():
    return contract.new_checkpoint(PROFILE, policy='assume', execution_profile=EXECUTION)


def finish(checkpoint, stage):
    arguments = {'home_verified': stage == 'verify_home'}
    if stage in ('verify_held', 'verify_released'):
        arguments.update(confirmed_box='held' if stage == 'verify_held' else 'released',
                         verification_source='assumed')
    return contract.complete_stage(contract.begin_stage(checkpoint, stage), stage, **arguments)


def through(stage, checkpoint=None):
    checkpoint = fresh() if checkpoint is None else checkpoint
    start = contract.progress_index(checkpoint)
    for current in contract.STAGES[start:contract.STAGES.index(stage) + 1]:
        checkpoint = finish(checkpoint, current)
    return checkpoint


class CyclePauseBoundaryTests(unittest.TestCase):
    def test_pause_decision_waits_only_for_the_current_actions_nonmotion_postcondition(self):
        self.assertTrue(cli.should_pause(fresh(), True))
        for stage in contract.STAGES:
            with self.subTest(stage=stage):
                checkpoint = through(stage)
                original = copy.deepcopy(checkpoint)
                self.assertFalse(cli.should_pause(checkpoint, False))
                self.assertEqual(cli.should_pause(checkpoint, True), stage not in POSTCONDITIONS)
                self.assertEqual(checkpoint, original)

    def test_every_nonfinal_pause_resumes_next_physical_step_without_recovery(self):
        expected = {
            'navigate_get1': ('enable_vision', 'empty', 'get1', True),
            'enable_vision': ('grasp', 'empty', 'get1', True),
            'grasp': ('retreat', 'held', 'get1', False),
            'verify_held': ('retreat', 'held', 'get1', False),
            'retreat': ('navigate_put1', 'held', None, False),
            'navigate_put1': ('deposit', 'held', 'put1', False),
            'deposit': ('home', 'released', None, False),
            'verify_released': ('home', 'released', None, False),
        }
        for interrupted, (following, box, waypoint, home) in expected.items():
            with self.subTest(interrupted=interrupted):
                checkpoint = through(interrupted)
                if interrupted in POSTCONDITIONS:
                    self.assertFalse(cli.should_pause(checkpoint, True))
                    checkpoint = finish(checkpoint, POSTCONDITIONS[interrupted])
                self.assertTrue(cli.should_pause(checkpoint, True))
                original = copy.deepcopy(checkpoint)
                planned = plan_resume(checkpoint, PROFILE, execution_profile=EXECUTION)
                self.assertEqual(checkpoint, original)
                self.assertEqual(planned['stage'], following)
                self.assertEqual(planned['requirements']['box_state'], box)
                self.assertEqual(planned['requirements']['waypoint'], waypoint)
                self.assertEqual(planned['requirements']['home'], home)
                self.assertEqual(planned['checkpoint']['completed'], [])
                self.assertEqual(planned['checkpoint']['confirmations'], {})
                self.assertFalse(planned['checkpoint']['origin']['recovery_confirmed'])
                self.assertFalse(planned['checkpoint']['origin']['explicit_state'])
                self.assertEqual(planned['checkpoint']['origin']['skipped_stages'], [])
                self.assertEqual(planned['checkpoint']['origin']['repeated_stages'], [])

    def test_post_grasp_and_deposit_do_not_become_known_until_verification_completes(self):
        for stage, verification, box in (('grasp', 'verify_held', 'held'),
                                         ('deposit', 'verify_released', 'released')):
            with self.subTest(stage=stage):
                incomplete = through(stage)
                self.assertEqual(incomplete['box_state'], 'unknown')
                self.assertEqual(contract.next_stage(incomplete), verification)
                with self.assertRaisesRegex(ValueError, 'Recovery requires'):
                    plan_resume(incomplete, PROFILE, execution_profile=EXECUTION)
                checkpoint = finish(incomplete, verification)
                self.assertEqual(checkpoint['box_state'], box)
                self.assertEqual(checkpoint['confirmations'][verification], {
                    'box_state': box, 'source': 'assumed', 'sensor_evidence': None})

    def test_home_action_success_alone_is_not_a_completed_cycle(self):
        checkpoint = through('home')
        self.assertEqual(contract.next_stage(checkpoint), 'verify_home')
        planned = plan_resume(checkpoint, PROFILE, execution_profile=EXECUTION)
        self.assertEqual(planned['stage'], 'verify_home')
        self.assertTrue(planned['requirements']['home'])
        active = contract.begin_stage(checkpoint, 'verify_home')
        with self.assertRaisesRegex(ValueError, 'Fresh HOME'):
            contract.complete_stage(active, 'verify_home')
        complete = contract.complete_stage(active, 'verify_home', home_verified=True)
        self.assertIsNone(contract.next_stage(complete))
        self.assertEqual(complete['box_state'], 'released')

    def test_failure_during_pause_postcondition_never_becomes_a_clean_resume(self):
        for action, verification in POSTCONDITIONS.items():
            with self.subTest(action=action):
                checkpoint = through(action)
                checkpoint = contract.fail_stage(contract.begin_stage(checkpoint, verification),
                    verification, 'postcondition unavailable')
                self.assertEqual(checkpoint['box_state'], 'unknown')
                self.assertNotIn(verification, checkpoint['completed'])
                with self.assertRaisesRegex(ValueError, 'Recovery requires'):
                    plan_resume(checkpoint, PROFILE, execution_profile=EXECUTION)

    def test_fresh_next_cycle_checkpoint_resumes_get1_without_repeating_previous_history(self):
        completed = through('verify_home')
        completed_snapshot = copy.deepcopy(completed)
        new_cycle = fresh()
        planned = plan_resume(new_cycle, PROFILE, execution_profile=EXECUTION)
        self.assertEqual(planned['stage'], 'navigate_get1')
        self.assertEqual(planned['requirements'], {
            'box_state': 'empty', 'home': True, 'waypoint': None, 'vision_prep': False})
        self.assertEqual(planned['checkpoint']['completed'], [])
        self.assertEqual(planned['checkpoint']['confirmations'], {})
        self.assertEqual(planned['checkpoint']['origin']['repeated_stages'], [])
        self.assertEqual(planned['checkpoint']['origin']['skipped_stages'], [])
        self.assertFalse(planned['checkpoint']['origin']['recovery_confirmed'])
        self.assertEqual(completed, completed_snapshot)
        self.assertEqual(completed['completed'], list(contract.STAGES))

    def test_resumed_segment_can_finish_then_start_an_independent_full_cycle(self):
        checkpoint = through('verify_held')
        segment = plan_resume(checkpoint, PROFILE, execution_profile=EXECUTION)['checkpoint']
        segment = through('verify_home', segment)
        self.assertEqual(segment['completed'], list(contract.STAGES[4:]))
        self.assertEqual(set(segment['confirmations']), {'verify_released'})
        self.assertIsNone(contract.next_stage(segment))
        next_cycle = through('verify_home', fresh())
        self.assertEqual(next_cycle['completed'], list(contract.STAGES))
        self.assertEqual(set(next_cycle['confirmations']), {'verify_held', 'verify_released'})
        self.assertEqual(next_cycle['execution_profile'], EXECUTION)

    def test_completed_cycle_is_not_implicitly_reused_as_a_resume_source(self):
        # Rollover creates a new journaled checkpoint. Feeding the old completed
        # one to the ordinary resume API must retain the existing rejection.
        with self.assertRaisesRegex(ValueError, 'already complete'):
            plan_resume(through('verify_home'), PROFILE, execution_profile=EXECUTION)


if __name__ == '__main__':
    unittest.main()
