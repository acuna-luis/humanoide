"""Offline failure cases for read-only telemetry; all actuator data is synthetic."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
from general_home.passive_trace_remote import parse_line, subscription, TOPICS, NativeMessages
from general_home.trace_analysis import analyze, decode_actuators, strict_json, ACTUATORS


def message(sample=0):
    stamp=dict(sec=1789100000,nanosec=sample*10_000_000)
    return dict(header=dict(stamp=stamp),act_item=[dict(id=i,stamp=stamp,
        position=.001*sample,velocity=.1,cmd_pos=.001*sample+.002,
        status=7,error_code=0) for i in ACTUATORS if i<11000])


def trace():
    records=[dict(kind='start',schema='cruzr-passive-motion-trace-v1',
        received_monotonic_ns=1,movement_commands=0)]
    for topic in TOPICS[1:]:
        records.append(dict(kind='message',topic=topic,message=dict(data=0),received_monotonic_ns=len(records)+1))
    for i in range(4):
        records.append(dict(kind='message',topic=TOPICS[0],message=message(i),received_monotonic_ns=(i+1)*10_000_000))
        if i==1:
            records.append(dict(kind='message',topic=TOPICS[1],message=dict(data=1),received_monotonic_ns=25_000_000))
    records.append(dict(kind='end',received_monotonic_ns=41_000_000,errors=[],movement_commands=0,
                        counts={TOPICS[0]:4,TOPICS[1]:2,TOPICS[2]:1}))
    return records


class PassiveTests(unittest.TestCase):
    def test_capture_drains_an_inflight_object_but_bounds_a_stalled_stream(self):
        for delay,complete,newline in [(1.05,True,True),(2.,False,True),(2.,False,False)]:
            with self.subTest(delay=delay,newline=newline),tempfile.TemporaryDirectory() as temp:
                fake=Path(temp)/'docker'
                fake.write_text('#!/usr/bin/env python3\nimport sys,time\n'
                    'if "/mc/actuator_state" in sys.argv[-1]:\n'
                    f' print("{{",end={chr(10) if newline else ""!r},flush=True)\n'
                    f' time.sleep({delay!r})\n'
                    ' print("\\n".join('+repr(json.dumps(message(),indent=4).splitlines()[1:])+'),flush=True)\n'
                    ' time.sleep(10)\n'
                    'else:\n'
                    ' while True:\n'
                    '  print("data: 1\\n---",flush=True);time.sleep(.05)\n')
                fake.chmod(0o700)
                env=dict(os.environ,PATH=temp+os.pathsep+os.environ['PATH'])
                run=subprocess.run([sys.executable,str(Path(__file__).with_name('general_home')/'passive_trace_remote.py'),
                    '--seconds','1','--motion-container','motion','--ros-container','ros'],
                    env=env,capture_output=True,text=True,timeout=5)
                self.assertEqual(run.returncode,0,run.stderr)
                ending=json.loads(run.stdout.splitlines()[-1])
                self.assertEqual(ending['counts'][TOPICS[0]],int(complete))
                self.assertEqual(bool(ending['errors']),not complete)
                self.assertLess(ending['elapsed_seconds'],3)

    def test_native_multiline_json_frames_exactly_one_message(self):
        reader=NativeMessages();data=message();data['header']['frame_id']='braces } { in a string'
        results=[]
        for line in json.dumps(data,indent=4).encode().splitlines():
            value=reader.feed(line)
            if value is not None:results.append(value)
        self.assertEqual(results,[data]);self.assertFalse(reader.lines)
        self.assertEqual(reader.feed(json.dumps(data).encode()),data)

    def test_native_compact_formatter_is_rejected_and_not_requested(self):
        with self.assertRaises(ValueError):NativeMessages().feed(b"act_item:[{'id':4001}], header:{}")
        self.assertNotIn('--print-compact',subscription(TOPICS[0],'motion','ros',8)[-1])

    def test_truncated_native_json_remains_incomplete(self):
        reader=NativeMessages()
        for line in [b'{',b'    "act_item": []']:
            self.assertIsNone(reader.feed(line))
        self.assertTrue(reader.lines)

    def test_fixed_ros_yaml_stops_and_native_json_are_supported(self):
        self.assertEqual(parse_line(TOPICS[1],b'data: 1'),{'data':1})
        self.assertIsNone(parse_line(TOPICS[1],b'---'))
        self.assertEqual(parse_line(TOPICS[0],json.dumps(message()).encode()),message())
        with self.assertRaises(ValueError):parse_line(TOPICS[0],b'ERROR: no data')
        with self.assertRaises(ValueError):parse_line(TOPICS[0],b'data: 1')
        with self.assertRaises(ValueError):parse_line(TOPICS[1],b'data: 2')

    def test_each_container_subscription_has_its_own_timeout(self):
        for topic in TOPICS:
            argv=subscription(topic,'motion_container','ros_container',8)
            self.assertEqual(argv[:2],['docker','exec'])
            self.assertIn('timeout --signal=TERM --kill-after=1s 11s',argv[-1])
            self.assertIn('topic echo',argv[-1])
            self.assertNotIn('service call',argv[-1]);self.assertNotIn('action send_goal',argv[-1])
        with self.assertRaises(ValueError):subscription('/other','motion','ros',8)

    def test_numeric_observations_keep_upstream_command_and_stopping_limits_explicit(self):
        result=analyze(trace())
        self.assertFalse(result['issues'])
        self.assertEqual(result['actuator_sample_count'],4)
        self.assertAlmostEqual(result['joints']['R_wrist_pitch_joint']['max_abs_requested_command_error_rad'],.002)
        stop=result['stop_observations'][0]
        self.assertAlmostEqual(stop['joint_travel_rad']['L_elbow_roll_joint'],.002)
        self.assertFalse(stop['stopping_bound_qualified'])
        self.assertFalse(result['physical_approval'])

    def test_stationary_capture_without_source_timestamp_progress_is_rejected(self):
        records=trace();records[4]['message']=copy.deepcopy(records[3]['message'])
        self.assertIn('actuator_header_not_advancing',analyze(records)['issues'])

    def test_missing_joint_duplicate_alias_and_nonfinite_values_reject(self):
        for changed in ['missing','duplicate','alias','nan','bool','stamp']:
            data=message()
            if changed=='missing':data['act_item'].pop()
            if changed=='duplicate':data['act_item'].append(copy.deepcopy(data['act_item'][0]))
            if changed=='alias':
                item=next(i for i in data['act_item'] if i['id']==2001).copy();item['id']=11004;data['act_item'].append(item)
            if changed=='nan':data['act_item'][0]['position']=float('nan')
            if changed=='bool':data['act_item'][0]['velocity']=True
            if changed=='stamp':data['act_item'][0]['stamp']={'sec':0,'nanosec':0}
            with self.subTest(changed=changed),self.assertRaises(ValueError):decode_actuators(data)

    def test_no_actuators_under_pressed_estop_does_not_pass(self):
        records=[r for r in trace() if r.get('topic')!=TOPICS[0]]
        records[-1]['counts'][TOPICS[0]]=0
        result=analyze(records)
        self.assertEqual(result['last_observed_stops'][TOPICS[1]],1)
        self.assertIn('insufficient_actuator_samples',result['issues'])
        self.assertFalse(result['physical_approval'])

    def test_incomplete_or_corrupted_capture_is_not_accepted(self):
        self.assertIn('incomplete_stream',analyze(trace()[:-1])['issues'])
        records=trace();records[-1]['counts'][TOPICS[0]]=6
        self.assertIn('end_counts_disagree',analyze(records)['issues'])
        records=trace();records[-1]['errors']=['subscriber failed']
        self.assertIn('collector_reported_errors',analyze(records)['issues'])
        records=trace();records[-2]['received_monotonic_ns']=1
        self.assertTrue(any('Nonmonotonic' in s for s in analyze(records)['issues']))

    def test_receive_gap_and_source_skew_are_visible(self):
        self.assertIn('actuator_receive_gap_exceeded',analyze(trace(),.005)['issues'])
        records=trace();records[3]['message']['act_item'][0]['stamp']={'sec':1789100002,'nanosec':0}
        self.assertIn('actuator_source_stamp_skew_exceeded',analyze(records)['issues'])

    def test_a_stream_that_goes_silent_cannot_pass_on_old_samples(self):
        records=trace();records[-1]['received_monotonic_ns']=200_000_000
        self.assertIn('actuator_stream_silent_before_capture_end',analyze(records)['issues'])

    def test_faults_and_disabled_actuators_are_reported(self):
        records=trace();records[3]['message']['act_item'][0]['status']=8
        values=analyze(records)['joints']['head_yaw_joint']
        self.assertEqual(values['fault_samples'],1);self.assertEqual(values['disabled_samples'],1)

    def test_duplicate_and_nonfinite_json_are_rejected(self):
        for raw in ['{"data":0,"data":1}','{"x":NaN}']:
            with self.assertRaises(ValueError):strict_json(raw)


if __name__=='__main__':unittest.main()
