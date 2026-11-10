import platform
import hashlib
import re
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).with_name('build_cpu_venv.sh')


class BuildVenvTests(unittest.TestCase):
    def test_pins_are_full_sha256_and_match_recorded_manifest(self):
        code = SCRIPT.read_text(encoding='utf-8')
        pins = dict(re.findall(r"^(MANIFEST_SHA|CONSTRAINTS_SHA)='([^']+)'$", code, re.M))
        self.assertEqual(set(pins), {'MANIFEST_SHA', 'CONSTRAINTS_SHA'})
        self.assertTrue(all(re.fullmatch(r'[0-9a-f]{64}', value) for value in pins.values()))
        project = SCRIPT.parents[3]
        evidence = project.parent / 'Humanoide-vla-evidence' / '20261110_SMOLVLA_CPU_ARM64_PREP'
        manifest = evidence / 'wheelhouse-candidate' / 'SHA256SUMS'
        constraints = evidence / 'constraints-arm64-from-ada.txt'
        if manifest.is_file() and constraints.is_file():
            self.assertEqual(hashlib.sha256(manifest.read_bytes()).hexdigest(), pins['MANIFEST_SHA'])
            self.assertEqual(hashlib.sha256(constraints.read_bytes()).hexdigest(), pins['CONSTRAINTS_SHA'])

    def test_help_and_isolation(self):
        run = subprocess.run(['bash', str(SCRIPT), '--help'], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0)
        text = SCRIPT.read_text(encoding='utf-8')
        for required in ('--network none', '--read-only', '--cap-drop ALL',
                         '--security-opt no-new-privileges', 'cruzr.smolvla.owner',
                         '--memory 4g', '--cpus 2', '--no-index',
                         'check_wheelhouse_manifest.py', 'SMOLVLA_IMPORT_OK'):
            self.assertIn(required, text)

    def test_missing_inputs_do_not_create_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'new'
            run = subprocess.run(['bash', str(SCRIPT), '--run', tmp, str(Path(tmp) / 'absent'), str(output)],
                                 capture_output=True, text=True)
            self.assertNotEqual(run.returncode, 0)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
