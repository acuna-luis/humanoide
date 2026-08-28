#!/usr/bin/env python3
"""Unit tests for the standard-library portion of E2.2 offline evaluation."""

from __future__ import annotations

import importlib.util
import pathlib
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).parents[1] / "evaluate_checkpoint_offline.py"
SPEC = importlib.util.spec_from_file_location("evaluate_checkpoint_offline", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class OfflineSelectionTests(unittest.TestCase):
    def test_tail_holdout_is_stratified_by_task(self) -> None:
        episodes = [
            {"episode_index": index, "tasks": MODULE.TASKS[1], "length": 20}
            for index in range(20)
        ] + [
            {"episode_index": 100 + index, "tasks": MODULE.TASKS[3], "length": 20}
            for index in range(10)
        ]
        eligible, held_out = MODULE.test_pool_for_task(episodes, 1)
        self.assertEqual(len(eligible), 20)
        self.assertEqual([row["episode_index"] for row in held_out], [17, 18, 19])

    def test_selection_is_reproducible(self) -> None:
        episodes = [
            {"episode_index": index * 2 + 1, "tasks": MODULE.TASKS[1], "length": 20}
            for index in range(30)
        ]
        first = MODULE.select_episode(episodes, 1, 0)
        second = MODULE.select_episode(episodes, 1, 0)
        self.assertEqual(first, second)

    def test_json_write_is_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / "result.json"
            MODULE.write_json_exclusive(path, {"ok": True})
            with self.assertRaises(FileExistsError):
                MODULE.write_json_exclusive(path, {"ok": False})


if __name__ == "__main__":
    unittest.main()
