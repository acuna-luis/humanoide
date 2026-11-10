#!/usr/bin/env python3
"""Build a pre-execution verifier for the three streamed wrist processes.

The caller must obtain the expected digests and session from an independently
retained, verified candidate. This only validates the transported byte strings;
it does not attest the interpreter, its standard library, Docker, ROS or any
robot state, and it does not grant authority to move anything.
"""
import re
import textwrap


MAX_SOURCE_BYTES = 1_000_000
MAX_PAYLOAD_BYTES = 1_000_000


def build_bootstrap(source_size, sentinel, expected_source_sha256,
                    expected_payload_sha256, expected_session_id, *, role):
    """Return Python source that checks source and payload before compiling.

    Wire format: exactly ``source_size`` raw bytes, one framing LF, the exact
    ASCII sentinel and LF, then one UTF-8 JSON line. The already-read JSON line
    is replayed once to ``sys.stdin.readline()`` for the existing entrypoint.
    Further input remains unread at the underlying descriptor, including when
    a heartbeat arrives in the same kernel write as the JSON payload.

    ``role`` is host (session_id under ``session``), guard or worker (direct
    session_id). The verifier rejects duplicate JSON keys and non-finite JSON.
    The supplied expectation must itself come from the correct session and a
    verified source binding; self-derived hashes are not an attestation.
    """
    if type(source_size) is not int or not 0 < source_size <= MAX_SOURCE_BYTES:
        raise ValueError('invalid_source_size')
    if not isinstance(sentinel, str) or not re.fullmatch(r'[A-Z][A-Za-z0-9_]{7,127}', sentinel):
        raise ValueError('invalid_sentinel')
    for value in (expected_source_sha256, expected_payload_sha256):
        if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
            raise ValueError('invalid_expected_sha256')
    if not isinstance(expected_session_id, str) or not re.fullmatch(r'[0-9a-f]{32}', expected_session_id):
        raise ValueError('invalid_expected_session')
    if role not in ('host', 'guard', 'worker'):
        raise ValueError('invalid_stream_role')

    constants = {'source_size': source_size, 'sentinel': sentinel.encode('ascii'),
                 'source_sha256': expected_source_sha256,
                 'payload_sha256': expected_payload_sha256,
                 'session_id': expected_session_id, 'role': role,
                 'max_payload': MAX_PAYLOAD_BYTES}
    return 'CONFIG = ' + repr(constants) + '\n' + textwrap.dedent('''\
        import hashlib, json, os, sys

        def exact(count):
            chunks = []
            while count:
                block = os.read(0, min(count, 65536))
                if not block:
                    raise ValueError('incomplete_stream')
                chunks.append(block)
                count -= len(block)
            return b''.join(chunks)

        def one_line(limit):
            # Reading from the unbuffered FD avoids stranding future heartbeat
            # bytes inside a buffered stdin object accessed later via fileno().
            line = bytearray()
            while True:
                byte = os.read(0, 1)
                if not byte:
                    raise ValueError('incomplete_payload_line')
                if byte == b'\\n':
                    return bytes(line)
                line.extend(byte)
                if len(line) > limit:
                    raise ValueError('payload_too_large')

        def unique(pairs):
            obj = {}
            for key, value in pairs:
                if key in obj:
                    raise ValueError('duplicate_payload_key')
                obj[key] = value
            return obj

        def nonfinite(_):
            raise ValueError('nonfinite_payload')

        source = exact(CONFIG['source_size'])
        if exact(1) != b'\\n' or exact(len(CONFIG['sentinel']) + 1) != CONFIG['sentinel'] + b'\\n':
            raise ValueError('invalid_stream_sentinel')
        if hashlib.sha256(source).hexdigest() != CONFIG['source_sha256']:
            raise ValueError('source_digest_mismatch')
        payload = one_line(CONFIG['max_payload'])
        if hashlib.sha256(payload).hexdigest() != CONFIG['payload_sha256']:
            raise ValueError('payload_digest_mismatch')
        text = payload.decode('utf-8') + '\\n'
        row = json.loads(text, object_pairs_hook=unique, parse_constant=nonfinite)
        if not isinstance(row, dict):
            raise ValueError('payload_not_object')
        if CONFIG['role'] == 'host':
            session = row.get('session')
            observed = session.get('session_id') if isinstance(session, dict) else None
        else:
            observed = row.get('session_id')
        if observed != CONFIG['session_id']:
            raise ValueError('payload_session_mismatch')

        class ReplayStdin:
            def __init__(self, original, first):
                self.original, self.first = original, first
            def readline(self, size=-1):
                if self.first:
                    if size is None or size < 0:
                        result, self.first = self.first, ''
                    else:
                        result, self.first = self.first[:size], self.first[size:]
                    return result
                return self.original.readline(size)
            def fileno(self):
                return self.original.fileno()
            def __getattr__(self, name):
                return getattr(self.original, name)

        sys.stdin = ReplayStdin(sys.stdin, text)
        # The verified bundle entrypoint receives this tuple from the trusted
        # bootstrap only after both byte strings and the session were checked.
        # It is not authentication against a party controlling Python/SSH.
        __pico_verified_stream__ = (CONFIG['role'], CONFIG['session_id'],
                                    CONFIG['source_sha256'], CONFIG['payload_sha256'])
        exec(compile(source, '<verified-pico-stream>', 'exec'))
        ''')
