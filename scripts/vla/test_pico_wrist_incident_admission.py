"""731084 successor admission tests with local files and fake worker only."""
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).parent/'runtime'))
import arm_native_lease_bridge as bridge
import pico_wrist_native_coordinator as coordinator
import pico_wrist_docker_launcher as launcher
import run_pico_wrist_native_trial as runner
import prepare_pico_wrist_native_probe as prep
from test_pico_wrist_native_coordinator import FakeGuard, real_worker_with_fake_transport, GOAL
from test_prepare_pico_wrist_native_probe import state, urdf, transmissions


class IncidentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'control';self.root.mkdir(mode=0o700)
        self.lease_dir=Path(self.tmp.name)/'historic';self.lease_dir.mkdir(mode=0o700)
        (self.root/'.trial.lock').write_bytes(b'');(self.root/'.trial.lock').chmod(0o600)
        (self.root/'PENDING_OR_UNRESOLVED.json').write_bytes(b'prior-marker')
        self.manifest=prep.prepare(state(),urdf(),transmissions())
        self.assertNotEqual(self.manifest['candidate']['xml_sha256'],coordinator.incident.TASK_SHA)
        self.session='a'*32
        self.patches=[patch.object(coordinator,'GLOBAL_RECEIPT_DIR',self.root),
                      patch.object(coordinator.incident,'LEASE_DIR',self.lease_dir),
                      patch.object(coordinator,'_incident_status'),
                      patch.object(coordinator.incident,'validate_record'),
                      patch.object(coordinator.incident,'container_task'),
                      patch.object(coordinator.incident,'no_observed_activity')]
        for p in self.patches:p.start();self.addCleanup(p.stop)

    def test_existing_marker_blocks_legacy_but_specific_gate_takes_lock(self):
        with self.assertRaisesRegex(RuntimeError,'previous_trial'): coordinator.acquire_trial_lock()
        fd=coordinator.acquire_trial_lock(incident_evidence=b'known')
        try:
            with self.assertRaises(BlockingIOError):coordinator.acquire_trial_lock(incident_evidence=b'known')
        finally:os.close(fd)
        self.assertEqual((self.root/'PENDING_OR_UNRESOLVED.json').read_bytes(),b'prior-marker')

    def test_daemon_exception_requires_checked_inventory_and_rejects_failure(self):
        coordinator.incident.no_observed_activity.side_effect=RuntimeError('daemon_node_controls_or_unexpected_publishers')
        with self.assertRaisesRegex(RuntimeError,'unexpected_publishers'):
            coordinator.acquire_trial_lock(incident_evidence=b'known')
        coordinator.incident.no_observed_activity.assert_called_once_with(allow_ros_daemon=True)
        self.assertTrue((self.root/'PENDING_OR_UNRESOLVED.json').exists())
        self.assertFalse(list(self.root.glob('RECOVERY-*')))

    def test_pc_transport_missing_altered_and_exact_evidence(self):
        p=Path(self.tmp.name)/'historical.json'
        with self.assertRaises(FileNotFoundError): runner.incident_evidence_b64(p)
        p.write_bytes(b'wrong')
        with self.assertRaisesRegex(ValueError,'evidence_hash_mismatch'): runner.incident_evidence_b64(p)
        with patch.object(runner,'INCIDENT_731084_EVIDENCE_SHA',hashlib.sha256(b'wrong').hexdigest()):
            self.assertEqual(base64.b64decode(runner.incident_evidence_b64(p)),b'wrong')

    def test_launcher_requires_model_mode_and_checks_pinned_evidence(self):
        digest=hashlib.sha256(b'pass').hexdigest()
        payload={'session':{},'manifest':{},'urdf_text':'','transmissions_text':'',
                 'guard_source':'pass','worker_source':'pass','source_digests':{'guard':digest,'worker':digest},
                 'operator_confirmed':True,'incident_evidence_b64':base64.b64encode(b'known').decode()}
        with patch.object(launcher.arm,'validate_preflight'),patch.object(launcher.probe,'validate'):
            with self.assertRaisesRegex(ValueError,'invalid_launcher_payload'):launcher.validate_payload(payload)
            payload['model_mode']=True
            self.assertEqual(launcher.validate_payload(payload),{})
            coordinator._incident_status.assert_called_once_with(b'known')
            payload['incident_evidence_b64']='bad-base64!'
            with self.assertRaisesRegex(ValueError,'invalid_incident_evidence'):launcher.validate_payload(payload)

    def test_private_historical_lease_directory_required(self):
        self.lease_dir.chmod(0o755)
        with self.assertRaisesRegex(ValueError,'not_private_or_canonical'):
            coordinator.acquire_trial_lock(incident_evidence=b'known')
        self.lease_dir.chmod(0o700)
        link=self.root/'lease-link';link.symlink_to(self.lease_dir,target_is_directory=True)
        with patch.object(coordinator.incident,'LEASE_DIR',link):
            with self.assertRaisesRegex(ValueError,'not_private_or_canonical'):
                coordinator.acquire_trial_lock(incident_evidence=b'known')

    def test_second_intent_and_predecessor_binding_keep_both_blocks(self):
        fd=coordinator.acquire_trial_lock(incident_evidence=b'known')
        try:
            path=coordinator.durable_incident_intent(self.root,self.manifest,self.session,b'known')
            self.assertTrue(path.exists())
            self.assertTrue((self.root/'PENDING_OR_UNRESOLVED.json').exists())
            binding=json.loads((self.root/('RECOVERY-'+self.session+'-incident-binding.json')).read_text())
            self.assertEqual(binding['predecessor_session_id'],coordinator.incident.SESSION)
            self.assertIs(binding['physical_control_qualified'],False)
            coordinator._incident_static(b'known',allow_new_session=self.session)
            with self.assertRaisesRegex(RuntimeError,'recovery_requires_manual_review'):
                coordinator.require_no_pending_recovery(self.root)
        finally:os.close(fd)

    def test_reusing_prior_task_and_prior_session_are_rejected(self):
        same=dict(self.manifest);same['candidate']=dict(same['candidate'],xml_sha256=coordinator.incident.TASK_SHA)
        with self.assertRaisesRegex(ValueError,'new_task'):
            coordinator.durable_incident_intent(self.root,same,self.session,b'known')
        with self.assertRaisesRegex(ValueError,'invalid_new_incident_trial_session'):
            coordinator.durable_incident_intent(self.root,self.manifest,coordinator.incident.SESSION,b'known')
        self.assertFalse(list(self.root.glob('RECOVERY-*')))

    def test_binding_write_failure_retains_both_marker_and_new_block(self):
        with patch.object(coordinator.incident,'durable_new',side_effect=OSError('disk failure')):
            with self.assertRaisesRegex(OSError,'disk failure'):
                coordinator.durable_incident_intent(self.root,self.manifest,self.session,b'known')
        self.assertTrue((self.root/'PENDING_OR_UNRESOLVED.json').exists())
        self.assertTrue((self.root/('RECOVERY-'+self.session+'-intent.json')).exists())

    def test_any_foreign_recovery_intent_fails_closed(self):
        (self.root/('RECOVERY-'+'b'*32+'-intent.json')).write_text('{}')
        with self.assertRaisesRegex(RuntimeError,'intent_set_changed'):
            coordinator.acquire_trial_lock(incident_evidence=b'known')

    def test_changed_guard_during_incident_recheck_never_gets_ack(self):
        self._assert_aborts_after_incident_check('moving')

    def test_permission_expiring_during_incident_recheck_never_gets_ack(self):
        self._assert_aborts_after_incident_check('expired')

    def _assert_aborts_after_incident_check(self, reason):
        lease=bridge.GuardLease(self.tmp.name,self.manifest['input']['reference_20d'],lambda:True)
        guard=FakeGuard(lease);workers=[];seen=[];changed=[False]
        permit={'goal_id':GOAL,'task_sha256':self.manifest['candidate']['xml_sha256'],
                'decision_sha256':'b'*64,'deadline_monotonic_ns':time.monotonic_ns()+5_000_000_000}
        pc=types.SimpleNamespace(begin_model_permit=lambda *_:None,permit_snapshot=lambda:permit)
        def static(evidence,*,allow_new_session=None):
            if allow_new_session is not None:
                changed[0]=True
                if reason=='expired':permit['deadline_monotonic_ns']=time.monotonic_ns()-1
        original_snapshot=guard.checked_snapshot
        def snapshot():
            row=copy.deepcopy(original_snapshot())
            if reason=='moving' and changed[0]:
                row['velocity'][bridge.arm.ARM_AXIS]=.002
            return row
        guard.checked_snapshot=snapshot
        def spawn(path,intent,uid):
            process=real_worker_with_fake_transport(self.manifest,path,intent,uid,lease.session_id,model=True)
            workers.append(process);return process
        def event(row):seen.append(row.get('event'));return True
        try:
            with patch.object(bridge.arm,'physical_release_gate'),patch.object(coordinator,'_incident_static',side_effect=static):
                expected=('guard_sample_not_stationary_at_reference' if reason=='moving'
                          else 'model_permission_expired_after_incident_check')
                with self.assertRaisesRegex((ValueError,RuntimeError),expected):
                    coordinator.coordinate(lease,guard,self.manifest,urdf(),transmissions(),spawn,
                        self.root,timeout=8,model_permit=pc,incident_evidence=b'known',event_sink=event)
            self.assertTrue(changed[0]);self.assertNotIn('dispatched',seen)
            self.assertFalse(guard.goal_acknowledged.is_set())
            self.assertTrue((self.root/'PENDING_OR_UNRESOLVED.json').exists())
            self.assertTrue((self.root/('RECOVERY-'+lease.session_id+'-intent.json')).exists())
        finally:
            guard.close()
            for process in workers:
                if process.poll() is None:process.terminate()
                process.wait(timeout=3)
                for stream in (process.stdin,process.stdout,process.stderr):stream.close()

    def test_integrated_fake_worker_keeps_previous_marker_and_uses_new_intent(self):
        # Coordinator + lease + model permit + worker IPC; local fake actuator.
        lease=bridge.GuardLease(self.tmp.name,self.manifest['input']['reference_20d'],lambda:True)
        guard=FakeGuard(lease);workers=[];seen=[]
        permit={'goal_id':GOAL,'task_sha256':self.manifest['candidate']['xml_sha256'],
                'decision_sha256':'b'*64,'deadline_monotonic_ns':time.monotonic_ns()+5_000_000_000}
        pc=types.SimpleNamespace(begin_model_permit=lambda *_:None,permit_snapshot=lambda:permit)
        def spawn(path,intent,uid):
            self.assertEqual(intent.name,'intent-'+lease.session_id+'.json')
            self.assertTrue((self.root/'PENDING_OR_UNRESOLVED.json').exists())
            self.assertTrue((self.root/('RECOVERY-'+lease.session_id+'-intent.json')).exists())
            process=real_worker_with_fake_transport(self.manifest,path,intent,uid,lease.session_id,model=True)
            workers.append(process);return process
        def event(row): seen.append(row.get('event'));return True
        try:
            with patch.object(bridge.arm,'physical_release_gate'):
                result=coordinator.coordinate(lease,guard,self.manifest,urdf(),transmissions(),spawn,
                    self.root,timeout=8,model_permit=pc,incident_evidence=b'known',event_sink=event)
            self.assertEqual(result['status'],'ACTION_SUCCEEDED_AND_POSTFLIGHT_OBSERVED')
            self.assertIn('uuid_request',seen)
            self.assertTrue((self.root/'PENDING_OR_UNRESOLVED.json').exists())
            self.assertTrue((self.root/('RECOVERY-'+lease.session_id+'-intent.json')).exists())
        finally:
            guard.close()
            for process in workers:
                if process.poll() is None:process.terminate()
                process.wait(timeout=3)
                for stream in (process.stdin,process.stdout,process.stderr):stream.close()

if __name__=='__main__':unittest.main()
