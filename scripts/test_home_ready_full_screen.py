import unittest
from unittest.mock import patch
import numpy as np
import audit_home_ready_full_screen as audit


class WaypointTests(unittest.TestCase):
    def test_round_trip(self):
        points = audit.stages()
        self.assertEqual(len(points), 7)
        for k in range(3):
            np.testing.assert_array_equal(points[k], points[-1-k])

    def test_staging_mapping(self):
        point = audit.stages()[1]
        self.assertEqual(np.flatnonzero(point).tolist(), [1, 8])
        self.assertEqual(point[1], -.6)

    def test_wrong_goal_dimensions_rejected(self):
        with patch.object(audit.yaml, 'safe_load', return_value={'request': {'goals': [[0.]]}}):
            with self.assertRaises(ValueError):
                audit.stages()


if __name__ == '__main__':
    unittest.main()
