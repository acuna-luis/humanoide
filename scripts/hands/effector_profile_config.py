"""Pure, byte-preserving configuration plans for the inspected Cruzr S2 profiles."""
import copy
import json
import re
import yaml

PROFILES = {'clamp': 'cruzr_s2_v1', 'v4': 'cruzr_s2_v1_sps'}
SERVICES = ['motion.' + name for name in (
    'action_list_manager_main', 'ecat_err_handler_service', 'hw',
    'manipulation_calibration_assistance_server_node', 'manipulation_robot_app',
    'mc_common', 'rtm_receiver', 't800_mc_server', 'vrpn_client_server_node')]
GUARD_SHA = '9f3f2e8363358c0fdb83486153f80145fddb3278ec6332bbf2425dbe8db993c7'
ENI_SHA = '678c7d6bae1608709400383d85c6e0e5edae7032b365d11977cb56bc984250e8'


def field(node, key):
    if not isinstance(node, yaml.MappingNode):
        raise ValueError('Expected a YAML mapping')
    matches = [v for k, v in node.value if k.value == key]
    if len(matches) != 1:
        raise ValueError('Missing/ambiguous YAML field: ' + key)
    return matches[0]


def yaml_environment(raw, route, profile, template=False, template_default=None):
    target = PROFILES[profile]
    text = raw.decode('utf-8')
    node = yaml.compose(text)
    for key in route:
        node = field(node, key)
    env = field(node, 'environment')
    if not isinstance(env, yaml.SequenceNode):
        raise ValueError('Unsupported environment structure; review required')
    nodes = [n for n in env.value if isinstance(n, yaml.ScalarNode) and n.value.startswith('HW_TYPE=')]
    allowed = {'HW_TYPE=' + value for value in PROFILES.values()}
    if template:
        allowed.add('HW_TYPE={{env "HW_TYPE"}}')
    if len(nodes) != 1 or nodes[0].value not in allowed:
        raise ValueError('Unknown or ambiguous hardware profile')
    selected = nodes[0]
    if template and selected.value == 'HW_TYPE={{env "HW_TYPE"}}' and template_default == target:
        return raw
    if selected.value == 'HW_TYPE=' + target:
        return raw
    candidate = (text[:selected.start_mark.index] + json.dumps('HW_TYPE=' + target)
                 + text[selected.end_mark.index:]).encode()
    expected = copy.deepcopy(yaml.safe_load(raw))
    values = expected
    for key in route:
        values = values[key]
    values['environment'][values['environment'].index(selected.value)] = 'HW_TYPE=' + target
    # deepcopy retains YAML aliases; changes in inherited lists must agree too.
    if yaml.safe_load(candidate) != expected:
        raise ValueError('Unexpected YAML change outside the hardware field')
    return candidate


def database_environment(raw, profile):
    parsed = json.loads(raw)
    source = parsed.get('envs', {}).get('HW_TYPE')
    if source not in PROFILES.values():
        raise ValueError('Unknown global Motion hardware profile')
    target = PROFILES[profile]
    if source == target:
        return raw
    matches = list(re.finditer(rb'"HW_TYPE"\s*:\s*"[^"]*"', raw))
    if len(matches) != 1:
        raise ValueError('Ambiguous HW_TYPE in database')
    m = matches[0]
    old = m.group()
    replacement = old[:old.rfind(b'"', 0, len(old)-1)+1] + target.encode() + b'"'
    candidate = raw[:m.start()] + replacement + raw[m.end():]
    expected = copy.deepcopy(parsed)
    expected['envs']['HW_TYPE'] = target
    if json.loads(candidate) != expected:
        raise ValueError('Unexpected database change')
    return candidate


def plan_files(host, files, profile, global_hw_type=None):
    if host == 'motion':
        return {
            'compose.yml': yaml_environment(files['compose.yml'], ('services', 'motion.mc_common'), profile),
            'db.json': database_environment(files['db.json'], profile),
        }
    if host == 'vision':
        return {
            'compose.yml': yaml_environment(files['compose.yml'], ('services', 'system.control_center'), profile),
            'system.metafile.yml': yaml_environment(files['system.metafile.yml'], ('nodes', 'control_center'), profile, True, global_hw_type),
        }
    raise ValueError('Unknown host')


def validate_container(before, after, profile):
    for key in ('Image',):
        if before[key] != after[key]:
            raise ValueError('Container image changed')
    for key in ('Cmd', 'Entrypoint', 'User', 'WorkingDir'):
        if before['Config'].get(key) != after['Config'].get(key):
            raise ValueError('Container execution settings changed: ' + key)
    def mounts(c):
        return sorted((m['Source'], m['Destination'], m['RW'], m['Type']) for m in c['Mounts'])
    if mounts(before) != mounts(after):
        raise ValueError('Container mounts changed')
    # Compose-generated defaults must not change runtime isolation or privileges.
    for key in ('Privileged', 'NetworkMode', 'IpcMode', 'PidMode', 'CapAdd', 'CapDrop',
                'Devices', 'DeviceCgroupRules', 'SecurityOpt', 'RestartPolicy'):
        if before['HostConfig'].get(key) != after['HostConfig'].get(key):
            raise ValueError('Container runtime settings changed: ' + key)
    a = dict(x.split('=', 1) for x in before['Config']['Env'])
    b = dict(x.split('=', 1) for x in after['Config']['Env'])
    if b != dict(a, HW_TYPE=PROFILES[profile]):
        raise ValueError('Unexpected environment change')
