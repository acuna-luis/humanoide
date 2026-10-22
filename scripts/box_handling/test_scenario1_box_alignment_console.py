"""Readable adjustment counts and measurements; no robot or action clients."""
import unittest

from scripts.box_handling.scenario1_console import ConsoleReporter


class BoxAlignmentConsoleTests(unittest.TestCase):
    def test_reports_chassis_attempt_and_configured_limit_in_millimetres(self):
        lines = ConsoleReporter().render(dict(event='box_alignment', phase='in_flight',
            attempt=2, max_corrections=5, displacement_base_m=dict(x=.0207, y=0)))
        text = '\n'.join(lines)
        self.assertIn('chasis 2/5', text)
        self.assertIn('X: 20,7 mm', text)
        self.assertNotIn('Y:', text)

    def test_observation_reports_base_frame_without_claiming_floor_height(self):
        lines = ConsoleReporter().render(dict(event='box_alignment', phase='observed',
            observation=dict(selection=dict(selected_pose=dict(position=dict(x=.7907, y=-.0364, z=.9019))))))
        self.assertIn('X=79,070 cm', lines[0])
        self.assertIn('Z no es altura al suelo', lines[0])

    def test_zero_adjustments_still_explain_single_grasp_and_new_sps_validation(self):
        lines = ConsoleReporter().render(dict(event='box_alignment', phase='ready', attempts=0))
        self.assertIn('realizados: 0', lines[0])
        self.assertIn('único agarre', lines[0])
        self.assertIn('nueva validación SPS', lines[0])

    def test_limits_and_incomplete_observations_do_not_report_a_successful_grasp(self):
        console = ConsoleReporter()
        self.assertEqual(console.render(dict(event='box_alignment', phase='observed', observation={})), [])
        text = '\n'.join(console.render(dict(event='box_alignment', phase='limit', reason='attempts')))
        self.assertIn('attempts', text)
        self.assertIn('No se inicia el agarre', text)


if __name__ == '__main__':
    unittest.main()
