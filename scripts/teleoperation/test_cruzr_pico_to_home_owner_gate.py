import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/teleoperation"))
import cruzr_pico_to_home_owner_gate as gate


def sample(positions, velocities=None):
    return {
        "name": list(gate.JOINT_ORDER),
        "position": list(positions),
        "velocity": list(velocities or [0.0] * 20),
    }


class GateTests(unittest.TestCase):
    def test_accepts_exact_pico_and_home(self):
        self.assertTrue(gate.evaluate(sample(gate.PICO_REFERENCE), "pico")["qualified"])
        self.assertTrue(gate.evaluate(sample(gate.HOME_REFERENCE), "home")["qualified"])

    def test_rejects_position_and_velocity(self):
        positions = list(gate.PICO_REFERENCE)
        positions[3] += 0.021
        self.assertFalse(gate.evaluate(sample(positions), "pico")["qualified"])
        velocities = [0.0] * 20
        velocities[7] = 0.011
        self.assertFalse(gate.evaluate(sample(gate.PICO_REFERENCE, velocities), "pico")["qualified"])

    def test_accepts_discrete_body_zero_variant_and_observed_measurements(self):
        positions = list(gate.PICO_BODY_ZERO_REFERENCE)
        positions[14:] = [-.002876213977, -.000766990394, -.000191747598,
                          -.000191747598, -.000383495197, 0.0]
        positions[0] += .002013350
        result = gate.evaluate(sample(positions), "pico")
        self.assertTrue(result["qualified"])
        self.assertEqual(result["matched_reference"], "pico_body_zero")
        self.assertEqual(result["out_of_tolerance_joints"], [])
        self.assertFalse(gate.evaluate(sample(positions), "home")["qualified"])
        self.assertEqual(gate.evaluate(sample(gate.PICO_REFERENCE), "pico")["matched_reference"],
                         "pico_body_flexed")

    def test_rejects_intermediate_body_and_mixed_endpoints(self):
        midpoint = [(a+b)/2 for a,b in zip(gate.PICO_REFERENCE, gate.PICO_BODY_ZERO_REFERENCE)]
        mixed = list(gate.PICO_BODY_ZERO_REFERENCE)
        mixed[16] = gate.PICO_REFERENCE[16]
        for positions in (midpoint, mixed):
            result = gate.evaluate(sample(positions), "pico")
            self.assertFalse(result["qualified"])
            self.assertIsNone(result["matched_reference"])
            self.assertTrue(result["out_of_tolerance_joints"])

    def test_each_variant_keeps_all_twenty_position_and_velocity_limits(self):
        for reference in gate.PICO_VARIANTS.values():
            for index in range(20):
                for sign in (-1, 1):
                    with self.subTest(index=index, sign=sign):
                        positions = list(reference); positions[index] += sign*.021
                        self.assertFalse(gate.evaluate(sample(positions), "pico")["qualified"])
                        velocities = [0.0]*20; velocities[index] = sign*.011
                        self.assertFalse(gate.evaluate(sample(reference, velocities), "pico")["qualified"])

    def test_invalid_reference_and_nonfinite_data_rejected(self):
        with self.assertRaises(ValueError): gate.evaluate(sample(gate.HOME_REFERENCE), "typo")
        for value in (float('nan'), float('inf'), True):
            positions = list(gate.PICO_BODY_ZERO_REFERENCE); positions[17] = value
            with self.assertRaises(ValueError): gate.evaluate(sample(positions), "pico")

    def test_open_lower_body_then_close_for_both_start_variants(self):
        from cruzr_pico_home_open_path import waypoints, DURATIONS_S
        for reference in gate.PICO_VARIANTS.values():
            start, opened, lowered, body_home, home = waypoints(reference)
            self.assertEqual(opened[14:], start[14:])
            self.assertEqual(lowered[14:], start[14:])
            for index in (3, 10):
                self.assertLessEqual(opened[index], -.5)
                self.assertEqual(opened[index], lowered[index])
                self.assertEqual(lowered[index], body_home[index])
            self.assertTrue(all(q == 0 for i,q in enumerate(lowered[:14]) if i not in (3,10)))
            self.assertEqual(body_home[14:], [0.0]*6)
            self.assertEqual(home, [0.0]*20)
            self.assertEqual([i for i in range(20) if body_home[i] != home[i]], [3,10])
            for a,b,duration in zip([start,opened,lowered,body_home],
                                    [opened,lowered,body_home,home], DURATIONS_S):
                self.assertLessEqual(1.875*max(abs(x-y) for x,y in zip(a,b))/duration, .08)

    def test_xml_keeps_body_open_and_maps_vendor_joint_order(self):
        import xml.etree.ElementTree as ET
        from cruzr_pico_home_open_path import validate_xml, waypoints
        path = ROOT/'scripts/teleoperation/tasks/cruzr_pico_to_home_owner.xml'
        validate_xml(path)
        stages = ET.parse(path).findall('.//Sequence/Parallel')
        self.assertEqual([s.get('name') for s in stages],
            ['open_arms','lower_arms_while_open','body_home_while_open','close_lowered_arms'])
        self.assertEqual([a.get('type') for a in stages[2]], ['head','lifter','waist'])
        vendor_order = ['shoulder_pitch','shoulder_roll','shoulder_yaw','elbow_roll',
                        'elbow_yaw','wrist_pitch','wrist_roll']
        targets = waypoints(gate.PICO_REFERENCE)[1:]
        for index in (0,1,3):
            for side,action in zip(['L','R'], stages[index]):
                self.assertEqual(action.get('type'), 'arm')
                expected = [targets[index][gate.JOINT_ORDER.index(side+'_'+n+'_joint')] for n in vendor_order]
                for actual,target in zip(map(float,action.get('joint_angles').split(';')),expected):
                    self.assertAlmostEqual(actual,target,places=10)

    def test_old_direct_home_xml_is_rejected(self):
        import tempfile
        from cruzr_pico_home_open_path import validate_xml
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'old.xml'
            path.write_text('<root main_tree_to_execute="MainTree"><BehaviorTree ID="MainTree">'
                '<Sequence><Parallel threshold="2"><Action ID="MetaMove" type="arm" '
                'location="left" duration="19.617" joint_angles="0;0;0;0;0;0;0" />'
                '</Parallel></Sequence></BehaviorTree></root>')
            with self.assertRaises(ValueError): validate_xml(path)

    def test_wrapper_uses_new_task_and_waits_longer_than_trajectory(self):
        import re
        from cruzr_pico_home_open_path import DURATIONS_S
        source = (ROOT/'scripts/teleoperation/cruzr_pico_to_home_owner.sh').read_text()
        self.assertIn('readonly TASK_NAME="cruzr/pico_to_home_open_v2"',source)
        self.assertIn('readonly XML_TARGET="$TASK_ROOT/cruzr/pico_to_home_open_v2.xml"',source)
        timeout = int(re.search(r'timeout (\d+) rosa action send_goal',source)[1])
        self.assertGreater(timeout,sum(DURATIONS_S)+20)

    def test_failed_remote_action_keeps_diagnostics_and_returncode(self):
        import os, subprocess, tempfile
        source = (ROOT/'scripts/teleoperation/cruzr_pico_to_home_owner.sh').read_text()
        remote = source.split('run_ssh bash -s -- "$CONTAINER" "$TASK_NAME"',1)[1]
        remote = remote.split('\n',1)[1].split('\nREMOTE',1)[0]
        with tempfile.TemporaryDirectory() as directory:
            stub = Path(directory)/'docker'
            stub.write_text('#!/bin/sh\necho CONTACT_DIAGNOSTIC >&2\nexit 7\n'); stub.chmod(0o755)
            result = subprocess.run(['bash','-s','--','mock-container','mock-task'], input=remote,
                text=True,capture_output=True,env=dict(os.environ,PATH=directory+os.pathsep+os.environ['PATH']))
        self.assertEqual(result.returncode,7,result.stderr)
        self.assertIn('CONTACT_DIAGNOSTIC',result.stdout)

    def test_rejects_missing_joint(self):
        value = sample(gate.PICO_REFERENCE)
        value["name"] = value["name"][:-1]
        value["position"] = value["position"][:-1]
        value["velocity"] = value["velocity"][:-1]
        with self.assertRaises(ValueError):
            gate.evaluate(value, "pico")


if __name__ == "__main__":
    unittest.main()
