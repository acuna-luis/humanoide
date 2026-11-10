import io
import copy
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import yaml
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
    def paired_case(self):
        initial = subject.probe.BODY
        # Deliberately reorder telemetry; conversion must map by name.
        names = list(reversed(initial))
        state = {'names': names, 'positions': [initial[n] for n in names],
                 'velocities': [0.0]*20, 'received_monotonic_ns': 1000}
        target = [initial[n] for n in MODEL_ORDER]
        target[-1] += .01
        row = {'index':0, 'image_source_ns':123, 'paired_state20':state,
               'prediction_received_monotonic_ns':1050, 'prediction':target+[.5],
               'proposed_minus_observed_rad':[target[i]-initial[n] for i,n in enumerate(MODEL_ORDER)]}
        urdf = '<robot>' + ''.join('<joint name="%s" type="revolute"><limit lower="-3" upper="3" velocity="1"/></joint>' % n
                                   for n in MODEL_ORDER) + '</robot>'
        config = {'transmissions':{n:{'joint':{'name':n, 'limit':{'lower':-3.0,'upper':3.0}}}
                                   for n in initial}}
        options = {'urdf_text':urdf, 'transmissions_text':yaml.safe_dump(config),
                   'max_state_age_ns':100, 'max_prediction_age_ns':100,
                   'min_sps_margin_rad':0.0, 'now_ns':1100}
        return row, config, options

    def test_paired_live_nominal_check_uses_names_and_never_authorizes(self):
        row, _, options = self.paired_case()
        result = subject.checked_live_step(row, .02, 4, **options)
        self.assertEqual(result['joint_order_hypothesis'], list(MODEL_ORDER))
        self.assertEqual(result['nominal_endpoint_check']['state_age_pc_ns'], 100)
        self.assertEqual(result['nominal_endpoint_check']['prediction_age_pc_ns'], 50)
        self.assertIs(result['physical_control_qualified'], False)
        self.assertEqual(result['physical_commands_sent'], 0)
        self.assertAlmostEqual(result['joints'][-1]['candidate_target_rad'], row['prediction'][6])

    def test_paired_live_rejects_stale_wrong_axes_nonfinite_and_excessive(self):
        row, _, options = self.paired_case()
        bad = copy.deepcopy(row); bad['paired_state20']['received_monotonic_ns'] = 999
        with self.assertRaisesRegex(ValueError, 'stale'): subject.checked_live_step(bad, .02, 4, **options)
        bad = copy.deepcopy(row); bad['paired_state20']['names'][0] = 'wrong_axis'
        with self.assertRaises(ValueError): subject.checked_live_step(bad, .02, 4, **options)
        bad = copy.deepcopy(row); bad['paired_state20']['velocities'] = None
        with self.assertRaises(ValueError): subject.checked_live_step(bad, .02, 4, **options)
        bad = copy.deepcopy(row); bad['prediction'][0] = float('nan')
        with self.assertRaises(ValueError): subject.checked_live_step(bad, .02, 4, **options)
        bad = copy.deepcopy(row); bad['prediction'][0] += .1; bad['proposed_minus_observed_rad'][0] += .1
        with self.assertRaisesRegex(ValueError, 'exceeds_supplied_limit'): subject.checked_live_step(bad, .02, 4, **options)
        bad = copy.deepcopy(row); bad['proposed_minus_observed_rad'][0] += .01
        with self.assertRaisesRegex(ValueError, 'observation_mismatch'): subject.checked_live_step(bad, .02, 4, **options)
        with patch.object(subject.probe, 'ARM', tuple(reversed(subject.probe.ARM))):
            with self.assertRaisesRegex(ValueError, 'model_native_arm_order_mismatch'):
                subject.checked_live_step(row, .02, 4, **options)

    def test_paired_live_applies_supplied_sps_margin_to_other_body_axes(self):
        row, config, options = self.paired_case()
        name = 'L_elbow_yaw_joint'
        q = subject.probe.BODY[name]
        config['transmissions'][name]['joint']['limit']['upper'] = q + .001
        options['transmissions_text'] = yaml.safe_dump(config)
        options['min_sps_margin_rad'] = .002
        with self.assertRaisesRegex(ValueError, 'sps_endpoint_margin_below_supplied_threshold:' + name):
            subject.checked_live_step(row, .02, 4, **options)

    def test_stream_nominal_mode_uses_paired_telemetry(self):
        row, _, options = self.paired_case()
        options.pop('now_ns')
        prediction = dict(shadow_rows()[1], **row)
        preview = subject.LivePreview(.02, 4, nominal=options)
        preview.accept(shadow_rows()[0])
        with patch.object(subject.time, 'monotonic_ns', return_value=1100):
            result = preview.accept(prediction)
        self.assertEqual(result['input_source'], 'paired_live_shadow_nominal_check')
        self.assertEqual(result['event'], 'native_step_preview')
        self.assertIs(result['physical_control_qualified'], False)

    def test_model_wrist_candidate_reuses_probe_and_records_adaptation(self):
        row, _, options = self.paired_case()
        row.update({'event':'prediction', 'image_sha256':'a'*64,
                    'physical_control_qualified':False})
        # Model asks for substantially more wrist movement and another axis;
        # the existing fixed probe executes neither of those full targets.
        row['prediction'][0] += .2
        row['proposed_minus_observed_rad'][0] += .2
        row['prediction'][6] += .1
        row['proposed_minus_observed_rad'][6] += .1
        options['verified_model_sha256'] = MODEL_SHA256
        result = subject.model_wrist_candidate(row, **options)
        manifest = result['manifest']
        initial = manifest['input']['reference_20d']
        self.assertEqual(result['model_action_original'], row['prediction'])
        self.assertEqual(result['model_arm_deltas_rad'], row['proposed_minus_observed_rad'])
        self.assertEqual(manifest['candidate']['moved_axis'], subject.probe.ARM_AXIS)
        for i, name in enumerate(MODEL_ORDER[:-1]):
            self.assertEqual(result['applied_arm_target_rad'][i], initial[name])
        self.assertAlmostEqual(result['applied_arm_target_rad'][-1]-initial[MODEL_ORDER[-1]], .01)
        self.assertEqual(subject.probe.validate(manifest, options['urdf_text'],
                                               options['transmissions_text'])['movement_commands'], 0)
        self.assertIs(result['physical_control_qualified'], False)
        self.assertEqual(result['physical_commands_sent'], 0)

    def test_model_wrist_candidate_rejects_negative_small_stale_and_wrong_provenance(self):
        row, _, options = self.paired_case()
        row.update({'event':'prediction', 'image_sha256':'a'*64,
                    'physical_control_qualified':False})
        options['verified_model_sha256'] = MODEL_SHA256
        initial = row['paired_state20']['positions'][row['paired_state20']['names'].index(MODEL_ORDER[-1])]
        for delta in (-.5, 0, .009):
            bad = copy.deepcopy(row)
            bad['prediction'][6] = initial + delta
            bad['proposed_minus_observed_rad'][6] = delta
            with self.assertRaisesRegex(ValueError, 'not_compatible'):
                subject.model_wrist_candidate(bad, **options)
        bad = copy.deepcopy(row); bad['paired_state20']['received_monotonic_ns'] = 999
        with self.assertRaisesRegex(ValueError, 'stale'):
            subject.model_wrist_candidate(bad, **options)
        bad = copy.deepcopy(row); bad['proposed_minus_observed_rad'][1] += .1
        with self.assertRaisesRegex(ValueError, 'observation_mismatch'):
            subject.model_wrist_candidate(bad, **options)
        bad = copy.deepcopy(row); bad['paired_state20']['velocities'] = None
        with self.assertRaises(ValueError):
            subject.model_wrist_candidate(bad, **options)
        bad = copy.deepcopy(row); bad['prediction'][0] = float('nan')
        with self.assertRaises(ValueError):
            subject.model_wrist_candidate(bad, **options)
        options['verified_model_sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'checkpoint_or_prediction'):
            subject.model_wrist_candidate(row, **options)

    def test_model_wrist_stream_accepts_one_prediction_only(self):
        row, _, options = self.paired_case()
        row['prediction'][6] += .1
        row['proposed_minus_observed_rad'][6] += .1
        options.pop('now_ns')
        prediction = dict(shadow_rows()[1], **row)
        preview = subject.LivePreview(.01, 4, wrist_candidate=options)
        preview.accept(shadow_rows()[0])
        with patch.object(subject.time, 'monotonic_ns', return_value=1100):
            result = preview.accept(prediction)
        self.assertEqual(result['event'], 'model_wrist_candidate')
        with self.assertRaisesRegex(ValueError, 'one_prediction'):
            preview.accept(dict(prediction, index=1, image_source_ns=124))
        with self.assertRaisesRegex(ValueError, 'fixed_probe'):
            subject.LivePreview(.02, 4, wrist_candidate=options)

    def test_wrist_candidate_stream_cli_requires_one_model_prediction(self):
        row, _, options = self.paired_case()
        row['prediction'][6] += .1
        row['proposed_minus_observed_rad'][6] += .1
        prediction = dict(shadow_rows()[1], **row)
        data = ''.join(json.dumps(item)+'\n' for item in
                       [shadow_rows()[0], prediction, shadow_rows()[2], shadow_rows()[3]]).encode()
        source = io.TextIOWrapper(io.BytesIO(data), encoding='utf-8')
        with tempfile.TemporaryDirectory() as tmp:
            urdf = Path(tmp)/'robot.urdf'; urdf.write_text(options['urdf_text'])
            sps = Path(tmp)/'transmissions.yaml'; sps.write_text(options['transmissions_text'])
            artifact = Path(tmp)/'wrist-artifact'
            args = ['--stream', '--wrist-candidate', '--wrist-output', str(artifact),
                    '--max-step-rad', '.01', '--duration-s', '4',
                    '--urdf', str(urdf), '--transmissions', str(sps), '--max-state-age-ns', '100',
                    '--max-prediction-age-ns', '100', '--min-sps-margin-rad', '0']
            with patch('sys.stdin', source), patch('sys.stdout', new_callable=io.StringIO) as output, \
                 patch.object(subject.time, 'monotonic_ns', return_value=1100):
                self.assertEqual(subject.main(args), 0)
            rows = [json.loads(line) for line in output.getvalue().splitlines()]
            self.assertEqual([r['event'] for r in rows],
                             ['native_preview_ready','native_preview_done','model_wrist_candidate',
                              'model_wrist_artifact_saved'])
            self.assertEqual(rows[2]['model_action_original'], prediction['prediction'])
            self.assertEqual(rows[2]['physical_commands_sent'], 0)
            self.assertEqual(json.loads((artifact/'manifest.json').read_bytes()), rows[2]['manifest'])
            decision = json.loads((artifact/'decision.json').read_bytes())
            self.assertEqual(decision['image_sha256'], prediction['image_sha256'])
            self.assertEqual(decision['model_action_original'], prediction['prediction'])
            self.assertEqual(decision['model_arm_deltas_rad'], prediction['proposed_minus_observed_rad'])
            receipt_raw = (artifact/'receipt.json').read_bytes()
            self.assertEqual(hashlib.sha256(receipt_raw).hexdigest(), rows[-1]['receipt_sha256'])
            receipt = json.loads(receipt_raw)
            self.assertFalse(receipt['image_bytes_retained'])
            for name, digest in receipt['sha256'].items():
                self.assertEqual(hashlib.sha256((artifact/name).read_bytes()).hexdigest(), digest)
            with patch('sys.stdout', new_callable=io.StringIO) as verified:
                self.assertEqual(subject.main(['--verify-wrist-artifact', str(artifact),
                                               '--receipt-sha256', rows[-1]['receipt_sha256']]), 0)
            self.assertEqual(json.loads(verified.getvalue())['status'], 'MODEL_WRIST_ARTIFACT_VERIFIED')

    def test_incomplete_or_duplicate_wrist_stream_never_creates_artifact(self):
        row, _, options = self.paired_case()
        row['prediction'][6] += .1
        row['proposed_minus_observed_rad'][6] += .1
        prediction = dict(shadow_rows()[1], **row)
        for tail in ([], [dict(prediction, index=1, image_source_ns=124)]):
            data = ''.join(json.dumps(item)+'\n' for item in
                           [shadow_rows()[0], prediction]+tail).encode()
            source = io.TextIOWrapper(io.BytesIO(data), encoding='utf-8')
            with tempfile.TemporaryDirectory() as tmp:
                urdf = Path(tmp)/'robot.urdf'; urdf.write_text(options['urdf_text'])
                sps = Path(tmp)/'transmissions.yaml'; sps.write_text(options['transmissions_text'])
                artifact = Path(tmp)/'wrist-artifact'
                args = ['--stream', '--wrist-candidate', '--wrist-output', str(artifact),
                        '--max-step-rad', '.01', '--duration-s', '4', '--urdf', str(urdf),
                        '--transmissions', str(sps), '--max-state-age-ns', '100',
                        '--max-prediction-age-ns', '100', '--min-sps-margin-rad', '0']
                with patch('sys.stdin', source), patch('sys.stdout', new_callable=io.StringIO) as output, \
                     patch('sys.stderr', new_callable=io.StringIO), \
                     patch.object(subject.time, 'monotonic_ns', return_value=1100):
                    self.assertEqual(subject.main(args), 1)
                self.assertFalse(artifact.exists())
                self.assertNotIn('model_wrist_candidate', output.getvalue())

    def test_wrist_artifact_never_overwrites_existing_path(self):
        row, _, options = self.paired_case()
        row.update({'event':'prediction', 'image_sha256':'a'*64,
                    'physical_control_qualified':False})
        row['prediction'][6] += .1
        row['proposed_minus_observed_rad'][6] += .1
        options['verified_model_sha256'] = MODEL_SHA256
        result = subject.model_wrist_candidate(row, **options)
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp)/'already-here'; destination.mkdir()
            (destination/'keep').write_text('user data')
            with self.assertRaises(FileExistsError):
                subject.save_model_wrist_artifact(destination, result, options['urdf_text'],
                                                  options['transmissions_text'])
            self.assertEqual((destination/'keep').read_text(), 'user data')
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), ['already-here'])

    def test_wrist_artifact_verification_rejects_tampering_and_incoherent_action(self):
        row, _, options = self.paired_case()
        row.update({'event':'prediction', 'image_sha256':'a'*64,
                    'physical_control_qualified':False})
        row['prediction'][6] += .1
        row['proposed_minus_observed_rad'][6] += .1
        options['verified_model_sha256'] = MODEL_SHA256
        result = subject.model_wrist_candidate(row, **options)
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp)/'wrist-artifact'
            saved = subject.save_model_wrist_artifact(destination, result, options['urdf_text'],
                                                      options['transmissions_text'])
            checked = subject.verify_model_wrist_artifact(destination, saved['receipt_sha256'])
            self.assertEqual(checked['status'], 'MODEL_WRIST_ARTIFACT_VERIFIED')
            self.assertFalse(checked['physical_control_qualified'])
            decision_file = destination/'decision.json'
            decision = json.loads(decision_file.read_bytes())
            decision['applied_arm_target_rad'][0] += .1
            altered = (json.dumps(decision, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()
            decision_file.write_bytes(altered)
            with self.assertRaisesRegex(ValueError, 'file_changed'):
                subject.verify_model_wrist_artifact(destination, saved['receipt_sha256'])
            # Even a newly computed receipt cannot make a model/manifest
            # mismatch pass the arithmetic check.
            receipt_file = destination/'receipt.json'
            receipt = json.loads(receipt_file.read_bytes())
            receipt['sha256']['decision.json'] = hashlib.sha256(altered).hexdigest()
            receipt_raw = (json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()
            receipt_file.write_bytes(receipt_raw)
            with self.assertRaisesRegex(ValueError, 'decision_mismatch'):
                subject.verify_model_wrist_artifact(destination, hashlib.sha256(receipt_raw).hexdigest())

    def test_cli_invalid_yaml_reports_error_without_traceback(self):
        row, _, options = self.paired_case()
        prediction = dict(shadow_rows()[1], **row)
        data = ''.join(json.dumps(item)+'\n' for item in [shadow_rows()[0], prediction]).encode()
        source = io.TextIOWrapper(io.BytesIO(data), encoding='utf-8')
        with tempfile.TemporaryDirectory() as tmp:
            urdf = Path(tmp)/'robot.urdf'; urdf.write_text(options['urdf_text'])
            sps = Path(tmp)/'transmissions.yaml'; sps.write_text('transmissions: [unterminated')
            args = ['--stream', '--max-step-rad', '.02', '--duration-s', '4', '--urdf', str(urdf),
                    '--transmissions', str(sps), '--max-state-age-ns', '100',
                    '--max-prediction-age-ns', '100', '--min-sps-margin-rad', '0']
            with patch('sys.stdin', source), patch('sys.stdout', new_callable=io.StringIO), \
                 patch('sys.stderr', new_callable=io.StringIO) as error, \
                 patch.object(subject.time, 'monotonic_ns', return_value=1100):
                self.assertEqual(subject.main(args), 1)
            self.assertIn('DRAFT_ERROR:', error.getvalue())
            self.assertNotIn('Traceback', error.getvalue())

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
