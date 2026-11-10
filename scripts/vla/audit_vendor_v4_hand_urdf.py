#!/usr/bin/env python3
"""Inspecciona el modelo v4 de un ZIP local, sin extraer ni controlar el robot.

El auditor describe lo que declara el proveedor: no verifica montaje, versiones,
movimiento ni correspondencia con los siete ejes publicados en esta unidad.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import posixpath
import sys
import xml.etree.ElementTree as ET
import zipfile

from prepare_ball_observations import RIGHT_HAND

MAX_URDF = 256 * 1024
MAX_MESH = 64 * 1024 * 1024
SIDES = ('left', 'right')


def sha_stream(stream):
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
        digest.update(chunk)
    return digest.hexdigest()


def side_model(archive, names, side):
    package = f'ubt_{side}_hand_v4_evt3_description'
    suffix = f'/{package}/urdf/hand4_evt3/hand4_evt3.urdf'
    matches = [name for name in names if name.endswith(suffix)]
    if len(matches) != 1:
        raise ValueError(f'{side}: missing or ambiguous URDF')
    path = matches[0]
    info = archive.getinfo(path)
    if info.file_size > MAX_URDF:
        raise ValueError('URDF too large')
    xml = archive.read(info)
    root = ET.fromstring(xml)
    if root.tag != 'robot':
        raise ValueError('URDF root is not a robot')
    links = root.findall('link')
    link_names = [link.get('name') for link in links]
    if any(not n for n in link_names) or len(set(link_names)) != len(link_names):
        raise ValueError('link names missing or duplicated')
    mesh_hashes = {}
    prefix = path[:-len(f'urdf/hand4_evt3/hand4_evt3.urdf')]
    package_uri = f'package://{package}/'
    collisions = 0
    for link in links:
        collisions += len(link.findall('collision'))
        for mesh in link.findall('./visual/geometry/mesh') + link.findall('./collision/geometry/mesh'):
            uri = mesh.get('filename', '')
            if not uri.startswith(package_uri):
                raise ValueError('mesh URI outside the hand package')
            relative = uri[len(package_uri):]
            if relative.startswith('/') or posixpath.normpath(relative) != relative or '..' in relative.split('/'):
                raise ValueError('invalid mesh path')
            member = prefix + relative
            if member not in names or archive.getinfo(member).file_size > MAX_MESH:
                raise ValueError('mesh missing or too large: ' + relative)
            if relative not in mesh_hashes:
                with archive.open(member) as stream:
                    mesh_hashes[relative] = sha_stream(stream)
    joints = []
    parents = {}
    joint_names = set()
    for joint in root.findall('joint'):
        name, kind = joint.get('name'), joint.get('type')
        parent, child = joint.find('parent'), joint.find('child')
        if (not name or name in joint_names or not kind or parent is None or child is None or
                parent.get('link') not in link_names or child.get('link') not in link_names or
                child.get('link') in parents):
            raise ValueError('invalid or duplicated joint topology')
        joint_names.add(name)
        parents[child.get('link')] = parent.get('link')
        limit = joint.find('limit')
        limits = None
        if limit is not None:
            limits = {}
            for key in ('lower', 'upper', 'velocity', 'effort'):
                if key in limit.attrib:
                    value = float(limit.get(key))
                    if not math.isfinite(value):
                        raise ValueError('nonfinite URDF limit')
                    limits[key] = value
        mimic = joint.find('mimic')
        joints.append({'name': name, 'type': kind, 'parent': parent.get('link'),
                       'child': child.get('link'), 'limits': limits,
                       'mimic': None if mimic is None else dict(mimic.attrib)})
    roots = set(link_names) - set(parents)
    if len(roots) != 1:
        raise ValueError('hand model must have exactly one root')
    root_link = next(iter(roots))
    for name in link_names:
        visited = set()
        current = name
        while current in parents:
            if current in visited:
                raise ValueError('cyclic URDF topology')
            visited.add(current)
            current = parents[current]
        if current != root_link:
            raise ValueError('disconnected URDF topology')
    observed = RIGHT_HAND if side == 'right' else [n.replace('right_', 'left_', 1) for n in RIGHT_HAND]
    return {'side': side, 'archive_member': path, 'urdf_sha256': hashlib.sha256(xml).hexdigest(),
            'root_link': root_link, 'links': len(links), 'collision_elements': collisions,
            'joints': joints, 'revolute_joints': sum(j['type'] == 'revolute' for j in joints),
            'mimic_joints': sum(j['mimic'] is not None for j in joints),
            'referenced_mesh_sha256': mesh_hashes, 'observed_topic_names': observed,
            'exact_name_matches': sorted(set(observed) & joint_names),
            'topic_to_urdf_mapping_verified': False, 'mounting_verified': False}


def inspect(path):
    path = Path(path)
    with path.open('rb') as stream:
        archive_sha = sha_stream(stream)
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or len(names) > 5000:
            raise ValueError('duplicated or excessive ZIP members')
        models = [side_model(archive, set(names), side) for side in SIDES]
    return {'schema': 'cruzr_vendor_v4_hand_urdf_audit_v1', 'zip_sha256': archive_sha,
            'models': models, 'physical_control_qualified': False,
            'physical_commands_generated': 0,
            'limitations': ['vendor EVT3 model, not established as matching the installed hands',
                            'URDF limits and geometry are not validated robot safety limits',
                            'no topic-to-model mapping, finger coupling or mounting calibration',
                            'no force/current units, actuator command or stopping procedure verified']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path, help='ZIP original del proveedor (sólo lectura)')
    args = parser.parse_args(argv)
    try:
        print(json.dumps(inspect(args.archive), ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, ET.ParseError, zipfile.BadZipFile) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
