#!/usr/bin/env python3
"""One cold load and one bounded shadow session; never executes robot commands.

Existing evidence is exported before startup (which resets runtime logs).
First model call and subsequent calls are reported separately. No speed tuning.
"""
import argparse
import json
from pathlib import Path
import statistics
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
WRAPPER = ROOT/'scripts/vla/run_ubtech_vla_shadow.sh'
sys.path.insert(0, str(ROOT/'scripts'))
from collect_estop_available_readonly import execute


def summarize(log):
    stages = {}
    for line in log.splitlines():
        if 'VLA_TIMING {' not in line:
            continue
        row = json.loads(line.split('VLA_TIMING ', 1)[1])
        if row['succeeded']:
            stages.setdefault(row['stage'], []).append(row['elapsed_seconds'])
    result = {}
    for stage, values in stages.items():
        warm = sorted(values[1:])
        result[stage] = dict(count=len(values), first_seconds=values[0],
            subsequent_median_seconds=statistics.median(warm) if warm else None,
            subsequent_max_seconds=max(warm) if warm else None)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--duration', type=int, default=30)
    parser.add_argument('--task-id', type=int, choices=(0, 2), default=0)
    args = parser.parse_args()
    if not 8 <= args.duration <= 60:
        parser.error('duration must be 8..60 seconds')
    out = args.output_dir.resolve(); out.mkdir(parents=True, exist_ok=False)
    measures = []; cleanup = False
    (out/'intent.json').write_text(json.dumps(dict(mode='shadow_only', task_id=args.task_id,
        started_at_unix=time.time(), duration=args.duration, completed=False), indent=2))
    def interrupted(signum, frame):
        raise RuntimeError('Interrupted by signal '+str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    def run(label, *flags, timeout=120):
        start = time.perf_counter()
        with (out/(label+'.log')).open('x') as log:
            proc = subprocess.run([str(WRAPPER), *flags], cwd=ROOT, stdout=log,
                                  stderr=subprocess.STDOUT, timeout=timeout)
        measures.append(dict(stage=label, seconds=time.perf_counter()-start, returncode=proc.returncode))
        (out/"host-times.json").write_text(json.dumps(measures, indent=2))
        print(json.dumps(measures[-1]), flush=True)
        if proc.returncode:
            raise RuntimeError(label+' failed; see log')
    error = None
    try:
        run('status_before', '--status')
        status = (out/'status_before.log').read_text()
        if 'INFERENCE_CONTAINER=exited' not in status or 'CONTROL_CONTAINER=exited' not in status or 'COMMAND_PATH_SAFE=publishers:0' not in status:
            raise RuntimeError('Requires stopped VLA containers and no command publishers; existing session not interrupted')
        run('backup_previous', '--export-evidence', str(out/'previous'))
        run('check', '--check')
        cleanup = True
        run('start_shadow', '--start-shadow', '--shadow-duration', '300')
        start = time.perf_counter()
        run('request_inference_start', '--start-inference')
        deadline = time.monotonic()+110
        while time.monotonic() < deadline:
            r = execute('vision', ['docker', 'exec', 'cruzr-vla-inference', 'tail', '-n', '100', '/home/ubt/additional/safe-runtime-logs/inference-process.log'])
            (out/'startup_latest.json').write_text(json.dumps(r, indent=2))
            if r.get('returncode') == 0 and 'Starting Cruzr S2 inference-only shadow node' in r.get('stdout',''):
                break
            if 'Traceback (most recent call last)' in r.get('stdout',''):
                raise RuntimeError('Inference startup exception; see startup_latest.json')
            time.sleep(2)
        else:
            raise RuntimeError('Model readiness timeout')
        measures.append(dict(stage='start_until_node_ready', seconds=time.perf_counter()-start))
        (out/"host-times.json").write_text(json.dumps(measures, indent=2))
        print(json.dumps(measures[-1]), flush=True)
        run('trigger', '--trigger', '--task-id', str(args.task_id), '--inference-duration', str(args.duration), timeout=args.duration+60)
    except Exception as exc:
        error = str(exc)
    finally:
        if cleanup:
            try:
                run('stop', '--stop', timeout=60)
            except Exception as exc:
                error = (error or '')+'; cleanup: '+str(exc)
            try:
                run('export', '--export-evidence', str(out/'results'))
            except Exception as exc:
                error = (error or '')+'; export: '+str(exc)
        log = out/'results/inference-process.log'
        report = dict(schema='cruzr-vla-shadow-benchmark-v1', task_id=args.task_id,
            requested_inference_duration_seconds=args.duration, host_wall_times=measures,
            internal=summarize(log.read_text()) if log.exists() else {}, error=error,
            physical_motion_executed=False, physical_trial_approved=False,
            timing_semantics='CPU wall durations, nested stages; do not add them. get_action includes preprocessing/postprocessing and may include asynchronous GPU work.')
        (out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report), flush=True)
    return 1 if error else 0


if __name__ == '__main__':
    raise SystemExit(main())
