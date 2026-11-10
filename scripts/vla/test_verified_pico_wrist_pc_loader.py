"""Pinned PC import check; no ROS, robot access, goal or movement."""
import hashlib
import importlib.machinery
import json
import contextlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from unittest.mock import Mock

import pico_wrist_review_binding as binding
import verified_pico_wrist_pc_loader as loader


class VerifiedPcLoaderTests(unittest.TestCase):
    def create_binding(self, root):
        root = Path(root)
        for name, data in (('manifest', '{}'), ('urdf', '<robot/>'),
                           ('sps', 'transmissions: {}'), ('review', 'Technical review.')):
            (root/name).write_text(data, encoding='utf-8')
        with patch.object(binding.probe, 'validate', return_value={}):
            result = binding.create(root/'bound', root/'manifest', root/'urdf', root/'sps', root/'review')
        return root/'bound', result['binding_sha256']

    def invoke(self, directory, digest):
        return subprocess.run([sys.executable, '-I', '-B', str(Path(loader.__file__).resolve()),
                               '--check', '--binding', str(directory), '--binding-sha256', digest],
                              capture_output=True, text=True, timeout=15)

    def test_imports_real_pc_modules_from_bound_bytes_with_no_motion(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory, digest = self.create_binding(tmp)
            result = self.invoke(directory, digest)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report['status'], 'VERIFIED_PC_IMPORT_ONLY')
            self.assertFalse(report['physical_control_qualified'])
            self.assertEqual(report['movement_commands'], 0)
            for name in ('run_pico_wrist_native_trial', 'check_arm_from_pico_supervised',
                         'head_from_pico_check', 'pico_cc_mode',
                         'arm_from_pico_supervised', 'pico_wrist_docker_launcher',
                         'pico_wrist_review_binding'):
                self.assertIn(name, report['modules_loaded'])

    def test_tampered_module_is_rejected_before_its_side_effect(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory, digest = self.create_binding(tmp)
            marker = Path(tmp)/'must-not-exist'
            path = directory/'pc-source-head_admission'
            path.write_bytes(b'open(' + repr(str(marker)).encode() + b',"w").write("executed")\n')
            result = self.invoke(directory, digest)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('bundle_evidence_changed:pc-source-head_admission', result.stderr)
            self.assertFalse(marker.exists())

    def test_forged_index_and_binding_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory, digest = self.create_binding(tmp)
            index_path = directory/'bundle-evidence.json'
            index = json.loads(index_path.read_bytes())
            index['sha256']['pc-source-trial_launcher'] = '0'*64
            index_path.write_text(json.dumps(index))
            result = self.invoke(directory, digest)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('bundle_evidence_index_changed', result.stderr)
            result = self.invoke(directory, '0'*64)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('review_binding_changed', result.stderr)

    def test_unbound_project_import_is_rejected(self):
        finder = loader.VerifiedFinder({})
        spec = importlib.machinery.ModuleSpec('unbound', None,
                    origin=str(loader.ROOT/'scripts/vla/unbound.py'))
        with patch.object(importlib.machinery.PathFinder, 'find_spec', return_value=spec):
            with self.assertRaisesRegex(ImportError, 'unbound_project_module:unbound'):
                finder.find_spec('unbound')

    def test_finder_remains_active_for_late_project_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory, digest = self.create_binding(tmp)
            script = r'''
import importlib, importlib.util, sys
spec = importlib.util.spec_from_file_location('trusted_bootstrap', sys.argv[1])
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)
modules = bootstrap.checked_snapshot(sys.argv[2], sys.argv[3])
with bootstrap.verified_pc_environment(modules) as (launcher, finder):
    assert finder in sys.meta_path
    name = 'pico_wrist_native_stage'
    assert name not in sys.modules
    late = importlib.import_module(name)
    assert late.__loader__ is finder
    assert name in finder.loaded
assert finder not in sys.meta_path
'''
            result = subprocess.run([sys.executable, '-I', '-B', '-c', script,
                                     str(Path(loader.__file__).resolve()), str(directory), digest],
                                    capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_run_requires_explicit_physical_report_before_reading_binding(self):
        result = subprocess.run([sys.executable, '-I', '-B', str(Path(loader.__file__).resolve()),
                                 '--run', '--binding', '/does-not-exist', '--binding-sha256', 'bad'],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 2)
        self.assertIn('requires current operator-reported physical conditions', result.stderr)

    def test_run_passes_binding_paths_and_keeps_import_context_active(self):
        active = []
        entrypoint = Mock()
        def blocked(*args, **kwargs):
            self.assertEqual(active, [True])
            raise RuntimeError('physical_dispatch_blocked')
        entrypoint.run_candidate.side_effect = blocked
        @contextlib.contextmanager
        def environment(_modules):
            active.append(True)
            try:
                yield entrypoint, object()
            finally:
                active.pop()
        with patch.object(loader, 'checked_snapshot', return_value={}), \
             patch.object(loader, 'verified_pc_environment', environment):
            rc = loader.main(['--run', '--physical-confirmed', '--binding', '/bound',
                              '--binding-sha256', 'a'*64])
        self.assertEqual(rc, 1)
        args, kwargs = entrypoint.run_candidate.call_args
        self.assertEqual(args[:4], (Path('/bound/manifest.json'), Path('/bound/robot.urdf'),
                                    Path('/bound/transmissions.yaml'), True))
        self.assertEqual(kwargs, {'binding_path': Path('/bound'), 'binding_sha256': 'a'*64})
        self.assertEqual(active, [])

    def test_real_run_hits_closed_gate_without_starting_a_process_or_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory, digest = self.create_binding(tmp)
            script = r'''
import importlib.util
import sys
from unittest.mock import patch
spec = importlib.util.spec_from_file_location('trusted_bootstrap', sys.argv[1])
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)
with patch('subprocess.Popen', side_effect=AssertionError('process_started')), \
     patch('socket.socket.connect', side_effect=AssertionError('network_started')), \
     patch('socket.create_connection', side_effect=AssertionError('network_started')):
    code = bootstrap.main(['--run', '--physical-confirmed', '--binding', sys.argv[2],
                           '--binding-sha256', sys.argv[3]])
assert code == 1
'''
            result = subprocess.run([sys.executable, '-I', '-B', '-c', script,
                                     str(Path(loader.__file__).resolve()), str(directory), digest],
                                    capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('physical_dispatch_blocked', result.stderr)
            self.assertNotIn('process_started', result.stderr)
            self.assertNotIn('network_started', result.stderr)

    def test_bootstrap_file_mismatch_fails_before_module_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory, digest = self.create_binding(tmp)
            # Preserve the index and binding consistency while pinning a loader
            # snapshot that differs from the currently executing bootstrap.
            source = directory/'pc-source-verified_pc_loader'
            source.write_bytes(source.read_bytes() + b'\n# changed\n')
            index_path = directory/'bundle-evidence.json'
            index = json.loads(index_path.read_bytes())
            index['sha256'][source.name] = hashlib.sha256(source.read_bytes()).hexdigest()
            index_raw = (json.dumps(index, sort_keys=True, indent=2)+'\n').encode()
            index_path.write_bytes(index_raw)
            binding_path = directory/'review-binding.json'
            obj = json.loads(binding_path.read_bytes())
            obj['bundle_evidence_sha256'] = hashlib.sha256(index_raw).hexdigest()
            raw = (json.dumps(obj, sort_keys=True, indent=2)+'\n').encode()
            binding_path.write_bytes(raw)
            result = self.invoke(directory, hashlib.sha256(raw).hexdigest())
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('bootstrap_file_changed', result.stderr)

    def test_missing_bound_artifact_fails_even_with_matching_new_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory, _ = self.create_binding(tmp)
            index_path = directory/'bundle-evidence.json'
            index = json.loads(index_path.read_bytes())
            del index['sha256']['bundle-guard.py']
            index_raw = (json.dumps(index, sort_keys=True, indent=2)+'\n').encode()
            index_path.write_bytes(index_raw)
            binding_path = directory/'review-binding.json'
            obj = json.loads(binding_path.read_bytes())
            obj['bundle_evidence_sha256'] = hashlib.sha256(index_raw).hexdigest()
            raw = (json.dumps(obj, sort_keys=True, indent=2)+'\n').encode()
            binding_path.write_bytes(raw)
            result = self.invoke(directory, hashlib.sha256(raw).hexdigest())
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('bundle_evidence_file_set_changed', result.stderr)

    def test_origin_alias_with_dotdot_is_rejected_before_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory, _ = self.create_binding(tmp)
            index_path = directory/'bundle-evidence.json'
            index = json.loads(index_path.read_bytes())
            name = 'arm_from_pico_supervised'
            original = index['source_origins'][name]
            index['source_origins'][name] = original.replace('/runtime/', '/runtime/../runtime/')
            index_raw = (json.dumps(index, sort_keys=True, indent=2)+'\n').encode()
            index_path.write_bytes(index_raw)
            binding_path = directory/'review-binding.json'
            obj = json.loads(binding_path.read_bytes())
            obj['bundle_evidence_sha256'] = hashlib.sha256(index_raw).hexdigest()
            raw = (json.dumps(obj, sort_keys=True, indent=2)+'\n').encode()
            binding_path.write_bytes(raw)
            result = self.invoke(directory, hashlib.sha256(raw).hexdigest())
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('source_origin_not_exact:', result.stderr)

    def test_origin_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root/'real').mkdir()
            (root/'real'/'module.py').write_text('pass\n')
            (root/'alias').symlink_to(root/'real', target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'source_origin_not_exact'):
                loader._exact_origin(str(root/'alias'/'module.py'), root, 'alias/module.py')


if __name__ == '__main__':
    unittest.main()
