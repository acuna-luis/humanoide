"""Offline regression checks; no ROS, network, processes or robot access."""
import copy
import json
import math
import unittest

from scripts.box_handling.scenario1_checks import (
    discover_containers, parse_controller_response, parse_health, parse_idle_status,
    validate_actuators, validate_map_points, validate_nav_pose,
)
from scripts.lib.cruzr_home_posture_gate import BODY_ACTUATOR_ALIASES, classify


def containers():
    return [dict(Name='/renamed-motion', State=dict(Running=True, Paused=False),
                 Config=dict(Image='registry/utars-integration:zs2_motion-v0.2.0',
                             Labels={'com.docker.compose.service': 'manipulation_robot_app'},
                             Env=['HW_TYPE=cruzr_s2_v1'])),
            dict(Name='/renamed-ros', State=dict(Running=True),
                 Config=dict(Image='registry/utars-integration:zs2_ros-v0.2.0',
                             Labels={'com.docker.compose.service': 'ros2'}, Env=[]))]


def controller_output(**replacements):
    states = {'manipulation_controller': 'running', 'sdk_controller': 'initialized',
              'vla_sdk_controller': 'initialized'}
    states.update(replacements)
    return 'Response(controller=' + repr([dict(name=k, state=v) for k, v in states.items()]) + ')\n'


def status_yaml(*statuses):
    if not statuses:
        return 'status_list: []\n---\n'
    return 'status_list:\n' + ''.join(
        '- goal_info:\n    goal_id:\n      uuid:\n      - 0\n'
        '    stamp:\n      sec: 100\n      nanosec: 0\n  status: %s\n' % status
        for status in statuses) + '---\n'


def health_battery(*socs):
    return 'batteries:\n' + ''.join('- batsoc: %s\n  voltage: 50.0\n' % soc for soc in socs)


def nav_pose(yaw=0.0, x=1.0, y=2.0, sec=100, ns=100_000_000):
    return dict(header=dict(frame_id='map', stamp=dict(sec=sec, nanosec=ns)),
                pose=dict(position=dict(x=x, y=y, z=0.0),
                          orientation=dict(x=0.0, y=0.0, z=math.sin(yaw / 2), w=math.cos(yaw / 2))))


def map_response():
    return dict(code=200, message=json.dumps(dict(umap=dict(target_points=[
        dict(id='get1', mode='logo_nav', type='logo', point_x=1, point_y=2, point_yaw=0),
        dict(id='put1', mode='', type='mapping_marker', point_x=3, point_y=4, point_yaw=.5)]))))


class DiscoveryChecks(unittest.TestCase):
    def test_service_labels_discover_renamed_containers(self):
        self.assertEqual(discover_containers(json.dumps(containers())),
                         {'native': 'renamed-motion', 'ros2': 'renamed-ros'})

    def test_historical_name_fallback_only_without_service_label(self):
        rows = containers()
        for row, name in zip(rows, ('walker-motion.manipulation_robot_app-1', 'walker-ros.ros2-1')):
            row['Name'] = '/' + name
            row['Config']['Labels'] = {}
        self.assertEqual(discover_containers(rows)['native'], 'walker-motion.manipulation_robot_app-1')
        rows[0]['Config']['Labels']['com.docker.compose.service'] = 'unrelated'
        with self.assertRaises(ValueError):
            discover_containers(rows)

    def test_ambiguous_missing_paused_stopped_and_restarting_fail(self):
        for state in ({'Running': False}, {'Running': True, 'Paused': True},
                      {'Running': True, 'Restarting': True}):
            rows = containers()
            rows[0]['State'] = state
            with self.subTest(state=state), self.assertRaises(ValueError):
                discover_containers(rows)
        rows = containers()
        extra = copy.deepcopy(rows[0]); extra['Name'] = '/other-motion'; rows.append(extra)
        with self.assertRaises(ValueError):
            discover_containers(rows)

    def test_hardware_and_image_fail_without_exposing_environment(self):
        for field, value in [('Env', ['HW_TYPE=other', 'PRIVATE_SENTINEL=do-not-show']),
                             ('Env', ['HW_TYPE=cruzr_s2_v1', 'HW_TYPE=cruzr_s2_v1']),
                             ('Image', 'unreviewed-build')]:
            rows = containers(); rows[0]['Config'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError) as error:
                discover_containers(rows)
            self.assertNotIn('PRIVATE_SENTINEL', str(error.exception))


class ControllerAndStatusChecks(unittest.TestCase):
    def test_expected_controller_state(self):
        self.assertEqual(parse_controller_response(controller_output())['sdk_controller'], 'initialized')

    def test_controller_changes_duplicate_and_missing_rejected(self):
        for output in (controller_output(sdk_controller='running'),
                       controller_output(manipulation_controller='initialized'),
                       controller_output() + controller_output(),
                       'Response(controller=[])', 'Response(controller=bad)', 'Response(controller=',
                       'Response(controller=[{"name":"sdk_controller","state":"initialized"},'
                       '{"name":"sdk_controller","state":"initialized"}])'):
            with self.subTest(output=output), self.assertRaises(ValueError):
                parse_controller_response(output)

    def test_explicit_empty_and_terminal_history_are_idle(self):
        self.assertEqual(parse_idle_status(status_yaml()), [])
        self.assertEqual(parse_idle_status(status_yaml(4, 5, 6)), [4, 5, 6])
        self.assertEqual(parse_idle_status('{"status_list":[{"status":4}]}'), [4])

    def test_unknown_active_invalid_and_truncated_status_fail(self):
        for output in (status_yaml(0), status_yaml(1), status_yaml(2), status_yaml(3),
                       status_yaml(7), status_yaml('false'), '', 'status_list:',
                       'status_list:\n- goal_info:\n    stamp:\n      sec: 100\n',
                       'status_list: []\nfailed query\n',
                       'status_list: []\n---\nstatus_list: []\n',
                       '{"status_list":[],"status_list":[]}', '{"status_list":[{"status":true}]}'):
            with self.subTest(output=output), self.assertRaises(ValueError):
                parse_idle_status(output)

    def test_duplicate_status_cannot_hide_executing_goal(self):
        output = status_yaml(4).replace('  status: 4', '  status: 2\n  status: 4')
        with self.assertRaises(ValueError):
            parse_idle_status(output)


class HealthChecks(unittest.TestCase):
    def health(self, **overrides):
        values = dict(estop='data: 0\n', servo='data: 0\n---\n', charger='data: 0\n',
                      battery=health_battery(20, 99.1))
        values.update(overrides)
        return parse_health(**values)

    def test_two_packs_and_clear_physical_inputs(self):
        self.assertEqual(self.health()['battery_soc'], [20., 99.1])
        self.assertEqual(self.health(battery={'batteries': [{'batsoc': 20}, {'batsoc': 70}]})['battery_soc'], [20., 70.])

    def test_each_estop_and_charger_fail_independently(self):
        for field in ('estop', 'servo', 'charger'):
            for value in ('data: 1\n', '', 'data: 0\ndata: 1\n', 'data: false\n', {'data': False}):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.health(**{field: value})

    def test_missing_low_invalid_extra_packs_and_weaker_threshold_fail(self):
        for battery in (health_battery(19.9, 80), health_battery(80), health_battery(30, 30, 30),
                        health_battery(101, 90), health_battery('NaN', 30), health_battery('true', 30),
                        'query failed\nbatsoc: 30\nbatsoc: 40\n',
                        {'bats': [{'batsoc': True}, {'batsoc': 60}]}):
            with self.subTest(battery=battery), self.assertRaises(ValueError):
                self.health(battery=battery)
        with self.assertRaises(ValueError):
            self.health(min_soc=10)

    def test_real_classifier_checks_20d_without_requiring_home(self):
        message = dict(act_item=[dict(id=aliases[0], error_code=0, status=7, position=.4,
                                     velocity=0., cmd_pos=.4) for _, aliases in BODY_ACTUATOR_ALIASES])
        report = validate_actuators(json.dumps(message), classify)
        self.assertEqual(report['MEASURED_HOME'], '0')
        for key, value in [('velocity', .021), ('cmd_pos', .42), ('error_code', 1), ('status', 15)]:
            changed = copy.deepcopy(message); changed['act_item'][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_actuators(changed, classify)
        with self.assertRaises(ValueError):
            validate_actuators({'act_item': []}, classify)


class ArrivalAndMapChecks(unittest.TestCase):
    target = dict(point_x=1., point_y=2., point_yaw=0.)

    def arrival(self, pose=None, **kwargs):
        arguments = dict(payload=nav_pose() if pose is None else pose, expected=self.target,
                         started_at=100., now=100.2)
        arguments.update(kwargs)
        return validate_nav_pose(**arguments)

    def test_fresh_arrival_and_advancing_second_sample(self):
        first = self.arrival()
        second = self.arrival(nav_pose(ns=200_000_000), previous_stamp=first['stamp'])
        self.assertGreater(second['stamp_ns'], first['stamp_ns'])
        self.assertEqual(second['distance_m'], 0.)

    def test_old_future_frozen_and_bad_clock_fail(self):
        for arguments in (dict(pose=nav_pose(sec=98)), dict(pose=nav_pose(sec=103)),
                          dict(previous_stamp=100.1), dict(now=99.9),
                          dict(pose=nav_pose(ns=-1)), dict(pose=nav_pose(sec=True)),
                          dict(pose=nav_pose(ns=1_000_000_000))):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                self.arrival(**arguments)

    def test_position_yaw_frame_nonfinite_and_bad_quaternion_fail(self):
        wrong_frame = nav_pose(); wrong_frame['header']['frame_id'] = 'odom'
        quaternion = nav_pose(); quaternion['pose']['orientation']['w'] = .5
        for pose in (nav_pose(x=1.051), nav_pose(yaw=math.radians(3.1)), nav_pose(x=float('nan')),
                     nav_pose(x=True), wrong_frame, quaternion, {}):
            with self.subTest(pose=pose), self.assertRaises(ValueError):
                self.arrival(pose)

    def test_yaw_wraparound_uses_shortest_angle(self):
        result = self.arrival(nav_pose(yaw=-math.pi+.01),
                              expected=dict(point_x=1., point_y=2., point_yaw=math.pi-.01))
        self.assertAlmostEqual(result['yaw_error_deg'], math.degrees(.02))

    def test_map_preserves_logo_and_marker_geometry(self):
        result = validate_map_points(map_response())
        self.assertEqual(result['get1']['mode'], 'logo_nav')
        self.assertEqual(result['get1']['id'], 'get1')
        self.assertEqual(result['put1']['mode'], 'free_nav')
        self.assertEqual(result['put1']['point_x'], 3.)
        self.assertEqual(result['put1']['speed']['linear']['x'], .18)
        self.assertEqual(result['put1']['_expected_pose']['point_yaw'], .5)

    def test_missing_duplicate_unknown_mode_and_invalid_map_fail(self):
        for alteration in ('missing', 'duplicate', 'mode', 'nonfinite', 'boolean'):
            response = map_response(); message = json.loads(response['message'])
            points = message['umap']['target_points']
            if alteration == 'missing': points.pop()
            if alteration == 'duplicate': points.append(copy.deepcopy(points[0]))
            if alteration == 'mode': points[0]['mode'] = 'unknown'
            if alteration == 'nonfinite': points[0]['point_x'] = float('inf')
            if alteration == 'boolean': points[0]['point_y'] = True
            response['message'] = message
            with self.subTest(alteration=alteration), self.assertRaises(ValueError):
                validate_map_points(response)
        for response in ({'code': 500}, [], '{"code":200,"code":500}'):
            with self.subTest(response=response), self.assertRaises(ValueError):
                validate_map_points(response)


if __name__ == '__main__':
    unittest.main()
