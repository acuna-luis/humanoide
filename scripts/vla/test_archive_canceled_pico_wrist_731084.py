"""Offline tests for the 731084 archive; no robot access."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

PATH = Path(__file__).parent/'runtime/archive_canceled_pico_wrist_731084.py'
spec = importlib.util.spec_from_file_location('archive_731084', PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.control = root/'control'; self.control.mkdir(mode=0o700)
        self.lease = root/'lease'; self.lease.mkdir(mode=0o700)
        (self.control/'.trial.lock').write_bytes(b'')
        (self.control/'.trial.lock').chmod(0o600)
        marker = json.dumps({'session_id':m.SESSION, 'task_path':m.TASK_PATH,
                             'task_sha256':m.TASK_SHA, 'state':'intent_before_stage_or_send'}).encode()
        (self.control/'PENDING_OR_UNRESOLVED.json').write_bytes(marker)
        (self.lease/('intent-'+m.SESSION+'.json')).write_bytes(marker)
        (self.lease/('arm-lease-'+m.SESSION+'.json')).write_text('{"deadline":0.0}\n')
        receipt = {'runtime_path':m.TASK_PATH, 'sha256':m.TASK_SHA, 'device':m.DEVICE,
                   'inode':m.INODE, 'directory_device':m.DIR_DEVICE, 'directory_inode':m.DIR_INODE,
                   'status':'STAGED_NOT_LOADED_OR_EXECUTED', 'movement_commands':0}
        rows = [{'event':'BRIDGE_READY'}, {'event':'stage_receipt','session_id':m.SESSION,'receipt':receipt},
                {'event':'uuid_request','goal_id':m.GOAL}, {'event':'dispatched','goal_id':m.GOAL},
                {'event':'accepted','goal_id':m.GOAL,'accepted':True}, {'event':'feedback'},
                {'event':'coordinator_failure','reason':'RuntimeError: guard_lost_during_trial','no_retry':True},
                {'event':'independent_cancel_unconfirmed'}]
        journal = ''.join(json.dumps(r)+'\n' for r in rows).encode()
        self.journal = self.control/('worker-events-'+m.SESSION+'.jsonl')
        self.journal.write_bytes(journal)
        self.marker_sha = m.sha(marker)
        self.journal_sha = m.sha(journal)
        uuid_lines = '\n'.join('      - '+str(x) for x in [46,32,234,141,52,217,78,77,145,146,229,224,193,30,146,29])
        self.terminal = root/'terminal.json'
        self.terminal.write_text(json.dumps({'status':{'returncode':0,'stderr':'',
            'stdout':'status_list:\n- goal_info:\n    goal_id:\n      uuid:\n'+uuid_lines+'\n  status: 5\n---\n'}}))
        self.terminal_sha = m.sha(self.terminal.read_bytes())
        self.hashes = [patch.object(m,'MARKER_SHA',self.marker_sha),
                       patch.object(m,'JOURNAL_SHA',self.journal_sha),
                       patch.object(m,'TERMINAL_EVIDENCE_SHA',self.terminal_sha)]
        for item in self.hashes:
            item.start(); self.addCleanup(item.stop)

    def recover(self, archive=False, task=None, inspect=lambda:{'observed':True}):
        return m.recover(terminal_evidence=self.terminal, archive=archive, control=self.control,
                         lease_dir=self.lease, inspect=inspect, task=task or (lambda mode:{'mode':mode}))

    def test_check_retains_marker_and_has_no_recovery_intent(self):
        result=self.recover()
        self.assertEqual(result['status'],'CHECKED_NO_CHANGES')
        self.assertTrue((self.control/'PENDING_OR_UNRESOLVED.json').exists())
        self.assertFalse(list(self.control.glob('RECOVERY-*')))
        self.assertFalse(result['physical_stop_verified'])

    def test_archive_retains_coordinator_block_and_evidence(self):
        def task(mode):
            self.assertTrue((self.control/'PENDING_OR_UNRESOLVED.json').exists())
            if mode == 'archive':
                self.assertTrue((self.control/('RECOVERY-'+m.SESSION+'-intent.json')).exists())
            return {'mode':mode}
        result=self.recover(archive=True,task=task)
        self.assertEqual(result['status'],'ARCHIVED_WITH_RECOVERY_BLOCK_RETAINED')
        self.assertTrue(Path(result['marker_archive']).exists())
        self.assertTrue(Path(result['recovery_block_retained']).exists())
        self.assertTrue((self.control/('RECOVERY-'+m.SESSION+'-complete.json')).exists())
        self.assertFalse(result['model_control_qualified'])
        self.assertFalse((self.control/'PENDING_OR_UNRESOLVED.json').exists())

    def test_recovery_intent_blocks_existing_coordinator(self):
        self.recover(archive=True)
        import sys
        sys.path.insert(0,str(Path(__file__).parent/'runtime'))
        sys.path.insert(0,str(Path(__file__).parent.parent/'box_handling'))
        import pico_wrist_native_coordinator as coordinator
        with self.assertRaisesRegex(RuntimeError,'recovery_requires_manual_review'):
            coordinator.require_no_pending_recovery(self.control)

    def test_crash_after_marker_unlink_still_blocks(self):
        unlink=os.unlink
        def interrupt(path,*args,**kwargs):
            result=unlink(path,*args,**kwargs)
            if str(path).endswith('/PENDING_OR_UNRESOLVED.json'):
                raise KeyboardInterrupt('simulated crash')
            return result
        with patch.object(m.os,'unlink',side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt): self.recover(archive=True)
        self.assertTrue((self.control/('RECOVERY-'+m.SESSION+'-intent.json')).exists())
        self.assertFalse((self.control/'PENDING_OR_UNRESOLVED.json').exists())

    def test_journal_change_fails_before_archive(self):
        self.journal.write_bytes(self.journal.read_bytes()+b'{}\n')
        with self.assertRaisesRegex(ValueError,'record_hash_mismatch'):
            self.recover(archive=True)
        self.assertTrue((self.control/'PENDING_OR_UNRESOLVED.json').exists())
        self.assertFalse(list(self.control.glob('RECOVERY-*')))

    def test_living_lease_blocks(self):
        (self.lease/('arm-lease-'+m.SESSION+'.json')).write_text('{"deadline":1.0}')
        with self.assertRaisesRegex(ValueError,'lease_not_revoked'): self.recover(archive=True)
        self.assertTrue((self.control/'PENDING_OR_UNRESOLVED.json').exists())

    def test_empty_status_not_terminal_even_with_matched_hash(self):
        self.terminal.write_text(json.dumps({'status':{'returncode':0,'stderr':'','stdout':'status_list: []\n'}}))
        with patch.object(m,'TERMINAL_EVIDENCE_SHA',m.sha(self.terminal.read_bytes())):
            with self.assertRaisesRegex(ValueError,'terminal_status_not_exact'): self.recover(archive=True)
        self.assertTrue((self.control/'PENDING_OR_UNRESOLVED.json').exists())

    def test_wrong_uuid_rejected_even_with_matched_hash(self):
        data=self.terminal.read_text().replace('      - 46','      - 47')
        self.terminal.write_text(data)
        with patch.object(m,'TERMINAL_EVIDENCE_SHA',m.sha(self.terminal.read_bytes())):
            with self.assertRaisesRegex(ValueError,'terminal_uuid_not_exact'): self.recover(archive=True)

    def test_check_allows_only_independently_checked_daemon(self):
        daemon={'pid':42,'rpc_socket_owned':True,'control_clients':0,'action_clients':0,
                'publishers':['/parameter_events','/rosout']}
        def run(argv, *, data=None):
            if argv[1]=='ps': return (m.APP+'\n'+m.ROS+'\n').encode()
            if argv[1]=='top':
                return (b'PID COMMAND\n2 bash\n42 python3\n' if argv[2]==m.ROS
                        else b'PID COMMAND\n2 robot_app\n')
            if argv[1]=='exec' and 'python3' in argv: return json.dumps(daemon).encode()
            return b'status_list: []\n'
        observed=m.no_observed_activity(run,allow_ros_daemon=True)
        self.assertEqual(observed['ros_cli_daemon'],daemon)
        with self.assertRaisesRegex(RuntimeError,'python_process_in_trial_container'):
            m.no_observed_activity(run,allow_ros_daemon=False)
        daemon['action_clients']=1
        with self.assertRaisesRegex(ValueError,'ros_daemon_identity_invalid'):
            m.no_observed_activity(run,allow_ros_daemon=True)

    def test_check_rejects_other_python_and_multiple_ros_python(self):
        def run(argv, *, data=None):
            if argv[1]=='ps': return (m.APP+'\n'+m.ROS+'\n').encode()
            if argv[1]=='top':
                return (b'PID COMMAND\n2 bash\n42 python3\n43 python3\n' if argv[2]==m.ROS
                        else b'PID COMMAND\n2 robot_app\n')
            raise AssertionError('must fail before ROS action read')
        with self.assertRaisesRegex(RuntimeError,'multiple_ros_python_processes'):
            m.no_observed_activity(run,allow_ros_daemon=True)

    def test_uncertain_archive_preserves_marker_and_block(self):
        def task(mode):
            if mode == 'archive': raise TimeoutError('uncertain_delivery')
            return {'mode':mode}
        with self.assertRaises(TimeoutError): self.recover(archive=True,task=task)
        self.assertTrue((self.control/'PENDING_OR_UNRESOLVED.json').exists())
        self.assertTrue((self.control/('RECOVERY-'+m.SESSION+'-intent.json')).exists())

    def test_activity_before_marker_removal_preserves_block(self):
        calls=[]
        def inspect():
            calls.append(1)
            if len(calls)==2: raise RuntimeError('active_or_unknown_action_status')
            return {'observed':True}
        with self.assertRaisesRegex(RuntimeError,'active_or_unknown'): self.recover(archive=True,inspect=inspect)
        self.assertTrue((self.control/'PENDING_OR_UNRESOLVED.json').exists())
        self.assertTrue((self.control/('RECOVERY-'+m.SESSION+'-intent.json')).exists())

if __name__ == '__main__': unittest.main()
