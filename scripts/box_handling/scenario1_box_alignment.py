"""Visual pickup alignment planning; no robot clients or motion authorization.

Observations may be outside the pickup gate, but are never returned to SPS.
Only the chassis X/Y target changes; native pickup keeps its original gate.
"""
import copy
import math
from types import MappingProxyType

if __package__:
    from . import front_sps_contract as sps
    from .probe_front_box import transform_poses, validate_detection
    from .select_front_box import select_front_box
    from .scenario1_perception import validate_pair
    from . import scenario1_resume_worker as base_gate
else:
    import front_sps_contract as sps
    from probe_front_box import transform_poses, validate_detection
    from select_front_box import select_front_box
    from scenario1_perception import validate_pair
    import scenario1_resume_worker as base_gate

POLICY = MappingProxyType(dict(max_corrections=2, max_step_m=.05,
    max_total_m=.05, inside_margin_m=.02, total_budget_s=70., min_improvement_m=.002,
    max_arrival_distance_m=.012, max_arrival_yaw_deg=2.))
HEAD_TASK = 'cruzr/move_head_lower'
HEAD_PATH = '/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/'+HEAD_TASK+'.xml'
HEAD_SHA256 = 'f3a73626f97b471d4a0a03c98c24de32243651116c497328e69b5ddc57ea46c1'


def observe(report, now_ns):
    """Same selector/freshness/exact TF as SPS, without authorizing delivery."""
    poses, stamp = validate_detection(report['vision_result'], report['status'],
                                     now_ns, report['request_ns'])
    tf = report['tf_at_detection']
    if (tf['header']['frame_id'] != 'base_link' or
            tf['child_frame_id'] != poses['header']['frame_id'] or
            tf['header']['stamp'] != poses['header']['stamp']):
        raise ValueError('BOX_ALIGNMENT_EXACT_TF_REQUIRED')
    selected = select_front_box(dict(frame_id='base_link',
        poses=transform_poses(poses['poses'], tf['transform'])))
    pending = dict(stamp_ns=stamp, selection=selected, detection=copy.deepcopy(report))
    # Check complete position/quaternion even when outside the pickup envelope.
    validate_pair(dict(pending, stamp_ns=stamp-1), pending)
    return pending


def displacement(pending):
    """Correct only violated planar axes, aiming 20 mm inside the unchanged gate."""
    position = pending['selection']['selected_pose']['position']
    low, high = sps.POSITION_BOUNDS_M['z']
    if not low <= position['z'] <= high:
        raise ValueError('BOX_ALIGNMENT_Z_UNCORRECTABLE: no planar correction for Z')
    delta = dict(x=0., y=0.)
    for axis in 'xy':
        value = position[axis]
        low, high = sps.POSITION_BOUNDS_M[axis]
        if value < low:
            delta[axis] = value-(low+POLICY['inside_margin_m'])
        elif value > high:
            delta[axis] = value-(high-POLICY['inside_margin_m'])
    if math.hypot(*delta.values()) > POLICY['max_step_m']+1e-12:
        raise ValueError('BOX_ALIGNMENT_OUTSIDE_ENVELOPE: correction exceeds 50 mm')
    return delta


def violation(pending):
    position = pending['selection']['selected_pose']['position']
    return math.hypot(*(max(low-position[axis], 0., position[axis]-high)
                        for axis, (low, high) in sps.POSITION_BOUNDS_M.items()))


def target(reference, delta):
    c, s = math.cos(reference['yaw']), math.sin(reference['yaw'])
    return dict(point_x=reference['x']+c*delta['x']-s*delta['y'],
                point_y=reference['y']+s*delta['x']+c*delta['y'],
                point_yaw=reference['yaw'])


def in_map(pending, reference):
    """Track geometry across chassis motion, rather than comparing base poses."""
    result = copy.deepcopy(pending)
    transform = dict(translation=dict(x=reference['x'], y=reference['y'], z=0.),
        rotation=dict(x=0., y=0., z=math.sin(reference['yaw']/2),
                      w=math.cos(reference['yaw']/2)))
    result['selection']['selected_pose'] = transform_poses(
        [pending['selection']['selected_pose']], transform)[0]
    return result


def validate_arrival(references, expected):
    """Allow native terminal precision before recapturing, never authorize grasp.

    The map correspondence gate is distinct from the unchanged box XYZ gate
    and the navigation guard's 5 mm window for permitting faster final turns.
    """
    if len(references) != 2:
        raise ValueError('BOX_ALIGNMENT_ARRIVAL_REQUIRES_TWO_POSES')
    measurements = []
    for row in references:
        values = [row[key] for key in ('x', 'y', 'yaw')]
        values += [expected[key] for key in ('point_x', 'point_y', 'point_yaw')]
        if any(type(value) not in (int, float) or not math.isfinite(value) for value in values):
            raise ValueError('BOX_ALIGNMENT_INVALID_ARRIVAL_POSE')
        distance = math.hypot(row['x']-expected['point_x'], row['y']-expected['point_y'])
        yaw = abs(math.degrees(math.atan2(math.sin(row['yaw']-expected['point_yaw']),
                                         math.cos(row['yaw']-expected['point_yaw']))))
        measurements.append(dict(distance_m=distance, yaw_error_deg=yaw,
            distance_tolerance_m=POLICY['max_arrival_distance_m'],
            yaw_tolerance_deg=POLICY['max_arrival_yaw_deg']))
    if any(row['distance_m'] > POLICY['max_arrival_distance_m']+1e-12 or
           row['yaw_error_deg'] > POLICY['max_arrival_yaw_deg']+1e-12 for row in measurements):
        raise ValueError('BOX_ALIGNMENT_ARRIVAL_NOT_CONFIRMED: 12 mm / 2 degrees required; '+
                         'measurements='+repr(measurements))
    stable_base(references)
    return measurements


def odom_reference(report):
    """Validate the already-acquired read-only rest gate, including its frame."""
    if (report.get('stationary') is not True or type(report.get('publishers')) is not int or
            report['publishers'] != 1 or len(report.get('samples', [])) != 2):
        raise ValueError('BOX_ALIGNMENT_ODOM_REFERENCE_REQUIRED')
    requested = base_gate.nanoseconds(report['requested_ns'], 'odometry request')
    completed = base_gate.nanoseconds(report['completed_ns'], 'odometry completion')
    if completed < requested:
        raise ValueError('BOX_ALIGNMENT_ODOM_CLOCK_REGRESSION')
    # The worker verified real receipt times/lease. Revalidate source data at
    # its recorded completion; do not invent advancing receipts or reacquire.
    samples = [base_gate.sample(raw, completed) for raw in report['samples']]
    if (not requested < samples[0]['stamp_ns'] < samples[1]['stamp_ns'] <= completed or
            samples[0]['frames'] != samples[1]['frames'] or
            any(completed-sample['stamp_ns'] > base_gate.MAX_AGE_NS or
                sample['linear'] > .003+1e-12 or sample['angular'] > .01+1e-12 for sample in samples)):
        raise ValueError('BOX_ALIGNMENT_ODOM_REFERENCE_REQUIRED')
    if (math.dist(samples[0]['position'], samples[1]['position']) > .005+1e-12 or
            abs(math.atan2(math.sin(samples[1]['yaw']-samples[0]['yaw']),
                           math.cos(samples[1]['yaw']-samples[0]['yaw']))) > math.radians(1)+1e-12):
        raise ValueError('BOX_ALIGNMENT_BASE_UNSTABLE')
    last = samples[-1]
    if (last['frames']['frame_id'] != 'odom' or
            last['frames']['child_frame_id'] not in ('base_link', 'base_footprint')):
        raise ValueError('BOX_ALIGNMENT_ODOM_FRAME_UNSUPPORTED')
    return dict(x=last['position'][0], y=last['position'][1], yaw=last['yaw'],
                stamp_ns=last['stamp_ns'], frames=last['frames'])


def association_observation(first, second, before_report, after_report):
    """Planar odom XY/yaw and stationary base_link Z; comparison geometry only.

    The fixed footprint/base height cancels between observations. These are
    diagnostic coordinates, never a full odom target or a pickup pose.
    """
    validate_pair(first, second)  # same-base diagnostic bounds remain unchanged
    before, after = odom_reference(before_report), odom_reference(after_report)
    if before['frames'] != after['frames']:
        raise ValueError('BOX_ALIGNMENT_ODOM_FRAME_CHANGED')
    if not (before_report['completed_ns'] < first['stamp_ns'] < second['stamp_ns'] <
            after_report['requested_ns']):
        raise ValueError('BOX_ALIGNMENT_ODOM_DOES_NOT_BRACKET_IMAGES')
    stable_base([before, after])
    poses = [pending['selection']['selected_pose'] for pending in (first, second)]
    quaternions = [[pose['orientation'][axis] for axis in 'xyzw'] for pose in poses]
    quaternions = [[v/math.hypot(*q) for v in q] for q in quaternions]
    if sum(a*b for a, b in zip(*quaternions)) < 0:
        quaternions[1] = [-v for v in quaternions[1]]
    qsum = [a+b for a,b in zip(*quaternions)]
    average = dict(stamp_ns=second['stamp_ns'], selection=dict(selected_pose=dict(
        position={axis: sum(pose['position'][axis] for pose in poses)/2 for axis in 'xyz'},
        orientation={axis: v/math.hypot(*qsum) for axis,v in zip('xyzw', qsum)})))
    yaw_delta = math.atan2(math.sin(after['yaw']-before['yaw']), math.cos(after['yaw']-before['yaw']))
    reference = dict(x=(before['x']+after['x'])/2, y=(before['y']+after['y'])/2,
                     yaw=before['yaw']+yaw_delta/2)
    return dict(frames=copy.deepcopy(before['frames']), observation=in_map(average, reference),
                comparison_only=True, reference=reference,
                image_stamps_ns=[first['stamp_ns'], second['stamp_ns']])


def validate_association(anchor, current):
    if not isinstance(anchor, dict) or not isinstance(current, dict):
        raise ValueError('BOX_ALIGNMENT_ASSOCIATION_REQUIRED')
    if anchor['frames'] != current['frames']:
        raise ValueError('BOX_ALIGNMENT_ODOM_FRAME_CHANGED')
    return validate_pair(anchor['observation'], current['observation'])


def stable_base(references):
    first, last = references
    yaw = abs(math.atan2(math.sin(last['yaw']-first['yaw']), math.cos(last['yaw']-first['yaw'])))
    if math.hypot(last['x']-first['x'], last['y']-first['y']) > .005+1e-12 or yaw > math.radians(1)+1e-12:
        raise ValueError('BOX_ALIGNMENT_BASE_UNSTABLE')


def match_pose_time(pending, references):
    """Match the image to two actual map samples collected during perception.

    Their acquisition was validated by the ordinary fresh pose reader. They
    are historical correspondence evidence, never an arrival authorization.
    """
    stamp = pending['stamp_ns']
    if type(stamp) is not int or stamp <= 0:
        raise ValueError('BOX_ALIGNMENT_INVALID_IMAGE_STAMP')
    previous = None
    for row in references:
        source = row['stamp_ns']
        if type(source) is not int or source <= 0 or (previous is not None and source <= previous):
            raise ValueError('BOX_ALIGNMENT_POSE_HISTORY_NONADVANCING')
        previous = source
        # All intermediate positions must stay within the same rest envelope;
        # a departure followed by a return cannot pass using endpoints alone.
        stable_base([references[0], row])
    near = sorted(references, key=lambda row: abs(row['stamp_ns']-stamp))[:2]
    if len(near) != 2 or any(abs(row['stamp_ns']-stamp) > 500_000_000 for row in near):
        delta = min((abs(row['stamp_ns']-stamp) for row in references), default=None)
        raise ValueError('BOX_ALIGNMENT_POSE_TIME_MISMATCH: image_ns=%s closest_delta_ns=%s samples=%s'
                         % (stamp, delta, len(references)))
    return dict(image_stamp_ns=stamp,
                poses=copy.deepcopy(sorted(near, key=lambda row: row['stamp_ns'])),
                max_delta_ns=max(abs(row['stamp_ns']-stamp) for row in near))


def pickup_posture(report, *, observation=True):
    """Require measured arms/torso HOME and the reviewed head observation pose.

    Full health/fault/rest/freshness checks precede this narrower pose check.
    This is not evidence that the grippers are physically empty.
    """
    for sample in report['actuator']:
        for item in sample['act_item']:
            if not observation and item['id'] in (1001, 1002):
                continue
            expected = -.43 if item['id'] == 1002 else 0.
            if item['id'] in (1001, 1002) or item['id'] in (
                    2001, 2002, 2003, 3001, 11001, 11002, 11003, 11004,
                    *range(4001, 4008), *range(5001, 5008)):
                if abs(item['position']-expected) >= .02:
                    raise ValueError('BOX_ALIGNMENT_POSTURE_REQUIRED: arms/torso HOME, head in observation')
