"""Pure comparison of successive frontal selections; no perception or motion.

These 2 cm / 3 degree thresholds are diagnostic consistency policy, not
certified reach, grasp, collision or physical safety limits. Freshness and
exact-time TF belong to the existing SPS contract upstream. Input positions
are the selected poses in base_link, never camera poses relabeled as base.
"""
import copy
import math


MAX_TRANSLATION_M = 0.02
MAX_ROTATION_DEG = 3.0


def _numeric(value):
    if type(value) not in (int, float):
        raise ValueError('Selection pose contains a nonnumeric value')
    try:
        value = float(value)
    except OverflowError as exc:
        raise ValueError('Selection pose contains a nonfinite value') from exc
    if not math.isfinite(value):
        raise ValueError('Selection pose contains a nonfinite value')
    return value


def _pose(pending):
    try:
        stamp = pending['stamp_ns']
        if type(stamp) is not int or stamp <= 0:
            raise ValueError('Selection requires a positive integer timestamp')
        pose = pending['selection']['selected_pose']
        position = [_numeric(pose['position'][key]) for key in 'xyz']
        quaternion = [_numeric(pose['orientation'][key]) for key in 'xyzw']
    except (TypeError, KeyError) as exc:
        raise ValueError('Malformed selected pose') from exc
    norm = math.hypot(*quaternion)
    if not math.isfinite(norm) or abs(norm - 1.0) > 0.01:
        raise ValueError('Selection requires a unit quaternion')
    return stamp, position, [value / norm for value in quaternion]


def _compare(previous, current):
    previous_stamp, previous_position, previous_quaternion = _pose(previous)
    stamp, position, quaternion = _pose(current)
    if stamp <= previous_stamp:
        raise ValueError('Selection timestamp did not advance')
    translation = math.dist(previous_position, position)
    # q and -q encode the same rotation. The norm of their difference/sum
    # yields the shortest rotational angle without acos precision loss.
    difference = math.dist(previous_quaternion, quaternion)
    total = math.hypot(*(a + b for a, b in zip(previous_quaternion, quaternion)))
    rotation = math.degrees(4.0 * math.atan2(min(difference, total), max(difference, total)))
    if (not math.isfinite(translation) or translation > MAX_TRANSLATION_M + 1e-12
            or rotation > MAX_ROTATION_DEG + 1e-12):
        raise ValueError('Selected pose changed beyond 0.02m / 3 degree consistency policy')
    return dict(previous_stamp_ns=previous_stamp, stamp_ns=stamp,
                translation_m=translation, rotation_deg=rotation,
                max_translation_m=MAX_TRANSLATION_M, max_rotation_deg=MAX_ROTATION_DEG,
                reachability_checked=False)


def validate_pair(previous, current):
    """Check two advancing detections; retain the second original as reference.

    Array indices are not identities. Matching position/orientation establishes
    geometric consistency only; these data cannot prove object identity in a
    scene where a different box occupies the same pose.
    """
    diagnostics = _compare(previous, current)
    diagnostics['reference'] = copy.deepcopy(current)
    return diagnostics


def guard_selection(pending, reference):
    """Check a new grasp selection before delivery, without changing its pose."""
    return _compare(reference, pending)


def stable_report(report, now_ns, original_select_report, capture, clock_ns):
    """Validate two captures at the task's actual perception point.

    Callbacks are supplied by the transient adapter. In particular, ``capture``
    must honor the remaining native result deadline; this helper neither starts
    clients nor extends that deadline. Any callback/validation failure propagates
    before a selection is returned. The original contract verifies each camera
    pose, its freshness and its own exact-time TF independently.
    """
    first = original_select_report(report, now_ns)
    second_report = capture()
    second = original_select_report(second_report, clock_ns())
    comparison = validate_pair(first, second)
    result = copy.deepcopy(second)
    result['stability'] = {key: value for key, value in comparison.items() if key != 'reference'}
    result['previous_detection'] = copy.deepcopy(report)
    return result
