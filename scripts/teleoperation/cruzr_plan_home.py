#!/usr/bin/env python3
"""HOME planner/auditor for empty clamps. Offline only; never installs or moves."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--audit-model', action='store_true', help='Audit synthetic HOME and PICO; no scene or live state assumed')
    mode.add_argument('--plan', action='store_true', help='Plan from archived --state and --scene')
    parser.add_argument('--state', type=Path)
    parser.add_argument('--scene', type=Path)
    parser.add_argument('--output', type=Path, required=True, help='New JSON report; never overwritten')
    parser.add_argument('--package-root', type=Path, default=ROOT/'cruzr_s2_description_splint/cruzr_s2_description')
    parser.add_argument('--urdf', type=Path, help='Defaults to supplied splint URDF inside package')
    parser.add_argument('--timeout', type=float, default=30.)
    parser.add_argument('--seed', type=int, default=20260910)
    parser.add_argument('--timing-law', choices=('quintic', 'cubic-rest'), default='quintic',
                        help='Offline timing: cubic-rest matches the audited native numeric formula only')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output already exists')
    if args.plan and (args.state is None or args.scene is None):
        parser.error('--plan requires --state and --scene')
    if args.audit_model and (args.state is not None or args.scene is not None):
        parser.error('--audit-model uses synthetic references; --state/--scene belong to --plan')
    sources = [Path(__file__), *Path(__file__).with_name('general_home').glob('*.py')]
    sources.extend([Path(__file__).with_name('review_clamp_trajectory_optimization.py'),
                    ROOT/'scripts/vla/analyze_vla_fixture_collision_e4_1c.py',
                    Path(__file__).with_name('cruzr_pico_to_home_owner_gate.py'),
                    Path(__file__).with_name('general_home')/'requirements.txt'])
    code_hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    try:
        import numpy as np
        from general_home.geometry import RobotGeometry, digest
        from general_home.inputs import load_state, load_json, timestamp
        from general_home.planner import plan, Validator, BudgetExceeded
        from cruzr_pico_to_home_owner_gate import JOINT_ORDER, PICO_VARIANTS
    except ImportError as exc:
        print('ERROR: use .venv/general-home/bin/python after installing '
              'scripts/teleoperation/general_home/requirements.txt. '+str(exc), file=sys.stderr)
        return 2
    urdf = args.urdf or args.package_root/'urdf/cruzr_s2_v1/cruzr_s2_v1.urdf'
    blockers = ['motion_trajectory_adapter_not_qualified', 'stopping_envelope_not_measured',
                'physical_mount_registration_not_qualified', 'controller_dynamics_not_qualified',
                'payload_and_support_stability_not_qualified',
                'archived_inputs_are_not_execution_authorization', 'boot_home_integration_pending']
    source_hashes = {}
    if args.plan:
        source_hashes = {str(p.resolve()): digest(p) for p in (args.state, args.scene)}
        state, state_info, auxiliary = load_state(args.state)
        scene = load_json(args.scene)
        if scene.get('schema') != 'cruzr-general-home-scene-v1':
            raise ValueError('Expected cruzr-general-home-scene-v1')
        scene_age = timestamp(scene.get('captured_at'))
    else:
        state_info, auxiliary = {'source': 'synthetic_model_references', 'live_authorization': False}, {}
        scene = {'frame_id': 'base_link', 'complete': True, 'objects': []}
        scene_age = None
        blockers.append('audit_scene_is_empty_and_synthetic')
    geometry = RobotGeometry(urdf, args.package_root, scene, auxiliary)
    if args.audit_model:
        validator = Validator(geometry)
        audit = {}
        for name, q in dict(HOME=np.zeros(20), **PICO_VARIANTS).items():
            q = np.asarray(q)
            audit[name] = dict(conflicts=validator.failures(q), within_limits=bool(
                ((q >= geometry.lower) & (q <= geometry.upper)).all()))
        result = dict(schema='cruzr-general-home-model-audit-v1', status='MODEL_AUDIT', references=audit, physical_approval=False,
                      installable=False, movement_commands=0)
    else:
        result = plan(geometry, state, timeout=args.timeout, seed=args.seed, timing_law=args.timing_law)
        # Retain the reported 5 degree / 2 mm / 0..40 mm uncertainty scenario.
        # This second check never converts the nominal candidate into approval.
        if result['status'] in ('GEOMETRIC_CANDIDATE', 'ALREADY_HOME_NUMERIC'):
            angular = 2*np.sin(np.deg2rad(5)/2)*geometry.weights.sum(axis=1)
            axial = np.array([.04*sum('hand_link' in name for name in pair) for pair in geometry.labels])
            errors = angular+axial+.004  # 2 mm per body, conservatively combined.
            import time
            robust = Validator(geometry, extra_margin=errors, deadline=time.monotonic()+args.timeout)
            path = [np.array(q) for q in result['waypoints_rad']]
            robust_ok = False
            try:
                robust_ok = all(robust.state(q) for q in path) and all(
                    robust.edge(a, b) for a, b in zip(path, path[1:]))
                result['error_scenario_separated'] = robust_ok
                if not robust_ok:
                    blockers.append('declared_error_scenario_not_separated')
            except BudgetExceeded:
                result['error_scenario_separated'] = False
                blockers.append('error_scenario_check_timeout')
            independent = Validator(geometry, extra_margin=errors, deadline=time.monotonic()+args.timeout)
            independent_ok = False
            try:
                independent_ok = robust_ok and all(independent.independent_progress(a,b)
                    for a,b in zip(path,path[1:]))
            except BudgetExceeded:
                blockers.append('independent_joint_progress_check_timeout')
            result['independent_joint_progress'] = dict(separated=independent_ok,
                scope='all positions inside each joint endpoint box, with declared error margins',
                covers_overshoot=False, physical_execution_verified=False,
                state_queries=independent.state_queries,
                unresolved_boxes=independent.unresolved_edges)
            if not independent_ok:
                blockers.append('independent_joint_progress_not_separated')
    if geometry.diagnostics['convex_enclosures']:
        blockers.append('open_meshes_use_conservative_convex_enclosures')
    if geometry.diagnostics['visual_fallback'] or geometry.diagnostics['links_without_geometry']:
        blockers.append('complete_physical_geometry_coverage_not_qualified')
    if geometry.assumed_auxiliary:
        blockers.append('auxiliary_joint_positions_assumed_zero')
    if geometry.diagnostics['nonpositive_velocity_limits']:
        blockers.append('urdf_has_nonpositive_dynamic_limits')
    if not geometry.source_files_unchanged() or any(digest(p) != value for p, value in source_hashes.items()):
        raise ValueError('Input/model changed while planning; discard report')
    if any(digest(p) != value for p, value in code_hashes.items()):
        raise ValueError('Planner source changed while planning; discard report')
    import importlib.metadata
    versions = {name: importlib.metadata.version(name) for name in ('numpy','scipy','trimesh','python-fcl','rtree')}
    result.update(joint_order=JOINT_ORDER, model=geometry.diagnostics,
        state_info=state_info, scene_age_seconds=scene_age, activation_blockers=blockers,
        scene_info=dict(source=scene.get('source','synthetic_audit'),
                        captured_at=scene.get('captured_at'),assertions_from_input_only=True),
        source_sha256=dict(geometry.manifest, **source_hashes, **code_hashes),
        dependency_versions=versions, physical_approval=False, installable=False, movement_commands=0)
    encoded = json.dumps(result, indent=2, allow_nan=False)+'\n'
    with args.output.open('x') as f:
        f.write(encoded)
    print(json.dumps(dict(status=result['status'], output=str(args.output),
        nominal_seconds=result.get('nominal_seconds'), physical_approval=False, movement_commands=0)))
    return 0 if args.audit_model or result['status'] in ('GEOMETRIC_CANDIDATE','ALREADY_HOME_NUMERIC') else 3


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        print('ERROR: '+str(exc), file=sys.stderr)
        raise SystemExit(2)
