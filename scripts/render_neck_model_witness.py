#!/usr/bin/env python3
"""Deterministic CAD illustration of an archived witness, never a live view."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from audit_clamp_pessimistic_screen import URDF, ARCHIVE, fk


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--report',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True)
    args = p.parse_args()
    report = json.loads(args.report.read_text())
    if report['status'] != 'OFFLINE_MODEL_DIAGNOSIS_NOT_PHYSICAL_VALIDATION':
        raise ValueError('unexpected report')
    for source in (URDF,ARCHIVE):
        if hashlib.sha256(source.read_bytes()).hexdigest() != report['source_sha256'][str(source)]:
            raise ValueError('source changed')
    row, = [r for r in report['results'] if r['case']=='historical_measured_READY']
    _,_,triangles = fk.load_robot(URDF,ARCHIVE)
    transform = np.asarray(row['head_in_torso'])
    links = ('head_pitch_link','torso_link')
    world = [fk.apply(triangles[links[0]].reshape(-1,3),transform).reshape(-1,3,3)*1000,
             triangles[links[1]]*1000]
    witnesses = np.asarray(row['triangles_in_torso_m'])*1000
    for tri,index,witness in zip(world,row['triangle_ids'],witnesses):
        np.testing.assert_allclose(tri[index],witness,atol=1e-9)
    crossings = np.array([h['point_m'] for h in row['crossings_in_torso']])*1000
    if crossings.shape != (2,3):
        raise ValueError('expected two independently verified crossings')
    center = crossings.mean(axis=0)
    colors = ['#3977b8','#a5adb4']
    bg = '#f7f9fc'
    fig = plt.figure(figsize=(14,8),facecolor=bg)
    fig.suptitle('¿DÓNDE SE CRUZAN LAS MALLAS DEL MODELO?',fontsize=20,fontweight='bold',y=.965)
    fig.text(.5,.9,'READY histórico medido · CAD del proveedor · no es una imagen del robot actual',
             ha='center',fontsize=12,color='#465266')
    a = fig.add_subplot(121,projection='3d',computed_zorder=False)
    b = fig.add_subplot(122,projection='3d',computed_zorder=False)
    light = np.array([.2,-.6,.8]); light /= np.linalg.norm(light)
    for tri,color in zip(world,colors):
        normals = np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
        normals /= np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-15)
        shade = .5+.5*np.abs(normals@light)
        rgb = np.array(matplotlib.colors.to_rgb(color))
        a.add_collection3d(Poly3DCollection(tri,facecolors=shade[:,None]*rgb,
            edgecolors='none',linewidths=0,rasterized=True,zorder=1))
    a.scatter(*center,s=200,facecolors='none',edgecolors='#d82b39',linewidths=3,zorder=10)
    a.text2D(.04,.87,'Círculo rojo: ubicación del testigo\ncerca de la unión cuello–torso',
             transform=a.transAxes,fontsize=11,color='#b7202c')
    points = np.concatenate([tri.reshape(-1,3) for tri in world])
    low,high = points.min(0),points.max(0)
    a.set_xlim(low[0]-20,high[0]+20); a.set_ylim(low[1]-20,high[1]+20)
    a.set_zlim(low[2]-20,high[2]+20); a.set_box_aspect(high-low+40)
    a.set_axis_off(); a.set_title('1 · Cabeza y torso completos',fontsize=13,pad=5)
    for tri,color in zip(witnesses,colors):
        b.add_collection3d(Poly3DCollection([tri],facecolors=color,edgecolors=color,
                                           alpha=.45,linewidths=2,zorder=1))
    b.plot(*crossings.T,color='#d82b39',linewidth=5,zorder=10)
    b.scatter(*crossings.T,color='#d82b39',s=45,zorder=11)
    points = witnesses.reshape(-1,3); lo,hi = points.min(0),points.max(0)
    half = max(hi-lo)/2+1.2; c=(hi+lo)/2
    b.set_xlim(c[0]-half,c[0]+half);b.set_ylim(c[1]-half,c[1]+half);b.set_zlim(c[2]-half,c[2]+half)
    b.set_box_aspect((1,1,1));b.tick_params(labelsize=8)
    b.set_xlabel('X del torso [mm]',fontsize=9,labelpad=8)
    b.set_ylabel('Y del torso [mm]',fontsize=9,labelpad=8)
    b.set_zlabel('Z del torso [mm]',fontsize=9,labelpad=8)
    b.set_title('2 · Sólo los dos triángulos testigo, ampliados',fontsize=13,pad=5)
    for ax in (a,b):
        ax.set_facecolor(bg);ax.view_init(elev=16,azim=-120)
    fig.legend(handles=[Patch(color=colors[0],label='Malla cabeza'),Patch(color=colors[1],label='Malla torso'),
        Patch(color='#d82b39',label='Cruce calculado; no daño observado')],
        loc='lower center',bbox_to_anchor=(.5,.13),ncol=3,frameon=False,fontsize=11)
    fig.text(.055,.065,'El segmento rojo une dos cruces arista–cara calculados. No mide profundidad de penetración ni fuerza.\n'
        'No se han recortado mallas ni cambiado READY. El marcado se dibuja encima para localizarlo; no prueba visibilidad física.',
        fontsize=10,color='#465266')
    fig.subplots_adjust(top=.82,bottom=.22,left=.02,right=.96,wspace=.12)
    args.output_dir.mkdir(parents=True,exist_ok=False)
    output = args.output_dir/'cuello_testigo_READY.png'
    fig.savefig(output,dpi=150,facecolor=bg)
    plt.close(fig)
    manifest = dict(report=str(args.report),report_sha256=hashlib.sha256(args.report.read_bytes()).hexdigest(),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        source_sha256=report['source_sha256'],image_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
        case=row['case'],triangle_ids=row['triangle_ids'],witness_center_torso_mm=center.tolist(),
        physical_authorized=False,movement_commands=0,robot_connections=0,
        note='Full meshes in context; only witness triangles in zoom. Marker overlaid regardless of occlusion.')
    (args.output_dir/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(output)


if __name__=='__main__':
    main()
