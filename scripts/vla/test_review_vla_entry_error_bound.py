import copy
import unittest

import numpy as np

from review_vla_entry_error_bound import scene_objects, validate_refinement_scene


class SceneScenarioTests(unittest.TestCase):
    def test_translate_both_solids_without_changing_size_or_input(self):
        source = {'table': [[.1, -.5, .7], [1., .5, .8]],
                  'box': [[.3, -.2, .8], [.7, .2, 1.1]]}
        before = copy.deepcopy(source)
        original = scene_objects(source)
        lowered = scene_objects(source, -20.)
        self.assertEqual(source, before)
        for a, b in zip(original, lowered):
            self.assertEqual(a['size_m'], b['size_m'])
            self.assertEqual(a['id'], b['id'])
            np.testing.assert_allclose(np.subtract(b['center_m'], a['center_m']), [0, 0, -.02], atol=1e-15)
        self.assertAlmostEqual(lowered[1]['center_m'][2]-lowered[0]['center_m'][2],
                               original[1]['center_m'][2]-original[0]['center_m'][2])

    def test_invalid_offset_or_scene_rejected(self):
        valid = {'box': [[0, 0, 0], [1, 1, 1]]}
        for value in (float('nan'), float('inf'), -float('inf')):
            with self.assertRaises(ValueError): scene_objects(valid, value)
        for source in ({}, [], {'x': [[0, 0, 0], [0, 1, 1]]}, {'x': [[0, 0, 0], [1, 1, float('nan')]]}):
            with self.assertRaises(ValueError): scene_objects(source, -20.)

    def test_old_report_only_matches_original_scene(self):
        validate_refinement_scene({}, 0.)
        with self.assertRaises(ValueError): validate_refinement_scene({}, -20.)

    def test_translated_report_must_match_exact_offset(self):
        validate_refinement_scene({'scene_z_offset_mm': -20.}, -20.)
        for value in (0., -19., float('nan')):
            with self.assertRaises(ValueError):
                validate_refinement_scene({'scene_z_offset_mm': value}, -20.)


if __name__ == '__main__':
    unittest.main()
