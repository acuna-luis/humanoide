"""Offline installed-clamp profile; missing registration remains explicit."""
import json
from pathlib import Path
from audit_clamp_pessimistic_screen import ROOT, URDF, ARCHIVE, fk
from build_clamp_simplified_model import build

CONTRACT = ROOT / 'config/clamp_mount_requalification.json'


def descendants(joints, parent):
    found = set()
    pending = [parent]
    while pending:
        current = pending.pop()
        for joint in joints:
            if joint['parent'] == current and joint['child'] not in found:
                found.add(joint['child'])
                pending.append(joint['child'])
    return found


def load():
    joints, boxes, meshes = fk.load_robot(URDF, ARCHIVE)
    contract = json.loads(CONTRACT.read_text())
    nominal = build(contract)
    if nominal['nominal_full_tool_envelope'] is None:
        raise ValueError('missing full nominal tool envelope')
    removed = set()
    for side in ('L', 'R'):
        root = side+'_pgc_base_link'
        if root not in boxes:
            raise ValueError('historical gripper root missing: '+root)
        removed |= {root} | descendants(joints, root)
    tools = {}
    for side in ('L', 'R'):
        mount = contract['mounts'][side]
        tools[side] = dict(parent_frame=side+'_sixforce_link',
            descriptive_envelope=nominal['nominal_full_tool_envelope'],
            descriptive_primitives=nominal['primitives'],
            coordinate_order=nominal['coordinate_order'],
            coordinate_warning=nominal['coordinate_warning'],
            translation_m=mount['translation_m'], rotation_matrix=mount['rotation_matrix'],
            uncertainty_m=mount['uncertainty_m'],
            status='NOMINAL_ENVELOPE_NOT_REGISTERED', world_geometry_available=False)
        # No guessed mounting transform or silent identity transform.
        if mount['translation_m'] is not None or mount['rotation_matrix'] is not None:
            raise ValueError('registration supplied: qualified transform loader required')
    kept_joints = [j for j in joints if j['child'] not in removed]
    return kept_joints, {n:b for n,b in boxes.items() if n not in removed}, \
        {n:t for n,t in meshes.items() if n not in removed}, dict(
            profile='installed_clamps_incomplete_registration', removed_historical_links=sorted(removed),
            tools=tools, collision_coverage_complete=False, physical_authorized=False,
            robot_connections=0, movement_commands=0)
