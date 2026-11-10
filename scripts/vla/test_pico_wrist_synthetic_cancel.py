"""Tests for a synthetic-only ROS diagnostic; no robot or network."""
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'runtime'))
import check_pico_wrist_synthetic_cancel as check
import pico_wrist_synthetic_cancel_host as host
import synthetic_wrist_action_server as server


class SyntheticCancelTests(unittest.TestCase):
    endpoint='/codex_smolvla_diag_'+'a'*32+'/action'
    goal='12345678-1234-4234-9234-123456789abc'

    def test_guard_remaps_every_physical_action_path(self):
        _,original,_=check.trial.source_bundle()
        copied=check.derived_guard(original,self.endpoint)
        self.assertEqual(original.count(check.REAL),4)
        self.assertNotIn(check.REAL,copied)
        self.assertEqual(copied.count(self.endpoint),4)
        compile(copied,'<guard>','exec')

    def test_guard_rejects_unexpected_source_and_any_other_endpoint(self):
        _,original,_=check.trial.source_bundle()
        for endpoint in ('/mc/manipulation/action','/codex_smolvla_diag_short/action',
                         self.endpoint+'/suffix',self.endpoint+'\n',None):
            with self.assertRaises(ValueError):check.derived_guard(original,endpoint)
        with self.assertRaisesRegex(ValueError,'layout_changed'):
            check.derived_guard(original.replace(check.REAL,'/already/changed',1),self.endpoint)

    def test_server_rejects_real_endpoint_before_ros_import(self):
        with self.assertRaisesRegex(ValueError,'synthetic_endpoint_required'):
            server.main(['--endpoint','/mc/manipulation/action','--goal-id',self.goal])
        with self.assertRaisesRegex(ValueError,'synthetic_uuid_required'):
            server.main(['--endpoint',self.endpoint,'--goal-id','00000000-0000-0000-0000-000000000000'])

    def test_terminal_status_has_time_to_propagate(self):
        self.assertFalse(server.terminal_published_long_enough(None,10.0))
        self.assertFalse(server.terminal_published_long_enough(10.0,12.49))
        self.assertTrue(server.terminal_published_long_enough(10.0,12.5))

    def test_builder_produces_compilable_isolated_streams(self):
        h,original,g,s=check.build_sources(self.endpoint)
        for source in (h,g,s):compile(source,'<check>','exec')
        self.assertNotIn(check.REAL,g)
        self.assertNotIn(check.REAL,s)
        self.assertIn(self.endpoint,g)
        self.assertIn('70.0',g)
        self.assertIn('guard_can_cancel=True',g)
        self.assertNotEqual(original,g)

    def test_synthetic_host_rejects_invalid_endpoint_before_other_inputs(self):
        value={k:None for k in ('session','manifest','urdf_text','transmissions_text','guard_source',
              'guard_sha256','synthetic_server_source','synthetic_server_sha256','endpoint','goal_id')}
        value.update(endpoint='/mc/manipulation/action',goal_id=self.goal)
        with self.assertRaisesRegex(ValueError,'synthetic_endpoint_required'):host.check(value)

    def test_stream_events_can_arrive_out_of_order(self):
        rows=[{'event':'SYNTHETIC_GOAL_ACTIVE','goal_id':self.goal},
              {'event':'SYNTHETIC_GOAL_SENT','goal_id':self.goal}]
        stream=io.BytesIO((''.join(json.dumps(x)+'\n' for x in rows)).encode())
        line=host.Lines(stream)
        self.assertEqual(line.get('SYNTHETIC_GOAL_SENT',1,self.goal)['goal_id'],self.goal)
        self.assertEqual(line.get('SYNTHETIC_GOAL_ACTIVE',1,self.goal)['goal_id'],self.goal)

    def test_guard_preflight_reason_is_retained_without_changing_output(self):
        raw=b'{"event":"preflight_failed","reason":"telemetry_missing"}\n'
        stream=host.GuardOutputAudit(io.BytesIO(raw))
        self.assertEqual(stream.readline(8192),raw)
        self.assertEqual(stream.preflight_reason,'telemetry_missing')

    def test_guard_other_output_is_unchanged(self):
        raw=b'{"event":"telemetry"}\n'
        stream=host.GuardOutputAudit(io.BytesIO(raw))
        self.assertEqual(stream.readline(8192),raw)
        self.assertIsNone(stream.preflight_reason)

    def test_uncertain_child_delivery_retains_handle_for_cleanup(self):
        child=object()
        for phase in ('source','sentinel','payload'):
            retained=[]
            error=host.launch.StreamStartUncertain(child,phase,TimeoutError(),
                                                   source_may_have_executed=phase!='source')
            with patch.object(host.launch,'start_streamed',side_effect=error):
                with self.assertRaisesRegex(RuntimeError,
                        'synthetic_child_start_uncertain_remote_cleanup_unconfirmed:'+phase):
                    host.start_diagnostic_child(retained,'unused')
            self.assertEqual(retained,[child])

    def test_cleanup_continues_after_first_child_failure(self):
        class Child:
            def __init__(self, fail):
                self.fail=fail; self.terminated=False; self.stdin=io.BytesIO(); self.stdout=io.BytesIO()
            def poll(self): return None
            def terminate(self):
                self.terminated=True
                if self.fail: raise OSError('injected')
            def wait(self, timeout): return 0
        first,second=Child(True),Child(False)
        failures=host.cleanup_diagnostic_children((first,second))
        self.assertEqual(failures,['child_0:OSError'])
        self.assertTrue(first.terminated and second.terminated)
        self.assertTrue(all(stream.closed for child in (first,second)
                            for stream in (child.stdin,child.stdout)))


if __name__=='__main__':unittest.main()
