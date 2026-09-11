"""Reconstruct proximity witnesses on pairs of source triangles.

FCL contact positions need not lie on both triangles. Generate edge/plane and
projected edge/edge candidates, then check every retained point against BOTH
triangles. This is a numeric witness finder, not a proof of disjointness.
"""
import numpy as np
import trimesh


def triangle_pair_witnesses(first, second, tolerance=1e-8):
    first, second = np.asarray(first, dtype=float), np.asarray(second, dtype=float)
    if (first.shape != second.shape or first.ndim != 3 or first.shape[1:] != (3, 3)
            or not np.isfinite(first).all() or not np.isfinite(second).all()
            or not np.isfinite(tolerance) or tolerance <= 0):
        raise ValueError('Invalid triangle-pair witness input')
    if not len(first):
        return np.empty((0, 3))
    candidates = [first, second]
    for a, b in ((first, second), (second, first)):
        normal = np.cross(b[:, 1]-b[:, 0], b[:, 2]-b[:, 0])
        lengths = np.linalg.norm(normal, axis=1)
        normal = normal/np.maximum(lengths[:, None], np.finfo(float).tiny)
        distances = np.einsum('nij,nj->ni', a-b[:, :1], normal)
        following = np.roll(distances, -1, axis=1)
        denominator = distances-following
        t = np.divide(distances, denominator, out=np.full_like(distances, np.nan), where=abs(denominator) > 1e-15)
        valid = (t >= 0) & (t <= 1) & (lengths[:, None] > 1e-20)
        points = a+np.nan_to_num(t)[:, :, None]*(np.roll(a, -1, axis=1)-a)
        candidates.append(np.where(valid[:, :, None], points, np.nan))
    # Coplanar intersections can have no contained vertex (crossing triangles).
    # Projected edge crossings supply candidates; the final 3-D distance test
    # also rejects apparent crossings of noncoplanar/disjoint edges.
    normal = np.cross(second[:, 1]-second[:, 0], second[:, 2]-second[:, 0])
    normal /= np.maximum(np.linalg.norm(normal, axis=1)[:, None], np.finfo(float).tiny)
    for i in range(3):
        p = first[:, i:i+1]
        r = first[:, [(i+1) % 3]]-p
        s = np.roll(second, -1, axis=1)-second
        delta = second-p
        denominator = np.einsum('nij,nj->ni', np.cross(r, s), normal)
        t = np.divide(np.einsum('nij,nj->ni', np.cross(delta, s), normal), denominator,
                      out=np.full_like(denominator, np.nan), where=abs(denominator) > 1e-20)
        u = np.divide(np.einsum('nij,nj->ni', np.cross(delta, r), normal), denominator,
                      out=np.full_like(denominator, np.nan), where=abs(denominator) > 1e-20)
        valid = (t >= 0) & (t <= 1) & (u >= 0) & (u <= 1)
        candidates.append(np.where(valid[:, :, None], p+np.nan_to_num(t)[:, :, None]*r, np.nan))
    points = np.concatenate(candidates, axis=1)
    count = points.shape[1]
    points = points.reshape(-1, 3)
    finite = np.isfinite(points).all(axis=1)
    points = points[finite]
    triangles = [np.repeat(x, count, axis=0)[finite] for x in (first, second)]
    # Degenerate faces do not establish a surface contact. No absence claim is
    # made when such a face or an unstable calculation yields no witness.
    nondegenerate = np.ones(len(points), dtype=bool)
    for tri in triangles:
        nondegenerate &= np.linalg.norm(np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]), axis=1) > 1e-20
    points = points[nondegenerate]
    if not len(points):
        return np.empty((0, 3))
    valid = np.ones(len(points), dtype=bool)
    for tri in triangles:
        closest = trimesh.triangles.closest_point(tri[nondegenerate], points)
        distance = np.linalg.norm(closest-points, axis=1)
        valid &= np.isfinite(distance) & (distance <= tolerance)
    return points[valid]
