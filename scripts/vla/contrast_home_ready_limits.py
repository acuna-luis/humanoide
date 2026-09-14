#!/usr/bin/env python3
"""Compare an offline access proposal to a read-only Motion configuration snapshot."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import yaml
from extract_s2_compiled_limits import position_domains


def contrast(review, snapshot):
    decoded = {}
    for path, record in snapshot.items():
        raw = base64.b64decode(record['base64'], validate=True)
        if hashlib.sha256(raw).hexdigest() != record['sha256']:
            raise ValueError('Snapshot hash mismatch')
        decoded[path] = raw.decode()
    def source(suffix):
        matches = [v for k, v in decoded.items() if k.endswith(suffix)]
        if len(matches) != 1:
            raise ValueError('Missing or ambiguous configuration')
        return matches[0]
    config = yaml.safe_load(source('/cruzr_s2_robot_description.yaml'))
    urdf = ET.fromstring(source('/cruzr_s2.urdf'))
    limits = {j.get('name'): j.find('limit').attrib for j in urdf.findall('joint')
              if j.find('limit') is not None}
    order = review['joint_order']
    error = review['geometry_audit']['joint_error_scenario_rad']
    if len(order) != 20 or len(set(order)) != 20 or not np.isfinite(error) or error < 0:
        raise ValueError('Invalid joint order or error domain')
    rows = []
    for stage in review['stages']:
        component = stage['location']+'_arm' if stage['type'] == 'arm' else stage['type']
        cfg = config[component]
        if cfg['type'] != stage['type'] or cfg.get('location', 'single') != stage['location']:
            raise ValueError('Group type/location mismatch')
        names = stage['joint_names']
        if len(cfg['kinematics']['zero_positions']) != len(names):
            raise ValueError('Group dimension mismatch')
        duration = stage['duration_seconds']
        if not np.isfinite(duration) or duration <= 0:
            raise ValueError('Invalid duration')
        for i, name in enumerate(names):
            index = order.index(name)
            a, b = stage['start_20d_rad'][index], stage['end_20d_rad'][index]
            lo, hi, vel, acc = -np.inf, np.inf, np.inf, None
            if name in limits:
                lim = limits[name]
                lo, hi, vel = float(lim['lower']), float(lim['upper']), float(lim['velocity'])
            configured = cfg['kinematics'].get('joint_limits')
            if configured:
                lo = max(lo, configured['pos'][i][0]); hi = min(hi, configured['pos'][i][1])
                vel = min(vel, configured['vel'][i]); acc = configured['acc'][i]
            if not np.isfinite([a, b, lo, hi, vel]).all() or vel <= 0:
                raise ValueError('Missing finite limits')
            peak_v = 1.5*abs(b-a)/duration
            peak_a = 6*abs(b-a)/duration**2
            domains = position_domains(a,b,lo,hi,error)
            rows.append(dict(joint=name, component=component,
                nominal_position_pass=domains['nominal_inside'],
                nominal_interval_rad=domains['nominal_interval_rad'],
                position_domain_rad=[min(a,b)-error,max(a,b)+error], limits_rad=[lo,hi],
                position_pass=min(a,b)-error >= lo and max(a,b)+error <= hi,
                cubic_peak_velocity_rad_s=peak_v, configured_velocity_rad_s=vel,
                velocity_pass=peak_v <= vel, cubic_peak_acceleration_rad_s2=peak_a,
                configured_acceleration_rad_s2=acc,
                acceleration_pass=None if acc is None else peak_a <= acc))
    if len(rows) != 20 or {r['joint'] for r in rows} != set(order):
        raise ValueError('Incomplete or repeated joint coverage')
    return dict(scope='CONFIGURATION_COMPARISON_ASSUMING_REST_TO_REST_CUBIC',
        group_type_location_dimensions_match=True, joint_order_runtime_verified=False,
        loaded_configuration_verified=False, motion_interpolator_verified=False,
        all_position_velocity_pass=all(r['position_pass'] and r['velocity_pass'] for r in rows),
        legacy_all_position_velocity_pass_scope='Full uncertainty band and cubic velocity, not only nominal commands',
        all_nominal_position_velocity_pass=all(r['nominal_position_pass'] and r['velocity_pass'] for r in rows),
        uncertainty_band_clipped=False,
        acceleration_missing=[r['joint'] for r in rows if r['acceleration_pass'] is None],
        physical_approval=False, rows=rows)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('review','snapshot','output'):
        p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    result=contrast(json.loads(a.review.read_text()),json.loads(a.snapshot.read_text()))
    result['sources_sha256']={str(f.resolve()):hashlib.sha256(f.read_bytes()).hexdigest()
                              for f in (a.review,a.snapshot,Path(__file__),Path(__file__).with_name('extract_s2_compiled_limits.py'))}
    with a.output.open('x') as f:
        json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','sources_sha256')}))


if __name__=='__main__':
    main()
