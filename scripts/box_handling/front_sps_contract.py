"""Pure SPS adapter contract; no ROS or movement. One detection, one selection."""
import copy
import math
import time
if __package__:
    from .probe_front_box import transform_poses, validate_detection
    from .select_front_box import select_front_box
else:
    from probe_front_box import transform_poses, validate_detection
    from select_front_box import select_front_box

# Native constructor maps approximate candidates to "select", and the final
# precision pose to "pose" (ELF 0x9adbe..0x9adfc). Do not infer order from names.
DETECTION_ACTION = '/cv/task/sps_select_action'
PRECISE_ACTION = '/cv/task/sps_pose_action'

# Conservative SPS position envelope, in exact-time base_link. Source:
# wrc/separate_right_cruzr.yaml: XYZ [.4,-.4,0]..[.8,.4,1.5]. Motion's
# X_BaseBox differs by millimetres in observed captures; reserve 1 cm on each
# face. This is NOT a calibrated transform error bound or an IK/collision proof.
# Keep it separate from target selection: never substitute another box to pass.
POSITION_GATE_ID = 'front_box_base_link_xyz_10mm_v1'
POSITION_MARGIN_M = 0.01
POSITION_BOUNDS_M = {'x': (0.41, 0.79), 'y': (-0.39, 0.39), 'z': (0.01, 1.49)}


def validate_position(pose):
    """Reject before SPS success, without changing the measured target pose."""
    position = pose.get('position', {})
    for axis, (low, high) in POSITION_BOUNDS_M.items():
        value = position.get(axis)
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError('BOX_POSITION_REJECTED: invalid base_link '+axis)
        if not low <= value <= high:
            raise ValueError(
                'BOX_POSITION_REJECTED: selected box base_link %s=%.4f m outside '
                '[%.2f, %.2f] m (10 mm reserve); no other box substituted'
                % (axis, value, low, high))
    return dict(policy=POSITION_GATE_ID, frame_id='base_link', passed=True,
                bounds_m=copy.deepcopy(POSITION_BOUNDS_M), margin_m=POSITION_MARGIN_M,
                reachability_checked=False)


def wait_terminal_result(results, lock, goal_id, timeout=9.0):
    """Never expose EXECUTING as a GetResult response to the C++ client."""
    deadline = time.monotonic()+timeout
    while time.monotonic() < deadline:
        with lock:
            result = results.get(goal_id)
            if result is not None and result.status in (4, 5, 6):
                return result
        time.sleep(0.005)
    raise TimeoutError('No terminal perception result before deadline')


def validate_goal(goal):
    if goal.get('task_type') != 'SPS':
        raise ValueError('Only SPS is supported')
    inputs = goal.get('sps_inputs', {})
    if inputs.get('object_name') != 'box' or inputs.get('select_id', 0) != 0:
        raise ValueError('Only box/0 is supported; other objects are not redirected')
    if any(inputs.get(k, False) for k in ('need_pcd', 'need_mask', 'tracking_mode')):
        raise ValueError('Point clouds, masks and tracking are unsupported')
    size = inputs.get('box_size', {})
    if any(size.get(k, 0) != 0 for k in 'xyz'):
        raise ValueError('SPS box-size overrides are unsupported')


def select_report(report, now_ns):
    """Recompute selection and return original camera pose, never base pose."""
    poses, stamp_ns = validate_detection(report['vision_result'], report['status'],
                                         now_ns, report['request_ns'])
    tf = report['tf_at_detection']
    if (tf['header']['frame_id'] != 'base_link' or
            tf['child_frame_id'] != poses['header']['frame_id'] or
            tf['header']['stamp'] != poses['header']['stamp']):
        raise ValueError('TF must match the detection frame and exact timestamp')
    candidates = {'frame_id': 'base_link',
                  'poses': transform_poses(poses['poses'], tf['transform'])}
    selected = select_front_box(candidates)
    selected['position_gate'] = validate_position(selected['selected_pose'])
    return dict(camera_pose=copy.deepcopy(poses['poses'][selected['selected_index']]),
                selection=selected, stamp_ns=stamp_ns, detection=copy.deepcopy(report))


class SelectionTransaction:
    """A missing/expired/overlapping transaction latches failure for this session."""
    def __init__(self):
        self.pending = None
        self.failed = False

    def invalidate(self):
        self.pending = None
        self.failed = True

    def detect(self, report, now_ns):
        try:
            if self.failed or self.pending is not None:
                raise ValueError('Session failed or previous selection not consumed')
            self.pending = select_report(report, now_ns)
            return self.result(self.pending)
        except Exception:
            self.invalidate()
            raise

    def select(self, now_ns):
        try:
            if self.failed or self.pending is None:
                raise ValueError('Selection requires a fresh detection in this session')
            pending = self.pending
            if not 0 <= now_ns-pending['stamp_ns'] <= 2_000_000_000:
                raise ValueError('Selected detection has expired')
            self.pending = None
            return self.result(pending), pending
        except Exception:
            self.invalidate()
            raise

    @staticmethod
    def result(pending):
        # Gate BOTH native replies, including final consumption of the pending
        # selection. Recompute from the actual camera pose to be returned;
        # a cached 'passed' flag cannot authorize a different/out-of-range pose.
        report = pending['detection']
        poses = report['vision_result']['trans_outputs']['box_pose']['poses']
        index = pending['selection']['selected_index']
        if pending['camera_pose'] != poses[index]:
            raise ValueError('SPS camera pose no longer matches selected detection')
        base_pose = transform_poses([pending['camera_pose']],
                                    report['tf_at_detection']['transform'])[0]
        if base_pose != pending['selection']['selected_pose']:
            raise ValueError('SPS selected pose no longer matches exact-time TF')
        validate_position(base_pose)
        return {'ok': True, 'sps_outputs': {
            'poses': [copy.deepcopy(pending['camera_pose'])], 'is_empty': False}}
