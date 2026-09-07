import unittest
import numpy as np
import clamp_work_model as model


class ClampModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.joints, cls.boxes, cls.meshes, cls.profile = model.load()

    def test_historical_grippers_removed_only(self):
        removed = self.profile['removed_historical_links']
        self.assertEqual(set(removed), {s+'_'+n+'_link' for s in ('L','R')
                                      for n in ('pgc_base','finger1','finger2')})
        for n in removed:
            self.assertNotIn(n, self.boxes)
            self.assertNotIn(n, self.meshes)
        for s in ('L','R'):
            self.assertIn(s+'_sixforce_link', self.boxes)
            self.assertIn(s+'_wrist_pitch_link', self.meshes)

    def test_dimensions_and_missing_registration(self):
        for tool in self.profile['tools'].values():
            lo, hi = np.asarray(tool['descriptive_envelope']['bounds_m'])
            np.testing.assert_allclose(hi-lo, [.082,.100,.130])
            self.assertIsNone(tool['translation_m'])
            self.assertIsNone(tool['rotation_matrix'])
            self.assertFalse(tool['world_geometry_available'])
        self.assertFalse(self.profile['collision_coverage_complete'])
        self.assertFalse(self.profile['physical_authorized'])

    def test_remaining_tree_resolves(self):
        q = {j['name']:0. for j in self.joints if j['type'] != 'fixed'}
        poses = model.fk.forward_kinematics(self.joints,q)
        self.assertTrue(set(self.boxes).issubset(poses))


if __name__ == '__main__':
    unittest.main()
