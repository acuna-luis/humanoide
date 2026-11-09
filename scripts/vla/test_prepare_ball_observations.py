#!/usr/bin/env python3
"""Offline tests of observational export; no robot APIs."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import prepare_ball_observations as subject


class BallObservationsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        (self.source / 'rgb').mkdir(parents=True)
        self.write('manifest.json', {'task': 'ball', 'training_ready': False})
        self.write('quality.json', {'capture_checks_passed': False, 'training_ready': False})
        hand = {'name': subject.RIGHT_HAND, 'position': [0.0] * 7}
        frames = [{'png_file': f'rgb/{n:06}.png', 'image_source_ns': 1_000_000_000 + n*10_000_000,
                   'state20': [0.0] * 20, 'hand_right': hand} for n in (1, 2)]
        (self.source / 'aligned.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in frames))
        for n in (1, 2):
            (self.source / 'rgb' / f'{n:06}.png').write_bytes(b'png-image-' + bytes([n]))
        samples = [self.command(1_005_000_000, 5), self.command(1_015_000_000, 7)]
        (self.source / 'samples.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in samples))
        self.checksums()
        self.spec = self.root / 'segments.json'
        self.spec.write_text(json.dumps({'segments': [{'id': 'demo', 'source_dir': str(self.source),
            'start_frame': 1, 'end_frame': 2, 'status': 'assisted', 'notes': 'human moves support'}]}))

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, value):
        (self.source / name).write_text(json.dumps(value))

    def command(self, stamp, mode):
        return {'kind': 'hand_command_right', 'source_ns': stamp,
                'message': {'mode': [mode]*7, 'names': subject.RIGHT_HAND}}

    def checksums(self):
        files = sorted(p for p in self.source.rglob('*') if p.is_file() and p.name != 'SHA256SUMS')
        (self.source / 'SHA256SUMS').write_text(''.join(
            f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(self.source)}\n' for p in files))

    def test_export_preserves_provenance_causality_and_no_action(self):
        out = self.root / 'output'
        manifest = subject.export(self.spec, out, 80)
        self.assertFalse(manifest['training_ready'])
        self.assertFalse(manifest['physical_control_qualified'])
        self.assertFalse(manifest['has_action_column'])
        self.assertEqual(manifest['segments'][0]['status'], 'assisted')
        self.assertEqual(manifest['segments'][0]['split'], 'unassigned')
        rows = [json.loads(s) for s in (out / 'demo' / 'observations.jsonl').read_text().splitlines()]
        self.assertEqual([r['right_hand_intent_candidate']['value'] for r in rows],
                         ['open_candidate', 'grasp_hold_candidate'])
        self.assertTrue(all(r['right_hand_intent_candidate']['provisional'] for r in rows))
        self.assertTrue(all('action' not in r for r in rows))
        self.assertEqual((out / 'demo' / 'rgb' / '000001.png').read_bytes(),
                         (self.source / 'rgb' / '000001.png').read_bytes())
        self.assertFalse(manifest['segments'][0]['source_capture_checks_passed'])
        with self.assertRaisesRegex(ValueError, 'already exists'):
            subject.export(self.spec, out, 80)

    def test_no_future_or_stale_label(self):
        commands = [(100, 1, [5]*7)]
        self.assertEqual(subject.latest_intent(commands, [100], 99, 1)['reason'], 'no_prior_command')
        self.assertEqual(subject.latest_intent(commands, [100], 2_000_100, 1)['reason'], 'prior_command_stale')

    def test_ambiguous_same_time_is_unknown(self):
        commands = [(100, 1, [5]*7), (100, 2, [7]*7)]
        self.assertEqual(subject.latest_intent(commands, [100, 100], 100, 1)['value'], 'unknown')

    def test_missing_state_or_changed_image_rejected_before_creating_output(self):
        (self.source / 'rgb' / '000001.png').write_bytes(b'corrupted')
        out = self.root / 'output'
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            subject.export(self.spec, out, 80)
        self.assertFalse(out.exists())

    def test_output_within_capture_and_bad_interval_rejected(self):
        with self.assertRaisesRegex(ValueError, 'source capture'):
            subject.export(self.spec, self.source / 'new', 80)
        spec = json.loads(self.spec.read_text())
        spec['segments'][0]['end_frame'] = 3
        self.spec.write_text(json.dumps(spec))
        with self.assertRaisesRegex(ValueError, 'missing aligned frame 3'):
            subject.export(self.spec, self.root / 'new', 80)

    def test_same_capture_cannot_cross_inspection_splits(self):
        spec = json.loads(self.spec.read_text())
        spec['segments'][0].update(start_frame=1, end_frame=1, split='inspection_train')
        spec['segments'].append({'id': 'other', 'source_dir': str(self.source),
            'start_frame': 2, 'end_frame': 2, 'status': 'unreviewed', 'notes': 'unknown',
            'split': 'inspection_test'})
        self.spec.write_text(json.dumps(spec))
        with self.assertRaisesRegex(ValueError, 'multiple inspection splits'):
            subject.export(self.spec, self.root / 'new', 80)
        self.assertFalse((self.root / 'new').exists())


if __name__ == '__main__':
    unittest.main()
