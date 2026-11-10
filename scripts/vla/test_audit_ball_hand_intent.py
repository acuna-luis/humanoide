"""Pruebas offline de la auditoría de mano; nunca requiere ROS o hardware."""
import unittest

from audit_ball_hand_intent import analyze


def prediction(stamp, score, image='a' * 64):
    return {'event': 'prediction', 'image_source_ns': stamp, 'image_sha256': image,
            'prediction': [0.0] * 7 + [score]}


def annotation(stamp, phase, image='a' * 64):
    return {'image_source_ns': stamp, 'image_sha256': image, 'phase': phase}


class AuditHandTests(unittest.TestCase):
    def test_expected_phases_and_mismatches(self):
        phases = ['approach', 'grasp', 'lift', 'lower', 'release']
        scores = [0.9, 0.9, 0.1, 0.8, 0.1]
        result = analyze([prediction(i + 1, v) for i, v in enumerate(scores)],
                         [annotation(i + 1, v) for i, v in enumerate(phases)])
        self.assertEqual(result['mismatch_count'], 2)
        self.assertEqual(result['findings'][0]['finding'], 'candidate_premature_closure')
        self.assertEqual(result['findings'][2]['finding'], 'candidate_premature_opening')
        self.assertIs(result['physical_control_qualified'], False)
        self.assertEqual(result['physical_commands_generated'], 0)

    def test_unknown_is_not_assumed_safe_or_mismatch(self):
        result = analyze([prediction(1, 0.9), prediction(2, 0.1)], [])
        self.assertEqual(result['annotated_samples'], 0)
        self.assertEqual(result['unannotated_samples'], 2)
        self.assertEqual(result['audit_coverage'], 'unannotated')
        self.assertIsNone(result['mismatch_count'])
        self.assertIsNone(result['findings'][0]['phase_annotation'])
        self.assertIsNone(result['findings'][0]['finding'])
        self.assertFalse(result['physical_control_qualified'])

    def test_annotation_binds_timestamp_and_image_and_phase_order(self):
        predictions = [prediction(1, 0.0), prediction(2, 1.0)]
        for annotations in ([annotation(1, 'approach', 'b' * 64)],
                            [annotation(3, 'approach')],
                            [annotation(1, 'release'), annotation(2, 'lift')],
                            [annotation(1, 'unknown')],
                            [annotation(1, 'approach'), annotation(1, 'grasp')]):
            with self.subTest(annotations=annotations), self.assertRaises(ValueError):
                analyze(predictions, annotations)

    def test_bad_scores_duplicates_and_thresholds_rejected(self):
        for rows, threshold in (([prediction(1, float('nan'))], 0.5),
                                ([prediction(1, True)], 0.5),
                                ([prediction(1, 0), prediction(1, 0)], 0.5),
                                ([prediction(1, 0)], float('nan')),
                                ([prediction(1, 0)], 0), ([prediction(1, 0)], 1)):
            with self.subTest(rows=rows, threshold=threshold), self.assertRaises(ValueError):
                analyze(rows, [], threshold)

    def test_threshold_is_exploratory_and_can_change_diagnostic_only(self):
        row = [prediction(1, 0.55)]
        notes = [annotation(1, 'approach')]
        self.assertEqual(analyze(row, notes, 0.5)['mismatch_count'], 1)
        high = analyze(row, notes, 0.7)
        self.assertEqual(high['mismatch_count'], 0)
        self.assertFalse(high['physical_control_qualified'])


if __name__ == '__main__':
    unittest.main()
