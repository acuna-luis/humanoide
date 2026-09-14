import unittest
from runtime.entry410_single_stage_remote import stop_cadence_ready


class CadenceTests(unittest.TestCase):
    def test_recent_single_value_is_not_a_heartbeat(self):
        self.assertFalse(stop_cadence_ready([]))
        self.assertFalse(stop_cadence_ready([100.]))

    def test_observed_vendor_cadence_accepted(self):
        self.assertTrue(stop_cadence_ready([5213.106936941, 5217.604407488, 5222.099553668]))

    def test_compatible_cadence(self):
        self.assertTrue(stop_cadence_ready([100., 101., 102.]))

    def test_invalid_or_regressed_clock(self):
        for sample in (float('nan'), float('inf'), 99.):
            with self.assertRaises(RuntimeError):
                stop_cadence_ready([100., sample])


if __name__ == '__main__':
    unittest.main()
