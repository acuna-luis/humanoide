"""Directional finite-box Taylor bounds against static scene solids, offline.

For a vertex v and unit direction n, f(q)=n.dot(FK(q)v). Its first derivative
at joint i is n.dot(axis_i cross (v-origin_i)). For ancestor joints i,j,
the mixed second derivative has magnitude at most the global perpendicular
radius of the deeper joint. Summing 0.5*M_ij*h_i*h_j bounds the Taylor remainder
throughout an independent joint box. Max over all model vertices bounds the
entire solid's support. No normal needs to be a correct FCL contact normal:
each tested direction supplies an independent separating-plane inequality.
"""
import numpy as np
import fcl


def remainder_bound(global_radii, depths, half_widths):
    radii, depths, widths = map(np.asarray, (global_radii, depths, half_widths))
    if radii.ndim != 1 or depths.shape != radii.shape or widths.shape != radii.shape:
        raise ValueError('Invalid Hessian bound shape')
    if not np.isfinite(radii).all() or not np.isfinite(widths).all() or (radii < 0).any() or (widths < 0).any():
        raise ValueError('Invalid Hessian bound')
    matrix = np.where(depths[:, None] >= depths[None, :], radii[:, None], radii[None, :])
    return float(.5 * widths @ matrix @ widths)


class DirectionalSceneBounds:
    def __init__(self, base, common, order):
        self.base, self.common, self.order = base, common, tuple(order)
        self.by_child = {j['child']: j for j in self.joints}
        self.by_name = {j['name']: j for j in self.joints}

    def __getattr__(self, name): return getattr(self.base, name)

    def interval_separations(self, q, half_widths, indices):
        result = self.base.interval_separations(q, half_widths, indices)
        candidates = [(k, i) for k, i in enumerate(indices)
                      if result[k] <= .002+1e-9 and self.pairs[i][1] >= self.robot_count]
        if not candidates: return result
        poses = self.common.fk.forward_kinematics(self.joints,
            dict(self.auxiliary, **dict(zip(self.order, q))))
        cached = {}
        for k, i in candidates:
            a, b = self.pairs[i]; shape, scene = self.shapes[a], self.shapes[b]
            if not np.array_equal(scene.pose, np.eye(4)):
                raise ValueError('Static scene transform must be baked into mesh')
            if a not in cached:
                chain = []; link = shape.link
                while link in self.by_child:
                    joint = self.by_child[link]; chain.append(joint['name']); link = joint['parent']
                chain.reverse()
                active = [j for j, name in enumerate(self.order) if name in chain]
                if any(self.by_name[self.order[j]]['type'] not in ('revolute', 'continuous') for j in active):
                    raise ValueError('Directional bound only supports revolute controls')
                points = self.common.fk.apply(shape.mesh.vertices, poses[shape.link])
                derivatives = []
                for j in active:
                    joint = self.by_name[self.order[j]]; transform = poses[joint['child']]
                    axis = transform[:3, :3] @ joint['axis']; axis /= np.linalg.norm(axis)
                    derivatives.append(np.cross(axis, points-transform[:3, 3]))
                cached[a] = points, np.asarray(derivatives), active, [chain.index(self.order[j]) for j in active]
            points, derivatives, active, depths = cached[a]
            shape.place(poses[shape.link])
            normals = list(np.eye(3))
            nearest = fcl.DistanceResult()
            fcl.distance(shape.obj, scene.obj, fcl.DistanceRequest(enable_nearest_points=True), nearest)
            pair_points = np.asarray(nearest.nearest_points)
            if pair_points.shape == (2, 3) and np.isfinite(pair_points).all():
                normal = pair_points[1]-pair_points[0]; length = np.linalg.norm(normal)
                if length > 1e-10: normals.append(normal/length)
            widths = np.asarray(half_widths)[active]
            remainder = remainder_bound(self.weights[i, active], np.asarray(depths), widths)
            for normal in normals:
                for direction in (normal, -normal):
                    first_order = (np.abs(derivatives @ direction).T @ widths) if active else np.zeros(len(points))
                    upper = np.max(points @ direction + first_order) + remainder + shape.geometry_error_m
                    lower = np.min(scene.mesh.vertices @ direction) - scene.geometry_error_m
                    # Explicit numerical cushion, separate from the physical 2mm.
                    gap = float(lower-upper-1e-7)
                    result[k] = max(result[k], gap, 0.)
        return result
