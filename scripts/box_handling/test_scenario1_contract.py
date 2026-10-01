"""Safety transitions and input contracts, without connecting to the robot."""
import copy
import json
import math
import unittest

from scripts.box_handling.scenario1_contract import (
    STAGES, begin_stage, complete_stage, fail_stage, new_checkpoint, next_stage,
    resume_checkpoint, validate_checkpoint, validate_motion_result,
    validate_navigation_result, validate_planning_result, validate_profile,
)


def profile():
    return {
        'id': 'current_tasks_v1',
        'box_size_m': [0.603, 0.397, 0.220],
        'intended_use': 'separate_nested_box',
        'grasp': {'task': 'local_front_box/separate_right_cruzr',
                  'compatibility': 'operator_assumed_existing'},
        'deposit': {'task': 'wrc_cruzr/put_cruzr_wrc_low',
                    'compatibility': 'operator_assumed_existing'},
    }


def finish(cp, stage):
    started = begin_stage(cp, stage)
    return complete_stage(
        started, stage,
        confirmed_box={'verify_held': 'held', 'verify_released': 'released'}.get(stage),
        home_verified=stage == 'verify_home',
    )


def through(stage, *, stop_after='verify_home', selected_profile=None):
    cp = new_checkpoint(selected_profile or profile(), stop_after=stop_after)
    for current in STAGES[:STAGES.index(stage) + 1]:
        cp = finish(cp, current)
    return cp


def terminal(desc='SUCCEED', code=1101001, status=4):
    return {'event': 'result', 'status': status,
            'result': {'state': {'state': code, 'desc': desc}}}


class ProfileTest(unittest.TestCase):
    def test_operator_assumption_is_accepted_without_becoming_verified(self):
        source = profile()
        result = validate_profile(source)
        self.assertEqual(result['grasp']['compatibility'], 'operator_assumed_existing')
        result['box_size_m'][0] = 1
        self.assertEqual(source['box_size_m'][0], 0.603)

    def test_approximate_or_nonfinite_size_is_not_the_requested_profile(self):
        for size in ([0.6, 0.4, 0.22], [0.603, 0.397, 0.217],
                     [math.nan, 0.397, 0.22], [0.603, math.inf, 0.22],
                     [True, 0.397, 0.22], ['0.603', 0.397, 0.22]):
            with self.subTest(size=size):
                item = profile()
                item['box_size_m'] = size
                with self.assertRaises(ValueError):
                    new_checkpoint(item)

    def test_pending_deposit_allows_grasp_only_but_cannot_extend_to_deposit(self):
        item = profile()
        item['deposit']['compatibility'] = 'pending'
        cp = through('verify_held', stop_after='verify_held', selected_profile=item)
        self.assertIsNone(next_stage(cp))
        with self.assertRaises(ValueError):
            validate_profile(item)
        with self.assertRaises(ValueError):
            resume_checkpoint(cp, item, confirmed_box='held', state_reconfirmed=True)

    def test_get1_only_allows_pending_deposit_without_weakening_other_profiles(self):
        for compatibility in ('pending', 'incompatible'):
            with self.subTest(compatibility=compatibility):
                item = profile()
                item['deposit']['compatibility'] = compatibility
                original = copy.deepcopy(item)
                cp = new_checkpoint(item, stop_after='navigate_get1')
                self.assertEqual(cp['stop_after'], 'navigate_get1')
                self.assertEqual(next_stage(cp), 'navigate_get1')
                self.assertEqual(item, original)
                with self.assertRaises(ValueError):
                    new_checkpoint(item, stop_after='verify_home')
                # Navigation-only does not relax the accepted grasp/profile
                # schema or turn an incompatible grasp into an approved one.
                item['grasp']['compatibility'] = compatibility
                with self.assertRaises(ValueError):
                    new_checkpoint(item, stop_after='navigate_get1')

    def test_unknown_keys_modes_tasks_or_compatibility_are_rejected(self):
        variants = []
        item = profile(); item['unused'] = True; variants.append(item)
        item = profile(); item['intended_use'] = 'carry_any_box'; variants.append(item)
        item = profile(); item['grasp']['task'] = 'Singapore/separate_right_cruzr'; variants.append(item)
        item = profile(); item['deposit']['task'] = 'cruzr/home'; variants.append(item)
        item = profile(); item['grasp']['compatibility'] = 'probably_ok'; variants.append(item)
        item = profile(); item['grasp']['compatibility'] = 'pending'; variants.append(item)
        item = profile(); item['grasp']['compatibility'] = 'incompatible'; variants.append(item)
        item = profile(); item['deposit']['override'] = True; variants.append(item)
        for item in variants:
            with self.subTest(profile=item), self.assertRaises(ValueError):
                validate_profile(item)
        with self.assertRaises(ValueError):
            validate_profile(profile(), stop_after='grasp')
        with self.assertRaises(ValueError):
            validate_profile(profile(), stop_after='get1')  # CLI alias is not a checkpoint stage.

    def test_put1_boundary_allows_unqualified_deposit_but_never_extends_into_it(self):
        for compatibility in ('pending', 'incompatible'):
            item = profile()
            item['deposit']['compatibility'] = compatibility
            original = copy.deepcopy(item)
            cp = through('navigate_put1', stop_after='navigate_put1', selected_profile=item)
            self.assertEqual(cp['box_state'], 'held')
            self.assertIsNone(next_stage(cp))
            self.assertEqual(item, original)
            with self.assertRaises(ValueError):
                begin_stage(cp, 'deposit')
            with self.assertRaises(ValueError):
                new_checkpoint(item, stop_after='verify_home')


class CheckpointTest(unittest.TestCase):
    def test_put1_boundary_is_clean_held_and_cannot_dispatch_any_later_stage(self):
        cp = through('navigate_put1', stop_after='navigate_put1')
        self.assertEqual(cp['completed'], list(STAGES[:6]))
        self.assertEqual(cp['box_state'], 'held')
        self.assertIsNone(cp['in_flight'])
        self.assertIsNone(cp['failure'])
        self.assertIsNone(next_stage(cp))
        self.assertEqual(validate_checkpoint(json.loads(json.dumps(cp)), profile()), cp)
        for stage in STAGES[6:]:
            with self.subTest(stage=stage), self.assertRaises(ValueError):
                begin_stage(cp, stage)

    def test_get1_only_completes_empty_after_exactly_one_stage(self):
        for policy in ('ask', 'assume', 'sensors'):
            with self.subTest(policy=policy):
                initial = new_checkpoint(profile(), stop_after='navigate_get1', policy=policy)
                started = begin_stage(initial, 'navigate_get1')
                self.assertEqual(started['completed'], [])
                self.assertEqual(started['in_flight'], 'navigate_get1')
                completed = complete_stage(started, 'navigate_get1')
                self.assertEqual(completed['completed'], ['navigate_get1'])
                self.assertEqual(completed['box_state'], 'empty')
                self.assertEqual(completed['confirmations'], {})
                self.assertIsNone(completed['in_flight'])
                self.assertIsNone(completed['failure'])
                self.assertIsNone(next_stage(completed))
                self.assertEqual(validate_checkpoint(json.loads(json.dumps(completed)), profile()), completed)
                self.assertEqual(initial['completed'], [])
                self.assertIsNone(initial['in_flight'])
                # Neither another get1 goal nor any manipulation stage is
                # authorized after the sole permitted navigation stage.
                for stage in STAGES:
                    with self.subTest(next_stage=stage), self.assertRaises(ValueError):
                        begin_stage(completed, stage)

    def test_get1_only_cannot_skip_navigation_or_forge_box_postconditions(self):
        initial = new_checkpoint(profile(), stop_after='navigate_get1')
        for stage in STAGES[1:]:
            with self.subTest(stage=stage), self.assertRaises(ValueError):
                begin_stage(initial, stage)
        started = begin_stage(initial, 'navigate_get1')
        for kwargs in ({'confirmed_box': 'empty'}, {'confirmed_box': 'held'},
                       {'home_verified': True}, {'verification_source': 'assumed'},
                       {'sensor_evidence': {'measured': True}}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                complete_stage(started, 'navigate_get1', **kwargs)

    def test_get1_only_checkpoint_cannot_be_extended_by_resume(self):
        cp = through('navigate_get1', stop_after='navigate_get1')
        original = copy.deepcopy(cp)
        for stop_after in ('navigate_get1', 'verify_held', 'verify_home'):
            for box in ('empty', 'held', 'released'):
                with self.subTest(stop_after=stop_after, box=box), self.assertRaisesRegex(
                        ValueError, 'clean verified-held/released'):
                    resume_checkpoint(cp, profile(), confirmed_box=box,
                                      state_reconfirmed=True, stop_after=stop_after)
        self.assertEqual(cp, original)

    def test_get1_only_rejects_completed_or_inflight_stages_beyond_stop(self):
        cp = through('navigate_get1', stop_after='navigate_get1')
        variants = []
        item = copy.deepcopy(cp); item['completed'].append('enable_vision'); variants.append(item)
        item = copy.deepcopy(cp); item['in_flight'] = 'enable_vision'; variants.append(item)
        item = copy.deepcopy(cp); item['in_flight'] = 'navigate_get1'; variants.append(item)
        item = copy.deepcopy(cp); item['box_state'] = 'held'; variants.append(item)
        for item in variants:
            with self.subTest(checkpoint=item), self.assertRaises(ValueError):
                validate_checkpoint(item)

    def test_failed_or_interrupted_get1_only_never_becomes_complete_or_resumable(self):
        initial = new_checkpoint(profile(), stop_after='navigate_get1')
        started = begin_stage(initial, 'navigate_get1')
        failed = fail_stage(started, 'navigate_get1', 'Arrival outside get1 tolerance')
        self.assertEqual(failed['completed'], [])
        self.assertEqual(failed['box_state'], 'unknown')
        self.assertEqual(failed['failure']['stage'], 'navigate_get1')
        for cp in (started, failed):
            with self.subTest(checkpoint=cp):
                with self.assertRaises(ValueError):
                    next_stage(cp)
                with self.assertRaises(ValueError):
                    resume_checkpoint(cp, profile(), confirmed_box='empty', state_reconfirmed=True)
        with self.assertRaises(ValueError):
            complete_stage(failed, 'navigate_get1')

    def test_full_cycle_needs_each_postcondition_and_does_not_mutate_input(self):
        cp = new_checkpoint(profile())
        for stage in STAGES:
            original = copy.deepcopy(cp)
            self.assertEqual(next_stage(cp), stage)
            next_cp = finish(cp, stage)
            self.assertEqual(cp, original)
            cp = json.loads(json.dumps(next_cp))
        self.assertEqual(cp['box_state'], 'released')
        self.assertIsNone(next_stage(cp))
        with self.assertRaises(ValueError):
            begin_stage(cp, 'home')

    def test_unverified_grasp_cannot_authorize_retreat(self):
        cp = through('grasp')
        self.assertEqual(cp['box_state'], 'unknown')
        with self.assertRaises(ValueError):
            begin_stage(cp, 'retreat')
        started = begin_stage(cp, 'verify_held')
        for incorrect in (None, 'empty', 'released', 'unknown'):
            with self.subTest(incorrect=incorrect), self.assertRaises(ValueError):
                complete_stage(started, 'verify_held', confirmed_box=incorrect)
        held = complete_stage(started, 'verify_held', confirmed_box='held')
        self.assertEqual(next_stage(held), 'retreat')

    def test_unverified_deposit_cannot_authorize_home(self):
        cp = through('deposit')
        self.assertEqual(cp['box_state'], 'unknown')
        with self.assertRaises(ValueError):
            begin_stage(cp, 'home')
        started = begin_stage(cp, 'verify_released')
        with self.assertRaises(ValueError):
            complete_stage(started, 'verify_released', confirmed_box='held')
        released = complete_stage(started, 'verify_released', confirmed_box='released')
        self.assertEqual(next_stage(released), 'home')

    def test_motion_success_does_not_prove_home(self):
        cp = begin_stage(through('home'), 'verify_home')
        for unverified in (False, 1, 'true', None):
            with self.subTest(value=unverified), self.assertRaises(ValueError):
                complete_stage(cp, 'verify_home', home_verified=unverified)
        self.assertIsNone(next_stage(complete_stage(cp, 'verify_home', home_verified=True)))

    def test_crash_at_every_inflight_stage_blocks_resume_and_next_command(self):
        cp = new_checkpoint(profile())
        for stage in STAGES:
            persisted = json.loads(json.dumps(begin_stage(cp, stage)))
            with self.subTest(stage=stage):
                with self.assertRaises(ValueError):
                    next_stage(persisted)
                with self.assertRaises(ValueError):
                    resume_checkpoint(persisted, profile(), confirmed_box='held',
                                      state_reconfirmed=True)
            cp = finish(cp, stage)

    def test_failure_at_every_stage_latches_unknown_and_blocks_resume(self):
        cp = new_checkpoint(profile())
        for stage in STAGES:
            failed = fail_stage(begin_stage(cp, stage), stage, 'terminal result unavailable')
            with self.subTest(stage=stage):
                self.assertEqual(failed['box_state'], 'unknown')
                with self.assertRaises(ValueError):
                    next_stage(failed)
                with self.assertRaises(ValueError):
                    resume_checkpoint(failed, profile(), confirmed_box='held',
                                      state_reconfirmed=True)
            cp = finish(cp, stage)

    def test_clean_held_stop_resumes_at_retreat_only_after_fresh_reconfirmation(self):
        cp = through('verify_held', stop_after='verify_held')
        resumed = resume_checkpoint(cp, profile(), confirmed_box='held', state_reconfirmed=True)
        self.assertEqual(next_stage(resumed), 'retreat')
        self.assertIsNone(next_stage(cp))
        for box, fresh in (('released', True), ('unknown', True), ('held', False), ('held', 1)):
            with self.subTest(box=box, fresh=fresh), self.assertRaises(ValueError):
                resume_checkpoint(cp, profile(), confirmed_box=box, state_reconfirmed=fresh)

    def test_clean_released_checkpoint_resumes_at_home(self):
        cp = through('verify_released')
        resumed = resume_checkpoint(cp, profile(), confirmed_box='released', state_reconfirmed=True)
        self.assertEqual(next_stage(resumed), 'home')
        with self.assertRaises(ValueError):
            resume_checkpoint(cp, profile(), confirmed_box='released', state_reconfirmed=True,
                              stop_after='verify_held')

    def test_other_clean_phases_do_not_become_arbitrary_resume_points(self):
        for stage in STAGES:
            if stage in ('verify_held', 'verify_released'):
                continue
            cp = through(stage)
            with self.subTest(stage=stage), self.assertRaises(ValueError):
                resume_checkpoint(cp, profile(), confirmed_box=cp['box_state'],
                                  state_reconfirmed=True)

    def test_tampered_or_different_profile_checkpoint_is_rejected(self):
        cp = through('verify_held')
        changed_profile = profile()
        changed_profile['id'] = 'different_setup'
        with self.assertRaises(ValueError):
            resume_checkpoint(cp, changed_profile, confirmed_box='held', state_reconfirmed=True)
        variants = []
        item = copy.deepcopy(cp); item['completed'].remove('grasp'); variants.append(item)
        item = copy.deepcopy(cp); item['box_state'] = 'released'; variants.append(item)
        item = copy.deepcopy(cp); item['in_flight'] = 'home'; variants.append(item)
        item = copy.deepcopy(cp); item['version'] = True; variants.append(item)
        item = copy.deepcopy(cp); item['operator_override'] = True; variants.append(item)
        for item in variants:
            with self.subTest(checkpoint=item), self.assertRaises(ValueError):
                validate_checkpoint(item)


class ConfirmationPolicyTest(unittest.TestCase):
    sources = {'ask': 'operator', 'assume': 'assumed', 'sensors': 'sensors'}

    def report(self, stamp=100):
        # Only provenance transport is tested here. Runtime sensor validators
        # must establish actual schema, timestamps, meaning and postconditions.
        return {'sample_stamp_ns': stamp, 'classification': 'runtime_checked'}

    def through(self, stage, policy, stop_after='verify_home'):
        cp = new_checkpoint(profile(), stop_after=stop_after, policy=policy)
        for current in STAGES[:STAGES.index(stage) + 1]:
            started = begin_stage(cp, current)
            kwargs = dict(home_verified=current == 'verify_home')
            if current in ('verify_held', 'verify_released'):
                kwargs.update(confirmed_box='held' if current == 'verify_held' else 'released',
                              verification_source=self.sources[policy],
                              sensor_evidence=self.report() if policy == 'sensors' else None)
            cp = complete_stage(started, current, **kwargs)
        return cp

    def test_new_default_is_v2_ask_with_no_premature_box_evidence(self):
        cp = new_checkpoint(profile())
        self.assertEqual(cp['version'], 2)
        self.assertEqual(cp['policy'], 'ask')
        self.assertEqual(cp['confirmations'], {})
        self.assertEqual(self.through('grasp', 'assume')['confirmations'], {})
        for unknown in ('automatic', '', None, True, 2):
            with self.subTest(policy=unknown), self.assertRaises(ValueError):
                new_checkpoint(profile(), policy=unknown)

    def test_all_policies_preserve_evidence_distinction_through_full_cycle(self):
        for policy, source in self.sources.items():
            with self.subTest(policy=policy):
                cp = self.through('verify_home', policy)
                self.assertIsNone(next_stage(cp))
                self.assertEqual(set(cp['confirmations']), {'verify_held', 'verify_released'})
                for stage, box in (('verify_held', 'held'), ('verify_released', 'released')):
                    record = cp['confirmations'][stage]
                    self.assertEqual(record['source'], source)
                    self.assertEqual(record['box_state'], box)
                    self.assertEqual(record['sensor_evidence'], self.report() if policy == 'sensors' else None)
                self.assertEqual(validate_checkpoint(json.loads(json.dumps(cp))), cp)

    def test_assumed_is_not_recorded_as_operator_or_measured(self):
        cp = self.through('verify_held', 'assume')
        record = cp['confirmations']['verify_held']
        self.assertEqual(record, dict(box_state='held', source='assumed', sensor_evidence=None))
        self.assertEqual(next_stage(cp), 'retreat')
        self.assertEqual(cp['policy'], 'assume')

    def test_completion_cannot_use_another_policys_evidence_source(self):
        for policy, expected in self.sources.items():
            started = begin_stage(self.through('grasp', policy), 'verify_held')
            for source in (*self.sources.values(), 'measured', True, None):
                if source == expected:
                    continue
                with self.subTest(policy=policy, source=source), self.assertRaises(ValueError):
                    complete_stage(started, 'verify_held', confirmed_box='held',
                                   verification_source=source,
                                   sensor_evidence=self.report() if source == 'sensors' else None)

    def test_sensor_source_and_boolean_alone_cannot_create_measurement_evidence(self):
        started = begin_stage(self.through('grasp', 'sensors'), 'verify_held')
        for evidence in (None, True, False, {}, [], 'verified', {'value': math.nan}):
            with self.subTest(evidence=evidence), self.assertRaises(ValueError):
                complete_stage(started, 'verify_held', confirmed_box='held',
                               verification_source='sensors', sensor_evidence=evidence)
        with self.assertRaises(ValueError):
            complete_stage(started, 'verify_held', confirmed_box='held', home_verified=True,
                           verification_source='sensors', sensor_evidence=self.report())

    def test_operator_and_assumption_cannot_smuggle_sensor_measurements(self):
        for policy in ('ask', 'assume'):
            started = begin_stage(self.through('grasp', policy), 'verify_held')
            with self.subTest(policy=policy), self.assertRaises(ValueError):
                complete_stage(started, 'verify_held', confirmed_box='held',
                               verification_source=self.sources[policy], sensor_evidence=self.report())

    def test_evidence_is_copied_and_only_allowed_at_box_checks(self):
        started = begin_stage(self.through('grasp', 'sensors'), 'verify_held')
        original = copy.deepcopy(started)
        evidence = self.report()
        completed = complete_stage(started, 'verify_held', confirmed_box='held',
                                   verification_source='sensors', sensor_evidence=evidence)
        evidence['sample_stamp_ns'] = 999
        self.assertEqual(completed['confirmations']['verify_held']['sensor_evidence']['sample_stamp_ns'], 100)
        self.assertEqual(started, original)
        with self.assertRaises(ValueError):
            complete_stage(begin_stage(completed, 'retreat'), 'retreat',
                           verification_source='sensors', sensor_evidence=self.report())

    def test_checkpoint_requires_exact_box_records_matching_completed_prefix(self):
        cp = self.through('verify_held', 'assume')
        variants = []
        item = copy.deepcopy(cp); item['confirmations'] = {}; variants.append(item)
        item = copy.deepcopy(cp); item['confirmations']['verify_released'] = dict(
            box_state='released', source='assumed', sensor_evidence=None); variants.append(item)
        item = copy.deepcopy(cp); item['confirmations']['verify_held']['source'] = 'operator'; variants.append(item)
        item = copy.deepcopy(cp); item['confirmations']['verify_held']['measured'] = True; variants.append(item)
        item = copy.deepcopy(cp); item['confirmations']['verify_held']['box_state'] = 'released'; variants.append(item)
        item = copy.deepcopy(cp); item['policy'] = 'sensors'; variants.append(item)
        for item in variants:
            with self.subTest(checkpoint=item), self.assertRaises(ValueError):
                validate_checkpoint(item)

    def test_resume_keeps_policy_and_requires_matching_fresh_evidence(self):
        for policy, source in self.sources.items():
            cp = self.through('verify_held', policy, stop_after='verify_held')
            original = copy.deepcopy(cp)
            evidence = self.report(200) if policy == 'sensors' else None
            resumed = resume_checkpoint(cp, profile(), confirmed_box='held', state_reconfirmed=True,
                                        policy=policy, verification_source=source, sensor_evidence=evidence)
            self.assertEqual(next_stage(resumed), 'retreat')
            self.assertEqual(resumed['policy'], policy)
            self.assertEqual(resumed['confirmations']['verify_held']['source'], source)
            self.assertEqual(resumed['confirmations']['verify_held']['sensor_evidence'], evidence)
            self.assertEqual(cp, original)
            for other_policy in self.sources:
                if other_policy != policy:
                    with self.subTest(policy=policy, other=other_policy), self.assertRaises(ValueError):
                        resume_checkpoint(cp, profile(), confirmed_box='held', state_reconfirmed=True,
                                          policy=other_policy, verification_source=self.sources[other_policy],
                                          sensor_evidence=self.report() if other_policy == 'sensors' else None)

    def test_sensor_resume_does_not_reuse_persisted_report_implicitly(self):
        cp = self.through('verify_held', 'sensors', stop_after='verify_held')
        for evidence in (None, {}, True):
            with self.subTest(evidence=evidence), self.assertRaises(ValueError):
                resume_checkpoint(cp, profile(), confirmed_box='held', state_reconfirmed=True,
                                  policy='sensors', verification_source='sensors', sensor_evidence=evidence)
        with self.assertRaises(ValueError):
            resume_checkpoint(cp, profile(), confirmed_box='held', state_reconfirmed=1,
                              policy='sensors', verification_source='sensors', sensor_evidence=self.report(200))

    def test_failed_or_inflight_checkpoints_remain_blocked_under_every_policy(self):
        for policy in self.sources:
            cp = self.through('grasp', policy)
            started = begin_stage(cp, 'verify_held')
            failed = fail_stage(started, 'verify_held', 'postcondition unavailable')
            self.assertEqual(failed['box_state'], 'unknown')
            self.assertEqual(failed['confirmations'], {})
            for checkpoint in (started, failed):
                with self.subTest(policy=policy), self.assertRaises(ValueError):
                    resume_checkpoint(checkpoint, profile(), confirmed_box='held', state_reconfirmed=True,
                                      policy=policy, verification_source=self.sources[policy],
                                      sensor_evidence=self.report() if policy == 'sensors' else None)

    def test_legacy_v1_works_only_with_original_interactive_policy(self):
        cp = new_checkpoint(profile(), stop_after='verify_held')
        cp['version'] = 1
        del cp['policy']; del cp['confirmations']
        for stage in STAGES[:STAGES.index('verify_held') + 1]:
            cp = finish(cp, stage)
        self.assertEqual(cp['version'], 1)
        self.assertNotIn('confirmations', cp)
        resumed = resume_checkpoint(cp, profile(), confirmed_box='held', state_reconfirmed=True)
        self.assertEqual(next_stage(resumed), 'retreat')
        self.assertEqual(resumed['version'], 1)
        for policy in ('assume', 'sensors'):
            with self.subTest(policy=policy), self.assertRaises(ValueError):
                resume_checkpoint(cp, profile(), confirmed_box='held', state_reconfirmed=True,
                                  policy=policy, verification_source=self.sources[policy],
                                  sensor_evidence=self.report() if policy == 'sensors' else None)
        changed = copy.deepcopy(cp); changed['policy'] = 'ask'
        with self.assertRaises(ValueError):
            validate_checkpoint(changed)


class ResultTest(unittest.TestCase):
    def test_structured_motion_success_is_independent_and_not_just_status_four(self):
        payload = terminal()
        result = validate_motion_result(payload)
        result['state']['desc'] = 'changed'
        self.assertEqual(payload['result']['state']['desc'], 'SUCCEED')
        for payload in (terminal(status=2), terminal(status=5), terminal(status=True),
                        terminal(desc='FAILURE'), terminal(code=7101100),
                        {'event': 'accepted', 'status': 4, 'result': terminal()['result']}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                validate_motion_result(payload)

    def test_nonfinite_or_malformed_result_is_rejected(self):
        payload = terminal(); payload['result']['pose'] = [math.nan]
        for value in (payload, {'event': 'result', 'status': 4, 'result': {}}, [], None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_motion_result(value)

    def test_navigation_preserves_narrow_auxiliary_lost_exception(self):
        payload = terminal(desc='VSLAM_LOCATION_LOST')
        with self.assertRaises(ValueError):
            validate_navigation_result(payload)
        payload['result']['dmsg'] = 'navigation_start SUCCEEDED: reached target'
        self.assertEqual(validate_navigation_result(payload)['state']['desc'], 'VSLAM_LOCATION_LOST')
        for desc in ('ERROR', 'NAVIGATION_ABORT', 'OBSTACLE', 'LOST', 'UNKNOWN'):
            failed = terminal(desc=desc)
            if desc != 'UNKNOWN':
                failed['result']['dmsg'] = 'navigation_start SUCCEEDED: reached target'
            with self.subTest(desc=desc), self.assertRaises(ValueError):
                validate_navigation_result(failed)

    def test_planning_reload_requires_terminal_ready(self):
        self.assertEqual(validate_planning_result(terminal(desc='READY', code=0))['state']['desc'], 'READY')
        self.assertEqual(validate_planning_result(terminal(desc='FINISH', code=0),
                                                 allow_finished=True)['state']['desc'], 'FINISH')
        for payload in (terminal(desc='READY', status=6), terminal(desc='READY', status=True),
                        terminal(desc='MAP_SETTING'), terminal(desc='MAP_SETTING_ERROR'),
                        terminal(desc='GOAL_OUTCOSTMAP'), terminal(desc='SUCCESS'), terminal(desc='FINISH')):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                validate_planning_result(payload)


if __name__ == '__main__':
    unittest.main()
