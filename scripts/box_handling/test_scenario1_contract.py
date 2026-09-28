"""Safety transitions and input contracts, without connecting to the robot."""
import copy
import json
import math
import unittest

from scripts.box_handling.scenario1_contract import (
    STAGES, begin_stage, complete_stage, fail_stage, new_checkpoint, next_stage,
    resume_checkpoint, validate_checkpoint, validate_motion_result,
    validate_navigation_result, validate_profile,
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


class CheckpointTest(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
