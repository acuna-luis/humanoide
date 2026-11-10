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
import prepare_pico_wrist_native_probe as probe
from test_prepare_pico_wrist_native_probe import state, urdf, transmissions
import test_prepare_ball_native_arm_step as model_fixture
import prepare_ball_native_arm_step as model
from audit_ball_arm_proposals import MODEL_SHA256


class VerifiedPcLoaderTests(unittest.TestCase):
    def create_model_binding(self, root):
        root = Path(root)
        row, _, options = model_fixture.NativeArmDraftTests().paired_case()
        row.update(event='prediction', image_sha256='a'*64, physical_control_qualified=False)
        row['prediction'][6] += .1
        row['proposed_minus_observed_rad'][6] += .1
        candidate = model.model_wrist_candidate(row, verified_model_sha256=MODEL_SHA256, **options)
        artifact = root/'artifact'
        receipt = model.save_model_wrist_artifact(artifact, candidate, options['urdf_text'],
                                                   options['transmissions_text'])
        (root/'review').write_text('Test review: no physical dispatch.')
        bound = root/'bound'
        info = binding.create(bound, artifact/'manifest.json', artifact/'robot.urdf',
                              artifact/'transmissions.yaml', root/'review',
                              model_artifact=artifact, model_receipt_sha256=receipt['receipt_sha256'])
        return bound, info['binding_sha256']

    def test_model_binding_retains_evidence_and_run_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory, digest = self.create_model_binding(tmp)
            self.assertIn('model_wrist_evidence', binding.verify(directory, digest))
            checked = self.invoke(directory, digest)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            result = subprocess.run([sys.executable, '-I', '-B', str(Path(loader.__file__).resolve()),
                        '--run', '--physical-confirmed', '--binding', str(directory),
                        '--binding-sha256', digest], capture_output=True, text=True, timeout=15)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('model_wrist_dispatch_not_enabled', result.stderr)

    def test_model_tamper_fails_even_with_recomputed_hashes(self):
        for mutation in ('prediction', 'joint_order', 'target'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                directory, _ = self.create_model_binding(tmp)
                decision_path = directory/'decision.json'
                decision = json.loads(decision_path.read_bytes())
                if mutation == 'prediction':
                    decision['model_action_original'][6] -= .2
                elif mutation == 'joint_order':
                    decision['applied_arm_joint_order'].reverse()
                else:
                    decision['applied_arm_target_rad'][0] += .01
                decision_path.write_text(json.dumps(decision))
                receipt_path = directory/'receipt.json'
                receipt = json.loads(receipt_path.read_bytes())
                receipt['sha256']['decision.json'] = hashlib.sha256(decision_path.read_bytes()).hexdigest()
                receipt_path.write_text(json.dumps(receipt))
                binding_path = directory/'review-binding.json'
                meta = json.loads(binding_path.read_bytes())
                meta['model_wrist_evidence']['decision_sha256'] = hashlib.sha256(decision_path.read_bytes()).hexdigest()
                meta['model_wrist_evidence']['receipt_sha256'] = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
                binding_path.write_text(json.dumps(meta))
                digest = hashlib.sha256(binding_path.read_bytes()).hexdigest()
                result = self.invoke(directory, digest)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('model_wrist_projection_mismatch', result.stderr)
                with self.assertRaises(ValueError):
                    binding.verify(directory, digest)
    def test_model_binding_rejects_receipt_or_candidate_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory, digest = self.create_model_binding(tmp)
            altered_urdf = Path(tmp)/'altered.urdf'
            altered_urdf.write_text('<robot/>')
            artifact = Path(tmp)/'artifact'
            receipt_digest = hashlib.sha256((artifact/'receipt.json').read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, 'model_candidate_input_changed'):
                binding.create(Path(tmp)/'other', artifact/'manifest.json', altered_urdf,
                               artifact/'transmissions.yaml', Path(tmp)/'review',
                               model_artifact=artifact, model_receipt_sha256=receipt_digest)
            self.assertFalse((Path(tmp)/'other').exists())
            (directory/'receipt.json').write_bytes(b'{}')
            self.assertNotEqual(self.invoke(directory, digest).returncode, 0)
            with self.assertRaises(ValueError):
                binding.verify(directory, digest)
    def test_valid_isolated_context_reaches_mock_preflight_without_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'manifest').write_text(json.dumps(probe.prepare(state(), urdf(), transmissions())))
            (root/'urdf').write_text(urdf())
            (root/'sps').write_text(transmissions())
            (root/'review').write_text('Test fixture; no robot access.')
            bound = root/'bound'
            info = binding.create(bound, root/'manifest', root/'urdf', root/'sps', root/'review')
            script = r'''
import importlib.util,sys
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('trusted_bootstrap',sys.argv[1]);boot=importlib.util.module_from_spec(spec);spec.loader.exec_module(boot)
modules,files,index_raw,binding_raw=boot.checked_snapshot(sys.argv[2],sys.argv[3],include_artifacts=True)
with boot.verified_pc_environment(modules,artifacts=(files,index_raw,binding_raw)) as (entry,finder):
 entry.EVIDENCE=Path(sys.argv[4])/'evidence'
 context={'finder':finder,'files':files,'index_raw':index_raw,'binding_raw':binding_raw}
 with patch.object(entry.arm,'physical_release_gate'), \
      patch.object(entry.passive.existing,'preflight',side_effect=RuntimeError('MOCK_PREFLIGHT_REACHED')), \
      patch('subprocess.Popen',side_effect=AssertionError('no_process')), \
      patch('socket.socket.connect',side_effect=AssertionError('no_network')):
  sys.meta_path.remove(finder)
  try:
   try: entry.run_candidate(None,None,None,True,binding_path=Path(sys.argv[2]),binding_sha256=sys.argv[3],verified_pc=context)
   except RuntimeError as e: assert str(e)=='verified_pc_context_required',str(e)
   else: raise AssertionError('inactive_finder_accepted')
  finally: sys.meta_path.insert(0,finder)
  fake=dict(context,finder=object())
  try: entry.run_candidate(None,None,None,True,binding_path=Path(sys.argv[2]),binding_sha256=sys.argv[3],verified_pc=fake)
  except RuntimeError as e: assert str(e)=='verified_pc_context_required',str(e)
  else: raise AssertionError('wrong_finder_accepted')
  try: entry.run_candidate(Path(sys.argv[2])/'manifest.json',Path(sys.argv[2])/'robot.urdf',Path(sys.argv[2])/'transmissions.yaml',True,binding_path=Path(sys.argv[2]),binding_sha256=sys.argv[3],verified_pc=context)
  except RuntimeError as e: assert str(e)=='MOCK_PREFLIGHT_REACHED',str(e)
  else: raise AssertionError('missing_preflight')
'''
            result = subprocess.run([sys.executable,'-I','-B','-c',script,
                str(Path(loader.__file__).resolve()),str(bound),info['binding_sha256'],str(root)],
                capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)

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
        def environment(_modules, *, artifacts=None):
            active.append(True)
            try:
                yield entrypoint, object()
            finally:
                active.pop()
        with patch.object(loader, 'checked_snapshot', return_value=({}, {}, b'index', b'binding')), \
             patch.object(loader, 'verified_pc_environment', environment):
            rc = loader.main(['--run', '--physical-confirmed', '--binding', '/bound',
                              '--binding-sha256', 'a'*64])
        self.assertEqual(rc, 1)
        args, kwargs = entrypoint.run_candidate.call_args
        self.assertEqual(args[:4], (Path('/bound/manifest.json'), Path('/bound/robot.urdf'),
                                    Path('/bound/transmissions.yaml'), True))
        self.assertEqual(kwargs['binding_path'], Path('/bound'))
        self.assertEqual(kwargs['binding_sha256'], 'a'*64)
        self.assertEqual(kwargs['verified_pc']['index_raw'], b'index')
        self.assertEqual(kwargs['verified_pc']['binding_raw'], b'binding')
        self.assertEqual(active, [])

    def test_invalid_bound_candidate_rejects_before_network(self):
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
            self.assertIn('invalid_bundle_input', result.stderr)
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
