"""Conservative convex-union coverage of a rigid CAD assembly, offline only.

Vertex tests alone do not prove coverage by a nonconvex union. We enclose the
whole CAD in a convex hull, cover each of its triangular faces by ONE convex
member, and require a common point in every member. The union is star-shaped
about that point; covering the entire hull boundary also covers its interior.
"""
from __future__ import annotations

import numpy as np
from scipy.spatial import ConvexHull
import trimesh

EPS = 1e-8
NUMERIC_PADDING_M = 1e-6


def points3(values):
    values = np.asarray(values, dtype=float)
    if values.ndim != 2 or values.shape[1] != 3 or not len(values) or not np.isfinite(values).all():
        raise ValueError('Expected finite Nx3 points')
    return values


def convex_mesh(vertices):
    """Keep Qhull topology: automatic vertex welding can reopen tiny CAD seams."""
    vertices = points3(vertices)
    hull = ConvexHull(vertices)
    faces = hull.simplices.copy()
    triangles = vertices[faces]
    normals = np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
    flip = np.einsum('ij,ij->i',normals,hull.equations[:,:3]) < 0
    faces[flip] = faces[flip][:,[0,2,1]]
    result = trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
    result.remove_unreferenced_vertices()
    if not result.is_volume:
        raise ValueError('Cannot construct a closed positive convex hull without welding')
    return result


class Capsule:
    def __init__(self, name, endpoints, radius):
        self.name, self.points, self.radius = name, points3(endpoints), float(radius)
        if self.points.shape != (2,3) or not np.isfinite(radius) or radius <= 0:
            raise ValueError('Invalid capsule')

    def score(self, vertices):
        vertices = points3(vertices)
        a,b = self.points
        axis = b-a
        length2 = axis@axis
        u = np.clip((vertices-a)@axis/length2,0,1) if length2 else np.zeros(len(vertices))
        return np.linalg.norm(vertices-(a+u[:,None]*axis),axis=1)-self.radius

    def specification(self):
        return dict(kind='capsule',name=self.name,endpoints_m=self.points.tolist(),radius_m=self.radius)


class RoundedHull:
    def __init__(self, name, vertices, radius):
        self.name, self.points, self.radius = name, points3(vertices), float(radius)
        if not np.isfinite(radius) or radius <= 0:
            raise ValueError('Invalid hull radius')
        self.hull = convex_mesh(self.points)
        self.planes = ConvexHull(self.hull.vertices).equations

    def score(self, vertices):
        vertices = points3(vertices)
        # A positive plane residual always goes through the actual distance
        # calculation; do not expand the interior test with a tolerance.
        inside = (vertices@self.planes[:,:3].T+self.planes[:,3] <= 0).all(axis=1)
        distance = np.zeros(len(vertices))
        if (~inside).any():
            _,distance[~inside],_ = trimesh.proximity.closest_point(self.hull,vertices[~inside])
        if not np.isfinite(distance).all():
            raise ValueError('Nonfinite hull distance')
        return distance-self.radius

    def specification(self):
        return dict(kind='rounded_convex_hull',name=self.name,vertices_m=self.hull.vertices.tolist(),
            radius_m=self.radius)


def certify_boundary(hull, members, anchor):
    """Sufficient, fail-closed finite certificate; never accept by sample density."""
    anchor = points3([anchor])
    if not members or not hull.is_volume:
        raise ValueError('Expected a closed positive hull and convex members')
    anchor_scores = [float(member.score(anchor)[0]) for member in members]
    if max(anchor_scores) > -EPS:
        raise ValueError('Convex members lack the required certified common anchor')
    scores = np.array([member.score(hull.vertices) for member in members])
    # Each member is convex: all three vertices inside it imply the whole
    # triangle inside it. Vertices in different members do not suffice.
    covered = (scores[:,hull.faces] <= -EPS).all(axis=2)
    return dict(boundary_faces=len(hull.faces), uncovered_faces=int((~covered.any(axis=0)).sum()),
        member_face_counts={m.name:int(row.sum()) for m,row in zip(members,covered)},
        common_anchor_m=anchor[0].tolist(), anchor_score_m=dict(zip([m.name for m in members],anchor_scores)),
        face_owners=[members[int(np.flatnonzero(c)[0])].name if c.any() else None for c in covered.T],
        volume_covered=bool(covered.any(axis=0).all()),
        proof='each boundary triangle in one convex member; every member shares anchor; star-shaped union'), covered


def build_cover(vertices, members, anchor):
    vertices = points3(vertices)
    hull = convex_mesh(vertices)
    equations = ConvexHull(hull.vertices).equations
    residual = float((vertices@equations[:,:3].T+equations[:,3]).max())
    if residual > EPS:
        raise ValueError('Source not contained in outer hull')
    before, covered = certify_boundary(hull,members,anchor)
    missing = ~covered.any(axis=0)
    result = list(members)
    patch = None
    if missing.any():
        # Retain COMPLETE ambiguous faces, not just individually outside vertices.
        patch_points = np.vstack([hull.triangles[missing].reshape(-1,3),anchor])
        patch = RoundedHull('CAD_supplement',np.unique(patch_points,axis=0),NUMERIC_PADDING_M)
        result.append(patch)
    certificate,_ = certify_boundary(hull,result,anchor)
    if not certificate['volume_covered']:
        raise ValueError('Supplement failed coverage verification')
    certificate.update(source_vertices=len(vertices),outer_hull_source_plane_residual_m=residual,
        outer_hull_faces=len(hull.faces),numerical_padding_m=NUMERIC_PADDING_M,
        physical_error_margin_included=False,physical_approval=False,installable=False)
    return result, certificate, before, hull, patch
