"""Read-only identity check inside Motion before starting the ROS bridge client."""
import base64
import hashlib
import json
from pathlib import Path
import sys


def check(payload):
    stage, release = payload['stage'], payload['release']
    root = Path('/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config')
    task_path = root/(stage['task']+'.xml')
    if hashlib.sha256(task_path.read_bytes()).hexdigest() != stage['xml_sha256']:
        raise RuntimeError('Installed XML mismatch')
    if hashlib.sha256((root/'task_list.yaml').read_bytes()).hexdigest() != release['task_list_sha256']:
        raise RuntimeError('Task registry mismatch')
    start_ticks = Path('/proc/1/stat').read_text().rsplit(')', 1)[1].split()[19]
    if (Path('/proc/sys/kernel/random/boot_id').read_text().strip() != release['boot_id']
            or start_ticks != str(release['pid1_start_ticks'])):
        raise RuntimeError('Motion process identity changed since qualification')


if __name__ == '__main__':
    check(json.loads(base64.b64decode(sys.argv[1], validate=True)))
