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
    def test_observed_vendor_labels_ignore_ros_export_and_other_motion_services(self):
        rows = containers()
        rows[0]['Name'] = '/walker-motion.manipulation_robot_app-1'
        rows[0]['Config']['Labels']['com.docker.compose.service'] = 'motion.manipulation_robot_app'
        rows[1]['Name'] = '/walker-ros.ros2-1'
        rows[1]['Config']['Labels']['com.docker.compose.service'] = 'ros.ros2'
        for name, service in [('walker-ros.ros2-export-1', 'ros.ros2-export'),
                              ('walker-motion.hw-1', 'motion.hw'),
                              ('walker-motion.mc_common-1', 'motion.mc_common')]:
            row = copy.deepcopy(rows[0])
            row['Name'] = '/'+name
            row['Config']['Labels']['com.docker.compose.service'] = service
            rows.append(row)
        self.assertEqual(discover_containers(rows), {'native':'walker-motion.manipulation_robot_app-1',
                                                    'ros2':'walker-ros.ros2-1'})

    def test_short_and_qualified_aliases_still_require_one_unique_role(self):
        rows = containers()
        extra = copy.deepcopy(rows[0])
        extra['Name'] = '/second-motion'
        extra['Config']['Labels']['com.docker.compose.service'] = 'motion.manipulation_robot_app'
        rows.append(extra)
        with self.assertRaisesRegex(ValueError, 'native=2'):
            discover_containers(rows)

    def test_known_name_conflicting_with_recognized_role_rejected(self):
        rows = containers()
        rows[0]['Name'] = '/walker-ros.ros2-1'
        with self.assertRaisesRegex(ValueError, 'conflicts'):
            discover_containers(rows)

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
                         started_at=100., now=100.2, point='get1')
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

    def test_each_destination_requires_its_radial_distance_limit(self):
        origin = dict(point_x=0., point_y=0., point_yaw=0.)
        for point, maximum in (('get1', .02), ('put1', .05)):
            with self.subTest(point=point):
                inside = maximum - 1e-8
                result = self.arrival(nav_pose(x=.6*inside, y=.8*inside),
                                      point=point, expected=origin)
                self.assertAlmostEqual(result['distance_m'], inside)
                self.assertEqual(result['distance_tolerance_m'], maximum)
                # This axis-aligned boundary is exactly representable by the
                # same float threshold, without subtracting a large map origin.
                self.arrival(nav_pose(x=maximum, y=0), point=point, expected=origin)
                # A nonzero map origin must not reject an inclusive boundary
                # solely because subtraction introduces float roundoff.
                self.arrival(nav_pose(x=1.+maximum), point=point)
                outside = maximum + 1e-8
                with self.assertRaisesRegex(ValueError, 'outside'):
                    self.arrival(nav_pose(x=.6*outside, y=.8*outside),
                                 point=point, expected=origin)
                # Per-axis checks would wrongly accept this diagonal error.
                with self.assertRaisesRegex(ValueError, 'outside'):
                    self.arrival(nav_pose(x=.8*maximum, y=.8*maximum),
                                 point=point, expected=origin)

    def test_each_destination_requires_its_yaw_limit_in_both_directions(self):
        for point, maximum_deg in (('get1', 2.), ('put1', 3.)):
            for sign in (-1, 1):
                with self.subTest(point=point, sign=sign):
                    result = self.arrival(nav_pose(yaw=math.radians(sign*(maximum_deg-1e-6))),
                                          point=point)
                    self.assertAlmostEqual(result['yaw_error_deg'], maximum_deg-1e-6)
                    self.assertEqual(result['yaw_tolerance_deg'], maximum_deg)
                    self.arrival(nav_pose(yaw=math.radians(sign*maximum_deg)), point=point)
                    with self.assertRaisesRegex(ValueError, 'outside'):
                        self.arrival(nav_pose(yaw=math.radians(sign*(maximum_deg+1e-6))),
                                     point=point)

    def test_get1_rejects_22mm_and_2_2deg_that_put1_still_accepts(self):
        for pose in (nav_pose(x=1.022), nav_pose(yaw=math.radians(2.2))):
            with self.subTest(pose=pose):
                with self.assertRaisesRegex(ValueError, 'outside'):
                    self.arrival(pose, point='get1')
                self.arrival(pose, point='put1')

    def test_destination_is_required_and_unknown_names_fail(self):
        with self.assertRaises(TypeError):
            validate_nav_pose(nav_pose(), self.target, 100., 100.2)
        for point in ('', 'get2', 'GET1', 'navigation_get1', None, True, []):
            with self.subTest(point=point), self.assertRaises(ValueError):
                self.arrival(point=point)

    def test_stricter_destination_still_rejects_stale_and_repeated_poses(self):
        for point in ('get1', 'put1'):
            with self.subTest(point=point):
                with self.assertRaises(ValueError):
                    self.arrival(nav_pose(sec=98), point=point)
                first = self.arrival(point=point)
                with self.assertRaises(ValueError):
                    self.arrival(previous_stamp=first['stamp'], point=point)

    def test_map_preserves_logo_and_marker_geometry(self):
        result = validate_map_points(map_response())
        self.assertEqual(result['get1']['mode'], 'logo_nav')
        self.assertEqual(result['get1']['id'], 'get1')
        self.assertEqual(result['put1']['mode'], 'free_nav')
        self.assertEqual(result['put1']['point_x'], 3.)
        self.assertEqual(result['put1']['speed']['linear']['x'], .18)
        self.assertEqual(result['put1']['_expected_pose']['point_yaw'], .5)

    def test_explicit_free_nav_preserves_current_pose_and_speed_policy(self):
        response = map_response()
        message = json.loads(response['message'])
        point = message['umap']['target_points'][0]
        point.update(mode='free_nav', type='precise_marker',
                     point_x=1.6735242237794687, point_y=.27833227656019477,
                     point_yaw=1.5997746657494152, speed_x=.3, speed_yaw=.3)
        response['message'] = message
        before = copy.deepcopy(response)
        target = validate_map_points(response)['get1']
        self.assertEqual(target['mode'], 'free_nav')
        self.assertEqual(target['level'], 1)
        for field in ('point_x', 'point_y', 'point_yaw'):
            self.assertEqual(target[field], point[field])
            self.assertEqual(target['_expected_pose'][field], point[field])
        self.assertEqual(target['speed'], {'linear': {'x': .18, 'y': .01, 'z': 0.},
                                          'angular': {'x': 0., 'y': 0., 'z': .20}})
        self.assertNotIn('id', target)
        self.assertEqual(response, before)

    def test_precise_logo_nav_keeps_id_and_does_not_copy_editor_metadata(self):
        response = map_response()
        message = json.loads(response['message'])
        point = message['umap']['target_points'][0]
        point.update(type='precise_marker', keyframe_index=-1,
                     mark_point={'id': 'false', 'point_x': .0001})
        response['message'] = message
        target = validate_map_points(response)['get1']
        self.assertEqual(target, {'map_name': 'utars_nav_map', 'mode': 'logo_nav', 'id': 'get1',
                                 '_expected_pose': {'point_x': 1., 'point_y': 2., 'point_yaw': 0.}})

    def test_empty_mode_is_only_supported_for_historical_mapping_marker(self):
        for marker_type in ('precise_marker', 'logo', None):
            response = map_response()
            message = json.loads(response['message'])
            message['umap']['target_points'][0].update(mode='', type=marker_type)
            response['message'] = message
            with self.subTest(marker_type=marker_type), self.assertRaisesRegex(ValueError, 'mode'):
                validate_map_points(response)

    def test_explicit_free_nav_still_requires_finite_coordinates_and_unique_points(self):
        for problem in ('duplicate', 'missing_coordinate', 'nan', 'bool'):
            response = map_response()
            message = json.loads(response['message'])
            points = message['umap']['target_points']
            points[0]['mode'] = 'free_nav'
            if problem == 'duplicate': points.append(copy.deepcopy(points[0]))
            if problem == 'missing_coordinate': del points[0]['point_yaw']
            if problem == 'nan': points[0]['point_x'] = float('nan')
            if problem == 'bool': points[0]['point_y'] = False
            response['message'] = message
            with self.subTest(problem=problem), self.assertRaises(ValueError):
                validate_map_points(response)

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
