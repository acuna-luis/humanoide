#!/usr/bin/env python3
"""Synthetic tests, no robot or external processes."""
import unittest
import numpy as np
from audit_clamp_photo_correspondence import fit_homography, hypotheses


class PhotoCorrespondenceTests(unittest.TestCase):
    def test_known_projective_mapping(self):
        source = np.array([[0,0],[1,0],[1,1],[0,1],[.2,.3],[.8,.7]])
        h = np.array([[2,.1,4], [.2,3,5], [.03,.02,1]])
        p = np.column_stack([source,np.ones(6)]) @ h.T
        result = fit_homography(source, p[:,:2]/p[:,2,None])
        self.assertLess(result['max_fit_px'], 1e-10)

    def test_threefold_pattern_retains_multiple_hypotheses(self):
        angles = np.radians([10,40,130,160,250,280])
        source = np.column_stack([np.cos(angles), np.sin(angles)])
        result = hypotheses(source, source*100+[450,650])
        self.assertEqual(len(result),12)
        self.assertGreaterEqual(sum(r['rms_fit_px'] < 1e-8 for r in result), 3)

    def test_bad_inputs_rejected(self):
        for points in (np.zeros((6,2)), np.full((6,2),np.nan), np.zeros((3,2))):
            with self.assertRaises(ValueError):
                fit_homography(points,points)


if __name__ == '__main__':
    unittest.main()
