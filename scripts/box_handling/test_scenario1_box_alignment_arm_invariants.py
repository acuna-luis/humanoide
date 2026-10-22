"""Pin the unchanged pickup sources and generated arm tasks for this port."""
import hashlib
import json
from pathlib import Path
import unittest

from scripts.box_handling import front_box_integration as integration
from scripts.box_handling import scenario1_runtime as runtime


ROOT = Path(__file__).resolve().parents[2]
REFERENCE = json.loads((Path(__file__).parent/'fixtures/box_alignment_arm_invariants_20261022.json').read_text())


class PickupArmInvariantsTests(unittest.TestCase):
    def test_native_pickup_sources_are_unchanged_from_the_pre_port_branch(self):
        for name, expected in REFERENCE['source_files_sha256'].items():
            with self.subTest(path=name):
                self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(), expected)

    def test_generated_tasks_parameters_dependencies_and_native_pins_are_unchanged(self):
        bundle = integration.build_bundle()
        self.assertEqual(bundle['manifest']['id'], REFERENCE['sps_bundle_id'])
        self.assertEqual({name: hashlib.sha256(text.encode()).hexdigest()
                          for name, text in bundle['tasks'].items()}, REFERENCE['generated_tasks_sha256'])
        self.assertEqual(bundle['manifest']['dependencies'], REFERENCE['generated_dependencies'])
        self.assertEqual(bundle['manifest']['native_binaries'], REFERENCE['native_binary_pins'])
        self.assertEqual(runtime.TASKS['grasp'], (REFERENCE['grasp_task'], REFERENCE['grasp_timeout_s']))


if __name__ == '__main__':
    unittest.main()
