#!/usr/bin/env python3
"""Read archived state/installed meshes; conditional OBB sweep, never motion."""
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/vla'))
import analyze_vla_fixture_collision_e4_1c as fk


def separation(ca,aa,ea,cb,ab,eb):
    """SAT projection gap on normalized axes; positive is a distance lower bound."""
    axes=[*aa.T,*ab.T]
    axes.extend(np.cross(x,y) for x in aa.T for y in ab.T)
    best=-float('inf')
    for a in axes:
        norm=np.linalg.norm(a)
        if norm<1e-10:continue
        a=a/norm
        best=max(best,abs(float(a@(cb-ca)))-float(np.abs(a@aa)@ea)-float(np.abs(a@ab)@eb))
    return best


def obb(pose,bounds):
    lo,hi=map(np.asarray,bounds)
    return pose[:3,:3]@((lo+hi)/2)+pose[:3,3],pose[:3,:3],(hi-lo)/2


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--snapshot-dir',type=Path,required=True)
    p.add_argument('--samples',type=int,default=101)
    p.add_argument('--output',type=Path)
    args=p.parse_args();out=args.snapshot_dir
    if not 2<=args.samples<=1001:raise ValueError('samples 2..1001')
    proposal=json.loads((out/'home-proposal.json').read_text())
    joints,boxes,meshes=fk.load_robot(out/'runtime.urdf',out/'runtime-meshes.zip')
    raw=json.loads(json.loads((out/'joints.json').read_text())['stdout']);initial=dict(zip(raw['name'],raw['position']))
    if any(j['name'] not in initial for j in joints if j['type']!='fixed'):raise ValueError('missing joint')
    # User's 2 mm linear allowance. Axial origin interval retained, not guessed.
    # Whole volume, not a wrist exemption: overlaps against attachment also reported.
    depth=max(.130,*(boxes[s+'_hand_link'][1][2] for s in ('L','R')))
    tool={
        'R':(np.array([.095-depth,-.035,-.050])-.002,np.array([.095,.047,.090])+.002),
        'L':(np.array([-.095,-.035,-.050])-.002,np.array([depth-.095,.047,.090])+.002)}
    targets=sorted(n for n in boxes if n not in ('L_hand_link','R_hand_link'))
    # Conservative common point-travel bound over each monotone joint interval.
    reach=sum(np.linalg.norm(j['origin'][:3,3]) for j in joints)
    reach+=max(max(np.linalg.norm(fk.corners(*b),axis=1)) for b in list(boxes.values())+list(tool.values()))
    records=[]
    for si,segment in enumerate(proposal['segments']):
        start=np.array(segment['start_rad']);end=np.array(segment['end_rad']);delta=end-start
        state=lambda a:dict(initial,**dict(zip(proposal['joint_names'],(start+a*delta).tolist())))
        # Physical time law is quintic; geometry follows the same monotone line.
        travel=reach*float(np.abs(delta).sum())/(args.samples-1)/2
        minima={};uncertain=set();witnesses={}
        for a in np.linspace(0,1,args.samples):
            poses=fk.forward_kinematics(joints,state(float(a)))
            tb={s:obb(poses[s+'_sixforce_link'],tool[s]) for s in ('L','R')}
            pairs=[(s,n,separation(*tb[s],*obb(poses[n],boxes[n]))) for s in ('L','R') for n in targets]
            pairs.append(('L','R_clamp',separation(*tb['L'],*tb['R'])))
            for side,name,gap in pairs:
                key=side+':'+name
                if gap<minima.get(key,float('inf')):
                    minima[key]=gap;witnesses[key]={'fraction':float(a),'gap_m':gap}
                if gap-2*travel<=0:uncertain.add(key)
        # At least one nearest grid point within half step covers every alpha.
        records.append({'segment':si,'target':segment['target'],'samples':args.samples,
            'point_travel_bound_half_grid_m':travel,'sample_min_projection_gaps_m':minima,
            'continuous_unresolved_pairs':sorted(uncertain),'worst_samples':witnesses,
            'continuous_separated_pairs':sorted(set(minima)-uncertain)})
    result={'status':'CONDITIONAL_SWEEP_NOT_PHYSICAL_APPROVAL','movement_commands':0,'executable':False,
        'position_limits_pass':proposal['position_bounds_pass'],'duration_s':proposal['total_duration_s'],
        'error_allowance_m':.002,'origin_axial_interval_m':[0,.040],
        'tool_bounds_in_sensor_m':{s:[x.tolist() for x in b] for s,b in tool.items()},
        'effective_total_depth_m':float(depth),'tested_robot_links':targets,'records':records,
        'coverage':'clamp-vs-robot and clamp-vs-clamp; not robot-vs-robot or external scene',
        'proof':'SAT positive normalized projection gap is a separation lower bound. Subtract twice global reach times half-grid sum of joint changes; covers continuous monotone joint curve conditionally.',
        'limitations':['bounds include filled empty space; negative SAT gap is not proven real collision',
         'installed robot collision meshes treated as link OBBs, not qualified physical surfaces',
         'user linear error applied to tool bounds; angular and tracking errors not bounded',
         '0..40 mm origin hypothesis retained; physical face correspondence not certified',
         'runtime controller interpolation/dynamics and external scene not checked',
         'no attachment-region exemption; all such overlaps remain reported'],
        'source_sha256':{str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in [Path(__file__),out/'runtime.urdf',out/'runtime-meshes.zip',out/'joints.json',out/'home-proposal.json']}}
    f=args.output or out/'geometry-check.json'
    with f.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False)
    print(json.dumps({'report':str(f),'duration_s':result['duration_s'],'depth_mm':depth*1000,
        'segments':[{'segment':r['segment'],'unresolved':len(r['continuous_unresolved_pairs']),
        'sample_overlaps':{k:v for k,v in r['worst_samples'].items() if v['gap_m']<=0}} for r in records]},indent=2))
if __name__=='__main__':main()
