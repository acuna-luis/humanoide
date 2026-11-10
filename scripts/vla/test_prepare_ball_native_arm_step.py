import io
import json
import math
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

import prepare_ball_native_arm_step as subject
from audit_ball_arm_proposals import MODEL_ORDER, MODEL_SHA256


def shadow_rows():
    return [
        {'event': 'model_ready', 'model_sha256': MODEL_SHA256,
         'physical_control_qualified': False, 'movement_commands': 0},
        {'event': 'prediction', 'index': 0, 'image_source_ns': 123,
         'image_sha256': 'a' * 64, 'physical_control_qualified': False,
         'prediction': [1.0, -1.0, 0.02, 0.0, 0.0, 0.0, 0.0, 0.9],
         'proposed_minus_observed_rad': [1.0, -1.0, 0.02, 0.0, 0.0, 0.0, 0.0]},
        {'event': 'done', 'samples': 1, 'physical_control_qualified': False},
        {'event': 'summary', 'predictions': 1, 'observations_sent': 1,
         'observations_dropped': 0, 'movement_commands': 0},
    ]


class NativeArmDraftTests(unittest.TestCase):
    def test_one_right_arm_step_clips_each_axis_and_keeps_order(self):
        result = subject.draft(shadow_rows(), 0, .05, 4.0)
        self.assertFalse(result['physical_control_qualified'])
        self.assertEqual(result['candidate_actions'], 1)
        self.assertEqual(result['physical_commands_sent'], 0)
        self.assertEqual(result['joint_order_hypothesis'], list(MODEL_ORDER))
        self.assertEqual([round(x['candidate_target_rad'], 5) for x in result['joints']],
                         [.05, -.05, .02, 0, 0, 0, 0])
        actions = ET.fromstring(result['candidate_xml']).findall('.//Action')
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0].attrib['ID'], 'MetaMove')
        self.assertEqual(actions[0].attrib['type'], 'arm')
        self.assertEqual(actions[0].attrib['location'], 'right')
        self.assertEqual([float(v) for v in actions[0].attrib['joint_angles'].split(';')],
                         [.05, -.05, .02, 0, 0, 0, 0])
        self.assertEqual(float(actions[0].attrib['duration']), 4.0)
        dynamic = result['candidate_dynamic_task']
        self.assertEqual(dynamic['task_name'], 'move_components_json')
        self.assertEqual(dynamic['yaml_args_hypothesis']['component_names'], ['right_arm'])
        self.assertEqual(dynamic['yaml_args_hypothesis']['goals'], [[.05, -.05, .02, 0, 0, 0, 0]])
        self.assertEqual(dynamic['yaml_args_hypothesis']['durations'], [4.0])
        self.assertEqual(dynamic['yaml_args_hypothesis']['mode'], 0)

    def test_invalid_model_provenance_and_nonfinite_values_are_rejected(self):
        for value in (math.nan, math.inf, True):
            rows = shadow_rows()
            rows[1]['prediction'][0] = value
            with self.assertRaises(ValueError):
                subject.draft(rows, 0, .05, 4)
        rows = shadow_rows()
        rows[0]['model_sha256'] = 'b' * 64
        with self.assertRaises(ValueError):
            subject.draft(rows, 0, .05, 4)

    def test_experimental_parameters_and_sample_must_be_valid(self):
        for index, step, duration in ((True, .05, 4), (1, .05, 4),
                                      (0, 0, 4), (0, .05, math.inf),
                                      (0, None, 4)):
            with self.assertRaises(ValueError):
                subject.draft(shadow_rows(), index, step, duration)

    def test_run_never_reads_input_or_connects(self):
        with patch.object(subject, 'read_rows', side_effect=AssertionError('must not read')):
            with patch('sys.stderr', new_callable=io.StringIO) as error:
                self.assertEqual(subject.main(['--run']), 2)
                self.assertIn('BLOCKED', error.getvalue())

    def test_live_stream_converts_real_lifecycle_without_a_hand_command(self):
        rows = shadow_rows()
        preview = subject.LivePreview(.05, 4.0)
        self.assertEqual(preview.accept(rows[0])['event'], 'native_preview_ready')
        step = preview.accept(rows[1])
        self.assertEqual(step['event'], 'native_step_preview')
        self.assertEqual(step['input_source'], 'live_shadow_relay')
        self.assertEqual(step['hand_scalar_uninterpreted'], .9)
        self.assertEqual(step['physical_commands_sent'], 0)
        self.assertEqual(len(ET.fromstring(step['candidate_xml']).findall('.//Action')), 1)
        self.assertIsNone(preview.accept(rows[2]))
        self.assertEqual(preview.accept(rows[3])['samples'], 1)
        preview.finish()

    def test_live_stream_rejects_stale_sequence_and_incomplete_summary(self):
        rows = shadow_rows()
        preview = subject.LivePreview(.05, 4.0)
        preview.accept(rows[0])
        preview.accept(rows[1])
        duplicate = dict(rows[1], index=1)
        with self.assertRaisesRegex(ValueError, 'sequence'):
            preview.accept(duplicate)
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            preview.finish()
        with self.assertRaises(ValueError):
            preview.accept(dict(rows[2], samples=2))

    def test_stream_cli_requires_complete_shadow_and_emits_no_command(self):
        data = ''.join(json.dumps(row) + '\n' for row in shadow_rows()).encode()
        source = io.TextIOWrapper(io.BytesIO(data), encoding='utf-8')
        with patch('sys.stdin', source), patch('sys.stdout', new_callable=io.StringIO) as output:
            self.assertEqual(subject.main(['--stream', '--max-step-rad', '.05', '--duration-s', '4']), 0)
            events = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual([row['event'] for row in events],
                         ['native_preview_ready', 'native_step_preview', 'native_preview_done'])
        self.assertTrue(all(row['physical_commands_sent'] == 0 for row in events))


if __name__ == '__main__':
    unittest.main()
