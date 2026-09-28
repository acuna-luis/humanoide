"""Pure input checks for scenario 1; no clients, commands or physical authority.

Callers must establish fresh, bounded reads. The YAML readers deliberately
accept the ROS CLI message forms used here, not arbitrary YAML documents.
"""
import ast
import json
import math
import re


EXPECTED_HW_TYPE = 'cruzr_s2_v1'
EXPECTED_IMAGE_FRAGMENT = 'utars-integration:zs2_motion-v0.2.0'
MIN_BATTERY_SOC = 20.0


def _object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON field')
        result[key] = value
    return result


def _reject_constant(_value):
    raise ValueError('Nonfinite JSON value')


def _json(value):
    if isinstance(value, str):
        try:
            return json.loads(value, object_pairs_hook=_object_pairs,
                              parse_constant=_reject_constant)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError('Malformed JSON') from exc
    return value


def _number(value, label):
    if type(value) not in (int, float):
        raise ValueError(label + ' must be finite and numeric')
    try:
        value = float(value)
    except OverflowError as exc:
        raise ValueError(label + ' must be finite and numeric') from exc
    if not math.isfinite(value):
        raise ValueError(label + ' must be finite and numeric')
    return value


def discover_containers(inspect_json):
    """Discover unique running roles; return names only, never environment data."""
    inventory = _json(inspect_json)
    if not isinstance(inventory, list) or not inventory:
        raise ValueError('Missing Docker inventory')
    roles = {'native': [], 'ros2': []}
    # Both the short Compose services and the qualified vendor services occur
    # in this project. Match exact labels: ros.ros2-export is a different role.
    services = {'manipulation_robot_app': 'native', 'motion.manipulation_robot_app': 'native',
                'ros2': 'ros2', 'ros.ros2': 'ros2'}
    fallbacks = {'walker-motion.manipulation_robot_app-1': 'native',
                 'walker-ros.ros2-1': 'ros2'}
    seen = set()
    for row in inventory:
        if not isinstance(row, dict):
            raise ValueError('Malformed Docker inventory')
        name = row.get('Name', '')
        if not isinstance(name, str) or not re.fullmatch(r'/?[A-Za-z0-9][A-Za-z0-9_.-]*', name):
            raise ValueError('Invalid Docker name')
        name = name.removeprefix('/')
        if name in seen:
            raise ValueError('Duplicate Docker container')
        seen.add(name)
        config = row.get('Config')
        if not isinstance(config, dict):
            raise ValueError('Missing Docker configuration')
        labels = config.get('Labels') or {}
        if not isinstance(labels, dict):
            raise ValueError('Malformed Docker labels')
        service = labels.get('com.docker.compose.service')
        role = services.get(service) if isinstance(service, str) else None
        if role is not None and name in fallbacks and fallbacks[name] != role:
            raise ValueError('Container name conflicts with Compose service role')
        if service is None:
            role = fallbacks.get(name)
        if role is None:
            continue
        state = row.get('State')
        if not isinstance(state, dict) or state.get('Running') is not True:
            continue
        if state.get('Paused', False) is not False or state.get('Restarting', False) is not False:
            raise ValueError('Required container paused or restarting')
        image = config.get('Image')
        if not isinstance(image, str) or not image:
            raise ValueError('Missing container image')
        if role == 'native':
            if EXPECTED_IMAGE_FRAGMENT not in image:
                raise ValueError('Unreviewed Motion image')
            environment = config.get('Env')
            if not isinstance(environment, list) or not all(isinstance(v, str) for v in environment):
                raise ValueError('Cannot verify Motion hardware type')
            hardware = [v.split('=', 1)[1] for v in environment if v.startswith('HW_TYPE=')]
            if hardware != [EXPECTED_HW_TYPE]:
                raise ValueError('Motion hardware type mismatch')
        roles[role].append(name)
    if any(len(names) != 1 for names in roles.values()):
        raise ValueError('Require exactly one running Motion and ROS2 container; '
                         + ', '.join(role+'='+str(len(names)) for role, names in roles.items()))
    return {role: names[0] for role, names in roles.items()}


def parse_controller_response(output):
    if isinstance(output, dict):
        if set(output) != {'controller'}:
            raise ValueError('Malformed controller response')
        rows = output['controller']
    else:
        if not isinstance(output, str) or output.count('Response(controller=') != 1:
            raise ValueError('Missing unique controller response')
        remainder = output.split('Response(controller=', 1)[1].splitlines()
        if not remainder:
            raise ValueError('Malformed controller response')
        literal = remainder[0]
        if not literal.endswith(')'):
            raise ValueError('Malformed controller response')
        try:
            rows = ast.literal_eval(literal[:-1])
        except (ValueError, SyntaxError) as exc:
            raise ValueError('Malformed controller response') from exc
    if not isinstance(rows, list):
        raise ValueError('Invalid controller inventory')
    states = {}
    for row in rows:
        if (not isinstance(row, dict) or not isinstance(row.get('name'), str)
                or not isinstance(row.get('state'), str) or row['name'] in states):
            raise ValueError('Invalid or duplicate controller')
        states[row['name']] = row['state']
    expected = {'manipulation_controller': 'running', 'sdk_controller': 'initialized',
                'vla_sdk_controller': 'initialized'}
    if any(states.get(name) != state for name, state in expected.items()):
        raise ValueError('Controllers do not permit exclusive manipulation')
    return states


def _yaml_lines(output):
    if not isinstance(output, str) or not output.strip() or '\t' in output:
        raise ValueError('Empty or malformed ROS YAML')
    lines = output.strip('\n').splitlines()
    if lines and lines[-1].strip() == '---':
        lines.pop()
    if any(not line.strip() or line.strip() in ('---', '...') for line in lines):
        raise ValueError('Expected exactly one ROS message')
    return lines


def parse_idle_status(output):
    """Require an explicit empty list or only terminal goals, never UNKNOWN."""
    if isinstance(output, dict) or (isinstance(output, str) and output.lstrip().startswith('{')):
        document = _json(output)
        rows = document.get('status_list') if isinstance(document, dict) else None
        if not isinstance(rows, list):
            raise ValueError('Missing action status list')
        if any(not isinstance(row, dict) or type(row.get('status')) is not int for row in rows):
            raise ValueError('Malformed action status')
        statuses = [row['status'] for row in rows]
    else:
        lines = _yaml_lines(output)
        if lines == ['status_list: []']:
            return []
        if lines[0] != 'status_list:' or len(lines) == 1:
            raise ValueError('Missing explicit action status list')
        # ros2 emits an indentless sequence of GoalStatus mappings. Require
        # exactly one integer status at the mapping's own depth per goal.
        entries = []
        for line in lines[1:]:
            if line.startswith('- '):
                entries.append([])
            elif not line.startswith('  '):
                raise ValueError('Malformed action status list')
            if not entries:
                raise ValueError('Malformed action status list')
            entries[-1].append(line)
        statuses = []
        for entry in entries:
            if entry[0] != '- goal_info:':
                raise ValueError('Malformed action goal entry')
            values = [line.removeprefix('  status:').strip() for line in entry
                      if line.startswith('  status:')]
            if len(values) != 1 or not re.fullmatch(r'[0-6]', values[0]):
                raise ValueError('Missing or malformed goal status')
            # Refuse non-YAML noise that might hide a failed query.
            for line in entry[1:]:
                if not re.fullmatch(r'\s+(?:[A-Za-z_][A-Za-z_0-9]*:.*|- \d+)', line):
                    raise ValueError('Malformed action status message')
            statuses.append(int(values[0]))
    if any(status not in (4, 5, 6) for status in statuses):
        raise ValueError('Motion action active or unknown')
    return statuses


def _scalar_zero(output, label):
    if isinstance(output, dict) or (isinstance(output, str) and output.lstrip().startswith('{')):
        document = _json(output)
        value = document.get('data') if isinstance(document, dict) else None
        valid = type(value) is int and value == 0
    else:
        valid = _yaml_lines(output) == ['data: 0']
    if not valid:
        raise ValueError(label + ' not confirmed clear')
    return 0


def parse_health(estop, servo, charger, battery, min_soc=MIN_BATTERY_SOC):
    minimum = _number(min_soc, 'Minimum battery charge')
    if not MIN_BATTERY_SOC <= minimum <= 100:
        raise ValueError('Battery threshold cannot weaken the established minimum')
    values = {'estop': _scalar_zero(estop, 'E-stop'),
              'servo_estop': _scalar_zero(servo, 'Servo E-stop'),
              'charger': _scalar_zero(charger, 'Charger')}
    if isinstance(battery, (dict, list)) or (isinstance(battery, str) and battery.lstrip().startswith(('{', '['))):
        document = _json(battery)
        socs = []
        def collect(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    if key == 'batsoc':
                        socs.append(_number(child, 'Battery charge'))
                    else:
                        collect(child)
            elif isinstance(value, list):
                for child in value:
                    collect(child)
        collect(document)
    else:
        lines = _yaml_lines(battery)
        socs = []
        for line in lines:
            if not re.fullmatch(r'\s*(?:- )?[A-Za-z_][A-Za-z_0-9]*:.*|\s*- \d+', line):
                raise ValueError('Malformed battery message')
            match = re.fullmatch(r'\s*(?:- )?batsoc:\s*(\S+)\s*', line)
            if re.match(r'\s*(?:- )?batsoc:', line):
                if not match or not re.fullmatch(r'\d+(?:\.\d+)?', match[1]):
                    raise ValueError('Malformed battery charge')
                socs.append(float(match[1]))
    if len(socs) != 2 or any(not math.isfinite(soc) or not minimum <= soc <= 100 for soc in socs):
        raise ValueError('Require two valid battery packs above minimum charge')
    values['battery_soc'] = socs
    return values


def validate_actuators(payload, classifier):
    """Reuse the reviewed 20D classifier, including velocity/command gates."""
    document = _json(payload)
    if not isinstance(document, dict):
        raise ValueError('Malformed actuator sample')
    lines = classifier(document, 0.02)
    if not isinstance(lines, list) or any(not isinstance(line, str) or '=' not in line for line in lines):
        raise ValueError('Malformed actuator classification')
    report = dict(line.split('=', 1) for line in lines)
    if len(report) != len(lines) or report.get('ACTUATOR_BODY_COUNT') != '20' or report.get('ACTUATOR_ARM_COUNT') != '14':
        raise ValueError('Incomplete actuator classification')
    return report


def validate_pose_sample(payload, started_at, now, previous_stamp=None):
    """Validate fresh map telemetry without claiming arrival at a target."""
    pose = _json(payload)
    started_at = _number(started_at, 'Read start')
    now = _number(now, 'Read completion')
    if now < started_at:
        raise ValueError('Clock moved backwards during pose read')
    try:
        stamp = pose['header']['stamp']
        sec, ns = stamp['sec'], stamp['nanosec']
        if type(sec) is not int or sec < 0 or type(ns) is not int or not 0 <= ns < 1_000_000_000:
            raise ValueError('Invalid pose timestamp')
        timestamp = _number(sec, 'Pose timestamp') + ns / 1e9
        if not started_at - 0.1 <= timestamp <= now + 0.5 or now - timestamp > 2:
            raise ValueError('Pose stale or clock inconsistent')
        if previous_stamp is not None and timestamp <= _number(previous_stamp, 'Previous timestamp'):
            raise ValueError('Pose timestamp did not advance')
        if pose['header']['frame_id'] != 'map':
            raise ValueError('Pose frame must be map')
        p, q = pose['pose']['position'], pose['pose']['orientation']
        p = {k: _number(p[k], 'Pose position') for k in 'xyz'}
        q = {k: _number(q[k], 'Pose orientation') for k in 'xyzw'}
        norm = math.sqrt(sum(v * v for v in q.values()))
        if abs(norm - 1) > 0.01:
            raise ValueError('Invalid pose quaternion')
        q = {k: v / norm for k, v in q.items()}
        yaw = math.atan2(2 * (q['w'] * q['z'] + q['x'] * q['y']),
                         1 - 2 * (q['y'] ** 2 + q['z'] ** 2))
        return {'stamp': timestamp, 'stamp_ns': sec * 1_000_000_000 + ns,
                'x': p['x'], 'y': p['y'], 'yaw': yaw}
    except (KeyError, TypeError) as exc:
        raise ValueError('Malformed navigation pose') from exc


def validate_nav_pose(payload, expected, started_at, now, previous_stamp=None):
    """Validate one fresh arrival sample; caller requires two advancing samples."""
    measured = validate_pose_sample(payload, started_at, now, previous_stamp)
    try:
        target = {k: _number(expected[k], 'Target pose') for k in ('point_x', 'point_y', 'point_yaw')}
    except (KeyError, TypeError) as exc:
        raise ValueError('Malformed navigation target') from exc
    distance = math.hypot(measured['x'] - target['point_x'], measured['y'] - target['point_y'])
    angle = abs(math.atan2(math.sin(measured['yaw'] - target['point_yaw']),
                           math.cos(measured['yaw'] - target['point_yaw'])))
    if distance > 0.05 or angle > math.radians(3):
        raise ValueError('Arrival outside 0.05m / 3 degree tolerance')
    return {'stamp': measured['stamp'], 'stamp_ns': measured['stamp_ns'],
            'distance_m': distance, 'yaw_error_deg': math.degrees(angle)}


def validate_map_points(response):
    """Preserve current get1/put1 geometry and supported navigation modes."""
    response = _json(response)
    try:
        if type(response.get('code')) is not int or response['code'] != 200:
            raise ValueError('Map request was not successful')
        message = _json(response['message'])
        points = message['umap']['target_points']
        if not isinstance(points, list) or any(not isinstance(point, dict) for point in points):
            raise ValueError('Malformed map points')
        targets = {}
        for name in ('get1', 'put1'):
            matches = [point for point in points if point.get('id') == name]
            if len(matches) != 1:
                raise ValueError('Require one unique ' + name)
            point = matches[0]
            marker = point.get('type') == 'mapping_marker' and point.get('mode') == ''
            if point.get('mode') != 'logo_nav' and not marker:
                raise ValueError('Unsupported waypoint navigation mode')
            expected = {key: _number(point.get(key), 'Waypoint coordinate')
                        for key in ('point_x', 'point_y', 'point_yaw')}
            target = {'map_name': 'utars_nav_map', 'mode': 'logo_nav', 'id': name}
            if marker:
                target = dict(map_name='utars_nav_map', mode='free_nav', level=1, **expected,
                              speed={'linear': {'x': 0.18, 'y': 0.01, 'z': 0.0},
                                     'angular': {'x': 0.0, 'y': 0.0, 'z': 0.20}})
            target['_expected_pose'] = expected
            targets[name] = target
        return targets
    except (AttributeError, KeyError, TypeError) as exc:
        raise ValueError('Malformed map response') from exc
