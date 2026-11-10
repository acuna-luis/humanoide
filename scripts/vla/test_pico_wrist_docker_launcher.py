"""Candidate host launcher tests; no docker, network or robot use."""
import json
import os
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent/'runtime'))
import pico_wrist_docker_launcher as launcher


class Output:
    def __init__(self): self.rows=[]; self.ready=threading.Event()
    def emit(self, row): self.rows.append(row); self.ready.set(); return True


class HostLauncherTests(unittest.TestCase):
    def test_gate_blocks_before_docker_or_payload(self):
        with patch.object(launcher.subprocess, 'run', side_effect=AssertionError('must not connect')):
            with self.assertRaisesRegex(RuntimeError, 'physical_dispatch_blocked'):
                launcher.launch(None)

    def handoff(self, *, wrong=False):
        read_fd, write_fd = os.pipe()
        session = {'session_id':'a'*32, 'age_at_handoff_s':0.0}
        output=Output(); failures=[]
        def run():
            try: launcher.pc_preflight_handoff(session, output, read_fd)
            except BaseException as exc: failures.append(exc)
        thread=threading.Thread(target=run); thread.start()
        try:
            self.assertTrue(output.ready.wait(2))
            challenge=output.rows[0]['challenge']
            ack={'event':'pc_preflight_ack','session_id':'a'*32,
                 'challenge': ('b'*32 if wrong else challenge), 'inventory_age_s':4.0}
            os.write(write_fd, (json.dumps(ack)+'\n').encode())
            thread.join(2)
            self.assertFalse(thread.is_alive())
            return session, failures
        finally:
            os.close(read_fd); os.close(write_fd)

    def test_handoff_includes_bounded_transit_margin(self):
        session, failures = self.handoff()
        self.assertEqual(failures, [])
        self.assertEqual(session['age_at_handoff_s'], 7.0)

    def test_wrong_challenge_rejected(self):
        _, failures = self.handoff(wrong=True)
        self.assertTrue(failures)
        self.assertIn('invalid_or_stale', str(failures[0]))


if __name__ == '__main__':
    unittest.main()
