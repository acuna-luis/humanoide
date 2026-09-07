import copy
import json
import unittest
import xml.etree.ElementTree as ET

from build_clamp_simplified_model import ROOT, build, drawing
from audit_clamp_mount_requalification import evaluate


class SimplifiedModelTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads((ROOT/'config/clamp_mount_requalification.json').read_text())

    def test_dimensions_and_one_sided_tabs(self):
        model = build(self.contract)
        lo, hi = model['primitives'][0]['bounds_m']
        for actual, expected in zip(lo+hi, [-.035, -.055, .059, .035, .045, .095]):
            self.assertAlmostEqual(actual, expected)
        tab_hi = model['primitives'][1]['bounds_m'][1][0]
        self.assertAlmostEqual(tab_hi-lo[0], .082)

    def test_never_claim_full_tool_or_ros(self):
        model = build(self.contract)
        self.assertIsNone(model['primitives'][2]['bounds_m'])
        for key in ('physical_authorized', 'full_tool_containment_proven',
                    'ros_collision_export_allowed', 'manufacturer_clamp_cad_required'):
            self.assertIs(model[key], False)

    def test_partial_artifact_is_not_a_mount_contract(self):
        with self.assertRaises(ValueError):
            evaluate(build(self.contract))

    def test_incomplete_dimensions_rejected(self):
        for field in ('plate_width_m', 'axis_to_pad_face_m', 'plate_with_pads_thickness_m'):
            contract = copy.deepcopy(self.contract)
            contract['reported_dimensions'][field] = None
            with self.assertRaises(ValueError):
                build(contract)

    def test_svg_parseable_and_no_unknown_support_polygon(self):
        self.contract['reported_dimensions'].pop('total_tool_depth_from_pad_face_m', None)
        svg = drawing(build(self.contract))
        ET.fromstring(svg)
        self.assertIn('sin contorno', svg)
        self.assertIn('NO demuestra', svg)

    def test_total_depth_and_negative_rear_not_clipped(self):
        model = build(self.contract)
        self.assertEqual(model['status'], 'NOMINAL_TOOL_ENVELOPE_UNREGISTERED')
        lo, hi = model['nominal_full_tool_envelope']['bounds_m']
        for got, wanted in zip(lo+hi, [-.035, -.055, -.035, .047, .045, .095]):
            self.assertAlmostEqual(got, wanted)
        self.assertAlmostEqual(hi[2]-lo[2], .130)
        self.assertFalse(model['physical_authorized'])
        self.assertFalse(model['full_tool_containment_proven'])
        ET.fromstring(drawing(model))

    def test_no_containment_claim_means_no_total_envelope(self):
        for value in (False, None, 'true', 1):
            self.contract['reported_dimensions']['support_contained_in_reported_other_margins'] = value
            self.assertIsNone(build(self.contract)['nominal_full_tool_envelope'])

    def test_bad_total_depth_rejected(self):
        for value in (True, -.130, .020, float('nan'), float('inf')):
            self.contract['reported_dimensions']['total_tool_depth_from_pad_face_m'] = value
            with self.assertRaises(ValueError):
                build(self.contract)


if __name__ == '__main__':
    unittest.main()
