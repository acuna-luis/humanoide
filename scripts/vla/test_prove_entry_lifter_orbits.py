import unittest
import numpy as np
from prepare_vla_entry_bundle import ROOT, RobotGeometry, common
from entry_relative_kinematics import RelativeChain
from entry_orbit_bounds import triangle_bounds


class LifterOrbitFrameTests(unittest.TestCase):
    def test_two_axis_bounds_enclose_full_fk_source_triangles(self):
        package = ROOT/'cruzr_s2_description_splint/cruzr_s2_description'
        model = RobotGeometry(package/'urdf/cruzr_s2_v1/cruzr_s2_v1.urdf', package,
                              dict(frame_id='base_link', complete=True, objects=[]))
        a, b = [next(s for s in model.shapes if s.name == name) for name in ('lifter_pitch_2_link#0', 'torso_link#0')]
        chain = RelativeChain(model.joints, a.link, b.link, common.fk)
        inv = np.linalg.inv(chain.b[0]['origin'])
        center = -.009
        pose = inv@chain.evaluate({'waist_yaw_joint': center})
        rng = np.random.default_rng(104)
        source = b.source_mesh.triangles[rng.choice(len(b.source_mesh.faces), 400, replace=False)]
        triangles = source@pose[:3, :3].T+pose[:3, 3]
        origin = chain.b[1]['origin'][:3, 3]
        axis = chain.b[1]['origin'][:3, :3]@chain.b[1]['axis']
        rel = triangles-origin
        radius = np.linalg.norm(rel-(rel@axis)[:, :, None]*axis, axis=2).max(1)
        bounds = triangle_bounds(triangles, (-.76, .018), 2*radius*np.sin(.009/2))
        for _ in range(20):
            state = dict(model.auxiliary, lifter_pitch_3_joint=rng.uniform(-.76, .018),
                         waist_yaw_joint=rng.uniform(center-.009, center+.009))
            fk = common.fk.forward_kinematics(model.joints, state)
            transform = inv@np.linalg.inv(fk[a.link])@fk[b.link]
            points = source@transform[:3, :3].T+transform[:3, 3]
            r = np.linalg.norm(points[:, :, :2], axis=2)
            self.assertTrue((r >= bounds[:, 0, None]).all() and (r <= bounds[:, 1, None]).all())
            self.assertTrue((points[:, :, 2] >= bounds[:, 2, None]).all() and (points[:, :, 2] <= bounds[:, 3, None]).all())
            angle = np.arctan2(points[:, :, 1], points[:, :, 0])
            midpoint = (bounds[:, 4]+bounds[:, 5])/2
            self.assertTrue((np.abs((angle-midpoint[:, None]+np.pi) % (2*np.pi)-np.pi) <= ((bounds[:, 5]-bounds[:, 4])/2)[:, None]).all())


if __name__ == '__main__':
    unittest.main()
