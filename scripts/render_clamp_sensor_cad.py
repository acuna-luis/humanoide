#!/usr/bin/env python3
"""Render vendor sensor STL orthographic SVG, without editing photos or SDK.

Painter sorting is an illustration only, not a visibility/collision proof.
Both sides of the z axis are shown; no physical mounting orientation is chosen.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zipfile

from audit_clamp_sensor_reference import ARCHIVE, inspect


def render(data, side, direction):
    count = struct.unpack_from('<I', data, 80)[0]
    triangles = []
    for i in range(count):
        tri = [struct.unpack_from('<3f', data,84+50*i+12+12*j) for j in range(3)]
        triangles.append(tri)
    # Viewing from +z: x right/y up. From -z: x left/y up (not a 3D reflection).
    triangles.sort(key=lambda tri: direction*sum(p[2] for p in tri))
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="740" viewBox="0 0 900 740">',
           '<rect width="900" height="740" fill="white"/>',
           f'<text x="30" y="35" font-size="22">{side}_sixforce_link — visto desde {"+" if direction>0 else "-"}Z</text>',
           '<text x="30" y="65" font-size="16">CAD proveedor, sin soporte clamp; NO montaje validado</text>']
    for tri in triangles:
        a = [tri[1][k]-tri[0][k] for k in range(3)]
        b = [tri[2][k]-tri[0][k] for k in range(3)]
        n = [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
        norm = sum(v*v for v in n)**.5
        shade = int(100+130*abs(n[2])/norm) if norm else 100
        pts = ' '.join(f'{450+direction*p[0]*9000:.3f},{370-p[1]*9000:.3f}' for p in tri)
        out.append(f'<polygon points="{pts}" fill="rgb({shade},{shade},{shade})" stroke="rgb({shade},{shade},{shade})" stroke-width="0.15"/>')
    out.extend(['<path d="M 60 665 h 180" stroke="black" stroke-width="3"/>',
                '<text x="60" y="700" font-size="18">20 mm CAD (escala de dibujo)</text>',
                '<text x="450" y="700" font-size="16">Proyección ortográfica; no fotografía</text>', '</svg>'])
    return '\n'.join(out)+'\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    ref = inspect(ARCHIVE)
    args.output_dir.mkdir(exist_ok=False)
    artifacts = {}
    with zipfile.ZipFile(ARCHIVE) as archive:
        for side, spec in ref['sides'].items():
            data = archive.read(spec['mesh_member'])
            for direction in (1,-1):
                name = side+('_plus_z.svg' if direction>0 else '_minus_z.svg')
                payload = render(data,side,direction)
                with (args.output_dir/name).open('x') as out:
                    out.write(payload)
                artifacts[name] = hashlib.sha256(payload.encode()).hexdigest()
    report = dict(status='CAD_ILLUSTRATION_ONLY', archive_sha256=ref['archive_sha256'],
                  artifacts=artifacts, physical_authorized=False, robot_connections=0,
                  movement_commands=0, limitations=['approximate_painter_visibility',
                  'no_photo_registration', 'no_passive_clamp_mesh'])
    with (args.output_dir/'manifest.json').open('x') as out:
        json.dump(report,out,indent=2)
        out.write('\n')
    print(args.output_dir)
