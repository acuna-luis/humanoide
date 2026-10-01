"""A real terminal-group SIGINT must leave the isolated transport alive."""
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import tempfile
import unittest

from scripts.box_handling import scenario1_cli as cli


# The stand-in server completes only after receiving a heartbeat DURING the
# pending stage. Neither this fixture nor its launcher connects to a robot.
SERVER = r'''
import json,sys
json.loads(sys.stdin.readline())
print(json.dumps(dict(event='ready')),flush=True)
pending=False
for line in sys.stdin:
    message=json.loads(line)
    if message['command']=='stage': pending=True
    elif message['command']=='heartbeat' and pending:
        print(json.dumps(dict(event='stage_complete',heartbeat_observed=True)),flush=True)
        pending=False
    elif message['command']=='finish': break
'''


class ProcessGroupSignalTest(unittest.TestCase):
    def test_terminal_ctrl_c_keeps_child_and_heartbeat_until_stage_finishes(self):
        with tempfile.TemporaryDirectory() as directory:
            harness = '''import json,sys
from pathlib import Path
from scripts.box_handling import scenario1_cli as cli
cli.ssh_command=lambda wifi: [sys.executable,'-u','-c',SERVER]
with cli.StageStop(True) as stop:
    connection=cli.Connection({},False,Path(DIRECTORY))
    try:
        connection.wait('ready',timeout=8)
        connection.send(dict(command='stage'))
        print('AWAITING_SIGINT',flush=True)
        result=connection.wait('stage_complete',timeout=8)
        cli.finish_connection(connection)
        print('RESULT='+json.dumps(dict(requested=stop.requested,heartbeat=result['heartbeat_observed'])),flush=True)
    finally: connection.close()
'''.replace('SERVER', repr(SERVER)).replace('DIRECTORY', repr(directory))
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
            child = subprocess.Popen([sys.executable, '-u', '-B', '-c', harness], cwd=cli.ROOT,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                     start_new_session=True, env=env)
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(child.stdout, selectors.EVENT_READ)
                    self.assertTrue(selector.select(8), 'Harness failed to become ready')
                self.assertEqual(child.stdout.readline().strip(), 'AWAITING_SIGINT')
                os.killpg(child.pid, signal.SIGINT)
                stdout, stderr = child.communicate(timeout=10)
                self.assertEqual(child.returncode, 0, stderr)
                result = next(line.removeprefix('RESULT=') for line in stdout.splitlines() if line.startswith('RESULT='))
                self.assertEqual(json.loads(result), dict(requested=True, heartbeat=True))
                self.assertIn('terminaré la etapa actual', stderr)
            finally:
                if child.poll() is None:
                    child.kill()
                    child.communicate(timeout=3)


if __name__ == '__main__':
    unittest.main()
