"""Comprobaciones offline del análisis ZIP de los modelos de mano."""
import json
from pathlib import Path
import tempfile
import unittest
import warnings
import zipfile

import audit_vendor_v4_hand_urdf as audit


def hand(side):
    prefix = 'L' if side == 'left' else 'R'
    package = f'ubt_{side}_hand_v4_evt3_description'
    mesh = f'package://{package}/meshes/hand4_evt3/base.STL'
    xml = f'''<robot name="test">
      <link name="{prefix}_base"><collision><geometry><mesh filename="{mesh}"/></geometry></collision></link>
      <link name="{prefix}_finger"/>
      <joint name="{prefix}_joint" type="revolute"><parent link="{prefix}_base"/>
        <child link="{prefix}_finger"/><limit lower="0" upper="1" effort="1.35" velocity="2.409"/>
      </joint></robot>'''
    return package, xml


def build(path, *, missing_mesh=False, duplicate=False, bad_topology=False):
    with zipfile.ZipFile(path, 'w') as z:
        for side in ('left', 'right'):
            package, xml = hand(side)
            if bad_topology and side == 'right':
                xml = xml.replace('link="R_base"', 'link="unknown"', 1)
            urdf = f'root/{package}/urdf/hand4_evt3/hand4_evt3.urdf'
            z.writestr(urdf, xml)
            if not missing_mesh:
                z.writestr(f'root/{package}/meshes/hand4_evt3/base.STL', b'mesh')
            if duplicate and side == 'right':
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', UserWarning)
                    z.writestr(urdf, xml)


class ModelAuditTests(unittest.TestCase):
    def test_tree_limits_and_no_assumed_mapping(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'input.zip'
            build(p)
            result = audit.inspect(p)
        self.assertFalse(result['physical_control_qualified'])
        self.assertEqual(result['physical_commands_generated'], 0)
        for model in result['models']:
            self.assertEqual(model['links'], 2)
            self.assertEqual(model['revolute_joints'], 1)
            self.assertEqual(model['joints'][0]['limits']['effort'], 1.35)
            self.assertEqual(model['exact_name_matches'], [])
            self.assertFalse(model['topic_to_urdf_mapping_verified'])
            self.assertFalse(model['mounting_verified'])
        json.dumps(result, allow_nan=False)

    def test_missing_mesh_duplicate_or_bad_tree_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            for flag in ('missing_mesh', 'duplicate', 'bad_topology'):
                p = Path(d) / (flag + '.zip')
                build(p, **{flag: True})
                with self.subTest(flag=flag), self.assertRaises(ValueError):
                    audit.inspect(p)

    def test_invalid_zip_rejected_without_network_or_robot(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'bad.zip'
            p.write_bytes(b'not a zip file')
            with self.assertRaises(zipfile.BadZipFile):
                audit.inspect(p)


if __name__ == '__main__':
    unittest.main()
