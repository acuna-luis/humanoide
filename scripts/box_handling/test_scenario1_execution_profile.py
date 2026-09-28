"""Pure execution-profile identity tests; no network, robot or file writes."""
import copy
import hashlib
import json
import unittest

from scripts.box_handling import scenario1_contract as contract
from scripts.box_handling.scenario1_resume import plan_resume


STANDARD = 'standard_v1'
OPTIMISTIC = 'optimistic_v1'


def profile():
    return dict(id='execution_identity_fixture', box_size_m=[.603, .397, .220],
                intended_use='separate_nested_box',
                grasp=dict(task='local_front_box/separate_right_cruzr',
                           compatibility='operator_assumed_existing'),
                deposit=dict(task='wrc_cruzr/put_cruzr_wrc_low',
                             compatibility='operator_assumed_existing'))


def finish(checkpoint, stage):
    arguments = dict(home_verified=stage == 'verify_home')
    if stage in ('verify_held', 'verify_released'):
        arguments.update(confirmed_box='held' if stage == 'verify_held' else 'released',
                         verification_source='assumed')
    return contract.complete_stage(contract.begin_stage(checkpoint, stage), stage, **arguments)


def held(execution=STANDARD):
    checkpoint = contract.new_checkpoint(profile(), policy='assume',
                                        execution_profile=execution, stop_after='verify_held')
    for stage in contract.STAGES[:4]:
        checkpoint = finish(checkpoint, stage)
    return checkpoint


def digest(checkpoint):
    return hashlib.sha256(json.dumps(checkpoint, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


class ExecutionProfileContractTest(unittest.TestCase):
    def test_default_standard_preserves_legacy_v2_keys_and_identity(self):
        checkpoint = contract.new_checkpoint(profile(), policy='assume')
        self.assertEqual(set(checkpoint), {
            'version', 'profile_id', 'profile_sha256', 'stop_after', 'completed',
            'in_flight', 'box_state', 'failure', 'policy', 'confirmations'})
        before = copy.deepcopy(checkpoint)
        self.assertEqual(contract.execution_profile(checkpoint), STANDARD)
        self.assertEqual(contract.validate_checkpoint(checkpoint, profile()), before)
        self.assertEqual(checkpoint, before)
        self.assertEqual(checkpoint, contract.new_checkpoint(
            profile(), policy='assume', execution_profile=STANDARD))

    def test_optimistic_identity_is_separate_from_geometry_and_survives_roundtrip(self):
        standard = contract.new_checkpoint(profile(), policy='assume')
        optimistic = contract.new_checkpoint(profile(), policy='assume', execution_profile=OPTIMISTIC)
        self.assertEqual(optimistic['version'], 2)
        self.assertEqual(optimistic['execution_profile'], OPTIMISTIC)
        self.assertEqual(optimistic['profile_id'], standard['profile_id'])
        self.assertEqual(optimistic['profile_sha256'], standard['profile_sha256'])
        restored = contract.validate_checkpoint(json.loads(json.dumps(optimistic)), profile())
        self.assertEqual(contract.execution_profile(restored), OPTIMISTIC)
        self.assertNotEqual(digest(restored), digest(standard))

    def test_optimistic_requires_assume_during_construction_and_validation(self):
        for policy in ('ask', 'sensors'):
            with self.subTest(policy=policy):
                with self.assertRaisesRegex(ValueError, 'requires assume'):
                    contract.new_checkpoint(profile(), policy=policy, execution_profile=OPTIMISTIC)
                checkpoint = contract.new_checkpoint(profile(), policy=policy)
                checkpoint['execution_profile'] = OPTIMISTIC
                with self.assertRaisesRegex(ValueError, 'requires assume'):
                    contract.validate_checkpoint(checkpoint, profile())
                with self.assertRaisesRegex(ValueError, 'requires assume'):
                    contract.execution_profile(checkpoint)

    def test_unknown_or_false_execution_identity_never_defaults_to_standard(self):
        for value in ('optimistic', 'standard_v2', '', None, False, True, 1, [], {}):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, 'Unknown execution profile'):
                    contract.new_checkpoint(profile(), policy='assume', execution_profile=value)
                checkpoint = contract.new_checkpoint(profile(), policy='assume')
                checkpoint['execution_profile'] = value
                with self.assertRaisesRegex(ValueError, 'Unknown execution profile'):
                    contract.validate_checkpoint(checkpoint)

    def test_explicit_standard_field_is_valid_but_unknown_fields_are_not(self):
        checkpoint = contract.new_checkpoint(profile(), policy='assume')
        checkpoint['execution_profile'] = STANDARD
        self.assertEqual(contract.validate_checkpoint(checkpoint), checkpoint)
        checkpoint['skip_health_checks'] = True
        with self.assertRaisesRegex(ValueError, 'unknown fields'):
            contract.validate_checkpoint(checkpoint)

    def test_v1_is_standard_and_cannot_smuggle_an_execution_field(self):
        checkpoint = contract.new_checkpoint(profile(), policy='ask')
        checkpoint['version'] = 1
        del checkpoint['policy'], checkpoint['confirmations']
        before = copy.deepcopy(checkpoint)
        self.assertEqual(contract.execution_profile(checkpoint), STANDARD)
        self.assertEqual(contract.validate_checkpoint(checkpoint), before)
        planned = plan_resume(checkpoint, profile(), policy='ask')
        self.assertEqual(contract.execution_profile(planned['checkpoint']), STANDARD)
        self.assertNotIn('execution_profile', planned['checkpoint'])
        for execution in (STANDARD, OPTIMISTIC):
            changed = dict(checkpoint, execution_profile=execution)
            with self.subTest(execution=execution), self.assertRaises(ValueError):
                contract.validate_checkpoint(changed)
        self.assertEqual(checkpoint, before)

    def test_all_stage_transitions_and_failure_retain_optimistic_identity(self):
        checkpoint = contract.new_checkpoint(profile(), policy='assume', execution_profile=OPTIMISTIC)
        for stage in contract.STAGES:
            started = contract.begin_stage(checkpoint, stage)
            failed = contract.fail_stage(started, stage, 'synthetic failure')
            self.assertEqual(contract.execution_profile(failed), OPTIMISTIC)
            self.assertEqual(failed['box_state'], 'unknown')
            with self.assertRaises(ValueError):
                contract.next_stage(failed)
            checkpoint = finish(checkpoint, stage)
            self.assertEqual(contract.execution_profile(checkpoint), OPTIMISTIC)
        self.assertIsNone(contract.next_stage(checkpoint))
        self.assertTrue(all(record['source'] == 'assumed' for record in checkpoint['confirmations'].values()))


class ExecutionProfileResumeTest(unittest.TestCase):
    def test_legacy_standard_resume_does_not_change_source_keys_or_hash(self):
        source = held()
        before = copy.deepcopy(source)
        planned = plan_resume(source, profile(), policy='assume')
        self.assertEqual(planned['source_sha256'], digest(source))
        self.assertEqual(planned['checkpoint']['origin']['source_sha256'], digest(source))
        self.assertNotIn('execution_profile', planned['checkpoint'])
        self.assertEqual(source, before)

    def test_same_optimistic_profile_survives_multiple_resume_segments(self):
        source = held(OPTIMISTIC)
        planned = plan_resume(source, profile(), policy='assume', execution_profile=OPTIMISTIC)
        segment = planned['checkpoint']
        self.assertEqual(segment['version'], 3)
        self.assertEqual(segment['completed'], [])
        self.assertEqual(segment['entry_stage'], 'retreat')
        self.assertEqual(contract.execution_profile(segment), OPTIMISTIC)
        resumed_again = plan_resume(finish(segment, 'retreat'), profile(),
                                   policy='assume', execution_profile=OPTIMISTIC)
        self.assertEqual(resumed_again['stage'], 'navigate_put1')
        self.assertEqual(contract.execution_profile(resumed_again['checkpoint']), OPTIMISTIC)

    def test_cross_profile_resume_rejects_both_directions_even_with_recovery(self):
        for source_execution, requested in ((STANDARD, OPTIMISTIC), (OPTIMISTIC, STANDARD)):
            source = held(source_execution)
            for recovery in (False, True):
                with self.subTest(source=source_execution, requested=requested, recovery=recovery):
                    with self.assertRaisesRegex(ValueError, 'cannot change.*execution profile'):
                        plan_resume(source, profile(), policy='assume', execution_profile=requested,
                                    recovery_confirmed=recovery, box_state='held')

    def test_omitted_resume_profile_cannot_silently_convert_optimistic(self):
        with self.assertRaisesRegex(ValueError, 'cannot change.*execution profile'):
            plan_resume(held(OPTIMISTIC), profile(), policy='assume')

    def test_explicit_recovery_keeps_profile_and_failure_provenance(self):
        source = contract.new_checkpoint(profile(), policy='assume', execution_profile=OPTIMISTIC)
        source = contract.fail_stage(contract.begin_stage(source, 'navigate_get1'),
                                     'navigate_get1', 'interrupted goal')
        planned = plan_resume(source, profile(), stage='grasp', box_state='empty',
                              recovery_confirmed=True, policy='assume', execution_profile=OPTIMISTIC)
        checkpoint = planned['checkpoint']
        self.assertEqual(contract.execution_profile(checkpoint), OPTIMISTIC)
        self.assertEqual(checkpoint['origin']['source_failure'], source['failure'])
        self.assertEqual(checkpoint['origin']['source_sha256'], digest(source))
        self.assertEqual(checkpoint['completed'], [])
        with self.assertRaisesRegex(ValueError, 'cannot change.*execution profile'):
            plan_resume(source, profile(), stage='grasp', box_state='empty',
                        recovery_confirmed=True, policy='assume', execution_profile=STANDARD)

    def test_invalid_requested_profile_is_rejected_before_building_a_segment(self):
        for value in (None, True, 'optimistic_v2'):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'Unknown execution profile'):
                plan_resume(held(), profile(), policy='assume', execution_profile=value)

    def test_legacy_clean_resume_api_cannot_bypass_identity(self):
        source = held(OPTIMISTIC)
        kwargs = dict(confirmed_box='held', state_reconfirmed=True,
                      policy='assume', verification_source='assumed')
        with self.assertRaisesRegex(ValueError, 'cannot change.*execution profile'):
            contract.resume_checkpoint(source, profile(), **kwargs)
        resumed = contract.resume_checkpoint(source, profile(), execution_profile=OPTIMISTIC, **kwargs)
        self.assertEqual(contract.execution_profile(resumed), OPTIMISTIC)
        self.assertEqual(resumed['completed'], source['completed'])


if __name__ == '__main__':
    unittest.main()
