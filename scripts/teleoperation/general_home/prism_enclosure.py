"""Recognize complete convex prism sidewalls; close their two missing caps.

This is deliberately narrower than hole filling. Every source vertex must be
on one of two congruent convex end loops, and every side band must consist of
exactly its two triangles. Unknown/open sheets fail closed. Original meshes
are never edited. The derived convex enclosure contains all source triangles
and the prism interior, including numerically imperfect end planes.
"""
from collections import Counter

import numpy as np
from scipy.spatial import ConvexHull,cKDTree

from .union_coverage import convex_mesh

REGISTRATION_TOLERANCE_M = 1e-8


def _loops(mesh):
    edges,counts = np.unique(np.sort(mesh.edges,axis=1),axis=0,return_counts=True)
    if not len(edges) or counts.max()>2:
        return None
    boundary = edges[counts==1]
    vertices,degree = np.unique(boundary,return_counts=True)
    if not len(vertices) or not (degree==2).all():
        return None
    neighbours = {int(v):[] for v in vertices}
    for a,b in boundary:
        neighbours[int(a)].append(int(b));neighbours[int(b)].append(int(a))
    unseen = set(neighbours)
    loops = []
    while unseen:
        start = min(unseen);previous,current = None,start
        loop = []
        while current in unseen:
            loop.append(current);unseen.remove(current)
            nxt = next(v for v in neighbours[current] if v!=previous)
            previous,current = current,nxt
        if current!=start:
            return None
        loops.append(loop)
    return loops


def convex_prism_enclosure(mesh):
    """Return a full prism hull and certificate, or None for unrecognized CAD."""
    if not np.isfinite(mesh.vertices).all() or mesh.is_watertight or not mesh.is_winding_consistent:
        return None
    loops = _loops(mesh)
    if loops is None or len(loops)!=2 or len(loops[0])!=len(loops[1]):
        return None
    a,b = [np.array(loop,dtype=int) for loop in loops]
    n = len(a)
    if n<3 or len(mesh.vertices)!=2*n or len(mesh.faces)!=2*n:
        return None
    first,second = mesh.vertices[a],mesh.vertices[b]
    displacement = second.mean(axis=0)-first.mean(axis=0)
    distance,correspondence = cKDTree(second).query(first+displacement)
    error = float(distance.max())
    if len(set(correspondence))!=n or error>REGISTRATION_TOLERANCE_M:
        return None
    b = b[correspondence]
    centered = first-first.mean(axis=0)
    _,sv,basis = np.linalg.svd(centered,full_matrices=False)
    if sv[1]<1e-7 or abs(displacement@basis[-1])<1e-7:
        return None
    plane_errors = [float(np.abs((mesh.vertices[loop]-mesh.vertices[loop].mean(axis=0))@basis[-1]).max()) for loop in (a,b)]
    if max(plane_errors)>REGISTRATION_TOLERANCE_M:
        return None
    # The end polygon must traverse its convex hull exactly, without interior
    # vertices, crossed edges or a concave recess that a cap could misrepresent.
    planar = centered@basis[:2].T
    boundary = ConvexHull(planar).vertices.tolist()
    if len(boundary)!=n:
        return None
    increments = np.diff(np.r_[boundary,boundary[0]])%n
    if not ((increments==1).all() or (increments==n-1).all()):
        return None
    remaining = Counter(tuple(sorted(map(int,face))) for face in mesh.faces)
    for i in range(n):
        j = (i+1)%n
        # Both diagonals are permitted; doubled faces or a missing band are not.
        variants = [((a[i],a[j],b[j]),(a[i],b[j],b[i])),
                    ((a[i],a[j],b[i]),(a[j],b[j],b[i]))]
        chosen = None
        for variant in variants:
            keys = [tuple(sorted(map(int,face))) for face in variant]
            if all(remaining[key]>0 for key in keys):
                chosen = keys;break
        if chosen is None:
            return None
        for key in chosen:
            remaining[key]-=1
    if any(remaining.values()):
        return None
    hull = convex_mesh(mesh.vertices)
    planes = ConvexHull(hull.vertices).equations
    excess = float((mesh.vertices@planes[:,:3].T+planes[:,3]).max())
    if excess>1e-10:
        return None
    return hull,dict(kind='two_congruent_convex_end_loops_complete_side_bands',
        source_faces=len(mesh.faces),source_vertices=len(mesh.vertices),end_loop_vertices=n,
        end_displacement_m=displacement.tolist(),congruence_error_m=error,
        plane_error_m=max(plane_errors),source_hull_plane_excess_m=excess,
        source_triangles_covered=True,prism_interior_covered=True,
        source_geometry_modified=False,physical_approval=False)


def component_prism_covers(mesh):
    """Keep closed parts and replace only recognized open prism walls by hulls.

    Require every component to qualify; never silently drop a residual sheet.
    """
    parts = mesh.split(only_watertight=False,repair=False)
    if sum(len(p.faces) for p in parts)!=len(mesh.faces):
        return None
    covers,certificates = [],[]
    for index,part in enumerate(parts):
        if part.is_watertight:
            covers.append(part)
            continue
        result = convex_prism_enclosure(part)
        if result is None:
            return None
        hull,certificate = result
        covers.append(hull);certificates.append(dict(component_index=index,**certificate))
    if not certificates:
        return None
    return covers,certificates
