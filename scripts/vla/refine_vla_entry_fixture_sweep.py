#!/usr/bin/env python3
"""Offline conditional fixture review; no robot commands or physical approval.

Run from repository root. Requires an archived evidence directory containing
metric-scene.json and candidate-source-verification.json. The modeled scene
is deliberately partial: two inferred cuboids from the 2026-09-11 table trial.
Bounds and sample counts are diagnostic assumptions, not certified tolerances.
"""
import argparse
import sys,json,numpy as np,trimesh
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'scripts/teleoperation'))
from general_home.geometry import RobotGeometry,Shape,solid_distance
import review_clamp_trajectory_optimization as common
from cruzr_pico_to_home_owner_gate import JOINT_ORDER
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--evidence-dir',type=Path,required=True);args=parser.parse_args();p=args.evidence_dir;
if (p/'refined-scene-result.json').exists():raise SystemExit('Output already exists; use a new evidence directory')
r=json.loads((p/'quick-scene-result.json').read_text());entries=json.loads((p/'candidate-source-verification.json').read_text());ready=np.array(json.loads(Path('scripts/vla/runtime/cruzr_s2_vla_ready_entry_transition_e6_1c.json').read_text())['observed_ready_reference_20d_rad']);pkg=Path('cruzr_s2_description_splint/cruzr_s2_description');g=RobotGeometry(pkg/'urdf/cruzr_s2_v1/cruzr_s2_v1.urdf',pkg,{'frame_id':'base_link','complete':True,'objects':[]});obstacles={}
for name,raw in r['obstacle_bounds_base_m'].items():
 bounds=np.array(raw);mesh=trimesh.creation.box(extents=bounds[1]-bounds[0]);mesh.apply_translation(bounds.mean(axis=0));obstacles[name]=Shape.from_mesh(name,'base_link',mesh)
output={}
for eid in ['episode_000430','episode_000438']:
 end=np.array(entries[eid]['first_state']);events=r['routes'][eid+'/via_ready'][1]['potential_overlaps'];out=[]
 for event in events:
  a=next(s for s in g.shapes if s.link==event['link']);b=obstacles[event['obstacle']];best=(1e9,None)
  for f in np.linspace(event['first_fraction'],event['last_fraction'],61):
   q=ready+(end-ready)*f;poses=common.fk.forward_kinematics(g.joints,dict(zip(JOINT_ORDER,q)));a.place(poses[a.link]);d=solid_distance(a,b)
   if d<best[0]:best=(d,float(f))
  out.append(dict(link=a.link,obstacle=b.name,minimum_distance_m=best[0],at_fraction=best[1],representation=a.representation))
 output[eid]=out
(p/'refined-scene-result.json').write_text(json.dumps(output,indent=2)+'\n');print(json.dumps(output,indent=2))
