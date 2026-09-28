"""Real local pipes, synthetic workers; no robot, ROS or network."""
import sys
import unittest

from scripts.box_handling.scenario1_session import ProcessSession


WORKER = '''import json,sys,os
print(json.dumps({'event':'session_ready','request_id':None}),flush=True)
for line in sys.stdin:
    value=json.loads(line)
    ident=value['request_id']
    if value.get('wrong_id'):ident='unrelated'
    if value.get('fail'):
        print(json.dumps({'event':'error','request_id':ident,'reason':'synthetic failure'}),flush=True)
    else:
        print(json.dumps({'event':'result','request_id':ident,'pid':os.getpid()}),flush=True)
    print(json.dumps({'event':'request_complete','request_id':ident,'returncode':78 if value.get('fail') else 0}),flush=True)
'''


class SessionTest(unittest.TestCase):
    def session(self):
        return ProcessSession([sys.executable, '-u', '-B', '-c', WORKER], lambda event: None)

    def test_reuses_process_and_correlates_two_independent_requests(self):
        channel = self.session()
        try:
            first = channel.call({}, timeout=2)[0]
            second = channel.call({}, timeout=2)[0]
            self.assertEqual(first['pid'], second['pid'])
            self.assertNotEqual(first['request_id'], second['request_id'])
        finally:
            channel.close()
        self.assertEqual(channel.process.returncode, 0)

    def test_failure_is_latched_and_preserves_reason(self):
        channel = self.session()
        try:
            with self.assertRaisesRegex(RuntimeError, 'synthetic failure'):
                channel.call({'fail': True}, timeout=2)
            with self.assertRaisesRegex(RuntimeError, 'SESSION_FAILED'):
                channel.call({}, timeout=2)
            self.assertEqual(channel.sequence, 1)
        finally:
            channel.close()

    def test_unrelated_response_cannot_satisfy_a_new_request(self):
        channel = self.session()
        try:
            with self.assertRaisesRegex(RuntimeError, 'REQUEST_MISMATCH'):
                channel.call({'wrong_id': True}, timeout=2)
            self.assertTrue(channel.failed)
        finally:
            channel.close()

    def test_close_preserves_terminal_evidence_received_after_failure(self):
        events = []
        worker = WORKER+'''print(json.dumps({'event':'interrupted_terminal','request_id':'1','status':6}),flush=True)
'''
        channel = ProcessSession([sys.executable, '-u', '-B', '-c', worker], events.append)
        with self.assertRaises(RuntimeError):
            channel.call({'wrong_id': True}, timeout=2)
        channel.close()
        self.assertTrue(channel.failed)
        self.assertTrue(any(e['event'] == 'interrupted_terminal' for e in events))
        self.assertTrue(any(e['event'] == 'worker_closed' for e in events))


if __name__ == '__main__':
    unittest.main()
