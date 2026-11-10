"""Candidate launcher source and closed-gate tests; no SSH or robot actions."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import run_pico_wrist_native_trial as launcher


def execute_streamed(source, payload):
    sentinel = 'FAKE_SOURCE_END'
    bootstrap = ('import sys\nparts=[]\nfor line in sys.stdin:\n'
                 ' if line.rstrip("\\n")=='+repr(sentinel)+': break\n'
                 ' parts.append(line)\n'
                 'exec(compile("".join(parts),"<source>","exec"))\n')
    return subprocess.run([sys.executable,'-B','-c',bootstrap],
        input=source+'\n'+sentinel+'\n'+json.dumps(payload)+'\n',
        text=True,capture_output=True,timeout=10)


class LauncherTests(unittest.TestCase):
    def test_run_blocked_before_file_or_network(self):
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('must not read')), \
             patch.object(launcher.subprocess, 'Popen', side_effect=AssertionError('must not connect')):
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(launcher.main(['--run', '--physical-confirmed']), 2)

    def test_bundles_compile_and_guard_has_independent_cancel_mode(self):
        host, guard, worker = launcher.source_bundle()
        for name, source in (('host',host),('guard',guard),('worker',worker)):
            compile(source, '<'+name+'>', 'exec')
        self.assertIn('guard_can_cancel=True', guard)

    def test_evidence_retains_exact_bundles_inputs_and_rejects_overwrite(self):
        host, guard, worker, sources = launcher.source_bundle(include_sources=True)
        with tempfile.TemporaryDirectory() as tmp:
            outdir = Path(tmp)
            digest = launcher.retain_bundle_evidence(outdir, sources, host, guard, worker,
                                                     b'{"a":1}\n', b'URDF\r\n', b'YAML\n')
            raw = (outdir/'bundle-evidence.json').read_bytes()
            index = json.loads(raw)
            self.assertEqual(digest, hashlib.sha256(raw).hexdigest())
            self.assertFalse(index['review_attested'])
            self.assertEqual((outdir/'robot.urdf').read_bytes(), b'URDF\r\n')
            for name, expected in index['sha256'].items():
                self.assertEqual(hashlib.sha256((outdir/name).read_bytes()).hexdigest(), expected)
            self.assertEqual((outdir/'bundle-host.py').read_text(), host)
            launcher.verify_bundle_evidence(outdir, digest)
            (outdir/'bundle-guard.py').write_text('changed')
            with self.assertRaisesRegex(RuntimeError, 'bundle_evidence_changed'):
                launcher.verify_bundle_evidence(outdir, digest)
            with self.assertRaises(FileExistsError):
                launcher.retain_bundle_evidence(outdir, sources, host, guard, worker,
                                                b'other', b'other', b'other')

    def test_host_stream_rejects_before_docker(self):
        host, _, _ = launcher.source_bundle()
        child = execute_streamed(host, {})
        self.assertNotEqual(child.returncode,0)
        self.assertIn('BRIDGE_READY',child.stdout)
        self.assertIn('physical_dispatch_blocked',child.stderr)

    def test_worker_stream_reports_blocked_result_without_goal(self):
        _, _, worker = launcher.source_bundle()
        child = execute_streamed(worker, {'session_id':'a'*32})
        rows=[json.loads(line) for line in child.stdout.splitlines()]
        self.assertEqual(child.returncode,2)
        self.assertIn('worker_error',[x.get('event') for x in rows])
        self.assertEqual(rows[-1],{'event':'worker_result','returncode':2})
        self.assertNotIn('dispatched',[x.get('event') for x in rows])


if __name__ == '__main__':
    unittest.main()
