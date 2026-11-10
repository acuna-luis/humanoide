#!/usr/bin/env python3
"""Checks for the fixed native wrist experiment, not a VLA release gate.

These checks do not dispatch, establish operator-report provenance, guarantee a
physical stop, or authorize movement. The calling supervisor must bind the
report to the actual conversation, run the checks on the bytes it will use,
and keep the existing guard, lease, cancellation and exclusion mechanisms.
"""
import json
import math
import re

import prepare_pico_wrist_native_probe as probe
import arm_from_pico_supervised as arm


CONDITIONS = frozenset({
    'v4_hands_installed_and_empty', 'pico_posture_head_down',
    'wrist_swept_zone_clear', 'wheels_locked', 'charger_disconnected',
    'both_estops_accessible', 'person_at_estop', 'manual_controls_inactive',
})


def check_operator_report(report, session_id):
    """Check the structure of an operator report, not its provenance or age.

    The caller must obtain the report in the current session immediately
    before movement; do not infer it from an old record or the schema alone.
    Battery, work mode and control status still require the existing live checks.
    """
    if (not isinstance(session_id, str) or not re.fullmatch('[0-9a-f]{32}', session_id)
            or not isinstance(report, dict)
            or set(report) != {'session_id', 'conditions'}
            or report['session_id'] != session_id
            or not isinstance(report['conditions'], dict)
            or set(report['conditions']) != CONDITIONS
            or any(value is not True for value in report['conditions'].values())):
        raise ValueError('operator_report_incomplete_or_unbound')
    return {'operator_report_structurally_complete': True,
            'provenance_or_freshness_established': False}


def check_candidate(manifest_raw, urdf_raw, transmissions_raw, binding_dir,
                    binding_sha256, *, source_snapshot, pc_snapshot):
    """Check exact candidate bytes and sources; no dispatch capability results."""
    import pico_wrist_review_binding as binding
    if any(type(value) is not bytes for value in (manifest_raw, urdf_raw, transmissions_raw)):
        raise ValueError('candidate_requires_exact_bytes')
    manifest = json.loads(manifest_raw)
    probe.validate(manifest, urdf_raw.decode('utf-8'), transmissions_raw.decode('utf-8'))
    binding.compare_candidate_inputs(binding_dir, binding_sha256, manifest_raw, urdf_raw,
                                     transmissions_raw, source_snapshot=source_snapshot,
                                     pc_snapshot=pc_snapshot)
    return manifest


def check_guard_before_dispatch(manifest, lease, guard):
    """Validate live Motion-side data with the guard's own clock and lease.

    Call immediately before dispatch and retain the same continuous guard.
    The guard's launch provenance and cancellation mode must be independently
    bound by the caller. No PC clock is compared with a Motion timestamp.
    """
    import pico_wrist_native_coordinator as coordinator
    reference = manifest['input']['reference_20d']
    if guard.lease is not lease or lease.initial != reference:
        raise ValueError('guard_lease_or_reference_mismatch')
    sample = guard.checked_snapshot()
    positions, velocities = sample.get('position'), sample.get('velocity')
    if (not isinstance(positions, dict) or not isinstance(velocities, dict)
            or set(positions) != set(arm.BODY) or set(velocities) != set(arm.BODY)
            or any(type(positions[n]) not in (int, float)
                   or not math.isfinite(positions[n])
                   or abs(positions[n] - reference[n]) > arm.LOCKED_DRIFT_RAD
                   or type(velocities[n]) not in (int, float)
                   or not math.isfinite(velocities[n])
                   or abs(velocities[n]) > .001 for n in arm.BODY)):
        raise ValueError('guard_sample_not_stationary_at_reference')
    message = {'name': list(arm.BODY), 'position': [positions[n] for n in arm.BODY],
               'velocity': [velocities[n] for n in arm.BODY]}
    arm.motion_envelope(message, reference)
    coordinator.check_stationary_targets(manifest, sample, reference)
    return sample
