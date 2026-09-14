#!/usr/bin/env python3
"""Describe recorded head probe motion; no stop/servo certification or robot IO."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--trace',type=Path,required=True);p.add_argument('--after-analysis',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();rows=[json.loads(line) for line in a.trace.read_text().splitlines()]
    whole=[r for r in rows if r.get('topic')=='/mc/whole_joint_states']
    motors=[r for r in rows if r.get('topic')=='/mc/actuator_state']
    events=[r for r in rows if r.get('kind')!='message']
    dispatch=next(r['received_monotonic'] for r in events if r.get('kind')=='dispatch')
    def positions(r):return dict(zip(r['message']['name'],r['message']['position'],strict=True))
    initial=positions(next(r for r in reversed(whole) if r['received_monotonic']<dispatch))
    final=positions(whole[-1]);head={}
    for name,ident in [('head_yaw_joint',1001),('head_pitch_joint',1002)]:
        values=[item for r in motors for item in r['message']['act_item'] if item['id']==ident]
        head[name]=dict(initial_joint_rad=initial[name],final_joint_rad=final[name],
            observed_max_motor_velocity_rad_s=max(abs(v['velocity']) for v in values),
            observed_max_requested_command_discrepancy_deg=max(abs(v['cmd_pos']-v['position'])*180/math.pi for v in values),
            motor_samples=len(values),applied_servo_setpoint_available=False)
    others=[n for n in initial if not n.startswith(('head_','driving_wheel_'))]
    deviations={n:max(abs(positions(r)[n]-initial[n]) for r in whole if r['received_monotonic']>=dispatch) for n in others}
    stops={t:[r['received_monotonic'] for r in rows if r.get('topic')==t]
           for t in ('/emb/estop_key_state','/emb/servo_estop_key_state')}
    after=json.loads(a.after_analysis.read_text())
    result=dict(scope='ONE_HEAD_TRIAL_SAMPLED_OBSERVATIONS_ONLY',head=head,other_joint_maximum_deviation_rad=deviations,
        maximum_named_state_receive_gap_seconds=max(b['received_monotonic']-x['received_monotonic'] for x,b in zip(whole,whole[1:])),
        events=events,stop_receive_times=stops,
        after_capture_issues=after['issues'],after_capture_sample_count=after['actuator_sample_count'],
        after_capture_max_abs_velocity_rad_s=max(v['max_abs_velocity_rad_s'] for v in after['joints'].values()),
        cancellation_caused_stop_demonstrated=False,physical_estop_exercised=False,
        stopping_bound_qualified=False,physical_approval_of_ENTRY=False,
        limitations=['cmd_pos is requested without limit, not the applied servo setpoint',
            'Stop-topic receipt is not physical switch actuation time',
            'A final stationary posture does not establish the effect of cancellation',
            'This head trial does not qualify arms, lifter or future error bounds'])
    result['sources_sha256']={str(f.resolve()):hashlib.sha256(f.read_bytes()).hexdigest() for f in (a.trace,a.after_analysis,Path(__file__))}
    with a.output.open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(head=head,after_velocity=result['after_capture_max_abs_velocity_rad_s'])))


if __name__=='__main__':main()
