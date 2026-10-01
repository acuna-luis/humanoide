"""Bounded HOME retry supervision with in-memory IO and no robot connection."""
import copy
import unittest

from scripts.box_handling import scenario1_cli as cli
from scripts.box_handling import scenario1_contract as contract
from scripts.box_handling import scenario1_resume as resume
from scripts.box_handling import scenario1_runtime as runtime
from scripts.box_handling.test_scenario1_runtime import PROFILE


FIRST_UUID = '11111111-1111-4111-8111-111111111111'
SECOND_UUID = '22222222-2222-4222-8222-222222222222'


def terminal(*, failed=False, goal_id=FIRST_UUID):
    return dict(event='result', goal_id=goal_id, status=6 if failed else 4,
                result={'state': {'desc': 'MoveToGoalFailed' if failed else 'SUCCEED',
                                  'state': 7104050 if failed else 1101001}})


def checkpoint_at(stage='home', *, policy='assume', profile='optimistic_v1', active=True):
    cp = contract.new_checkpoint(PROFILE, policy=policy, execution_profile=profile)
    for previous in contract.STAGES[:contract.STAGES.index(stage)]:
        cp = contract.begin_stage(cp, previous)
        values = {}
        if previous in ('verify_held', 'verify_released'):
            values = dict(confirmed_box='held' if previous == 'verify_held' else 'released',
                          verification_source={'ask': 'operator', 'assume': 'assumed',
                                               'sensors': 'sensors'}[policy])
            if policy == 'sensors':
                values['sensor_evidence'] = {'test': 'qualified fake evidence'}
        cp = contract.complete_stage(cp, previous, **values)
    return contract.begin_stage(cp, stage) if active else cp


class FakeRuntime(runtime.Runtime):
    """Only the production stage/retry orchestration runs; all IO is recorded."""
    def __init__(self, results, checkpoint=None):
        cp = checkpoint if checkpoint is not None else checkpoint_at()
        self.events = []
        super().__init__(dict(checkpoint=copy.deepcopy(cp), profile=PROFILE,
                              policy=cp['policy'], execution_profile=contract.execution_profile(cp)),
                         lambda event, **values: self.events.append(copy.deepcopy(
                             dict(event=event, **values))))
        self.armed = True
        self.results = list(results)
        self.trace = []
        self.actions = []
        self.persisted = copy.deepcopy(cp)
        self.fail_at = {}
        self.gate_counts = {}

    def gate(self, name, **values):
        self.gate_counts[name] = self.gate_counts.get(name, 0) + 1
        self.trace.append(dict(call=name, **values))
        failure = self.fail_at.get(name)
        if failure and self.gate_counts[name] == failure[0]:
            raise RuntimeError(failure[1])

    def connected(self):
        self.gate('connected')

    def discover(self):
        self.gate('discover')

    def hashes(self):
        self.gate('hashes')

    def health(self, require_home=False):
        self.gate('health', require_home=require_home)

    def quick_health(self):
        self.gate('quick_health', after_ns=self.last_action_end_ns)

    def save(self):
        self.gate('save', checkpoint=copy.deepcopy(self.checkpoint))
        self.persisted = copy.deepcopy(self.checkpoint)

    def action(self, kind, goal, timeout, *, allow_home_retry=False):
        if self.persisted != self.checkpoint or not self.checkpoint['in_flight']:
            raise AssertionError('Action preceded durable intent')
        row = dict(call='action', kind=kind, goal=copy.deepcopy(goal), timeout=timeout,
                   allow_home_retry=allow_home_retry, checkpoint=copy.deepcopy(self.checkpoint))
        self.trace.append(row)
        self.actions.append(row)
        if not self.results:
            raise AssertionError('Unexpected additional physical attempt')
        result = self.results.pop(0)
        if isinstance(result, BaseException):
            raise result
        self.last_action_end_ns = 1000 + len(self.actions)
        return copy.deepcopy(result)


class HomeRetryRuntimeTests(unittest.TestCase):
    def test_exact_failure_revalidates_and_saves_single_allowance_before_second_dispatch(self):
        first, second = terminal(failed=True), terminal(goal_id=SECOND_UUID)
        original = copy.deepcopy(first)
        machine = FakeRuntime([first, second])
        self.assertEqual(machine.motion_stage('home'), second)
        self.assertEqual(first, original)
        self.assertEqual([r['call'] for r in machine.trace],
                         ['action', 'connected', 'discover', 'hashes', 'health',
                          'quick_health', 'connected', 'save', 'connected', 'action', 'connected'])
        self.assertEqual([a['allow_home_retry'] for a in machine.actions], [True, False])
        self.assertEqual([a['goal'] for a in machine.actions],
                         [{'task_name': 'cruzr/home', 'yaml_args': '{}'}] * 2)
        self.assertEqual([a['kind'] for a in machine.actions], ['motion', 'motion'])
        self.assertEqual([a['timeout'] for a in machine.actions], [runtime.TASKS['home'][1]] * 2)
        self.assertEqual(machine.trace[4], dict(call='health', require_home=False))
        self.assertEqual(machine.trace[5], dict(call='quick_health', after_ns=1001))
        self.assertEqual(machine.actions[1]['checkpoint'], machine.persisted)
        self.assertEqual(machine.persisted['home_retry']['failed_goal_id'], FIRST_UUID)
        self.assertFalse(contract.home_retry_available(machine.persisted))
        self.assertEqual(machine.persisted['in_flight'], 'home')
        self.assertNotIn('home', machine.persisted['completed'])

    def test_first_success_has_no_extra_checks_reservation_or_goal(self):
        machine = FakeRuntime([terminal()])
        before = copy.deepcopy(machine.checkpoint)
        self.assertEqual(machine.motion_stage('home'), terminal())
        self.assertEqual([r['call'] for r in machine.trace], ['action'])
        self.assertEqual(machine.checkpoint, before)
        self.assertFalse(any(e['event'] == 'home_retry' for e in machine.events))

    def test_every_non_home_motion_stage_remains_single_attempt(self):
        for stage in set(runtime.TASKS) - {'home'}:
            with self.subTest(stage=stage):
                machine = FakeRuntime([terminal(failed=True)], checkpoint_at(stage))
                with self.assertRaises(ValueError):
                    machine.motion_stage(stage)
                self.assertEqual(len(machine.actions), 1)
                self.assertFalse(machine.actions[0]['allow_home_retry'])
                self.assertNotIn('home_retry', machine.checkpoint)

    def test_standard_profiles_never_opt_in_even_with_assumed_release(self):
        for policy in ('ask', 'assume', 'sensors'):
            with self.subTest(policy=policy):
                cp = checkpoint_at(policy=policy, profile='standard_v1')
                machine = FakeRuntime([terminal(failed=True)], cp)
                with self.assertRaises(ValueError):
                    machine.motion_stage('home')
                self.assertEqual(len(machine.actions), 1)
                self.assertFalse(machine.actions[0]['allow_home_retry'])
                self.assertNotIn('home_retry', machine.checkpoint)

    def test_nonreleased_home_checkpoint_never_authorizes_an_attempt(self):
        for state in ('empty', 'held', 'unknown'):
            with self.subTest(box_state=state):
                cp = checkpoint_at()
                cp['box_state'] = state
                machine = FakeRuntime([terminal(failed=True)], cp)
                with self.assertRaises(ValueError):
                    machine.motion_stage('home')
                self.assertEqual(machine.actions, [])

    def test_wrong_or_unknown_terminal_results_never_send_second_goal(self):
        bad_results = []
        for status in (4, 5, True, 6.0):
            item = terminal(failed=True); item['status'] = status; bad_results.append(item)
        for desc in ('FAIL', 'MoveToGoalFailed ', 'ClampBoxOutOfReach'):
            item = terminal(failed=True); item['result']['state']['desc'] = desc; bad_results.append(item)
        for code in (7101100, True, 7104050.0):
            item = terminal(failed=True); item['result']['state']['state'] = code; bad_results.append(item)
        for key, value in [('event', 'feedback'), ('goal_id', None), ('goal_id', 'not-a-uuid')]:
            item = terminal(failed=True); item[key] = value; bad_results.append(item)
        bad_results += [None, {}, [], [terminal(failed=True), terminal(failed=True)]]
        for result in bad_results:
            with self.subTest(result=result):
                machine = FakeRuntime([result])
                with self.assertRaises((ValueError, RuntimeError, TypeError)):
                    machine.motion_stage('home')
                self.assertEqual(len(machine.actions), 1)
                self.assertNotIn('home_retry', machine.checkpoint)

    def test_timeout_unknown_outcome_and_client_failure_do_not_retry(self):
        for error in (TimeoutError('terminal outcome unknown'), RuntimeError('worker gone'),
                      RuntimeError('duplicate terminal result')):
            with self.subTest(error=error):
                machine = FakeRuntime([error])
                with self.assertRaises(type(error)):
                    machine.motion_stage('home')
                self.assertEqual([r['call'] for r in machine.trace], ['action'])
                self.assertNotIn('home_retry', machine.checkpoint)

    def test_connection_dependency_health_and_stationary_faults_block_retry(self):
        cases = [('connected', 1, 'PC disconnected'), ('discover', 1, 'container changed'),
                 ('hashes', 1, 'XML changed'), ('health', 1, 'actuator fault'),
                 ('health', 1, 'E-stop active'), ('health', 1, 'charger connected'),
                 ('quick_health', 1, 'not stationary'), ('quick_health', 1, 'stale live telemetry'),
                 ('connected', 2, 'lease expired')]
        for gate, count, reason in cases:
            with self.subTest(gate=gate, reason=reason):
                machine = FakeRuntime([terminal(failed=True)])
                machine.fail_at[gate] = (count, reason)
                with self.assertRaisesRegex(RuntimeError, reason):
                    machine.motion_stage('home')
                self.assertEqual(len(machine.actions), 1)
                self.assertNotIn('home_retry', machine.checkpoint)

    def test_failed_save_or_disconnect_after_reservation_never_dispatches_second_goal(self):
        for gate, count in [('save', 1), ('connected', 3)]:
            with self.subTest(gate=gate):
                machine = FakeRuntime([terminal(failed=True)])
                machine.fail_at[gate] = (count, 'cannot dispatch')
                with self.assertRaisesRegex(RuntimeError, 'cannot dispatch'):
                    machine.motion_stage('home')
                self.assertEqual(len(machine.actions), 1)
                self.assertFalse(contract.home_retry_available(machine.checkpoint))

    def test_second_failure_or_timeout_is_fatal_without_a_third_attempt(self):
        for second in (terminal(failed=True, goal_id=SECOND_UUID), TimeoutError('second timeout')):
            with self.subTest(second=second):
                machine = FakeRuntime([terminal(failed=True), second])
                with self.assertRaises((ValueError, TimeoutError)):
                    machine.motion_stage('home')
                self.assertEqual(len(machine.actions), 2)
                self.assertEqual([a['allow_home_retry'] for a in machine.actions], [True, False])
                self.assertFalse(contract.home_retry_available(machine.persisted))
                self.assertFalse(any(e.get('phase') == 'succeeded' for e in machine.events))

    def test_second_failure_is_journaled_as_failed_home_with_consumed_allowance(self):
        machine = FakeRuntime([terminal(failed=True), terminal(failed=True, goal_id=SECOND_UUID)],
                              checkpoint_at(active=False))
        with self.assertRaises(ValueError):
            machine.stage({'stage': 'home'})
        self.assertEqual(len(machine.actions), 2)
        self.assertEqual(machine.persisted['failure']['stage'], 'home')
        self.assertEqual(machine.persisted['box_state'], 'unknown')
        self.assertIsNone(machine.persisted['in_flight'])
        self.assertEqual(machine.persisted['home_retry']['used'], 1)
        self.assertNotIn('home', machine.persisted['completed'])
        self.assertFalse(any(e['event'] == 'stage_complete' for e in machine.events))

    def test_already_consumed_checkpoint_cannot_gain_another_retry(self):
        cp = contract.reserve_home_retry(checkpoint_at(), terminal(failed=True),
                                         first_result_ns=100, reserved_ns=101)
        machine = FakeRuntime([terminal(failed=True, goal_id=SECOND_UUID)], cp)
        with self.assertRaises(ValueError):
            machine.motion_stage('home')
        self.assertEqual(len(machine.actions), 1)
        self.assertFalse(machine.actions[0]['allow_home_retry'])
        self.assertEqual(machine.checkpoint, cp)

    def test_explicit_recovery_segment_inherits_consumed_retry(self):
        cp = contract.reserve_home_retry(checkpoint_at(), terminal(failed=True),
                                         first_result_ns=100, reserved_ns=101)
        cp = contract.fail_stage(cp, 'home', 'second native attempt failed')
        plan = resume.plan_resume(cp, PROFILE, stage='home', box_state='released',
                                  recovery_confirmed=True, policy='assume',
                                  execution_profile='optimistic_v1')
        active = contract.begin_stage(plan['checkpoint'], 'home')
        machine = FakeRuntime([terminal(failed=True, goal_id=SECOND_UUID)], active)
        with self.assertRaises(ValueError):
            machine.motion_stage('home')
        self.assertEqual(len(machine.actions), 1)
        self.assertFalse(machine.actions[0]['allow_home_retry'])
        self.assertEqual(machine.checkpoint['home_retry'], cp['home_retry'])

    def test_retry_stays_in_one_stage_and_graceful_pause_still_requires_measured_home(self):
        machine = FakeRuntime([terminal(failed=True), terminal(goal_id=SECOND_UUID)],
                              checkpoint_at(active=False))
        machine.stage({'stage': 'home'})
        completed = [e['stage'] for e in machine.events if e['event'] == 'stage_complete']
        self.assertEqual(completed, ['home'])
        self.assertEqual(contract.next_stage(machine.checkpoint), 'verify_home')
        self.assertFalse(cli.should_pause(machine.checkpoint, True))
        self.assertNotIn('verify_home', machine.checkpoint['completed'])
        self.assertFalse(any(r['call'] == 'health' and r['require_home'] for r in machine.trace))
        machine.stage({'stage': 'verify_home'})
        self.assertEqual(len(machine.actions), 2)
        self.assertTrue(any(r['call'] == 'health' and r['require_home'] for r in machine.trace))
        self.assertEqual([e['stage'] for e in machine.events if e['event'] == 'stage_complete'],
                         ['home', 'verify_home'])

    def test_successful_retry_cannot_hide_failure_of_final_measured_home(self):
        machine = FakeRuntime([terminal(failed=True), terminal(goal_id=SECOND_UUID)],
                              checkpoint_at(active=False))
        machine.stage({'stage': 'home'})
        machine.fail_at['health'] = (machine.gate_counts['health'] + 1, 'HOME not measured')
        with self.assertRaisesRegex(RuntimeError, 'HOME not measured'):
            machine.stage({'stage': 'verify_home'})
        self.assertEqual(len(machine.actions), 2)
        self.assertEqual(machine.checkpoint['failure']['stage'], 'verify_home')
        self.assertNotIn('verify_home', machine.checkpoint['completed'])


if __name__ == '__main__':
    unittest.main()
