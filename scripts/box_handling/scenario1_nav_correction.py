"""Bounded GET1 and visual pickup correction checks; no command transport.

These are detection/abort limits, not a proof of physical stopping distance.
Map and odometry are evaluated in their own frames, never subtracted.
"""
import copy
import json
import math
from types import MappingProxyType


POLICY = MappingProxyType({
    'max_corrections': 2,
    'max_initial_distance_m': .05,
    'max_initial_yaw_deg': 5.,
    'action_timeout_s': 30.,
    'total_budget_s': 70.,
    'max_excursion_m': .08,
    'max_path_m': .12,
    'max_worsening_m': .015,
    'max_linear_speed_m_s': .10,
    'max_approach_angular_speed_rad_s': .60,
    'max_angular_speed_rad_s': 1.20,
    'alignment_linear_speed_m_s': .02,
    'max_yaw_excursion_deg': 195.,
    'yaw_excursion_margin_deg': 15.,
    'max_yaw_path_deg': 400.,
    'source_age_s': .5,
    'receive_age_s': .5,
    'no_progress_s': 4.,
    'settle_timeout_s': 1.5,
})
_NS = 1_000_000_000
_EPS = 1e-12


def qualification_report():
    """Operational permission is not a claim of physical qualification.

    The operator authorized wider monitoring limits after the 2026-09-28
    incident. The vendor speed request remains advisory; measured limits and
    terminal arrival checks still decide whether the sequence can continue.
    """
    return {'motion_enabled': True, 'status': 'enabled_for_validation',
            'physical_validation': 'pending',
            'reason_code': 'GET1_CORRECTION_SUPERVISED',
            'reason': 'ajuste nativo supervisado con límites ampliados por autorización del operador',
            'incident': '20260928T112349Z_IMPROVED_SCENARIO1_1010309'}


def require_motion_qualified():
    # Historical API name: permission here does not certify physical behavior.
    report = qualification_report()
    if not report['motion_enabled']:
        raise RuntimeError(report['reason_code'] + ': ' + report['reason'] +
                           '; no se enviará otro objetivo correctivo. Se mantienen 2 cm / 2 grados.')


def _number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(label + ' must be finite numeric')
    return float(value)


def _ns(value, label):
    if type(value) is not int or value <= 0:
        raise ValueError(label + ' must be positive integer nanoseconds')
    return value


def _exact(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(label + ' has unexpected or missing fields')


def _angle(value):
    return math.atan2(math.sin(value), math.cos(value))


def _errors(pose, target):
    return (math.hypot(pose['x'] - target['point_x'], pose['y'] - target['point_y']),
            abs(_angle(pose['yaw'] - target['point_yaw'])))


def _travel_heading_error(pose, target):
    """Differential chassis may reach a nearby point forward or backward."""
    direction = math.atan2(target['point_y'] - pose['y'], target['point_x'] - pose['x'])
    delta = _angle(direction - pose['yaw'])
    return min(abs(delta), abs(_angle(delta + math.pi)))


def distance_tolerance(spec):
    return .005 if spec['point'] == 'box_pickup' else .02


def yaw_limits(spec):
    reference, target = spec['reference'], spec['target']
    distance, final_yaw = _errors(reference, target)
    travel = _travel_heading_error(reference, target) if distance > distance_tolerance(spec) + _EPS else 0.
    # ArcPrecise follows a tangent circle: its ideal heading change to a point
    # at bearing alpha is 2*alpha. Bearing alone would reject a valid arc.
    excursion = min(POLICY['max_yaw_excursion_deg'],
                    max(10., math.degrees(2 * travel + final_yaw) + POLICY['yaw_excursion_margin_deg']))
    return {'excursion_deg': excursion,
            'path_deg': min(POLICY['max_yaw_path_deg'], 2 * excursion + 10.)}


def validate_spec(spec, goal=None):
    """Return a normalized private copy; callers cannot supply looser policy."""
    _exact(spec, ('version', 'point', 'target', 'reference', 'attempt'), 'Correction spec')
    if type(spec['version']) is not int or spec['version'] != 1 or spec['point'] not in ('get1', 'box_pickup'):
        raise ValueError('Correction only supports version 1 / get1 or box_pickup')
    if type(spec['attempt']) is not int or not 1 <= spec['attempt'] <= POLICY['max_corrections']:
        raise ValueError('Correction attempt outside budget')
    _exact(spec['target'], ('point_x', 'point_y', 'point_yaw'), 'Correction target')
    _exact(spec['reference'], ('x', 'y', 'yaw', 'stamp_ns'), 'Correction reference')
    result = copy.deepcopy(spec)
    result['target'] = {key: _number(value, 'Target ' + key) for key, value in spec['target'].items()}
    result['reference'] = {key: (_ns(value, 'Reference stamp') if key == 'stamp_ns'
                                 else _number(value, 'Reference ' + key))
                           for key, value in spec['reference'].items()}
    distance, yaw = _errors(result['reference'], result['target'])
    if distance > POLICY['max_initial_distance_m'] + _EPS or yaw > math.radians(POLICY['max_initial_yaw_deg']) + _EPS:
        raise ValueError('Correction reference outside initial distance/yaw envelope')
    if goal is not None:
        try:
            if not isinstance(goal, dict) or goal['command'] != 'navigation_start':
                raise ValueError('Correction requires navigation_start')
            args = goal['arg_json']
            if isinstance(args, str):
                args = json.loads(args)
            target = args['target_point']
            if target['mode'] != 'free_nav' or target['map_name'] != 'utars_nav_map':
                raise ValueError('Correction requires explicit free_nav target on utars_nav_map')
            for key, expected in result['target'].items():
                if _number(target[key], 'Goal ' + key) != expected:
                    raise ValueError('Correction goal differs from measured target')
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError('Malformed correction navigation goal') from exc
    return result


def make_spec(target, reference, attempt, *, point='get1'):
    return validate_spec({'version': 1, 'point': point, 'target': target,
                          'reference': reference, 'attempt': attempt})


def _sample(kind, payload, received_ns):
    if isinstance(payload, str):
        payload = json.loads(payload)
    try:
        header = payload['header']
        stamp = header['stamp']
        sec, ns = stamp['sec'], stamp['nanosec']
        if type(sec) is not int or sec < 0 or type(ns) is not int or not 0 <= ns < _NS:
            raise ValueError('Invalid telemetry timestamp')
        stamp_ns = _ns(sec * _NS + ns, 'Telemetry stamp')
        frame = header['frame_id']
        if not isinstance(frame, str) or not frame.strip() or frame != frame.strip():
            raise ValueError('Invalid telemetry frame')
        if kind == 'map' and frame != 'map':
            raise ValueError('Correction pose frame must be map')
        pose = payload['pose'] if kind == 'map' else payload['pose']['pose']
        position = {key: _number(pose['position'][key], 'Position') for key in 'xyz'}
        q = {key: _number(pose['orientation'][key], 'Quaternion') for key in 'xyzw'}
        norm = math.sqrt(sum(value * value for value in q.values()))
        if abs(norm - 1.) > .01:
            raise ValueError('Invalid telemetry quaternion')
        q = {key: value / norm for key, value in q.items()}
        yaw = math.atan2(2 * (q['w'] * q['z'] + q['x'] * q['y']),
                         1 - 2 * (q['y'] ** 2 + q['z'] ** 2))
        result = dict(x=position['x'], y=position['y'], yaw=yaw, stamp_ns=stamp_ns,
                      received_ns=received_ns, frame_id=frame)
        if kind == 'odom':
            child = payload['child_frame_id']
            if not isinstance(child, str) or not child.strip() or child != child.strip():
                raise ValueError('Invalid odometry child frame')
            twist = payload['twist']['twist']
            linear = [_number(twist['linear'][key], 'Linear velocity') for key in 'xyz']
            angular = [_number(twist['angular'][key], 'Angular velocity') for key in 'xyz']
            result.update(child_frame_id=child, linear_speed_m_s=math.hypot(*linear),
                          angular_speed_rad_s=math.hypot(*angular))
        return result
    except (KeyError, TypeError) as exc:
        raise ValueError('Malformed ' + kind + ' telemetry') from exc


class Guard:
    """Fail-sticky monitor, armed only after fresh stationary telemetry."""
    def __init__(self, spec, requested_ns):
        self.spec = validate_spec(spec)
        self.distance_tolerance_m = distance_tolerance(self.spec)
        self.requested_ns = _ns(requested_ns, 'Request time')
        if self.spec['reference']['stamp_ns'] > self.requested_ns:
            raise ValueError('Correction reference is from the future')
        self.failure = None
        self.velocity_violation = None
        self.armed_ns = None
        self._clock_ns = self.requested_ns
        self._recent = {'map': [], 'odom': []}
        self._map_history = []
        self._counts = {'map': 0, 'odom': 0}
        self._frames = {}
        self._origins = {}
        self._path = {'map': 0., 'odom': 0.}
        self._excursion = {'map': 0., 'odom': 0.}
        self._yaw_excursion = {'map': 0., 'odom': 0.}
        self._yaw_path = {'map': 0., 'odom': 0.}
        self._yaw_displacement = {'map': 0., 'odom': 0.}
        self._yaw_limits = yaw_limits(self.spec)
        self._max_linear = self._max_angular = 0.
        self._best_distance = _errors(self.spec['reference'], self.spec['target'])[0]
        self._progress = None
        self._progress_ns = None
        self._progress_source = None
        self._pickup_odom_target = None
        self._pickup_odom_progress_m = None
        self._pickup_odom_distance_m = None
        self._pickup_odom_progress_ns = None
        self._pickup_initial_distance_m = None
        self._pickup_recovery_peak_m = None
        self._pickup_recovery_ns = None
        self._heading_progress = None
        self._alignment_started = False
        self._settle_started_ns = None
        self._settled_ns = None

    def _fail(self, message):
        if self.failure is None:
            self.failure = str(message)
        raise ValueError(self.failure)

    def _healthy(self):
        if self.failure is not None:
            raise ValueError(self.failure)

    def _clock(self, now_ns):
        self._healthy()
        try:
            now_ns = _ns(now_ns, 'Clock')
        except ValueError as exc:
            self._fail(exc)
        if now_ns < self._clock_ns:
            self._fail('Correction clock moved backwards')
        self._clock_ns = now_ns
        return now_ns

    def _fresh(self, sample, now_ns):
        for field, limit in (('stamp_ns', POLICY['source_age_s']), ('received_ns', POLICY['receive_age_s'])):
            age = (now_ns - sample[field]) / _NS
            if age < 0 or age > limit:
                self._fail('Correction telemetry stale or future: ' + field)

    def angular_limit(self, sample):
        if self.armed_ns is None:
            return .01
        # The vendor's final turn has a separate 1.1 rad/s command ceiling.
        # Permit its measured margin only at the target, with little translation.
        # DDS streams can arrive in different orders. Later map poses must not
        # authorize a high odometry speed recorded before reaching the point.
        causal = [pose for pose in self._map_history
                  if pose['stamp_ns'] <= sample['stamp_ns']][-2:]
        poses = self._recent['map']
        close = len(poses) == 2 and len(causal) == 2 and all(
            0 <= sample['received_ns'] - pose['stamp_ns'] <= POLICY['source_age_s'] * _NS and
            0 <= sample['received_ns'] - pose['received_ns'] <= POLICY['receive_age_s'] * _NS and
            _errors(pose, self.spec['target'])[0] <= self.distance_tolerance_m + _EPS for pose in poses + causal)
        if close and sample['linear_speed_m_s'] <= POLICY['alignment_linear_speed_m_s'] + _EPS:
            return POLICY['max_angular_speed_rad_s']
        return POLICY['max_approach_angular_speed_rad_s']

    def add(self, kind, payload, received_ns):
        self._healthy()
        try:
            if kind not in self._recent:
                raise ValueError('Unsupported correction telemetry stream')
            received_ns = _ns(received_ns, 'Receipt time')
            sample = _sample(kind, payload, received_ns)
            # A persistent VOLATILE reader can still have a pre-request backlog.
            # Drain it only until this stream provides its first new sample;
            # never count it, adopt its frame, or forgive later regressions.
            if (self.armed_ns is None and not self._recent[kind] and
                    sample['stamp_ns'] <= self.requested_ns and received_ns >= self.requested_ns):
                return
            if sample['stamp_ns'] <= self.requested_ns or received_ns < self.requested_ns:
                raise ValueError('Correction requires telemetry newer than request')
            self._fresh(sample, received_ns)
            recent = self._recent[kind]
            if recent and (sample['stamp_ns'] <= recent[-1]['stamp_ns'] or
                           received_ns <= recent[-1]['received_ns']):
                raise ValueError('Correction telemetry timestamps did not advance')
            frames = (sample['frame_id'], sample.get('child_frame_id'))
            if kind in self._frames and frames != self._frames[kind]:
                raise ValueError('Correction telemetry frame changed')
            self._frames[kind] = frames
            if kind == 'odom':
                linear, angular = sample['linear_speed_m_s'], sample['angular_speed_rad_s']
                self._max_linear, self._max_angular = max(self._max_linear, linear), max(self._max_angular, angular)
                linear_limit = .003 if self.armed_ns is None else POLICY['max_linear_speed_m_s']
                angular_limit = self.angular_limit(sample)
                if linear > linear_limit + _EPS or angular > angular_limit + _EPS:
                    phase = ('preparing' if self.armed_ns is None else
                             'settling' if self._settle_started_ns is not None else 'active')
                    self.velocity_violation = dict(
                        phase=phase, stamp_ns=sample['stamp_ns'], received_ns=received_ns,
                        linear_speed_m_s=linear, linear_limit_m_s=linear_limit,
                        angular_speed_rad_s=angular, angular_limit_rad_s=angular_limit,
                        exceeded=[name for name, value, limit in
                                  (('linear', linear, linear_limit), ('angular', angular, angular_limit))
                                  if value > limit + _EPS],
                        sample=copy.deepcopy(payload if isinstance(payload, dict) else json.loads(payload)))
                    raise ValueError('Correction velocity exceeds %s limit: '
                                     'linear=%.9f m/s (limit=%.9f), '
                                     'angular=%.9f rad/s (limit=%.9f), stamp_ns=%d' %
                                     (phase, linear, linear_limit, angular, angular_limit, sample['stamp_ns']))
            if self.armed_ns is None and kind == 'map':
                reference = self.spec['reference']
                if (math.hypot(sample['x'] - reference['x'], sample['y'] - reference['y']) > .005 + _EPS or
                        abs(_angle(sample['yaw'] - reference['yaw'])) > math.radians(1.) + _EPS):
                    raise ValueError('Correction reference differs from fresh map pose')
                distance, yaw = _errors(sample, self.spec['target'])
                if distance > POLICY['max_initial_distance_m'] + _EPS or yaw > math.radians(POLICY['max_initial_yaw_deg']) + _EPS:
                    raise ValueError('Fresh correction pose outside initial envelope')
            if self.armed_ns is not None:
                origin = self._origins[kind]
                previous = recent[-1]
                self._path[kind] += math.hypot(sample['x'] - previous['x'], sample['y'] - previous['y'])
                self._excursion[kind] = max(self._excursion[kind], math.hypot(sample['x'] - origin['x'], sample['y'] - origin['y']))
                yaw_step = _angle(sample['yaw'] - previous['yaw'])
                self._yaw_displacement[kind] += yaw_step
                self._yaw_excursion[kind] = max(self._yaw_excursion[kind], abs(self._yaw_displacement[kind]))
                self._yaw_path[kind] += abs(yaw_step)
                if self._path[kind] > POLICY['max_path_m'] + _EPS:
                    raise ValueError('Correction path budget exceeded in ' + kind)
                if self._excursion[kind] > POLICY['max_excursion_m'] + _EPS:
                    raise ValueError('Correction excursion budget exceeded in ' + kind)
                if self._yaw_excursion[kind] > math.radians(self._yaw_limits['excursion_deg']) + _EPS:
                    raise ValueError('Correction yaw excursion exceeded in ' + kind)
                if self._yaw_path[kind] > math.radians(self._yaw_limits['path_deg']) + _EPS:
                    raise ValueError('Correction accumulated yaw budget exceeded in ' + kind)
                if kind == 'odom' and self._pickup_odom_target is not None:
                    # Compare within odom against the requested relative offset
                    # anchored at dispatch. A fresh map estimate may lag wheel
                    # odometry. Only new best-distance improvements count: travel,
                    # reversing, oscillations and overshoot do not renew this timer.
                    distance = _errors(sample, self._pickup_odom_target)[0]
                    self._pickup_odom_distance_m = distance
                    if (self._settle_started_ns is None and
                            self._pickup_odom_progress_m - distance >= .002 - _EPS):
                        self._pickup_odom_progress_m = distance
                        self._pickup_odom_progress_ns = received_ns
                        self._progress_ns = received_ns
                        self._progress_source = 'odom_relative_goal'
                if kind == 'map':
                    distance, yaw = _errors(sample, self.spec['target'])
                    if distance > self._best_distance + POLICY['max_worsening_m'] + _EPS:
                        raise ValueError('Correction distance worsened beyond limit')
                    self._best_distance = min(self._best_distance, distance)
                    heading = _travel_heading_error(sample, self.spec['target'])
                    # A short native pickup approach can first move away inside
                    # the existing worsening envelope. Count its measured return
                    # once, before any net positional progress. Repeated retreat /
                    # return cycles cannot keep the watchdog alive. GET1 retains
                    # its previous best-distance rule and all limits stay active.
                    initial_recovery = (self.spec['point'] == 'box_pickup' and
                                        not self._alignment_started and
                                        self._pickup_recovery_ns is None and
                                        self._progress[0] >= self._pickup_initial_distance_m - _EPS)
                    if initial_recovery:
                        self._pickup_recovery_peak_m = max(self._pickup_recovery_peak_m, distance)
                    recovery_progress = (initial_recovery and
                                         self._pickup_recovery_peak_m - self._pickup_initial_distance_m >= .002 - _EPS and
                                         self._pickup_recovery_peak_m - distance >= .002 - _EPS)
                    if distance <= self.distance_tolerance_m + _EPS and not self._alignment_started:
                        # Enter final orientation once; repeated threshold crossings
                        # must not renew the no-progress watchdog indefinitely.
                        self._alignment_started = True
                        self._progress = (min(self._progress[0], distance), yaw)
                        self._progress_ns = received_ns
                        self._progress_source = 'map'
                    positional_progress = self._progress[0] - distance >= .002 - _EPS
                    final_progress = (distance <= self.distance_tolerance_m + _EPS and
                                      self._progress[1] - yaw >= math.radians(.2) - _EPS)
                    heading_progress = (distance > self.distance_tolerance_m + _EPS and not self._alignment_started and
                                        self._heading_progress - heading >= math.radians(.2) - _EPS)
                    if positional_progress or final_progress or heading_progress or recovery_progress:
                        # ArcPrecise may still turn away from final yaw while
                        # closing in. Each genuine 2 mm position improvement
                        # reanchors final yaw, so the following return turn need
                        # not first beat a minimum measured halfway through the arc.
                        self._progress = (min(self._progress[0], distance),
                                          yaw if positional_progress else min(self._progress[1], yaw))
                        self._heading_progress = heading if positional_progress else min(self._heading_progress, heading)
                        self._progress_ns = received_ns
                        self._progress_source = 'map'
                        if recovery_progress:
                            self._pickup_recovery_ns = received_ns
            recent.append(sample)
            del recent[:-2]
            if kind == 'map':
                self._map_history.append(sample)
                del self._map_history[:-128]
            self._counts[kind] += 1
            if self._settle_started_ns is not None:
                self._settled_ns = None
        except (ValueError, TypeError, OverflowError) as exc:
            self._fail(exc)

    def ready(self, now_ns):
        now_ns = self._clock(now_ns)
        for recent in self._recent.values():
            for sample in recent:
                self._fresh(sample, now_ns)
        return all(len(recent) >= 2 for recent in self._recent.values())

    def arm(self, now_ns):
        if self.armed_ns is not None:
            self._fail('Correction guard already armed')
        if not self.ready(now_ns):
            self._fail('Correction needs two fresh samples per stream before dispatch')
        self.armed_ns = now_ns
        self._origins = {kind: dict(recent[-1]) for kind, recent in self._recent.items()}
        self._progress = _errors(self._origins['map'], self.spec['target'])
        self._heading_progress = _travel_heading_error(self._origins['map'], self.spec['target'])
        self._alignment_started = self._progress[0] <= self.distance_tolerance_m + _EPS
        self._best_distance = min(self._best_distance, self._progress[0])
        self._progress_ns = now_ns
        self._progress_source = 'map'
        self._pickup_initial_distance_m = self._progress[0]
        self._pickup_recovery_peak_m = self._progress[0]
        if (self.spec['point'] == 'box_pickup' and
                self._frames['odom'] in (('odom', 'base_link'), ('odom', 'base_footprint'))):
            # Two fresh stationary streams establish the same starting chassis
            # posture. Express its map-goal offset in the local odometry axes;
            # never subtract map and odom positions or publish this as a TF/goal.
            mapped, odom = self._origins['map'], self._origins['odom']
            angle = odom['yaw'] - mapped['yaw']
            dx = self.spec['target']['point_x'] - mapped['x']
            dy = self.spec['target']['point_y'] - mapped['y']
            self._pickup_odom_target = dict(
                point_x=odom['x'] + math.cos(angle)*dx - math.sin(angle)*dy,
                point_y=odom['y'] + math.sin(angle)*dx + math.cos(angle)*dy,
                point_yaw=_angle(odom['yaw'] + self.spec['target']['point_yaw'] - mapped['yaw']))
            self._pickup_odom_progress_m = _errors(odom, self._pickup_odom_target)[0]
            self._pickup_odom_distance_m = self._pickup_odom_progress_m

    def check(self, now_ns):
        now_ns = self._clock(now_ns)
        if self.armed_ns is None:
            self._fail('Correction guard has not been armed')
        if (now_ns - self.armed_ns) / _NS > POLICY['action_timeout_s']:
            self._fail('Correction action time budget exceeded')
        if (self._settle_started_ns is not None and
                (now_ns - self._settle_started_ns) / _NS > POLICY['settle_timeout_s']):
            self._fail('Correction terminal settling time budget exceeded')
        for recent in self._recent.values():
            self._fresh(recent[-1], now_ns)
        distance, yaw = _errors(self._recent['map'][-1], self.spec['target'])
        if ((distance > self.distance_tolerance_m + _EPS or yaw > math.radians(2.) + _EPS) and
                (now_ns - self._progress_ns) / _NS >= POLICY['no_progress_s']):
            self._fail('Correction made no significant progress')
        return self.summary()

    def begin_settle(self, now_ns):
        """Start post-result observation without resetting any active limit."""
        self.check(now_ns)
        if self._settle_started_ns is not None:
            self._fail('Correction terminal settling already started')
        self._settle_started_ns = now_ns
        self._settled_ns = None

    def settled(self, now_ns):
        """Require two new stationary odometry and stable map samples.

        A terminal action result alone does not establish that the chassis has
        stopped. Brief deceleration within the active limits is allowed, while
        source freshness, motion budgets and the existing deadline remain live.
        """
        self.check(now_ns)
        if self._settle_started_ns is None:
            self._fail('Correction terminal settling has not started')
        self._settled_ns = None
        for recent in self._recent.values():
            if len(recent) < 2 or any(sample['stamp_ns'] <= self._settle_started_ns or
                                      sample['received_ns'] <= self._settle_started_ns
                                      for sample in recent):
                return False
            for sample in recent:
                self._fresh(sample, now_ns)
        if any(sample['linear_speed_m_s'] > .003 + _EPS or
               sample['angular_speed_rad_s'] > .01 + _EPS for sample in self._recent['odom']):
            return False
        first, second = self._recent['map']
        if (math.hypot(first['x'] - second['x'], first['y'] - second['y']) > .005 + _EPS or
                abs(_angle(first['yaw'] - second['yaw'])) > math.radians(1.) + _EPS):
            return False
        self._settled_ns = now_ns
        return True

    def summary(self):
        latest = self._recent['map'][-1] if self._recent['map'] else self.spec['reference']
        distance, yaw = _errors(latest, self.spec['target'])
        return {'version': 1, 'point': self.spec['point'], 'attempt': self.spec['attempt'],
                'armed': self.armed_ns is not None, 'failure': self.failure,
                'velocity_violation': copy.deepcopy(self.velocity_violation),
                'requested_ns': self.requested_ns, 'armed_ns': self.armed_ns,
                'settle_started_ns': self._settle_started_ns,
                'settled_ns': self._settled_ns, 'settled': self._settled_ns is not None,
                'samples': dict(self._counts),
                'frames': {kind: {'frame_id': frames[0], 'child_frame_id': frames[1]}
                           for kind, frames in self._frames.items()},
                'last_stamp_ns': {kind: recent[-1]['stamp_ns'] if recent else None
                                  for kind, recent in self._recent.items()},
                'last_pose': {kind: {key: recent[-1][key] for key in ('x', 'y', 'yaw', 'stamp_ns', 'received_ns')}
                              if recent else None for kind, recent in self._recent.items()},
                'path_m': dict(self._path), 'max_excursion_m': dict(self._excursion),
                'max_yaw_excursion_deg': {kind: math.degrees(value) for kind, value in self._yaw_excursion.items()},
                'yaw_path_deg': {kind: math.degrees(value) for kind, value in self._yaw_path.items()},
                'yaw_limits': dict(self._yaw_limits),
                'progress_phase': 'final_alignment' if self._alignment_started else 'approach',
                'progress_ns': self._progress_ns,
                'progress_source': self._progress_source,
                'progress_distance_m': self._progress[0] if self._progress else None,
                'pickup_odometry': {'target': copy.deepcopy(self._pickup_odom_target),
                                    'distance_m': self._pickup_odom_distance_m,
                                    'progress_distance_m': self._pickup_odom_progress_m,
                                    'progress_ns': self._pickup_odom_progress_ns,
                                    'arrival_authorized': False},
                'pickup_recovery': {'initial_distance_m': self._pickup_initial_distance_m,
                                    'peak_distance_m': self._pickup_recovery_peak_m,
                                    'used_ns': self._pickup_recovery_ns},
                'max_linear_speed_m_s': self._max_linear, 'max_angular_speed_rad_s': self._max_angular,
                'distance_m': distance, 'yaw_error_deg': math.degrees(yaw),
                'distance_tolerance_m': self.distance_tolerance_m,
                'policy': dict(POLICY), 'arrival_verified': False}
