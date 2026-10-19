"""Identifier states must not turn uncertainty into a material or motion approval."""

from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from material import compare_codes, decode_codes


def code(value, **extra):
    return {"raw_value": value, "format": "QRCode", "position": [[0, 0], [10, 0], [10, 10], [0, 10]], **extra}


class MaterialContractTests(unittest.TestCase):
    def test_decoder_preserves_rgb_mode_instead_of_zxing_ndarray_bgr_default(self):
        import numpy as np
        captured = []
        decoder = SimpleNamespace(read_barcodes=lambda image: captured.append(image) or [])
        image = np.zeros((4, 6, 3), dtype=np.uint8)
        image[0, 0] = [255, 0, 0]
        with patch.dict(sys.modules, {"zxingcpp": decoder}):
            self.assertEqual(decode_codes(image), [])
        self.assertEqual(captured[0].mode, "RGB")
        self.assertEqual(captured[0].getpixel((0, 0)), (255, 0, 0))

    def test_matching_and_different_material_are_distinct(self):
        self.assertEqual(compare_codes([code("ITR-001")], "ITR-001", "piece")["result"], "MATCH")
        self.assertEqual(compare_codes([code("ITR-002")], "ITR-001", "piece")["result"], "MISMATCH")

    def test_comparison_is_exact_without_normalization(self):
        for observed in ("itr-001", " ITR-001", "ITR-001 ", "ITR-001\n"):
            self.assertEqual(compare_codes([code(observed)], "ITR-001", "piece")["result"], "MISMATCH")

    def test_no_read_and_unknown_expected_are_not_match(self):
        self.assertEqual(compare_codes([], "ITR-001", "piece")["result"], "NO_READ")
        self.assertEqual(compare_codes([code("ITR-001")], None, "piece")["result"], "UNKNOWN")
        self.assertEqual(compare_codes([code("ITR-001")], "ITR-001", "unconfirmed")["result"], "UNKNOWN")

    def test_multiple_distinct_labels_are_ambiguous_even_with_match(self):
        result = compare_codes([code("ITR-001"), code("ITR-002")], "ITR-001", "box")
        self.assertEqual(result["result"], "AMBIGUOUS")
        self.assertIsNone(result["recognized_material"])

    def test_duplicate_observations_do_not_create_ambiguity(self):
        result = compare_codes([code("ITR-001"), code("ITR-001", format="Code128")], "ITR-001", "lot")
        self.assertEqual(result["result"], "MATCH")
        self.assertFalse(result["piece_identity_verified"])
        self.assertEqual(result["identity_scope"], "lot")

    def test_invalid_observation_cannot_be_ignored_beside_valid_one(self):
        result = compare_codes([code("ITR-001"), code(None, decoding_error="payload_not_utf8")], "ITR-001", "piece")
        self.assertEqual(result["result"], "PROCESSING_ERROR")
        self.assertTrue(result["exceptions"])

    def test_original_utf8_bytes_must_agree_with_raw_text(self):
        matching = code("PIEZA-ñ", raw_bytes_hex="PIEZA-ñ".encode().hex())
        self.assertEqual(compare_codes([matching], "PIEZA-ñ", "piece")["result"], "MATCH")
        mismatching = code("ITR-001", raw_bytes_hex=b"ITR-002".hex())
        self.assertEqual(compare_codes([mismatching], "ITR-001", "piece")["result"], "PROCESSING_ERROR")

    def test_json_field_requires_explicit_parser_contract(self):
        label = code('{"material_id": "ITR-001", "lot": "L001"}')
        self.assertEqual(compare_codes([label], "ITR-001", "box")["result"], "MISMATCH")
        result = compare_codes([label], "ITR-001", "box", parser={"type": "json_field", "field": "material_id"})
        self.assertEqual(result["result"], "MATCH")
        bad = compare_codes([code('{"lot":"L001"}')], "ITR-001", "box",
                            parser={"type": "json_field", "field": "material_id"})
        self.assertEqual(bad["result"], "PROCESSING_ERROR")

    def test_malformed_inputs_are_processing_errors(self):
        cases = [(None, "ITR-001", "piece"), (["ITR-001"], "ITR-001", "piece"),
                 ([{}], "ITR-001", "piece"), ([code(4)], "ITR-001", "piece"),
                 ([code("")], "ITR-001", "piece"), ([], "", "piece"), ([], None, "guessed")]
        for observations, expected, scope in cases:
            with self.subTest(observations=observations, expected=expected, scope=scope):
                self.assertEqual(compare_codes(observations, expected, scope)["result"], "PROCESSING_ERROR")

    def test_parser_rejects_implicit_normalization_and_unknown_formats(self):
        for parser in ({"type": "exact_utf8", "strip": True}, {"type": "gs1"},
                       {"type": "json_field", "field": ""}):
            self.assertEqual(compare_codes([code("ITR-001")], "ITR-001", "piece", parser=parser)["result"], "PROCESSING_ERROR")


if __name__ == "__main__":
    unittest.main()
