import copy
import unittest

from review_entry_fixture_hypotheses import padded_objects, profile_padding


class FixturePaddingTests(unittest.TestCase):
    def test_padding_preserves_pose_and_source(self):
        source = [dict(id='table', size_m=[.84, .838, .038], center_m=[.6, 0, .65], rpy_rad=[.1, 0, 0])]
        before = copy.deepcopy(source)
        padded = padded_objects(source, 20)
        self.assertEqual(source, before)
        self.assertAlmostEqual(padded[0]['size_m'][2], .078)
        self.assertEqual(padded[0]['center_m'], source[0]['center_m'])
        self.assertEqual(padded[0]['rpy_rad'], source[0]['rpy_rad'])

    def test_invalid_padding_rejected(self):
        for value in (-1, float('nan'), float('inf')):
            with self.assertRaises(ValueError): padded_objects([], value)

    def test_offline_profile_keeps_clearance_separate_from_registration(self):
        profile=dict(schema='cruzr-entry-scene-uncertainty-review-v1',
                     scope='OFFLINE_HYPOTHESIS_NOT_EXECUTION_CONFIGURATION',
                     physical_approval=False,uncertainty_bound_qualified=False,
                     minimum_geometric_clearance_mm=2.,scene_translation_allowance_mm=50.)
        self.assertEqual(profile_padding(profile),[50.])
        for key,value in [('physical_approval',True),('uncertainty_bound_qualified',True),
                          ('minimum_geometric_clearance_mm',0),('scene_translation_allowance_mm',-1)]:
            bad=dict(profile,**{key:value})
            with self.assertRaises(ValueError):profile_padding(bad)


if __name__ == '__main__': unittest.main()
