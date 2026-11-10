#!/usr/bin/env python3
"""Run the arm supervisor's passive check only; cannot send a robot goal."""
import argparse
import json
from pathlib import Path
import sys
import time
import uuid

import run_head_from_pico_supervised as head
from head_from_pico_check import execute

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / 'scripts/vla/runtime'
ARM_TASK = '/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/move_components_json.xml'
ARM_TASK_SHA = 'bfcfc097dfefb3e81fcb2acc913d7db55545b3ea3b853b345b9ba1836c01b797'
SPS_TRANSMISSIONS = '/opt/walker/config_mc_cruzr_s2_v1_sps/share/config_mc_cruzr_s2_v1_sps/config/ecat_hardware/transmissions.yaml'
SPS_SHA = '7c7e0760c274c59237ca5787bc2e75096692ee92c43bcf79f61cbad2cfa0f29c'
EVIDENCE_ROOT = ROOT.parent / 'Humanoide-vla-evidence' / 'ARM_PICO_SUPERVISED_CHECK'


def source_bundle():
    sources = {
        'metamove_head_probe': (RUNTIME / 'metamove_head_probe.py').read_text(),
        'head_from_pico_readonly': (RUNTIME / 'head_from_pico_readonly.py').read_text(),
        'head_from_pico_supervised': (RUNTIME / 'arm_from_pico_supervised.py').read_text(),
    }
    for source in sources.values():
        compile(source, '<arm-passive-source>', 'exec')
    code = 'import sys,types\n'
    for name in ('metamove_head_probe', 'head_from_pico_readonly', 'head_from_pico_supervised'):
        code += ('m=types.ModuleType(' + repr(name) + ')\n'
                 'exec(' + repr(sources[name]) + ',m.__dict__)\n'
                 'sys.modules[' + repr(name) + ']=m\n')
    code += ('import json\n'
             'print(json.dumps({"event":"BRIDGE_READY"}),flush=True)\n'
             'session=json.loads(sys.stdin.readline())\n'
             'raise SystemExit(m.main(session,dry_run=True))\n')
    return code


def preflight():
    mode, started, container = head.preflight()
    discovered = execute('motion', ['docker', 'ps', '--format', '{{.Names}}'])
    motion, _ = head.admission.parse_containers(discovered)
    hardware = [name for name in discovered.get('stdout', '').splitlines() if name == 'walker-motion.hw-1']
    if len(hardware) != 1:
        raise RuntimeError('hardware_container_not_unique')
    for component in (motion, hardware[0]):
        profile = execute('motion', ['docker', 'exec', component, 'printenv', 'HW_TYPE'])
        if profile.get('returncode') != 0 or profile.get('stdout', '').strip() != 'cruzr_s2_v1_sps':
            raise RuntimeError('sps_profile_missing_or_changed')
    limits = execute('motion', ['docker', 'exec', hardware[0], 'sha256sum', SPS_TRANSMISSIONS])
    if limits.get('returncode') != 0 or limits.get('stdout', '').split()[:1] != [SPS_SHA]:
        raise RuntimeError('sps_transmission_limits_missing_or_changed')
    task = execute('motion', ['docker', 'exec', motion, 'sha256sum', ARM_TASK])
    if task.get('returncode') != 0 or task.get('stdout', '').split()[:1] != [ARM_TASK_SHA]:
        raise RuntimeError('dynamic_arm_task_missing_or_changed')
    return mode, started, container


def check():
    token = uuid.uuid4().hex
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    outdir = EVIDENCE_ROOT / ('check-' + token)
    outdir.mkdir(mode=0o700)
    print('EVIDENCIA=' + str(outdir), flush=True)
    mode, started, container = preflight()
    session = {'schema': 'cruzr_head_pico_preflight_v1', 'task_sha256': ARM_TASK_SHA,
               'pico_sha256': head.admission.PICO_SHA, 'work_mode': mode,
               'operator_confirmed': False, 'controller_status_writers_checked': True,
               'age_at_handoff_s': 0.0, 'session_id': token, 'mode': 'check'}
    sentinel = 'CODE_END_' + uuid.uuid4().hex
    rc, events = head.stream_remote(head.remote_command(container, sentinel), source_bundle(),
                                    sentinel, session, started, outdir)
    passed = (rc == 0 and events.count('pre_dispatch_ready') == 1 and
              events.count('PICO_ARM_SUPERVISED_DRY_RUN_PASSED') == 1 and
              not any(x in events for x in ('dispatch', 'UNRESOLVED', 'UNRESOLVED_MONITORING',
                                             'OPERATOR_ALERT', 'LOCAL_COMMUNICATION_ALERT', 'OUTPUT_INVALID')))
    (outdir / 'result.json').write_text(json.dumps({'returncode': rc, 'events': events,
        'movement_commands': 0 if passed else None, 'physical_control_qualified': False}, indent=2)+'\n')
    if not passed:
        raise RuntimeError('arm_passive_check_failed_no_motion')
    print('ARM_PASSIVE_CHECK_PASSED; no physical command sent.', flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true')
    group.add_argument('--run', action='store_true')
    args = parser.parse_args(argv)
    if args.run:
        print('BLOCKED: this passive checker cannot dispatch a robot goal', file=sys.stderr)
        return 2
    try:
        check()
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print('ARM_CHECK_FAILED: ' + str(exc), file=sys.stderr, flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
