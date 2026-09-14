import copy
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np

from entry410_stage_contract import load_stage, qualify, REQUIRED_EVIDENCE
from prepare_entry360_stages import JOINT_ORDER, staged_path, stage_xml
from prepare_vla_entry_bundle import digest


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); source = self.root/'source'; source.write_text('fixture')
        points, stages = staged_path(np.zeros(20), np.linspace(-.2, .2, 20))
        self.report = dict(schema='cruzr-entry410-stages-offline-v1', candidate='episode_000410',
                           joint_order=JOINT_ORDER, stages=stages, access_waypoints_20d_rad=[q.tolist() for q in points],
                           sources_sha256={str(source):digest(source)}, model_sources={str(source):digest(source)},
                           configured_limits_check=dict(configuration_files_match_current_hashes=True),
                           geometry_audit=dict(timed_out=False, pairs=[dict(pair=['hand', 'scene:table'], status='CERTIFIED_AFFINE_INTERVALS')]), drafts_sha256={})
        for i, stage in enumerate(stages, 1):
            for direction in ('forward', 'reverse'):
                name = f'DRAFT_{i:02d}_{stage["type"]}_{stage["location"]}_{direction}.xml'
                path = self.root/name; path.write_text(stage_xml(stage, direction == 'reverse'))
                self.report['drafts_sha256'][name] = digest(path)
        self.path = self.root/'review.json'; self.save()

    def save(self): self.path.write_text(json.dumps(self.report))

    def test_all_ten_stages_match_and_reverse_endpoints(self):
        for i in range(1, 6):
            a, b = (load_stage(self.path, i, direction) for direction in ('forward', 'reverse'))
            self.assertEqual(a['start'], b['end']); self.assertEqual(a['end'], b['start'])
            self.assertFalse(a['physical_approval'])

    def test_wrong_candidate_rejected(self):
        self.report['candidate'] = 'episode_000040'; self.save()
        with self.assertRaises(ValueError): load_stage(self.path, 1, 'forward')

    def test_modified_xml_even_with_rehashed_manifest_rejected(self):
        name = next(n for n in self.report['drafts_sha256'] if '01_' in n and 'forward' in n)
        path = self.root/name; path.write_text(path.read_text().replace('duration="', 'duration="9'))
        self.report['drafts_sha256'][name] = digest(path); self.save()
        with self.assertRaises(ValueError): load_stage(self.path, 1, 'forward')

    def test_unresolved_scene_rejected(self):
        self.report['geometry_audit']['pairs'][0]['status'] = 'UNRESOLVED'; self.save()
        with self.assertRaises(ValueError): load_stage(self.path, 1, 'forward')

    def test_changed_source_rejected(self):
        (self.root/'source').write_text('changed')
        with self.assertRaises(ValueError): load_stage(self.path, 1, 'forward')

    def test_skip_or_invalid_direction_rejected(self):
        for number, direction in ((0, 'forward'), (6, 'forward'), (True, 'forward'), (1, 'both')):
            with self.assertRaises(ValueError): load_stage(self.path, number, direction)

    def test_modified_duration_rejected(self):
        self.report['stages'][0]['duration_seconds'] += 1; self.save()
        with self.assertRaises(ValueError): load_stage(self.path, 1, 'forward')

    def test_boolean_release_is_not_evidence(self):
        release = self.root/'release.json'; release.write_text('{"authorized":true}')
        with self.assertRaises(ValueError): qualify(release, load_stage(self.path, 1, 'forward'))


if __name__ == '__main__': unittest.main()
