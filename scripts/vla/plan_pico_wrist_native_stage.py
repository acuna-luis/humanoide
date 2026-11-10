#!/usr/bin/env python3
"""Create a reviewable, non-executing staging plan for the native wrist probe.

No SSH, robot files, ROS client, movement or automatic deletion. The planned
ROSA action client has not been connected to the live PICO/v4 corridor monitor;
this plan cannot install, authorize or run the candidate.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from prepare_pico_wrist_native_probe import TASK_ROOT, validate

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SOURCES = {
    'pico_wrist_action_client.py': REPO / 'scripts/vla/pico_wrist_action_client.py',
    'scenario1_request_ids.py': REPO / 'scripts/box_handling/scenario1_request_ids.py',
}
EXPECTED = {
    'pico_wrist_action_client.py': '7cef03f8ec1a93d011a898409544a7f3d7eee4d1a8eb6458abbe71d266df7512',
    'scenario1_request_ids.py': '904adfb55e621fde1bd03d8e7fd96b61bf1866e5a0b94f92b36eb53999d4092d',
}


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def build_plan(manifest, urdf_text, transmission_text, sources=SOURCES):
    validate(manifest, urdf_text, transmission_text)
    observed = {name: sha256_bytes(path.read_bytes()) for name, path in sources.items()}
    if observed != EXPECTED:
        raise ValueError('native_box_transport_source_changed')
    candidate = manifest['candidate']
    task_path = candidate['runtime_path']
    digest = candidate['xml_sha256']
    if task_path != TASK_ROOT + candidate['task_name'] + '.xml':
        raise ValueError('unexpected_task_destination')
    # The previously verified native runner uses /tmp shared between host and
    # container; this plan requires checking that property again at staging.
    stage_dir = '/tmp/cruzr-pico-v4-wrist-' + digest[:16]
    return {
        'schema': 'cruzr_pico_v4_wrist_stage_plan_v1',
        'status': 'PLAN_ONLY_NOT_INSTALLED_NOT_EXECUTABLE',
        'robot_connections': 0, 'remote_writes': 0, 'movement_commands': 0,
        'physical_control_qualified': False,
        'target': {'host': 'Motion', 'container_role': 'manipulation_robot_app',
                   'task_path': task_path, 'task_name': candidate['task_name'],
                   'expected_sha256': digest, 'xml': candidate['xml']},
        'planned_support_dir': stage_dir,
        'transport_sources': observed,
        'recheck_hashes': {'meta_move_so': manifest['expected_meta_move_sha256'],
                           'urdf': manifest['input']['urdf_sha256'],
                           'sps_transmissions': manifest['input']['transmissions_sha256']},
        'planned_goal': candidate['goal'],
        'staging_steps': [
            'rediscover Motion containers and controller profile; verify current authorized physical conditions',
            're-read source and health checks and compare the complete current named posture to the reviewed reference',
            'independently compare exact URDF, SPS transmissions and MetaMove bytes with the planned hashes',
            'create a new private support directory and stage exact manifest, XML and pinned native client sources',
            'require a previously absent nonsymlink task path and create it without overwrite',
            'read back and verify exact installed bytes and preserve an installation receipt for selective rollback',
            'verify task availability and run the reviewed passive preflight; do not dispatch an action',
        ],
        'missing_before_run': [
            'a reviewed PICO/v4 launcher joining native ROSA transport to the live whole-body/hand corridor guard',
            'a bounded guard heartbeat/lease, fault handling, terminal observation and no retry after uncertain receipt',
            'physical scene and v4 hand geometry, trajectory, native planner and actual stopping behavior',
            'current hardware/profile/controller identity and operator conditions at the instant of movement',
        ],
        'rollback': ('Only remove the exact task and support files created by a future staging receipt, '
                     'after verifying their hashes and that no later change depends on them; do not '
                     'modify task_list, SDK, controllers, modes or unrelated files.'),
        'limitations': [
            'This is a local staging plan, not a script that installs or executes the candidate.',
            'The transport timeout and cancellation request do not prove physical braking.',
            'This fixed wrist action is independent of SmolVLA and does not open any VLA gate.',
            'Diagnostic SPS endpoint margin is not a certified safety requirement or execution approval.',
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--manifest', type=Path)
    group.add_argument('--run', action='store_true')
    parser.add_argument('--urdf', type=Path)
    parser.add_argument('--transmissions', type=Path)
    parser.add_argument('--output', type=Path, help='new local plan JSON; stdout if omitted')
    args = parser.parse_args(argv)
    if args.run:
        print('BLOCKED: plan has no robot connection or physical execution', file=sys.stderr)
        return 2
    try:
        if args.urdf is None or args.transmissions is None:
            raise ValueError('--urdf_and_transmissions_required')
        manifest = json.loads(args.manifest.read_bytes())
        plan = build_plan(manifest, args.urdf.read_bytes().decode('utf-8'),
                          args.transmissions.read_bytes().decode('utf-8'))
        output = json.dumps(plan, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
        if args.output is None:
            print(output, end='')
        else:
            with args.output.open('x', encoding='utf-8') as stream:
                stream.write(output)
            print(json.dumps({'status': plan['status'], 'output': str(args.output),
                              'movement_commands': 0}))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('PLAN_FAILED: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
