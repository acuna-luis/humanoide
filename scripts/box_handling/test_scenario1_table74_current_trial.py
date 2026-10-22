"""Current table74 approach-only immutable contract tests; no robot clients."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from scripts.box_handling import scenario1_table74_current_trial as trial


SNAPSHOT = Path(__file__).resolve().parents[2]/'vendor/ubtech/cruzr_s2/snapshot_20260916/motion'


def reference():
    return dict(version=1, mode='operator_assumed_vendor45', source_checkpoint_sha256='a'*64,
                surface_height_m=.74, reference_surface_height_m=.45, scope='current_held_put1_only',
                evidence='Explicit current operator assumption; not a measured calibration.')


def sources():
    return ((SNAPSHOT/'tasks/wrc_cruzr/put_cruzr_wrc_low.xml').read_text(),
            (SNAPSHOT/'meta_clamp/wrc/put_cruzr_wrc_low.yaml').read_text())


def bundle():
    return trial.build_bundle(reference(), *sources())


class CurrentTable74Tests(unittest.TestCase):
    def test_exact_phase_nominal_values_and_no_qualification(self):
        b = bundle()
        self.assertEqual(trial.validate_bundle(b), b)
        review = b['review']
        self.assertEqual(review['phase'], 'approach_vendor_reference')
        self.assertEqual(review['first_hand_absolute_z_m'], .94)
        self.assertEqual(review['nominal_precontact_clearance_m'], .20)
        self.assertEqual(review['nominal_target_box_bottom_above_floor_m'], .94)
        self.assertEqual(review['reference_kind'], 'operator_assumption_not_measurement')
        self.assertEqual(review['physical_validation'], 'pending')
        for key in ('automatic_execution_authorized', 'installed', 'integrated_in_optimistic',
                    'measured_calibration_created', 'support_confirmed', 'pin_disengagement_confirmed'):
            self.assertIs(review[key], False)

    def test_exact_yaml_whitelist_preserves_every_other_source_byte(self):
        original_xml, original_yaml = sources(); b = bundle()
        expected = original_yaml
        for y in ('0.285', '-0.285'):
            expected = expected.replace('position: [0.75, '+y+', 0.65]', 'position: [0.75, '+y+', 0.94]')
        expected = expected.replace('position: [0.0, 0.0, -0.20]', 'position: [0.0, 0.0, 0.0]')
        candidate = b['tasks'][trial.META_ROOT+b['task_name']+'.yaml']
        self.assertEqual(candidate, expected)
        self.assertEqual(candidate.count('position: [0.0, 0.0, 0.0]'), 3)
        self.assertIn('box_size: [0.6, 0.4, 0.28]', candidate)
        self.assertIn('position: [0.20, 0.0, 0.0]', candidate)
        self.assertIn('position: [0.30, 0, 1.2]', candidate)
        self.assertIn('collision_detect: true', candidate)
        self.assertIn('enable_admit: true', candidate)
        for x in ('admit_param:', 'task_stack:', 'collision_data:'):
            self.assertIn(x, candidate)

    def test_one_metaclamp_only_and_source_identity_hashes(self):
        b = bundle(); name = b['task_name']
        xml = b['tasks'][trial.TASK_ROOT+name+'.xml']
        actions = ET.fromstring(xml).findall('.//Action')
        self.assertEqual([a.attrib for a in actions], [dict(ID='MetaClamp', name=name)])
        self.assertNotIn('open_arm', xml)
        self.assertNotIn('home', xml)
        self.assertEqual(b['manifest']['robot_files'], dict(trial.DEPENDENCIES, **{
            path: hashlib.sha256(content.encode()).hexdigest() for path,content in b['tasks'].items()}))
        self.assertEqual(b['manifest']['dependencies'], trial.DEPENDENCIES)
        self.assertTrue(name.startswith('local_table74_current/'))
        self.assertTrue(name.endswith('_approach'))

    def test_source_checkpoint_and_evidence_are_part_of_immutable_identity(self):
        first = bundle()
        for field, value in (('source_checkpoint_sha256', 'b'*64), ('evidence', 'Another current explicit source assumption')):
            changed = reference(); changed[field] = value
            second = trial.build_bundle(changed, *sources())
            self.assertNotEqual(first['task_name'], second['task_name'])

    def test_wrong_reference_modes_dimensions_types_and_extra_flags_rejected(self):
        for key, value in (('mode', 'measured'), ('surface_height_m', .695),
                           ('reference_surface_height_m', .90), ('source_checkpoint_sha256', 'a'*63),
                           ('version', True), ('surface_height_m', True), ('surface_height_m', float('nan')),
                           ('scope', 'any_grasp'), ('evidence', '')):
            r = reference(); r[key] = value
            with self.subTest(key=key,value=value), self.assertRaises(ValueError): trial.build_bundle(r, *sources())
        r = reference(); r['physical_validation'] = 'completed'
        with self.assertRaises(ValueError): trial.build_bundle(r, *sources())

    def test_vendor_source_changes_rejected_before_candidate(self):
        xml, yaml = sources()
        for x, y in ((xml+'\n', yaml), (xml, yaml.replace('enable_admit: true', 'enable_admit: false'))):
            with self.assertRaises(ValueError): trial.build_bundle(reference(), x, y)

    def test_rehashed_trajectory_force_torso_opening_and_claim_changes_rejected(self):
        for old, new in (('position: [0.75, 0.285, 0.94]', 'position: [0.76, 0.285, 0.94]'),
                         ('position: [0.0, 0.0, 0.0]', 'position: [0.0, 0.0, -0.20]'),
                         ('enable_admit: true', 'enable_admit: false'),
                         ('position: [0.30, 0, 1.2]', 'position: [0.40, 0, 1.2]'),
                         ('duration: 12.0', 'duration: 13.0'),
                         ('box_size: [0.6, 0.4, 0.28]', 'box_size: [0.603, 0.397, 0.22]')):
            b = bundle(); path = trial.META_ROOT+b['task_name']+'.yaml'
            self.assertIn(old, b['tasks'][path]); b['tasks'][path] = b['tasks'][path].replace(old, new, 1)
            b['manifest']['robot_files'][path] = trial.sha256(b['tasks'][path])
            with self.subTest(old=old), self.assertRaises(ValueError): trial.validate_bundle(b)
        for mutate in (lambda b: b['review'].update(physical_validation='completed'),
                       lambda b: b['review'].update(nominal_precontact_clearance_m=.05),
                       lambda b: b['dependencies'].update({trial.META_CLAMP_PATH:'b'*64})):
            b = bundle(); mutate(b)
            with self.assertRaises(ValueError): trial.validate_bundle(b)

    def test_in_memory_validation_has_no_file_or_native_dependency(self):
        b = bundle()
        # Reconstruct the same namespace as the remote bootstrap, without
        # __file__, package machinery, native libraries or source YAML reads.
        code = Path(trial.__file__).read_text()
        namespace = {'__name__': 'scenario1_table74_current_trial_memory', '__package__': None}
        import sys
        from scripts.box_handling import scenario1_deposit
        from unittest.mock import patch
        with patch.dict(sys.modules, {'scenario1_deposit': scenario1_deposit}):
            exec(compile(code, '<memory-current-table74>', 'exec'), namespace)
        original = copy.deepcopy(b)
        self.assertEqual(namespace['validate_bundle'](b), b)
        self.assertEqual(b, original)

    def test_cli_writes_only_new_local_artifacts_and_refuses_overwrite(self):
        import contextlib
        import io
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder); src = base/'reference.json'; output = base/'candidate'
            src.write_text(json.dumps(reference()))
            with contextlib.redirect_stdout(io.StringIO()) as captured:
                self.assertEqual(trial.main(['--reference', str(src), '--output', str(output)]), 0)
            self.assertEqual(json.loads(captured.getvalue())['status'], 'PREPARED_LOCALLY_NOT_INSTALLED_OR_EXECUTED')
            candidate = json.loads((output/'bundle.json').read_text())
            self.assertEqual(trial.validate_bundle(candidate), candidate)
            self.assertEqual(set(p.name for p in output.iterdir()),
                             {'bundle.json', 'review.json', *(Path(p).name for p in candidate['tasks'])})
            before = {p.name:p.read_bytes() for p in output.iterdir()}
            with self.assertRaises(FileExistsError):
                trial.main(['--reference', str(src), '--output', str(output)])
            self.assertEqual(before, {p.name:p.read_bytes() for p in output.iterdir()})


if __name__ == '__main__':
    unittest.main()
