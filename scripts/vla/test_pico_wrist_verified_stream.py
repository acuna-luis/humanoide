"""Exercise verified streamed bootstrap locally; no network, Docker or ROS."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pico_wrist_verified_stream as verified


SESSION = '1' * 32
SENTINEL = 'PICO_SOURCE_END_' + '2' * 32
SOURCE = (b'import json,os,sys\n'
          b'p=json.loads(sys.stdin.readline())\n'
          b'print("VERIFIED_ENTRY",p.get("session_id",p.get("session",{}).get("session_id")),flush=True)\n'
          b'print("NEXT="+os.read(sys.stdin.fileno(),64).decode(),flush=True)\n')


def h(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(row):
    return json.dumps(row, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')


def invoke(role='worker', *, source=SOURCE, expected_source=SOURCE, payload=None,
           expected_payload=None, session=SESSION, sentinel_line=None, tail=b'heartbeat\n'):
    if payload is None:
        payload = encoded({'session': {'session_id': SESSION}} if role == 'host'
                          else {'session_id': SESSION, 'name': 'muñeca'})
    if expected_payload is None:
        expected_payload = payload
    bootstrap = verified.build_bootstrap(len(expected_source), SENTINEL, h(expected_source),
                                         h(expected_payload), session, role=role)
    wire = source + b'\n' + (sentinel_line if sentinel_line is not None
                             else SENTINEL.encode() + b'\n') + payload + b'\n' + tail
    return subprocess.run([sys.executable, '-B', '-c', bootstrap], input=wire,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)


class VerifiedStreamTests(unittest.TestCase):
    def test_all_three_roles_replay_payload_and_preserve_future_fd_bytes(self):
        for role in ('host', 'guard', 'worker'):
            with self.subTest(role=role):
                result = invoke(role)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(('VERIFIED_ENTRY ' + SESSION).encode(), result.stdout)
                self.assertIn(b'NEXT=heartbeat\n', result.stdout)

    def test_changed_source_never_runs_even_when_sentinel_is_present(self):
        altered = SOURCE.replace(b'VERIFIED_ENTRY', b'COMPROMISED___', 1)
        self.assertEqual(len(altered), len(SOURCE))
        result = invoke(source=altered)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(b'COMPROMISED___', result.stdout)
        self.assertIn(b'source_digest_mismatch', result.stderr)

    def test_changed_payload_never_runs_source(self):
        expected = encoded({'session_id': SESSION, 'task': 'a'})
        altered = encoded({'session_id': SESSION, 'task': 'b'})
        result = invoke(payload=altered, expected_payload=expected)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(b'VERIFIED_ENTRY', result.stdout)
        self.assertIn(b'payload_digest_mismatch', result.stderr)

    def test_matching_digest_does_not_override_wrong_session(self):
        payload = encoded({'session_id': 'f' * 32})
        result = invoke(payload=payload)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(b'VERIFIED_ENTRY', result.stdout)
        self.assertIn(b'payload_session_mismatch', result.stderr)

    def test_host_requires_nested_session(self):
        result = invoke('host', payload=encoded({'session_id': SESSION}))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'payload_session_mismatch', result.stderr)

    def test_invalid_or_truncated_sentinel_never_runs(self):
        for sentinel in (SENTINEL.encode() + b'X\n', SENTINEL.encode()):
            with self.subTest(sentinel=sentinel):
                result = invoke(sentinel_line=sentinel, tail=b'')
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn(b'VERIFIED_ENTRY', result.stdout)
                self.assertTrue(b'invalid_stream_sentinel' in result.stderr or
                                b'incomplete_stream' in result.stderr)

    def test_duplicate_keys_rejected_even_when_payload_digest_matches(self):
        payload = ('{"session_id":"' + SESSION + '","session_id":"' + SESSION + '"}').encode()
        result = invoke(payload=payload)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(b'VERIFIED_ENTRY', result.stdout)
        self.assertIn(b'duplicate_payload_key', result.stderr)

    def test_missing_payload_lf_fails_without_running_code(self):
        payload = encoded({'session_id': SESSION})
        bootstrap = verified.build_bootstrap(len(SOURCE), SENTINEL, h(SOURCE), h(payload),
                                             SESSION, role='worker')
        result = subprocess.run([sys.executable, '-B', '-c', bootstrap],
                                input=SOURCE+b'\n'+SENTINEL.encode()+b'\n'+payload,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(b'VERIFIED_ENTRY', result.stdout)
        self.assertIn(b'incomplete_payload_line', result.stderr)

    def test_untrusted_bootstrap_parameters_are_rejected(self):
        for kwargs in ({'source_size': True}, {'source_size': 0},
                       {'expected_source_sha256': '0'*63},
                       {'expected_payload_sha256': 'G'*64},
                       {'expected_session_id': 'z'*32}, {'sentinel': 'x\ncode'},
                       {'role': 'controller'}):
            args = dict(source_size=len(SOURCE), sentinel=SENTINEL,
                        expected_source_sha256=h(SOURCE), expected_payload_sha256=h(b'{}'),
                        expected_session_id=SESSION, role='worker')
            args.update(kwargs)
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                verified.build_bootstrap(**args)


if __name__ == '__main__':
    unittest.main()
