#!/usr/bin/env python3
"""Local tests for the isolated experiment runner; no GPU or external calls."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import train_offline as subject


class OfflineRunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        target = self.root / 'lerobot_dataset/meta/info.json'
        target.parent.mkdir(parents=True)
        self.names = [f'joint_{i}' for i in range(27)]
        self.actions = [f'joint_{i}' for i in range(7)] + ['grasp']
        info = {'fps': 2, 'total_episodes': 1, 'features': {
            'observation.state': {'shape': [27], 'names': self.names},
            'action': {'shape': [8], 'names': self.actions},
            'observation.images.camera1': {'shape': [3, 576, 960]}}}
        target.write_text(json.dumps(info), encoding='utf-8')
        self.manifest = {'schema': 'cruzr_ball_lerobot_offline_experiment_v1',
            'offline_experiment_only': True, 'training_ready': False,
            'physical_control_qualified': False, 'not_authorized_for_hub_upload_or_robot_execution': True,
            'fps': 2, 'segments': [{'status': 'candidate_success', 'split': 'inspection_train'}],
            'action_names': self.actions, 'state_names': self.names,
            'output_sha256': {'lerobot_dataset/meta/info.json': hashlib.sha256(target.read_bytes()).hexdigest()}}
        self.save_manifest()

    def tearDown(self):
        self.tmp.cleanup()

    def save_manifest(self):
        (self.root / 'manifest.json').write_text(json.dumps(self.manifest), encoding='utf-8')

    def test_dataset_integrity_and_contract(self):
        self.assertEqual(subject.verify_dataset(self.root)['fps'], 2)
        self.manifest['physical_control_qualified'] = True
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, 'unqualified offline'):
            subject.verify_dataset(self.root)

    def test_tampered_or_escaping_data_rejected(self):
        self.manifest['output_sha256']['lerobot_dataset/meta/info.json'] = '0' * 64
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, 'checksum'):
            subject.verify_dataset(self.root)
        self.manifest['output_sha256'] = {'../outside': '0' * 64}
        self.save_manifest()
        with self.assertRaises((ValueError, FileNotFoundError)):
            subject.verify_dataset(self.root)

    def test_invalid_segment_rejected(self):
        self.manifest['segments'][0]['status'] = 'assisted'
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, 'unexpected training'):
            subject.verify_dataset(self.root)

    def test_model_hashing_rejects_symlinks_outside_mount(self):
        model = self.root / 'model'
        model.mkdir()
        (model / 'config.json').write_text('{}', encoding='utf-8')
        self.assertEqual(subject.model_files(model)['config.json'], hashlib.sha256(b'{}').hexdigest())
        outside = self.root / 'outside'
        outside.write_text('private', encoding='utf-8')
        (model / 'escape').symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'escapes'):
            subject.model_files(model)

    def test_tokenizer_override_preserves_normalizer_and_local_path(self):
        calls = []
        def original(*args, **kwargs):
            calls.append((args, kwargs))
            return 'ok'
        wrapped = subject.with_local_tokenizer(original, Path('/models/vlm'))
        self.assertEqual(wrapped(policy_cfg='cfg', pretrained_path='/models/base',
            preprocessor_overrides={'normalizer_processor': {'stats': 'current'}}), 'ok')
        overrides = calls[0][1]['preprocessor_overrides']
        self.assertEqual(overrides['tokenizer_processor']['tokenizer_name'], '/models/vlm')
        self.assertEqual(overrides['normalizer_processor']['stats'], 'current')
        with self.assertRaisesRegex(ValueError, 'pre-existing tokenizer'):
            wrapped(preprocessor_overrides={'tokenizer_processor': {}})


if __name__ == '__main__':
    unittest.main()
