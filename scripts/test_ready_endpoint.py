import copy
import unittest
import numpy as np
import audit_ready_endpoint as audit


class EndpointTests(unittest.TestCase):
    def test_same_endpoint(self):
        contract = audit.endpoint_contract()
        audit.require_same_endpoint(contract, copy.deepcopy(contract))

    def test_changes_rejected(self):
        contract = audit.endpoint_contract()
        for key in ('head_command_order', 'arms_vendor_order', 'waist_command_order'):
            altered = copy.deepcopy(contract)
            altered[key][0] += .01
            with self.assertRaises(ValueError):
                audit.require_same_endpoint(contract, altered)

    def test_head_hold_rejected(self):
        contract = audit.endpoint_contract()
        altered = copy.deepcopy(contract)
        altered['head_command_order'] = [0., 0.]
        with self.assertRaises(ValueError):
            audit.require_same_endpoint(contract, altered)

    def test_crossing_and_separated(self):
        a = np.array([[0.,0,0],[4,0,0],[0,4,0]])
        b = np.array([[1.,1,-1],[1,1,1],[2,1,1]])
        self.assertTrue(audit.independent_crossing(a, b))
        self.assertFalse(audit.independent_crossing(a, b+10))


if __name__ == '__main__':
    unittest.main()
