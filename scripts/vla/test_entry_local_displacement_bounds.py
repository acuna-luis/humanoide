"""Finite-rotation counterexamples and 3D property checks; never physical approval."""
import math
from types import SimpleNamespace
import unittest
import numpy as np

from prepare_vla_entry_bundle import common, certify_pairs
from entry_local_displacement_bounds import LocalDisplacementBounds, chord_displacement


def geometry(three_d=False):
    joints=[]
    for name, parent, child, xyz, axis in [
        ('a','base_link','one',[0,0,0],[0,0,1]),
        ('b','one','two',[1,0,0],[0,1,0] if three_d else [0,0,1])]:
        joints.append(dict(name=name,type='revolute',parent=parent,child=child,
                           origin=common.fk.transform(xyz,np.eye(3)),axis=np.array(axis,float)))
    box = np.array([[.999,-.001,-.001],[1.001,.001,.001]])
    shapes=[SimpleNamespace(link=l,mesh=SimpleNamespace(bounds=box),geometry_error_m=0.)
            for l in ['two','base_link','one']]
    return SimpleNamespace(joints=joints,shapes=shapes,auxiliary={},
        pairs=[(0,1),(0,2)],labels=[['two','scene'],['two','one']],
        weights=np.array([[2.01,1.01],[0.,1.01]]))


class LocalBoundTests(unittest.TestCase):
    def test_folded_arm_uses_local_radius_without_missing_cross_terms(self):
        g=LocalDisplacementBounds(geometry(),common,['a','b'])
        q=np.array([0.,math.pi]);half=np.array([.2,.2])
        bound=g.displacement_bounds(q,half)[0]
        self.assertLess(bound,.202)
        points=g.corners[0]
        poses=common.fk.forward_kinematics(g.joints,dict(zip(g.order,q)))
        p0=common.fk.apply(points,poses['two'])
        for x in np.linspace(-.2,.2,13):
            for y in np.linspace(-.2,.2,13):
                poses=common.fk.forward_kinematics(g.joints,dict(zip(g.order,q+[x,y])))
                d=np.linalg.norm(common.fk.apply(points,poses['two'])-p0,axis=1).max()
                self.assertLessEqual(d,bound+1e-12)

    def test_three_dimensional_finite_rotations_are_enclosed(self):
        g=LocalDisplacementBounds(geometry(True),common,['a','b'])
        rng=np.random.default_rng(2718)
        for _ in range(80):
            q=rng.uniform(-2,2,2);half=rng.uniform(0,2,2)
            b=g.displacement_bounds(q,half)[0]
            p0=common.fk.apply(g.corners[0],common.fk.forward_kinematics(g.joints,dict(zip(g.order,q)))['two'])
            for delta in rng.uniform(-half,half,(20,2)):
                p=common.fk.apply(g.corners[0],common.fk.forward_kinematics(g.joints,dict(zip(g.order,q+delta)))['two'])
                self.assertLessEqual(np.linalg.norm(p-p0,axis=1).max(),b+1e-12)

    def test_common_rotation_cancels_and_descendant_rotation_does_not(self):
        g=LocalDisplacementBounds(geometry(),common,['a','b'])
        self.assertEqual(g.displacement_bounds([0,0],[1,0])[1],0.)
        self.assertGreater(g.displacement_bounds([0,0],[0,1])[1],.9)

    def test_large_angular_interval_cannot_wrap_to_zero(self):
        self.assertAlmostEqual(chord_displacement([[2]], [2*math.pi])[0],4.)
        self.assertAlmostEqual(chord_displacement([[2]], [.1])[0],4*math.sin(.05))
        for r,h in [([[-1]],[1]), ([[1]],[-1]), ([[1]],[float('nan')]), ([[1]],[1,2])]:
            with self.assertRaises(ValueError):chord_displacement(r,h)

    def test_combined_interval_and_uncertainty_are_both_passed(self):
        from test_prepare_vla_entry_bundle import AnalyticGeometry
        class Checked(AnalyticGeometry):
            calls=[]
            def displacement_bounds(self,q,h):
                self.calls.append(h.copy())
                return self.weights@h
        g=Checked();result=certify_pairs(g,[[0.],[1.]],joint_error_rad=.02,max_depth=3)
        self.assertTrue(any(np.allclose(h,[.52]) for h in g.calls))
        self.assertTrue(any(np.allclose(h,[.02]) for h in g.calls))
        self.assertFalse(result['physical_approval'])


if __name__=='__main__':unittest.main()
