import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import smolvla_physical_bridge as b  # noqa: E402


class PlanStep(unittest.TestCase):
    def test_clip_envelope_and_abort(self):
        obs = b.PICO_POSE[:]
        pred = [o + 1.0 for o in obs] + [0.9]
        diff = [p - o for p, o in zip(pred, obs)]
        got_obs, target, info = b.plan_step(pred, diff, obs, None, max_step=0.05, envelope=0.5,
                                            margin=0.03, jump_abort=0.15)
        self.assertEqual([round(x, 9) for x in got_obs], [round(x, 9) for x in obs])
        for t, o, (lo, hi) in zip(target, obs, b.URDF_LIMITS):
            self.assertLessEqual(t - o, 0.05 + 1e-9)
            self.assertLessEqual(t, hi - 0.03 + 1e-9)
        with self.assertRaises(ValueError):
            b.plan_step(pred, diff, obs, [o + 0.3 for o in obs], max_step=0.05, envelope=0.5,
                        margin=0.03, jump_abort=0.15)


class PlanChunk(unittest.TestCase):
    def test_sequential_clipping(self):
        obs = b.PICO_POSE[:]
        chunk = [[o - 1.0 for o in obs] + [0.9] for _ in range(8)]
        targets = b.plan_chunk(chunk, 4, obs, obs, max_step=0.1, envelope=1.3, margin=0.03)
        self.assertEqual(len(targets), 4)
        prev = obs
        for t in targets:
            self.assertTrue(all(abs(a - p) <= 0.1 + 1e-9 for a, p in zip(t, prev)))
            prev = t

    def test_envelope_respected(self):
        obs = b.PICO_POSE[:]
        chunk = [[o + 5.0 for o in obs] + [0.1] for _ in range(8)]
        targets = b.plan_chunk(chunk, 8, obs, obs, max_step=0.1, envelope=0.25, margin=0.03)
        self.assertTrue(all(abs(t - s) <= 0.25 + 1e-9 for t, s in zip(targets[-1], obs)))


    def test_offset_skips_concurrent_action(self):
        obs = b.PICO_POSE[:]
        chunk = [[o + 0.05 * i for o in obs] + [0.1] for i in range(8)]
        first = b.plan_chunk(chunk, 1, obs, obs, max_step=0.1, envelope=1.3, margin=0.03, offset=1)[0]
        self.assertAlmostEqual(first[0] - obs[0], 0.05)


class HandGateTest(unittest.TestCase):
    def test_close_only_near_and_stay_closed_while_moving(self):
        g = b.HandGate(0.5, 2, 0.15)
        seq = [(.9, [1]), (.9, [.1]), (.9, [.1]), (.9, [.5]), (.9, [.5]), (.2, [.5]), (.2, [.5])]
        self.assertEqual([g.update(s, d) for s, d in seq], ['open', None, 'closed', None, None, None, 'open'])


class Xml(unittest.TestCase):
    def test_xml_is_well_formed(self):
        obs = b.PICO_POSE[:]
        ET.fromstring(b.step_xml(obs, 1.0, 'closed'))
        ET.fromstring(b.chunk_xml([obs, obs], 0.5, 'open'))
        root = ET.fromstring(b.setup_xml((-0.49, -0.65), obs, 5.0))
        actions = root.iter('Action')
        types = [a.get('type') for a in actions]
        self.assertEqual(types, ['head', 'arm', 'effector'])
        self.assertEqual(root.find('.//Parallel').get('threshold'), '3')

    def test_head_only_setup(self):
        root = ET.fromstring(b.setup_xml((-0.49, -0.65), None, 3.0))
        self.assertEqual([a.get('type') for a in root.iter('Action')], ['head'])
        self.assertEqual(next(root.iter('Action')).get('joint_angles'), '-0.4900; -0.6500')


if __name__ == '__main__':
    unittest.main()
