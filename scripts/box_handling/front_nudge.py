#!/usr/bin/env python3
"""ROS2 container: one supervised 5cm navigation goal, or read-only --check.

Never publishes velocities, changes limits, selects a box, or retries a goal.
Requires the existing utars_nav_map localization and the external robot preflight.
A stop request is not proof of physical stopping; supervision remains necessary.
"""
import argparse
import json
import math
import signal
import time

DISTANCE = .05
MAP = 'utars_nav_map'
# The 2026-09-22 trial exposed a reverse command from ArcPreciseController
# for this forward target. Preserve read-only diagnostics; no further dispatch
# until that vendor contract is resolved and another trial is reviewed.
RUN_QUALIFIED = False


def yaw(q):
    values = [q[k] for k in ('x', 'y', 'z', 'w')]
    if not all(math.isfinite(v) for v in values) or abs(sum(v*v for v in values)-1) > .02:
        raise ValueError('Invalid quaternion')
    return math.atan2(2*(q['w']*q['z']+q['x']*q['y']), 1-2*(q['y']**2+q['z']**2))


def xyheading(pose):
    x, y = pose['position']['x'], pose['position']['y']
    if not all(math.isfinite(v) for v in (x,y)):
        raise ValueError('Nonfinite position')
    return (x, y, yaw(pose['orientation']))


def target_for(pose):
    x,y,angle = xyheading(pose)
    return dict(map_name=MAP, mode='free_nav', level=1,
        point_x=x+DISTANCE*math.cos(angle), point_y=y+DISTANCE*math.sin(angle), point_yaw=angle,
        speed=dict(linear=dict(x=.03,y=0.,z=0.), angular=dict(x=0.,y=0.,z=.05)))


def displacement(start, current):
    dx,dy = current[0]-start[0], current[1]-start[1]
    angle = math.atan2(math.sin(current[2]-start[2]), math.cos(current[2]-start[2]))
    return (math.cos(start[2])*dx+math.sin(start[2])*dy,
            -math.sin(start[2])*dx+math.cos(start[2])*dy, angle)


def check_corridor(delta):
    forward, lateral, angle = delta
    if not all(math.isfinite(v) for v in delta):
        raise ValueError('Nonfinite displacement')
    if not -.005 <= forward <= .06 or abs(lateral) > .012 or abs(angle) > math.radians(2):
        raise ValueError('Outside supervised straight-step envelope: '+repr(delta))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check',action='store_true');mode.add_argument('--run',action='store_true')
    parser.add_argument('--physical-confirmed',action='store_true')
    args=parser.parse_args()
    if args.run and not args.physical_confirmed:parser.error('Current physical confirmation required')
    if args.run and not RUN_QUALIFIED:
        parser.error('Run blocked after reverse-motion trial; use --check and review the navigation contract')
    import rclpy
    from rclpy.action import ActionClient
    from rclpy.qos import qos_profile_sensor_data
    from rosidl_runtime_py.convert import message_to_ordereddict
    from geometry_msgs.msg import PoseStamped
    from nav_msgs.msg import Odometry
    from std_msgs.msg import UInt8
    from unav_task_msgs.action import Task
    from mc_state_msgs.msg import ActuatorState
    rclpy.init();node=rclpy.create_node('front_five_cm_navigation_probe')
    client=ActionClient(node,Task,'/vnav/task/command');state={};subs=[]
    moving=False;start=None;initial_body=None;last_trace=0.
    def emit(**row):print(json.dumps(dict(monotonic=time.monotonic(),**row),allow_nan=False),flush=True)
    def receive(key,msg):state[key]=(time.monotonic(),message_to_ordereddict(msg))
    for key,topic,typ in [('map','/nav/robot_pose',PoseStamped),('odom','/mc/odom',Odometry),
        ('actuators','/mc/actuator_state',ActuatorState),('estop','/emb/estop_key_state',UInt8),
        ('servo','/emb/servo_estop_key_state',UInt8),('charger','/emb/chrg_input_status',UInt8)]:
        subs.append(node.create_subscription(typ,topic,lambda m,k=key:receive(k,m),qos_profile_sensor_data))
    def checked():
        now=time.monotonic()
        for key in ('map','odom','actuators','estop','servo','charger'):
            limit=6 if key in ('estop','servo','charger') else .5
            if key not in state or not 0 <= now-state[key][0] <= limit:
                raise RuntimeError('Missing/stale telemetry '+key)
            data=state[key][1]
            if key in ('estop','servo','charger'):
                if data['data'] != 0:raise RuntimeError('Stop/charger active '+key)
            else:
                stamp=data['header']['stamp'];age=(node.get_clock().now().nanoseconds-stamp['sec']*10**9-stamp['nanosec'])/1e9
                if not -.05 <= age <= .5:raise RuntimeError('Invalid source time '+key)
        if state['map'][1]['header']['frame_id']!='map':raise RuntimeError('Wrong map frame')
        # Canonical logical IDs for this verified v0.2.0 clamp unit.
        groups=[(1001,),(1002,),(2001,11004),(2002,11003),(2003,11002),(3001,11001),
                *[(i,) for i in range(4001,4008)],*[(i,) for i in range(5001,5008)]]
        items=state['actuators'][1]['act_item'];ids=[x['id'] for x in items]
        if len(ids)!=len(set(ids)):raise RuntimeError('Duplicate actuator IDs')
        body=[]
        for group in groups:
            found=[x for x in items if x['id'] in group]
            if len(found)!=1:raise RuntimeError('Missing/ambiguous body actuator')
            x=found[0]
            if x['error_code'] or x['status']&8 or x['status']&7!=7:raise RuntimeError('Actuator fault/disabled')
            values=[x[k] for k in ('position','velocity','cmd_pos')]
            if not all(math.isfinite(v) for v in values) or abs(x['velocity'])>.02 or abs(x['cmd_pos']-x['position'])>.01:
                raise RuntimeError('Body moving or inconsistent command')
            body.append(x['position'])
        if initial_body is not None and any(abs(a-b)>.01 for a,b in zip(body,initial_body)):
            raise RuntimeError('Body posture changed')
        odo=state['odom'][1];twist=odo['twist']['twist']
        if not all(math.isfinite(twist[t][k]) for t in ('linear','angular') for k in 'xyz'):
            raise RuntimeError('Nonfinite odometry twist')
        if moving and (math.hypot(twist['linear']['x'],twist['linear']['y'])>.06
                       or abs(twist['angular']['z'])>.10):
            raise RuntimeError('Unexpected base speed')
        current=xyheading(odo['pose']['pose'])
        if start is not None:check_corridor(displacement(start,current))
        return current,body
    def wait(future,seconds,monitor=False):
        nonlocal last_trace
        end=time.monotonic()+seconds
        while not future.done() and time.monotonic()<end:
            rclpy.spin_once(node,timeout_sec=.02)
            if monitor:
                current,_=checked()
                if time.monotonic()-last_trace>.1:
                    emit(kind='progress',delta=displacement(start,current));last_trace=time.monotonic()
        if not future.done():raise TimeoutError('Action completion unknown; no retry')
        return future.result()
    def command(name,arg=None,seconds=10,monitor=False):
        handle=wait(client.send_goal_async(Task.Goal(command=name,arg_json=json.dumps(arg or {}))),5,monitor)
        if not handle.accepted:raise RuntimeError('Rejected '+name)
        emit(kind='accepted',command=name,goal_id=bytes(handle.goal_id.uuid).hex())
        response=wait(handle.get_result_async(),seconds,monitor)
        result=message_to_ordereddict(response.result)
        emit(kind='result',command=name,status=response.status,result=result)
        if response.status!=4:raise RuntimeError('Failed '+name)
        return result
    def stationary():
        t=state['odom'][1]['twist']['twist']
        return math.hypot(t['linear']['x'],t['linear']['y'])<.003 and abs(t['angular']['z'])<.01
    def interrupted(signum,frame):raise InterruptedError('Interrupted; request stop, no retry')
    for sig in (signal.SIGINT,signal.SIGTERM,signal.SIGHUP):signal.signal(sig,interrupted)
    try:
        if not client.wait_for_server(timeout_sec=4):raise RuntimeError('Navigation server absent')
        actual=command('get_map_name');fsm=command('check_state')
        if json.loads(actual['result_json'])['map_name']!=MAP or 'FSM_WAITNAVIGATE' not in fsm['dmsg']:
            raise RuntimeError('Map/localization not ready; run preparation separately')
        end=time.monotonic()+12;stable_since=None
        while time.monotonic()<end:
            rclpy.spin_once(node,timeout_sec=.02)
            try:checked();ok=stationary()
            except (RuntimeError,ValueError):ok=False
            stable_since=(stable_since or time.monotonic()) if ok else None
            if stable_since and time.monotonic()-stable_since>=1:break
        else:raise RuntimeError('Could not admit stationary healthy telemetry')
        start,initial_body=checked();target=target_for(state['map'][1]['pose'])
        emit(kind='plan',target=target,odom_start=start,body=initial_body,physical_confirmed=args.physical_confirmed)
        if args.check:emit(status='NUDGE_CHECK_OK_NO_MOTION');return
        moving=True
        result=command('navigation_start',{'target_point':target},30,True)
        if (result['state']['desc'] not in ('SUCCESS','SUCCEED') and
                not result['dmsg'].startswith('navigation_start SUCCEEDED')):
            raise RuntimeError('Navigation result did not establish arrival')
        end=time.monotonic()+4;stable_since=None
        while time.monotonic()<end:
            rclpy.spin_once(node,timeout_sec=.02);current,_=checked()
            stable_since=(stable_since or time.monotonic()) if stationary() else None
            if stable_since and time.monotonic()-stable_since>=1:break
        else:raise RuntimeError('Base did not settle')
        delta=displacement(start,current)
        moving=False
        if not .035 <= delta[0] <= .06:
            raise RuntimeError('Measured travel not a 5cm step; no retry: '+repr(delta))
        emit(status='NUDGE_FINISHED_AND_STATIONARY',delta=delta,grasp_sent=False)
    except BaseException as exc:
        emit(status='NUDGE_FAILED_NO_RETRY',reason=str(exc))
        if moving:
            try:command('navigation_stop',seconds=8)
            except BaseException as stop_error:emit(status='STOP_RESPONSE_UNCONFIRMED',reason=str(stop_error))
            emit(status='PHYSICAL_STOP_REQUIRES_VERIFICATION')
        raise
    finally:
        client.destroy();node.destroy_node();rclpy.shutdown()


if __name__=='__main__':main()
