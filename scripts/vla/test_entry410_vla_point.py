import math
import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace

from prepare_entry410_vla_point import select_point
from runtime.entry410_vla_point_remote import check_tick, check_tracking, check_wheels, check_handoff_reply, check_sdk_state
from runtime.cruzr_s2_vla_sdk_transport import plan_minimum_jerk
from run_entry410_vla_point import new_evidence_dir, check_controller_inventory


class PointTrialTests(unittest.TestCase):
    def test_controller_inventory_rejects_conflicting_owner_or_wrong_resources(self):
        def controller(name, state, joints):
            return dict(name=name, state=state, claimed_resources=[dict(
                hardware_interface='hardware::MultimodeJointInterface', resources=joints)])
        rows = [controller('manipulation_controller', 'running', ['arm']),
                controller('vla_sdk_controller', 'initialized', ['arm']),
                controller('sdk_controller', 'initialized', ['arm', 'wheel']),
                controller('chassis_controller', 'running', ['wheel'])]
        def validate():
            return check_controller_inventory('response: x.Response(controller='+repr(rows)+')\n', ['arm'])
        validate()
        rows[1]['state'] = 'running'
        with self.assertRaises(ValueError): validate()
        rows[1]['state'] = 'initialized'
        rows[1]['claimed_resources'][0]['resources'].append('wheel')
        with self.assertRaises(ValueError): validate()
        rows[1]['claimed_resources'][0]['resources'].pop()
        rows.append(controller('teleop', 'running', ['arm']))
        with self.assertRaises(ValueError): validate()

    def test_handoff_failure_and_missing_or_stale_feedback_reject(self):
        for reply in (None, SimpleNamespace(success=False, message='busy')):
            with self.assertRaises(RuntimeError): check_handoff_reply(reply)
        check_handoff_reply(SimpleNamespace(success=True, message='switched'))
        valid = dict(received=2., values={'arm': (0., 0.)}, error=None)
        check_sdk_state(valid, ['arm'], 2.02, 1.9)
        for changed in ({}, dict(valid, received=1.), dict(valid, error='invalid'),
                        dict(valid, values={'wheel': (0., 0.)})):
            with self.assertRaises(RuntimeError): check_sdk_state(changed, ['arm'], 2.02, 1.9)

    def test_wheel_quantization_is_bounded_by_position_and_speed(self):
        check_wheels({'wheel': [.001533981, .007330383]}, {'wheel': 0.})
        for value in ([.00201, 0.], [0., .01001], [math.nan, 0.]):
            with self.assertRaises(RuntimeError):
                check_wheels({'wheel': value}, {'wheel': 0.})

    def test_repeated_directory_preserves_first_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = new_evidence_dir(Path(tmp)/'trial')
            (first/'result.json').write_text('original')
            second = new_evidence_dir(first)
            self.assertNotEqual(first, second)
            self.assertEqual(second.parent, first.parent)
            self.assertEqual((first/'result.json').read_text(), 'original')
            self.assertEqual(list(second.iterdir()), [])

    def row(self, value, index=0, accepted=True):
        return dict(accepted=accepted, reasons=[], chunk_id=index,
                    metrics=dict(first_point_positions={'arm': value, 'body': 9.}))

    def test_selects_smallest_accepted_without_clipping_and_locks_body(self):
        delta, chunk, target = select_point([self.row(.12), self.row(.09, 1),
            self.row(.02, 2, False)], [0., .3], ['arm', 'body'], ['arm'])
        self.assertEqual((delta, chunk, target), (.09, 1, [.09, .3]))

    def test_excessive_or_missing_point_rejects(self):
        for rows in ([], [self.row(.10001)]):
            with self.assertRaises(ValueError):
                select_point(rows, [0., 0.], ['arm', 'body'], ['arm'])

    def test_nonfinite_rejects(self):
        with self.assertRaises(ValueError):
            select_point([self.row(math.nan)], [0., 0.], ['arm', 'body'], ['arm'])

    def test_runtime_rejects_late_dispatch_instead_of_catching_up(self):
        with self.assertRaises(RuntimeError):
            check_tick(1.041, 1.01, 1.)
        with self.assertRaises(RuntimeError):
            check_tick(1.05, 1.05, 1.)
        check_tick(1.012, 1.01, 1.)

    def test_tracking_rejects_position_speed_and_nonfinite(self):
        for pair in ([.006, 0.], [0., .051], [math.nan, 0.]):
            with self.assertRaises(RuntimeError):
                check_tracking({'a': pair}, [0.], ['a'])
        check_tracking({'a': [.001, .01]}, [0.], ['a'])

    def test_bridge_has_rest_endpoints_and_bounded_derivatives(self):
        limits = dict(maximum_target_delta_rad=[.1]*14, maximum_velocity_rad_s=[.05]*14,
            maximum_acceleration_rad_s2=[.1]*14, minimum_transition_duration_seconds=4.,
            maximum_transition_duration_seconds=4., sample_period_seconds=.01,
            analytic_peak_velocity_factor=1.875, analytic_peak_acceleration_factor=5.773502691896258)
        points = plan_minimum_jerk([0.]*14, [.025, -.025]+[0.]*12, limits)
        self.assertEqual(len(points), 401)
        self.assertEqual(points[0]['positions'], [0.]*14)
        self.assertEqual(points[-1]['positions'], [.025, -.025]+[0.]*12)
        for endpoint in (points[0], points[-1]):
            self.assertEqual(endpoint['velocities'], [0.]*14)
        self.assertLessEqual(max(abs(v) for p in points for v in p['velocities']), .05)
        self.assertLessEqual(max(abs(v) for p in points for v in p['accelerations']), .1)


if __name__ == '__main__':
    unittest.main()
