#!/usr/bin/env python3
"""Propuesta matemática PICO→HOME para revisión; no planifica colisiones ni mueve."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'scripts/lib')]
from cruzr_home_posture_gate import classify


def build(joints, actuators, names, urdf):
    classify(actuators, .02)  # exige actuadores sanos, reposo y consignas próximas
    if len(names) != 20 or len(set(names)) != 20:
        raise ValueError('Se requieren veinte nombres únicos')
    raw_names = joints['name']
    if len(set(raw_names)) != len(raw_names):
        raise ValueError('Nombres duplicados')
    for field in ('position', 'velocity'):
        values = joints[field]
        if len(values) != len(raw_names) or any(type(x) not in (int,float) or not math.isfinite(x) for x in values):
            raise ValueError('Estado incompleto/no finito')
    pos = dict(zip(raw_names, joints['position']))
    vel = dict(zip(raw_names, joints['velocity']))
    start = [pos[n] for n in names]
    if max(abs(vel[n]) for n in names) > .01:
        raise ValueError('Muestra articular en movimiento')
    model = {j.get('name'):j for j in ET.fromstring(urdf).findall('joint')}
    bounds = {}
    for n,q in zip(names,start):
        j = model[n]
        if j.get('type') != 'revolute':
            raise ValueError('Tipo de articulación inesperado: '+n)
        lim=j.find('limit');lo,hi=float(lim.get('lower')),float(lim.get('upper'))
        if not (math.isfinite(lo) and math.isfinite(hi) and lo<hi and lo<=q<=hi and lo<=0<=hi):
            raise ValueError('Extremo fuera de límites: '+n)
        bounds[n]=[lo,hi]
    # Dos fases hipotéticas. NO se afirma que este orden evite contacto.
    arms_zero=[0.0]*14+start[14:]
    points=[('medida',start),('brazos_cero_cuerpo_conservado',arms_zero),('HOME_numerico',[0.0]*20)]
    segments=[]
    for (label,a),(target,b) in zip(points,points[1:]):
        d=max(abs(y-x) for x,y in zip(a,b))
        duration=max(1.875*d/.15,math.sqrt((10/math.sqrt(3))*d/.5),.001)*1.000001
        segments.append(dict(source=label,target=target,start_rad=a,end_rad=b,duration_s=duration,
                             analytic_vmax_rad_s=1.875*d/duration,
                             analytic_amax_rad_s2=(10/math.sqrt(3))*d/duration**2))
    return dict(schema='pico-home-review-only-v1',joint_names=names,segments=segments,
                source_state='archived_samples_not_live_at_execution',
                interpolation='quintic 10u^3-15u^4+6u^5; reposo en extremos',
                provisional_design_limits={'velocity':.15,'acceleration':.5},
                position_bounds=bounds,position_bounds_pass=True,
                total_duration_s=sum(s['duration_s'] for s in segments),
                collision_validated=False,runtime_equivalence_verified=False,
                executable=False,physical_authorized=False,
                unresolved=['geometría y escena actuales','trayectoria libre de contacto',
                            'estabilidad, seguimiento y frenado','interpolador instalado',
                            'estado y control exclusivos antes de ejecutar'],
                warning='Hipótesis directa por grupos, no búsqueda de una ruta segura. No convertir a XML/ROS para ensayarla.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot-dir',type=Path,required=True)
    parser.add_argument('--urdf',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    sources={}
    def sample(name):
        p=args.snapshot_dir/(name+'.json');raw=p.read_bytes();sources[str(p)]=hashlib.sha256(raw).hexdigest()
        envelope=json.loads(raw)
        if envelope.get('returncode')!=0:raise ValueError('Captura fallida: '+name)
        return json.loads(envelope['stdout'])
    contract=ROOT/'scripts/vla/runtime/cruzr_s2_vla_ready_entry_transition_e6_1c.json'
    names=json.loads(contract.read_text())['joint_order']
    result=build(sample('joints'),sample('actuators'),names,args.urdf.read_text())
    for p in [args.urdf,contract,Path(__file__)]:sources[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    result['source_sha256']=sources
    with args.output.open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps({'duration_s':result['total_duration_s'],'position_bounds_pass':True,'executable':False,'output':str(args.output)}))

if __name__=='__main__':main()
