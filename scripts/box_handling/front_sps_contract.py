"""Pure SPS adapter contract; no ROS or movement. One detection, one selection."""
import copy
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
        return {'ok': True, 'sps_outputs': {
            'poses': [copy.deepcopy(pending['camera_pose'])], 'is_empty': False}}
