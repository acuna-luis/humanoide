"""Offline tests of necessary checks; no physical release or robot access."""
import copy
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pico_wrist_trial_admission as subject
import pico_wrist_review_binding as binding
import prepare_pico_wrist_native_probe as probe
from test_prepare_pico_wrist_native_probe import state, transmissions, urdf


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.manifest = probe.prepare(state(), urdf(), transmissions())
        self.reference = self.manifest['input']['reference_20d']
        self.lease = SimpleNamespace(initial=self.reference)
        self.sample = {'position': dict(self.reference),
                       'velocity': {name: 0.0 for name in self.reference}}
        self.guard = SimpleNamespace(lease=self.lease, checked_snapshot=lambda: self.sample)

    def test_operator_report_is_structured_but_not_proven_fresh(self):
        session = 'a' * 32
        report = {'session_id': session, 'conditions': {n: True for n in subject.CONDITIONS}}
        self.assertFalse(subject.check_operator_report(report, session)['provenance_or_freshness_established'])
        report['conditions']['person_at_estop'] = False
        with self.assertRaises(ValueError):
            subject.check_operator_report(report, session)
        report['conditions']['person_at_estop'] = True
        with self.assertRaises(ValueError):
            subject.check_operator_report(report, 'b' * 32)

    def test_candidate_is_validated_and_exact_bytes_are_bound(self):
        raw = json.dumps(self.manifest).encode()
        with patch.object(binding, 'compare_candidate_inputs') as compare:
            self.assertEqual(subject.check_candidate(raw, urdf().encode(), transmissions().encode(),
                             'binding', 'digest', source_snapshot='source', pc_snapshot='pc'), self.manifest)
            compare.assert_called_once_with('binding', 'digest', raw, urdf().encode(),
                                            transmissions().encode(), source_snapshot='source', pc_snapshot='pc')
            tampered = copy.deepcopy(self.manifest)
            tampered['candidate']['step_rad_experimental'] = .02
            with self.assertRaises(ValueError):
                subject.check_candidate(json.dumps(tampered).encode(), urdf().encode(),
                                        transmissions().encode(), 'binding', 'digest',
                                        source_snapshot='source', pc_snapshot='pc')

    def test_guard_requires_stationary_reference_and_sps_warning(self):
        self.assertEqual(subject.check_guard_before_dispatch(self.manifest, self.lease, self.guard), self.sample)
        self.sample['velocity']['R_wrist_roll_joint'] = .002
        with self.assertRaisesRegex(ValueError, 'not_stationary'):
            subject.check_guard_before_dispatch(self.manifest, self.lease, self.guard)
        self.sample['velocity']['R_wrist_roll_joint'] = 0
        self.sample['position']['R_wrist_roll_joint'] += .003
        with self.assertRaisesRegex(ValueError, 'not_stationary'):
            subject.check_guard_before_dispatch(self.manifest, self.lease, self.guard)

    def test_guard_refuses_different_lease_and_unhealthy_snapshot(self):
        with self.assertRaisesRegex(ValueError, 'lease_or_reference'):
            subject.check_guard_before_dispatch(self.manifest, SimpleNamespace(initial=self.reference), self.guard)
        def failed():
            raise RuntimeError('guard_not_healthy_for_snapshot')
        self.guard.checked_snapshot = failed
        with self.assertRaisesRegex(RuntimeError, 'guard_not_healthy'):
            subject.check_guard_before_dispatch(self.manifest, self.lease, self.guard)

    def test_sps_warning_rejects_small_drift_towards_nearby_limit(self):
        measured = state()
        measured['position'][measured['name'].index('L_elbow_yaw_joint')] = 2.879
        measured['position'][measured['name'].index('R_elbow_yaw_joint')] = -2.879
        manifest = probe.prepare(measured, urdf(), transmissions())
        reference = manifest['input']['reference_20d']
        lease = SimpleNamespace(initial=reference)
        sample = {'position': dict(reference), 'velocity': {n: 0.0 for n in reference}}
        sample['position']['L_elbow_yaw_joint'] += .0007
        guard = SimpleNamespace(lease=lease, checked_snapshot=lambda: sample)
        with self.assertRaisesRegex(ValueError, 'approaching_nominal_sps_limit'):
            subject.check_guard_before_dispatch(manifest, lease, guard)


if __name__ == '__main__':
    unittest.main()
