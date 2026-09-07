import unittest
from audit_timestamp_pairing import pair, stamp


def row(ns):
    return {'header': {'stamp': {'sec': ns // 10**9, 'nanosec': ns % 10**9}}}


class PairTests(unittest.TestCase):
    def test_bracket_and_clock_required(self):
        args = ([row(110)], [row(100), row(120)], 10)
        self.assertFalse(pair(*args)['pairs'][0]['temporal_pair_accepted'])
        self.assertTrue(pair(*args, clock_reference_verified=True)['pairs'][0]['temporal_pair_accepted'])
        self.assertFalse(pair([row(99)], args[1], 10, True)['pairs'][0]['temporal_pair_accepted'])

    def test_empty_far_and_invalid(self):
        self.assertIsNone(pair([row(100)], [], 10)['pairs'][0]['joint_index'])
        self.assertFalse(pair([row(110)], [row(100), row(120)], 9, True)['pairs'][0]['temporal_pair_accepted'])
        for values in ([row(120), row(100)], [row(100), row(100)]):
            with self.assertRaises(ValueError):
                pair([], values, 10)
        with self.assertRaises(ValueError):
            stamp(row(0))

    def test_observed_gap_not_accepted(self):
        result = pair([row(1788778414578540000)], [row(1788778413290172079)], 20_000_000)
        self.assertEqual(result['pairs'][0]['delta_ns'], -1288367921)
        self.assertFalse(result['pairs'][0]['temporal_pair_accepted'])
        self.assertFalse(result['physical_authorized'])


if __name__ == '__main__':
    unittest.main()
