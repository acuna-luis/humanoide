#!/usr/bin/env python3
"""Look for counterexamples to ignoring whole moving CAD interface pairs.

Offline, synthetic states only. A found original-surface intersection outside
ALL enlarged reference overlap boxes disproves a reference-only justification
for excluding the whole pair. Failure to find one is never an approval.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import time

import fcl
import numpy as np
import trimesh

import review_clamp_trajectory_optimization as common
from audit_home_interfaces import boundary_object
from cruzr_pico_to_home_owner_gate import JOINT_ORDER, PICO_VARIANTS
from general_home.geometry import RobotGeometry
from general_home.planner import Validator
from general_home.contact_witnesses import triangle_pair_witnesses

WITNESS_TOLERANCE_M = 1e-8


def validated_surface_contacts(mesh_a, mesh_b, pose_b, object_a, object_b, contact_limit=256):
    """Retain FCL positions only when close to BOTH named source triangles.

    FCL's contact.pos can be a triangle vertex outside the actual intersection,
    particularly for coplanar faces. Those unverified positions are not evidence
    of contact at that location. Both objects here are expressed in A's frame.
    """
    result = fcl.CollisionResult()
    fcl.collide(object_a, object_b, fcl.CollisionRequest(num_max_contacts=contact_limit, enable_contact=True), result)
    if not result.contacts:
        return np.empty((0, 3)), dict(reported=0, validated=0, discarded=0, reconstructed=0)
    indices = np.array([[c.b1, c.b2] for c in result.contacts], dtype=int)
    points = np.array([c.pos for c in result.contacts], dtype=float)
    if (not np.isfinite(points).all() or (indices < 0).any()
            or (indices[:, 0] >= len(mesh_a.faces)).any() or (indices[:, 1] >= len(mesh_b.faces)).any()):
        raise ValueError('Invalid FCL source triangle/contact')
    triangles_a = mesh_a.triangles[indices[:, 0]]
    triangles_b = mesh_b.triangles[indices[:, 1]] @ pose_b[:3, :3].T + pose_b[:3, 3]
    distances = np.stack([np.linalg.norm(trimesh.triangles.closest_point(triangles, points)-points, axis=1)
                          for triangles in (triangles_a, triangles_b)], axis=1)
    valid = np.isfinite(distances).all(axis=1) & (distances <= WITNESS_TOLERANCE_M).all(axis=1)
    reconstructed = triangle_pair_witnesses(triangles_a, triangles_b, WITNESS_TOLERANCE_M)
    return np.concatenate([points[valid], reconstructed]), dict(reported=len(points), validated=int(valid.sum()), discarded=int((~valid).sum()),
        reconstructed=len(reconstructed),
        tolerance_m=WITNESS_TOLERANCE_M, may_be_truncated=len(points) >= contact_limit)


def reference_overlap_box(vertices_a, vertices_b_in_a, padding=.002):
    """Outer bound on reference overlap/proximity, in the first link's frame."""
    a, b = np.asarray(vertices_a, dtype=float), np.asarray(vertices_b_in_a, dtype=float)
    if (any(x.ndim != 2 or x.shape[1] != 3 or not len(x) or not np.isfinite(x).all()
            for x in (a, b)) or not np.isfinite(padding) or padding < 0):
        raise ValueError('Invalid reference overlap input')
    low = np.maximum(a.min(axis=0)-padding, b.min(axis=0)-padding)
    high = np.minimum(a.max(axis=0)+padding, b.max(axis=0)+padding)
    return None if (low > high).any() else np.array([low, high])


def outside_all_boxes(points, boxes):
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
        raise ValueError('Invalid witness points')
    inside = np.zeros(len(points), dtype=bool)
    for box in boxes:
        if box is not None:
            box = np.asarray(box, dtype=float)
            if box.shape != (2, 3) or not np.isfinite(box).all() or (box[0] > box[1]).any():
                raise ValueError('Invalid reference box')
            inside |= ((points >= box[0]-2*WITNESS_TOLERANCE_M) & (points <= box[1]+2*WITNESS_TOLERANCE_M)).all(axis=1)
    return points[~inside]


def relative_pose(model, q, first, second):
    poses = common.fk.forward_kinematics(model.joints, dict(model.auxiliary, **dict(zip(JOINT_ORDER, q))))
    return np.linalg.inv(poses[first.link]) @ poses[second.link]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--package-root', type=Path, default=Path(__file__).resolve().parents[2]/'cruzr_s2_description_splint/cruzr_s2_description')
    parser.add_argument('--steps', type=int, default=9, help='Samples per changing joint; not a continuous proof')
    parser.add_argument('--maximum-absolute-angle', type=float, help='Optional narrower synthetic domain in radians, intersected with URDF limits')
    args = parser.parse_args()
    if args.output.exists() or not 3 <= args.steps <= 17:
        parser.error('Choose a new output and 3..17 steps')
    if args.maximum_absolute_angle is not None and (not np.isfinite(args.maximum_absolute_angle) or args.maximum_absolute_angle <= 0):
        parser.error('--maximum-absolute-angle must be finite and positive')
    sources = [Path(__file__), *Path(__file__).with_name('general_home').glob('*.py'),
        Path(__file__).with_name('audit_home_interfaces.py'),
        Path(__file__).with_name('cruzr_pico_to_home_owner_gate.py'),
        Path(common.__file__), Path(common.fk.__file__), Path(common.internal.__file__), Path(common.pico.__file__)]
    hashes = {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    started = time.monotonic()
    model = RobotGeometry(args.package_root/'urdf/cruzr_s2_v1/cruzr_s2_v1.urdf', args.package_root,
        dict(frame_id='base_link', complete=True, objects=[]))
    by_name = {s.name: s for s in model.shapes}
    references = dict(HOME=np.zeros(20), **PICO_VARIANTS)
    lower, upper = model.lower.copy(), model.upper.copy()
    if args.maximum_absolute_angle is not None:
        lower = np.maximum(lower, -args.maximum_absolute_angle)
        upper = np.minimum(upper, args.maximum_absolute_angle)
    failures = Validator(model).failures(np.zeros(20))
    results = []
    for failure in failures:
        names = failure['controlling_joints']
        if not names:
            continue
        if len(names) > 2:
            raise ValueError('Unexpected interface domain; review sampling scope')
        first, second = [by_name[n] for n in failure['pair']]
        a, b = boundary_object(first.source_mesh), boundary_object(second.source_mesh)
        boxes = []
        for q in references.values():
            pose = relative_pose(model, q, first, second)
            vertices = np.asarray(second.source_mesh.vertices) @ pose[:3, :3].T + pose[:3, 3]
            boxes.append(reference_overlap_box(first.source_mesh.vertices, vertices))
        axes = [JOINT_ORDER.index(n) for n in names]
        grid = [np.unique(np.r_[np.linspace(lower[i], upper[i], args.steps), 0.]) for i in axes]
        witness = None
        samples = 0
        contact_counts = dict(reported=0, validated=0, discarded=0, reconstructed=0)
        for values in itertools.product(*grid):
            q = np.zeros(20)
            q[axes] = values
            pose = relative_pose(model, q, first, second)
            b.setTransform(fcl.Transform(pose[:3, :3], pose[:3, 3]))
            points, stats = validated_surface_contacts(first.source_mesh, second.source_mesh, pose, a, b)
            for key in contact_counts:
                contact_counts[key] += stats[key]
            samples += 1
            if len(points):
                novel = outside_all_boxes(points, boxes)
                if len(novel):
                    witness = dict(joint_positions_rad=q.tolist(), point_in_first_link_m=novel[0].tolist(),
                        frame_id=first.link, reference_box_padding_m=.002,
                        checked_against_both_source_triangles=True, witness_tolerance_m=WITNESS_TOLERANCE_M,
                        scope='CAD surface counterexample; not a measured physical contact')
                    break
        result = dict(pair=failure['pair'], controlling_joints=names, samples=samples,
            source_contact_validation=contact_counts,
            reference_boxes_in_first_link_m=[None if box is None else box.tolist() for box in boxes],
            counterexample=witness, exemption_authorized=False,
            status='WHOLE_PAIR_EXCLUSION_HAS_NOVEL_CAD_CONTACT' if witness else 'NO_COUNTEREXAMPLE_FOUND_NOT_PROVEN_SAFE')
        results.append(result)
        print(json.dumps(dict(pair=result['pair'], status=result['status'], samples=samples)), flush=True)
    if not model.source_files_unchanged() or any(hashlib.sha256(Path(p).read_bytes()).hexdigest() != sha for p, sha in hashes.items()):
        raise ValueError('Sources changed during audit')
    report = dict(schema='cruzr-interface-exclusion-counterexamples-v1', interfaces=results,
        reference_order=list(references), joint_order=JOINT_ORDER, model=model.diagnostics,
        synthetic_domain=dict(lower_rad=lower.tolist(), upper_rad=upper.tolist(),
            origin='CAD URDF limits, optionally intersected with the requested absolute angle bound',
            active_motion_limits_verified=False),
        source_sha256=dict(model.manifest, **hashes),
        counterexample_count=sum(r['counterexample'] is not None for r in results),
        physical_approval=False, installable=False, movement_commands=0,
        scope='synthetic bounded grid seeking negative examples; never proves absence of collision',
        duration_seconds=time.monotonic()-started)
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
