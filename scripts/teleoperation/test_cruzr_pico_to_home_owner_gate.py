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

    def test_rejects_missing_joint(self):
        value = sample(gate.PICO_REFERENCE)
        value["name"] = value["name"][:-1]
        value["position"] = value["position"][:-1]
        value["velocity"] = value["velocity"][:-1]
        with self.assertRaises(ValueError):
            gate.evaluate(value, "pico")


if __name__ == "__main__":
    unittest.main()
