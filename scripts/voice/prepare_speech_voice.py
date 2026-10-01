#!/usr/bin/env python3
"""Back up and build exact-message speech localization; never activate services.

Compiler inputs and ABI tests run only in a separate /tmp directory. Installation
uses deploy_voice_assets.py separately, with its existing E-stop requirement.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import wave

if __package__:
    from .deploy_voice_assets import execute, require, ssh
else:
    from deploy_voice_assets import execute, require, ssh

CONTAINER = 'walker-voice.speech_service-1'
ENTRY = '/opt/walker/entrypoint.sh'
BINARY = '/opt/walker/speech_service/lib/speech_service/speech_service'
MESSAGES = '/opt/walker/sys_task_msgs/lib/libsys_task_msgs.so'
TARGET = '/etc/walker/voice/teleop_charge_es_v1'
PINS = {
    ENTRY: '59f77c2dc18749753e6178fd6170152339d5f69bbb7b44e284df4d1f48c7f5e1',
    BINARY: '3ffd6c14664f513bf4f9db7db355189fe08dd39f60c0e185edfb58ea23a2d5e2',
    MESSAGES: '98ed5126e8848cb5d228f973e8f95c5e413cb8160aaf12a1f6c7c26b2723b419',
}
MARKER = '# VOICE-TELEOP-CHARGE-08: exact speech messages; native fallback.'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def validate_catalog(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError('Expected a nonempty catalog')
    fixed = []
    ids, texts = set(), set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('Malformed catalog entry')
        if row.get('kind') != 'fixed':
            raise ValueError('Only reviewed fixed messages are accepted')
        if not isinstance(row.get('id'), str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,63}', row['id']):
            raise ValueError('Invalid audio id')
        if any(not isinstance(row.get(key), str) or not row[key].strip() or '\0' in row[key]
               for key in ('zh', 'es', 'en')):
            raise ValueError('Missing translation or invalid text')
        if not re.search(r'[\u4e00-\u9fff]', row['zh']):
            raise ValueError('Expected an exact Chinese source')
        if any(re.search(r'[\u4e00-\u9fff]', row[key]) for key in ('es', 'en')):
            raise ValueError('Untranslated Chinese remains')
        if row['id'] in ids or row['zh'] in texts:
            raise ValueError('Duplicate audio id or source text')
        ids.add(row['id']); texts.add(row['zh']); fixed.append(row)
    return fixed


def build_catalog_header(rows):
    rows = validate_catalog(rows)
    return ('#pragma once\n#include <map>\n#include <string>\n'
            '#ifndef SPEECH_AUDIO_ROOT\n#define SPEECH_AUDIO_ROOT "'+TARGET+'/audio_es"\n#endif\n'
            'static const std::map<std::string,std::pair<std::string,std::string>> speech_catalog={\n'+
            ''.join('{'+json.dumps(row['zh'], ensure_ascii=False)+',{'+json.dumps(row['id'])+','+
                    json.dumps(row['en'], ensure_ascii=False)+'}},\n' for row in rows)+'};\n')


def launcher_with_voice(before, hashes, library):
    needle = 'eval "$cmd"'
    if before.count(needle) != 1 or 'VOICE-TELEOP-CHARGE-08' in before:
        raise ValueError('Unexpected entrypoint; review instead of stacking installations')
    if not hashes or library not in hashes:
        raise ValueError('The library must have an expected hash')
    for path, digest in hashes.items():
        if not isinstance(path, str) or not path.startswith('/') or not re.fullmatch(r'[0-9a-f]{64}', digest):
            raise ValueError('Invalid compatibility pin')
    condition = ' &&\n     '.join('[[ "$(sha256sum '+shlex.quote(path)+
        ' 2>/dev/null | cut -d\' \' -f1)" == '+shlex.quote(digest)+' ]]'
        for path, digest in hashes.items())
    block = (MARKER+'\nif '+condition+'; then\n export LD_PRELOAD='+shlex.quote(library)+
             '"${LD_PRELOAD:+:$LD_PRELOAD}"\nelse\n printf "%s\\n" '
             '"[VOICE_SPEECH] incompatible assets; native voice retained" >&2\nfi\n')
    after = before.replace(needle, block+needle)
    assert after.replace(block, '') == before
    return after


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', required=True, type=Path)
    parser.add_argument('--audio', required=True, type=Path)
    parser.add_argument('--evidence', required=True, type=Path)
    args = parser.parse_args(argv)
    rows = validate_catalog(json.loads(args.catalog.read_text()))
    args.evidence.mkdir(parents=True, exist_ok=False, mode=0o700)
    source = args.evidence/'source'; source.mkdir()
    for path in (Path(__file__).parent/'speech').iterdir():
        if path.suffix in ('.cpp', '.hpp'):
            shutil.copy2(path, source/path.name)
    (source/'catalog.hpp').write_text(build_catalog_header(rows))
    audio = args.evidence/'audio_es'; audio.mkdir()
    for row in rows:
        path = args.audio/(row['id']+'.wav')
        with wave.open(str(path)) as wav:
            if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 2, 16000) or wav.getnframes() < 1600:
                raise ValueError('Invalid Spanish WAV: '+row['id'])
        shutil.copy2(path, audio/path.name)
    (args.evidence/'catalog.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2)+'\n')
    shutil.copy2(__file__, args.evidence/'recipe.py')
    inventory = execute('vision', ['docker', 'ps', '--format', '{{.Names}}'])
    (args.evidence/'inventory.json').write_text(json.dumps(inventory, indent=2))
    if CONTAINER not in require(inventory).splitlines():
        raise RuntimeError('Speech container is not running')
    inspect = execute('vision', ['docker', 'inspect', '--format',
        '{{json .Mounts}}', CONTAINER])
    (args.evidence/'mounts.json').write_text(json.dumps(inspect, indent=2))
    for mount in json.loads(require(inspect)):
        dest = mount['Destination'].rstrip('/')
        if ENTRY == dest or ENTRY.startswith(dest+'/'):
            raise RuntimeError('Speech entrypoint is shared; review scope')
    with (args.evidence/'originals.tar.gz').open('wb') as stream:
        result = ssh(['docker', 'exec', CONTAINER, 'tar', 'czf', '-', '--dereference',
                      ENTRY, BINARY, MESSAGES], stdout=stream, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError('Backup failed: '+result.stderr.decode())
    with tarfile.open(args.evidence/'originals.tar.gz') as archive:
        originals = {name: archive.extractfile(name.lstrip('/')).read() for name in PINS}
    hashes = {name: sha(data) for name, data in originals.items()}
    (args.evidence/'original-hashes.json').write_text(json.dumps(hashes, indent=2)+'\n')
    if hashes != PINS:
        raise RuntimeError('Native compatibility/baseline changed; no compilation or deployment')

    remote = '/tmp/'+args.evidence.resolve().parent.name+'-'+args.evidence.name
    if not re.fullmatch(r'/tmp/[A-Za-z0-9_-]+', remote):
        raise ValueError('Use a simple evidence directory name')
    archive_path = args.evidence/'compiler-inputs.tar.gz'
    with tarfile.open(archive_path, 'w:gz') as archive:
        for directory in (source, audio):
            for path in sorted(directory.iterdir()):
                archive.add(path, arcname=str(path.relative_to(args.evidence)))
    require(execute('vision', ['docker', 'exec', '-u', '0', CONTAINER, 'mkdir', '-m', '700', remote]))
    with archive_path.open('rb') as stream:
        result = ssh(['docker', 'exec', '-i', '-u', '0', CONTAINER, 'tar', 'xzf', '-', '-C', remote],
                     stdin=stream, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError('Compiler input transfer failed')
    # Both variants execute an isolated native-message round trip. No ROS node,
    # goal, speaker or service is created by the test program.
    common = ['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-I'+remote+'/source',
              '-L/opt/walker/sys_task_msgs/lib']
    commands = []
    for variant, define in [('fallback', []), ('files', ['-DSPEECH_AUDIO_ROOT="'+remote+'/audio_es"'])]:
        directory = remote+'/'+variant
        commands.append(['mkdir', directory])
        commands.append(common+define+['-fPIC', '-shared', remote+'/source/voice_speech.cpp',
            '-o', directory+'/libvoice_speech.so', '-lsys_task_msgs', '-ldl'])
        commands.append(common+define+[remote+'/source/native_test.cpp', '-o', directory+'/voice_speech_native_test',
            '-lsys_task_msgs', '-ldl'])
        commands.append(['env', '-u', 'LD_PRELOAD', directory+'/voice_speech_native_test', '--expect-native'])
        commands.append(['cp', directory+'/voice_speech_native_test', directory+'/voice_speech_unrelated_test'])
        commands.append(['env', 'LD_PRELOAD='+directory+'/libvoice_speech.so',
                         directory+'/voice_speech_unrelated_test', '--expect-native'])
        commands.append(['env', 'LD_PRELOAD='+directory+'/libvoice_speech.so', directory+'/voice_speech_native_test',
                         '--expect-'+variant])
    shell = 'source /opt/walker/setup.bash\nset -e\nulimit -c 0\n'+'\n'.join(shlex.join(command) for command in commands)
    result = ssh(['docker', 'exec', '-u', '0', CONTAINER, 'bash', '-lc', shell], capture_output=True, text=True)
    (args.evidence/'compile-test.json').write_text(json.dumps(dict(rc=result.returncode,
        stdout=result.stdout, stderr=result.stderr, commands=commands, remote=remote), indent=2))
    if result.returncode:
        raise RuntimeError('Native build/test failed; see compile-test.json')
    for name in ('libvoice_speech.so', 'voice_speech_native_test'):
        with (args.evidence/name).open('wb') as stream:
            result = ssh(['docker', 'exec', '-u', '0', CONTAINER, 'cat', remote+'/fallback/'+name],
                         stdout=stream, stderr=subprocess.PIPE)
        if result.returncode:
            raise RuntimeError('Compiled asset transfer failed')
    deployment = args.evidence/'deployment'; (deployment/'payload').mkdir(parents=True)
    plan = []

    def add(group, target, data, before=None, mode=0o644):
        key = sha(target.encode()); (deployment/'payload'/key).write_bytes(data)
        plan.append(dict(container=group, target=target, before_sha256=before,
                         after_sha256=sha(data), payload=key, metadata=dict(mode=mode, uid=0, gid=0)))

    for name in ('libvoice_speech.so', 'voice_speech_native_test'):
        add('HOST', TARGET+'/'+name, (args.evidence/name).read_bytes(), mode=0o755)
    for directory in (source, audio):
        for path in sorted(directory.iterdir()):
            add('HOST', TARGET+'/'+str(path.relative_to(args.evidence)), path.read_bytes())
    add('HOST', TARGET+'/catalog.json', (args.evidence/'catalog.json').read_bytes())
    pins = {BINARY: hashes[BINARY], MESSAGES: hashes[MESSAGES],
            **{row['target']: row['after_sha256'] for row in plan}}
    after = launcher_with_voice(originals[ENTRY].decode(), pins, TARGET+'/libvoice_speech.so')
    launcher = args.evidence/'entrypoint.after.sh'; launcher.write_text(after)
    subprocess.run(['bash', '-n', str(launcher)], check=True)
    add(CONTAINER, ENTRY, after.encode(), hashes[ENTRY], 0o755)
    (deployment/'plan.json').write_text(json.dumps(plan, indent=2)+'\n')
    print('PREPARED: '+str(len(rows))+' messages, '+str(len(plan))+' files; no restart, goals or playback.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
