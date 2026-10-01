"""Continuous-cycle boundaries and cached-map navigation, with offline IO only."""
import copy
from contextlib import contextmanager
import json
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import scenario1_contract as contract
from scripts.box_handling import scenario1_resume as resume
from scripts.box_handling import scenario1_runtime as runtime
from scripts.box_handling.test_scenario1_optimistic import optimistic_machine
from scripts.box_handling.test_scenario1_runtime import PROFILE
from scripts.box_handling import test_scenario1_navigation_modes as navigation
from scripts.box_handling import test_scenario1_planner_sync as planner


def advance(machine, stop='verify_home'):
    while (stage := contract.next_stage(machine.checkpoint)) is not None:
        machine.stage(dict(stage=stage))
        if stage == stop:
            break


class CycleRolloverTest(unittest.TestCase):
    @contextmanager
    def machine(self, *, stop='verify_home'):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(runtime.time, 'monotonic', return_value=100.):
            machine = optimistic_machine(directory)
            machine.cycle = True
            machine.session_deadline = 110.
            (machine.session/'lease.json').write_text(json.dumps({'deadline': 110.}))
            machine.points = dict(cached='map and waypoints')
            machine.planner_map_synced = True
            advance(machine, stop=stop)
            yield machine

    def assert_unchanged(self, machine, before, lease):
        self.assertEqual(machine.checkpoint, before)
        self.assertEqual((machine.session/'lease.json').read_bytes(), lease)
        self.assertEqual(machine.cycle_number, 1)
        self.assertFalse(list(machine.session.glob('cycle-*.json')))
        self.assertFalse(any(row['event'] == 'cycle_ready' for row in machine.events))

    def test_full_verified_cycle_rolls_over_durably_without_map_or_motion_commands(self):
        with self.machine() as machine:
            completed = copy.deepcopy(machine.checkpoint)
            points = machine.points
            calls = list(machine.calls)
            machine.next_cycle(2)
            self.assertEqual(machine.calls, calls)
            self.assertEqual(machine.session_deadline, 1000.)
            self.assertEqual(json.loads((machine.session/'lease.json').read_text()), {'deadline': 1000.})
            self.assertIs(machine.points, points)
            self.assertTrue(machine.planner_map_synced)
            self.assertEqual(contract.next_stage(machine.checkpoint), 'navigate_get1')
            self.assertEqual(machine.checkpoint['box_state'], 'empty')
            self.assertEqual(machine.checkpoint['completed'], [])
            self.assertEqual(machine.checkpoint['execution_profile'], 'optimistic_v1')
            self.assertEqual(machine.checkpoint['policy'], 'assume')
            self.assertEqual(json.loads((machine.session/'checkpoint.json').read_text()), machine.checkpoint)
            archive = json.loads((machine.session/'cycle-000001.json').read_text())
            self.assertEqual(archive, dict(artifact='completed_cycle', cycle_number=1, checkpoint=completed))
            with self.assertRaises(ValueError):
                contract.validate_checkpoint(archive)
            self.assertEqual([event['event'] for event in machine.events[-2:]], ['checkpoint', 'cycle_ready'])
            self.assertEqual(machine.events[-1]['cycle_number'], 2)

    def test_partial_stages_including_successful_home_do_not_allow_rollover(self):
        for stage in contract.STAGES[:-1]:
            with self.subTest(stage=stage), self.machine(stop=stage) as machine:
                before = copy.deepcopy(machine.checkpoint)
                lease = (machine.session/'lease.json').read_bytes()
                with self.assertRaisesRegex(RuntimeError, 'CYCLE_BOUNDARY_NOT_VERIFIED'):
                    machine.next_cycle(2)
                self.assert_unchanged(machine, before, lease)

    def test_inflight_failed_or_unverified_home_cannot_be_promoted_by_rollover(self):
        for failed in (False, True):
            with self.subTest(failed=failed), self.machine(stop='home') as machine:
                machine.checkpoint = contract.begin_stage(machine.checkpoint, 'verify_home')
                if failed:
                    machine.checkpoint = contract.fail_stage(machine.checkpoint, 'verify_home', 'pose not HOME')
                before = copy.deepcopy(machine.checkpoint)
                lease = (machine.session/'lease.json').read_bytes()
                with self.assertRaises(ValueError):
                    machine.next_cycle(2)
                self.assert_unchanged(machine, before, lease)

    def test_disabled_unarmed_and_wrong_cycle_numbers_are_rejected(self):
        for setting, value in [('cycle', False), ('armed', False),
                               ('number', None), ('number', True), ('number', 0),
                               ('number', 1), ('number', 3), ('number', 2.)]:
            with self.subTest(setting=setting, value=value), self.machine() as machine:
                number = value if setting == 'number' else 2
                if setting != 'number':
                    setattr(machine, setting, value)
                before = copy.deepcopy(machine.checkpoint)
                lease = (machine.session/'lease.json').read_bytes()
                with self.assertRaisesRegex(RuntimeError, 'CYCLE_BOUNDARY_NOT_VERIFIED'):
                    machine.next_cycle(number)
                self.assert_unchanged(machine, before, lease)

    def test_repeated_rollover_requires_another_completed_cycle(self):
        with self.machine() as machine:
            machine.next_cycle(2)
            for number in (2, 3):
                with self.subTest(number=number), self.assertRaisesRegex(RuntimeError, 'CYCLE_BOUNDARY_NOT_VERIFIED'):
                    machine.next_cycle(number)
            advance(machine)
            machine.next_cycle(3)
            self.assertEqual(machine.cycle_number, 3)
            self.assertEqual(contract.next_stage(machine.checkpoint), 'navigate_get1')
            self.assertEqual([path.name for path in sorted(machine.session.glob('cycle-*.json'))],
                             ['cycle-000001.json', 'cycle-000002.json'])

    def test_cycle_requires_optimistic_full_length_profile(self):
        for profile, policy, stop in [('standard_v1', 'assume', 'verify_home'),
                                      ('optimistic_v1', 'assume', 'navigate_get1'),
                                      ('optimistic_v1', 'assume', 'verify_held')]:
            with self.subTest(profile=profile, stop=stop):
                cp = contract.new_checkpoint(PROFILE, policy=policy, execution_profile=profile, stop_after=stop)
                with self.assertRaisesRegex(ValueError, 'Continuous cycles'):
                    runtime.Runtime(dict(profile=PROFILE, checkpoint=cp, execution_profile=profile,
                                         policy=policy, cycle=True))
        cp = contract.new_checkpoint(PROFILE, policy='assume', execution_profile='optimistic_v1')
        for cycle in (1, 'true', None):
            with self.subTest(cycle=cycle), self.assertRaisesRegex(ValueError, 'Continuous cycles'):
                runtime.Runtime(dict(profile=PROFILE, checkpoint=cp, execution_profile='optimistic_v1',
                                     policy='assume', cycle=cycle))

    def test_stop_expiry_disconnect_and_monitor_fault_cannot_renew_lease(self):
        for failure in ('stop', 'expired', 'missing_deadline', 'heartbeat', 'adapter', 'health'):
            with self.subTest(failure=failure), self.machine() as machine:
                if failure == 'stop': machine.stop.set()
                if failure == 'expired': machine.session_deadline = 100.
                if failure == 'missing_deadline': machine.session_deadline = None
                if failure == 'heartbeat': machine.last_heartbeat = 87.
                if failure == 'adapter': machine.adapters = [Mock(poll=Mock(return_value=1))]
                if failure == 'health':
                    machine.live_monitor_enabled = True
                    machine.check_live_health = Mock(side_effect=ValueError('latched health fault'))
                before = copy.deepcopy(machine.checkpoint)
                lease = (machine.session/'lease.json').read_bytes()
                with self.assertRaises((ValueError, RuntimeError)):
                    machine.next_cycle(2)
                self.assert_unchanged(machine, before, lease)

    def test_watchdog_stop_after_connected_check_cannot_be_resurrected(self):
        with self.machine() as machine:
            before = copy.deepcopy(machine.checkpoint)
            lease = (machine.session/'lease.json').read_bytes()
            machine.connected = Mock(side_effect=machine.stop.set)
            with self.assertRaisesRegex(RuntimeError, 'CYCLE_LEASE_EXPIRED'):
                machine.next_cycle(2)
            self.assert_unchanged(machine, before, lease)

    def test_segmented_resume_finishes_then_clears_entry_requirements_for_next_cycle(self):
        with self.machine(stop='verify_released') as machine:
            plan = resume.plan_resume(machine.checkpoint, PROFILE, policy='assume',
                                      execution_profile='optimistic_v1')
            self.assertEqual(plan['stage'], 'home')
            machine.checkpoint = plan['checkpoint']
            machine.resume_plan = plan
            machine.resume_validated = True
            machine.check_resume_entry = Mock()
            advance(machine)
            self.assertEqual(machine.checkpoint['completed'], ['home', 'verify_home'])
            machine.next_cycle(2)
            self.assertIsNone(machine.resume_plan)
            self.assertFalse(machine.resume_validated)
            self.assertEqual(machine.checkpoint['version'], 2)
            self.assertNotIn('entry_stage', machine.checkpoint)
            self.assertEqual(contract.next_stage(machine.checkpoint), 'navigate_get1')
            machine.stage(dict(stage='navigate_get1'))
            machine.check_resume_entry.assert_called_once_with()

    def test_idle_clients_are_retired_before_renewal_but_health_and_small_clients_survive(self):
        with self.machine() as machine:
            old = Mock(sequence=128, failed=False)
            old.process.poll.return_value = None
            old.process.returncode = 0
            new = Mock(sequence=127, failed=False)
            new.process.poll.return_value = None
            machine.action_sessions = dict(motion=old, navigation=new)
            health = Mock(failed=False)
            health.process.poll.return_value = None
            machine.health_session = health
            machine.next_cycle(2)
            old.close.assert_called_once_with()
            new.close.assert_not_called()
            health.close.assert_not_called()
            self.assertEqual(machine.action_sessions, dict(navigation=new))
            self.assertIs(machine.health_session, health)

    def test_failed_client_or_failed_close_does_not_renew(self):
        for failed, returncode in [(True, 0), (False, 1)]:
            with self.subTest(failed=failed, returncode=returncode), self.machine() as machine:
                client = Mock(sequence=128, failed=failed)
                client.process.poll.return_value = None
                client.process.returncode = returncode
                machine.action_sessions['motion'] = client
                before = copy.deepcopy(machine.checkpoint)
                lease = (machine.session/'lease.json').read_bytes()
                with self.assertRaisesRegex(RuntimeError, 'PERSISTENT_WORKER_LOST|CYCLE_WORKER_CLOSE_FAILED'):
                    machine.next_cycle(2)
                self.assert_unchanged(machine, before, lease)


class CycleNavigationTest(unittest.TestCase):
    @contextmanager
    def machine(self):
        with planner.PlannerSyncTests().machine() as values:
            machine, events, pose, http = values
            machine.cycle = True
            yield values

    def test_first_navigation_loads_planner_later_navigation_keeps_fresh_pose_and_arrival(self):
        with self.machine() as (machine, events, pose, http):
            machine.navigate('get1')
            self.assertTrue(machine.planner_map_synced)
            self.assertEqual(http.call_count, 2)
            self.assertEqual(machine.health_request.call_count, 3)
            points = machine.points
            http_count = http.call_count
            machine.prepare_map = Mock(side_effect=AssertionError('No repeat prepare_map'))
            machine.map_points = Mock(side_effect=AssertionError('No repeat map_points'))
            machine.action.reset_mock()
            machine.health_request.reset_mock()
            machine.map_state.reset_mock()
            events.clear()
            for point in ('put1', 'get1', 'put1', 'get1'):
                pose.update(navigation.POSES[point])
                machine.navigate(point)
            self.assertIs(machine.points, points)
            self.assertEqual(http.call_count, http_count)
            machine.prepare_map.assert_not_called()
            machine.map_points.assert_not_called()
            self.assertEqual(planner.PlannerSyncTests().commands(machine), [('navigation', 'navigation_start')]*4)
            self.assertEqual(machine.health_request.call_count, 8)
            self.assertEqual(machine.map_state.call_count, 4)
            self.assertEqual(len([event for event in events if event['event'] == 'arrival']), 8)

    def test_broken_pose_still_blocks_before_navigation_despite_cached_map(self):
        with self.machine() as (machine, events, pose, http):
            machine.navigate('get1')
            machine.action.reset_mock()
            machine.health_request.side_effect = RuntimeError('pose unavailable')
            with self.assertRaisesRegex(RuntimeError, 'pose unavailable'):
                machine.navigate('get1')
            machine.action.assert_not_called()

    def test_post_navigation_map_change_blocks_cycle_arrival(self):
        with self.machine() as (machine, events, pose, http):
            machine.navigate('get1')
            machine.action.reset_mock()
            machine.health_request.reset_mock()
            machine.map_state.return_value = ('other_map', 'FSM_WAITNAVIGATE')
            events.clear()
            with self.assertRaisesRegex(RuntimeError, 'Estado después de navegación'):
                machine.navigate('get1')
            machine.action.assert_called_once()
            self.assertEqual(machine.health_request.call_count, 1)
            self.assertFalse(any(row['event'] == 'arrival' for row in events))

    def test_cached_navigation_rejects_bad_arrival_instead_of_entering_next_stage(self):
        for point in ('get1', 'put1'):
            with self.subTest(point=point), self.machine() as (machine, events, pose, http):
                machine.navigate('get1')
                pose.update(navigation.POSES[point])
                machine.action.reset_mock()
                machine.health_request.reset_mock()
                events.clear()

                def dispatched(*args):
                    pose['point_x'] += .06
                    return copy.deepcopy(navigation.SUCCESS)

                machine.action.side_effect = dispatched
                with self.assertRaises((ValueError, RuntimeError)):
                    machine.navigate(point)
                machine.action.assert_called_once()
                self.assertEqual(machine.health_request.call_count, 2)
                self.assertFalse(any(row['event'] == 'arrival' for row in events))

    def test_native_failure_after_cache_reuse_is_not_retried_as_map_preparation(self):
        with self.machine() as (machine, events, pose, http):
            machine.navigate('get1')
            machine.action.reset_mock()
            machine.action.side_effect = lambda *args: copy.deepcopy(navigation.OUTSIDE_MAP)
            machine.prepare_map = Mock(side_effect=AssertionError('No retry'))
            machine.map_points = Mock(side_effect=AssertionError('No retry'))
            with self.assertRaises(ValueError):
                machine.navigate('get1')
            machine.action.assert_called_once()
            machine.prepare_map.assert_not_called()
            machine.map_points.assert_not_called()


if __name__ == '__main__':
    unittest.main()
