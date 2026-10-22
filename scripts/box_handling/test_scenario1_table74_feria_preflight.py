"""Recipe-only phase optimization with mocked existing read/command boundaries."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import scenario1_runtime as runtime
from scripts.box_handling import scenario1_table74_trial_run as trial
from scripts.box_handling import scenario1_table74_current_release_run as release_run
from scripts.box_handling.test_scenario1_table74_recipe import recorded_release_payload
from scripts.box_handling.test_scenario1_table74_current_release_run import payload as supervised_payload
from scripts.box_handling.test_scenario1_table74_trial_run import SUCCESS


def machine(folder,*,recorded=True):
    payload=recorded_release_payload()if recorded else supervised_payload()
    events=[]
    result=release_run.ReleaseRuntime(payload,lambda event,**fields:events.append(dict(event=event,**fields)))
    result.events=events;result.session=Path(folder);result.armed=result.resume_validated=True
    result.container_identity=copy.deepcopy(payload['resume_context']['containers'])
    result.dependency_identity=copy.deepcopy(payload['resume_context']['dependencies'])
    result.points=copy.deepcopy(payload['resume_context']['points'])
    result.live_monitor_enabled=True;result.health_session=Mock()
    result.connected=Mock();result.discover=Mock();result.health=Mock();result.quick_health=Mock()
    result.map_points=Mock(return_value=result.points);result.verify_trial_files=Mock()
    result.hashes=Mock(side_effect=result.verify_trial_files)
    result.audit_native_completion=Mock()
    return result


def fresh_entry(self,*,refresh_health=False):
    self.resume_validated=True


class EntryHandshakeTests(unittest.TestCase):
    def test_recent_authentic_entry_reused_only_for_explicit_handshake_with_live_health(self):
        with tempfile.TemporaryDirectory()as folder:
            r=machine(folder);clock=[100.]
            with patch.object(runtime.Runtime,'check_resume_entry',autospec=True,side_effect=fresh_entry)as fresh, \
                    patch.object(trial.time,'monotonic',side_effect=lambda:clock[0]):
                r.check_resume_entry();self.assertEqual(fresh.call_count,1)
                r.resume_validated=False  # Runtime.run deliberately requests the handshake.
                clock[0]=101.;r.check_resume_entry(refresh_health=True)
                self.assertTrue(r.resume_validated);self.assertEqual(fresh.call_count,1)
                r.quick_health.assert_called_once();r.discover.assert_not_called();r.hashes.assert_not_called()
                reused=[e for e in r.events if e['event']=='trial_resume_entry_reused']
                self.assertEqual(len(reused),1);self.assertEqual(reused[0]['age_s'],1.)
                self.assertFalse(reused[0]['current_entry_measurement_refreshed'])
                # Reuse does not renew the proof or create an indefinite cache.
                r.check_resume_entry(refresh_health=True)
                self.assertEqual(fresh.call_count,2)

    def test_exact_two_second_expiry_or_backwards_clock_uses_fresh_bounded_entry(self):
        for now in (102.,103.,99.):
            with self.subTest(now=now),tempfile.TemporaryDirectory()as folder:
                r=machine(folder);clock=[100.]
                with patch.object(runtime.Runtime,'check_resume_entry',autospec=True,side_effect=fresh_entry)as fresh, \
                        patch.object(trial.time,'monotonic',side_effect=lambda:clock[0]):
                    r.check_resume_entry();clock[0]=now;r.check_resume_entry(refresh_health=True)
                self.assertEqual(fresh.call_count,2);r.discover.assert_called_once();r.hashes.assert_called_once()
                r.quick_health.assert_called_once();r.health.assert_not_called();r.map_points.assert_called_once()
                self.assertFalse(any(e['event']=='trial_resume_entry_reused'for e in r.events))

    def test_cache_expiring_while_live_health_waits_is_not_reused(self):
        with tempfile.TemporaryDirectory()as folder:
            r=machine(folder);clock=[100.]
            with patch.object(runtime.Runtime,'check_resume_entry',autospec=True,side_effect=fresh_entry)as fresh, \
                    patch.object(trial.time,'monotonic',side_effect=lambda:clock[0]):
                r.check_resume_entry();clock[0]=101.9
                r.quick_health.side_effect=lambda:clock.__setitem__(0,102.1)
                r.check_resume_entry(refresh_health=True)
            self.assertEqual(fresh.call_count,2);r.discover.assert_called_once()
            self.assertFalse(any(e['event']=='trial_resume_entry_reused'for e in r.events))

    def test_context_last_action_or_health_worker_change_prevents_reuse(self):
        for changed in ('containers','dependencies','points','resume_context','source','action','worker'):
            with self.subTest(changed=changed),tempfile.TemporaryDirectory()as folder:
                r=machine(folder)
                with patch.object(runtime.Runtime,'check_resume_entry',autospec=True,side_effect=fresh_entry)as fresh, \
                        patch.object(trial.time,'monotonic',return_value=100.):
                    r.check_resume_entry()
                    if changed=='containers':r.container_identity['changed']=['new','start']
                    elif changed=='dependencies':r.dependency_identity['changed']='0'*64
                    elif changed=='points':r.points['changed']={}
                    elif changed=='resume_context':r.payload['resume_context']['boot_id']='other'
                    elif changed=='source':r.resume_plan['source_sha256']='0'*64
                    elif changed=='action':r.last_action_end_ns=1234
                    else:r.health_session=Mock()
                    r.check_resume_entry(refresh_health=True)
                self.assertEqual(fresh.call_count,2);r.discover.assert_called_once();r.hashes.assert_called_once()
                self.assertFalse(any(e['event']=='trial_resume_entry_reused'for e in r.events))

    def test_new_stop_or_live_health_fault_is_fatal_not_a_fallback_to_older_success(self):
        for failed in ('connection','health'):
            with self.subTest(failed=failed),tempfile.TemporaryDirectory()as folder:
                r=machine(folder)
                with patch.object(runtime.Runtime,'check_resume_entry',autospec=True,side_effect=fresh_entry)as fresh, \
                        patch.object(trial.time,'monotonic',return_value=100.):
                    r.check_resume_entry()
                    (r.connected if failed=='connection'else r.quick_health).side_effect=RuntimeError('new fault')
                    with self.assertRaisesRegex(RuntimeError,'new fault'):r.check_resume_entry(refresh_health=True)
                self.assertEqual(fresh.call_count,1);self.assertFalse(r.resume_validated)
                r.discover.assert_not_called();r.health.assert_not_called()

    def test_disabled_live_monitor_or_changed_container_cannot_use_cached_admission(self):
        for failed in ('monitor','container'):
            with self.subTest(failed=failed),tempfile.TemporaryDirectory()as folder:
                r=machine(folder)
                with patch.object(runtime.Runtime,'check_resume_entry',autospec=True,side_effect=fresh_entry)as fresh, \
                        patch.object(trial.time,'monotonic',return_value=100.):
                    r.check_resume_entry()
                    if failed=='monitor':
                        r.live_monitor_enabled=False;r.quick_health.side_effect=RuntimeError('LIVE_HEALTH_NOT_ARMED')
                    else:
                        r.container_identity['changed']=['other','start'];r.discover.side_effect=RuntimeError('CONTAINER_CHANGED')
                    with self.assertRaises(RuntimeError):r.check_resume_entry(refresh_health=True)
                self.assertEqual(fresh.call_count,1);self.assertFalse(r.resume_validated)

    def test_supervised_handshake_retains_original_full_refresh(self):
        with tempfile.TemporaryDirectory()as folder:
            r=machine(folder,recorded=False)
            with patch.object(runtime.Runtime,'check_resume_entry',autospec=True,side_effect=fresh_entry)as fresh:
                r.check_resume_entry(refresh_health=True)
            fresh.assert_called_once_with(r,refresh_health=True)
            r.quick_health.assert_not_called();self.assertIsNone(r._trial_entry_cache)

    def test_invalid_false_none_or_mutated_recipe_never_uses_any_optimized_gate(self):
        for value in (False,None,{},dict(kind='recorded_recipe_assumption')):
            with self.subTest(value=value),tempfile.TemporaryDirectory()as folder:
                r=machine(folder);r.payload['recipe_provenance']=value
                with patch.object(runtime.Runtime,'check_resume_entry')as fresh,self.assertRaises(ValueError):
                    r.check_resume_entry(refresh_health=True)
                fresh.assert_not_called();r.quick_health.assert_not_called();r.discover.assert_not_called()


class StagePreflightTests(unittest.TestCase):
    def test_recipe_stage_keeps_fresh_entry_and_all_hashes_but_uses_live_health(self):
        with tempfile.TemporaryDirectory()as folder:
            r=machine(folder)
            with patch.object(runtime.Runtime,'check_resume_entry',autospec=True,side_effect=fresh_entry)as fresh, \
                    patch.object(runtime.Runtime,'action',return_value=copy.deepcopy(SUCCESS))as action, \
                    patch.object(trial.time,'monotonic',return_value=100.):
                r.check_resume_entry();self.assertEqual(fresh.call_count,1)
                r.stage({'command':'stage','stage':trial.STAGE})
            self.assertEqual(fresh.call_count,2)
            self.assertEqual(fresh.call_args.kwargs,{'refresh_health':False})
            r.discover.assert_called_once();r.hashes.assert_called_once();r.verify_trial_files.assert_called_once()
            r.health.assert_not_called();self.assertEqual(r.quick_health.call_count,3)
            action.assert_called_once();r.audit_native_completion.assert_called_once()
            self.assertEqual(r.trial_record['phase'],'succeeded')

    def test_supervised_stage_keeps_complete_health_and_extra_final_file_read(self):
        with tempfile.TemporaryDirectory()as folder:
            r=machine(folder,recorded=False)
            with patch.object(runtime.Runtime,'check_resume_entry',autospec=True,side_effect=fresh_entry), \
                    patch.object(runtime.Runtime,'action',return_value=copy.deepcopy(SUCCESS)):
                r.stage({'command':'stage','stage':trial.STAGE})
            r.health.assert_called_once_with(require_home=False);self.assertEqual(r.verify_trial_files.call_count,2)
            self.assertEqual(r.quick_health.call_count,2);r.audit_native_completion.assert_not_called()

    def test_stage_live_health_fresh_entry_hash_or_force_fault_never_advances(self):
        for failed in ('health','entry','hash','native_audit'):
            with self.subTest(failed=failed),tempfile.TemporaryDirectory()as folder:
                r=machine(folder)
                if failed=='health':r.quick_health.side_effect=RuntimeError('health fault')
                if failed=='hash':r.hashes.side_effect=RuntimeError('dependency changed')
                if failed=='native_audit':r.audit_native_completion.side_effect=RuntimeError('native force')
                entry=RuntimeError('arrival outside tolerance')if failed=='entry'else fresh_entry
                with patch.object(runtime.Runtime,'check_resume_entry',autospec=True,side_effect=entry), \
                        patch.object(runtime.Runtime,'action',return_value=copy.deepcopy(SUCCESS))as action:
                    with self.assertRaises(RuntimeError):r.stage({'command':'stage','stage':trial.STAGE})
                self.assertEqual(r.trial_record['phase'],'failed')
                self.assertEqual(action.call_count,1 if failed=='native_audit'else 0)
                self.assertFalse(any(e['event']=='stage_complete'for e in r.events))

    def test_runtime_startup_remains_complete_health_before_ready_in_recipe_mode(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);r=machine(folder);r.payload['mode']='check';r.health_session=None
            r.payload['resume_context']=dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                containers=r.container_identity,dependencies=r.dependency_identity,points=r.points,
                execution_profile=r.execution_profile)
            r.map_state=Mock(return_value=('utars_nav_map','FSM_WAITNAVIGATE'));r.read_poses=Mock()
            r.start_live_monitor=Mock();r.check_box_alignment_head=Mock()
            with patch.object(runtime.threading,'Thread'),patch.object(runtime.signal,'signal'), \
                    patch.object(runtime,'check_sps_discovery'), \
                    patch.object(runtime,'open',side_effect=lambda name,mode:open(root/'runtime.lock',mode),create=True), \
                    patch.object(runtime.Runtime,'check_resume_entry',autospec=True,side_effect=fresh_entry):
                self.assertEqual(r.run(),0)
            r.health.assert_called_once_with(require_home=False);r.start_live_monitor.assert_called_once()
            self.assertTrue(any(e['event']=='ready'for e in r.events))


if __name__=='__main__':unittest.main()
