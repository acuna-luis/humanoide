"""Explicit resume plans and truthful v3 segments; no ROS or physical actions."""
import copy
import hashlib
import json
import unittest

from scripts.box_handling import scenario1_contract as contract
from scripts.box_handling.scenario1_resume import plan_resume
from scripts.box_handling.test_scenario1_contract import profile


SOURCES = {'ask': 'operator', 'assume': 'assumed', 'sensors': 'sensors'}


def finish(cp, stage):
    arguments = {'home_verified': stage == 'verify_home'}
    if stage in ('verify_held', 'verify_released'):
        policy = cp.get('policy', 'ask')
        arguments.update(confirmed_box='held' if stage == 'verify_held' else 'released',
                         verification_source=SOURCES[policy],
                         sensor_evidence={'fixture': 'new_sensor_report'} if policy == 'sensors' else None)
    return contract.complete_stage(contract.begin_stage(cp, stage), stage, **arguments)


def before(stage, policy='assume', stop_after='verify_home'):
    cp = contract.new_checkpoint(profile(), policy=policy, stop_after=stop_after)
    for previous in contract.STAGES[:contract.STAGES.index(stage)]:
        cp = finish(cp, previous)
    return cp


class ResumePlanTest(unittest.TestCase):
    def test_every_stage_can_be_an_explicit_entry_without_a_fabricated_prefix(self):
        source = contract.new_checkpoint(profile(), policy='assume')
        for stage in contract.STAGES:
            with self.subTest(stage=stage):
                planned = plan_resume(source, profile(), stage=stage,
                    box_state=contract.ENTRY_BOX_STATES[stage], recovery_confirmed=True)
                cp = planned['checkpoint']
                self.assertEqual(cp['version'], 3)
                self.assertEqual(cp['entry_stage'], stage)
                self.assertEqual(cp['entry_box_state'], contract.ENTRY_BOX_STATES[stage])
                self.assertEqual(cp['completed'], [])
                self.assertEqual(cp['confirmations'], {})
                self.assertEqual(contract.next_stage(cp), stage)
                self.assertEqual(contract.progress_index(cp), contract.STAGES.index(stage))
                self.assertEqual(cp['origin']['skipped_stages'], list(contract.STAGES[:contract.STAGES.index(stage)]))
                self.assertEqual(cp['origin']['repeated_stages'], [])
                self.assertEqual(contract.validate_checkpoint(json.loads(json.dumps(cp)), profile()), cp)

    def test_requirements_are_explicit_and_match_each_entry(self):
        source = contract.new_checkpoint(profile(), policy='assume')
        for stage in contract.STAGES:
            planned = plan_resume(source, profile(), stage=stage,
                box_state=contract.ENTRY_BOX_STATES[stage], recovery_confirmed=True)
            expected_waypoint = ('get1' if stage in ('enable_vision', 'grasp', 'verify_held', 'retreat')
                                 else 'put1' if stage == 'deposit' else None)
            self.assertEqual(planned['requirements'], {
                'box_state': contract.ENTRY_BOX_STATES[stage],
                'home': stage in ('navigate_get1', 'enable_vision', 'grasp', 'verify_home'),
                'waypoint': expected_waypoint, 'vision_prep': stage == 'grasp'})

    def test_clean_known_next_boundaries_need_no_recovery_acknowledgement(self):
        for stage in contract.STAGES:
            source = before(stage)
            if source['box_state'] == 'unknown':
                continue
            for selection in (None, stage):
                with self.subTest(stage=stage, selection=selection):
                    planned = plan_resume(source, profile(), stage=selection)
                    self.assertEqual(planned['stage'], stage)
                    origin = planned['checkpoint']['origin']
                    self.assertFalse(origin['explicit_state'])
                    self.assertFalse(origin['recovery_confirmed'])
                    self.assertEqual(origin['requested_stage'], selection)

    def test_unknown_post_grasp_or_post_deposit_needs_explicit_recovery(self):
        for stage in ('verify_held', 'verify_released'):
            source = before(stage)
            self.assertEqual(source['box_state'], 'unknown')
            for confirmed, state in ((False, None), (True, None), (False, contract.ENTRY_BOX_STATES[stage])):
                with self.subTest(stage=stage, confirmed=confirmed, state=state), self.assertRaisesRegex(ValueError, 'Recovery requires'):
                    plan_resume(source, profile(), recovery_confirmed=confirmed, box_state=state)
            result = plan_resume(source, profile(), recovery_confirmed=True,
                                 box_state=contract.ENTRY_BOX_STATES[stage])
            self.assertEqual(result['stage'], stage)
            self.assertEqual(result['checkpoint']['confirmations'], {})

    def test_every_failed_or_inflight_stage_needs_both_recovery_inputs(self):
        for stage in contract.STAGES:
            active = contract.begin_stage(before(stage), stage)
            failed = contract.fail_stage(active, stage, 'synthetic interruption')
            for source in (active, failed):
                for selection in (None, stage):
                    for ack, state in ((False, None), (True, None), (False, contract.ENTRY_BOX_STATES[stage])):
                        with self.subTest(stage=stage, failed=source['failure'], ack=ack, state=state), self.assertRaises(ValueError):
                            plan_resume(source, profile(), stage=selection,
                                        recovery_confirmed=ack, box_state=state)
                    result = plan_resume(source, profile(), stage=selection,
                        recovery_confirmed=True, box_state=contract.ENTRY_BOX_STATES[stage])
                    cp = result['checkpoint']
                    self.assertEqual(cp['completed'], [])
                    self.assertIsNone(cp['failure'])
                    self.assertIsNone(cp['in_flight'])
                    self.assertEqual(cp['origin']['source_failure'], source['failure'])
                    self.assertEqual(cp['origin']['source_in_flight'], source['in_flight'])

    def test_wrong_explicit_state_always_blocks_even_on_clean_boundaries(self):
        for stage in contract.STAGES:
            for state in (*contract.BOX_STATES, True, 1, [], ''):
                if state == contract.ENTRY_BOX_STATES[stage]:
                    continue
                with self.subTest(stage=stage, state=state), self.assertRaises(ValueError):
                    plan_resume(before(stage), profile(), box_state=state, recovery_confirmed=True)

    def test_stage_override_records_only_the_jump_and_requires_acknowledgement(self):
        source = before('navigate_put1')
        for selected in ('retreat', 'deposit'):
            with self.subTest(selected=selected), self.assertRaises(ValueError):
                plan_resume(source, profile(), stage=selected, box_state='held')
            planned = plan_resume(source, profile(), stage=selected, box_state='held', recovery_confirmed=True)
            origin = planned['checkpoint']['origin']
            self.assertEqual(origin['skipped_stages'], ['navigate_put1'] if selected == 'deposit' else [])
            self.assertEqual(origin['repeated_stages'], ['retreat'] if selected == 'retreat' else [])

    def test_source_stop_does_not_hide_the_actual_next_stage(self):
        for stop, following in (('navigate_get1', 'enable_vision'), ('verify_held', 'retreat'),
                                ('navigate_put1', 'deposit')):
            source = finish(before(stop, stop_after=stop), stop)
            self.assertIsNone(contract.next_stage(source))
            self.assertEqual(plan_resume(source, profile())['stage'], following)
            self.assertEqual(source['stop_after'], stop)

    def test_completed_cycle_requires_explicit_recovery_selection(self):
        source = finish(before('verify_home'), 'verify_home')
        with self.assertRaisesRegex(ValueError, 'already complete'):
            plan_resume(source, profile())
        with self.assertRaises(ValueError):
            plan_resume(source, profile(), stage='navigate_get1', box_state='empty')
        planned = plan_resume(source, profile(), stage='navigate_get1', box_state='empty', recovery_confirmed=True)
        self.assertIsNone(planned['checkpoint']['origin']['source_next_stage'])
        self.assertEqual(planned['checkpoint']['origin']['repeated_stages'], list(contract.STAGES))
        self.assertEqual(planned['checkpoint']['completed'], [])

    def test_profile_policy_and_argument_types_cannot_change_implicitly(self):
        for policy in SOURCES:
            source = before('retreat', policy)
            for other in SOURCES:
                if other != policy:
                    with self.assertRaisesRegex(ValueError, 'policy'):
                        plan_resume(source, profile(), policy=other)
            self.assertEqual(plan_resume(source, profile(), policy=policy)['checkpoint']['policy'], policy)
        source = before('retreat')
        for arguments in ({'recovery_confirmed': 1}, {'recovery_confirmed': 'yes'},
                          {'stage': 'get1'}, {'stage': 4}, {'policy': 'automatic'},
                          {'stop_after': 'navigate_get1'}, {'stop_after': 'unknown'}):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                plan_resume(source, profile(), **arguments)
        changed = profile()
        changed['id'] = 'different-profile'
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            plan_resume(source, changed)

    def test_canonical_source_hash_and_input_independence(self):
        source = before('retreat')
        original = copy.deepcopy(source)
        planned = plan_resume(source, profile())
        expected = hashlib.sha256(json.dumps(source, sort_keys=True, separators=(',', ':'),
                                            allow_nan=False).encode()).hexdigest()
        self.assertEqual(planned['source_sha256'], expected)
        self.assertEqual(planned['checkpoint']['origin']['source_sha256'], expected)
        reordered = dict(reversed(list(source.items())))
        self.assertEqual(plan_resume(reordered, profile())['source_sha256'], expected)
        planned['checkpoint']['origin']['skipped_stages'].append('tamper')
        self.assertEqual(source, original)

    def test_legacy_v1_remains_ask_without_promoting_evidence(self):
        source = before('retreat', policy='ask')
        source['version'] = 1
        source.pop('policy')
        source.pop('confirmations')
        planned = plan_resume(source, profile(), policy='ask')
        self.assertEqual(planned['checkpoint']['policy'], 'ask')
        self.assertEqual(planned['checkpoint']['confirmations'], {})
        with self.assertRaises(ValueError):
            plan_resume(source, profile())


class SegmentContractTest(unittest.TestCase):
    def entry(self, stage, policy='assume', stop_after='verify_home'):
        source = contract.new_checkpoint(profile(), policy=policy)
        return plan_resume(source, profile(), stage=stage, box_state=contract.ENTRY_BOX_STATES[stage],
                           recovery_confirmed=True, stop_after=stop_after, policy=policy)['checkpoint']

    def test_full_execution_from_every_entry_records_only_actual_stages(self):
        for entry in contract.STAGES:
            cp = self.entry(entry)
            for stage in contract.STAGES[contract.STAGES.index(entry):]:
                original = copy.deepcopy(cp)
                cp = finish(cp, stage)
                self.assertEqual(original['completed'], list(contract.STAGES[
                    contract.STAGES.index(entry):contract.STAGES.index(stage)]))
            self.assertIsNone(contract.next_stage(cp))
            self.assertEqual(contract.progress_index(cp), len(contract.STAGES))
            self.assertEqual(cp['completed'], list(contract.STAGES[contract.STAGES.index(entry):]))
            expected_records = set(cp['completed']) & {'verify_held', 'verify_released'}
            self.assertEqual(set(cp['confirmations']), expected_records)

    def test_failure_and_inflight_use_absolute_progress_not_segment_length(self):
        for entry in contract.STAGES:
            cp = self.entry(entry)
            active = contract.begin_stage(cp, entry)
            self.assertEqual(active['in_flight'], entry)
            failed = contract.fail_stage(active, entry, 'failure')
            self.assertEqual(failed['failure']['stage'], entry)
            self.assertEqual(failed['box_state'], 'unknown')
            self.assertEqual(failed['completed'], [])
            for blocked in (active, failed):
                with self.assertRaises(ValueError):
                    contract.next_stage(blocked)
            with self.assertRaises(ValueError):
                contract.complete_stage(failed, entry)

    def test_sensor_resume_never_manufactures_measured_verification_records(self):
        cp = self.entry('verify_held', policy='sensors')
        self.assertEqual(cp['confirmations'], {})
        active = contract.begin_stage(cp, 'verify_held')
        with self.assertRaises(ValueError):
            contract.complete_stage(active, 'verify_held', confirmed_box='held', verification_source='sensors')
        cp = finish(cp, 'verify_held')
        self.assertEqual(cp['confirmations']['verify_held']['source'], 'sensors')
        self.assertEqual(cp['completed'], ['verify_held'])
        planned = plan_resume(cp, profile(), policy='sensors')
        self.assertEqual(planned['checkpoint']['confirmations'], {})
        self.assertEqual(planned['requirements']['box_state'], 'held')

    def test_second_recovery_links_source_segment_without_flattening_history(self):
        first = self.entry('retreat')
        first = finish(first, 'retreat')
        first = contract.fail_stage(contract.begin_stage(first, 'navigate_put1'), 'navigate_put1', 'lost result')
        source_copy = copy.deepcopy(first)
        second = plan_resume(first, profile(), stage='deposit', box_state='held', recovery_confirmed=True)
        cp = second['checkpoint']
        self.assertEqual(cp['completed'], [])
        self.assertEqual(cp['origin']['skipped_stages'], ['navigate_put1'])
        self.assertEqual(cp['origin']['source_failure'], {'stage': 'navigate_put1', 'reason': 'lost result'})
        self.assertNotEqual(cp['origin']['source_sha256'], first['origin']['source_sha256'])
        self.assertEqual(first, source_copy)
        cp = finish(cp, 'deposit')
        self.assertEqual(cp['completed'], ['deposit'])
        third = plan_resume(cp, profile(), box_state='released', recovery_confirmed=True)['checkpoint']
        self.assertEqual(third['entry_stage'], 'verify_released')
        self.assertEqual(third['completed'], [])

    def test_tampered_segment_origin_or_fabricated_evidence_is_rejected(self):
        initial = self.entry('retreat')
        variants = []
        for field, value in (('completed', list(contract.STAGES[:4])), ('entry_stage', 'bogus'),
                             ('entry_box_state', 'empty'), ('box_state', 'released'), ('stop_after', 'navigate_get1')):
            item = copy.deepcopy(initial); item[field] = value; variants.append(item)
        for field, value in (('source_sha256', 'bad'), ('requested_stage', None),
                             ('explicit_state', 1), ('recovery_confirmed', False),
                             ('skipped_stages', []), ('repeated_stages', ['grasp']),
                             ('source_next_stage', 'unknown'), ('source_in_flight', 'home'),
                             ('source_failure', {'stage': 'home', 'reason': 'bad'}), ('extra', True)):
            item = copy.deepcopy(initial); item['origin'][field] = value; variants.append(item)
        item = copy.deepcopy(initial)
        item['confirmations']['verify_held'] = {'box_state': 'held', 'source': 'assumed', 'sensor_evidence': None}
        variants.append(item)
        for item in variants:
            with self.subTest(item=item), self.assertRaises(ValueError):
                contract.validate_checkpoint(item)

    def test_segment_cannot_overrun_stop_or_skip_its_first_stage(self):
        cp = self.entry('verify_held', stop_after='verify_held')
        with self.assertRaises(ValueError):
            contract.begin_stage(cp, 'retreat')
        cp = finish(cp, 'verify_held')
        self.assertEqual(cp['completed'], ['verify_held'])
        self.assertIsNone(contract.next_stage(cp))
        with self.assertRaises(ValueError):
            contract.begin_stage(cp, 'retreat')
        self.assertEqual(plan_resume(cp, profile())['stage'], 'retreat')


if __name__ == '__main__':
    unittest.main()
