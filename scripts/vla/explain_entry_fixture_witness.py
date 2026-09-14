#!/usr/bin/env python3
"""Quantify and visualize a verified model witness. No robot connection."""
import argparse
import copy
import json
from pathlib import Path

import fcl
import numpy as np
import trimesh

from prepare_vla_entry_bundle import ROOT, RobotGeometry, JOINT_ORDER, common, digest
from general_home.geometry import solid_distance


def ordered_surface_points(mesh_a, mesh_b, points):
    """FCL BVH nearest point ordering can be reversed; verify membership."""
    points = np.asarray(points, float)
    if points.shape != (2, 3) or not np.isfinite(points).all():
        raise ValueError('Invalid nearest points')
    da = trimesh.proximity.closest_point_naive(mesh_a, points)[1]
    db = trimesh.proximity.closest_point_naive(mesh_b, points)[1]
    if da[0] <= 1e-6 and db[1] <= 1e-6: return points, False
    if da[1] <= 1e-6 and db[0] <= 1e-6: return points[::-1].copy(), True
    raise ValueError('Nearest points do not belong to their surfaces')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('review', 'witness', 'output', 'html'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.html.exists(): parser.error('Outputs must be new')
    review = json.loads(args.review.read_text()); witness = json.loads(args.witness.read_text())
    if (witness['scope'] != 'RECOMPUTED_MODEL_WITNESS' or review['joint_order'] != JOINT_ORDER
            or witness['sources_sha256'][str(args.review.resolve())] != digest(args.review)
            or len(review['scenarios']) != 1): parser.error('Unverified or mismatched inputs')
    scenario = review['scenarios'][0]; padding = scenario['padding_mm']/1000
    objects = copy.deepcopy(scenario['scene_objects'])
    plain = copy.deepcopy(objects)
    for obj in plain:
        obj['size_m'] = (np.asarray(obj['size_m'])-2*padding).tolist()
        if min(obj['size_m']) <= 0: parser.error('Invalid unpadded size')
    sources = [args.review, args.witness, Path(__file__), Path(common.__file__), Path(common.fk.__file__),
               ROOT/'scripts/teleoperation/general_home/geometry.py',
               ROOT/'scripts/vla/prepare_vla_entry_bundle.py']
    hashes = {str(p.resolve()): digest(p) for p in sources}
    package = ROOT/'cruzr_s2_description_splint/cruzr_s2_description'
    def model(scene):
        m = RobotGeometry(package/'urdf/cruzr_s2_v1/cruzr_s2_v1.urdf', package,
                          dict(frame_id='base_link', complete=True, objects=scene))
        if m.manifest != review['model_sources']: raise ValueError('Model changed')
        return m
    inflated, actual = model(objects), model(plain)
    q = np.asarray(witness['q']); route = scenario['routes'][witness['route']]
    path = np.asarray(route['waypoints_20d_rad']); segment = witness['segment']; t = witness['fraction']
    if not 0 <= segment < len(path)-1 or not 0 <= t <= 1: parser.error('Invalid witness location')
    nominal = (1-t)*path[segment]+t*path[segment+1]
    if (q.shape != (20,) or not np.isfinite(q).all() or (q < actual.lower).any()
            or (q > actual.upper).any()
            or np.max(np.abs(q-nominal)) > route['audit']['joint_error_scenario_rad']+1e-12):
        parser.error('Invalid witness posture')
    def place(m, state):
        poses = common.fk.forward_kinematics(m.joints, dict(m.auxiliary, **dict(zip(JOINT_ORDER,state))))
        for s in m.shapes[:m.robot_count]: s.place(poses[s.link])
    index = actual.labels.index(witness['pair']); a,b = actual.pairs[index]
    if b < actual.robot_count: parser.error('Requires robot-scene pair')
    place(actual, nominal)
    nominal_distance = float(solid_distance(actual.shapes[a], actual.shapes[b]))
    place(actual, q); place(inflated, q)
    nearest = fcl.DistanceResult()
    raw = float(fcl.distance(actual.shapes[a].obj, actual.shapes[b].obj,
                            fcl.DistanceRequest(enable_nearest_points=True), nearest))
    points = np.asarray(nearest.nearest_points)
    if raw <= 0 or points.shape != (2,3) or not np.isfinite(points).all():
        parser.error('Requires separated unpadded pair and finite nearest points')
    if not np.isclose(np.linalg.norm(points[1]-points[0]), raw, rtol=1e-5, atol=1e-7):
        parser.error('Nearest point length disagrees with distance')
    meshes=[]
    for i in (a,b):
        mesh=actual.shapes[i].mesh.copy();mesh.apply_transform(actual.shapes[i].pose);meshes.append(mesh)
    points, swapped = ordered_surface_points(*meshes, points)
    # A separate, explicit translated box tests whether the witness needs the
    # simultaneous growth of every face. Never modify either archived scene.
    extra = min(.001, (padding-raw)/2) if raw < padding else .001
    shift = (points[0]-points[1])*(1+extra/raw)
    translated = copy.deepcopy(plain)
    target = b-actual.robot_count
    translated[target]['center_m'] = (np.asarray(translated[target]['center_m'])+shift).tolist()
    moved = model(translated); place(moved,q)
    contacts = int(fcl.collide(moved.shapes[a].obj,moved.shapes[b].obj,fcl.CollisionRequest(),fcl.CollisionResult()))
    inflated_contacts = int(fcl.collide(inflated.shapes[a].obj,inflated.shapes[b].obj,fcl.CollisionRequest(),fcl.CollisionResult()))
    output = dict(scope='OFFLINE_SCENE_TRANSLATION_COUNTEREXAMPLE',physical_approval=False,
        physical_contact_observed=False,fixture_registration_qualified=False,
        pair=witness['pair'],fraction=t,
        nominal_to_unpadded_scene_distance_mm=1000*nominal_distance,
        perturbed_to_unpadded_scene_distance_mm=1000*raw,
        expanded_scene_fcl_contacts=inflated_contacts,
        explicit_scene_translation_base_mm=(1000*shift).tolist(),
        explicit_scene_translation_norm_mm=float(1000*np.linalg.norm(shift)),
        translation_within_50mm=bool(np.linalg.norm(shift) <= .05),
        translated_unpadded_box_fcl_contacts=contacts,
        nearest_points_order_corrected=swapped,
        translation_respects_table_support='NOT_ESTABLISHED',
        scene_angular_error_tested=False,maximum_joint_error_degrees=float(np.degrees(np.max(np.abs(q-nominal)))),
        model_sources=actual.manifest,sources_sha256=hashes)
    items=[]
    def add(m,i,color,wire,label):
        shape=m.shapes[i]
        vertices=common.fk.apply(shape.mesh.vertices,shape.pose)
        items.append(dict(vertices=vertices.tolist(),faces=shape.mesh.faces.tolist(),color=color,wire=wire,label=label))
    add(actual,a,'#f87e70',False,'Abrazadera perturbada')
    add(actual,b,'#45b9ff',True,'Caja del ajuste visual')
    add(inflated,b,'#f5ba59',True,'Caja ampliada 50 mm')
    add(moved,b,'#b397fa',True,'Caja trasladada (hipótesis)')
    for i in range(actual.robot_count,len(actual.shapes)):
        if i != b: add(actual,i,'#739789',True,'Mesa del ajuste visual')
    payload=json.dumps(dict(items=items,summary=output,focus=actual.shapes[b].mesh.centroid.tolist()),separators=(',',':'))
    template=HTML.replace('__DATA__',payload.replace('</',r'<\/'))
    if any(digest(Path(p)) != h for p,h in hashes.items()) or not actual.source_files_unchanged():
        raise RuntimeError('Source changed')
    with args.output.open('x') as f: json.dump(output,f,indent=2);f.write('\n')
    with args.html.open('x') as f:f.write(template)
    print(json.dumps({k:v for k,v in output.items() if k not in ('sources_sha256','model_sources')}))


HTML='''<!doctype html><html lang="es"><meta charset="utf-8"><title>ENTRY: contraejemplo del modelo</title>
<style>body{margin:0;background:#13212e;color:#edf4fa;font:16px system-ui}main{max-width:1100px;margin:auto;padding:18px}h1{font-size:23px}canvas{width:100%;height:560px;background:#192e3e;touch-action:none}p{line-height:1.5}label{display:inline-block;margin:8px}small{color:#bdd0e1}</style>
<main><h1>ENTRY440: comprobación geométrica de la postura final</h1>
<p>Contraejemplo calculado; no es una colisión observada en el robot. La escena viene de un ajuste visual cuya exactitud está pendiente.</p>
<div id="legend"></div><canvas id="view"></canvas><small>Arrastra para girar. Rueda para ampliar. Coordenadas en metros, marco base_link. Las cajas se muestran con aristas; todos sus volúmenes intervienen en el cálculo.</small>
<p id="numbers"></p><p>Las perturbaciones articulares son independientes dentro de ±1°. La traslación ilustrada es una hipótesis de registro; no se ha demostrado que conserve el apoyo de la caja en la mesa. Esto no aprueba ni ordena movimiento.</p></main>
<script>const data=__DATA__;const canvas=document.getElementById('view'),ctx=canvas.getContext('2d');
let yaw=-.8,pitch=.45,scale=520,down=false,last=[0,0];const visible=data.items.map(()=>true);
data.items.forEach((o,i)=>{let l=document.createElement('label');l.style.color=o.color;let c=document.createElement('input');c.type='checkbox';c.checked=true;c.onchange=()=>{visible[i]=c.checked;draw()};l.append(c,document.createTextNode(o.label));document.getElementById('legend').append(l)});
const s=data.summary;document.getElementById('numbers').textContent=`Separación contra caja sin ampliar: nominal ${s.nominal_to_unpadded_scene_distance_mm.toFixed(2)} mm; postura perturbada ${s.perturbed_to_unpadded_scene_distance_mm.toFixed(2)} mm. Error articular máximo ${s.maximum_joint_error_degrees.toFixed(3)}°. Traslación ilustrada ${s.explicit_scene_translation_norm_mm.toFixed(2)} mm; contactos calculados ${s.translated_unpadded_box_fcl_contacts}.`;
function project(v){let [x,y,z]=v.map((n,i)=>n-data.focus[i]);let a=Math.cos(yaw)*x-Math.sin(yaw)*y,b=Math.sin(yaw)*x+Math.cos(yaw)*y;return [canvas.width/2+scale*a,canvas.height/2-scale*(Math.cos(pitch)*z-Math.sin(pitch)*b),Math.cos(pitch)*b+Math.sin(pitch)*z]}
function draw(){canvas.width=canvas.clientWidth;canvas.height=560;ctx.clearRect(0,0,canvas.width,canvas.height);let triangles=[];data.items.forEach((o,i)=>{if(!visible[i])return;let p=o.vertices.map(project);o.faces.forEach(f=>{let v=f.map(k=>p[k]);triangles.push({v,color:o.color,wire:o.wire,z:v.reduce((a,b)=>a+b[2],0)/3})})});triangles.sort((a,b)=>a.z-b.z);triangles.forEach(t=>{ctx.beginPath();t.v.forEach((p,i)=>i?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1]));ctx.closePath();ctx.strokeStyle=t.color;ctx.lineWidth=t.wire?1:0.35;if(!t.wire){ctx.fillStyle=t.color;ctx.fill()}ctx.globalAlpha=t.wire?.55:1;ctx.stroke();ctx.globalAlpha=1})}
canvas.onpointerdown=e=>{down=true;last=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId)};canvas.onpointerup=()=>down=false;canvas.onpointermove=e=>{if(!down)return;yaw+=(e.clientX-last[0])*.008;pitch=Math.max(-1.5,Math.min(1.5,pitch+(e.clientY-last[1])*.008));last=[e.clientX,e.clientY];draw()};canvas.onwheel=e=>{e.preventDefault();scale=Math.max(150,Math.min(3000,scale*Math.exp(-e.deltaY*.001)));draw()};window.onresize=draw;draw();</script></html>'''


if __name__=='__main__':main()
