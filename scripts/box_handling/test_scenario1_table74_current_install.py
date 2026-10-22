"""Exercise current approach installation with fake Docker and real validators."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.box_handling import scenario1_table74_current_trial as current
from scripts.box_handling import scenario1_table74_current_lower as lower
from scripts.box_handling import scenario1_table74_current_release as release
from scripts.box_handling import scenario1_table74_trial_install as installer
from scripts.box_handling.test_scenario1_table74_trial_install import FakeDocker, sources


def bundle():
    return current.build_bundle(dict(version=1, mode='operator_assumed_vendor45',
        source_checkpoint_sha256='a'*64, surface_height_m=.74,
        reference_surface_height_m=.45, scope='current_held_put1_only',
        evidence='SYNTHETIC test of assumed reference; no physical measurement'),
        *sources().values())


class CurrentInstallationTests(unittest.TestCase):
    factory = staticmethod(bundle)

    def test_live_check_install_rollback_preserve_vendor_and_use_exact_task_pair(self):
        value, docker = self.factory(), FakeDocker()
        docker.files[release.SOURCE_YAML_PATH] = (Path(__file__).resolve().parents[2]/
            'vendor/ubtech/cruzr_s2/snapshot_20260916/motion/meta_clamp/wrc/open_arm_cruzr.yaml').read_text()
        before = copy.deepcopy(docker.files)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def operate(mode):
                return installer.operate(value, operation=mode, run=docker,
                    evidence_root=root/'evidence', lock_path=root/'lock')
            checked = operate('check')
            self.assertFalse(checked['installed'])
            self.assertEqual(docker.writes, [])
            installed = operate('install')
            self.assertEqual(installed['phase'], value['manifest']['phase'])
            self.assertEqual(installed['movement_commands'], 0)
            self.assertEqual(installed['restarts'], 0)
            self.assertEqual(set(installed['created_files']), set(value['tasks']))
            self.assertEqual([Path(p).suffix for p in docker.writes], ['.yaml', '.xml'])
            self.assertTrue(operate('check')['installed'])
            for path, content in before.items():
                self.assertEqual(docker.files[path], content)
            rolled = operate('rollback')
            self.assertEqual(set(rolled['removed_files']), set(value['tasks']))
            self.assertEqual(docker.files, before)

    def test_phase_cannot_select_a_different_trusted_builder(self):
        for phase in ('approach_only', 'support_only', 'opening', None):
            value, docker = self.factory(), FakeDocker()
            value['manifest']['phase'] = phase
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(ValueError):
                    installer.operate(value, run=docker, lock_path=Path(directory)/'lock')
                self.assertEqual(docker.calls, [])

    def test_remote_bootstrap_loads_and_validates_without_repository_imports(self):
        value = self.factory()
        code = installer.remote_source()
        code += '\nassert sys.modules["scenario1_table74_trial_install"]._validate('+repr(value)+')[0]=='+repr(value['manifest']['id'])+'\n'
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, '-B', '-'], input=code, cwd=directory,
                                    text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)


def lower_bundle():
    return lower.build_bundle(dict(version=1, stage='precontact',
        gap_above_surface_m=.19, target_clearance_m=.05, surface_height_m=.74,
        predecessor_bundle_id='b'*64,
        predecessor_goal_id='80974a9d-f9b2-4322-a2d7-2db41f28766e',
        scope='current_post_trial_box_only',
        evidence='SYNTHETIC test of reported gap; no physical measurement'),
        *sources().values())


class LowerInstallationTests(CurrentInstallationTests):
    factory = staticmethod(lower_bundle)


def release_bundle():
    original = sources()
    opening = (Path(__file__).resolve().parents[2]/
        'vendor/ubtech/cruzr_s2/snapshot_20260916/motion/meta_clamp/wrc/open_arm_cruzr.yaml').read_text()
    return release.build_bundle(dict(version=1, stage='pin_relief', surface_height_m=.74,
        predecessor_bundle_id='c'*64, predecessor_goal_id='a8b7e6b9-f578-4b37-b028-9e2b5e179819',
        operator_support_confirmed=True, tool_table_clearance_m=.04, required_pin_exit_m=.03,
        operator_pins_free=False, lateral_path_clear=True, scope='current_supported_box_only',
        evidence='SYNTHETIC test of operator support declarations, not physical evidence'),
        original[release.SOURCE_XML_PATH], opening)


class ReleaseInstallationTests(CurrentInstallationTests):
    factory = staticmethod(release_bundle)


if __name__ == '__main__':
    unittest.main()
