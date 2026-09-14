import unittest
from prove_entry_interface_boundaries import prove_boundary_box


class BoundaryProofTests(unittest.TestCase):
    def test_positive_function_entire_interval(self):
        r=prove_boundary_box(lambda q:1+q[0]**2,[-1],[1],[2])
        self.assertTrue(r['proved']);self.assertGreater(r['lower_bound_m'],0)
        self.assertLessEqual(r['lower_bound_m'],1)

    def test_center_contact_is_not_approved(self):
        self.assertFalse(prove_boundary_box(lambda q:abs(q[0]),[-1],[1],[1])['proved'])

    def test_budget_exhaustion_not_approved(self):
        self.assertFalse(prove_boundary_box(lambda q:.01,[-1],[1],[1],max_nodes=1)['proved'])

    def test_invalid_input_rejected(self):
        with self.assertRaises(ValueError):prove_boundary_box(lambda q:1,[1],[-1],[1])


if __name__=='__main__':unittest.main()
