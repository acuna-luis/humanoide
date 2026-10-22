"""Cancellation evidence regressions; no ROS clients, connections or motion."""
import copy
import unittest
import uuid

from scripts.box_handling import scenario1_correction_recovery as recovery


GOAL_ID = 'c8fd5d60-9f44-4662-ace6-3ede6365cfea'
OTHER_ID = '9681d437-685a-48b0-b60a-a3b7d40e9f06'


def evidence():
    request = dict(goal=dict(command='navigation_start'),
                   correction=dict(point='box_pickup', attempt=1),
                   allow_correction_recovery=True)

    def row(event, **values):
        return dict(event=event, goal_id=GOAL_ID, **values)

    rows = [row('accepted', accepted=True),
            row('error', failure_code=recovery.FAILURE_CODE,
                reason='Correction made no significant progress'),
            row('cancel_requested', physical_stop_verified=False),
            row('cancel_response', response=dict(return_code=0, goals_canceling=[
                dict(goal_id=dict(uuid=list(uuid.UUID(GOAL_ID).bytes)))])),
            row('result', status=5, result={}),
            row('interrupted_terminal', status=5, physical_stop_verified=False),
            row(recovery.EVENT, version=1, code='NO_PROGRESS_CANCELLED', attempt=1,
                terminal_received_ns=100, physical_stop_verified=False)]
    return request, rows


class CorrectionRecoveryContractTest(unittest.TestCase):
    def assert_invalid(self, mutate):
        request, rows = evidence()
        mutate(request, rows)
        with self.assertRaisesRegex(ValueError, 'CORRECTION_RECOVERY_INVALID'):
            recovery.validate_recovery(request, rows)

    def test_valid_marker_is_isolated_and_claims_no_physical_stop(self):
        request, rows = evidence()
        report = recovery.validate_recovery(request, rows)
        self.assertEqual(report, rows[-1])
        self.assertIsNot(report, rows[-1])
        report['goal_id'] = OTHER_ID
        self.assertEqual(rows[-1]['goal_id'], GOAL_ID)
        self.assertIs(rows[-1]['physical_stop_verified'], False)
        self.assertEqual(recovery.RECOVERY_RETURN_CODE, 4)

    def test_result_can_precede_cancel_acknowledgment(self):
        request, rows = evidence()
        rows[3], rows[4] = rows[4], rows[3]
        recovery.validate_recovery(request, rows)

    def test_all_seven_permitted_attempts_and_strict_integer_types(self):
        for attempt in range(1, 8):
            request, rows = evidence()
            request['correction']['attempt'] = rows[-1]['attempt'] = attempt
            recovery.validate_recovery(request, rows)
        for value in (0, 8, True, False, 1., '1', None):
            with self.subTest(value=value):
                self.assert_invalid(lambda request, rows: request['correction'].update(attempt=value))
                self.assert_invalid(lambda request, rows: rows[-1].update(attempt=value))

    def test_get1_motion_and_nonexplicit_optin_never_qualify(self):
        for value in (False, 1, 'true', None):
            with self.subTest(value=value):
                self.assert_invalid(lambda request, rows: request.update(allow_correction_recovery=value))
        self.assert_invalid(lambda request, rows: request.pop('allow_correction_recovery'))
        self.assert_invalid(lambda request, rows: request['correction'].update(point='get1'))
        self.assert_invalid(lambda request, rows: request['goal'].update(command='home'))
        self.assert_invalid(lambda request, rows: request.update(goal=None))
        self.assert_invalid(lambda request, rows: request.update(correction=[]))

    def test_every_decisive_event_must_exist_exactly_once(self):
        for index in range(7):
            with self.subTest(index=index, mode='missing'):
                self.assert_invalid(lambda request, rows: rows.pop(index))
            with self.subTest(index=index, mode='duplicate'):
                self.assert_invalid(lambda request, rows: rows.insert(index, copy.deepcopy(rows[index])))

    def test_every_event_identity_must_match(self):
        for index in range(7):
            with self.subTest(index=index):
                self.assert_invalid(lambda request, rows: rows[index].update(goal_id=OTHER_ID))

    def test_noncanonical_uuid_rejected_even_if_all_rows_agree(self):
        for value in ('uuid-1', GOAL_ID.upper(), GOAL_ID.replace('-', ''), None, 1):
            def mutate(request, rows):
                for row in rows:
                    row['goal_id'] = value
            with self.subTest(value=value):
                self.assert_invalid(mutate)

    def test_acknowledgment_requires_zero_integer_and_one_exact_uuid(self):
        for value in (True, False, 0., '0', None, 1):
            with self.subTest(value=value):
                self.assert_invalid(lambda request, rows: rows[3]['response'].update(return_code=value))
        for value in ([], None, {}, [dict(goal_id=dict(uuid=list(uuid.UUID(OTHER_ID).bytes)))],
                      [dict(goal_id=dict(uuid=[0]*16))]*2):
            with self.subTest(value=value):
                self.assert_invalid(lambda request, rows: rows[3]['response'].update(goals_canceling=value))

    def test_cancel_uuid_bytes_must_be_sixteen_nonboolean_integers(self):
        for value in ([0]*15, [0]*17, [True]+[0]*15, [-1]+[0]*15,
                      [256]+[0]*15, ['0']+[0]*15, [0.]+[0]*15, GOAL_ID, None):
            with self.subTest(value=value):
                self.assert_invalid(lambda request, rows: rows[3]['response']['goals_canceling'][0]['goal_id'].update(uuid=value))

    def test_success_abort_and_boolean_result_status_are_not_canceled(self):
        for index in (4, 5):
            for status in (4, 6, True, False, 5., '5', None):
                with self.subTest(index=index, status=status):
                    self.assert_invalid(lambda request, rows: rows[index].update(status=status))

    def test_late_success_or_duplicate_terminal_cannot_be_recovered(self):
        self.assert_invalid(lambda request, rows: rows.insert(-1,
            dict(event='result', goal_id=GOAL_ID, status=4, result={})))
        self.assert_invalid(lambda request, rows: rows.append(
            dict(event='result', goal_id=GOAL_ID, status=4, result={})))

    def test_only_typed_no_progress_error_qualifies(self):
        self.assert_invalid(lambda request, rows: rows[1].pop('failure_code'))
        self.assert_invalid(lambda request, rows: rows[1].update(failure_code='ESTOP'))
        self.assert_invalid(lambda request, rows: rows[1].update(reason='Correction telemetry stale'))
        self.assert_invalid(lambda request, rows: rows.insert(2,
            dict(event='error', goal_id=GOAL_ID, reason='Lease expired')))

    def test_rejected_unknown_terminal_and_worker_failures_rejected(self):
        for event in ('rejected', 'terminal_unknown', 'worker_error', 'worker_log',
                      'worker_closed', 'worker_exit_unconfirmed', 'unrecognized'):
            with self.subTest(event=event):
                self.assert_invalid(lambda request, rows: rows.insert(2,
                    dict(event=event, goal_id=GOAL_ID)))

    def test_positive_acceptance_and_unknown_physical_stop_required(self):
        for value in (False, 1, None, 'true'):
            self.assert_invalid(lambda request, rows: rows[0].update(accepted=value))
        for index in (2, 5, 6):
            for value in (True, 0, None, 'false'):
                with self.subTest(index=index, value=value):
                    self.assert_invalid(lambda request, rows: rows[index].update(physical_stop_verified=value))

    def test_marker_fields_types_and_terminal_receipt(self):
        for value in (True, 1., '1', None, 2):
            self.assert_invalid(lambda request, rows: rows[-1].update(version=value))
        for value in (0, -1, True, 1., '100', None):
            self.assert_invalid(lambda request, rows: rows[-1].update(terminal_received_ns=value))
        self.assert_invalid(lambda request, rows: rows[-1].update(code='SUCCESS'))
        self.assert_invalid(lambda request, rows: rows[-1].update(arbitrary=True))
        self.assert_invalid(lambda request, rows: rows[-1].update(time_ns=99))
        self.assert_invalid(lambda request, rows: rows[-1].pop('physical_stop_verified'))
        self.assert_invalid(lambda request, rows: rows[-1].update(attempt=2))

    def test_ordered_receipts_and_marker_closes_evidence(self):
        for first, second in ((0, 1), (1, 2), (2, 3), (2, 4), (4, 5), (5, 6)):
            def mutate(request, rows):
                rows[first], rows[second] = rows[second], rows[first]
            with self.subTest(first=first, second=second):
                self.assert_invalid(mutate)
        self.assert_invalid(lambda request, rows: rows.append(
            dict(event='feedback', goal_id=GOAL_ID, feedback={})))

    def test_optional_metadata_is_checked_when_present(self):
        request, rows = evidence()
        request['request_id'] = 'r1'
        for index, row in enumerate(rows):
            row.update(request_id='r1', time_ns=100+index)
        recovery.validate_recovery(request, rows)
        rows[2]['request_id'] = 'r2'
        with self.assertRaises(ValueError):
            recovery.validate_recovery(request, rows)
        for value in (True, 0, '100'):
            self.assert_invalid(lambda request, rows: rows[0].update(time_ns=value))

    def test_pre_dispatch_guard_snapshots_can_have_no_uuid(self):
        request, rows = evidence()
        for phase in ('preparing', 'armed'):
            rows.insert(0, dict(event='correction_guard', phase=phase, goal_id=None))
        recovery.validate_recovery(request, rows)
        rows[0]['phase'] = 'failed'
        with self.assertRaises(ValueError):
            recovery.validate_recovery(request, rows)

    def test_nonterminal_statuses_allowed_but_conflicting_terminal_blocked(self):
        for status in (1, 2, 3, 5):
            request, rows = evidence()
            rows.insert(1, dict(event='status', goal_id=GOAL_ID, status=status))
            recovery.validate_recovery(request, rows)
        for status in (0, 4, 6, True, '5', 5.):
            self.assert_invalid(lambda request, rows: rows.insert(1,
                dict(event='status', goal_id=GOAL_ID, status=status)))

    def test_guard_snapshots_preserve_identity_and_only_latched_no_progress(self):
        for failure in (None, 'Correction made no significant progress'):
            for telemetry_failure in (None, 'Correction made no significant progress'):
                request, rows = evidence()
                rows.insert(2, dict(event='correction_guard', goal_id=GOAL_ID,
                    phase='failed', snapshot=dict(point='box_pickup', attempt=1,
                        failure=failure, telemetry_failure=telemetry_failure,
                        velocity_violation=None)))
                recovery.validate_recovery(request, rows)
        for snapshot in (None, [], {},
                dict(point='get1', attempt=1),
                dict(point='box_pickup', attempt=2),
                dict(point='box_pickup', attempt=True),
                dict(point='box_pickup', attempt=1., failure=None),
                dict(point='box_pickup', attempt=1, failure='Correction telemetry stale'),
                dict(point='box_pickup', attempt=1, telemetry_failure='estop'),
                dict(point='box_pickup', attempt=1, velocity_violation={}),
                dict(point='box_pickup', attempt=1, telemetry_failure=False),
                dict(point='box_pickup', attempt=1, failure=False)):
            with self.subTest(snapshot=snapshot):
                self.assert_invalid(lambda request, rows: rows.insert(2,
                    dict(event='correction_guard', goal_id=GOAL_ID,
                         phase='failed', snapshot=snapshot)))

    def test_malformed_evidence_rejected_and_exception_preserves_channel(self):
        request, rows = evidence()
        for value in (None, [], {}, [None], ['error']):
            with self.subTest(value=value), self.assertRaises(ValueError):
                recovery.validate_recovery(request, value)
        channel = object()
        error = recovery.CorrectionRecoveryRequired(rows[-1], channel)
        self.assertIs(error.channel, channel)
        self.assertEqual(error.report, rows[-1])
        error.report['attempt'] = 7
        self.assertEqual(rows[-1]['attempt'], 1)


class CorrectionRetirementContractTest(unittest.TestCase):
    def evidence(self):
        _, rows = evidence()
        tail = [dict(event='status', goal_id=GOAL_ID, request_id='14', status=5),
                dict(event='feedback', goal_id=GOAL_ID, request_id='14', feedback={}),
                dict(event='session_closed', request_id=None,
                     reason='Request input pipe disconnected')]
        return rows[-1], tail

    def test_confirmed_eof_with_optional_trailing_status_and_feedback(self):
        marker, rows = self.evidence()
        result = recovery.validate_retirement(marker, rows, '14')
        self.assertEqual(result, rows)
        self.assertIsNot(result, rows)
        result[0]['status'] = 4
        self.assertEqual(rows[0]['status'], 5)
        recovery.validate_retirement(marker, rows[-1:], '14')

    def test_no_opaque_error_or_unconfirmed_exit_can_precede_eof(self):
        marker, rows = self.evidence()
        for event in ('error', 'worker_log', 'worker_exit_unconfirmed', 'worker_closed',
                      'result', 'terminal_unknown', recovery.EVENT, 'unknown'):
            bad = copy.deepcopy(rows)
            bad.insert(1, dict(event=event, goal_id=GOAL_ID, request_id='14'))
            with self.subTest(event=event), self.assertRaises(ValueError):
                recovery.validate_retirement(marker, bad, '14')

    def test_missing_duplicate_or_misordered_session_close_rejected(self):
        marker, rows = self.evidence()
        variants = [rows[:-1], rows+[copy.deepcopy(rows[-1])],
                    [rows[-1]]+rows[:-1], [], None, {}, [None]]
        for bad in variants:
            with self.subTest(rows=bad), self.assertRaises(ValueError):
                recovery.validate_retirement(marker, bad, '14')

    def test_every_trailing_callback_requires_matching_goal_and_request(self):
        marker, rows = self.evidence()
        for index in (0, 1):
            for field, value in (('goal_id', OTHER_ID), ('goal_id', None),
                                 ('request_id', None), ('request_id', 14),
                                 ('request_id', '15')):
                bad = copy.deepcopy(rows)
                bad[index][field] = value
                with self.subTest(index=index, field=field, value=value), self.assertRaises(ValueError):
                    recovery.validate_retirement(marker, bad, '14')

    def test_only_permitted_integer_statuses_survive_retirement(self):
        marker, rows = self.evidence()
        for status in (1, 2, 3, 5):
            rows[0]['status'] = status
            recovery.validate_retirement(marker, rows, '14')
        for status in (0, 4, 6, True, False, 5., '5', None):
            rows[0]['status'] = status
            with self.subTest(status=status), self.assertRaises(ValueError):
                recovery.validate_retirement(marker, rows, '14')

    def test_close_has_explicit_uncorrelated_eof_and_no_other_reason(self):
        marker, rows = self.evidence()
        for values in (dict(request_id='14'), dict(request_id=False), dict(reason=None),
                       dict(reason='Lease expired'), dict(reason=''), dict(reason=True)):
            bad = copy.deepcopy(rows)
            bad[-1].update(values)
            with self.subTest(values=values), self.assertRaises(ValueError):
                recovery.validate_retirement(marker, bad, '14')
        del rows[-1]['request_id']
        with self.assertRaises(ValueError):
            recovery.validate_retirement(marker, rows, '14')

    def test_marker_and_receipt_types_remain_strict(self):
        marker, rows = self.evidence()
        for values in (dict(event='result'), dict(goal_id='uuid-1'),
                       dict(version=True), dict(physical_stop_verified=True),
                       dict(code='SUCCESS')):
            bad = dict(marker, **values)
            with self.subTest(values=values), self.assertRaises(ValueError):
                recovery.validate_retirement(bad, rows, '14')
        for request_id in (None, 14, True, ''):
            with self.subTest(request_id=request_id), self.assertRaises(ValueError):
                recovery.validate_retirement(marker, rows, request_id)
        for value in (True, 0, '10'):
            bad = copy.deepcopy(rows)
            bad[0]['time_ns'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                recovery.validate_retirement(marker, bad, '14')


if __name__ == '__main__':
    unittest.main()
