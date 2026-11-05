import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from demo import frame_exception_code


class FrameErrorTests(unittest.TestCase):
    def test_matching_code_does_not_hide_inference_failure(self):
        self.assertEqual(frame_exception_code("MATCH", [{"component": "perception"}]), "APP2_PROCESSING_ERROR")

    def test_no_read_remains_distinct_from_a_diagnostic_failure(self):
        self.assertEqual(frame_exception_code("NO_READ", []), "APP2_NO_READ")
        self.assertEqual(frame_exception_code("NO_READ", [{"component": "diagnostic"}]), "APP2_PROCESSING_ERROR")
