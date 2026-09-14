#!/usr/bin/env python3
"""Bounded read-only named joint and actuator-health capture. No publishers."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collect_estop_available_readonly import execute

REMOTE = '''
import json,time
import rclpy
from rclpy.qos import qos_profile_sensor_data
from rosidl_runtime_py.utilities import get_message
from rosidl_runtime_py.convert import message_to_ordereddict
rclpy.init();node=rclpy.create_node('entry_named_state_readonly')
topics=['/mc/whole_joint_states','/mc/actuator_state'];latest={};subs=[];rows=[]
def receive(t,m):latest[t]=(time.monotonic(),message_to_ordereddict(m))
try:
 end=time.monotonic()+4
 while time.monotonic()<end:
  graph=dict(node.get_topic_names_and_types())
  if all(t in graph and len(graph[t])==1 for t in topics):break
  rclpy.spin_once(node,timeout_sec=.02)
 else:raise RuntimeError('Topics unavailable')
 for t in topics:subs.append(node.create_subscription(get_message(graph[t][0]),t,lambda m,t=t:receive(t,m),qos_profile_sensor_data))
 end=time.monotonic()+5;last=0
 while time.monotonic()<end:
  rclpy.spin_once(node,timeout_sec=.01);now=time.monotonic()
  if now-last<.05 or len(latest)!=2:continue
  row={'received_monotonic':now,'messages':{}}
  for t in topics:
   received,data=latest[t];stamp=data['header']['stamp'];source_ns=stamp['sec']*10**9+stamp['nanosec']
   age=(node.get_clock().now().nanoseconds-source_ns)/1e9
   if now-received>.5 or not 0<=age<=.5:raise RuntimeError('Stale source or reception')
   row['messages'][t]=data
  rows.append(row);last=now
 print(json.dumps({'schema':'cruzr-entry-named-state-capture-v1','samples':rows,'robot_commands':0},allow_nan=False))
finally:node.destroy_node();rclpy.shutdown()
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    a.output_dir.mkdir(parents=True,exist_ok=False)
    discovery=execute('motion',['docker','ps','--format','{{.Names}}'])
    (a.output_dir/'discovery.json').write_text(json.dumps(discovery,indent=2))
    containers=[n for n in discovery.get('stdout','').splitlines() if n.endswith('ros2-1')]
    if discovery.get('returncode')!=0 or len(containers)!=1:raise RuntimeError('ROS container discovery failed')
    command='source /opt/ros/humble/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; timeout 12 python3 -c '+shlex.quote(REMOTE)
    result=execute('motion',['docker','exec',containers[0],'bash','-lc',command])
    (a.output_dir/'response.json').write_text(json.dumps(result,indent=2))
    (a.output_dir/'collector_remote.py').write_text(REMOTE)
    if result.get('returncode')!=0:raise RuntimeError('Capture failed; see response.json')
    data=json.loads(result['stdout'])
    if len(data.get('samples',[]))<2:raise RuntimeError('Insufficient samples')
    (a.output_dir/'capture.json').write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'samples':len(data['samples']),'robot_commands':0,'sha256':hashlib.sha256((a.output_dir/'capture.json').read_bytes()).hexdigest()}))


if __name__=='__main__':main()
