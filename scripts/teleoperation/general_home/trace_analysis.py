"""Offline observations from passive telemetry, never a stopping certificate."""
import json
import math

ACTUATORS = {
    1001: 'head_yaw_joint', 1002: 'head_pitch_joint',
    2001: 'lifter_pitch_1_joint', 11004: 'lifter_pitch_1_joint',
    2002: 'lifter_pitch_2_joint', 11003: 'lifter_pitch_2_joint',
    2003: 'lifter_pitch_3_joint', 11002: 'lifter_pitch_3_joint',
    3001: 'waist_yaw_joint', 11001: 'waist_yaw_joint',
}
ARM_ORDER = ['shoulder_pitch', 'shoulder_roll', 'shoulder_yaw', 'elbow_roll',
             'elbow_yaw', 'wrist_pitch', 'wrist_roll']
for prefix, base in [('L', 4001), ('R', 5001)]:
    ACTUATORS.update({base+i: prefix+'_'+name+'_joint' for i,name in enumerate(ARM_ORDER)})
NAMES = sorted(set(ACTUATORS.values()))
ACT_TOPIC = '/mc/actuator_state'
STOP_TOPICS = ['/emb/estop_key_state', '/emb/servo_estop_key_state']


def number(value, label):
    if type(value) not in (int,float) or not math.isfinite(value):
        raise ValueError(label+': expected finite number')
    return float(value)


def integer(value, label, lower=0, upper=None):
    if type(value) is not int or value < lower or (upper is not None and value > upper):
        raise ValueError(label+': invalid integer')
    return value


def stamp_ns(stamp):
    if not isinstance(stamp,dict): raise ValueError('Missing source stamp')
    seconds = integer(stamp.get('sec'), 'stamp seconds')
    ns = integer(stamp.get('nanosec'), 'stamp nanoseconds', upper=999999999)
    if seconds == 0 and ns == 0: raise ValueError('Zero source stamp')
    return seconds*1_000_000_000+ns


def decode_actuators(message):
    items = message.get('act_item')
    if not isinstance(items,list): raise ValueError('Missing act_item array')
    header = stamp_ns(message.get('header',{}).get('stamp'))
    result = {}
    ids = set()
    for item in items:
        if not isinstance(item,dict): raise ValueError('Invalid actuator object')
        actuator_id = integer(item.get('id'),'actuator id')
        if actuator_id in ids: raise ValueError('Duplicate actuator ID')
        ids.add(actuator_id)
        if actuator_id not in ACTUATORS: continue  # Wheels/hands are outside the 20 axes.
        name = ACTUATORS[actuator_id]
        if name in result: raise ValueError('Duplicate actuator aliases for '+name)
        state = {key: number(item.get(key),key) for key in ['position','velocity','cmd_pos']}
        state.update(stamp_ns=stamp_ns(item.get('stamp')),
                     error_code=integer(item.get('error_code'),'error_code',upper=65535),
                     status=integer(item.get('status'),'status',upper=65535))
        result[name] = state
    if set(result) != set(NAMES): raise ValueError('Missing controlled actuators: '+','.join(sorted(set(NAMES)-set(result))))
    return header,result


def strict_json(line):
    def unique(items):
        result={}
        for key,value in items:
            if key in result: raise ValueError('Duplicate JSON key: '+key)
            result[key]=value
        return result
    def constant(value): raise ValueError('Nonfinite JSON: '+value)
    return json.loads(line,object_pairs_hook=unique,parse_constant=constant)


def analyze(records, max_gap_seconds=.05):
    if not 0 < number(max_gap_seconds,'max gap') <= 1: raise ValueError('max gap outside (0,1]')
    issues=[]; samples=[]; states={topic:[] for topic in STOP_TOPICS}
    seen_counts={ACT_TOPIC:0, **{topic:0 for topic in STOP_TOPICS}}
    start=None; ending=None; previous_receive=None; previous_source=None
    max_gap=0.; max_source_skew=0.; previous_act_stamp={}
    def issue(message):
        if len(issues)<100 and message not in issues:issues.append(message)
    for index,record in enumerate(records):
        try:
            if not isinstance(record,dict):raise ValueError('Expected record object')
            receive=integer(record.get('received_monotonic_ns'),'receive time',lower=1)
            if previous_receive is not None and receive <= previous_receive:raise ValueError('Nonmonotonic receive time')
            previous_receive=receive
            kind=record.get('kind')
            if ending is not None:raise ValueError('Data after end marker')
            if kind=='start':
                if index or start is not None:raise ValueError('Unexpected start marker')
                if record.get('schema')!='cruzr-passive-motion-trace-v1':raise ValueError('Unknown trace schema')
                if record.get('movement_commands')!=0:raise ValueError('Not passive capture')
                start=record;continue
            if start is None:raise ValueError('Missing start marker')
            if kind=='end':
                ending=record
                if record.get('errors') or record.get('error_count',0):issue('collector_reported_errors')
                if record.get('movement_commands')!=0:issue('end_marker_not_passive')
                continue
            if kind!='message':raise ValueError('Unknown record kind')
            topic=record.get('topic');message=record.get('message')
            if topic not in seen_counts or not isinstance(message,dict):raise ValueError('Unknown/malformed topic')
            seen_counts[topic]+=1
            if topic in STOP_TOPICS:
                value=integer(message.get('data'),'E-stop state',upper=1)
                states[topic].append((receive,value));continue
            header,joints=decode_actuators(message)
            if previous_source is not None and header <= previous_source:issue('actuator_header_not_advancing')
            previous_source=header
            for name,joint in joints.items():
                source=joint['stamp_ns']
                if name in previous_act_stamp and source<=previous_act_stamp[name]:issue('actuator_stamp_not_advancing:'+name)
                previous_act_stamp[name]=source
                max_source_skew=max(max_source_skew,abs(source-header)/1e9)
            if samples:max_gap=max(max_gap,(receive-samples[-1][0])/1e9)
            samples.append((receive,joints))
        except (ValueError,TypeError,AttributeError) as exc:issue('record '+str(index)+': '+str(exc))
    if start is None or ending is None:issue('incomplete_stream')
    if ending is not None and ending.get('counts')!=seen_counts:issue('end_counts_disagree')
    if len(samples)<2:issue('insufficient_actuator_samples')
    if samples and ending is not None:
        if (ending['received_monotonic_ns']-samples[-1][0])/1e9 > max_gap_seconds:
            issue('actuator_stream_silent_before_capture_end')
    if max_gap>max_gap_seconds:issue('actuator_receive_gap_exceeded')
    if max_source_skew>max_gap_seconds:issue('actuator_source_stamp_skew_exceeded')
    for topic,values in states.items():
        if not values:issue('missing_stop_samples:'+topic)
    peaks={name:dict(max_abs_velocity_rad_s=0.,max_abs_requested_command_error_rad=0.,
                     observed_position_span_rad=0.,fault_samples=0,disabled_samples=0) for name in NAMES}
    for name in NAMES:
        values=[joints[name] for _,joints in samples]
        if not values:continue
        peaks[name]=dict(max_abs_velocity_rad_s=max(abs(j['velocity']) for j in values),
            max_abs_requested_command_error_rad=max(abs(j['cmd_pos']-j['position']) for j in values),
            observed_position_span_rad=max(j['position'] for j in values)-min(j['position'] for j in values),
            fault_samples=sum(bool(j['error_code'] or (j['status']&8)) for j in values),
            disabled_samples=sum((j['status']&7)!=7 for j in values))
    stops=[]
    for topic,values in states.items():
        for i,(received,value) in enumerate(values):
            if not i or not value or values[i-1][1]!=0:continue
            before=[s for s in samples if s[0]<received]
            released=next((t for t,v in values[i+1:] if v==0),math.inf)
            after=[s for s in samples if received<=s[0]<released]
            observation=dict(topic=topic,received_monotonic_ns=received,
                physical_stop_time_known=False,stopping_bound_qualified=False,
                status='INSUFFICIENT_BRACKETING_DATA')
            if before and after:
                selected=[before[-1]]+after
                observation.update(status='SAMPLED_OBSERVATION_ONLY',
                    before_event_gap_seconds=(received-selected[0][0])/1e9,
                    after_event_gap_seconds=(after[0][0]-received)/1e9,
                    observed_after_seconds=(after[-1][0]-received)/1e9,
                    joint_travel_rad={name:sum(abs(b[name]['position']-a[name]['position'])
                        for (_,a),(_,b) in zip(selected,selected[1:])) for name in NAMES},
                    last_sample_max_abs_velocity_rad_s=max(abs(j['velocity']) for j in after[-1][1].values()))
            stops.append(observation)
    return dict(schema='cruzr-passive-motion-analysis-v1',
        status='NUMERIC_OBSERVATIONS_AVAILABLE' if not issues else 'INSUFFICIENT_OR_INVALID_DATA',
        issues=issues,actuator_sample_count=len(samples),max_receive_gap_seconds=max_gap,
        max_source_stamp_skew_seconds=max_source_skew,analysis_gap_threshold_seconds=max_gap_seconds,
        joints=peaks,last_observed_stops={topic:values[-1][1] if values else None for topic,values in states.items()},
        stop_sample_counts={topic:len(values) for topic,values in states.items()},
        stop_observations=stops,physical_approval=False,stopping_bound_qualified=False,
        limitations=['cmd_pos is the last requested command WITHOUT LIMIT, not the applied servo setpoint',
            'No clock synchronization or absolute sample freshness is certified',
            'Topic receive time is not physical E-stop actuation time',
            'Sampled travel omits possible motion between samples and is not an upper bound',
            'This recorder is not a watchdog, does not cancel actions and cannot stop a robot',
            'Data from one trial cannot qualify every posture, speed or stopping mechanism'])
