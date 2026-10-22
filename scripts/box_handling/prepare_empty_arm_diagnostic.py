#!/usr/bin/env python3
"""Prepare a small empty-arm SDK candidate locally. Never connects or executes.

The selected arm follows a scaled version of its native preparation vector,
relative to a complete measured HOME reference, then returns to that reference.
This does not reproduce the full preparation, box contact, grasp or IK solver.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


DURATION_S = 22
FREQUENCY_HZ = 500
MAX_AMPLITUDE_DEG = 2.
RAMP_S = 8.
JOINT_SUFFIXES = ('shoulder_pitch', 'shoulder_roll', 'shoulder_yaw', 'elbow_roll',
                  'elbow_yaw', 'wrist_pitch', 'wrist_roll')
JOINTS = {
    'head': ('head_yaw_joint', 'head_pitch_joint'),
    'left_arm': tuple('L_'+name+'_joint' for name in JOINT_SUFFIXES),
    'right_arm': tuple('R_'+name+'_joint' for name in JOINT_SUFFIXES),
    'lifter': ('lifter_pitch_1_joint', 'lifter_pitch_2_joint', 'lifter_pitch_3_joint'),
    'waist': ('waist_yaw_joint',),
}
NATIVE_PREPARATION = {
    'right': (.315, -.484, 1.910, -1.503, .697, .362, .142),
    'left': (-.315, -.484, -1.910, -1.503, -.697, -.362, .142),
}
REQUIRED_JOINTS = tuple(name for group in JOINTS.values() for name in group)


def finite_number(value, label):
    if type(value) not in (int, float):
        raise ValueError(label+' must be finite numeric')
    try:
        number = float(value)
    except OverflowError as error:
        raise ValueError(label+' must be finite numeric') from error
    if not math.isfinite(number):
        raise ValueError(label+' must be finite numeric')
    return number


def json_object(raw):
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key: '+key)
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=unique_pairs)
    if not isinstance(value, dict):
        raise ValueError('Expected a canonical JointState JSON object')
    json.dumps(value, allow_nan=False)
    return value


def canonical_state(sample):
    """Require all 20 named body axes; extra axes are recorded, never commanded."""
    if not isinstance(sample, dict):
        raise ValueError('Expected canonical JointState object')
    try:
        names, positions, velocities = (sample[key] for key in ('name', 'position', 'velocity'))
        if (any(type(values) is not list for values in (names, positions, velocities)) or
                len(names) != len(positions) or len(names) != len(velocities)):
            raise ValueError('Canonical names/positions/velocities must have matching lengths')
        if any(type(name) is not str or not name or name != name.strip() for name in names) or len(set(names)) != len(names):
            raise ValueError('Canonical names must be unique nonempty strings')
        if set(REQUIRED_JOINTS)-set(names):
            raise ValueError('Missing canonical 20D joint; zero filling is forbidden')
        positions = [finite_number(value, 'Position') for value in positions]
        velocities = [finite_number(value, 'Velocity') for value in velocities]
        if 'effort' in sample:
            effort = sample['effort']
            if type(effort) is not list or len(effort) not in (0, len(names)):
                raise ValueError('Canonical effort must be empty or match names')
            for value in effort:
                finite_number(value, 'Effort')
        stamp = sample['header']['stamp']
        sec, ns = stamp['sec'], stamp['nanosec']
        if type(sec) is not int or sec < 0 or type(ns) is not int or not 0 <= ns < 10**9 or sec*10**9+ns <= 0:
            raise ValueError('Invalid canonical source timestamp')
    except (KeyError, TypeError) as error:
        raise ValueError('Incomplete canonical JointState') from error
    values = dict(zip(names, positions))
    if max(abs(values[name]) for name in REQUIRED_JOINTS) >= .02:
        raise ValueError('Measured 20D source is outside HOME |q| < 0.02 rad')
    if any(abs(value) >= .002 for value in velocities):
        raise ValueError('Measured source is not at rest |velocity| < 0.002 rad/s')
    return values


def quintic(u):
    return u*u*u*(10+u*(-15+6*u))


def envelope(t):
    if t <= 2:
        return 0.
    if t < 10:
        return quintic((t-2)/RAMP_S)
    if t <= 12:
        return 1.
    if t < 20:
        return 1.-quintic((t-12)/RAMP_S)
    return 0.


def check_urdf(urdf_text, initial, peak, offsets):
    """Check named URDF position/velocity limits, never collision or live limits."""
    root = ET.fromstring(urdf_text)
    if root.tag != 'robot':
        raise ValueError('Expected URDF robot root')
    joints = root.findall('joint')
    names = [joint.get('name') for joint in joints]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate URDF joint names')
    by_name = dict(zip(names, joints))
    result = {}
    for name in REQUIRED_JOINTS:
        joint = by_name.get(name)
        # The native manipulation URDF can omit both head axes. They must
        # remain exactly fixed; record the absent coverage rather than invent
        # limits or use another model. Every arm/torso axis is still required.
        if joint is None and name in JOINTS['head'] and not offsets.get(name, 0.) and peak[name] == initial[name]:
            continue
        if joint is None or joint.get('type') != 'revolute':
            raise ValueError('URDF must contain bounded revolute '+name)
        limit = joint.find('limit')
        if limit is None:
            raise ValueError('Missing URDF limit '+name)
        try:
            low, high, velocity = (finite_number(float(limit.attrib[key]), 'URDF '+key) for key in ('lower', 'upper', 'velocity'))
        except (KeyError, TypeError) as error:
            raise ValueError('Incomplete URDF limit '+name) from error
        if low >= high or velocity <= 0:
            raise ValueError('Invalid URDF limits '+name)
        if any(not low <= value <= high for value in (initial[name], peak[name])):
            raise ValueError('URDF position limit violation '+name)
        maximum_velocity = 1.875*abs(offsets.get(name, 0.))/RAMP_S
        if maximum_velocity > velocity:
            raise ValueError('URDF velocity limit violation '+name)
        result[name] = dict(lower_rad=low, upper_rad=high, velocity_limit_rad_s=velocity,
                           requested_max_velocity_rad_s=maximum_velocity)
    return result


def prepare(sample, arm, amplitude_deg=MAX_AMPLITUDE_DEG, *, urdf_text=None):
    """Return motion and review dictionaries without files, ROS or SDK imports."""
    initial = canonical_state(sample)
    if arm not in NATIVE_PREPARATION:
        raise ValueError('Arm must be right or left')
    amplitude = finite_number(amplitude_deg, 'Amplitude degrees')
    if not 0 < amplitude <= MAX_AMPLITUDE_DEG:
        raise ValueError('Amplitude must be in (0, 2] degrees')
    native_vector = NATIVE_PREPARATION[arm]
    scale = math.radians(amplitude)/max(abs(value) for value in native_vector)
    moving_group = arm+'_arm'
    offsets = {name: scale*value for name, value in zip(JOINTS[moving_group], native_vector)}
    peak = {name: initial[name]+offsets.get(name, 0.) for name in REQUIRED_JOINTS}
    if any(peak[name] == initial[name] for name in offsets):
        raise ValueError('Amplitude is below numeric resolution for a selected arm axis')
    urdf_limits = check_urdf(urdf_text, initial, peak, offsets) if urdf_text is not None else None
    count = DURATION_S*FREQUENCY_HZ+1
    motion = dict(robot='Utars', source='utars_teleop')
    largest_step = 0.
    for group, names in JOINTS.items():
        rows, previous = [], None
        for index in range(count):
            t = index/FREQUENCY_HZ
            factor = envelope(t)
            q = [initial[name] if factor == 0. or name not in offsets else
                 initial[name]+offsets[name]*factor for name in names]
            if previous is not None:
                largest_step = max(largest_step, *(abs(a-b) for a, b in zip(previous, q)))
            rows.append(dict(t=t, q=q))
            previous = q
        motion[group] = rows
    review = dict(schema='cruzr-empty-arm-preparation-diagnostic-v1', status='PREPARED_NOT_EXECUTED',
        executable_approved=False, physical_approval=False, robot_connections=0, movement_commands=0,
        source=dict(header=copy.deepcopy(sample['header']), initial_values_by_name={name: initial[name] for name in REQUIRED_JOINTS},
                    extra_axes_not_commanded={name: value for name, value in initial.items() if name not in REQUIRED_JOINTS},
                    freshness_verified=False),
        candidate=dict(arm=arm, groups=list(JOINTS), joint_order={group: list(names) for group, names in JOINTS.items()},
            moving_joints=list(JOINTS[moving_group]), unchanged_joints=[name for name in REQUIRED_JOINTS if name not in offsets],
            native_preparation_vector_rad=list(native_vector), relative_scaled_vector_rad=[offsets[name] for name in JOINTS[moving_group]],
            vector_scale=scale, amplitude_deg=amplitude, maximum_axis_delta_rad=math.radians(amplitude),
            duration_s=DURATION_S, sampling_hz=FREQUENCY_HZ, samples_per_group=count,
            timeline_s=dict(initial_hold=[0, 2], outward_ramp=[2, 10], peak_hold=[10, 12], return_ramp=[12, 20], final_hold=[20, 22]),
            initial_matches_source_exactly=True, final_equals_initial=True, other_13_axes_unchanged=True,
            largest_sample_step_rad=largest_step, analytical_max_velocity_rad_s=1.875*math.radians(amplitude)/RAMP_S,
            analytical_max_acceleration_rad_s2=(10*math.sqrt(3)/3)*math.radians(amplitude)/RAMP_S**2),
        urdf=dict(checked=urdf_text is not None, position_velocity_limits=urdf_limits,
                  checked_joint_count=len(urdf_limits) if urdf_limits is not None else 0,
                  unmodelled_unchanged_joints=([name for name in REQUIRED_JOINTS if name not in urdf_limits]
                                              if urdf_limits is not None else []),
                  sha256=hashlib.sha256(urdf_text.encode()).hexdigest() if urdf_text is not None else None),
        limitations=['Candidate only; no execution or automatic next-arm trial is started or scheduled',
            'Uses measured HOME reference plus scaled native vector, not the full preparation posture or MetaClamp grasp',
            'No box contact, load, elbow clearance, whole-body collision or stopping-distance qualification',
            'Nominal URDF limits do not prove current controller limits, calibration or physical clearance',
            'SDK player/profile/group order and fresh named state must be matched independently before playback',
            'All five body groups are commanded; unchanged values do not create hardware isolation',
            'No new current/force threshold, watchdog, servo limit or recovery behavior is installed',
            'Passive telemetry recording does not itself stop motion; no active safety monitor is implemented'])
    return motion, review


def build(state_path, arm, output, amplitude_deg=MAX_AMPLITUDE_DEG, *, urdf_path=None):
    state_path, output = Path(state_path), Path(output)
    if output.exists():
        raise ValueError('Output directory must be new; refusing to overwrite')
    source = state_path.read_bytes()
    urdf_bytes = Path(urdf_path).read_bytes() if urdf_path is not None else None
    motion, review = prepare(json_object(source), arm, amplitude_deg,
                            urdf_text=urdf_bytes.decode() if urdf_bytes is not None else None)
    raw = (json.dumps(motion, separators=(',', ':'), allow_nan=False)+'\n').encode()
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    filename = 'empty_arm_'+arm+'.motion'
    review['source'].update(path=str(state_path.resolve()), sha256=hashlib.sha256(source).hexdigest())
    review['candidate'].update(path=str((output/filename).resolve()), sha256=hashlib.sha256(raw).hexdigest())
    review['builder_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if urdf_path is not None:
        review['urdf'].update(path=str(Path(urdf_path).resolve()), sha256=hashlib.sha256(urdf_bytes).hexdigest())
    with (output/filename).open('xb') as stream:
        stream.write(raw)
    with (output/'review.json').open('x') as stream:
        json.dump(review, stream, indent=2, allow_nan=False)
        stream.write('\n')
    return review


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True, help='Canonical JointState JSON; no wrapper or motor-axis values')
    parser.add_argument('--arm', choices=('right', 'left'), required=True)
    parser.add_argument('--output', type=Path, required=True, help='New private local output directory')
    parser.add_argument('--amplitude-deg', type=float, default=MAX_AMPLITUDE_DEG)
    parser.add_argument('--urdf', type=Path, help='Freshly verified native URDF for named position/velocity limit checks')
    args = parser.parse_args(argv)
    try:
        review = build(args.state, args.arm, args.output, args.amplitude_deg, urdf_path=args.urdf)
    except (ValueError, OSError, ET.ParseError) as error:
        parser.error(str(error))
    print(json.dumps(dict(status=review['status'], candidate=review['candidate'],
                         urdf_checked=review['urdf']['checked'], movement_commands=0), indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
