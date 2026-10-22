"""Bounded pickup recovery: synthetic telemetry and local pipes only."""
import copy
import json
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from scripts.box_handling import scenario1_box_alignment as alignment
from scripts.box_handling import scenario1_correction_recovery as recovery
from scripts.box_handling import scenario1_runtime as runtime
from scripts.box_handling.scenario1_session import ProcessSession
from scripts.box_handling import test_scenario1_box_alignment as fixtures
from scripts.box_handling.test_scenario1_correction_recovery import evidence


class AlignmentRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.fixtures = fixtures.AlignmentRuntimeTests()
        self.addCleanup(self.fixtures.doCleanups)

    def observation(self, **values):
        return self.fixtures.observation(**values)

    def machine(self, observations):
        machine = self.fixtures.machine(observations)
        machine.recover_box_alignment = Mock()
        return machine

    def stopped(self):
        _, rows = evidence()
        return recovery.CorrectionRecoveryRequired(rows[-1])

    def test_fresh_inside_box_after_cancel_proceeds_to_one_grasp_without_home(self):
        machine = self.machine([self.observation(x=.7854),
            self.observation(x=.765, stamp=200, base_x=1.02)])
        machine.action.side_effect = [fixtures.SUCCESS, self.stopped(), fixtures.SUCCESS]
        machine.stage(dict(stage='grasp'))
        machine.recover_box_alignment.assert_called_once()
        self.assertEqual([c.args[0] for c in machine.action.call_args_list],
                         ['motion', 'navigation', 'motion'])
        self.assertEqual(machine.action.call_args_list[-1].args[1]['task_name'],
                         'local_front_box/separate_right_cruzr')
        self.assertEqual(machine.measure_box_for_pickup.call_count, 2)
        self.assertEqual(machine.checkpoint['completed'].count('grasp'), 1)
        ready = [c.kwargs for c in machine.emit.call_args_list
                 if c.args == ('box_alignment',) and c.kwargs.get('phase') == 'ready'][-1]
        self.assertAlmostEqual(ready['total_requested_m'], .0154)

    def test_outside_box_gets_new_larger_goal_from_new_pose_and_never_old_client(self):
        machine = self.machine([self.observation(x=.7854),
            self.observation(x=.779, stamp=200, base_x=1.008),
            self.observation(x=.761, stamp=300, base_x=1.025)])
        machine.pose_references.return_value = [dict(x=1.025, y=2., yaw=0.)]*2
        machine.action.side_effect = [fixtures.SUCCESS, self.stopped(), fixtures.SUCCESS, fixtures.SUCCESS]
        machine.stage(dict(stage='grasp'))
        requests = [c for c in machine.action.call_args_list if c.args[0] == 'navigation']
        self.assertEqual(len(requests), 2)
        self.assertTrue(requests[0].kwargs['recover_no_progress'])
        self.assertFalse(requests[1].kwargs['recover_no_progress'])
        spec = requests[1].kwargs['correction']
        self.assertAlmostEqual(spec['reference']['x'], 1.008)
        self.assertAlmostEqual(spec['target']['point_x'], 1.033)
        self.assertEqual(spec['attempt'], 2)
        ready = [c.kwargs for c in machine.emit.call_args_list
                 if c.args == ('box_alignment',) and c.kwargs.get('phase') == 'ready'][-1]
        self.assertAlmostEqual(ready['total_requested_m'], .0404)

    def test_second_cancellation_is_not_recovered(self):
        machine = self.machine([self.observation(x=.7854),
            self.observation(x=.779, stamp=200, base_x=1.008)])
        machine.action.side_effect = [fixtures.SUCCESS, self.stopped(), self.stopped()]
        with self.assertRaisesRegex(RuntimeError, 'RECOVERY_LIMIT'):
            machine.align_box_for_pickup()
        machine.recover_box_alignment.assert_called_once()
        self.assertEqual(machine.action.call_count, 3)

    def test_plain_error_text_health_and_other_failures_never_recover(self):
        for reason in ('Correction made no significant progress', 'estop not confirmed clear',
                       'WORKER_DISCONNECTED', 'Correction velocity exceeds limit'):
            machine = self.machine([self.observation(x=.7854)])
            machine.action.side_effect = [fixtures.SUCCESS, RuntimeError(reason)]
            with self.subTest(reason=reason), self.assertRaises(RuntimeError):
                machine.align_box_for_pickup()
            machine.recover_box_alignment.assert_not_called()
            self.assertEqual(machine.action.call_count, 2)

    def test_canceled_partial_goal_consumes_distance_budget(self):
        machine = self.machine([self.observation(x=.82),
            self.observation(x=.798, stamp=200, base_x=1.022),
            self.observation(x=.785, stamp=300, base_x=1.035)])
        machine.pose_references.return_value = [dict(x=1.041, y=2., yaw=0.)]*2
        machine.action.side_effect = [fixtures.SUCCESS, self.stopped(), fixtures.SUCCESS]
        with self.assertRaisesRegex(RuntimeError, 'BOX_ALIGNMENT_LIMIT.*distance'):
            machine.align_box_for_pickup()
        self.assertEqual(machine.action.call_count, 3)
        limit = [c.kwargs for c in machine.emit.call_args_list
                 if c.args == ('box_alignment',) and c.kwargs.get('phase') == 'limit'][-1]
        self.assertAlmostEqual(limit['total_requested_m'], .078)
        self.assertAlmostEqual(limit['next_step_m'], .025)

    def test_recovery_never_resets_original_deadline(self):
        machine = self.machine([self.observation(x=.7854)])
        clock = [100.]
        machine.action.side_effect = [fixtures.SUCCESS, self.stopped()]
        machine.recover_box_alignment.side_effect = lambda error: clock.__setitem__(0, 221.)
        with patch.object(runtime.time, 'monotonic', side_effect=lambda: clock[0]), \
                self.assertRaisesRegex(RuntimeError, 'TOTAL_BUDGET'):
            machine.align_box_for_pickup()
        self.assertEqual(machine.action.call_count, 2)
        self.assertEqual(machine.measure_box_for_pickup.call_count, 1)

    def test_changed_box_or_no_visual_improvement_blocks_new_motion(self):
        for next_x in (.74, .7854):
            machine = self.machine([self.observation(x=.7854),
                self.observation(x=next_x, stamp=200)])
            machine.action.side_effect = [fixtures.SUCCESS, self.stopped()]
            with self.subTest(next_x=next_x), self.assertRaises((ValueError, RuntimeError)):
                machine.align_box_for_pickup()
            self.assertEqual(machine.action.call_count, 2)
            self.assertFalse((machine.session/'box-alignment-reference.json').exists())

    def test_recovery_goal_preserves_observation_and_native_envelope(self):
        pending = self.observation(x=.7854)[0]
        original = copy.deepcopy(pending)
        delta = alignment.displacement(pending, recovery=True)
        self.assertAlmostEqual(delta['x'], .025)
        self.assertEqual(pending, original)
        self.assertGreaterEqual(.7854-delta['x'], .43)
        self.assertLessEqual(.7854-delta['x'], .77)
        self.assertLessEqual(abs(delta['x']), alignment.POLICY['max_step_m'])


class RecoveryAdmissionTest(unittest.TestCase):
    def machine(self):
        helper = fixtures.AlignmentRuntimeTests()
        self.addCleanup(helper.doCleanups)
        machine = helper.machine([])
        report = fixtures.posture()
        for index, sample in enumerate(report['actuator']):
            sample['header'] = dict(stamp=dict(sec=0, nanosec=200+index))
        machine.health.return_value = report
        machine.stationary_base = Mock(return_value=fixtures.base_report(300))
        machine.pose_references.return_value = [dict(x=1., y=2., yaw=0., stamp_ns=n) for n in (400, 401)]
        machine.map_state = Mock(return_value=('utars_nav_map', 'FSM_WAITNAVIGATE'))
        machine.map_points = Mock()
        marker = evidence()[1][-1]
        channel = SimpleNamespace(failed=False, recovery_pending=marker, sequence=1,
            process=SimpleNamespace(poll=lambda: None, returncode=0), close=Mock(return_value=[
                dict(event='session_closed', request_id=None, reason='Request input pipe disconnected')]))
        machine.action_sessions['navigation'] = channel
        return machine, channel, recovery.CorrectionRecoveryRequired(marker, channel)

    def test_only_confirmed_post_cancel_rest_can_retire_old_client(self):
        machine, channel, error = self.machine()
        machine.recover_box_alignment(error)
        channel.close.assert_called_once()
        self.assertNotIn('navigation', machine.action_sessions)
        machine.map_state.assert_called_once()
        machine.action.assert_not_called()

    def test_fault_posture_stale_odom_map_and_worker_fail_before_retirement(self):
        for problem in ('health', 'posture', 'old_posture', 'old_odom', 'old_map', 'moving_map', 'worker'):
            machine, channel, error = self.machine()
            if problem == 'health': machine.health.side_effect = RuntimeError('fault')
            if problem == 'posture': machine.health.return_value['actuator'][0]['act_item'][2]['position'] = .3
            if problem == 'old_posture': machine.health.return_value['actuator'][0]['header']['stamp']['nanosec'] = 99
            if problem == 'old_odom': machine.stationary_base.return_value = fixtures.base_report(100)
            if problem == 'old_map': machine.pose_references.return_value[0]['stamp_ns'] = 99
            if problem == 'moving_map': machine.pose_references.return_value[1]['x'] += .006
            if problem == 'worker': channel.process.poll = lambda: 2
            with self.subTest(problem=problem), self.assertRaises((ValueError, RuntimeError)):
                machine.recover_box_alignment(error)
            channel.close.assert_not_called()
            machine.map_state.assert_not_called()

    def test_retirement_or_busy_map_never_allows_measurement_or_motion(self):
        for problem in ('retirement', 'opaque_output', 'map'):
            machine, channel, error = self.machine()
            if problem == 'retirement': channel.process.returncode = 2
            elif problem == 'opaque_output': channel.close.return_value.insert(0, dict(event='worker_log', text='fault'))
            else: machine.map_state.return_value = ('utars_nav_map', 'FSM_NAVIGATING')
            with self.subTest(problem=problem), self.assertRaises((RuntimeError, ValueError)):
                machine.recover_box_alignment(error)
            machine.measure_box_for_pickup.assert_not_called()
            machine.action.assert_not_called()


class RecoveryPipeTest(unittest.TestCase):
    def session(self, rows, *, opaque_output=False, opaque_after_complete=False):
        worker = '''import json,sys
print(json.dumps({'event':'session_ready','request_id':None}),flush=True)
request=json.loads(sys.stdin.readline())
if OPAQUE: print('unclassified native output',flush=True)
for row in ROWS:
 row['request_id']=request['request_id'];print(json.dumps(row),flush=True)
print(json.dumps({'event':'request_complete','request_id':request['request_id'],'returncode':4}),flush=True)
if LATEOPAQUE: print('unclassified native output after marker',flush=True)
for line in sys.stdin: raise RuntimeError('retire-only')
print(json.dumps({'event':'session_closed','request_id':None,'reason':'Request input pipe disconnected'}),flush=True)
'''.replace('ROWS', repr(rows)).replace('LATEOPAQUE', repr(opaque_after_complete)).replace('OPAQUE', repr(opaque_output))
        return ProcessSession([sys.executable, '-u', '-B', '-c', worker], lambda event: None)

    def test_valid_canceled_outcome_parks_without_poison_or_another_request(self):
        request, rows = evidence()
        channel = self.session(rows)
        try:
            received = channel.call(request, timeout=2)
            self.assertEqual(received[-1]['event'], recovery.EVENT)
            self.assertFalse(channel.failed)
            self.assertEqual(channel.recovery_pending['code'], 'NO_PROGRESS_CANCELLED')
            with self.assertRaisesRegex(RuntimeError, 'RECOVERY_PENDING'):
                channel.call(request, timeout=2)
        finally:
            channel.close()
        self.assertEqual(channel.process.returncode, 0)

    def test_code_four_without_proof_or_explicit_scope_is_fatal(self):
        for problem in ('ack', 'optin'):
            request, rows = evidence()
            if problem == 'ack': rows.pop(3)
            else: request.pop('allow_correction_recovery')
            channel = self.session(rows)
            try:
                with self.subTest(problem=problem), self.assertRaises(ValueError):
                    channel.call(request, timeout=2)
                self.assertTrue(channel.failed)
            finally:
                channel.close()

    def test_unclassified_native_output_blocks_recovery_even_with_valid_marker(self):
        request, rows = evidence()
        channel = self.session(rows, opaque_output=True)
        try:
            with self.assertRaisesRegex(RuntimeError, 'RECOVERY_UNCLASSIFIED_OUTPUT'):
                channel.call(request, timeout=2)
            self.assertTrue(channel.failed)
            self.assertIsNone(channel.recovery_pending)
        finally:
            channel.close()

    def test_unclassified_output_after_marker_blocks_zero_exit_retirement(self):
        request, rows = evidence()
        channel = self.session(rows, opaque_after_complete=True)
        channel.call(request, timeout=2)
        trailing = channel.close()
        self.assertEqual(channel.process.returncode, 0)
        with self.assertRaisesRegex(ValueError, 'RETIREMENT_INVALID'):
            recovery.validate_retirement(channel.recovery_pending, trailing, str(channel.sequence))


class RecoveryConsoleTest(unittest.TestCase):
    def test_only_typed_navigation_outcome_is_presented_as_pending_recovery(self):
        reporter = fixtures.ConsoleReporter()
        typed = dict(event='error', reason='Correction made no significant progress',
                     failure_code=recovery.FAILURE_CODE)
        self.assertIn('evaluar una recuperación', reporter.detail(typed, 'navigation')[0])
        self.assertIn('ERROR', reporter.detail(typed, 'motion')[0])
        self.assertIn('ERROR', reporter.detail(dict(typed, failure_code=None), 'navigation')[0])
        self.assertIn('pendiente', reporter.detail(dict(event='request_complete', returncode=4), 'navigation')[0])
        self.assertIn('ERROR', reporter.detail(dict(event='request_complete', returncode=4), 'motion')[0])

    def test_console_distinguishes_cancel_acceptance_and_measured_stationarity(self):
        reporter = fixtures.ConsoleReporter()
        pending = reporter.render(dict(event='box_alignment', phase='recovery_required'))
        stopped = reporter.render(dict(event='box_alignment', phase='recovery_stationary'))
        self.assertIn('comprobando reposo', pending[0])
        self.assertIn('Chasis detenido', stopped[0])
        self.assertIn('sin volver a HOME', stopped[0])


if __name__ == '__main__':
    unittest.main()
