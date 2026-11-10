#!/usr/bin/env python3
"""Bind a written technical review to a snapshot of the wrist-trial sources.

This is a local integrity tool, not a review, an authorization, or a robot
controller. It copies exact supplied inputs, the review, source files, and
three generated bundles into a new directory. No network or ROS is used.
Physical execution remains blocked by the existing launcher and runtime gates.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

import prepare_pico_wrist_native_probe as probe
import run_pico_wrist_native_trial as launcher

MAX_REVIEW_BYTES = 128 * 1024
MODEL_FILES = ('manifest.json', 'task.xml', 'decision.json', 'robot.urdf',
               'transmissions.yaml', 'receipt.json')


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _write_new(path, data):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    if path.read_bytes() != data:
        raise RuntimeError('binding_readback_mismatch:' + path.name)


def _model_snapshot(directory, receipt_sha256):
    # Validate exactly the bytes subsequently retained, not paths that can
    # change between verification and copying. The verifier is local code and
    # is not itself attested by this binding.
    import prepare_ball_native_arm_step as model
    data = {}
    for name in MODEL_FILES:
        with (Path(directory)/name).open('rb') as stream:
            data[name] = stream.read(16 * 1024 * 1024 + 1)
        if len(data[name]) > 16 * 1024 * 1024:
            raise ValueError('model_artifact_too_large:' + name)
    with tempfile.TemporaryDirectory(prefix='wrist-model-verification-') as tmp:
        for name, raw in data.items():
            (Path(tmp)/name).write_bytes(raw)
        model.verify_model_wrist_artifact(tmp, receipt_sha256)
    return data


def create(output, manifest_path, urdf_path, transmissions_path, review_path, *,
           model_artifact=None, model_receipt_sha256=None):
    """Capture exact sources and the supplied review, without authorizing use."""
    output = Path(output)
    manifest_raw = Path(manifest_path).read_bytes()
    urdf_raw = Path(urdf_path).read_bytes()
    transmissions_raw = Path(transmissions_path).read_bytes()
    if (model_artifact is None) != (model_receipt_sha256 is None):
        raise ValueError('model_artifact_and_receipt_digest_required')
    model_data = None
    if model_artifact is not None:
        model_data = _model_snapshot(model_artifact, model_receipt_sha256)
        for name, raw in (('manifest.json', manifest_raw), ('robot.urdf', urdf_raw),
                          ('transmissions.yaml', transmissions_raw)):
            if model_data[name] != raw:
                raise ValueError('model_candidate_input_changed:' + name)
    review_raw = Path(review_path).read_bytes()
    if not 0 < len(review_raw) <= MAX_REVIEW_BYTES or not review_raw.strip():
        raise ValueError('review_text_empty_or_too_large')
    review_raw.decode('utf-8')
    probe.validate(json.loads(manifest_raw), urdf_raw.decode('utf-8'),
                   transmissions_raw.decode('utf-8'))
    host, guard, worker, sources = launcher.source_bundle(include_sources=True)
    pc_sources = launcher.controlled_pc_sources()
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    evidence_digest = launcher.retain_bundle_evidence(
        output, sources, host, guard, worker, manifest_raw, urdf_raw,
        transmissions_raw, pc_sources=pc_sources)
    _write_new(output/'technical-review.txt', review_raw)
    binding = {
        'schema': 'pico_wrist_technical_review_binding_v1',
        'bundle_evidence_sha256': evidence_digest,
        'review_sha256': _hash(review_raw),
        'scope': 'retained_controlled_source_bytes_and_supplied_review_only',
        'physical_control_qualified': False,
        'reviewer_identity_authenticated': False,
        'loaded_runtime_or_firmware_verified': False,
        'movement_commands': 0,
    }
    if model_data is not None:
        for name in ('decision.json', 'receipt.json', 'task.xml'):
            _write_new(output/name, model_data[name])
        binding['model_wrist_evidence'] = {
            'schema': 'pico_wrist_model_evidence_v1',
            'receipt_sha256': model_receipt_sha256,
            'decision_sha256': _hash(model_data['decision.json']),
            'task_sha256': _hash(model_data['task.xml']),
        }
    raw = (json.dumps(binding, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')
    _write_new(output/'review-binding.json', raw)
    fd = os.open(output, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return {'binding_sha256': _hash(raw), **binding}


def verify(output, expected_binding_sha256):
    """Verify a previously recorded binding against an independently held digest."""
    if (not isinstance(expected_binding_sha256, str) or
            len(expected_binding_sha256) != 64 or
            any(c not in '0123456789abcdef' for c in expected_binding_sha256)):
        raise ValueError('expected_binding_sha256_required')
    output = Path(output)
    raw = (output/'review-binding.json').read_bytes()
    if _hash(raw) != expected_binding_sha256:
        raise ValueError('review_binding_changed')
    binding = json.loads(raw)
    expected_fields = {'schema', 'bundle_evidence_sha256', 'review_sha256', 'scope',
                       'physical_control_qualified', 'reviewer_identity_authenticated',
                       'loaded_runtime_or_firmware_verified', 'movement_commands'}
    if (not isinstance(binding, dict) or set(binding) not in
            (expected_fields, expected_fields | {'model_wrist_evidence'}) or
            binding['schema'] != 'pico_wrist_technical_review_binding_v1' or
            binding['scope'] != 'retained_controlled_source_bytes_and_supplied_review_only' or
            binding['physical_control_qualified'] is not False or
            binding['reviewer_identity_authenticated'] is not False or
            binding['loaded_runtime_or_firmware_verified'] is not False or
            type(binding['movement_commands']) is not int or binding['movement_commands'] != 0):
        raise ValueError('invalid_review_binding')
    if _hash((output/'technical-review.txt').read_bytes()) != binding['review_sha256']:
        raise ValueError('technical_review_changed')
    launcher.verify_bundle_evidence(output, binding['bundle_evidence_sha256'])
    if 'model_wrist_evidence' in binding:
        evidence = binding['model_wrist_evidence']
        if (not isinstance(evidence, dict) or set(evidence) !=
                {'schema', 'receipt_sha256', 'decision_sha256', 'task_sha256'} or
                evidence['schema'] != 'pico_wrist_model_evidence_v1'):
            raise ValueError('invalid_model_wrist_evidence')
        data = _model_snapshot(output, evidence['receipt_sha256'])
        if (_hash(data['decision.json']) != evidence['decision_sha256'] or
                _hash(data['task.xml']) != evidence['task_sha256']):
            raise ValueError('model_wrist_evidence_changed')
        index_raw = (output/'bundle-evidence.json').read_bytes()
        if _hash(index_raw) != binding['bundle_evidence_sha256']:
            raise ValueError('bundle_evidence_index_changed_during_model_check')
        indexed = json.loads(index_raw)['sha256']
        for name in ('manifest.json', 'robot.urdf', 'transmissions.yaml'):
            if _hash(data[name]) != indexed[name]:
                raise ValueError('model_candidate_input_changed:' + name)
    return {'binding_sha256': expected_binding_sha256, **binding}


def compare_current(output, expected_binding_sha256, *, source_snapshot=None, pc_snapshot=None):
    """Compare current controlled files/bundles with the already verified binding.

    This is a point-in-time file comparison. It does not attest Python modules
    already loaded into memory, installed robot libraries or future execution.
    """
    result = verify(output, expected_binding_sha256)
    index = json.loads((Path(output)/'bundle-evidence.json').read_bytes())
    expected = index['sha256']
    host, guard, worker, sources = (launcher.source_bundle(include_sources=True)
                                    if source_snapshot is None else source_snapshot)
    pc_sources = launcher.controlled_pc_sources() if pc_snapshot is None else pc_snapshot
    current = {'bundle-host.py': host.encode('utf-8'),
               'bundle-guard.py': guard.encode('utf-8'),
               'bundle-worker.py': worker.encode('utf-8')}
    for name, (source, _) in sources.items():
        if not name.isidentifier() or not isinstance(source, str):
            raise ValueError('invalid_current_source')
        current['source-'+name+'.py'] = source.encode('utf-8')
    for name, (source, _) in pc_sources.items():
        if not name.isidentifier() or not isinstance(source, bytes):
            raise ValueError('invalid_current_pc_source')
        current['pc-source-'+name] = source
    expected_names = {name for name in expected if name.startswith(('source-', 'pc-source-', 'bundle-'))}
    if set(current) != expected_names:
        raise ValueError('current_controlled_source_set_changed')
    for name, data in current.items():
        if _hash(data) != expected[name]:
            raise ValueError('current_controlled_source_changed:' + name)
    return {**result, 'current_controlled_sources_match': True,
            'comparison_scope': 'point_in_time_file_bytes_not_loaded_runtime_or_future_execution'}


def compare_candidate_inputs(output, expected_binding_sha256, manifest_raw, urdf_raw, transmissions_raw,
                             *, source_snapshot=None, pc_snapshot=None):
    """Bind candidate input bytes as well as the current controlled sources.

    Only the bytes passed by the caller are compared; this does not prove that
    a later execution will use them or that robot-side files match these bytes.
    """
    result = compare_current(output, expected_binding_sha256, source_snapshot=source_snapshot,
                             pc_snapshot=pc_snapshot)
    index_raw = (Path(output)/'bundle-evidence.json').read_bytes()
    if _hash(index_raw) != result['bundle_evidence_sha256']:
        raise ValueError('bundle_evidence_index_changed_during_comparison')
    expected = json.loads(index_raw)['sha256']
    values = {'manifest.json': manifest_raw, 'robot.urdf': urdf_raw,
              'transmissions.yaml': transmissions_raw}
    for name, raw in values.items():
        if type(raw) is not bytes or _hash(raw) != expected.get(name):
            raise ValueError('candidate_input_changed:' + name)
    return {**result, 'candidate_input_bytes_match': True,
            'physical_control_qualified': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--create', type=Path, help='new local output directory')
    mode.add_argument('--verify', type=Path, help='existing local binding directory')
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--urdf', type=Path)
    parser.add_argument('--transmissions', type=Path)
    parser.add_argument('--review', type=Path, help='existing UTF-8 technical review')
    parser.add_argument('--model-artifact', type=Path, help='retain and verify model wrist decision artifact')
    parser.add_argument('--model-receipt-sha256', help='independently held artifact receipt SHA-256')
    parser.add_argument('--expected-binding-sha256')
    parser.add_argument('--compare-current', action='store_true',
                        help='with --verify, compare current controlled sources and bundles')
    args = parser.parse_args(argv)
    try:
        if args.create is not None:
            if any(value is None for value in (args.manifest, args.urdf, args.transmissions, args.review)):
                raise ValueError('manifest_urdf_transmissions_and_review_required')
            if args.expected_binding_sha256 is not None:
                raise ValueError('expected_digest_only_for_verify')
            if args.compare_current:
                raise ValueError('compare_current_only_for_verify')
            result = create(args.create, args.manifest, args.urdf, args.transmissions, args.review,
                            model_artifact=args.model_artifact,
                            model_receipt_sha256=args.model_receipt_sha256)
        else:
            if args.model_artifact is not None or args.model_receipt_sha256 is not None:
                raise ValueError('model_artifact_only_for_create')
            if args.review is not None:
                raise ValueError('review_path_only_for_create')
            inputs = (args.manifest, args.urdf, args.transmissions)
            if any(value is not None for value in inputs):
                if not args.compare_current or any(value is None for value in inputs):
                    raise ValueError('complete_candidate_inputs_require_compare_current')
                result = compare_candidate_inputs(args.verify, args.expected_binding_sha256,
                                                  *(path.read_bytes() for path in inputs))
            else:
                result = (compare_current if args.compare_current else verify)(args.verify, args.expected_binding_sha256)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, UnicodeError) as exc:
        print('REVIEW_BINDING_FAILED: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
