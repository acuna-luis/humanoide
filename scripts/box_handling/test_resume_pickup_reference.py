"""Historical aligned-resume proof tests; no ROS, network or processes."""
import copy
import json
from pathlib import Path
import unittest

from scripts.box_handling import scenario1_box_alignment as alignment
from scripts.box_handling import scenario1_contract as contract
from scripts.box_handling import scenario1_perception as perception
from scripts.box_handling import resume_pickup_reference as reference
from scripts.box_handling.test_scenario1_box_alignment import detection_report


def fixture_source():
    """A clean held source 50 mm from nominal get1, reproducible without logs."""
    profile = json.loads(Path(__file__).with_name('scenario1_table74_preparation.json').read_text())
    checkpoint = contract.new_checkpoint(profile, stop_after='verify_held', policy='assume',
                                          execution_profile='optimistic_v1')
    for stage in ('navigate_get1', 'enable_vision', 'grasp', 'verify_held'):
        checkpoint = contract.complete_stage(contract.begin_stage(checkpoint, stage), stage,
            **({'confirmed_box': 'held', 'verification_source': 'assumed'} if stage == 'verify_held' else {}))
    context = dict(boot_id='069a60e8-ffbb-4cd2-ae5f-de9efdead0af',
        containers={'native': ['a'*64, '2026-10-22T10:27:22Z'], 'ros2': ['b'*64, '2026-10-22T10:27:22Z']},
        dependencies={'sps_package': 'bf145fa17e1116fc', 'home_sha256': 'c'*64,
                      'vision_sha256': 'd'*64, 'extra': {}}, execution_profile='optimistic_v1',
        points={'get1': {'map_name': 'utars_nav_map', 'id': 'get1', 'mode': 'logo_nav',
                         '_expected_pose': dict(point_x=1., point_y=2., point_yaw=0.)},
                'put1': {'map_name': 'utars_nav_map', 'id': 'put1', 'mode': 'logo_nav',
                         '_expected_pose': dict(point_x=3., point_y=2., point_yaw=0.)}})
    start = 100_000_000_000
    rows = []
    def event(t, name, **fields):
        value = dict(event=name, time_ns=start+int(t*10**9), **fields)
        rows.append(value)
        return value
    def pending(t, x):
        r = detection_report()
        ns = start+int(t*10**9)
        stamp = dict(sec=ns//10**9, nanosec=ns % 10**9)
        r['request_ns'] = ns-50_000_000
        r['vision_result']['trans_outputs']['box_pose']['header']['stamp'] = stamp
        r['vision_result']['trans_outputs']['box_pose']['poses'] = [dict(
            position=dict(x=x, y=.1, z=.7), orientation=dict(x=0., y=0., z=0., w=1.))]
        r['tf_at_detection']['header']['stamp'] = copy.deepcopy(stamp)
        r['tf_at_detection']['transform']['translation']['x'] = 0.
        return alignment.observe(r, ns+20_000_000)
    def pose(t, x):
        return dict(x=x, y=2., yaw=0., stamp_ns=start+int(t*10**9))
    def observed(t, first, last, p):
        association = dict(frames={'frame_id': 'odom', 'child_frame_id': 'base_link'},
                           observation=alignment.in_map(last, p), comparison_only=True)
        return event(t, 'box_alignment', phase='observed', observation=last,
                     stability=perception.validate_pair(first, last), reference=p,
                     association=association)
    def action(t, kind, name, rid, gid, **fields):
        return event(t, 'action', kind=kind,
                     detail=dict(event=name, request_id=rid, **({'goal_id': gid} if gid else {}), **fields))
    def successful(t, kind, rid, gid):
        endpoint = '/mc/manipulation/action' if kind == 'motion' else '/vnav/task/command'
        action(t, kind, 'dispatched', rid, gid, endpoint=endpoint)
        action(t+.01, kind, 'accepted', rid, gid, accepted=True)
        state = dict(state=1101001, desc='SUCCEED') if kind == 'motion' else dict(state=1218003, desc='SUCCESS')
        action(t+.02, kind, 'result', rid, gid, status=4, result=dict(state=state))
        action(t+.03, kind, 'request_complete', rid, None, returncode=0)
    event(.01, 'ready', context=copy.deepcopy(context), points=copy.deepcopy(context['points']), map_name='utars_nav_map')
    event(.02, 'armed', remote_evidence='/tmp/fixture-source')
    first, second = pending(1., .82), pending(1.2, .82)
    for t, phase, p in ((1.02, 'first', first), (1.22, 'second', second)):
        event(t, 'box_alignment_capture', phase=phase, observation=p, received_ns=start+int(t*10**9))
    initial = observed(1.3, first, second, pose(1.25, 1.))
    delta = alignment.displacement(second)
    event(1.4, 'box_alignment', phase='in_flight', attempt=1, max_corrections=5,
          displacement_base_m=delta, observation=second, total_requested_m=delta['x'],
          spec=dict(reference=initial['reference'], target=alignment.target(initial['reference'], delta)))
    successful(1.5, 'navigation', '17', '56e4f051-26b0-414b-bab6-76c0b6b738f9')
    action(1.55, 'navigation', 'correction_guard', '17', '56e4f051-26b0-414b-bab6-76c0b6b738f9',
           phase='terminal', snapshot=dict(point='box_pickup', attempt=1, armed=True,
                                          settled=True, failure=None, velocity_violation=None, telemetry_failure=None))
    event(1.9, 'box_alignment', phase='arrival', attempt=1,
          measurements=[dict(distance_m=.001, yaw_error_deg=.1)]*2)
    first, second = pending(2., .77), pending(2.2, .77)
    for t, phase, p in ((2.02, 'first', first), (2.22, 'second', second)):
        event(t, 'box_alignment_capture', phase=phase, observation=p, received_ns=start+int(t*10**9))
    samples = [pose(2.25, 1.05), pose(2.3, 1.05)]
    event(2.31, 'pose_check', measurements=samples, publisher_count=2, arrival_verified=False)
    event(2.32, 'box_alignment_time_pair', current_reference=samples[-1], matches=[
        dict(image_stamp_ns=p['stamp_ns'], poses=[pose(t-.01, 1.05), pose(t+.01, 1.05)])
        for p, t in ((first, 2.), (second, 2.2))])
    final = observed(2.4, first, second, samples[-1])
    event(2.45, 'box_alignment_association', passed=True,
          measurement=alignment.validate_association(initial['association'], final['association']))
    event(2.5, 'box_alignment', phase='ready', attempts=1, total_requested_m=delta['x'],
          observation=second, inside_margin_m=.02)
    successful(2.6, 'motion', '3', '2b041539-9946-49d4-a882-fb764d11884b')
    event(3., 'stage_complete', stage='grasp', logical_assumption=False)
    event(3.1, 'checkpoint', checkpoint=copy.deepcopy(checkpoint))
    event(3.2, 'stage_complete', stage='verify_held', logical_assumption=True)
    event(3.3, 'session_finishing', reason='requested')
    return rows, checkpoint, context, profile


class PickupReferenceTests(unittest.TestCase):
    def test_measured_reference_and_compact_round_trip_preserve_nominal_point(self):
        rows, cp, context, profile = fixture_source()
        before = copy.deepcopy((rows, cp, context, profile))
        result = reference.derive_reference(rows, cp, context, profile)
        self.assertEqual(result['expected_pose'], dict(point_x=1.05, point_y=2., point_yaw=0.))
        self.assertEqual(context['points']['get1']['_expected_pose']['point_x'], 1.)
        self.assertFalse(result['box_state_measured'])
        self.assertTrue(result['fresh_arrival_tolerance_unchanged'])
        self.assertEqual(reference.validate_reference(result, cp, context, profile), result)
        self.assertEqual((rows, cp, context, profile), before)
        result['expected_pose']['point_x'] = 8.
        with self.assertRaises(ValueError): reference.validate_reference(result, cp, context, profile)

    def test_legacy_without_alignment_returns_none(self):
        rows, cp, context, profile = fixture_source()
        self.assertIsNone(reference.derive_reference([r for r in rows if r['event'] != 'box_alignment'], cp, context, profile))

    def test_source_must_be_clean_immediate_held_boundary(self):
        for field, value in [('box_state', 'unknown'), ('in_flight', 'grasp'), ('failure', {'stage': 'grasp', 'reason': 'stopped'})]:
            rows, cp, context, profile = fixture_source(); cp[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): reference.derive_reference(rows, cp, context, profile)

    def test_context_and_checkpoint_identity_are_bound(self):
        rows, cp, context, profile = fixture_source()
        result = reference.derive_reference(rows, cp, context, profile)
        for change in ('boot_id', 'containers', 'dependencies', 'points'):
            modified = copy.deepcopy(context); modified[change] = {}
            with self.subTest(change=change), self.assertRaises(ValueError): reference.validate_reference(result, cp, modified, profile)

    def test_missing_final_gates_and_malformed_arrival_samples_rejected(self):
        for name in ('pose_check', 'box_alignment_time_pair', 'box_alignment_association', 'session_finishing'):
            rows, cp, context, profile = fixture_source()
            with self.subTest(event=name), self.assertRaises(ValueError):
                reference.derive_reference([r for r in rows if r['event'] != name], cp, context, profile)
        rows, cp, context, profile = fixture_source()
        next(r for r in rows if r['event']=='pose_check')['measurements'][1]['stamp_ns'] = True
        with self.assertRaises(ValueError): reference.derive_reference(rows, cp, context, profile)

    def test_late_navigation_or_failure_before_finish_blocks_reference(self):
        for detail in (dict(event='error', reason='health fault'),
                       dict(event='dispatched', endpoint='/vnav/task/command', request_id='18', goal_id='33fdff0d-6056-473c-a931-cf5c97b0dbea')):
            rows, cp, context, profile = fixture_source()
            rows.insert(-1, dict(event='action', kind='navigation', time_ns=103_250_000_000, detail=detail))
            with self.subTest(detail=detail), self.assertRaises(ValueError): reference.derive_reference(rows, cp, context, profile)

    def test_cleanup_lease_error_after_requested_finish_does_not_invent_failed_grasp(self):
        rows, cp, context, profile = fixture_source()
        rows.extend([dict(event='action', kind='motion', time_ns=104_000_000_000,
                          detail=dict(event='error', reason='Lease missing, invalid or expired')),
                     dict(event='action', kind='motion', detail=dict(event='worker_closed', returncode=2))])
        self.assertIsNotNone(reference.derive_reference(rows, cp, context, profile))

    def test_proof_mutation_hash_uuid_and_terminal_contradictions_rejected(self):
        for mutate in (
                lambda r: r['proof_rows'].pop(),
                lambda r: r.update(proof_sha256='0'*64),
                lambda r: r.update(expected_pose=dict(point_x=1., point_y=2., point_yaw=0.))):
            rows, cp, context, profile = fixture_source(); result = reference.derive_reference(rows, cp, context, profile)
            mutate(result)
            with self.assertRaises(ValueError): reference.validate_reference(result, cp, context, profile)
        for field, value in [('status', 6), ('status', True), ('goal_id', 'ffffffff-ffff-4fff-8fff-ffffffffffff')]:
            rows, cp, context, profile = fixture_source()
            row = next(r for r in rows if r['event']=='action' and r['kind']=='motion' and r['detail']['event']=='result')
            row['detail'][field] = value
            with self.subTest(field=field,value=value), self.assertRaises(ValueError): reference.derive_reference(rows, cp, context, profile)

    def test_failed_unsettled_or_foreign_correction_guard_blocks_reference(self):
        for key, value in (('failure', 'no progress'), ('settled', False), ('attempt', True),
                           ('attempt', 2), ('point', 'get1'), ('telemetry_failure', 'stale')):
            rows, cp, context, profile = fixture_source()
            guard = next(r['detail']['snapshot'] for r in rows if r['event']=='action' and
                         r['detail']['event']=='correction_guard')
            guard[key] = value
            with self.subTest(key=key,value=value), self.assertRaises(ValueError): reference.derive_reference(rows, cp, context, profile)

    def test_no_dispatch_or_failed_terminal_can_hide_in_post_finish_cleanup(self):
        for detail in (dict(event='dispatched', request_id='4', goal_id='33fdff0d-6056-473c-a931-cf5c97b0dbea'),
                       dict(event='result', status=6), dict(event='error', reason='servo fault')):
            rows, cp, context, profile = fixture_source()
            rows.append(dict(event='action', kind='navigation', time_ns=104_000_000_000, detail=detail))
            with self.subTest(detail=detail), self.assertRaises(ValueError): reference.derive_reference(rows, cp, context, profile)

    def test_arbitrary_commanded_target_and_real_reference_substitution_rejected(self):
        for mutate in (lambda r: r['spec']['target'].update(point_x=9.),
                       lambda r: r.update(total_requested_m=.11),
                       lambda r: r.update(attempt=True)):
            rows, cp, context, profile = fixture_source()
            mutate(next(r for r in rows if r['event']=='box_alignment' and r.get('phase')=='in_flight'))
            with self.assertRaises(ValueError): reference.derive_reference(rows, cp, context, profile)
        rows, cp, context, profile = fixture_source()
        next(r for r in rows if r['event']=='box_alignment' and r.get('phase')=='observed' and r['time_ns']>102_000_000_000)['reference']['x'] = 8.
        with self.assertRaises(ValueError): reference.derive_reference(rows, cp, context, profile)


if __name__ == '__main__':
    unittest.main()
