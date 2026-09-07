#!/usr/bin/env python3
"""Offline regression tests; fixtures are local temporary files only."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ANALYZER = Path(__file__).with_name('analyze_contact_evidence.py')


class ContactAuditTests(unittest.TestCase):
    def fixture(self, root):
        evidence = root / 'raw'
        for host in ('motion', 'vision'):
            (evidence / host).mkdir(parents=True)
            entries = []
            if host == 'motion':
                raw = (
                    "W2026-09-04 19:58:01.981529 BTree task: 'cruzr/home' is start\n"
                    "E2026-09-04 19:58:02.436163 left_arm's 2-th position cmd: 0.10316 is over of range: [-1.85873, 0.0987266]\n"
                ).encode()
                (evidence / host / 'log').write_bytes(raw)
                entries.append(dict(path='/log', bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
            (evidence / host / 'remote-manifest.json').write_text(json.dumps(entries))
        files = sorted(p for p in evidence.rglob('*') if p.is_file())
        (evidence / 'evidence.sha256').write_text(''.join(
            f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(evidence)}\n' for p in files))
        return evidence

    def run_analysis(self, raw, output):
        return subprocess.run([sys.executable, '-B', str(ANALYZER), str(raw), '--output', str(output)],
                              capture_output=True, text=True, timeout=10)

    def test_reproducibility_timezone_and_limit(self):
        with tempfile.TemporaryDirectory(prefix='contact-audit-test-') as tmp:
            root = Path(tmp)
            raw = self.fixture(root)
            for target in ('a', 'b'):
                result = self.run_analysis(raw, root / target)
                self.assertEqual(result.returncode, 0, result.stderr)
            timeline = (root / 'a/timeline.tsv').read_text()
            self.assertIn('2026-09-04T13:58:01.981529+02:00', timeline)
            self.assertIn('joint_limit', timeline)
            self.assertEqual(timeline, (root / 'b/timeline.tsv').read_text())
            self.assertNotEqual(self.run_analysis(raw, root / 'a').returncode, 0)

    def test_tampering_rejected_before_output(self):
        with tempfile.TemporaryDirectory(prefix='contact-audit-test-') as tmp:
            root = Path(tmp)
            raw = self.fixture(root)
            (raw / 'motion/log').write_text('altered')
            result = self.run_analysis(raw, root / 'out')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Integrity failure', result.stderr)
            self.assertFalse((root / 'out').exists())


if __name__ == '__main__':
    unittest.main()
