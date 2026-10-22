"""Offline admission of a successful native action followed by a log-only error."""
import copy
import hashlib
import json
from pathlib import Path
import unittest

from scripts.box_handling import scenario1_table74_log_recovery as recovery
from scripts.box_handling.test_scenario1_table74_current_lower_run import predecessor
from scripts.box_handling.test_scenario1_table74_current_trial_run import PROFILE


def authorize(proof):
    """Bind synthetic raw encodings, or rebind a deliberately mutated fixture."""
    originals = {name: value for name, value in proof.items() if name != recovery.AUTHORIZATION_FILE}
    proof[recovery.AUTHORIZATION_FILE] = dict(version=1, kind='table74_log_only_recovery',
        next_stage='precontact', source_directory='/private/offline/table74-approach',
        source_sha256={name: hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
                       for name, value in originals.items()}, proof_sha256=recovery.digest(originals),
        operator_state_assumed_unchanged=True, current_physical_measurement=False)
    return proof


def fixture_source():
    """A genuine-contract synthetic failed approach, with its raw failure intact."""
    proof = predecessor()
    journal = dict(proof['trial.json'], phase='failed', error=recovery.ALLOWED_ERROR)
    proof['trial.json'] = copy.deepcopy(journal)
    events = proof['events.jsonl']
    events[:] = [e for e in events if e['event'] not in ('stage_complete', 'session_finishing')]
    events[-1]['trial'] = copy.deepcopy(journal)
    events.append(dict(event='error', time_ns=80, reason=recovery.ALLOWED_ERROR, physical_state='unconfirmed'))
    for offset, kind in enumerate(('navigation', 'motion', 'health_worker')):
        detail = dict(event='error', request_id=None,
            reason=('RuntimeError: Health worker lease expired or stop requested' if kind == 'health_worker'
                    else 'Lease missing, invalid or expired'))
        if kind != 'health_worker':
            detail['goal_id'] = None
        wrapper = dict(event='health_worker') if kind == 'health_worker' else dict(event='action', kind=kind)
        events.append(dict(wrapper, time_ns=90+offset*2, detail=detail))
        events.append(dict(wrapper, time_ns=91+offset*2, detail=dict(event='worker_closed',
            returncode=78 if kind == 'health_worker' else 2, physical_stop_verified=False)))
    return authorize(proof), copy.deepcopy(PROFILE)


class LogRecoveryTests(unittest.TestCase):
    def validate(self, proof=None):
        proof, profile = fixture_source() if proof is None else (proof, PROFILE)
        return recovery.validate_proof(proof, profile)

    def test_admits_only_next_phase_without_rewriting_failed_evidence(self):
        proof, profile = fixture_source(); original = copy.deepcopy(proof)
        info = recovery.validate_proof(proof, profile)
        self.assertEqual(proof, original)
        self.assertEqual(info['completed_stage'], 'approach')
        self.assertEqual(info['phase'], 'approach_vendor_reference')
        self.assertIs(info['planned']['executable'], False)
        self.assertEqual(info['predecessor_sha256'], recovery.digest(proof))
        self.assertEqual(info['planned']['source_sha256'], recovery.digest(proof))
        self.assertEqual(info['planned']['requirements'], dict(box_state='held', home=False,
                                                             waypoint='put1', vision_prep=False))
        self.assertFalse(info['diagnostic_debt']['native_log_verified'])
        self.assertFalse(info['diagnostic_debt']['current_physical_measurement'])
        self.assertEqual(proof['trial.json']['phase'], 'failed')
        info['chain_bundles'][0]['task_name'] = 'changed-output'
        self.assertEqual(proof, original)

    def test_receipt_exact_types_scope_and_raw_hash_names_are_required(self):
        for change in ('missing', 'extra_file', 'version_bool', 'kind', 'stage', 'relative_directory',
                       'traversal_directory', 'source_hash_bool', 'source_hash_missing', 'proof_digest',
                       'operator_false', 'measurement_true', 'unknown_field'):
            proof, _ = fixture_source(); receipt = proof[recovery.AUTHORIZATION_FILE]
            if change == 'missing': proof.pop(recovery.AUTHORIZATION_FILE)
            elif change == 'extra_file': proof['extra.json'] = {}
            elif change == 'version_bool': receipt['version'] = True
            elif change == 'kind': receipt['kind'] = 'generic_recovery'
            elif change == 'stage': receipt['next_stage'] = 'support'
            elif change == 'relative_directory': receipt['source_directory'] = 'relative'
            elif change == 'traversal_directory': receipt['source_directory'] = '/private/../other'
            elif change == 'source_hash_bool': receipt['source_sha256']['trial.json'] = True
            elif change == 'source_hash_missing': receipt['source_sha256'].pop('trial.json')
            elif change == 'proof_digest': receipt['proof_sha256'] = '0'*64
            elif change == 'operator_false': receipt['operator_state_assumed_unchanged'] = False
            elif change == 'measurement_true': receipt['current_physical_measurement'] = True
            else: receipt['qualified'] = True
            with self.subTest(change=change), self.assertRaises(ValueError): self.validate(proof)

    def test_original_tamper_is_detected_even_before_semantic_validation(self):
        proof, _ = fixture_source(); proof['context.json']['boot_id'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'original proof identity'): self.validate(proof)

    def test_only_exact_log_failure_after_success_is_recoverable(self):
        for phase, error in (('succeeded', None), ('failed', 'TABLE74_NATIVE_FAULT: DectionForceCollision'),
                             ('failed', 'TABLE74_NATIVE_IDENTITY: other error'), ('pending', None)):
            proof, _ = fixture_source(); journal = proof['trial.json']
            journal.update(phase=phase, error=error)
            proof['events.jsonl'][-8]['trial'] = copy.deepcopy(journal)
            authorize(proof)
            with self.subTest(phase=phase, error=error), self.assertRaises(ValueError): self.validate(proof)

    def test_goal_result_request_acceptance_and_status_are_strict(self):
        for change in ('uuid', 'other_goal', 'second_result', 'status_bool', 'status_aborted',
                       'code', 'rejected', 'request_id', 'complete_missing', 'complete_bool',
                       'late_failure', 'cancel', 'motion_unknown'):
            proof, _ = fixture_source(); events = proof['events.jsonl']
            native = [e for e in events if e.get('event') == 'action' and e.get('kind') == 'motion'
                      and e.get('detail', {}).get('event') != 'worker_closed']
            row = lambda name: next(e for e in native if e['detail']['event'] == name)
            if change == 'uuid': proof['trial.json']['result']['goal_id'] = 'not-a-uuid'
            elif change == 'other_goal': row('accepted')['detail']['goal_id'] = 'b765c1be-d570-4aaa-b267-b7af56d6fc25'
            elif change == 'second_result': events.insert(6, copy.deepcopy(row('result')))
            elif change == 'status_bool': proof['trial.json']['result']['status'] = True
            elif change == 'status_aborted': proof['trial.json']['result']['status'] = 6
            elif change == 'code': proof['trial.json']['result']['result']['state']['state'] = 7104050
            elif change == 'rejected': row('accepted')['detail']['accepted'] = False
            elif change == 'request_id': row('accepted')['detail']['request_id'] = '2'
            elif change == 'complete_missing': events.remove(row('request_complete'))
            elif change == 'complete_bool': row('request_complete')['detail']['returncode'] = False
            else:
                inserted = copy.deepcopy(row('accepted')); inserted['time_ns'] = 45
                if change == 'late_failure': inserted['detail'].update(event='status', status=6)
                elif change == 'cancel': inserted['detail']['event'] = 'cancel_requested'
                else: inserted['detail']['event'] = 'unreviewed_action'
                events.insert(5, inserted)
            authorize(proof)
            with self.subTest(change=change), self.assertRaises(ValueError): self.validate(proof)

    def test_physical_worker_or_navigation_error_cannot_be_relabelled_log_only(self):
        for change in ('health_error', 'force_log', 'feedback_fault', 'estop', 'nav_after', 'nav_unknown', 'nav_failed', 'top_error',
                       'terminal_unknown', 'session_finishing', 'stage_complete'):
            proof, _ = fixture_source(); events = proof['events.jsonl']
            extra = dict(event='health_worker', time_ns=25, detail=dict(event='error', reason='stale telemetry'))
            if change == 'force_log': extra['detail'] = dict(event='worker_log', text='Collision force on right_hand axis[2] exceeded limit 3 times, exiting.')
            elif change == 'feedback_fault': extra = dict(event='action', kind='motion', time_ns=45,
                detail=dict(event='feedback', feedback=dict(state=dict(desc='DectionForceCollision'))))
            elif change == 'estop': extra = dict(event='health', time_ns=25, safety=dict(estop=1, servo_estop=0, charger=0))
            elif change == 'nav_after': extra = dict(event='action', kind='navigation', time_ns=45, detail=dict(event='dispatched'))
            elif change == 'nav_unknown': extra = dict(event='action', kind='navigation', time_ns=25, detail=dict(event='unreviewed_action'))
            elif change == 'nav_failed': extra = dict(event='action', kind='navigation', time_ns=25, detail=dict(event='status', status=6))
            elif change == 'top_error': extra = dict(event='error', time_ns=25, reason='fault')
            elif change == 'terminal_unknown': extra['detail']['event'] = 'terminal_unknown'
            elif change in ('session_finishing', 'stage_complete'): extra = dict(event=change, time_ns=25)
            events.insert(3 if extra['time_ns'] == 25 else 5, extra); authorize(proof)
            with self.subTest(change=change), self.assertRaises(ValueError): self.validate(proof)

    def test_closure_must_be_complete_idle_and_after_diagnostic_failure(self):
        for change in ('missing_worker', 'missing_close', 'goal_in_tail', 'wrong_rc', 'rc_bool', 'new_goal', 'extra_close'):
            proof, _ = fixture_source(); events = proof['events.jsonl']
            if change == 'missing_worker': del events[-2:]
            elif change == 'missing_close': events.pop()
            elif change == 'goal_in_tail': events[-2]['detail']['request_id'] = '1'
            elif change == 'wrong_rc': events[-1]['detail']['returncode'] = 0
            elif change == 'rc_bool': events[-1]['detail']['returncode'] = True
            elif change == 'new_goal': events[-1]['detail']['event'] = 'dispatched'
            else: events.append(dict(events[-1], time_ns=100))
            authorize(proof)
            with self.subTest(change=change), self.assertRaises(ValueError): self.validate(proof)

    def test_context_dependencies_journal_and_order_mutations_are_rejected(self):
        for change in ('ready_context', 'source', 'dependencies', 'missing_dependencies', 'third_trial',
                       'timestamp_bool', 'timestamp_regressed', 'terminal_after_failed', 'failed_journal_diff'):
            proof, _ = fixture_source(); events = proof['events.jsonl']
            if change == 'ready_context': proof['context.json']['boot_id'] = 'changed'
            elif change == 'source': proof['source-context.json']['checkpoint']['box_state'] = 'unknown'
            elif change == 'dependencies': events[1]['hashes'] = {}
            elif change == 'missing_dependencies': events.pop(1)
            elif change == 'third_trial': events.insert(3, dict(events[2], time_ns=21))
            elif change == 'timestamp_bool': events[0]['time_ns'] = True
            elif change == 'timestamp_regressed': events[4]['time_ns'] = 1
            elif change == 'terminal_after_failed': proof['trial.json']['finished_ns'] = 45
            else: events[-8]['trial']['error'] = 'different'
            authorize(proof)
            with self.subTest(change=change), self.assertRaises(ValueError): self.validate(proof)

    def test_original_real_offline_failure_is_admitted_without_source_changes(self):
        root = Path(__file__).resolve().parents[3]/'Humanoide-vla-evidence'/(
            '20261022T150133Z_TABLE74_SUPERVISED_CYCLE_1280135/approach/physical-run')
        names = ('bundle.json', 'trial.json', 'source-context.json', 'context-checkpoint.json', 'context.json', 'events.jsonl')
        if not all((root/name).is_file() for name in names): self.skipTest('Private historical evidence is not available')
        raw = {name: (root/name).read_bytes() for name in names}
        proof = {name: ([json.loads(line) for line in value.decode().splitlines() if line.strip()]
                        if name == 'events.jsonl' else json.loads(value)) for name, value in raw.items()}
        authorize(proof)
        proof[recovery.AUTHORIZATION_FILE].update(source_directory=str(root),
            source_sha256={name: hashlib.sha256(value).hexdigest() for name, value in raw.items()})
        info = self.validate(proof)
        self.assertEqual(info['goal_id'], '48339049-920e-4c9b-9762-7774f92c3621')
        self.assertEqual(info['completed_stage'], 'approach')
        self.assertEqual(raw, {name: (root/name).read_bytes() for name in names})


if __name__ == '__main__': unittest.main()
