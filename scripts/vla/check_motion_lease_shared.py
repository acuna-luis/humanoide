#!/usr/bin/env python3
"""Check a temporary lease path and monotonic clock across Motion containers.

This makes one private temporary marker on Motion and removes it on completion.
It sends no ROS actions and neither qualifies nor starts physical control.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collect_estop_available_readonly import execute

REMOTE = r'''import json,os,subprocess,tempfile,time,uuid
containers=['walker-ros.ros2-1','walker-motion.manipulation_robot_app-1']
with tempfile.TemporaryDirectory(prefix='pico-lease-shared-check-',dir='/tmp') as directory:
 os.chmod(directory,0o700)
 path=directory+'/marker'
 token=uuid.uuid4().hex
 with open(path,'x') as stream: stream.write(token)
 result={}
 for container in containers:
  probe="import json,os,time; print(json.dumps({'value':open("+repr(path)+").read(),'namespace':os.readlink('/proc/self/ns/time'),'monotonic':time.monotonic()}))"
  before=time.monotonic()
  process=subprocess.run(['docker','exec',container,'python3','-B','-c',probe],capture_output=True,text=True,timeout=6)
  after=time.monotonic()
  if process.returncode:
   raise RuntimeError('container_probe_failed:'+container)
  value=json.loads(process.stdout)
  result[container]={'read_matches':value['value']==token,
   'same_time_namespace':value['namespace']==os.readlink('/proc/self/ns/time'),
   'monotonic_in_host_interval':before<=value['monotonic']<=after,
   'interval_seconds':after-before}
print(json.dumps(result))
'''


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', required=True)
    parser.parse_args(argv)
    try:
        discovery = execute('motion', ['docker', 'ps', '--format', '{{.Names}}'])
        expected = {'walker-ros.ros2-1', 'walker-motion.manipulation_robot_app-1'}
        if discovery.get('returncode') != 0 or not expected <= set(discovery.get('stdout', '').splitlines()):
            raise ValueError('required_containers_not_found')
        remote = execute('motion', ['python3', '-B', '-c', REMOTE])
        if remote.get('returncode') != 0:
            raise RuntimeError('remote_check_failed')
        result = json.loads(remote.get('stdout', ''))
        if set(result) != expected or any(any(value.get(key) is not True for key in
               ('read_matches', 'same_time_namespace', 'monotonic_in_host_interval'))
               for value in result.values()):
            raise ValueError('shared_lease_or_clock_unconfirmed')
        print(json.dumps({'status': 'SHARED_TMP_AND_CLOCK_OBSERVED', 'containers': result,
                          'physical_control_qualified': False, 'movement_commands': 0}, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        print('SHARED_CHECK_FAILED: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
