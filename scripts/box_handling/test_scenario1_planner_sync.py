"""Regression for a planner caching zero destinations before an editor save."""
import copy
from contextlib import contextmanager
import json
from types import MethodType
import unittest

from scripts.box_handling import scenario1_runtime as runtime
from scripts.box_handling import test_scenario1_navigation_modes as fixtures


READY = dict(event='result', status=4, result=dict(state=dict(desc='READY', state=0)))


class PlannerSyncTests(unittest.TestCase):
    @contextmanager
    def machine(self, modes=('logo_nav', 'logo_nav')):
        helper = fixtures.NavigationModesTests()
        with helper.machine(fixtures.saved_map(*modes)) as values:
            machine, events, pose, http = values
            machine.sync_planner_map = MethodType(runtime.Runtime.sync_planner_map, machine)
            machine.action.side_effect = lambda kind, goal, timeout: copy.deepcopy(
                READY if kind == 'planning' else fixtures.SUCCESS)
            yield values

    def commands(self, machine):
        return [(call.args[0], call.args[1]['command']) for call in machine.action.call_args_list]

    def test_reload_populates_empty_cache_before_id_lookup_and_only_once(self):
        with self.machine() as (machine, events, pose, http):
            cached = set()
            def dispatch(kind, goal, timeout):
                if kind == 'planning':
                    self.assertEqual(set(goal), {'command', 'map_name'})
                    self.assertEqual(goal['map_name'], 'utars_nav_map')
                    if goal['command'] == 'set_map':
                        cached.update(fixtures.POSES)
                    return copy.deepcopy(READY)
                target = json.loads(goal['arg_json'])['target_point']
                self.assertEqual(target['mode'], 'logo_nav')
                return copy.deepcopy(fixtures.SUCCESS if target['id'] in cached else fixtures.OUTSIDE_MAP)
            machine.action.side_effect = dispatch
            machine.navigate('get1')
            pose.update(fixtures.POSES['put1'])
            machine.navigate('put1')
            self.assertEqual(self.commands(machine), [('planning', 'check_state'), ('planning', 'set_map'),
                ('navigation', 'navigation_start'), ('navigation', 'navigation_start')])
            self.assertTrue(machine.planner_map_synced)
            self.assertEqual(machine.health_request.call_count, 5)
            sync = [row for row in events if row['event'] == 'planner_map_sync']
            self.assertEqual([row['phase'] for row in sync], ['start', 'complete'])
            self.assertEqual(len([row for row in events if row['event'] == 'arrival']), 4)

    def test_refresh_preserves_each_requested_navigation_mode(self):
        for mode in ('free_nav', 'logo_nav'):
            with self.subTest(mode=mode), self.machine((mode, mode)) as (machine, events, pose, http):
                machine.navigate('get1')
                goal = machine.action.call_args.args[1]
                self.assertEqual(json.loads(goal['arg_json'])['target_point']['mode'], mode)
                self.assertEqual(self.commands(machine)[:2], [('planning', 'check_state'), ('planning', 'set_map')])

    def test_previous_finished_navigation_allows_refresh_but_reload_must_be_ready(self):
        finished = copy.deepcopy(READY); finished['result']['state']['desc'] = 'FINISH'
        with self.machine() as (machine, events, pose, http):
            machine.action.side_effect = [finished, copy.deepcopy(READY), copy.deepcopy(fixtures.SUCCESS)]
            machine.navigate('get1')
            self.assertTrue(machine.planner_map_synced)
        with self.machine() as (machine, events, pose, http):
            machine.action.side_effect = [copy.deepcopy(READY), finished]
            with self.assertRaises(ValueError): machine.navigate('get1')
            self.assertFalse(machine.planner_map_synced)

    def test_busy_or_unknown_planner_blocks_reload_and_navigation(self):
        for desc in ('RUNNING', 'MAP_SETTING', 'MAP_SETTING_ERROR', 'UNKNOWN'):
            with self.subTest(desc=desc), self.machine() as (machine, events, pose, http):
                failed = copy.deepcopy(READY); failed['result']['state']['desc'] = desc
                machine.action.side_effect = lambda *args: failed
                with self.assertRaises(ValueError): machine.navigate('get1')
                self.assertEqual(self.commands(machine), [('planning', 'check_state')])
                self.assertFalse(machine.planner_map_synced)

    def test_reload_failure_or_timeout_is_terminal_before_navigation(self):
        for failure in (RuntimeError('timeout'), dict(event='result', status=4,
                result=dict(state=dict(desc='MAP_SETTING_ERROR', state=0)))):
            with self.subTest(failure=failure), self.machine() as (machine, events, pose, http):
                machine.action.side_effect = [copy.deepcopy(READY), failure]
                with self.assertRaises((ValueError, RuntimeError)): machine.navigate('get1')
                self.assertEqual(len(machine.action.call_args_list), 2)
                self.assertFalse(machine.planner_map_synced)
                self.assertFalse(any(row['event'] == 'navigation_target' for row in events))

    def test_navigation_map_change_blocks_reload(self):
        with self.machine() as (machine, events, pose, http):
            machine.map_state.side_effect = [('utars_nav_map', 'FSM_WAITNAVIGATE'),
                                             ('other', 'FSM_WAITNAVIGATE')]
            with self.assertRaisesRegex(RuntimeError, 'PLANNER_SYNC_MAP_NOT_READY'): machine.navigate('get1')
            machine.action.assert_not_called()

    def test_changes_during_reload_block_navigation(self):
        for changed in ('map', 'points', 'pose'):
            with self.subTest(changed=changed), self.machine() as (machine, events, pose, http):
                def dispatch(kind, goal, timeout):
                    if goal['command'] == 'set_map':
                        if changed == 'map': machine.map_state.return_value = ('other', 'FSM_WAITNAVIGATE')
                        if changed == 'points': machine.points['get1']['_expected_pose']['point_x'] += .01
                        if changed == 'pose': machine.health_request.side_effect = RuntimeError('pose unavailable')
                    return copy.deepcopy(READY)
                machine.action.side_effect = dispatch
                with self.assertRaises(RuntimeError): machine.navigate('get1')
                self.assertEqual(len(machine.action.call_args_list), 2)
                self.assertFalse(machine.planner_map_synced)

    def test_native_rejection_after_refresh_still_fails_and_never_retries(self):
        with self.machine() as (machine, events, pose, http):
            machine.action.side_effect = [copy.deepcopy(READY), copy.deepcopy(READY),
                                          copy.deepcopy(fixtures.OUTSIDE_MAP)]
            with self.assertRaises(ValueError): machine.stage({'stage': 'navigate_get1'})
            self.assertEqual(self.commands(machine), [('planning', 'check_state'), ('planning', 'set_map'),
                                                       ('navigation', 'navigation_start')])
            self.assertEqual(machine.checkpoint['failure']['stage'], 'navigate_get1')
            self.assertEqual(machine.checkpoint['completed'], [])
            with self.assertRaises(ValueError): machine.stage({'stage': 'enable_vision'})

    def test_new_session_requires_its_own_reload(self):
        for _ in range(2):
            with self.machine() as (machine, events, pose, http):
                machine.navigate('get1')
                self.assertIn(('planning', 'set_map'), self.commands(machine))


if __name__ == '__main__':
    unittest.main()
