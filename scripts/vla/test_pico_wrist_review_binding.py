"""Local review binding tests; no network, ROS or robot access."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pico_wrist_review_binding as subject


class ReviewBindingTests(unittest.TestCase):
    def create_binding(self, root):
        root = Path(root)
        manifest = root/'input.json'; manifest.write_text('{}')
        urdf = root/'robot.urdf'; urdf.write_bytes(b'<robot/>\r\n')
        transmissions = root/'transmissions.yaml'; transmissions.write_bytes(b'transmissions: {}\n')
        review = root/'review.txt'; review.write_text('Technical review: control remains blocked.\n')
        output = root/'binding'
        with patch.object(subject.probe, 'validate', return_value={}):
            result = subject.create(output, manifest, urdf, transmissions, review)
        return output, result

    def test_binding_retains_exact_bytes_and_never_qualifies_motion(self):
        with tempfile.TemporaryDirectory() as tmp:
            output, result = self.create_binding(tmp)
            self.assertFalse(result['physical_control_qualified'])
            self.assertFalse(result['reviewer_identity_authenticated'])
            self.assertFalse(result['loaded_runtime_or_firmware_verified'])
            self.assertEqual(result['movement_commands'], 0)
            self.assertEqual((output/'robot.urdf').read_bytes(), b'<robot/>\r\n')
            self.assertEqual(subject.verify(output, result['binding_sha256']), result)
            index = json.loads((output/'bundle-evidence.json').read_bytes())
            self.assertIn('pc-source-trial_launcher', index['sha256'])
            self.assertIn('source-arm_from_pico_supervised.py', index['sha256'])
            self.assertIn('bundle-guard.py', index['sha256'])

    def test_review_and_source_tampering_are_rejected(self):
        for changed in ('technical-review.txt', 'bundle-worker.py', 'pc-source-trial_launcher'):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as tmp:
                output, result = self.create_binding(tmp)
                (output/changed).write_text('changed')
                with self.assertRaises((ValueError, RuntimeError)):
                    subject.verify(output, result['binding_sha256'])

    def test_binding_digest_and_schema_are_enforced(self):
        with tempfile.TemporaryDirectory() as tmp:
            output, result = self.create_binding(tmp)
            with self.assertRaisesRegex(ValueError, 'review_binding_changed'):
                subject.verify(output, '0'*64)
            data = json.loads((output/'review-binding.json').read_bytes())
            data['physical_control_qualified'] = True
            raw = json.dumps(data).encode()
            (output/'review-binding.json').write_bytes(raw)
            with self.assertRaisesRegex(ValueError, 'invalid_review_binding'):
                subject.verify(output, hashlib.sha256(raw).hexdigest())
            with self.assertRaisesRegex(ValueError, 'expected_binding_sha256_required'):
                subject.verify(output, 'not-a-sha')

    def test_compare_current_detects_changed_source_or_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            output, result = self.create_binding(tmp)
            matching = subject.compare_current(output, result['binding_sha256'])
            self.assertTrue(matching['current_controlled_sources_match'])
            self.assertFalse(matching['physical_control_qualified'])
            current = subject.launcher.controlled_pc_sources()
            name = 'trial_launcher'
            changed = dict(current)
            changed[name] = (current[name][0] + b'\n# changed\n', current[name][1])
            with patch.object(subject.launcher, 'controlled_pc_sources', return_value=changed):
                with self.assertRaisesRegex(ValueError, 'current_controlled_source_changed:pc-source-trial_launcher'):
                    subject.compare_current(output, result['binding_sha256'])
            host, guard, worker, sources = subject.launcher.source_bundle(include_sources=True)
            with patch.object(subject.launcher, 'source_bundle', return_value=(host+'\n# changed', guard, worker, sources)):
                with self.assertRaisesRegex(ValueError, 'current_controlled_source_changed:bundle-host.py'):
                    subject.compare_current(output, result['binding_sha256'])
            changed.pop(name)
            with patch.object(subject.launcher, 'controlled_pc_sources', return_value=changed):
                with self.assertRaisesRegex(ValueError, 'current_controlled_source_set_changed'):
                    subject.compare_current(output, result['binding_sha256'])

    def test_candidate_inputs_must_match_the_bound_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            output, result = self.create_binding(tmp)
            values = [b'{}', b'<robot/>\r\n', b'transmissions: {}\n']
            checked = subject.compare_candidate_inputs(output, result['binding_sha256'], *values)
            self.assertTrue(checked['candidate_input_bytes_match'])
            self.assertFalse(checked['physical_control_qualified'])
            for index, expected_name in enumerate(('manifest.json', 'robot.urdf', 'transmissions.yaml')):
                modified = list(values)
                modified[index] += b'changed'
                with self.subTest(name=expected_name), self.assertRaisesRegex(ValueError, 'candidate_input_changed'):
                    subject.compare_candidate_inputs(output, result['binding_sha256'], *modified)

    def test_empty_review_or_overwrite_fails_without_robot_connection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ('manifest', 'urdf', 'sps'):
                (root/name).write_text('{}')
            review = root/'review'; review.write_text(' ')
            with patch.object(subject.probe, 'validate', return_value={}), \
                 patch('subprocess.Popen', side_effect=AssertionError('no subprocess allowed')):
                with self.assertRaisesRegex(ValueError, 'review_text_empty'):
                    subject.create(root/'out', root/'manifest', root/'urdf', root/'sps', review)
                self.assertFalse((root/'out').exists())
                review.write_text('Review with limitations.\n')
                subject.create(root/'out', root/'manifest', root/'urdf', root/'sps', review)
                with self.assertRaises(FileExistsError):
                    subject.create(root/'out', root/'manifest', root/'urdf', root/'sps', review)


if __name__ == '__main__':
    unittest.main()
