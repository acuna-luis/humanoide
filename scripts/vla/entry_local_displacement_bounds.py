"""Posture-dependent finite rotation bounds for offline affine ENTRY review.

Proof: telescope joint changes from proximal to distal. At the instant joint i
changes, its descendants still have nominal angles; ancestor changes rigidly
move its axis and descendant shape together. Its nominal perpendicular radius
therefore bounds that step. A point rotates at most 2*r*sin(min(h,pi)/2) for
|delta|<=h. Sum steps and both branches after cancelling common ancestors.
This is a finite perturbation bound, not a Jacobian linearization or sampling.
"""
import math
import numpy as np


class SelectivePairDistances:
    """Same conservative solids as RobotGeometry, queried only where needed."""
    def __init__(self, base, common, distance_function):
        self.base, self.common, self.distance_function = base, common, distance_function

    def __getattr__(self, name):
        return getattr(self.base, name)

    def selected_distances(self, q, indices):
        q=np.asarray(q,dtype=float)
        if q.shape!=self.lower.shape or not np.isfinite(q).all() or (q<self.lower).any() or (q>self.upper).any():
            raise ValueError('Invalid selective-query posture')
        if any(type(i) not in (int,np.int64,np.int32) or not 0<=i<len(self.pairs) for i in indices):
            raise ValueError('Invalid selective-query pair')
        poses=self.common.fk.forward_kinematics(self.joints,
            dict(self.auxiliary, **dict(zip(self.common.JOINT_ORDER,q))))
        needed={s for i in indices for s in self.pairs[i]}
        bounds={}
        for s in needed:
            shape=self.shapes[s]
            if s<self.robot_count:shape.place(poses[shape.link])
            points=self.common.fk.apply(self.common.fk.corners(*shape.mesh.bounds),shape.pose)
            bounds[s]=(points.min(axis=0),points.max(axis=0))
        answer=[]
        for i in indices:
            a,b=self.pairs[i];low_a,high_a=bounds[a];low_b,high_b=bounds[b]
            gap=float(np.linalg.norm(np.maximum(0,np.maximum(low_a-high_b,low_b-high_a))))
            answer.append(max(0.,gap-self.shapes[a].geometry_error_m-self.shapes[b].geometry_error_m)
                if gap>.04 else self.distance_function(self.shapes[a],self.shapes[b]))
        return np.asarray(answer)

    def distances(self,q):
        return self.selected_distances(q,list(range(len(self.labels))))


def chord_displacement(radii, half_widths):
    radii = np.asarray(radii, dtype=float)
    half_widths = np.asarray(half_widths, dtype=float)
    if (radii.ndim != 2 or half_widths.shape != (radii.shape[1],) or
            not np.isfinite(radii).all() or not np.isfinite(half_widths).all() or
            (radii < 0).any() or (half_widths < 0).any()):
        raise ValueError('Invalid finite-rotation enclosure')
    return radii @ (2*np.sin(np.minimum(half_widths, math.pi)/2))


class LocalDisplacementBounds:
    def __init__(self, base, common, joint_order):
        self.base, self.common, self.order = base, common, tuple(joint_order)
        by_child = {j['child']: j for j in base.joints}
        self.joint_map = {j['name']: j for j in base.joints}
        if any(self.joint_map[n]['type'] not in ('revolute', 'continuous') for n in self.order):
            raise ValueError('Only independent revolute controls are supported')
        self.masks = []
        for shape in base.shapes:
            names = set()
            link = shape.link
            while link in by_child:
                j = by_child[link]
                names.add(j['name'])
                link = j['parent']
            self.masks.append(np.array([n in names for n in self.order]))
        self.corners = [common.fk.corners(*(s.mesh.bounds +
                        np.array([[-1], [1]])*s.geometry_error_m)) for s in base.shapes]
        self.cached_key = None
        self.cached_radii = None

    def __getattr__(self, name):
        return getattr(self.base, name)

    def pair_radii_at(self, q):
        q = np.asarray(q, dtype=float)
        if q.shape != (len(self.order),) or not np.isfinite(q).all():
            raise ValueError('Invalid nominal posture')
        key = q.tobytes()
        if key == self.cached_key:
            return self.cached_radii
        poses = self.common.fk.forward_kinematics(self.joints,
                    dict(self.auxiliary, **dict(zip(self.order, q))))
        shape_radii = np.zeros((len(self.shapes), len(self.order)))
        for s, shape in enumerate(self.shapes):
            points = self.common.fk.apply(self.corners[s], poses[shape.link])
            for i in np.flatnonzero(self.masks[s]):
                joint = self.joint_map[self.order[i]]
                # Rotation about the joint axis leaves that axis unchanged;
                # child-frame origin and axis therefore locate its world line.
                pose = poses[joint['child']]
                axis = pose[:3, :3] @ joint['axis']
                norm = np.linalg.norm(axis)
                if not np.isfinite(norm) or norm <= 0:
                    raise ValueError('Invalid revolute axis')
                axis = axis/norm
                shape_radii[s, i] = np.linalg.norm(
                    np.cross(points-pose[:3, 3], axis), axis=1).max()
        pairs = []
        for a, b in self.pairs:
            # Common ancestors only apply a shared rigid transform to a pair.
            exclusive = np.logical_xor(self.masks[a], self.masks[b])
            pairs.append((shape_radii[a]+shape_radii[b])*exclusive)
        result = np.asarray(pairs)
        if (result > self.weights+1e-7).any():
            raise ValueError('Local radii exceed independent global enclosure')
        self.cached_key, self.cached_radii = key, result
        return result

    def displacement_bounds(self, q, half_widths):
        return chord_displacement(self.pair_radii_at(q), half_widths)

    def interval_separations(self,q,half_widths,indices):
        from entry_interval_boxes import scene_separations
        return scene_separations(self,self.common,self.order,q,half_widths,indices)
