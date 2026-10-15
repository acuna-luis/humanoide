import unittest
from scripts.patch_web_map_fusion import patch, BEFORE, AFTER


class FusionRequestTests(unittest.TestCase):
    def test_only_normal_creation_changes_and_json_is_explicit(self):
        source = b'JSON.stringify({map_name:w,mapping_mode:"normal"}),command:"mapping_start";mapping_mode:"mapping_extend"'
        result = patch(source)
        self.assertEqual(result, source.replace(BEFORE, AFTER))
        self.assertIn(b'map_name:w,mapping_mode:"normal",map_type:"fusion"', result)
        self.assertIn(b'mapping_mode:"mapping_extend"', result)

    def test_missing_duplicate_and_already_patched_requests_are_rejected(self):
        for source in (b'unknown', BEFORE+BEFORE, AFTER):
            with self.subTest(source=source), self.assertRaises(ValueError):
                patch(source)


if __name__ == '__main__':
    unittest.main()
