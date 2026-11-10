"""Offline tests only: temporary directories and local dummy processes."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

PATH = Path(__file__).parent/'runtime/archive_failed_pico_wrist_stage.py'
spec = importlib.util.spec_from_file_location('archive_failed_pico_wrist_stage', PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
sys.path.insert(0, str(Path(__file__).parent/'runtime'))
sys.path.insert(0, str(Path(__file__).parent.parent/'box_handling'))
import pico_wrist_native_coordinator as coordinator


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.control = self.root/'control'; self.control.mkdir(mode=0o700)
        self.lease = self.root/'lease'; self.lease.mkdir(mode=0o700)
        (self.control/'.trial.lock').write_bytes(b'')
        (self.control/'.trial.lock').chmod(0o600)
        intent = {'session_id':m.SESSION,'task_path':m.TASK_PATH,'task_sha256':m.TASK_SHA,
                  'state':'intent_before_stage_or_send'}
        marker=(json.dumps(intent)+'\n').encode()
        (self.control/'PENDING_OR_UNRESOLVED.json').write_bytes(marker)
        (self.lease/('intent-'+m.SESSION+'.json')).write_bytes(marker)
        (self.lease/('arm-lease-'+m.SESSION+'.json')).write_text('{"deadline":0.0}\n')
        receipt={'runtime_path':m.TASK_PATH,'sha256':m.TASK_SHA,'device':m.DEVICE,'inode':m.INODE,
                 'directory_device':m.DIR_DEVICE,'directory_inode':m.DIR_INODE,
                 'status':'STAGED_NOT_LOADED_OR_EXECUTED','movement_commands':0}
        rows=[{'event':'BRIDGE_READY'}, {'event':'stage_receipt','session_id':m.SESSION,'receipt':receipt},
              {'event':'coordinator_failure','reason':'JSONDecodeError: invalid','no_retry':True}]
        (self.control/('worker-events-'+m.SESSION+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in rows))

    def tearDown(self): self.temp.cleanup()

    def run_recovery(self, *, archive=False, task=None, inspect=lambda: {'observed':True}):
        task = task or (lambda mode: {'mode':mode})
        return m.recover(archive=archive,control=self.control,lease_dir=self.lease,inspect=inspect,task=task)

    def test_check_preserves_everything(self):
        result=self.run_recovery()
        self.assertEqual(result['status'],'CHECKED_NO_CHANGES')
        self.assertTrue((self.control/'PENDING_OR_UNRESOLVED.json').is_file())
        self.assertFalse(list(self.control.glob('RECOVERY-*')))

    def test_archive_keeps_marker_until_verified_task_receipt(self):
        calls=[]
        def task(mode):
            calls.append(mode)
            self.assertTrue((self.control/'PENDING_OR_UNRESOLVED.json').is_file())
            if mode=='archive':
                self.assertTrue((self.control/('RECOVERY-'+m.SESSION+'-intent.json')).is_file())
            return {'mode':mode}
        result=self.run_recovery(archive=True,task=task)
        self.assertEqual(calls,['check','archive'])
        self.assertFalse((self.control/'PENDING_OR_UNRESOLVED.json').exists())
        self.assertTrue(Path(result['marker_archive']).is_file())
        self.assertTrue((self.control/('RECOVERY-'+m.SESSION+'-xml-archived.json')).is_file())
        self.assertTrue((self.control/('RECOVERY-'+m.SESSION+'-complete.json')).is_file())
        self.assertTrue((self.control/('RECOVERY-'+m.SESSION+'-intent-archived.json')).is_file())
        self.assertFalse((self.control/('RECOVERY-'+m.SESSION+'-intent.json')).exists())

    def test_crash_after_marker_unlink_keeps_recovery_guard_and_blocks_both_launch_paths(self):
        unlink=os.unlink
        def crash_after_unlink(path,*args,**kwargs):
            result=unlink(path,*args,**kwargs)
            if str(path).endswith('/PENDING_OR_UNRESOLVED.json'):
                raise KeyboardInterrupt('simulated process death after unlink')
            return result
        with patch.object(m.os,'unlink',side_effect=crash_after_unlink):
            with self.assertRaises(KeyboardInterrupt): self.run_recovery(archive=True)
        self.assertFalse((self.control/'PENDING_OR_UNRESOLVED.json').exists())
        self.assertTrue((self.control/('RECOVERY-'+m.SESSION+'-intent.json')).exists())
        with patch.object(coordinator,'GLOBAL_RECEIPT_DIR',self.control):
            with self.assertRaisesRegex(RuntimeError,'recovery_requires_manual_review'):
                coordinator.acquire_trial_lock()
            fd=os.open(self.control/'.trial.lock',os.O_RDWR)
            try:
                with patch.object(coordinator.arm,'require_verified_stream'):
                    with self.assertRaisesRegex(RuntimeError,'recovery_requires_manual_review'):
                        coordinator.coordinate(types.SimpleNamespace(session_id=m.SESSION),None,None,None,None,None,
                                               self.control,held_lock_fd=fd,verified_provenance=('host',))
            finally:
                os.close(fd)

    def test_uncertain_archive_leaves_marker_and_intent(self):
        def task(mode):
            if mode=='archive': raise TimeoutError('uncertain_delivery')
            return {'mode':mode}
        with self.assertRaises(TimeoutError): self.run_recovery(archive=True,task=task)
        self.assertTrue((self.control/'PENDING_OR_UNRESOLVED.json').is_file())
        self.assertTrue((self.control/('RECOVERY-'+m.SESSION+'-intent.json')).is_file())
        self.assertFalse((self.control/('ARCHIVED-PENDING-'+m.SESSION+'.json')).exists())

    def test_new_uuid_during_xml_archive_preserves_marker_and_recovery_guard(self):
        def task(mode):
            if mode=='archive':
                journal=self.control/('worker-events-'+m.SESSION+'.jsonl')
                with journal.open('a') as stream:
                    stream.write('{"event":"uuid_request"}\n')
            return {'mode':mode}
        with self.assertRaisesRegex(ValueError,'pre_uuid_failure'):
            self.run_recovery(archive=True,task=task)
        self.assertTrue((self.control/'PENDING_OR_UNRESOLVED.json').is_file())
        self.assertTrue((self.control/('RECOVERY-'+m.SESSION+'-intent.json')).is_file())
        self.assertFalse((self.control/('ARCHIVED-PENDING-'+m.SESSION+'.json')).exists())

    def test_action_becomes_active_before_marker_archive_preserves_guard(self):
        calls=[]
        def inspect():
            calls.append(1)
            if len(calls)==2:
                raise RuntimeError('active_or_unknown_action_status')
            return {'observed':True}
        with self.assertRaisesRegex(RuntimeError,'active_or_unknown'):
            self.run_recovery(archive=True,inspect=inspect)
        self.assertTrue((self.control/'PENDING_OR_UNRESOLVED.json').is_file())
        self.assertTrue((self.control/('RECOVERY-'+m.SESSION+'-intent.json')).is_file())

    def test_fsync_failure_after_marker_unlink_attempts_to_restore(self):
        real_fsync=os.fsync
        counter=[]
        def fail_after_unlink(fd):
            counter.append(fd)
            if len(counter)==6:
                raise OSError('injected fsync failure after unlink')
            return real_fsync(fd)
        with patch.object(m.os,'fsync',side_effect=fail_after_unlink):
            with self.assertRaisesRegex(OSError,'injected fsync'):
                self.run_recovery(archive=True)
        marker=self.control/'PENDING_OR_UNRESOLVED.json'
        archived=self.control/('ARCHIVED-PENDING-'+m.SESSION+'.json')
        self.assertTrue(marker.is_file())
        self.assertEqual(marker.stat().st_ino,archived.stat().st_ino)

    def test_crash_before_guard_removal_keeps_launcher_blocked_even_after_complete(self):
        unlink=os.unlink
        def crash_before_guard_unlink(path,*args,**kwargs):
            if str(path).endswith('-intent.json'):
                raise KeyboardInterrupt('simulated crash before guard release')
            return unlink(path,*args,**kwargs)
        with patch.object(m.os,'unlink',side_effect=crash_before_guard_unlink):
            with self.assertRaises(KeyboardInterrupt): self.run_recovery(archive=True)
        self.assertTrue((self.control/('RECOVERY-'+m.SESSION+'-complete.json')).is_file())
        self.assertTrue((self.control/('RECOVERY-'+m.SESSION+'-intent.json')).is_file())
        with patch.object(coordinator,'GLOBAL_RECEIPT_DIR',self.control):
            with self.assertRaisesRegex(RuntimeError,'recovery_requires_manual_review'):
                coordinator.acquire_trial_lock()

    def test_uuid_or_extra_journal_record_fails_closed(self):
        path=self.control/('worker-events-'+m.SESSION+'.jsonl')
        with path.open('a') as stream: stream.write('{"event":"uuid_request"}\n')
        with self.assertRaisesRegex(ValueError,'pre_uuid_failure'): self.run_recovery(archive=True)
        self.assertTrue((self.control/'PENDING_OR_UNRESOLVED.json').is_file())

    def test_live_lease_or_activity_rejects_before_changes(self):
        (self.lease/('arm-lease-'+m.SESSION+'.json')).write_text('{"deadline":1.0}\n')
        with self.assertRaisesRegex(ValueError,'lease_not_revoked'): self.run_recovery(archive=True)
        self.assertTrue((self.control/'PENDING_OR_UNRESOLVED.json').is_file())
        self.assertFalse(list(self.control.glob('RECOVERY-*')))

    def test_active_action_blocks(self):
        def run(argv,*,data=None):
            if argv[1]=='ps': return (m.APP+'\n'+m.ROS+'\n').encode()
            if argv[1]=='top': return b'PID COMMAND\n2 bash\n'
            return b'status_list:\n- goal_info:\n  status: 2\n'
        with self.assertRaisesRegex(RuntimeError,'active_or_unknown'): m.no_observed_activity(run)

    def test_container_archive_preserves_exact_inode_and_bytes(self):
        root=self.root/'tasks';root.mkdir()
        p=root/'task.xml';p.write_bytes(b'<root/>\n')
        st=p.stat(); ds=root.stat()
        payload={'root':str(root),'name':p.name,'dev':st.st_dev,'ino':st.st_ino,
                 'dir_dev':ds.st_dev,'dir_ino':ds.st_ino,'sha':m.sha(p.read_bytes()),
                 'session':m.SESSION,'mode':'archive'}
        r=subprocess.run([sys.executable,'-B','-c',m.CONTAINER_ARCHIVE],input=json.dumps(payload)+'\n',
                         text=True,capture_output=True,timeout=5)
        self.assertEqual(r.returncode,0,r.stderr)
        archived=root/json.loads(r.stdout)['archive_name']
        self.assertFalse(p.exists()); self.assertEqual(archived.read_bytes(),b'<root/>\n')
        self.assertEqual(archived.stat().st_ino,st.st_ino)


if __name__=='__main__': unittest.main()
