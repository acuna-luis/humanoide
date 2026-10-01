"""Saved-map navigation modes through the real dispatcher, with offline IO only."""
import copy
from contextlib import contextmanager
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import scenario1_contract as contract
from scripts.box_handling import scenario1_runtime as runtime
from scripts.box_handling.test_scenario1_checks import nav_pose


PROFILE = json.loads(Path(__file__).with_name('scenario1_current_geometry.json').read_text())
POSES = {
    'get1': dict(point_x=1.6735242237794687, point_y=.27833227656019477,
                 point_yaw=1.5997746657494152),
    'put1': dict(point_x=.8480681192655206, point_y=.08398720513730051,
                 point_yaw=-1.5556636186477018),
}
SUCCESS = dict(event='result', status=4, result=dict(
    state=dict(desc='SUCCEED', state=1101001), dmsg='navigation_start SUCCEEDED'))
OUTSIDE_MAP = dict(event='result', status=6, result=dict(
    state=dict(desc='导航模块,目标点附近停靠超出范围,请检查目标点合法性', state=7218013),
    dmsg='navigation_start FAILURE, change to FSM_WaitNavigate'))


def saved_map(get1_mode, put1_mode):
    points = []
    for name, mode in [('get1', get1_mode), ('put1', put1_mode)]:
        points.append(dict(id=name, mode=mode,
            type='mapping_marker' if mode == '' else 'precise_marker',
            mark_point=dict(id='false'), keyframe_index=-1,
            speed_x=.3, speed_y=.05, speed_yaw=.3, **POSES[name]))
    return dict(code=200, message=dict(umap=dict(target_points=points)))


class NavigationModesTests(unittest.TestCase):
    @contextmanager
    def machine(self, response):
        """Keep map parsing, readiness, pose checks, dispatch and journals real."""
        events = []
        clock = {'now': 100.}
        pose = dict(POSES['get1'])
        checkpoint = contract.new_checkpoint(PROFILE, policy='assume')

        def fetch(request, timeout):
            self.assertEqual(request.full_url, 'http://192.168.11.3:30023/map/get/utars_nav_map')
            self.assertEqual(request.method, 'POST')
            self.assertEqual(timeout, 8)
            return io.BytesIO(json.dumps(response).encode())

        def telemetry(kind):
            self.assertEqual(kind, 'pose')
            rows = []
            for offset in (.1, .2):
                stamp = round((clock['now'] + offset) * 1e9)
                rows.append(nav_pose(x=pose['point_x'], y=pose['point_y'], yaw=pose['point_yaw'],
                    sec=stamp // 1_000_000_000, ns=stamp % 1_000_000_000))
            clock['now'] += .3
            return dict(poses=rows, publisher_count=2)

        with tempfile.TemporaryDirectory() as directory, \
                patch.object(runtime.time, 'time', side_effect=lambda: clock['now']), \
                patch.object(runtime.time, 'monotonic', side_effect=lambda: clock['now']), \
                patch.object(runtime.urllib.request, 'urlopen', side_effect=fetch) as http, \
                patch.object(runtime.subprocess, 'run', side_effect=AssertionError('No processes')), \
                patch.object(runtime.subprocess, 'Popen', side_effect=AssertionError('No processes')):
            machine = runtime.Runtime(dict(mode='run', profile=PROFILE, checkpoint=checkpoint),
                lambda event, **values: events.append(dict(event=event, **values)))
            machine.session = Path(directory)
            machine.armed = True
            machine.discover = Mock()
            machine.hashes = Mock()
            machine.health = Mock()
            machine.sync_planner_map = Mock()  # Separately covered by planner synchronization tests.
            machine.map_state = Mock(return_value=('utars_nav_map', 'FSM_WAITNAVIGATE'))
            machine.health_request = Mock(side_effect=telemetry)
            machine.action = Mock(return_value=copy.deepcopy(SUCCESS))
            yield machine, events, pose, http

    def assert_target(self, machine, name, mode):
        kind, goal, timeout = machine.action.call_args.args
        self.assertEqual((kind, goal['command'], timeout), ('navigation', 'navigation_start', 180))
        self.assertEqual(machine.action.call_args.kwargs, {})
        target = json.loads(goal['arg_json'])['target_point']
        self.assertEqual(target['mode'], mode)
        self.assertEqual(target['map_name'], 'utars_nav_map')
        self.assertNotIn('_expected_pose', target)
        if mode == 'logo_nav':
            self.assertEqual(target, dict(map_name='utars_nav_map', mode='logo_nav', id=name))
        else:
            self.assertEqual({key: target[key] for key in POSES[name]}, POSES[name])
            self.assertEqual(target['level'], 1)
            self.assertEqual(target['speed'], dict(linear=dict(x=.18, y=.01, z=0.),
                                                   angular=dict(x=0., y=0., z=.2)))
        self.assertEqual(machine.points[name]['_expected_pose'], POSES[name])
        return target

    def dispatch_both(self, modes):
        response = saved_map(*modes)
        with self.machine(response) as (machine, events, pose, http):
            for name, mode in zip(('get1', 'put1'), modes):
                pose.update(POSES[name])
                machine.navigate(name)
                self.assert_target(machine, name, mode or 'free_nav')
                arrivals = [row for row in events if row['event'] == 'arrival' and row['point'] == name]
                self.assertEqual(len(arrivals), 2)
                for row in arrivals:
                    self.assertLess(row['measurement']['distance_m'], 1e-12)
            self.assertEqual(machine.action.call_count, 2)
            self.assertEqual(machine.health_request.call_count, 4)
            self.assertEqual(http.call_count, 2)

    def test_explicit_free_nav_dispatches_current_saved_poses_for_both_points(self):
        self.dispatch_both(('free_nav', 'free_nav'))

    def test_precise_logo_nav_dispatches_ids_for_both_points(self):
        self.dispatch_both(('logo_nav', 'logo_nav'))

    def test_points_may_use_different_navigation_modes(self):
        for modes in [('logo_nav', 'free_nav'), ('free_nav', 'logo_nav')]:
            with self.subTest(modes=modes):
                self.dispatch_both(modes)

    def test_legacy_mapping_marker_and_string_message_remain_supported(self):
        response = saved_map('', 'logo_nav')
        response['message'] = json.dumps(response['message'])
        with self.machine(response) as (machine, events, pose, http):
            machine.navigate('get1')
            self.assert_target(machine, 'get1', 'free_nav')

    def test_target_event_precedes_action_and_describes_actual_wire_goal(self):
        for mode in ('free_nav', 'logo_nav'):
            with self.subTest(mode=mode), self.machine(saved_map(mode, mode)) as (machine, events, pose, http):
                def action(kind, goal, timeout):
                    self.assertEqual(events[-1], dict(event='navigation_target', point='get1',
                        mode=mode, expected=POSES['get1'], target=json.loads(goal['arg_json'])['target_point']))
                    return copy.deepcopy(SUCCESS)
                machine.action.side_effect = action
                machine.navigate('get1')
                machine.action.assert_called_once()

    def test_native_failure_never_switches_modes_retries_or_claims_arrival(self):
        for mode in ('free_nav', 'logo_nav'):
            for point in ('get1', 'put1'):
                with self.subTest(mode=mode, point=point), self.machine(saved_map(mode, mode)) as (
                        machine, events, pose, http):
                    pose.update(POSES[point])
                    machine.action.return_value = copy.deepcopy(OUTSIDE_MAP)
                    with self.assertRaises(ValueError):
                        machine.navigate(point)
                    machine.action.assert_called_once()
                    self.assert_target(machine, point, mode)
                    self.assertEqual(machine.health_request.call_count, 1)
                    self.assertFalse(any(row['event'] == 'arrival' for row in events))

    def test_get1_native_failure_is_persisted_before_vision_or_grasp(self):
        for mode in ('free_nav', 'logo_nav'):
            with self.subTest(mode=mode), self.machine(saved_map(mode, mode)) as (machine, events, pose, http):
                def fail_action(*args):
                    stored = json.loads((machine.session / 'checkpoint.json').read_text())
                    self.assertEqual(stored['in_flight'], 'navigate_get1')
                    return copy.deepcopy(OUTSIDE_MAP)
                machine.action.side_effect = fail_action
                with self.assertRaises(ValueError):
                    machine.stage(dict(stage='navigate_get1'))
                stored = json.loads((machine.session / 'checkpoint.json').read_text())
                self.assertEqual(stored['completed'], [])
                self.assertEqual(stored['failure']['stage'], 'navigate_get1')
                self.assertIsNone(stored['in_flight'])
                self.assertFalse(any(row['event'] == 'stage_complete' for row in events))
                for stage in ('enable_vision', 'grasp'):
                    with self.assertRaises(ValueError):
                        machine.stage(dict(stage=stage))
                machine.action.assert_called_once()

    def test_mode_changes_after_preflight_block_before_dispatch(self):
        for before, after in [('free_nav', 'logo_nav'), ('logo_nav', 'free_nav')]:
            with self.subTest(before=before, after=after):
                response = saved_map(before, before)
                with self.machine(response) as (machine, events, pose, http):
                    machine.map_points()
                    response['message']['umap']['target_points'][0]['mode'] = after
                    with self.assertRaisesRegex(RuntimeError, 'MAP_POINTS_CHANGED'):
                        machine.navigate('get1')
                    machine.action.assert_not_called()
                    machine.health_request.assert_not_called()

    def test_coordinate_changes_after_preflight_block_before_dispatch(self):
        for mode in ('free_nav', 'logo_nav'):
            for coordinate in ('point_x', 'point_y', 'point_yaw'):
                with self.subTest(mode=mode, coordinate=coordinate):
                    response = saved_map(mode, mode)
                    with self.machine(response) as (machine, events, pose, http):
                        machine.map_points()
                        response['message']['umap']['target_points'][1][coordinate] += .01
                        with self.assertRaisesRegex(RuntimeError, 'MAP_POINTS_CHANGED'):
                            machine.navigate('put1')
                        machine.action.assert_not_called()

    def test_map_state_change_after_success_still_blocks_arrival(self):
        for mode in ('free_nav', 'logo_nav'):
            with self.subTest(mode=mode), self.machine(saved_map(mode, mode)) as (machine, events, pose, http):
                machine.map_state.side_effect = [('utars_nav_map', 'FSM_WAITNAVIGATE'),
                                                 ('another_map', 'FSM_WAITNAVIGATE')]
                with self.assertRaisesRegex(RuntimeError, 'Estado después de navegación'):
                    machine.navigate('get1')
                machine.action.assert_called_once()
                self.assertEqual(machine.health_request.call_count, 1)
                self.assertFalse(any(row['event'] == 'arrival' for row in events))

    def test_successful_actions_in_either_mode_still_require_measured_arrival(self):
        for mode in ('free_nav', 'logo_nav'):
            for point in ('get1', 'put1'):
                with self.subTest(mode=mode, point=point), self.machine(saved_map(mode, mode)) as (
                        machine, events, pose, http):
                    pose.update(POSES[point])
                    pose['point_x'] += .06  # Outside arrival and bounded get1 correction entry.
                    with self.assertRaises((ValueError, RuntimeError)):
                        machine.navigate(point)
                    machine.action.assert_called_once()
                    self.assertEqual(machine.health_request.call_count, 2)
                    self.assertFalse(any(row['event'] == 'arrival' for row in events))


if __name__ == '__main__':
    unittest.main()
