#!/usr/bin/env python3
"""Offline regression tests for unqualified motor-space target hypotheses."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import prepare_ball_candidate_targets as subject
import prepare_ball_observations as observations


class CandidateTargetsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / 'capture'
        (self.source / 'rgb').mkdir(parents=True)
        self.names = [f'L_test_{i}_joint' for i in range(13)] + subject.JOINTS
        self.reductions = [-1, 1, 1, -1, 1, -1, 1]
        self.state = [0.0] * 20
        self.cmd = [0.0] * 13 + [0.1] * 7
        hand = {'name': subject.RIGHT_HAND, 'position': [0.0]*7}
        raw = [
            {'kind': 'joints', 'source_ns': 1_000_000_000,
             'message': {'name': self.names, 'position': self.state}},
            {'kind': 'actuators', 'source_ns': 1_000_000_000,
             'message': {'act_item': [{'name': j.replace('_joint', '_motor'), 'cmd_pos': 0.1} for j in subject.JOINTS]}},
            {'kind': 'hand_right', 'source_ns': 1_000_000_000, 'message': hand},
            {'kind': 'hand_command_right', 'source_ns': 1_000_000_000,
             'message': {'names': subject.RIGHT_HAND, 'mode': [5]*7}},
        ]
        (self.source/'samples.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in raw))
        rows = []
        for n, stamp in [(1, 1_010_000_000), (2, 1_200_000_000), (3, 1_250_000_000)]:
            (self.source/'rgb'/f'{n:06}.png').write_bytes(f'pixels{n}'.encode())
            rows.append({'png_file': f'rgb/{n:06}.png', 'image_source_ns': stamp,
                'state20': self.state, 'actuator_cmd_pos20': self.cmd, 'hand_right': hand,
                'source_lines': {'joints': 1, 'actuators': 2, 'hand_right': 3}})
        (self.source/'aligned.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rows))
        (self.source/'manifest.json').write_text(json.dumps({'joint_names': self.names}))
        (self.source/'quality.json').write_text(json.dumps({'capture_checks_passed': False, 'training_ready': False}))
        self.update_checksums()
        spec = self.root/'spec.json'
        spec.write_text(json.dumps({'segments': [
            {'id': 'candidate', 'source_dir': str(self.source), 'start_frame': 1, 'end_frame': 2,
             'status': 'candidate_success', 'notes': 'visual candidate', 'split': 'inspection_train'},
            {'id': 'assisted', 'source_dir': str(self.source), 'start_frame': 3, 'end_frame': 3,
             'status': 'assisted', 'notes': 'human assistance', 'split': 'inspection_train'}]}))
        self.obs = self.root/'obs'
        observations.export(spec, self.obs, 80)
        entries = {}
        for name, reduction in zip(subject.JOINTS, self.reductions):
            entries[name] = {'type': 'SimpleTransmission',
                'actuator': {'name': name.replace('_joint', '_motor'), 'mechanicalReduction': reduction},
                'joint': {'name': name, 'offset': 0.0, 'limit': {'lower': -1, 'upper': 1}}}
        text = subject.yaml.safe_dump({'transmissions': entries}, sort_keys=True)
        transmission_hash = hashlib.sha256(text.encode()).hexdigest()
        self.snapshot = self.root/'snapshot.json'
        self.snapshot.write_text(json.dumps({'/test/ecat_hardware/transmissions.yaml':
            {'text': text, 'sha256': transmission_hash}}))
        self.patcher_a = patch.object(subject, 'SNAPSHOT_SHA256', observations.digest(self.snapshot))
        self.patcher_b = patch.object(subject, 'TRANSMISSIONS_SHA256', transmission_hash)
        self.patcher_a.start(); self.patcher_b.start()

    def tearDown(self):
        self.patcher_b.stop(); self.patcher_a.stop(); self.tmp.cleanup()

    def update_checksums(self):
        files = sorted(p for p in self.source.rglob('*') if p.is_file() and p.name != 'SHA256SUMS')
        (self.source/'SHA256SUMS').write_text(''.join(
            f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(self.source)}\n' for p in files))

    def test_transforms_motor_commands_and_never_state_or_unknown(self):
        out = self.root/'candidate_bundle'
        m = subject.prepare(self.obs, self.snapshot, out)
        self.assertFalse(m['training_ready'])
        self.assertFalse(m['physical_control_qualified'])
        self.assertEqual([s['id'] for s in m['segments']], ['candidate'])
        self.assertEqual(m['excluded_non_candidate_segments'], [{'id': 'assisted', 'status': 'assisted'}])
        self.assertEqual(m['experimental_target8_order'], subject.JOINTS + ['grasp_hold_intent_candidate'])
        rows = [json.loads(x) for x in (out/'candidate'/'candidate_targets.jsonl').read_text().splitlines()]
        self.assertEqual(rows[0]['experimental_joint_target7'], [-0.1, 0.1, 0.1, -0.1, 0.1, -0.1, 0.1])
        self.assertNotEqual(rows[0]['experimental_joint_target7'], rows[0]['state20'][-7:])
        self.assertEqual(rows[0]['experimental_hand_label'], 0)
        self.assertIsNone(rows[1]['experimental_hand_label'])
        self.assertIsNone(rows[1]['experimental_target8'])
        self.assertEqual(rows[0]['actuator_source_ns'], 1_000_000_000)
        self.assertEqual(m['segments'][0]['max_image_gap_ms'], 190.0)
        self.assertEqual(m['segments'][0]['unknown_hand_labels'], 1)
        self.assertNotIn('action', rows[0])
        with self.assertRaisesRegex(ValueError, 'new directory'):
            subject.prepare(self.obs, self.snapshot, out)

    def test_rejects_historical_snapshot_tampering(self):
        self.snapshot.write_text(self.snapshot.read_text()+' ')
        with self.assertRaisesRegex(ValueError, 'snapshot checksum'):
            subject.prepare(self.obs, self.snapshot, self.root/'out')
        self.assertFalse((self.root/'out').exists())

    def test_rejects_mismatched_input_observation_hash(self):
        f = self.obs/'candidate'/'observations.jsonl'
        f.write_text(f.read_text().replace('0.1', '0.2', 1))
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            subject.prepare(self.obs, self.snapshot, self.root/'out')
        self.assertFalse((self.root/'out').exists())

    def test_rejects_source_capture_split_leak(self):
        f = self.obs/'manifest.json'
        data = json.loads(f.read_text())
        data['segments'][1]['split'] = 'inspection_test'
        f.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'different inspection splits'):
            subject.prepare(self.obs, self.snapshot, self.root/'out')
        self.assertFalse((self.root/'out').exists())

    def test_rejects_edited_source_and_input_overlap(self):
        (self.source/'samples.jsonl').write_text('modified\n')
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            subject.prepare(self.obs, self.snapshot, self.root/'out')
        with self.assertRaisesRegex(ValueError, 'overlap input'):
            subject.prepare(self.obs, self.snapshot, self.obs/'out')


if __name__ == '__main__':
    unittest.main()
