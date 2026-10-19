import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from perception import checkpoint_category


class CheckpointCategoryTests(unittest.TestCase):
    def test_sparse_coco_ids_do_not_change_contiguous_model_indices(self):
        self.assertEqual(checkpoint_category(0, {0: 7, 1: 23}), 7)
        self.assertEqual(checkpoint_category(1, {0: 7, 1: 23}), 23)

    def test_custom_background_is_excluded_not_named_as_a_part(self):
        self.assertIsNone(checkpoint_category(2, {0: 7, 1: 23}))

    def test_other_indices_are_errors_not_silently_dropped(self):
        for index in (-1, 3):
            with self.assertRaises(ValueError):
                checkpoint_category(index, {0: 7, 1: 23})
