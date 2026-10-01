#!/usr/bin/env python3
"""Validate table90 locally or export an additive remote file installer.

No SSH, robot commands or restart are performed by this PC entrypoint.
Running the exported program on Motion with bundle JSON on stdin installs
files only. It does not qualify geometry, load tasks or permit motion.
"""
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import base64

if __package__:
    from . import scenario1_table90 as table90
    from . import scenario1_deposit_install as file_installer
else:
    import scenario1_table90 as table90
    import scenario1_deposit_install as file_installer


def remote_source():
    # Isolated namespaces reuse the existing checked additive writer without
    # changing its legacy builder or accepting arbitrary new task contents.
    return (
        "import sys\n"
        "_table={'__name__':'table90_contract'}\n"
        'exec(compile('+repr(Path(table90.__file__).read_text())+",'scenario1_table90.py','exec'),_table)\n"
        "_files={'__name__':'table90_file_installer','_CHECKS_SOURCE':"+
        repr(file_installer.discovery_source())+'}\n'
        'exec(compile('+repr(Path(file_installer.__file__).read_text())+",'scenario1_deposit_install.py','exec'),_files)\n"
        "_files['validate_bundle']=_table['validate_bundle']\n"
        "raise SystemExit(_files['main']())\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--remote-program', type=Path, help='New local file; exports installer, does not run it')
    parser.add_argument('--install', action='store_true', help='Install additive files on Motion; no reload or movement')
    parser.add_argument('--wifi', action='store_true')
    parser.add_argument('--evidence-dir', type=Path, help='New PC directory required with --install')
    args = parser.parse_args()
    bundle = json.loads(args.bundle.read_text())
    identity, hashes = table90.validate_bundle(bundle)
    if args.install:
        if not args.evidence_dir or args.remote_program:
            parser.error('--install requires --evidence-dir and cannot export --remote-program')
        if __package__:
            from . import scenario1_cli as cli
        else:
            import scenario1_cli as cli
        args.evidence_dir.mkdir(parents=True, exist_ok=False)
        (args.evidence_dir/'bundle.json').write_text(json.dumps(bundle, indent=2)+'\n')
        source = remote_source()
        (args.evidence_dir/'remote-program.py').write_text(source)
        command = cli.ssh_command(args.wifi)[:-1]+[shlex.join([
            'python3', '-B', '-c', 'import base64;exec(base64.b64decode('+repr(base64.b64encode(source.encode()).decode())+'))'])]
        env = dict(os.environ, CRUZR_INTERNAL_ASKPASS='1',
                   SSH_ASKPASS=str(cli.ROOT/'scripts/cruzr_recover_to_home.sh'),
                   SSH_ASKPASS_REQUIRE='force', DISPLAY=os.environ.get('DISPLAY', ':0'))
        result = subprocess.run(command, env=env, input=json.dumps(bundle), text=True,
                                capture_output=True, timeout=90, start_new_session=True)
        (args.evidence_dir/'stdout.json').write_text(result.stdout)
        (args.evidence_dir/'stderr.txt').write_text(result.stderr)
        if result.returncode:
            raise RuntimeError('Table90 install failed; see durable local evidence')
        receipt = json.loads(result.stdout)
        if receipt.get('status') != 'installed' or receipt.get('id') != identity or receipt.get('task_hashes') != hashes:
            raise RuntimeError('Table90 install receipt mismatch')
        print(json.dumps(receipt, indent=2))
        return
    if args.remote_program:
        with args.remote_program.open('x') as stream:
            stream.write(remote_source())
    print(json.dumps(dict(status='LOCAL_BUNDLE_OK', id=identity, task_hashes=hashes,
                          loaded='not_verified', physical_validation='pending',
                          movement_commands=0, remote_operations=0), indent=2))


if __name__ == '__main__':
    main()
