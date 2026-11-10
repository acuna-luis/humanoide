"""Offline plan-only tests; no physical action or remote writes."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import plan_pico_wrist_native_stage as plan
import prepare_pico_wrist_native_probe as prepare
from test_prepare_pico_wrist_native_probe import state, transmissions, urdf


class StagePlanTests(unittest.TestCase):
    def test_plan_captures_native_box_sources_and_no_writes(self):
        bundle = prepare.prepare(state(), urdf(), transmissions())
        result = plan.build_plan(bundle, urdf(), transmissions())
        self.assertEqual(result['transport_sources'], plan.EXPECTED)
        self.assertEqual(result['target']['task_name'], bundle['candidate']['task_name'])
        self.assertEqual(result['planned_goal']['yaml_args'], '{}')
        self.assertTrue(result['planned_support_dir'].startswith('/tmp/'))
        self.assertEqual(result['movement_commands'], 0)
        self.assertEqual(result['remote_writes'], 0)
        self.assertFalse(result['physical_control_qualified'])
        self.assertTrue(any('corridor guard' in x for x in result['missing_before_run']))

    def test_changed_source_or_candidate_rejected(self):
        bundle = prepare.prepare(state(), urdf(), transmissions())
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / 'fake.py'; bad.write_text('pass\n')
            with self.assertRaisesRegex(ValueError, 'transport_source_changed'):
                plan.build_plan(bundle, urdf(), transmissions(), {'scenario1_action_client.py': bad})
        bundle['candidate']['runtime_path'] = '/tmp/unreviewed.xml'
        with self.assertRaises(ValueError):
            plan.build_plan(bundle, urdf(), transmissions())

    def test_run_blocked_before_file_reads(self):
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('must not read')):
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(plan.main(['--run']), 2)

    def test_plan_output_cannot_overwrite_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = prepare.prepare(state(), urdf(), transmissions())
            (root/'manifest.json').write_text(json.dumps(bundle))
            (root/'runtime.urdf').write_text(urdf())
            (root/'transmissions.yaml').write_text(transmissions())
            output = root/'plan.json'
            args = ['--manifest', str(root/'manifest.json'), '--urdf', str(root/'runtime.urdf'),
                    '--transmissions', str(root/'transmissions.yaml'), '--output', str(output)]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(plan.main(args), 0)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(plan.main(args), 1)


if __name__ == '__main__':
    unittest.main()
