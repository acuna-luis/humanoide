"""Durable one-retry HOME budget and recovery lineage; no ROS or filesystem IO."""
import copy
import json
import unittest

from scripts.box_handling import scenario1_contract as contract
from scripts.box_handling.scenario1_resume import plan_resume
from scripts.box_handling.test_scenario1_contract import profile
from scripts.box_handling.test_scenario1_resume import finish


GOAL_ID = 'b37ade53-a203-4eb7-a1c9-964c3f80d1de'


def failed_result():
    return dict(event='result', goal_id=GOAL_ID, status=6,
                result={'state': {'state': 7104050, 'desc': 'MoveToGoalFailed'}})


def before(stage='home', *, policy='assume', execution_profile='optimistic_v1'):
    cp = contract.new_checkpoint(profile(), policy=policy, execution_profile=execution_profile)
    for current in contract.STAGES[:contract.STAGES.index(stage)]:
        cp = finish(cp, current)
    return cp


def active_home():
    return contract.begin_stage(before(), 'home')


def reserved_home():
    return contract.reserve_home_retry(active_home(), failed_result(),
                                       first_result_ns=1000, reserved_ns=1001)


def resume(source, stage='home'):
    return plan_resume(source, profile(), stage=stage,
                       box_state=contract.ENTRY_BOX_STATES[stage], recovery_confirmed=True,
                       policy='assume', execution_profile='optimistic_v1')['checkpoint']


class HomeRetryCheckpointTest(unittest.TestCase):
    def test_reservation_is_an_independent_exact_record_and_preserves_progress(self):
        cp, result = active_home(), failed_result()
        old_cp, old_result = copy.deepcopy(cp), copy.deepcopy(result)
        result['request_id'] = '27'
        result['result']['state']['header'] = {'stamp': {'sec': 0, 'nanosec': 0}}
        reserved = contract.reserve_home_retry(cp, result, first_result_ns=1000, reserved_ns=1001)
        self.assertEqual(reserved['home_retry'], dict(version=1, used=1,
            failed_goal_id=GOAL_ID, first_result_ns=1000, reserved_ns=1001,
            status=6, code=7104050, desc='MoveToGoalFailed'))
        self.assertEqual(reserved['completed'], cp['completed'])
        self.assertEqual(reserved['in_flight'], 'home')
        self.assertIsNone(reserved['failure'])
        self.assertEqual(cp, old_cp)
        self.assertEqual(result['goal_id'], old_result['goal_id'])
        self.assertEqual(contract.validate_checkpoint(json.loads(json.dumps(reserved))), reserved)
        reserved['confirmations']['verify_released']['source'] = 'tampered'
        self.assertEqual(cp, old_cp)

    def test_retry_available_only_for_the_eligible_active_stage(self):
        for stage in contract.STAGES:
            for policy, execution in (('assume', 'optimistic_v1'), ('assume', 'standard_v1'),
                                      ('ask', 'standard_v1'), ('sensors', 'standard_v1')):
                with self.subTest(stage=stage, policy=policy, execution=execution):
                    cp = before(stage, policy=policy, execution_profile=execution)
                    self.assertFalse(contract.home_retry_available(cp))
                    active = contract.begin_stage(cp, stage)
                    expected = stage == 'home' and execution == 'optimistic_v1'
                    self.assertEqual(contract.home_retry_available(active), expected)
                    if not expected:
                        with self.assertRaises(ValueError):
                            contract.reserve_home_retry(active, failed_result(),
                                first_result_ns=1000, reserved_ns=1001)

    def test_second_reservation_is_rejected_before_any_new_dispatch(self):
        cp = reserved_home()
        self.assertFalse(contract.home_retry_available(cp))
        with self.assertRaisesRegex(ValueError, 'unavailable'):
            contract.reserve_home_retry(cp, failed_result(), first_result_ns=2000, reserved_ns=2001)
        self.assertEqual(cp['home_retry']['first_result_ns'], 1000)

    def test_abort_must_have_the_exact_native_status_code_and_description(self):
        for path, values in (
            (('event',), ('interrupted_terminal', 'error', None)),
            (('status',), (4, 5, True, '6', 6.0, None)),
            (('result', 'state', 'state'), (1101001, 7104051, True, '7104050', 7104050.0, None)),
            (('result', 'state', 'desc'), ('SUCCEED', 'movetogoalfailed', '', None)),
        ):
            for value in values:
                with self.subTest(path=path, value=value):
                    result = failed_result()
                    target = result
                    for key in path[:-1]:
                        target = target[key]
                    target[path[-1]] = value
                    with self.assertRaises(ValueError):
                        contract.reserve_home_retry(active_home(), result,
                            first_result_ns=1000, reserved_ns=1001)

    def test_missing_or_malformed_results_cannot_reserve_a_retry(self):
        variants = [None, [], 'MoveToGoalFailed', {},
                    {'event': 'result', 'goal_id': GOAL_ID, 'status': 6, 'result': None},
                    {'event': 'result', 'goal_id': GOAL_ID, 'status': 6, 'result': {'state': []}}]
        for key in failed_result():
            row = failed_result()
            row.pop(key)
            variants.append(row)
        row = failed_result()
        row['extra'] = float('nan')
        variants.append(row)
        for result in variants:
            with self.subTest(result=result), self.assertRaises(ValueError):
                contract.reserve_home_retry(active_home(), result,
                    first_result_ns=1000, reserved_ns=1001)

    def test_retry_requires_a_canonical_nonzero_goal_uuid(self):
        for value in (None, '', True, 123, GOAL_ID.upper(), GOAL_ID.replace('-', ''),
                      '{'+GOAL_ID+'}', ' '+GOAL_ID, '00000000-0000-0000-0000-000000000000'):
            with self.subTest(value=value):
                result = failed_result()
                result['goal_id'] = value
                with self.assertRaises(ValueError):
                    contract.reserve_home_retry(active_home(), result,
                        first_result_ns=1000, reserved_ns=1001)

    def test_timestamps_are_positive_integer_nanoseconds_and_ordered(self):
        for first, reserved in ((0, 1), (-1, 1), (True, 1), (1.0, 2), ('1', 2),
                                (1, None), (1, False), (1, 1.0), (2, 1)):
            with self.subTest(first=first, reserved=reserved), self.assertRaises(ValueError):
                contract.reserve_home_retry(active_home(), failed_result(),
                    first_result_ns=first, reserved_ns=reserved)
        self.assertEqual(contract.reserve_home_retry(active_home(), failed_result(),
            first_result_ns=1000, reserved_ns=1000)['home_retry']['used'], 1)

    def test_ledger_cannot_be_relaxed_with_extra_missing_or_invalid_fields(self):
        original = reserved_home()
        variants = []
        for key in original['home_retry']:
            cp = copy.deepcopy(original)
            cp['home_retry'].pop(key)
            variants.append(cp)
        for key, value in (('version', True), ('version', 2), ('used', 0), ('used', 2),
                           ('used', True), ('status', 4), ('code', 1101001),
                           ('desc', 'SUCCEED'), ('failed_goal_id', 'g1'),
                           ('first_result_ns', 0), ('reserved_ns', 999), ('unknown', 1)):
            cp = copy.deepcopy(original)
            cp['home_retry'][key] = value
            variants.append(cp)
        for value in (None, [], 'used'):
            cp = copy.deepcopy(original)
            cp['home_retry'] = value
            variants.append(cp)
        for cp in variants:
            with self.subTest(ledger=cp['home_retry']), self.assertRaises(ValueError):
                contract.validate_checkpoint(cp)

    def test_ledger_cannot_appear_in_standard_or_legacy_checkpoints(self):
        for policy in ('ask', 'assume', 'sensors'):
            cp = contract.begin_stage(before(policy=policy, execution_profile='standard_v1'), 'home')
            cp['home_retry'] = reserved_home()['home_retry']
            with self.subTest(policy=policy), self.assertRaises(ValueError):
                contract.validate_checkpoint(cp)
        cp = contract.begin_stage(before(policy='ask', execution_profile='standard_v1'), 'home')
        cp.update(version=1, home_retry=reserved_home()['home_retry'])
        cp.pop('policy')
        cp.pop('confirmations')
        with self.assertRaises(ValueError):
            contract.validate_checkpoint(cp)

    def test_old_checkpoints_keep_their_exact_serialized_shape(self):
        for execution, policy in (('standard_v1', 'ask'), ('optimistic_v1', 'assume')):
            cp = before(execution_profile=execution, policy=policy)
            serialized = json.dumps(cp, sort_keys=True)
            self.assertEqual(json.dumps(contract.validate_checkpoint(cp), sort_keys=True), serialized)
            self.assertNotIn('home_retry', cp)

    def test_success_still_requires_separate_home_verification_and_keeps_ledger(self):
        cp = reserved_home()
        after_home = contract.complete_stage(cp, 'home')
        self.assertEqual(contract.next_stage(after_home), 'verify_home')
        self.assertEqual(after_home['home_retry'], cp['home_retry'])
        active = contract.begin_stage(after_home, 'verify_home')
        with self.assertRaises(ValueError):
            contract.complete_stage(active, 'verify_home')
        finished = contract.complete_stage(active, 'verify_home', home_verified=True)
        self.assertIsNone(contract.next_stage(finished))
        self.assertEqual(finished['home_retry'], cp['home_retry'])

    def test_failed_second_attempt_keeps_failure_and_consumed_budget(self):
        cp = reserved_home()
        failed = contract.fail_stage(cp, 'home', 'second attempt aborted')
        self.assertEqual(failed['failure'], {'stage': 'home', 'reason': 'second attempt aborted'})
        self.assertEqual(failed['box_state'], 'unknown')
        self.assertEqual(failed['home_retry'], cp['home_retry'])
        self.assertFalse(contract.home_retry_available(failed))

    def test_crash_after_reservation_and_failed_attempt_both_keep_budget_on_resume(self):
        cp = reserved_home()
        for source in (cp, contract.fail_stage(cp, 'home', 'second attempt aborted')):
            with self.subTest(failure=source['failure']):
                resumed = resume(source)
                self.assertEqual(resumed['home_retry'], source['home_retry'])
                self.assertIsNot(resumed['home_retry'], source['home_retry'])
                self.assertFalse(contract.home_retry_available(contract.begin_stage(resumed, 'home')))
                self.assertEqual(resumed['origin']['source_failure'], source['failure'])
                self.assertEqual(resumed['origin']['source_in_flight'], source['in_flight'])

    def test_nested_recoveries_and_rewinds_never_reset_the_budget(self):
        cp = reserved_home()
        for _ in range(3):
            cp = contract.fail_stage(cp, 'home', 'interrupted again')
            cp = contract.begin_stage(resume(cp), 'home')
            self.assertFalse(contract.home_retry_available(cp))
            self.assertEqual(cp['home_retry']['failed_goal_id'], GOAL_ID)
        rewind = resume(cp, 'navigate_get1')
        for stage in contract.STAGES[:contract.STAGES.index('home')]:
            rewind = finish(rewind, stage)
        self.assertFalse(contract.home_retry_available(contract.begin_stage(rewind, 'home')))

    def test_verification_only_resume_retains_evidence_without_ordering_home(self):
        failed = contract.fail_stage(reserved_home(), 'home', 'terminal aborted')
        resumed = resume(failed, 'verify_home')
        self.assertEqual(contract.next_stage(resumed), 'verify_home')
        self.assertEqual(resumed['home_retry'], failed['home_retry'])
        self.assertFalse(contract.home_retry_available(resumed))

    def test_only_a_new_cycle_gets_a_new_budget(self):
        completed = contract.complete_stage(reserved_home(), 'home')
        completed = finish(completed, 'verify_home')
        resumed = resume(completed)
        self.assertFalse(contract.home_retry_available(contract.begin_stage(resumed, 'home')))
        fresh = contract.new_checkpoint(profile(), policy='assume', execution_profile='optimistic_v1')
        self.assertNotIn('home_retry', fresh)
        for stage in contract.STAGES[:contract.STAGES.index('home')]:
            fresh = finish(fresh, stage)
        self.assertTrue(contract.home_retry_available(contract.begin_stage(fresh, 'home')))

    def test_stale_pc_checkpoint_cannot_grant_another_automatic_retry(self):
        # Remote may have fsynced the reservation and dispatched its second
        # goal while the PC still only knows that the first HOME is in flight.
        stale = active_home()
        before_recovery = copy.deepcopy(stale)
        resumed = resume(stale)
        self.assertIs(resumed['home_retry_blocked'], True)
        self.assertNotIn('home_retry', resumed)
        active = contract.begin_stage(resumed, 'home')
        self.assertFalse(contract.home_retry_available(active))
        with self.assertRaisesRegex(ValueError, 'unavailable'):
            contract.reserve_home_retry(active, failed_result(), first_result_ns=1000, reserved_ns=1001)
        # Explicitly confirmed recovery HOME itself remains executable and can
        # finish normally; only its automatic repetition is withheld.
        completed = contract.complete_stage(active, 'home')
        self.assertEqual(contract.next_stage(completed), 'verify_home')
        self.assertEqual(stale, before_recovery)

    def test_home_failure_without_ledger_is_also_an_uncertain_budget(self):
        failed = contract.fail_stage(active_home(), 'home', 'transport lost after native result')
        resumed = resume(failed)
        self.assertIs(resumed['home_retry_blocked'], True)
        self.assertNotIn('home_retry', resumed)
        self.assertEqual(resumed['origin']['source_failure'], failed['failure'])
        self.assertFalse(contract.home_retry_available(contract.begin_stage(resumed, 'home')))

    def test_uncertain_budget_survives_nested_resumes_rewinds_and_completion(self):
        cp = resume(active_home())
        for _ in range(3):
            active = contract.begin_stage(cp, 'home')
            failed = contract.fail_stage(active, 'home', 'explicit recovery interrupted')
            cp = resume(failed)
            self.assertIs(cp['home_retry_blocked'], True)
            self.assertNotIn('home_retry', cp)
        rewind = resume(cp, 'navigate_get1')
        for stage in contract.STAGES[:contract.STAGES.index('home')]:
            rewind = finish(rewind, stage)
        active = contract.begin_stage(rewind, 'home')
        self.assertFalse(contract.home_retry_available(active))
        complete = finish(contract.complete_stage(active, 'home'), 'verify_home')
        repeated = resume(complete)
        self.assertIs(repeated['home_retry_blocked'], True)
        self.assertFalse(contract.home_retry_available(contract.begin_stage(repeated, 'home')))

    def test_clean_pause_before_home_retains_available_budget(self):
        clean = before()
        resumed = resume(clean)
        self.assertNotIn('home_retry_blocked', resumed)
        self.assertNotIn('home_retry', resumed)
        self.assertTrue(contract.home_retry_available(contract.begin_stage(resumed, 'home')))

    def test_non_home_failure_does_not_invent_an_uncertain_home_budget(self):
        active = contract.begin_stage(before('deposit'), 'deposit')
        failed = contract.fail_stage(active, 'deposit', 'deposit failed')
        resumed = resume(failed)
        self.assertNotIn('home_retry_blocked', resumed)
        self.assertTrue(contract.home_retry_available(contract.begin_stage(resumed, 'home')))

    def test_new_cycle_resets_uncertain_budget_without_mutating_its_origin(self):
        completed = finish(contract.complete_stage(
            contract.begin_stage(resume(active_home()), 'home'), 'home'), 'verify_home')
        self.assertIs(completed['home_retry_blocked'], True)
        fresh = before()
        self.assertNotIn('home_retry_blocked', fresh)
        self.assertTrue(contract.home_retry_available(contract.begin_stage(fresh, 'home')))
        self.assertIs(completed['home_retry_blocked'], True)

    def test_uncertain_marker_requires_literal_true_in_an_optimistic_checkpoint(self):
        for value in (False, 0, 1, None, 'true', [], {}):
            cp = active_home()
            cp['home_retry_blocked'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                contract.validate_checkpoint(cp)
        for policy in ('ask', 'assume', 'sensors'):
            cp = before(policy=policy, execution_profile='standard_v1')
            cp['home_retry_blocked'] = True
            with self.subTest(policy=policy), self.assertRaises(ValueError):
                contract.validate_checkpoint(cp)
        legacy = before(policy='ask', execution_profile='standard_v1')
        legacy.update(version=1, home_retry_blocked=True)
        legacy.pop('policy')
        legacy.pop('confirmations')
        with self.assertRaises(ValueError):
            contract.validate_checkpoint(legacy)


if __name__ == '__main__':
    unittest.main()
