import unittest
import numpy as np
from entry_subdivided_scene_bounds import partition_bound


class PartitionTests(unittest.TestCase):
    def test_cover_both_halves_to_prove_positive_quadratic(self):
        def bound(q, h):
            return max(0., 1+q[0]**2-2*abs(q[0])*h[0]-h[0]**2)
        value, nodes, complete = partition_bound(bound, [0.], [1.], [1.])
        self.assertTrue(complete)
        self.assertGreater(nodes, 1)
        self.assertGreater(value, .002)
        self.assertLessEqual(value, 1.)

    def test_unclear_child_cannot_inherit_sibling_proof(self):
        value, nodes, complete = partition_bound(
            lambda q,h: 1. if q[0] < 0 else 0., [0.], [1.], [1.], max_nodes=20)
        self.assertFalse(complete)
        self.assertEqual(value, 0.)
        self.assertEqual(nodes, 20)

    def test_exhausted_budget_never_proves_parent(self):
        self.assertEqual(partition_bound(lambda q,h: 0., [0.], [1.], [1.], max_nodes=1),
                         (0., 1, False))

    def test_invalid_input_or_child_bound_rejected(self):
        for width in ([-1.], [np.nan]):
            with self.assertRaises(ValueError): partition_bound(lambda q,h: 1., [0.], width, [1.])
        with self.assertRaises(ValueError): partition_bound(lambda q,h: np.nan, [0.], [1.], [1.])


if __name__ == '__main__': unittest.main()
