from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).with_name('resolve_cpu_wheelhouse.sh')


class ResolveTests(unittest.TestCase):
    def test_help_and_bounded_download_configuration(self):
        result = subprocess.run(['bash', str(SCRIPT), '--help'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        code = SCRIPT.read_text(encoding='utf-8')
        for expected in ('--index-url https://pypi.org/simple', 'timeout --signal=TERM',
                         'MANIFEST_SHA=', 'CONSTRAINTS_SHA=', 'platform_machine="aarch64"',
                         'check_wheelhouse_manifest.py'):
            self.assertIn(expected, code)

    def test_missing_inputs_fail_without_creating_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'new'
            result = subprocess.run(['bash', str(SCRIPT), '--download',
                                     str(Path(tmp) / 'missing'), tmp, str(output)],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
