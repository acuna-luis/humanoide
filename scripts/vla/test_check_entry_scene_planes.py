import unittest
import numpy as np
from check_entry_scene_planes import compare_patches, decode_points


class ScenePlaneTests(unittest.TestCase):
    def test_common_translation_cancels_but_floor_bias_does_not(self):
        rng = np.random.default_rng(93)
        xy = rng.uniform(-.3, .3, (100, 2))
        xyz = np.concatenate([np.column_stack([xy, np.full(100, h)]) for h in (.8, 0., .04)])
        uv = np.concatenate([rng.uniform([i*100, 0], [i*100+20, 20], (100, 2)) for i in range(3)])
        annotations = dict(known_table_height_m=.8, patches={name:dict(polygon_uv=[[i*100-1, -1], [i*100+21, -1], [i*100+21, 21], [i*100-1, 21]]) for i, name in enumerate(('table', 'floor1', 'floor2'))})
        a = compare_patches(uv, xyz, annotations)
        b = compare_patches(uv, xyz+[1., -2., 4.], annotations)
        self.assertAlmostEqual(a['height_spread_m'], .04)
        np.testing.assert_allclose(a['inferred_height_minus_known_m'], b['inferred_height_minus_known_m'], atol=1e-12)
        self.assertFalse(a['total_error_bound_established'])

    def test_incomplete_capture_rejected(self):
        with self.assertRaises(ValueError):
            decode_points(dict(capture_complete=False))


if __name__ == '__main__':
    unittest.main()
