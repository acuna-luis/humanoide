"""Fixed head-only supervised probe. No installation, restart or recovery."""
import json
import math
import time


def check_envelope(q, initial, names):
    if any(not math.isfinite(q[n]) for n in names):raise RuntimeError('Nonfinite state')
    if not -.45<=q['head_pitch_joint']<=.02 or abs(q['head_yaw_joint'])>.02:
        raise RuntimeError('Head outside reviewed envelope')
    if any(abs(q[n]-initial[n])>.02 for n in names if not n.startswith('head_')):
        raise RuntimeError('Other joint moved outside stationary envelope')


def check_stop_cadence(samples, maximum_gap=3.):
    if len(samples)<2:return False
    if any(b-a>maximum_gap for a,b in zip(samples,samples[1:])):
        raise RuntimeError('E-stop telemetry cadence exceeds monitor requirement; no dispatch')
    return True


def main(run):
    import rclpy
    from rclpy.action import ActionClient
    from rclpy.qos import qos_profile_sensor_data
    from rosidl_runtime_py.utilities import get_message
    from rosidl_runtime_py.convert import message_to_ordereddict
    from mc_task_msgs.action import ArmTask
    rclpy.init();node=rclpy.create_node('fixed_metamove_head_probe')
    state={};subs=[];goal=None;result=None;stop_times={}
    def emit(**row):print(json.dumps(dict(received_monotonic=time.monotonic(),**row),allow_nan=False),flush=True)
    topics=['/mc/whole_joint_states','/mc/actuator_state','/emb/estop_key_state','/emb/servo_estop_key_state']
    names=['head_yaw_joint','head_pitch_joint','waist_yaw_joint',
           *['lifter_pitch_'+str(i)+'_joint' for i in (1,2,3)],
           *[s+'_'+j+'_joint' for s in ('L','R') for j in ('shoulder_pitch','shoulder_roll','shoulder_yaw','elbow_roll','elbow_yaw','wrist_pitch','wrist_roll')]]
    def receive(t,m):
        data=message_to_ordereddict(m);now=time.monotonic()
        if t in topics[2:]:stop_times.setdefault(t,[]).append(now)
        state[t]=(now,data)
        emit(kind='message',topic=t,message=data)
    def checked():
        now=time.monotonic()
        for t in topics:
            if t not in state or now-state[t][0]>(3 if t in topics[2:] else .5):
                raise RuntimeError('Missing/stale telemetry: '+t)
        if any(state[t][1]['data']!=0 for t in topics[2:]):raise RuntimeError('E-stop active')
        raw=state[topics[1]][1]
        selected=[x for x in raw['act_item'] if x['id'] in [1001,1002,11001,11002,11003,11004,2001,2002,2003,3001,*range(4001,4008),*range(5001,5008)]]
        if len(selected)!=20 or any(x['error_code'] or x['status']&8 or x['status']&7!=7 for x in selected):
            raise RuntimeError('Actuator count, fault or disabled actuator')
        msg=state[topics[0]][1]
        for data in (raw,msg):
            stamp=data['header']['stamp'];age=(node.get_clock().now().nanoseconds-(stamp['sec']*10**9+stamp['nanosec']))/1e9
            if not 0<=age<=.5:raise RuntimeError('Stale source stamp')
        if len(set(msg['name']))!=len(msg['name']):raise RuntimeError('Duplicate joint name')
        q=dict(zip(msg['name'],msg['position'],strict=True));v=dict(zip(msg['name'],msg['velocity'],strict=True))
        if any(n not in q or n not in v or not math.isfinite(q[n]) or not math.isfinite(v[n]) for n in names):
            raise RuntimeError('Incomplete finite named state')
        return q,v
    try:
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            graph=dict(node.get_topic_names_and_types())
            if all(t in graph and len(graph[t])==1 for t in topics):break
            rclpy.spin_once(node,timeout_sec=.1)
        else:raise RuntimeError('Required topics unavailable')
        for t in topics:
            subs.append(node.create_subscription(get_message(graph[t][0]),t,lambda m,t=t:receive(t,m),qos_profile_sensor_data))
        deadline=time.monotonic()+10;since=None;last_reason='No usable state'
        while time.monotonic()<deadline:
            rclpy.spin_once(node,timeout_sec=.02)
            # Do not mistake one fresh initial sample for a viable heartbeat.
            cadence=all(check_stop_cadence(stop_times.get(t,[])) for t in topics[2:])
            try:q,v=checked();ok=cadence and all(abs(q[n])<=.02 and abs(v[n])<=.001 for n in names)
            except RuntimeError as error:ok=False;last_reason=str(error)
            since=(since or time.monotonic()) if ok else None
            if since and time.monotonic()-since>=1:break
        else:raise RuntimeError('HOME/telemetry admission failed: '+last_reason)
        if not run:emit(status='HEAD_PROBE_READ_ONLY_PASSED');return
        initial=dict(q)
        client=ActionClient(node,ArmTask,'/mc/manipulation/action')
        if not client.wait_for_server(timeout_sec=2):raise RuntimeError('Action server absent')
        checked()
        request=ArmTask.Goal();request.task_name='cruzr/move_head_lower';request.yaml_args='{}'
        emit(kind='dispatch',task=request.task_name)
        future=client.send_goal_async(request);deadline=time.monotonic()+5
        while not future.done() and time.monotonic()<deadline:rclpy.spin_once(node,timeout_sec=.02)
        if not future.done():raise RuntimeError('Acceptance unknown; no retry; operator E-stop required')
        goal=future.result()
        if not goal.accepted:raise RuntimeError('Goal rejected')
        emit(kind='accepted',goal_id=list(map(int,goal.goal_id.uuid)));result=goal.get_result_async();deadline=time.monotonic()+10;since=None;reported=False
        while time.monotonic()<deadline:
            rclpy.spin_once(node,timeout_sec=.01);q,v=checked()
            check_envelope(q,initial,names)
            if result is not None and result.done():
                response=result.result()
                if response.status!=4 or response.result.state.desc!='SUCCEED':raise RuntimeError('Motion did not succeed')
                if not reported:emit(kind='action_succeeded',result=message_to_ordereddict(response.result));reported=True
                stable=abs(q['head_pitch_joint']+.43)<=.02 and all(abs(v[n])<=.01 for n in names)
                since=(since or time.monotonic()) if stable else None
                if since and time.monotonic()-since>=1:
                    emit(status='HEAD_PROBE_SUCCEEDED_AND_SETTLED',normal_completion_only=True,estop_qualified=False);return
        raise RuntimeError('Head trial deadline exceeded')
    except BaseException as exc:
        emit(status='HEAD_PROBE_FAILED_NO_RETRY',reason=str(exc))
        if goal is not None and goal.accepted:
            future=goal.cancel_goal_async();deadline=time.monotonic()+2
            while not future.done() and time.monotonic()<deadline:rclpy.spin_once(node,timeout_sec=.02)
            emit(kind='cancel_request',response_received=future.done(),
                 response=message_to_ordereddict(future.result()) if future.done() else None,
                 physical_stop_demonstrated=False)
            if result is not None and result.done():
                response=result.result()
                emit(kind='late_action_result',status=response.status,result=message_to_ordereddict(response.result))
        raise
    finally:node.destroy_node();rclpy.shutdown()


if __name__=='__main__':
    import sys
    if sys.argv[1:] not in (['--check'],['--run']):raise SystemExit('Expected --check or --run')
    main(sys.argv[1:] == ['--run'])
