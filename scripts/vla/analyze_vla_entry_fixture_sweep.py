#!/usr/bin/env python3
"""Offline conditional fixture review; no robot commands or physical approval.

Run from repository root. Requires an archived evidence directory containing
metric-scene.json and candidate-source-verification.json. The modeled scene
is deliberately partial: two inferred cuboids from the 2026-09-11 table trial.
Bounds and sample counts are diagnostic assumptions, not certified tolerances.
"""
import argparse
import sys,json,numpy as np
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'scripts/teleoperation'))
from general_home.geometry import RobotGeometry
import review_clamp_trajectory_optimization as common
from cruzr_pico_to_home_owner_gate import JOINT_ORDER
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--evidence-dir',type=Path,required=True)
parser.add_argument('--obstacles-json',type=Path,help='Explicit inferred bounds: object name -> [minimum XYZ, maximum XYZ], metres in base_link')
args=parser.parse_args();p=args.evidence_dir
if (p/'quick-scene-result.json').exists():raise SystemExit('Output already exists; use a new evidence directory')
reg=json.loads((p/'metric-scene.json').read_text());qmap=dict(zip(reg['joints']['name'],reg['joints']['position']));start=np.array([qmap[n] for n in JOINT_ORDER]);ref=json.loads(Path('scripts/vla/runtime/cruzr_s2_vla_ready_entry_transition_e6_1c.json').read_text());ready=np.array(ref['observed_ready_reference_20d_rad']);entries=json.loads((p/'candidate-source-verification.json').read_text())
pkg=Path('cruzr_s2_description_splint/cruzr_s2_description');g=RobotGeometry(pkg/'urdf/cruzr_s2_v1/cruzr_s2_v1.urdf',pkg,{'frame_id':'base_link','complete':True,'objects':[]})
# Exploratory complete cuboids enclosing only tabletop/box, not a complete scene.
obstacles={'tabletop_inferred':np.array([[.50,-.61,.60],[1.44,.31,.72]]),'box_inferred':np.array([[.60,-.45,.64],[1.07,.21,.93]])}
if args.obstacles_json:
 raw=json.loads(args.obstacles_json.read_text())
 if not isinstance(raw,dict) or not raw:raise SystemExit('Obstacle bounds must be a nonempty object')
 obstacles={name:np.asarray(bounds,dtype=float) for name,bounds in raw.items()}
 for name,bounds in obstacles.items():
  if bounds.shape!=(2,3) or not np.isfinite(bounds).all() or not (bounds[1]>bounds[0]).all():
   raise SystemExit(f'Invalid XYZ bounds for {name}')
output={'scope':'CONDITIONAL_SAMPLED_ROBOT_VS_TWO_INFERRED_CUBOIDS_ONLY','physical_approval':False,'scene_complete':False,'obstacle_bounds_base_m':{k:v.tolist() for k,v in obstacles.items()},'routes':{}}
for eid in ['episode_000430','episode_000438']:
 end=np.array(entries[eid]['first_state']);routes={'via_ready':[start,ready,end],'direct_candidate':[start,end]}
 for name,path in routes.items():
  result=[]
  for stage,(a,b) in enumerate(zip(path,path[1:])):
   q=a+(b-a)*np.linspace(0,1,201)[:,None];poses=common.batch_fk(g.joints,q);events=[];minimum=(1e9,None,None,None)
   for shape in g.shapes:
    if shape.link not in poses:continue
    obs_a=common.batch_obb(poses[shape.link],shape.mesh.bounds)
    for label,bounds in obstacles.items():
     obs_b=common.batch_obb(np.broadcast_to(np.eye(4),(len(q),4,4)),bounds)
     gaps=common.batch_gap(obs_a,obs_b);idx=int(np.argmin(gaps));cur=(float(gaps[idx]),shape.link,label,idx)
     if cur[0]<minimum[0]:minimum=cur
     bad=np.flatnonzero(gaps<=.002)
     if len(bad):events.append({'link':shape.link,'obstacle':label,'minimum_sat_gap_m':float(gaps.min()),'sample_count':len(bad),'first_fraction':float(bad[0]/200),'last_fraction':float(bad[-1]/200)})
   result.append({'stage':stage,'minimum':minimum,'potential_overlaps':events})
  output['routes'][eid+'/'+name]=result
(p/'quick-scene-result.json').write_text(json.dumps(output,indent=2)+'\n');print(json.dumps(output,indent=2))
