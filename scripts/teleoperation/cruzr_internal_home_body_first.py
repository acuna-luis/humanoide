"""Body-first HOME candidate. No assertion of safety from arbitrary poses."""
import xml.etree.ElementTree as ET
from cruzr_internal_home_open_path import xml_tree as old_tree

def xml_bytes():
    root = old_tree(20)
    seq = root.find('.//Sequence')
    seq.set('name', 'home_body_first_v4_20s')
    body = seq[2]
    seq.remove(body)
    body.set('name', 'body_home_preserving_arm_joints')
    seq.insert(0, body)
    ET.indent(root, space='    ')
    return (ET.tostring(root, encoding='unicode')+'\n').encode()

def validate_xml(data, seconds=20):
    def signature(n):
        return n.tag, sorted(n.attrib.items()), [signature(c) for c in n]
    if seconds != 20 or signature(ET.fromstring(data)) != signature(ET.fromstring(xml_bytes())):
        raise ValueError('Unexpected body-first HOME sequence')
