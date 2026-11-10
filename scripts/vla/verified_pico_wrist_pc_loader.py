#!/usr/bin/env python3
"""Load wrist-trial PC modules from a pinned snapshot before invocation.

Run with ``python3 -I -B``. ``--check`` is local; ``--run`` delegates to the
single-wrist launcher with current operator confirmation and its checks. The
interpreter, bootstrap before its self-check, external libraries, shell helpers,
robot runtime and physical environment are outside its guarantee. It does not
enable SmolVLA or direct guard dispatch and cannot certify stopping.
"""
import argparse
import contextlib
import hashlib
import importlib
import importlib.abc
import importlib.machinery
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
MAX_FILE = 16 * 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024
PC_MODULES = {
    'trial_launcher': 'scripts/vla/run_pico_wrist_native_trial.py',
    'review_binding': 'scripts/vla/pico_wrist_review_binding.py',
    'full_passive_check': 'scripts/vla/check_pico_wrist_full_passive.py',
    'bridge_check': 'scripts/vla/check_arm_native_bridge_live.py',
    'arm_preflight': 'scripts/vla/check_arm_from_pico_supervised.py',
    'head_launcher': 'scripts/vla/run_head_from_pico_supervised.py',
    'head_admission': 'scripts/vla/head_from_pico_check.py',
    'estop_reader': 'scripts/collect_estop_available_readonly.py',
    'pico_cc_mode': 'scripts/teleoperation/pico_cc_mode.py',
    'verified_pc_loader': 'scripts/vla/verified_pico_wrist_pc_loader.py',
    'model_decision': 'scripts/vla/pico_wrist_model_decision.py',
}
PC_DATA_SOURCES = {
    'model_live_relay': 'scripts/vla/run_ball_live_shadow.py',
    'model_live_adapter': 'scripts/vla/live_ball_observation_adapter.py',
    'model_live_guard': 'scripts/vla/ball_arm_preview_guard.py',
    'model_live_collector': 'scripts/vla/passive_episode_remote.py',
    'model_live_observations': 'scripts/vla/prepare_ball_observations.py',
    'model_live_audit': 'scripts/vla/audit_ball_arm_proposals.py',
    'model_live_profile': 'scripts/vla/runtime/cruzr_s2_vla_profile.json',
    'model_server_wrapper': 'scripts/vla/smolvla_ball_server/shadow_live_inference.sh',
    'model_server_inference': 'scripts/vla/smolvla_ball_server/shadow_live_inference.py',
    'model_server_failed_eval': 'scripts/vla/smolvla_ball_server/evaluate_failed_offline.py',
    'model_server_train_eval': 'scripts/vla/smolvla_ball_server/evaluate_train_offline.py',
    'model_server_train': 'scripts/vla/smolvla_ball_server/train_offline.py',
}
BUNDLE_PATHS = {
    'metamove_head_probe': 'scripts/vla/runtime/metamove_head_probe.py',
    'head_from_pico_readonly': 'scripts/vla/runtime/head_from_pico_readonly.py',
    'arm_from_pico_supervised': 'scripts/vla/runtime/arm_from_pico_supervised.py',
    'scenario1_request_ids': 'scripts/box_handling/scenario1_request_ids.py',
    'pico_wrist_action_client': 'scripts/vla/pico_wrist_action_client.py',
    'prepare_pico_wrist_native_probe': 'scripts/vla/prepare_pico_wrist_native_probe.py',
    'arm_native_lease_bridge': 'scripts/vla/arm_native_lease_bridge.py',
    'pico_wrist_native_stage': 'scripts/vla/runtime/pico_wrist_native_stage.py',
    'pico_wrist_native_worker': 'scripts/vla/runtime/pico_wrist_native_worker.py',
    'pico_wrist_trial_admission': 'scripts/vla/pico_wrist_trial_admission.py',
    'archive_canceled_pico_wrist_731084': 'scripts/vla/runtime/archive_canceled_pico_wrist_731084.py',
    'pico_wrist_native_coordinator': 'scripts/vla/runtime/pico_wrist_native_coordinator.py',
    'pico_wrist_pc_heartbeat': 'scripts/vla/pico_wrist_pc_heartbeat.py',
    'pico_wrist_verified_stream': 'scripts/vla/pico_wrist_verified_stream.py',
    'pico_wrist_docker_launcher': 'scripts/vla/runtime/pico_wrist_docker_launcher.py',
}
BUNDLED_MODULES = frozenset(BUNDLE_PATHS)
MODEL_ARM = ('R_shoulder_pitch_joint', 'R_shoulder_roll_joint', 'R_shoulder_yaw_joint',
             'R_elbow_roll_joint', 'R_elbow_yaw_joint', 'R_wrist_pitch_joint', 'R_wrist_roll_joint')


def _object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError('duplicate_json_key')
        obj[key] = value
    return obj


def _json(raw):
    return json.loads(raw, object_pairs_hook=_object)


def _read(path):
    # Each file is consumed once; use these same in-memory bytes afterwards.
    with path.open('rb') as stream:
        raw = stream.read(MAX_FILE + 1)
    if len(raw) > MAX_FILE:
        raise ValueError('snapshot_file_too_large:' + path.name)
    return raw


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _inside(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _exact_origin(origin_text, root, relative):
    """Require the expected canonical checkout file, with no symlink aliases."""
    expected = root / relative
    if origin_text != str(expected) or expected.resolve(strict=True) != expected:
        raise ValueError('source_origin_not_exact:' + relative)
    return expected


def _check_model_evidence(directory, evidence, files):
    """Check retained model evidence; this does not attest its producer."""
    if (not isinstance(evidence, dict) or set(evidence) !=
            {'schema', 'receipt_sha256', 'decision_sha256', 'task_sha256'} or
            evidence['schema'] != 'pico_wrist_model_evidence_v1'):
        raise ValueError('invalid_model_wrist_evidence')
    for name, field in (('receipt.json', 'receipt_sha256'),
                        ('decision.json', 'decision_sha256'), ('task.xml', 'task_sha256')):
        raw = _read(directory/name)
        if _sha(raw) != evidence[field]:
            raise ValueError('model_wrist_evidence_changed:' + name)
        files[name] = raw
    receipt, decision, manifest = (_json(files[name]) for name in
                                    ('receipt.json', 'decision.json', 'manifest.json'))
    names = {'manifest.json', 'task.xml', 'decision.json', 'robot.urdf', 'transmissions.yaml'}
    if (not isinstance(receipt, dict) or set(receipt) !=
            {'schema', 'sha256', 'model_sha256', 'image_sha256', 'image_bytes_retained',
             'physical_control_qualified', 'physical_commands_sent'} or
            receipt['schema'] != 'cruzr_model_wrist_artifact_v1' or
            receipt['image_bytes_retained'] is not False or
            receipt['physical_control_qualified'] is not False or
            type(receipt['physical_commands_sent']) is not int or receipt['physical_commands_sent'] != 0 or
            not isinstance(receipt['sha256'], dict) or set(receipt['sha256']) != names or
            any(receipt['sha256'][name] != _sha(files[name]) for name in names)):
        raise ValueError('invalid_model_wrist_receipt')
    candidate, state = manifest['candidate'], manifest['input']['canonical_joint_state']
    state_names, positions = state['name'], state['position']
    if (not isinstance(state_names, list) or len(state_names) != 20 or
            len(set(state_names)) != 20 or not isinstance(positions, list) or len(positions) != 20 or
            not set(MODEL_ARM).issubset(state_names)):
        raise ValueError('invalid_model_wrist_state')
    initial = [positions[state_names.index(name)] for name in MODEL_ARM]
    values, deltas = decision['model_action_original'], decision['model_arm_deltas_rad']
    target = candidate['target_rad']
    if (not isinstance(values, list) or len(values) != 8 or
            not isinstance(deltas, list) or len(deltas) != 7 or
            not isinstance(target, list) or len(target) != 7 or
            any(type(x) not in (int, float) or not math.isfinite(x)
                for x in values + deltas + target + initial) or
            candidate['arm_joint_order'] != list(MODEL_ARM) or
            decision['applied_arm_joint_order'] != list(MODEL_ARM) or
            candidate['moved_axis'] != MODEL_ARM[-1] or candidate['step_rad_experimental'] != .01 or
            decision['applied_arm_target_rad'] != target or
            decision['adaptation'] != 'hold_six_arm_axes_clip_positive_wrist_to_0.01_rad_hand_unchanged' or
            decision['physical_control_qualified'] is not False or
            type(decision['physical_commands_sent']) is not int or decision['physical_commands_sent'] != 0 or
            decision['model_sha256'] != receipt['model_sha256'] or decision['image_sha256'] != receipt['image_sha256'] or
            files['task.xml'] != candidate['xml'].encode('utf-8') or
            candidate['xml_sha256'] != _sha(files['task.xml']) or
            any(not math.isclose(values[i]-initial[i], deltas[i], rel_tol=1e-6, abs_tol=1e-6)
                for i in range(7)) or values[6]-initial[6] < .01 or
            any(not math.isclose(target[i], initial[i]+(.01 if i == 6 else 0),
                                 rel_tol=0, abs_tol=1e-12) for i in range(7))):
        raise ValueError('model_wrist_projection_mismatch')


def checked_snapshot(directory, expected_digest, *, root=ROOT, include_artifacts=False):
    """Verify the entire retained snapshot before compiling project modules."""
    if not isinstance(expected_digest, str) or not re.fullmatch('[0-9a-f]{64}', expected_digest):
        raise ValueError('expected_binding_sha256_required')
    directory, root = Path(directory), Path(root).resolve()
    binding_raw = _read(directory / 'review-binding.json')
    if _sha(binding_raw) != expected_digest:
        raise ValueError('review_binding_changed')
    binding = _json(binding_raw)
    fields = {'schema', 'bundle_evidence_sha256', 'review_sha256', 'scope',
              'physical_control_qualified', 'reviewer_identity_authenticated',
              'loaded_runtime_or_firmware_verified', 'movement_commands'}
    if (not isinstance(binding, dict) or set(binding) not in
            (fields, fields | {'model_wrist_evidence'}) or
            binding['schema'] != 'pico_wrist_technical_review_binding_v1' or
            binding['scope'] != 'retained_controlled_source_bytes_and_supplied_review_only' or
            binding['physical_control_qualified'] is not False or
            binding['reviewer_identity_authenticated'] is not False or
            binding['loaded_runtime_or_firmware_verified'] is not False or
            type(binding['movement_commands']) is not int or binding['movement_commands'] != 0):
        raise ValueError('invalid_review_binding')
    if _sha(_read(directory / 'technical-review.txt')) != binding['review_sha256']:
        raise ValueError('technical_review_changed')
    index_raw = _read(directory / 'bundle-evidence.json')
    if _sha(index_raw) != binding['bundle_evidence_sha256']:
        raise ValueError('bundle_evidence_index_changed')
    index = _json(index_raw)
    if (not isinstance(index, dict) or index.get('schema') != 'pico_wrist_bundle_evidence_v1'
            or not isinstance(index.get('sha256'), dict)
            or not isinstance(index.get('source_origins'), dict)
            or not isinstance(index.get('pc_source_origins'), dict)):
        raise ValueError('invalid_bundle_evidence_index')
    required_files = ({'bundle-host.py', 'bundle-guard.py', 'bundle-worker.py',
                       'manifest.json', 'robot.urdf', 'transmissions.yaml',
                       'pc-source-askpass_script'} |
                      {'pc-source-' + name for name in set(PC_MODULES) | set(PC_DATA_SOURCES)} |
                      {'source-' + name + '.py' for name in BUNDLED_MODULES})
    if set(index['sha256']) != required_files:
        raise ValueError('bundle_evidence_file_set_changed')
    files, total = {}, 0
    for name, digest in index['sha256'].items():
        if (not isinstance(name, str) or Path(name).name != name or name in ('.', '..')
                or not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest)):
            raise ValueError('invalid_evidence_filename_or_digest')
        raw = _read(directory / name)
        total += len(raw)
        if total > MAX_TOTAL:
            raise ValueError('snapshot_too_large')
        if _sha(raw) != digest:
            raise ValueError('bundle_evidence_changed:' + name)
        files[name] = raw
    if 'model_wrist_evidence' in binding:
        _check_model_evidence(directory, binding['model_wrist_evidence'], files)
    # Require the complete known local Python closure, not a selectable subset.
    if set(index['source_origins']) != BUNDLED_MODULES:
        raise ValueError('bundle_source_set_changed')
    expected_pc = set(PC_MODULES) | set(PC_DATA_SOURCES) | {'askpass_script'}
    if set(index['pc_source_origins']) != expected_pc:
        raise ValueError('pc_source_set_changed')
    modules = {}
    for key, rel in PC_MODULES.items():
        origin = _exact_origin(index['pc_source_origins'][key], root, rel)
        raw = files.get('pc-source-' + key)
        if raw is None:
            raise ValueError('pc_source_missing:' + key)
        if key == 'verified_pc_loader':
            # This consistency check is after bootstrap execution and is not
            # an attestation of the already-running bootstrap or interpreter.
            if _sha(_read(Path(__file__).resolve())) != _sha(raw):
                raise ValueError('bootstrap_file_changed')
            continue
        modules[origin.stem] = (raw, str(origin))
    for key, rel in PC_DATA_SOURCES.items():
        _exact_origin(index['pc_source_origins'][key], root, rel)
    _exact_origin(index['pc_source_origins']['askpass_script'], root, 'scripts/cruzr_recover_to_home.sh')
    for name, rel in BUNDLE_PATHS.items():
        raw = files.get('source-' + name + '.py')
        origin = _exact_origin(index['source_origins'][name], root, rel)
        if raw is None:
            raise ValueError('bundle_source_missing:' + name)
        if name in modules:
            raise ValueError('duplicate_project_module:' + name)
        modules[name] = (raw, str(origin))
    # Compile every candidate before running any of them. This catches syntax
    # errors and ensures the code objects come from the verified byte copies.
    compiled = {name: (compile(raw, origin, 'exec', dont_inherit=True), origin, _sha(raw))
                for name, (raw, origin) in modules.items()}
    if include_artifacts:
        return compiled, files, index_raw, binding_raw
    return compiled


class VerifiedFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def __init__(self, modules, root=ROOT):
        self.modules, self.root = modules, Path(root).resolve()
        self.loaded = set()

    def find_spec(self, fullname, path=None, target=None):
        if fullname in self.modules:
            return importlib.util.spec_from_loader(fullname, self, origin=self.modules[fullname][1])
        # Reject unlisted project source found through paths inserted by a
        # verified module. Standard and third-party dependencies are not pinned.
        found = importlib.machinery.PathFinder.find_spec(fullname, path)
        origin = None if found is None else found.origin
        if isinstance(origin, str) and _inside(Path(origin).resolve(), self.root):
            raise ImportError('unbound_project_module:' + fullname)
        return None

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        code, origin, _ = self.modules[module.__name__]
        module.__file__ = origin
        exec(code, module.__dict__)
        self.loaded.add(module.__name__)


@contextlib.contextmanager
def verified_pc_environment(modules, *, root=ROOT, artifacts=None):
    """Keep the verified finder active while a caller uses the entrypoint.

    Only the caller's verified project modules are covered. Calling an entrypoint
    is not authorization, and the physical gates remain unchanged.
    """
    if not sys.flags.isolated:
        raise RuntimeError('isolated_python_required_use_python3_-I_-B')
    for name, module in tuple(sys.modules.items()):
        if name in modules:
            raise RuntimeError('bound_module_already_loaded:' + name)
        origin = getattr(module, '__file__', None)
        if name != '__main__' and isinstance(origin, str) and _inside(Path(origin).resolve(), Path(root).resolve()):
            raise RuntimeError('project_module_already_loaded:' + name)
    finder = VerifiedFinder(modules, root)
    finder.verified_artifacts = artifacts
    sys.meta_path.insert(0, finder)
    try:
        # Import all transitive PC entrypoints even when a particular CLI branch
        # loads them lazily; imports do not call preflight, ROS or launch().
        entrypoint = importlib.import_module('run_pico_wrist_native_trial')
        for name in ('check_arm_from_pico_supervised', 'check_pico_wrist_full_passive',
                     'pico_wrist_review_binding'):
            importlib.import_module(name)
        yield entrypoint, finder
    finally:
        sys.meta_path.remove(finder)


def check_loaded_modules(modules, *, root=ROOT):
    """Import real PC entrypoints, without invoking preflight or robot access."""
    with verified_pc_environment(modules, root=root) as (_, finder):
        return sorted(finder.loaded)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--run', action='store_true')
    parser.add_argument('--binding', required=True, type=Path)
    parser.add_argument('--binding-sha256', required=True)
    parser.add_argument('--physical-confirmed', action='store_true',
                        help='operator reports current conditions; does not open a gate')
    parser.add_argument('--model-live', action='store_true',
                        help='reserved two-phase model path; physical dispatch remains blocked')
    parser.add_argument('--incident-731084', action='store_true',
                        help='reserved exact-predecessor admission; physical dispatch remains blocked')
    args = parser.parse_args(argv)
    if args.check and args.physical_confirmed:
        parser.error('--physical-confirmed is only supported with --run')
    if args.run and not args.physical_confirmed:
        parser.error('--run requires current operator-reported physical conditions')
    if args.model_live and not args.run:
        parser.error('--model-live is only supported with --run')
    if args.incident_731084 and not args.model_live:
        parser.error('--incident-731084 requires --model-live')
    try:
        if args.model_live:
            raise RuntimeError('model_wrist_dispatch_not_enabled')
        modules, files, index_raw, binding_raw = checked_snapshot(
            args.binding, args.binding_sha256, include_artifacts=True)
        if args.run and 'receipt.json' in files:
            raise RuntimeError('model_wrist_dispatch_not_enabled')
        with verified_pc_environment(modules, artifacts=(files, index_raw, binding_raw)) as (entrypoint, finder):
            if args.check:
                print(json.dumps({'status': 'VERIFIED_PC_IMPORT_ONLY', 'modules_loaded': sorted(finder.loaded),
                                  'physical_control_qualified': False, 'movement_commands': 0,
                                  'limits': ['bootstrap_and_interpreter_trusted',
                                             'external_dependencies_not_attested',
                                             'no_preflight_or_robot_access',
                                  'direct_and_vla_dispatch_blocked']}))
            else:
                model_options = {'model_mode': True} if args.model_live else {}
                if args.incident_731084:
                    model_options['incident_731084'] = True
                result = entrypoint.run_candidate(args.binding/'manifest.json',
                    args.binding/'robot.urdf', args.binding/'transmissions.yaml', True,
                    binding_path=args.binding, binding_sha256=args.binding_sha256,
                    verified_pc={'finder':finder, 'files':files, 'index_raw':index_raw,
                                 'binding_raw':binding_raw}, **model_options)
                print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, ImportError, SyntaxError) as exc:
        print('VERIFIED_PC_LOAD_FAILED: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
