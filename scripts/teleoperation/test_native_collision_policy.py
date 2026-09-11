"""Tests of actual pinned machine-code tracing, never physical motion."""
import itertools
import os
from pathlib import Path
import tempfile
import unittest

from general_home.native_collision_policy import trace_group_pairs


class NativePolicyTests(unittest.TestCase):
    def test_unknown_binary_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp)/'unknown.so'
            binary.write_bytes(b'not an executable')
            with self.assertRaisesRegex(ValueError, 'hash'):
                trace_group_pairs(binary, 2)

    def test_group_count_validation_precedes_file_access(self):
        for count in (0, 17, -1, True, 1.5, '2'):
            with self.subTest(count=count), self.assertRaises(ValueError):
                trace_group_pairs('/absent', count)

    @unittest.skipUnless(os.environ.get('CRUZR_POLICY_LIBRARY'), 'Specify private archived librobot.so')
    def test_native_group_pairs(self):
        for count in (1, 2, 3, 4, 8, 16):
            with self.subTest(count=count):
                result = trace_group_pairs(os.environ['CRUZR_POLICY_LIBRARY'], count)
                expected = list(itertools.combinations(range(count), 2))
                self.assertEqual([tuple(p) for p in result['queried_group_pairs']], expected)
                self.assertEqual(result['host_native_calls'], 0)
                self.assertFalse(result['physical_approval'])
                self.assertTrue(result['distance_result_is_stubbed'])

    @unittest.skipUnless(os.environ.get('CRUZR_POLICY_LIBRARY'), 'Specify private archived librobot.so')
    def test_tampered_library_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            blob = bytearray(Path(os.environ['CRUZR_POLICY_LIBRARY']).read_bytes())
            blob[-1] ^= 1
            binary = Path(tmp)/'changed.so'
            binary.write_bytes(blob)
            with self.assertRaisesRegex(ValueError, 'hash'):
                trace_group_pairs(binary, 2)


if __name__ == '__main__':
    unittest.main()
