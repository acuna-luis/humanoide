"""Offline triangle-bound separation using a revolute joint's cylindrical frame.

The bounds enclose triangle surfaces, not the material of hollow CAD assemblies.
An unresolved bound is not a collision. No pair exemption or robot transport.
"""
from dataclasses import dataclass
import numpy as np

EPS = 1e-7


def triangle_bounds(triangles, angular_shift=(0., 0.), displacement=0.):
    t = np.asarray(triangles, float)
    if t.ndim != 3 or t.shape[1:] != (3, 3) or not len(t) or not np.isfinite(t).all():
        raise ValueError('Expected finite triangles')
    shift = np.asarray(angular_shift, float)
    d = np.broadcast_to(np.asarray(displacement, float), (len(t),))
    if shift.shape != (2,) or not np.isfinite(shift).all() or shift[0] > shift[1] or not np.isfinite(d).all() or (d < 0).any():
        raise ValueError('Invalid angular/displacement interval')
    xy = t[:, :, :2]
    end = np.roll(xy, -1, axis=1); edge = end-xy
    length2 = np.sum(edge*edge, axis=2)
    u = np.clip(-np.sum(xy*edge, axis=2)/np.maximum(length2, 1e-300), 0, 1)
    rlo = np.linalg.norm(xy+u[:, :, None]*edge, axis=2).min(1)
    cross = xy[:, :, 0]*end[:, :, 1]-xy[:, :, 1]*end[:, :, 0]
    # Origin inside a nondegenerate projected triangle => minimum radius zero.
    area = np.abs(cross.sum(1))
    inside = ((cross >= 0).all(1) | (cross <= 0).all(1)) & (area > 1e-20)
    rlo[inside] = 0
    rhi = np.linalg.norm(xy, axis=2).max(1)
    angle = np.arctan2(xy[:, :, 1], xy[:, :, 0])
    lo, hi = angle.min(1), angle.max(1)
    # A sector narrower than pi is convex; vertex extrema enclose the triangle.
    full = (hi-lo >= np.pi) | (rlo <= d+EPS)
    widening = np.arcsin(np.minimum(1., (d+EPS)/np.maximum(rlo, EPS)))
    lo, hi = lo-widening+shift[0], hi+widening+shift[1]
    lo[full], hi[full] = -np.pi, np.pi
    return np.column_stack((np.maximum(0, rlo-d-EPS), rhi+d+EPS,
                            t[:, :, 2].min(1)-d-EPS, t[:, :, 2].max(1)+d+EPS,
                            lo-EPS, hi+EPS))


def separation(a, b):
    """Lower Euclidean surface distance between cylindrical boxes; broadcasts."""
    a, b = np.asarray(a), np.asarray(b)
    radial = np.maximum(0., np.maximum(a[..., 0]-b[..., 1], b[..., 0]-a[..., 1]))
    axial = np.maximum(0., np.maximum(a[..., 2]-b[..., 3], b[..., 2]-a[..., 3]))
    center = (a[..., 4]+a[..., 5]-b[..., 4]-b[..., 5])/2
    halfwidth = (a[..., 5]-a[..., 4]+b[..., 5]-b[..., 4])/2
    angle = np.maximum(0., np.abs((center+np.pi) % (2*np.pi)-np.pi)-halfwidth)
    angular = 4*a[..., 0]*b[..., 0]*np.sin(angle/2)**2
    return np.maximum(0., np.sqrt(radial**2+axial**2+angular)-EPS)


@dataclass
class Node:
    bound: np.ndarray
    ids: np.ndarray
    children: tuple = ()


def tree(bounds, centers, ids=None, leaf_size=8):
    if ids is None:
        ids = np.arange(len(bounds))
    values = bounds[ids]
    enclosing = np.array([values[:, 0].min(), values[:, 1].max(), values[:, 2].min(),
                          values[:, 3].max(), values[:, 4].min(), values[:, 5].max()])
    if len(ids) <= leaf_size:
        return Node(enclosing, ids)
    axis = np.ptp(centers[ids], axis=0).argmax()
    ordered = ids[np.argsort(centers[ids, axis], kind='stable')]; mid = len(ids)//2
    return Node(enclosing, ids, (tree(bounds, centers, ordered[:mid], leaf_size),
                                 tree(bounds, centers, ordered[mid:], leaf_size)))


def refine_triangle_pair(a, b, bounds_b, max_nodes=4096):
    """Subdivide surfaces, preserving all children and the full angular domain."""
    pending = [(a, b)]; count = 0; minimum = float('inf')
    while pending and count < max_nodes:
        x, y = pending.pop(); count += 1
        bound = float(separation(triangle_bounds(x[None])[0], bounds_b(y[None])[0]))
        if bound > 0:
            minimum = min(minimum, bound); continue
        lengths = [np.linalg.norm(t-np.roll(t, -1, axis=0), axis=1) for t in (x, y)]
        which = int(lengths[1].max() > lengths[0].max())
        t = (x, y)[which]; edge = int(lengths[which].argmax())
        i, j, k = edge, (edge+1) % 3, (edge+2) % 3
        mid = (t[i]+t[j])/2
        children = (np.array([t[i], mid, t[k]]), np.array([mid, t[j], t[k]]))
        pending.extend((x, child) if which else (child, y) for child in children)
    return dict(proved=not pending, nodes=count, lower_bound_m=minimum if not pending else 0.)


def prove_boxes(a, b, triangles_a, triangles_b, max_nodes=200000, refine_b=None):
    ta, tb = tree(a, triangles_a.mean(1)), tree(b, triangles_b.mean(1))
    pending = [(ta, tb)]; count = 0; minimum = float('inf')
    while pending:
        if count >= max_nodes:
            return dict(proved=False, reason='NODE_BUDGET', nodes=count)
        x, y = pending.pop(); count += 1
        bound = float(separation(x.bound, y.bound))
        if bound > 0:
            minimum = min(minimum, bound); continue
        if not x.children and not y.children:
            distances = separation(a[x.ids, None], b[y.ids])
            for i, j in np.argwhere(distances <= 0):
                refined = (refine_triangle_pair(triangles_a[x.ids[i]], triangles_b[y.ids[j]], refine_b)
                           if refine_b is not None else dict(proved=False))
                if not refined['proved']:
                    return dict(proved=False, reason='ORBIT_ENVELOPES_OVERLAP_NOT_COLLISION', nodes=count,
                                unresolved_triangles=[int(x.ids[i]), int(y.ids[j])], refinement=refined)
                distances[i, j] = refined['lower_bound_m']
            minimum = min(minimum, float(distances.min())); continue
        if x.children and (not y.children or len(x.ids) >= len(y.ids)):
            pending.extend((child, y) for child in x.children)
        else:
            pending.extend((x, child) for child in y.children)
    return dict(proved=True, reason='ALL_TRIANGLE_ORBIT_BOXES_SEPARATED', nodes=count, lower_bound_m=minimum)
