"""Complete URDF proximity model; fixed assemblies only, no moving-pair exemptions.

Closed meshes use FCL BVH distance plus solid containment checks. Open meshes
use a convex enclosure, explicitly reported, so missing faces cannot create
an artificial route through the part. Sources are never modified.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections import Counter
import hashlib
import itertools
from pathlib import Path
import xml.etree.ElementTree as ET

import fcl
import numpy as np
import trimesh

import review_clamp_trajectory_optimization as common
from cruzr_pico_to_home_owner_gate import JOINT_ORDER
from .prism_enclosure import component_prism_covers


def finite_vector(value, size, label):
    if not isinstance(value, (list, tuple, np.ndarray)) or len(value) != size:
        raise ValueError(f'{label}: expected {size} values')
    if any(isinstance(x, (bool, np.bool_)) or not isinstance(x, (int, float, np.number)) for x in value):
        raise ValueError(label + ': nonnumeric value')
    out = np.asarray(value, dtype=float)
    if out.shape != (size,) or not np.isfinite(out).all():
        raise ValueError(label + ': nonfinite value')
    return out


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@dataclass
class Shape:
    name: str
    link: str
    mesh: trimesh.Trimesh
    obj: fcl.CollisionObject
    solid_points: np.ndarray
    convex: bool
    pose: np.ndarray
    components: list
    representation: str
    geometry_error_m: float = 0.0
    source_mesh: object = None
    enclosure_certificate: object = None

    @classmethod
    def from_mesh(cls, name, link, mesh):
        if len(mesh.faces) == 0 or not np.isfinite(mesh.vertices).all():
            raise ValueError('Empty/nonfinite geometry: '+name)
        representation = 'closed_mesh'
        geometry_error = 0.0
        enclosure_certificate = None
        source_mesh = mesh
        if not mesh.is_watertight:
            # CAD assemblies can share an edge between otherwise closed solids.
            # Keep the exact triangle multiset and separate their topology. Do
            # not repair holes, weld coordinates or discard small components.
            parts = mesh.split(only_watertight=False, repair=False)
            if parts and all(part.is_watertight for part in parts):
                separated = trimesh.util.concatenate(parts)
                if (separated.is_watertight and
                        Counter(t.tobytes() for t in mesh.triangles) ==
                        Counter(t.tobytes() for t in separated.triangles)):
                    mesh = separated
                    representation = 'closed_component_union_exact_triangles'
        if not mesh.is_watertight:
            # A bounded numeric seam repair, not general hole filling. Retain
            # every triangle, measure its vertex displacement, and accept only
            # an entirely closed union. 10 nm is far below the physical error
            # budget, but it is still subtracted from every distance bound.
            welded = mesh.copy()
            welded.merge_vertices(digits_vertex=6)
            displacement = float(np.linalg.norm(welded.triangles-mesh.triangles, axis=2).max())
            if displacement <= 1e-8:
                parts = welded.split(only_watertight=False, repair=False)
                if parts and all(part.is_watertight for part in parts):
                    separated = trimesh.util.concatenate(parts)
                    if (separated.is_watertight and
                            Counter(t.tobytes() for t in welded.triangles) ==
                            Counter(t.tobytes() for t in separated.triangles)):
                        mesh = separated
                        geometry_error = displacement
                        representation = 'closed_component_union_bounded_numeric_weld'
        if not mesh.is_watertight:
            # Some exports omit only the two end caps of complete bolt/shaft
            # sidewalls. Recognize their entire convex-prism topology, retain
            # all other closed components, and enclose each such prism locally.
            # Any residual unrecognized sheet keeps the whole-link fallback.
            enclosed = component_prism_covers(mesh)
            if enclosed is not None:
                parts,enclosure_certificate = enclosed
                mesh = trimesh.util.concatenate(parts)
                if not mesh.is_watertight:
                    raise ValueError('Certified component union is not closed: '+name)
                representation = 'closed_components_with_certified_prism_enclosures'
        # Non-watertight surfaces have no reliable inside/outside. The hull
        # contains the source surface and its possible enclosed volume.
        convex = not mesh.is_watertight
        if convex:
            source = mesh
            mesh = source.convex_hull
            representation = 'convex_enclosure'
            if not mesh.is_volume:
                # Some CAD exports yield a degenerate convex triangulation.
                # Fall back to a complete box, never drop those faces/parts.
                mesh = trimesh.creation.box(extents=source.extents)
                mesh.apply_translation(source.bounds.mean(axis=0))
                representation = 'box_enclosure'
                if not mesh.is_volume:
                    raise ValueError('Cannot construct solid enclosure: '+name)
            vertices = np.asarray(mesh.vertices, dtype=np.float64)
            faces = np.c_[np.full(len(mesh.faces), 3), mesh.faces].ravel().astype(np.int32)
            model = fcl.Convex(vertices, len(mesh.faces), faces)
            points = np.empty((0, 3))
            components = [mesh]
        else:
            model = fcl.BVHModel()
            model.beginModel(len(mesh.vertices), len(mesh.faces))
            model.addSubModel(np.asarray(mesh.vertices), np.asarray(mesh.faces, dtype=np.int32))
            model.endModel()
            # One point from each disconnected boundary component is enough
            # to detect nesting after surface intersections have been ruled out.
            components = mesh.split(only_watertight=False, repair=False)
            points = np.array([component.vertices[0] for component in components])
        return cls(name, link, mesh, fcl.CollisionObject(model), points, convex,
                   np.eye(4), components, representation, geometry_error, source_mesh,
                   enclosure_certificate)

    def place(self, pose):
        self.pose = pose
        self.obj.setTransform(fcl.Transform(pose[:3, :3], pose[:3, 3]))

    def contains_world(self, points):
        if not len(points):
            return False
        local = (points-self.pose[:3, 3]) @ self.pose[:3, :3]
        # Treat disconnected solids as a union, not the parity/XOR of shells.
        # Filling a nested cavity is conservative; accepting an overlapping
        # pair of closed shells as empty would not be.
        return any(bool(component.contains(local).any()) for component in self.components)


def solid_distance(a, b):
    result = fcl.CollisionResult()
    if fcl.collide(a.obj, b.obj, fcl.CollisionRequest(), result):
        return 0.0
    result = fcl.DistanceResult()
    value = float(fcl.distance(a.obj, b.obj, fcl.DistanceRequest(), result))
    if not np.isfinite(value):
        raise ValueError('Nonfinite collision distance')
    if value <= 0:
        return 0.0
    # FCL mesh queries measure boundary distance and can miss a solid fully
    # contained in another. Test representatives both ways, including convex
    # objects against mesh boundaries (convex/convex is covered by FCL).
    if not (a.convex and b.convex):
        for first, second in ((a, b), (b, a)):
            points = first.solid_points if not first.convex else first.mesh.vertices[:1]
            world = points @ first.pose[:3, :3].T + first.pose[:3, 3]
            if second.contains_world(world):
                return 0.0
    return max(0., value-a.geometry_error_m-b.geometry_error_m)


class RobotGeometry:
    def __init__(self, urdf, package_root, scene, auxiliary=None):
        self.urdf = Path(urdf).resolve()
        package_root = Path(package_root).resolve()
        self.manifest = {str(self.urdf): digest(self.urdf)}
        tree = ET.parse(self.urdf).getroot()
        links = [link.get('name') for link in tree.findall('link')]
        if len(links) != len(set(links)) or not links or any(not name for name in links):
            raise ValueError('Duplicate/empty model links')
        if any(j.find('mimic') is not None for j in tree.findall('joint')):
            raise ValueError('Mimic joints require an explicit coupled model')
        self.joints = common.model_joints(self.urdf)
        names = [j['name'] for j in self.joints]
        if len(names) != len(set(names)) or any(not name for name in names) or any(n not in names for n in JOINT_ORDER):
            raise ValueError('Duplicate/missing model joints')
        if any(j['parent'] not in links or j['child'] not in links for j in self.joints):
            raise ValueError('Joint references an unknown link')
        if len({j['child'] for j in self.joints}) != len(self.joints):
            raise ValueError('Multiple parents for a link')
        roots = set(links)-{j['child'] for j in self.joints}
        if roots != {'base_link'}:
            raise ValueError('Expected base_link as sole root')
        limits = {j.get('name'): j.find('limit') for j in tree.findall('joint')}
        self.lower = np.array([float(limits[n].get('lower')) for n in JOINT_ORDER])
        self.upper = np.array([float(limits[n].get('upper')) for n in JOINT_ORDER])
        if (not np.isfinite(self.lower).all() or not np.isfinite(self.upper).all()
                or (self.lower >= self.upper).any() or (self.lower > 0).any() or (self.upper < 0).any()):
            raise ValueError('Invalid joint limits or HOME outside limits')
        if any(j['type'] != 'revolute' for j in self.joints if j['name'] in JOINT_ORDER):
            raise ValueError('20 controlled joints must be revolute for radius bounds')
        if any(j['type'] not in ('fixed', 'revolute', 'continuous') for j in self.joints):
            raise ValueError('Unsupported joint type for global radius bounds')
        if any(np.linalg.norm(j['axis']) <= 1e-12 for j in self.joints if j['type'] != 'fixed'):
            raise ValueError('Zero joint axis')
        extra = {j['name'] for j in self.joints if j['type'] != 'fixed'}-set(JOINT_ORDER)
        auxiliary = {} if auxiliary is None else auxiliary
        if not isinstance(auxiliary, dict) or set(auxiliary)-extra:
            raise ValueError('Unknown auxiliary joint')
        self.auxiliary = {name: float(finite_vector([value], 1, name)[0]) for name, value in auxiliary.items()}
        self.assumed_auxiliary = sorted(extra-set(auxiliary))
        self.auxiliary.update({name: 0.0 for name in self.assumed_auxiliary})
        for joint in self.joints:
            if joint['name'] in extra and joint['type'] == 'revolute':
                limit = limits[joint['name']]
                lo, hi = float(limit.get('lower')), float(limit.get('upper'))
                if not np.isfinite([lo, hi]).all() or not lo <= self.auxiliary[joint['name']] <= hi:
                    raise ValueError('Auxiliary joint outside limits: '+joint['name'])
        rigid = {'base_link': 'base_link'}
        pending = list(self.joints)
        while pending:
            available = [j for j in pending if j['parent'] in rigid]
            if not available:
                raise ValueError('Disconnected/cyclic URDF')
            for joint in available:
                rigid[joint['child']] = rigid[joint['parent']] if joint['type'] == 'fixed' else joint['child']
                pending.remove(joint)
        self.shapes = []
        visual = []
        missing = []
        for link in tree.findall('link'):
            name = link.get('name')
            parts = link.findall('collision')
            if not parts:
                parts = link.findall('visual')
                (visual if parts else missing).append(name)
            for index, part in enumerate(parts):
                geometry = part.find('geometry')
                mesh_node = geometry.find('mesh')
                if mesh_node is not None:
                    prefix = 'package://cruzr_s2_description/'
                    raw = mesh_node.get('filename', '')
                    if not raw.startswith(prefix):
                        raise ValueError('Unsupported mesh URI: '+raw)
                    path = (package_root/raw[len(prefix):]).resolve()
                    if not path.is_relative_to(package_root):
                        raise ValueError('Mesh escapes package root')
                    self.manifest[str(path)] = digest(path)
                    mesh = trimesh.load_mesh(path, process=True)
                    scale = common.fk.xyz(mesh_node.get('scale'), (1, 1, 1))
                    if (scale <= 0).any():
                        raise ValueError('Nonpositive mesh scale')
                    mesh.apply_scale(scale)
                elif geometry.find('box') is not None:
                    size = common.fk.xyz(geometry.find('box').get('size'))
                    if (size <= 0).any():
                        raise ValueError('Nonpositive box size')
                    mesh = trimesh.creation.box(extents=size)
                else:
                    raise ValueError('Unsupported collision geometry on '+name)
                mesh.apply_transform(common.fk.origin_transform(part.find('origin')))
                self.shapes.append(Shape.from_mesh(f'{name}#{index}', name, mesh))
        self.robot_count = len(self.shapes)
        if not self.robot_count:
            raise ValueError('No collision geometry')
        self.pairs = []
        ignored_rigid = []
        for a, b in itertools.combinations(range(self.robot_count), 2):
            if rigid[self.shapes[a].link] == rigid[self.shapes[b].link]:
                ignored_rigid.append([self.shapes[a].name, self.shapes[b].name])
            else:
                self.pairs.append((a, b))
        if not isinstance(scene, dict) or scene.get('frame_id') != 'base_link':
            raise ValueError('Scene must be expressed in base_link')
        if not isinstance(scene.get('objects'), list) or scene.get('complete') is not True:
            raise ValueError('Scene completeness/objects must be provided explicitly')
        identifiers = set()
        for obj in scene['objects']:
            name = obj.get('id')
            if not isinstance(name, str) or not name or name in identifiers:
                raise ValueError('Duplicate/empty scene object ID')
            identifiers.add(name)
            if obj.get('type') != 'box':
                raise ValueError('Only explicit scene boxes are supported')
            size = finite_vector(obj.get('size_m'), 3, name)
            center = finite_vector(obj.get('center_m'), 3, name)
            rpy = finite_vector(obj.get('rpy_rad'), 3, name)
            if (size <= 0).any():
                raise ValueError('Nonpositive obstacle size')
            mesh = trimesh.creation.box(extents=size)
            mesh.apply_transform(common.fk.transform(center, common.fk.rotation_rpy(rpy)))
            self.shapes.append(Shape.from_mesh('scene:'+name, 'base_link', mesh))
            self.pairs.extend((i, len(self.shapes)-1) for i in range(self.robot_count))
        error_bounds = [s.mesh.bounds + np.array([[-1], [1]])*s.geometry_error_m for s in self.shapes]
        self.weights = np.array([common.pair_radii(self.joints, self.shapes[a].link,
            error_bounds[a], self.shapes[b].link, error_bounds[b])
            for a, b in self.pairs]).reshape(-1, 20)
        self.labels = [[self.shapes[a].name, self.shapes[b].name] for a, b in self.pairs]
        self.pair_details = [dict(
            scope='invariant_for_fixed_auxiliary_and_base' if not np.any(weight) else 'changes_with_controlled_joints',
            controlling_joints=[name for name, radius in zip(JOINT_ORDER, weight) if radius > 0],
            representations=[self.shapes[a].representation, self.shapes[b].representation],
            numeric_geometry_error_m=self.shapes[a].geometry_error_m+self.shapes[b].geometry_error_m)
            for (a, b), weight in zip(self.pairs, self.weights)]
        self.diagnostics = dict(links=len(links), robot_shapes=self.robot_count,
            checked_pairs=len(self.pairs), rigid_internal_pairs=ignored_rigid,
            visual_fallback=visual, links_without_geometry=missing,
            convex_enclosures=[s.name for s in self.shapes if s.convex],
            geometry_representation={s.name:s.representation for s in self.shapes},
            prism_enclosure_certificates={s.name:s.enclosure_certificate for s in self.shapes if s.enclosure_certificate},
            numeric_geometry_error_m={s.name:s.geometry_error_m for s in self.shapes if s.geometry_error_m},
            assumed_auxiliary_zero=self.assumed_auxiliary,
            nonpositive_velocity_limits=[n for n in JOINT_ORDER if
                not np.isfinite(float(limits[n].get('velocity', '0')))
                or float(limits[n].get('velocity', '0')) <= 0])

    def distances(self, q):
        q = finite_vector(q, 20, 'joint positions')
        if (q < self.lower).any() or (q > self.upper).any():
            raise ValueError('Joint position outside model limits')
        poses = common.fk.forward_kinematics(self.joints, dict(self.auxiliary, **dict(zip(JOINT_ORDER, q))))
        for shape in self.shapes[:self.robot_count]:
            shape.place(poses[shape.link])
        bounds = []
        for shape in self.shapes:
            points = common.fk.apply(common.fk.corners(*shape.mesh.bounds), shape.pose)
            bounds.append((points.min(axis=0), points.max(axis=0)))
        answer = []
        for a, b in self.pairs:
            low_a, high_a = bounds[a]
            low_b, high_b = bounds[b]
            gap = float(np.linalg.norm(np.maximum(0, np.maximum(low_a-high_b, low_b-high_a))))
            # Far AABB separation is already a conservative lower bound.
            answer.append(max(0., gap-self.shapes[a].geometry_error_m-self.shapes[b].geometry_error_m)
                          if gap > .04 else solid_distance(self.shapes[a], self.shapes[b]))
        return np.asarray(answer)

    def source_files_unchanged(self):
        return all(digest(path) == expected for path, expected in self.manifest.items())
