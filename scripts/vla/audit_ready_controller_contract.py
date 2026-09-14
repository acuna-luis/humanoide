#!/usr/bin/env python3
"""Offline configuration/compiled-limit audit. Never grants motion permission."""
import argparse
import hashlib
import json
from pathlib import Path

import yaml
from extract_s2_compiled_limits import extract

COMPONENT_SHA = 'f6d076fbaad5f97309b6708a623e519bad1d1fdad378e3ed40c80aa14da25acf'


def compiled_fields(component, arm):
    if hashlib.sha256(component).hexdigest() != COMPONENT_SHA:
        raise ValueError('Component binary differs from manually audited data flow')
    # Pinned binary audit: YAML vel -> xmm0; acc -> xmm1 at 0x95b88..0x95bc0.
    # JointLimits constructor 0x975a0 stores xmm0/xmm1 at offsets 0x10/0x18.
    # This labels constructor defaults, NOT the values in the running object.
    return [dict(position_rad=x[:2], velocity_rad_s=x[2],
                 acceleration_rad_s2=x[3]) for x in extract(arm)]


def configuration_checks(review, snapshot):
    decoded = {}
    for name, record in snapshot.items():
        if hashlib.sha256(record['text'].encode()).hexdigest() != record['sha256']:
            raise ValueError('Configuration snapshot hash mismatch')
        decoded[name] = yaml.safe_load(record['text'])

    def unique(suffix):
        values = [v for k, v in decoded.items() if k.endswith(suffix)]
        if len(values) != 1:
            raise ValueError('Missing/ambiguous configuration: ' + suffix)
        return values[0]

    controllers = unique('/cruzr_s2_v1_mc_config/config/controllers_config.yaml')
    transmissions = unique('/ecat_hardware/transmissions.yaml')['transmissions']
    limits = {v['joint']['name']: v['joint']['limit'] for v in transmissions.values()}
    order = review['joint_order']
    groups = []
    rows = []
    for stage in review['stages']:
        key = (stage['location'] + '_arm' if stage['type'] == 'arm' else stage['type']) + '_controller'
        cfg = controllers[key]
        groups.append(dict(controller=key, configured_names=cfg['joints'],
                           proposed_names=stage['joint_names'],
                           match=cfg['joints'] == stage['joint_names'] and cfg['controller_dof'] == len(stage['joint_names'])))
        for name in stage['joint_names']:
            i = order.index(name)
            a, z = stage['start_20d_rad'][i], stage['end_20d_rad'][i]
            lim = limits[name]
            rows.append(dict(joint=name, minimum_proposed_rad=min(a,z), maximum_proposed_rad=max(a,z),
                             hardware_position_rad=[lim['lower'],lim['upper']],
                             nominal_position_pass=lim['lower'] <= min(a,z) <= max(a,z) <= lim['upper']))
    return dict(configured_group_order_matches=all(g['match'] for g in groups), groups=groups,
                hardware_position_rows=rows,
                hardware_nominal_outside=[r['joint'] for r in rows if not r['nominal_position_pass']])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ('review', 'hardware-snapshot', 'component-binary', 'arm-binary', 'output'):
        p.add_argument('--'+arg, type=Path, required=True)
    a = p.parse_args()
    review = json.loads(a.review.read_text())
    result = configuration_checks(review, json.loads(a.hardware_snapshot.read_text()))
    result['compiled_arm_limits'] = compiled_fields(a.component_binary.read_bytes(), a.arm_binary.read_bytes())
    result.update(scope='CONFIGURED_ORDER_AND_AUDITED_COMPILED_DEFAULTS_ONLY',
                  effective_runtime_limits_verified=False, effective_dispatch_verified=False,
                  physical_approval=False, movement_commands=0,
                  acceleration_field_evidence=dict(yaml_acc_key_va='0xcd367', yaml_to_xmm1='0x95baf..0x95bbb',
                      constructor_store='0x975a4..0x975b0', joint_record_offset='0x18'))
    result['sources_sha256'] = {str(f.resolve()):hashlib.sha256(f.read_bytes()).hexdigest()
        for f in (a.review,a.hardware_snapshot,a.component_binary,a.arm_binary,Path(__file__),Path(__file__).with_name('extract_s2_compiled_limits.py'))}
    with a.output.open('x') as f:
        json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps({k: result[k] for k in ('configured_group_order_matches','hardware_nominal_outside','physical_approval')}))


if __name__ == '__main__':
    main()
