"""Recorded pickup reference integration; fake telemetry, no movement or SSH."""
import copy
import io
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import resume_pickup_reference as pickup
from scripts.box_handling import scenario1_cli as cli
from scripts.box_handling import scenario1_contract as contract
from scripts.box_handling import scenario1_resume as resume
from scripts.box_handling import scenario1_runtime as runtime
from scripts.box_handling.test_resume_pickup_reference import fixture_source
from scripts.box_handling.test_scenario1_checks import nav_pose


class PickupResumeRuntimeTests(unittest.TestCase):
    def payload(self, *, include=True):
        rows, source, context, profile = fixture_source()
        options = dict(stage=None, box_state='held', recovery_confirmed=False,
            stop_after='navigate_put1', policy=source['policy'],
            execution_profile=contract.execution_profile(source))
        plan = resume.plan_resume(source, profile, **options)
        payload = dict(mode='check', profile=profile, policy=source['policy'],
            execution_profile=contract.execution_profile(source), checkpoint=plan['checkpoint'],
            resume_source_checkpoint=source, resume_context=context, resume_options=options,
            resume_plan=plan, resume_worker='# fake passive read-only acquisition')
        reference = pickup.derive_reference(rows, source, context, profile)
        self.assertIsNotNone(reference)
        if include:
            payload['resume_pickup_reference'] = reference
        return payload, reference

    def machine(self, directory, *, include=True):
        payload, reference = self.payload(include=include)
        events = []
        machine = runtime.Runtime(payload, lambda event, **value: events.append(dict(event=event, **value)))
        machine.session = Path(directory)
        machine.points = copy.deepcopy(payload['resume_context']['points'])
        machine.map_state = Mock(return_value=('utars_nav_map', 'FSM_WAITNAVIGATE'))
        machine.create_session = Mock()
        machine.discover = Mock()
        machine.hashes = Mock()
        machine.health = Mock()
        machine.map_points = Mock(return_value=machine.points)
        machine.native = Mock(return_value=json.dumps(dict(event='resume_base_check', stationary=True, publishers=1)))
        machine.action = Mock(side_effect=AssertionError('No action permitted during held entry checks'))
        machine.verify_sensors = Mock(side_effect=AssertionError('No fabricated sensor qualification'))
        machine.events = events
        self.set_pose(machine, reference['expected_pose'])
        return machine, reference

    def set_pose(self, machine, target, *, extra_x=0.):
        machine.health_request = Mock(return_value=dict(publisher_count=2, poses=[
            nav_pose(x=target['point_x']+extra_x, y=target['point_y'], yaw=target['point_yaw'], ns=ns)
            for ns in (510_000_000, 520_000_000)]))

    def check(self, machine):
        with patch.object(runtime.time, 'time', side_effect=[100.5]+[100.6]*30):
            machine.check_resume_entry(refresh_health=True)

    def test_aligned_held_reference_passes_existing_twenty_mm_gate_without_changing_map_points(self):
        with tempfile.TemporaryDirectory() as directory:
            machine, reference = self.machine(directory)
            nominal = machine.points['get1']['_expected_pose']
            self.assertGreater(math.hypot(reference['expected_pose']['point_x']-nominal['point_x'],
                                          reference['expected_pose']['point_y']-nominal['point_y']), .02)
            snapshot = copy.deepcopy(machine.points)
            self.check(machine)
            self.assertTrue(machine.resume_validated)
            self.assertEqual(machine.points, snapshot)
            machine.action.assert_not_called()
            machine.verify_sensors.assert_not_called()
            measured = next(row for row in machine.events if row['event'] == 'resume_arrival')
            self.assertEqual(measured['reference_source'], 'recorded_box_alignment')
            self.assertEqual(measured['expected_pose'], reference['expected_pose'])
            self.assertTrue(all(row['distance_tolerance_m'] == .02 for row in measured['measurements']))

    def test_no_reference_preserves_nominal_gate_and_rejects_the_aligned_pose(self):
        with tempfile.TemporaryDirectory() as directory:
            machine, _ = self.machine(directory, include=False)
            with self.assertRaisesRegex(RuntimeError, 'RESUME_WAYPOINT_NOT_CONFIRMED'):
                self.check(machine)
            self.assertFalse(machine.resume_validated)
            machine.action.assert_not_called()
            self.set_pose(machine, machine.points['get1']['_expected_pose'])
            self.check(machine)
            self.assertTrue(machine.resume_validated)
            machine.action.assert_not_called()

    def test_recorded_reference_does_not_allow_nominal_fallback_or_larger_tolerance(self):
        with tempfile.TemporaryDirectory() as directory:
            for mode in ('outside_twenty_mm', 'nominal_fallback'):
                machine, reference = self.machine(directory)
                if mode == 'outside_twenty_mm':
                    self.set_pose(machine, reference['expected_pose'], extra_x=.020001)
                else:
                    self.set_pose(machine, machine.points['get1']['_expected_pose'])
                with self.subTest(mode=mode), self.assertRaisesRegex(RuntimeError, 'RESUME_WAYPOINT_NOT_CONFIRMED'):
                    self.check(machine)
                self.assertFalse(machine.resume_validated)
                machine.action.assert_not_called()

    def test_tampered_pose_or_context_is_rejected_before_any_runtime_action(self):
        for field in ('pose', 'context'):
            payload, _ = self.payload()
            if field == 'pose':
                payload['resume_pickup_reference']['expected_pose']['point_x'] += .001
            else:
                payload['resume_context']['boot_id'] = 'another-boot'
            with self.subTest(field=field), self.assertRaises(ValueError):
                runtime.Runtime(payload)

    def test_reference_is_not_admitted_for_another_resume_stage(self):
        payload, _ = self.payload()
        options = dict(payload['resume_options'], stage='navigate_put1', recovery_confirmed=True)
        plan = resume.plan_resume(payload['resume_source_checkpoint'], payload['profile'], **options)
        payload.update(resume_options=options, resume_plan=plan, checkpoint=plan['checkpoint'])
        with self.assertRaisesRegex(ValueError, 'RESUME_PICKUP_REFERENCE_STAGE_MISMATCH'):
            runtime.Runtime(payload)

    def test_reference_is_revalidated_during_fresh_entry_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            machine, _ = self.machine(directory)
            machine.resume_pickup_reference['expected_pose']['point_x'] += .001
            machine.resume_validated = True
            with self.assertRaisesRegex(ValueError, 'RESUME_PICKUP_REFERENCE_INVALID'):
                self.check(machine)
            self.assertFalse(machine.resume_validated)
            machine.action.assert_not_called()

    def test_not_ready_localization_or_ambiguous_odometry_still_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            for mode in ('localization', 'odometry'):
                machine, _ = self.machine(directory)
                if mode == 'localization':
                    machine.map_state.return_value = ('utars_nav_map', 'FSM_WAITRELOCATE')
                else:
                    machine.native.return_value = json.dumps(dict(event='resume_base_check', stationary=True, publishers=2))
                with self.subTest(mode=mode), self.assertRaises(RuntimeError):
                    self.check(machine)
                self.assertFalse(machine.resume_validated)
                machine.action.assert_not_called()


class PickupResumeCliTests(unittest.TestCase):
    def write_source(self, root):
        rows, checkpoint, context, profile = fixture_source()
        folder = root/'source'
        folder.mkdir()
        source = folder/'checkpoint.json'
        source.write_text(json.dumps(checkpoint, indent=2))
        (folder/'context.json').write_text(json.dumps(context, indent=2))
        (folder/'events.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
        return source, {p.name: p.read_bytes() for p in folder.iterdir()}, profile

    def args(self, source, mode, *extra):
        return ['--table-height-cm', '74', '--box-alignment-attempts', '5',
                '--resume', str(source), '--stop-after', 'put1', '--box-state', 'held', mode, *extra]

    def assert_source_untouched(self, source, before):
        self.assertEqual({p.name: p.read_bytes() for p in source.parent.iterdir()}, before)
        self.assertFalse(source.with_name(source.name+'.consumed.json').exists())

    def test_aligned_plan_derives_reference_offline_without_consuming_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, before, _ = self.write_source(root)
            with patch.object(cli, 'Connection', side_effect=AssertionError('No network')), \
                    patch.object(cli, 'claim_resume', side_effect=AssertionError('No claim')), \
                    patch.object(cli.subprocess, 'run', side_effect=AssertionError('No commands')), \
                    patch.object(cli.subprocess, 'Popen', side_effect=AssertionError('No processes')), \
                    patch('sys.stdout', io.StringIO()) as output:
                self.assertEqual(cli.main(self.args(source, '--plan'), policy='assume',
                                          execution_profile='optimistic_v1'), 0)
            report = json.loads(output.getvalue()[output.getvalue().index('{'):])
            self.assertEqual(report['stages'], ['retreat', 'navigate_put1'])
            self.assertEqual(report['resume']['stage'], 'retreat')
            self.assertEqual(report['resume_pickup_reference']['expected_pose'],
                             dict(point_x=1.05, point_y=2., point_yaw=0.))
            self.assertFalse(report['resume_pickup_reference']['box_state_measured'])
            self.assert_source_untouched(source, before)
            self.assertEqual(sorted(path.name for path in root.iterdir()), ['source'])

    def test_aligned_check_carries_validated_reference_but_never_claims_or_sends(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, before, profile = self.write_source(root)
            evidence = root/'check-evidence'
            payloads, instances = [], []

            class Connection:
                def __init__(self, payload, wifi, location, *, console=None):
                    payloads.append(copy.deepcopy(payload))
                    instances.append(self)
                    self.process = Mock()
                    self.process.wait.return_value = 0
                    self.close = Mock()
                    self.send = Mock(side_effect=AssertionError('No supervisor commands'))

                def wait(self, event):
                    if event != 'ready':
                        raise AssertionError('A passive check only waits for readiness')
                    return dict(context=copy.deepcopy(payloads[-1]['resume_context']),
                                map_name='utars_nav_map', nav_state='FSM_WAITNAVIGATE')

            def make_payload(mode, selected, checkpoint):
                return dict(mode=mode, profile=selected, checkpoint=checkpoint, modules=[],
                    action_client='', perception_guard='', sensor_worker='', health_worker='', resume_worker='')

            with patch.object(cli, 'Connection', Connection), \
                    patch.object(cli, 'make_payload', side_effect=make_payload), \
                    patch.object(cli, 'claim_resume', side_effect=AssertionError('No claim')), \
                    patch.object(cli.subprocess, 'run', side_effect=AssertionError('No commands')), \
                    patch.object(cli.subprocess, 'Popen', side_effect=AssertionError('No processes')), \
                    patch.object(cli, 'open', side_effect=lambda name, mode: open(root/Path(name).name, mode), create=True), \
                    patch('builtins.input', side_effect=AssertionError('No prompts')), \
                    patch('sys.stdout', io.StringIO()) as output:
                self.assertEqual(cli.main(self.args(source, '--check', '--evidence-dir', str(evidence)),
                    policy='assume', execution_profile='optimistic_v1'), 0)
            payload = payloads[0]
            self.assertEqual(payload['mode'], 'check')
            self.assertEqual(payload['resume_plan']['stage'], 'retreat')
            reference = pickup.validate_reference(payload['resume_pickup_reference'],
                payload['resume_source_checkpoint'], payload['resume_context'], profile)
            self.assertEqual(reference['expected_pose'], dict(point_x=1.05, point_y=2., point_yaw=0.))
            self.assertEqual(json.loads((evidence/'resume-pickup-reference.json').read_text()), reference)
            self.assertFalse((evidence/'checkpoint.json').exists())
            instances[0].send.assert_not_called()
            instances[0].close.assert_called_once()
            self.assert_source_untouched(source, before)
            self.assertIn('RESUME_CHECK_OK', output.getvalue())


if __name__ == '__main__':
    unittest.main()
