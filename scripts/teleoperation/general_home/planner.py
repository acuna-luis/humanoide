"""Deterministic RRT-Connect with conservative segment certificates and retiming.

No XML, ROS, SSH or execution API. A geometric candidate is never an execution
permit; timing is an explicit mathematical law with provisional design caps.
"""
from __future__ import annotations

from collections import OrderedDict
import math
import time

import numpy as np

from .geometry import finite_vector


class BudgetExceeded(Exception):
    pass


class Validator:
    def __init__(self, geometry, clearance=.002, max_depth=16, deadline=None, extra_margin=None):
        if not math.isfinite(clearance) or clearance < 0 or not 1 <= max_depth <= 24:
            raise ValueError('Invalid clearance or subdivision depth')
        self.geometry = geometry
        self.margin = np.full(len(geometry.labels), clearance)
        if extra_margin is not None:
            extra_margin = np.asarray(extra_margin)
            if extra_margin.shape != self.margin.shape or not np.isfinite(extra_margin).all() or (extra_margin < 0).any():
                raise ValueError('Invalid pair error margins')
            self.margin += extra_margin
        self.max_depth = max_depth
        self.deadline = deadline
        self.cache = OrderedDict()
        self.state_queries = 0
        self.edge_queries = 0
        self.unresolved_edges = 0
        self.independent_progress_queries = 0
        self.minimum_certified_slack_m = math.inf

    def tick(self):
        if self.deadline is not None and time.monotonic() >= self.deadline:
            raise BudgetExceeded()

    def distances(self, q):
        self.tick()
        q = finite_vector(q, len(self.geometry.lower), 'state')
        if (q < self.geometry.lower).any() or (q > self.geometry.upper).any():
            raise ValueError('State outside limits')
        key = q.tobytes()
        if key not in self.cache:
            distance = self.geometry.distances(q)
            if distance.shape != self.margin.shape or not np.isfinite(distance).all():
                raise ValueError('Invalid distance result')
            self.cache[key] = distance
            self.state_queries += 1
            if len(self.cache) > 4096:
                self.cache.popitem(last=False)
        return self.cache[key]

    def state(self, q):
        q = finite_vector(q, len(self.geometry.lower), 'state')
        if (q < self.geometry.lower).any() or (q > self.geometry.upper).any():
            return False
        return bool((self.distances(q) > self.margin+1e-9).all())

    def failures(self, q):
        distance = self.distances(q)
        details = getattr(self.geometry, 'pair_details', [{} for _ in self.geometry.labels])
        return [dict(pair=pair, separation_lower_bound_m=float(value),
                     required_margin_m=float(margin), **detail)
                for pair, value, margin, detail in zip(self.geometry.labels, distance, self.margin, details)
                if value <= margin+1e-9]

    def edge(self, a, b):
        """Prove the affine joint-space segment, not merely sampled endpoints.

        At a midpoint, each shape can move at most sum(radius_j*|delta_j|/2).
        Common ancestors cancel in the pair weights. If the distance exceeds
        that travel plus margin, the entire interval is separated. Otherwise
        subdivide; an exhausted resolution is a rejection, never a pass.
        """
        self.edge_queries += 1
        a, b = np.asarray(a), np.asarray(b)
        if not self.state(a) or not self.state(b):
            return False
        pending = [(a, b, 0)]
        while pending:
            self.tick()
            lo, hi, depth = pending.pop()
            mid = (lo+hi)/2
            distances = self.distances(mid)
            if (distances <= self.margin+1e-9).any():
                return False
            travel = self.geometry.weights @ (abs(hi-lo)/2)
            slack = distances-self.margin-travel
            if (slack > 1e-9).all():
                if len(slack):
                    self.minimum_certified_slack_m = min(self.minimum_certified_slack_m, float(slack.min()))
                continue
            if depth >= self.max_depth:
                self.unresolved_edges += 1
                return False
            pending.extend(((lo, mid, depth+1), (mid, hi, depth+1)))
        return True

    def independent_progress(self, a, b):
        """Certify the entire joint box, including arbitrary inter-axis lag.

        Each joint may be anywhere between its endpoints independently. This
        covers all bounded progress, including reversals/stalls inside the box;
        overshoot, tracking error and stopping travel require added margins.
        Unlike edge(), subdivisions partition the box along ONE axis at a time.
        No common start time, progress parameter or duration is assumed.
        """
        self.independent_progress_queries += 1
        a = finite_vector(a, len(self.geometry.lower), 'start')
        b = finite_vector(b, len(self.geometry.lower), 'end')
        if not self.state(a) or not self.state(b):
            return False
        pending = [(np.minimum(a,b), np.maximum(a,b), 0)]
        while pending:
            self.tick()
            lo, hi, depth = pending.pop()
            mid = (lo+hi)/2
            distances = self.distances(mid)
            if (distances <= self.margin+1e-9).any():
                return False
            radii = (hi-lo)/2
            travel = self.geometry.weights @ radii
            slack = distances-self.margin-travel
            uncertain = slack <= 1e-9
            if not uncertain.any():
                if len(slack):
                    self.minimum_certified_slack_m = min(self.minimum_certified_slack_m, float(slack.min()))
                continue
            if depth >= self.max_depth:
                self.unresolved_edges += 1
                return False
            # Split the coordinate contributing most to unproved pairs. This
            # only changes performance; every child keeps its full box bound.
            scores = np.max(self.geometry.weights[uncertain]*radii, axis=0)
            axis = int(np.argmax(scores))
            if scores[axis] <= 0:
                self.unresolved_edges += 1
                return False
            left_hi = hi.copy(); left_hi[axis] = mid[axis]
            right_lo = lo.copy(); right_lo[axis] = mid[axis]
            pending.extend(((lo,left_hi,depth+1), (right_lo,hi,depth+1)))
        return True


def segment_seconds(a, b, caps=(.3, .35, 1.5), law='quintic'):
    if law not in ('quintic', 'cubic-rest'):
        raise ValueError('Unknown timing law')
    if len(caps) != 3 or any(not math.isfinite(v) or v <= 0 for v in caps):
        raise ValueError('Positive velocity/acceleration/jerk caps required')
    delta = float(abs(np.asarray(b)-a).max())
    if delta == 0:
        return 0.0
    if law == 'cubic-rest':
        # Native rest-to-rest cubic has acceleration jumps at rest boundaries;
        # no finite global jerk bound can be claimed by increasing duration.
        return math.ceil(max(1., 1.5*delta/caps[0], math.sqrt(6*delta/caps[1]))*1000)/1000
    return math.ceil(max(1., 1.875*delta/caps[0],
                         math.sqrt(10/math.sqrt(3)*delta/caps[1]),
                         (60*delta/caps[2])**(1/3))*1000)/1000


def retime(path, law='quintic'):
    result = []
    for a, b in zip(path, path[1:]):
        seconds = segment_seconds(a, b, law=law)
        if not seconds:
            continue
        delta = abs(np.asarray(b)-a)
        step = dict(start_rad=list(map(float, a)), end_rad=list(map(float, b)), seconds=seconds,
            peak_velocity_rad_s=(1.875*delta/seconds).tolist(),
            peak_acceleration_rad_s2=(10/math.sqrt(3)*delta/seconds**2).tolist(),
            peak_jerk_rad_s3=(60*delta/seconds**3).tolist(), timing_law=law)
        if law == 'cubic-rest':
            step.update(peak_velocity_rad_s=(1.5*delta/seconds).tolist(),
                peak_acceleration_rad_s2=(6*delta/seconds**2).tolist(),
                peak_jerk_rad_s3=None, jerk_bound_including_waypoints=False,
                interior_jerk_rad_s3=(12*delta/seconds**3).tolist())
        result.append(step)
    return result


def route_cost(path, law='quintic'):
    return sum(segment_seconds(a, b, law=law) for a, b in zip(path, path[1:]))


def corridor_candidates(start, goal):
    yield 'direct', [start, goal]
    if len(start) != 20:
        return
    # Heuristics only: every state/edge must pass the same full collision test.
    # Preserve initial elbow/wrist/body angles instead of copying PICO.
    for opening in (-.35, -.5, -.65):
        opened = start.copy()
        opened[[3, 10]] = np.minimum(opened[[3, 10]], opening)
        down = opened.copy()
        down[:14] = 0
        down[[3, 10]] = opened[[3, 10]]
        body = down.copy()
        body[14:] = goal[14:]
        yield f'both_open_{opening}', [start, opened, down, body, goal]
        for first in (slice(0, 7), slice(7, 14)):
            one = opened.copy()
            one[first] = down[first]
            yield f'sequential_{first.start}_{opening}', [start, opened, one, down, body, goal]


def shortcut(path, validator, law='quintic'):
    path = [q.copy() for q in path]
    # Remove the most expensive detours first. Every shortcut is rechecked.
    for span in range(len(path)-1, 1, -1):
        index = 0
        while index+span < len(path):
            validator.tick()
            old = path[index:index+span+1]
            if (segment_seconds(old[0], old[-1], law=law) < route_cost(old, law)
                    and validator.edge(old[0], old[-1])):
                path[index+1:index+span] = []
            index += 1
    return path


def rrt_connect(start, goal, validator, rng, max_iterations=1500, step=.25):
    """Two trees; each edge is certified before inserting it into either tree."""
    if max_iterations < 1 or not math.isfinite(step) or step <= 0:
        raise ValueError('Invalid search budget/step')
    trees = [([start.copy()], [-1]), ([goal.copy()], [-1])]
    lower, upper = validator.geometry.lower, validator.geometry.upper
    scale = np.maximum(upper-lower, 1e-6)

    def extend(tree, target):
        nodes, parents = tree
        nearest = int(np.argmin(np.linalg.norm((np.array(nodes)-target)/scale, axis=1)))
        delta = target-nodes[nearest]
        norm = float(np.linalg.norm(delta))
        if norm < 1e-12:
            return nearest, True
        q = nodes[nearest]+delta*min(1., step/norm)
        if not validator.edge(nodes[nearest], q):
            return None, False
        nodes.append(q)
        parents.append(nearest)
        return len(nodes)-1, norm <= step

    def trace(tree, index):
        result = []
        while index >= 0:
            result.append(tree[0][index])
            index = tree[1][index]
        return result[::-1]

    for iteration in range(max_iterations):
        validator.tick()
        active = iteration % 2
        a, b = trees[active], trees[1-active]
        # Goal bias uses the other tree; uniform samples cover the full domain.
        target = b[0][0] if rng.random() < .15 else rng.uniform(lower, upper)
        index, _ = extend(a, target)
        if index is None:
            continue
        for _ in range(128):
            other, reached = extend(b, a[0][index])
            if other is None:
                break
            if reached:
                first, second = trace(a, index), trace(b, other)
                result = first+second[-2::-1]
                return result if active == 0 else result[::-1]
    return None


def plan(geometry, start, *, timeout=30., seed=20260910, clearance=.002, max_iterations=1500, timing_law='quintic'):
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('Timeout must be positive')
    start = finite_vector(start, len(geometry.lower), 'start')
    segment_seconds(start, start, law=timing_law)  # Validate even if endpoints reject.
    goal = np.zeros_like(start)
    result = dict(schema='cruzr-general-home-plan-v1', physical_approval=False,
        installable=False, movement_commands=0, seed=seed,
        curve='one common monotonic quintic per segment; zero velocity/acceleration at waypoints',
        design_caps=dict(velocity_rad_s=.3, acceleration_rad_s2=.35, jerk_rad_s3=1.5),
        clearance_m=clearance, steps=[], nominal_seconds=None)
    result['timing_law'] = timing_law
    if timing_law == 'cubic-rest':
        result.update(curve='one common monotonic cubic s=3u^2-2u^3 per segment; zero endpoint velocity, acceleration jumps at rest',
                      design_caps=dict(velocity_rad_s=.3, acceleration_rad_s2=.35, jerk_rad_s3=None),
                      native_math_only=True, native_group_execution_verified=False)
    validator = Validator(geometry, clearance, deadline=time.monotonic()+timeout)
    began = time.monotonic()
    try:
        for name, q in [('START', start), ('HOME', goal)]:
            if (q < geometry.lower).any() or (q > geometry.upper).any():
                result.update(status=name+'_OUTSIDE_LIMITS')
                return result
            if not validator.state(q):
                result.update(status=name+'_GEOMETRY_REJECTED', conflicts=validator.failures(q))
                return result
        if np.array_equal(start, goal):
            result.update(status='ALREADY_HOME_NUMERIC', nominal_seconds=0., waypoints_rad=[start.tolist()])
            return result
        candidates = []
        for label, path in corridor_candidates(start, goal):
            validator.tick()
            if all(validator.edge(a, b) for a, b in zip(path, path[1:])):
                candidates.append((route_cost(path, timing_law), label, path))
                if label == 'direct':
                    break
        if candidates:
            _, label, path = min(candidates, key=lambda item: item[0])
        else:
            label = 'rrt_connect'
            path = rrt_connect(start, goal, validator, np.random.default_rng(seed), max_iterations)
        if path is None:
            result.update(status='SEARCH_EXHAUSTED', reason='No verified route found within this search; not proof of impossibility')
            return result
        path = shortcut(path, validator, timing_law)
        # Retiming preserves this exact affine geometric segment, synchronously
        # for every joint. No independent component interpolation is assumed.
        if not all(validator.edge(a, b) for a, b in zip(path, path[1:])):
            result.update(status='FINAL_CURVE_REJECTED')
            return result
        steps = retime(path, timing_law)
        result.update(status='GEOMETRIC_CANDIDATE', method=label, steps=steps,
                      waypoints_rad=[q.tolist() for q in path],
                      nominal_seconds=sum(s['seconds'] for s in steps))
        return result
    except BudgetExceeded:
        result.update(status='SEARCH_TIMEOUT', reason='Budget expired; no executable result')
        return result
    finally:
        result['planning_seconds'] = time.monotonic()-began
        result['verification'] = dict(state_queries=validator.state_queries,
            edge_queries=validator.edge_queries, unresolved_edges=validator.unresolved_edges,
            method='midpoint distance lower bounds minus per-pair joint travel; adaptive subdivision',
            minimum_certified_slack_m=validator.minimum_certified_slack_m
                if math.isfinite(validator.minimum_certified_slack_m) else None)
