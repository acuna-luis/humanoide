#!/usr/bin/env python3
"""Decompile selected functions from a local ELF copy; never execute that ELF.

Requires Java 21 and Ghidra. Optional setup downloads a pinned official release
into --tool-dir, outside the repo. No SSH, ROS, library patch or robot access.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import urllib.request
import zipfile

VERSION = '12.1.3'
ARCHIVE = 'ghidra_12.1.3_PUBLIC_20260817.zip'
URL = 'https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_12.1.3_build/' + ARCHIVE
SHA256 = '93a5d11a9ad510622acaaf908c556a7b9b764d338e78a7567f3689bf5081fd54'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def setup_tool(root):
    root.mkdir(parents=True, exist_ok=True)
    archive = root / ARCHIVE
    if not archive.exists():
        temporary = root / (ARCHIVE+'.part')
        urllib.request.urlretrieve(URL, temporary)
        if digest(temporary) != SHA256:
            raise ValueError('Ghidra download checksum mismatch')
        temporary.rename(archive)
    if digest(archive) != SHA256:
        raise ValueError('Ghidra archive checksum mismatch')
    with zipfile.ZipFile(archive) as source:
        for member in source.infolist():
            target = (root/member.filename).resolve()
            if not target.is_relative_to(root.resolve()):
                raise ValueError('Archive member outside tool directory')
            if not target.exists():
                source.extract(member, root)
            if target.is_file() and (member.external_attr >> 16) & 0o111:
                target.chmod(0o755)
    (root/'ghidra-source.json').write_text(json.dumps(
        dict(version=VERSION, url=URL, archive_sha256=SHA256), indent=2)+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tool-dir', required=True, type=Path)
    parser.add_argument('--setup-tool', action='store_true')
    parser.add_argument('--binary', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--filter', action='append', required=True,
                        help='Function-name substring; repeat for multiple functions')
    args = parser.parse_args()
    root = args.tool_dir.resolve()
    if args.setup_tool:
        setup_tool(root)
    headless = root / ('ghidra_'+VERSION+'_PUBLIC/support/analyzeHeadless')
    if not headless.is_file():
        parser.error('Ghidra missing; use --setup-tool or correct --tool-dir')
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    inputs = out/'inputs'; inputs.mkdir()
    projects = out/'projects'; projects.mkdir()
    copied = inputs/args.binary.name
    shutil.copy2(args.binary, copied)
    source_hash = digest(copied)
    scripts = Path(__file__).resolve().parent
    command = [str(headless), str(projects), 'box_selection',
               '-import', str(copied), '-analysisTimeoutPerFile', '180',
               '-max-cpu', '2', '-scriptPath', str(scripts),
               '-preScript', 'ConfigureBoxAnalysis.java',
               '-postScript', 'DecompileBoxSelection.java', str(out/'pseudocode.c'),
               *args.filter]
    (out/'manifest.json').write_text(json.dumps(dict(
        input=str(args.binary.resolve()), input_sha256=source_hash,
        ghidra_version=VERSION, ghidra_archive_sha256=SHA256, command=command,
        robot_changes=False, input_executed=False), indent=2)+'\n')
    print('Static analysis:', copied.name, flush=True)
    with (out/'analysis.log').open('w') as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=600)
    if digest(copied) != source_hash:
        raise RuntimeError('Input copy changed unexpectedly')
    output = out/'pseudocode.c'
    if result.returncode or not output.exists() or '// FUNCTION ' not in output.read_text():
        raise RuntimeError('No pseudocode exported; inspect '+str(out/'analysis.log'))
    print('Pseudocode:', output)


if __name__ == '__main__':
    main()
