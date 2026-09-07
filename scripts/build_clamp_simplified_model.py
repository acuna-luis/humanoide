#!/usr/bin/env python3
"""Build a LOCAL descriptive clamp model, never a qualified ROS collision object."""
import argparse
import hashlib
import json
import math
from pathlib import Path

from audit_clamp_mount_requalification import reported_plate_volume

ROOT = Path(__file__).resolve().parents[1]


def build(contract):
    if contract.get('schema') != 'cruzr-clamp-requalification-v1':
        raise ValueError('unexpected contract schema')
    d = contract['reported_dimensions']
    volume = reported_plate_volume(d)
    if volume['status'] != 'REPORTED_PLATE_VOLUME_NOT_FULL_TOOL':
        raise ValueError('incomplete or inconsistent plate dimensions')
    u = volume['lateral_plain_plate_bounds_m']
    v = volume['vertical_bounds_from_mount_plane_m']
    depth = volume['depth_from_sensor_axis_toward_pads_m']
    total = d.get('total_tool_depth_from_pad_face_m')
    envelope = None
    if total is not None:
        if type(total) not in (int, float) or not math.isfinite(total) or total < d['plate_with_pads_thickness_m']:
            raise ValueError('invalid total tool depth')
        if d.get('support_contained_in_reported_other_margins') is True:
            envelope = {
                'bounds_m': [[u[0], v[0], d['axis_to_pad_face_m']-total],
                             [u[1]+d['tab_projection_from_plate_edge_m'], v[1], depth[1]]],
                'source': d.get('total_tool_envelope_report_source'),
                'qualification': 'nominal_operator_report_not_independent_measurement',
                'includes_support_and_fasteners_by_report': True,
                'measurement_uncertainty_m': d.get('measurement_uncertainty_m'),
                'bilateral_scope': d.get('total_tool_envelope_bilateral_scope'),
            }
    return {
        'schema': 'clamp-descriptive-primitives-v1',
        'status': 'NOMINAL_TOOL_ENVELOPE_UNREGISTERED' if envelope else 'PARTIAL_MODEL_NOT_REGISTERED',
        'nominal_full_tool_envelope': envelope,
        'applies_to_sides_by_operator_report': ['L', 'R'],
        'coordinate_order': ['u_toward_tabs', 'v_upper_from_mount_plane',
                             'depth_sensor_axis_toward_pads'],
        'coordinate_warning': 'descriptive scalar coordinates; not a verified right-handed frame or ROS transform',
        'primitives': [
            {'name': 'plate_and_pads', 'type': 'box',
             'bounds_m': [[u[0], v[0], depth[0]], [u[1], v[1], depth[1]]],
             'evidence': d['source'], 'qualification': 'nominal_operator_dimensions'},
            {'name': 'whole_tab_edge_candidate', 'type': 'box',
             'bounds_m': [[u[1], v[0], depth[0]],
                          [u[1]+d['tab_projection_from_plate_edge_m'], v[1], depth[1]]],
             'qualification': 'conditional_envelope_not_measured_tab_shape',
             'condition': 'both tabs must lie within the plate height and depth interval'},
            {'name': 'support_braces_and_fasteners', 'type': 'unresolved_envelope',
             'bounds_m': None, 'qualification': 'visible_in_photos_dimensions_not_bounded'},
        ],
        'missing_for_full_tool': ([] if envelope else [
            'support/fastener min and max extent in each descriptive coordinate',
            'tab height/depth containment verification']) + [
            'measurement uncertainty bound',
            'registration of these coordinates to each sixforce frame'],
        'manufacturer_clamp_cad_required': False,
        'full_tool_containment_proven': False,
        'ros_collision_export_allowed': False,
        'physical_authorized': False,
        'robot_connections': 0, 'movement_commands': 0,
    }


def drawing(model):
    """Two metric projections of the reported plate; no invented support outline."""
    lo, hi = model['primitives'][0]['bounds_m']
    tab_hi = model['primitives'][1]['bounds_m'][1][0]
    u0, v0, z0 = [x*1000 for x in lo]
    u1, v1, z1 = [x*1000 for x in hi]
    tab_hi *= 1000
    scale = 3
    top = 155
    bottom = top+(v1-v0)*scale
    datum = top+v1*scale
    front = 110
    axis = 585
    plate_x = axis+z0*scale
    pad_x = axis+z1*scale
    envelope = model.get('nominal_full_tool_envelope')
    outline = ''
    support_label = '<text x="600" y="365">Soporte negro:</text><text x="600" y="392">sin contorno</text><text x="600" y="419">métrico cerrado</text>'
    note = f'El soporte NO se supone contenido entre 0 y {z0:g}: sus extremos siguen pendientes.'
    title = 'Abrazaderas L/R — modelo propio parcial, cotas en mm'
    if envelope:
        rear = envelope['bounds_m'][0][2]*1000
        total = z1-rear
        outline = f'<rect x="{axis+rear*scale}" y="{top}" width="{total*scale}" height="{bottom-top}" fill="none" stroke="#21826c" stroke-width="3" stroke-dasharray="8 5"/><text x="{axis+rear*scale-10}" y="500">{rear:g}</text>'
        support_label = f'<text x="600" y="365">T = {total:g}</text><text x="600" y="392">Envolvente</text><text x="600" y="419">nominal total</text>'
        note = f'Verde: envolvente total según medición y contención declaradas; extremo trasero {rear:g} mm.'
        title = 'Abrazaderas L/R — envolvente nominal propia, cotas en mm'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="650" viewBox="0 0 1100 650">
<rect width="1100" height="650" fill="white"/>
<style>text{{font-family:sans-serif;font-size:17px;fill:#172636}} .dim{{stroke:#526477;stroke-width:1}} .ref{{stroke:#526477;stroke-dasharray:6 5}}</style>
<text x="35" y="35" font-size="23">{title}</text>
<text x="35" y="65">Azul: placa medida. Naranja: reserva lateral de patitas, condicionada.</text>
<text x="110" y="110">Vista de la placa</text><text x="585" y="110">Perfil de profundidad</text>
<rect x="{front}" y="{top}" width="{(u1-u0)*scale}" height="{bottom-top}" fill="#b7dcf5" stroke="#12699e"/>
<rect x="{front+(u1-u0)*scale}" y="{top}" width="{(tab_hi-u1)*scale}" height="{bottom-top}" fill="#ffe0a8" stroke="#b26900" stroke-dasharray="5 4"/>
<line x1="{front-u0*scale}" x2="{front-u0*scale}" y1="135" y2="480" class="ref"/>
<line x1="85" x2="375" y1="{datum}" y2="{datum}" class="ref"/>
<text x="85" y="{datum-8}">plano de unión</text>
<text x="45" y="210">{v1:g}</text><text x="45" y="385">{-v0:g}</text>
<text x="155" y="490">{u1-u0:g} + {tab_hi-u1:g} = {tab_hi-u0:g}</text>
<text x="110" y="520">Altura total: {v1-v0:g}</text>
<rect x="{plate_x}" y="{top}" width="{(z1-z0)*scale}" height="{bottom-top}" fill="#b7dcf5" stroke="#12699e"/>
{outline}
<line x1="{axis}" x2="{axis}" y1="135" y2="480" class="ref"/>
<line x1="{axis}" x2="{pad_x}" y1="{datum}" y2="{datum}" class="ref"/>
<text x="565" y="500">Eje: 0</text><text x="{plate_x-15}" y="500">{z0:g}</text><text x="{pad_x-10}" y="500">{z1:g}</text>
<text x="{plate_x-3}" y="135">F = {z1-z0:g}</text>
{support_label}
<text x="585" y="530">A = {z1:g}; A − F = {z0:g}</text>
<text x="35" y="575">{note}</text>
<text x="35" y="607">Sin transformación ROS ni tolerancia validada. NO demuestra separación del torso ni autoriza HOME.</text>
</svg>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract', type=Path, default=ROOT/'config/clamp_mount_requalification.json')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    raw = args.contract.read_bytes()
    model = build(json.loads(raw))
    model['contract_sha256'] = hashlib.sha256(raw).hexdigest()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir/'model.json').write_text(json.dumps(model, indent=2, allow_nan=False)+'\n')
    (args.output_dir/'plate_projections.svg').write_text(drawing(model))
    print(model['status']+': '+str(args.output_dir))
    return 0  # Artifact creation only, never a qualification result.


if __name__ == '__main__':
    raise SystemExit(main())
