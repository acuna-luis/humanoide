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
import pico_wrist_review_binding as binding


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
    def test_controlled_pc_sources_exist_and_are_readable(self):
        sources = launcher.controlled_pc_sources()
        self.assertIn('estop_reader', sources)
        self.assertIn('review_binding', sources)
        self.assertTrue(all(isinstance(raw, bytes) and raw for raw, _ in sources.values()))

    def test_run_blocked_before_file_or_network(self):
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('must not read')), \
             patch.object(launcher.subprocess, 'Popen', side_effect=AssertionError('must not connect')):
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(launcher.main(['--run', '--physical-confirmed']), 2)

    def test_binding_is_checked_before_passive_robot_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root/'manifest.json'; manifest.write_bytes(b'{}')
            urdf = root/'robot.urdf'; urdf.write_bytes(b'<robot/>\r\n')
            transmissions = root/'sps.yaml'; transmissions.write_bytes(b'transmissions: {}\n')
            review = root/'review.txt'; review.write_text('Technical review; no motion approval.\n')
            retained = root/'binding'
            with patch.object(binding.probe, 'validate', return_value={}):
                result = binding.create(retained, manifest, urdf, transmissions, review)
            args = ['--check', '--binding', str(retained), '--binding-sha256', result['binding_sha256'],
                    '--manifest', str(manifest), '--urdf', str(urdf), '--transmissions', str(transmissions)]
            with patch.object(launcher.passive, 'main', return_value=0) as passive, \
                 contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(launcher.main(args), 0)
                passive.assert_called_once()
                self.assertIn('BINDING_BYTES_MATCH', output.getvalue())
            urdf.write_bytes(b'<robot/>\n')  # Same logical XML, different bytes.
            with patch.object(launcher.passive, 'main', side_effect=AssertionError('must not connect')), \
                 contextlib.redirect_stderr(io.StringIO()) as error:
                self.assertEqual(launcher.main(args), 1)
                self.assertIn('candidate_input_changed', error.getvalue())
            with patch.object(launcher.passive, 'main', side_effect=AssertionError('must not connect')), \
                 contextlib.redirect_stderr(io.StringIO()) as error:
                self.assertEqual(launcher.main(['--check', '--binding', str(retained)]), 1)
                self.assertIn('binding_digest_and_all_candidate_inputs_required', error.getvalue())

    def test_future_run_path_rejects_changed_binding_before_preflight_or_ssh(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root/'manifest.json'; manifest.write_bytes(b'{}')
            urdf = root/'robot.urdf'; urdf.write_bytes(b'<robot/>')
            transmissions = root/'sps.yaml'; transmissions.write_bytes(b'transmissions: {}')
            review = root/'review.txt'; review.write_text('Review with unresolved physical gates.\n')
            retained = root/'binding'
            with patch.object(binding.probe, 'validate', return_value={}):
                result = binding.create(retained, manifest, urdf, transmissions, review)
                manifest.write_bytes(b'{ }')  # Still JSON, but not the reviewed bytes.
                with patch.object(launcher.arm, 'physical_release_gate'), \
                     patch.object(launcher.passive.existing, 'preflight', side_effect=AssertionError('must not connect')), \
                     patch.object(launcher.subprocess, 'Popen', side_effect=AssertionError('must not connect')):
                    with self.assertRaisesRegex(ValueError, 'candidate_input_changed:manifest.json'):
                        launcher.run_candidate(manifest, urdf, transmissions, True,
                            binding_path=retained, binding_sha256=result['binding_sha256'])

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
            self.assertEqual(index['review_status'], 'not_reviewed')
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
