"""No robot access: verify fail-closed, reversible environment patch."""
import unittest
from unittest.mock import patch
from scripts.upgrade import cruzr_no_shm as impl


class NoShmTest(unittest.TestCase):
    def test_install_idempotent_and_exact_rollback(self):
        before = b'# fixture\nexport EXISTING=yes\n'
        with patch.object(impl, 'ORIGINAL_SHA', impl.sha(before)):
            after = impl.transformed(before)
            self.assertEqual(after, before+impl.BLOCK)
            self.assertEqual(impl.transformed(after), after)
            self.assertEqual(impl.transformed(after, rollback=True), before)
            self.assertEqual(impl.transformed(before, rollback=True), before)

    def test_unknown_original_or_modified_patch_rejected(self):
        before = b'# fixture\n'
        with patch.object(impl, 'ORIGINAL_SHA', impl.sha(before)):
            for content in (b'unknown', before+b'extra\n', before+impl.BLOCK+b'extra\n',
                            before+impl.BLOCK.replace(b'OFF', b'ON')):
                with self.subTest(content=content), self.assertRaises(ValueError):
                    impl.transformed(content)
                with self.assertRaises(ValueError):
                    impl.transformed(content, rollback=True)
