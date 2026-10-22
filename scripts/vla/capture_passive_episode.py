#!/usr/bin/env python3
"""Capture RGB + joints + actuator setpoints + forces, without moving the robot.

The default creates a new private episode on the Linux PC. Ctrl+C ends capture
only; it cannot stop the robot. No VLA container or control client is started.
"""
import argparse
import base64
import datetime
import hashlib
import json
import os
from pathlib import Path
import selectors
import shlex
import shutil
import signal
import subprocess
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from passive_episode_quality import analyze


def ssh_command(remote):
    return ['ssh', '-T', '-o', 'StrictHostKeyChecking=yes',
        '-o', 'ConnectTimeout=5', '-o', 'ConnectionAttempts=1',
        '-o', 'ServerAliveInterval=5', '-o', 'ServerAliveCountMax=2',
        '-o', 'PreferredAuthentications=password', '-o', 'PubkeyAuthentication=no',
        '-o', 'NumberOfPasswordPrompts=1', 'walker@192.168.11.3', shlex.join(remote)]


def capture(args):
    sys.path.insert(0, str(ROOT/'scripts'))
    from collect_estop_available_readonly import execute
    directory = args.output_dir
    directory.mkdir(parents=True, exist_ok=False, mode=0o700)
    (directory/'rgb').mkdir(mode=0o700)
    if shutil.disk_usage(directory).free < 256*1024*1024:
        raise ValueError('Less than 256 MiB free disk space')
    source = (HERE/'passive_episode_remote.py').read_bytes()
    profile = json.loads((HERE/'runtime/cruzr_s2_vla_profile.json').read_text())
    manifest = dict(schema='cruzr-passive-episode-v1', task=args.task, episode_id=directory.name,
        started_pc_ns=time.time_ns(), requested_seconds=args.seconds, fps_limit=args.fps,
        telemetry_hz_limit=args.telemetry_hz, joint_names=profile['joint_names'],
        movement_commands=0, action_label='unqualified actuator cmd_pos', training_ready=False,
        source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in
            (Path(__file__), HERE/'passive_episode_remote.py', HERE/'passive_episode_quality.py',
             HERE/'runtime/cruzr_s2_vla_profile.json')}, transport={})
    (directory/'sources').mkdir(mode=0o700)
    for path in (Path(__file__), HERE/'passive_episode_remote.py', HERE/'passive_episode_quality.py',
                 HERE/'runtime/cruzr_s2_vla_profile.json'):
        (directory/'sources'/path.name).write_bytes(path.read_bytes())
    def save():
        (directory/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    save()
    discovery = execute('vision', ['docker', 'ps', '--format', '{{.Names}}|{{.Image}}'])
    (directory/'discovery.json').write_text(json.dumps(discovery,indent=2)+'\n')
    candidates = [line.split('|')[0] for line in discovery.get('stdout','').splitlines()
                  if line.split('|')[0].startswith('walker-ros.') and line.split('|')[0].endswith('ros2-1')]
    if discovery.get('returncode') != 0 or len(candidates) != 1:
        manifest['transport']['error'] = 'Vision ROS container discovery failed'; save()
        raise ValueError(manifest['transport']['error'])
    container = candidates[0]
    manifest['container'] = container
    inventory = execute('vision', ['docker', 'inspect', '--format', '{{.Id}}|{{.State.StartedAt}}|{{.Image}}', container])
    (directory/'container-identity.json').write_text(json.dumps(inventory,indent=2)+'\n')
    if inventory.get('returncode') != 0:
        raise ValueError('Container identity read failed')
    shell = ('source /opt/ros/humble/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; '
        'exec timeout --signal=TERM --kill-after=2s '+str(int(args.seconds)+25)+'s python3 -B -u - '+
        shlex.join(['--seconds',str(args.seconds),'--fps',str(args.fps),'--telemetry-hz',str(args.telemetry_hz)]))
    command = ssh_command(['docker','exec','-i',container,'bash','-lc',shell])
    env = dict(os.environ,CRUZR_INTERNAL_ASKPASS='1',SSH_ASKPASS=str(ROOT/'scripts/cruzr_recover_to_home.sh'),
               SSH_ASKPASS_REQUIRE='force',DISPLAY=os.environ.get('DISPLAY',':0'))
    (directory/'collector_remote.py').write_bytes(source)
    proc = subprocess.Popen(command,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,start_new_session=True)
    proc.stdin.write(source); proc.stdin.close()
    selector = selectors.DefaultSelector()
    for stream, kind in ((proc.stdout,'stdout'),(proc.stderr,'stderr')):
        os.set_blocking(stream.fileno(),False)
        selector.register(stream,selectors.EVENT_READ,[kind,bytearray()])
    total, images = 0, 0
    deadline = time.monotonic()+args.seconds+45
    print('CAPTURA PASIVA: '+str(directory),flush=True)
    print('Espera a CAPTURA_LISTA antes de tu demostración. Este proceso no mueve el robot.',flush=True)
    try:
        with (directory/'samples.jsonl').open('x',buffering=1) as samples, (directory/'capture.log').open('x',buffering=1) as log:
            while selector.get_map():
                if time.monotonic() > deadline:
                    raise TimeoutError('Bounded capture deadline exceeded')
                for key,_ in selector.select(.2):
                    kind, buffer = key.data
                    block = os.read(key.fd,65536)
                    if not block:
                        selector.unregister(key.fileobj)
                        if buffer:
                            (directory/(kind+'-partial.bin')).write_bytes(buffer)
                            if kind == 'stderr':
                                log.write(buffer.decode('utf-8',errors='replace'))
                            else:
                                raise ValueError('Truncated final stdout record; saved stdout-partial.bin')
                        continue
                    total += len(block)
                    if total > args.max_mib*1024*1024:
                        raise ValueError('Capture stream size limit reached')
                    buffer.extend(block)
                    if len(buffer) > 48*1024*1024:
                        raise ValueError('Unbounded stream line')
                    while b'\n' in buffer:
                        line,_,rest = buffer.partition(b'\n'); buffer[:] = rest
                        text = line.decode('utf-8',errors='strict')
                        if kind == 'stderr' or not text.startswith('{'):
                            log.write(text+'\n'); continue
                        row = json.loads(text)
                        row['pc_received_ns'] = time.time_ns()
                        row['pc_received_monotonic_ns'] = time.monotonic_ns()
                        if row.get('kind') == 'rgb':
                            data = base64.b64decode(row.pop('png_b64'),validate=True)
                            if not data.startswith(b'\x89PNG\r\n\x1a\n') or hashlib.sha256(data).hexdigest()!=row['png_sha256']:
                                raise ValueError('Corrupt streamed PNG')
                            name = f'rgb/{images:06d}.png'; images += 1
                            (directory/name).write_bytes(data); row['png_file'] = name
                        elif row.get('kind') == 'ready':
                            print('CAPTURA_LISTA — grabando durante '+str(args.seconds)+' segundos.',flush=True)
                        samples.write(json.dumps(row,allow_nan=False,separators=(',',':'))+'\n')
            manifest['transport']['returncode'] = proc.wait(timeout=3)
    except KeyboardInterrupt:
        manifest['transport']['error'] = 'Capture interrupted by operator; robot was not signalled'
        print('Captura detenida; no se ha enviado parada al robot.',flush=True)
    except Exception as exc:
        manifest['transport']['error'] = type(exc).__name__+': '+str(exc)
    finally:
        selector.close()
        if proc.poll() is None:
            os.killpg(proc.pid,signal.SIGTERM)
            try: proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGKILL); proc.wait(timeout=3)
        manifest['transport']['returncode'] = proc.returncode
        manifest.update(finished_pc_ns=time.time_ns(),stream_bytes=total,png_frames=images)
        save()
    final_identity = execute('vision', ['docker','inspect','--format','{{.Id}}|{{.State.StartedAt}}|{{.Image}}',container])
    (directory/'container-identity-after.json').write_text(json.dumps(final_identity,indent=2)+'\n')
    if final_identity.get('returncode') != 0 or final_identity.get('stdout') != inventory.get('stdout'):
        manifest['transport']['error'] = 'Vision container identity changed or could not be revalidated'
        save()
    report = analyze(directory,args.tolerance_ms)
    (directory/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(directory))+'\n'
        for p in sorted(directory.rglob('*')) if p.is_file() and p.name != 'SHA256SUMS'))
    print(json.dumps(dict(directory=str(directory),capture_checks_passed=report['capture_checks_passed'],
        frames=images,matched_frames=report['matched_frames'],training_ready=False,error=manifest['transport'].get('error')),indent=2),flush=True)
    return 0 if report['capture_checks_passed'] else 3


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seconds',type=float,default=300)
    p.add_argument('--fps',type=float,default=5)
    p.add_argument('--telemetry-hz',type=float,default=30)
    p.add_argument('--task',default='demo_caja',help='Task/operation label; does not imply episode success')
    p.add_argument('--output-dir',type=Path)
    p.add_argument('--max-mib',type=int,default=2048)
    p.add_argument('--tolerance-ms',type=float,default=80)
    args = p.parse_args(argv)
    if not 1 <= args.seconds <= 1800 or not .5 <= args.fps <= 15 or not 1 <= args.telemetry_hz <= 100:
        p.error('Duration [1,1800], FPS [.5,15], telemetry Hz [1,100]')
    if not 1 <= args.max_mib <= 8192 or not 1 <= args.tolerance_ms <= 100:
        p.error('Size [1,8192] MiB and pairing tolerance [1,100] ms')
    if args.output_dir is None:
        name = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_EPISODE_'+uuid.uuid4().hex[:8]
        args.output_dir = ROOT.parent/'Humanoide-vla-evidence'/name
    try:
        return capture(args)
    except (ValueError,OSError,subprocess.SubprocessError) as exc:
        print('CAPTURA_NO_VALIDADA: '+str(exc),file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
