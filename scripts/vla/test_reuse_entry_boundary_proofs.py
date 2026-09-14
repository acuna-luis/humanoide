import unittest
import numpy as np
from reuse_entry_boundary_proofs import domain_contains


def domain(lo, hi, joints=('a',)):
    return dict(controlling_joints=list(joints), domain_lower_rad=lo, domain_upper_rad=hi)


class DomainReuseTests(unittest.TestCase):
    def test_exact_domain_and_subset(self):
        outer = domain([-1.], [1.])
        self.assertTrue(domain_contains(outer, outer))
        self.assertTrue(domain_contains(outer, domain([0.], [.5])))

    def test_one_ulp_extension_requires_new_proof(self):
        self.assertFalse(domain_contains(domain([-1.], [1.]),
                                        domain([-1.], [np.nextafter(1., np.inf)])))

    def test_joint_order_is_not_interchangeable(self):
        self.assertFalse(domain_contains(domain([-1., -1.], [1., 1.], ('a', 'b')),
                                        domain([-1., -1.], [1., 1.], ('b', 'a'))))

    def test_invalid_domains_raise(self):
        for invalid in (domain([np.nan], [1.]), domain([2.], [1.]), domain([], [1.])):
            with self.assertRaises(ValueError):
                domain_contains(domain([-1.], [1.]), invalid)


if __name__ == '__main__':
    unittest.main()
