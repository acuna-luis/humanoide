#!/usr/bin/env python3
"""Render actual archived audit meshes, not an imagined robot. No robot IO."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from audit_clamp_pessimistic_screen import URDF, ARCHIVE, fk
import clamp_work_model


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    joints, _, triangles, profile = clamp_work_model.load()
    root = ET.parse(URDF).getroot()
    with zipfile.ZipFile(ARCHIVE) as archive:
        members = {n.split('cruzr_s2_description/', 1)[-1]: n for n in archive.namelist() if not n.endswith('/')}
        for side in ('L', 'R'):
            name = side+'_shoulder_pitch_link'
            visual = root.find(f"link[@name='{name}']/visual")
            tri = fk.geometry_triangles(visual.find('geometry'), archive, members)
            triangles[name] = fk.apply(tri.reshape(-1, 3), fk.origin_transform(visual.find('origin'))).reshape(-1,3,3)
    q = {j['name']: 0. for j in joints if j['type'] != 'fixed'}
    poses = fk.forward_kinematics(joints, q)
    world = {n: fk.apply(tri.reshape(-1,3), poses[n]).reshape(-1,3,3) for n,tri in triangles.items()}
    colors = dict(body='#b3bcc5', arm='#408f95', head='#567cd3', fallback='#e9a23b', gripper='#a563b5')
    def category(n):
        if 'pgc' in n or 'finger' in n:
            return 'gripper'
        if 'shoulder_pitch_link' in n:
            return 'fallback'
        if n.startswith('head'):
            return 'head'
        return 'arm' if n.startswith(('L_', 'R_')) else 'body'
    allpoints = np.concatenate([x.reshape(-1,3) for x in world.values()])
    low, high = allpoints.min(0), allpoints.max(0)
    fig = plt.figure(figsize=(16,9), facecolor='#f6f8fb')
    fig.suptitle('MODELO CORREGIDO · SIN PINZAS PGC', fontsize=20, fontweight='bold', y=.96)
    axes = [fig.add_subplot(1,3,i+1, projection='3d') for i in range(3)]
    light = np.array([.5,-.3,.8]); light /= np.linalg.norm(light)
    for index, ax in enumerate(axes):
        ax.set_facecolor('#f6f8fb')
        for n, tri in world.items():
            if index == 2:
                continue
            normals = np.cross(tri[:,1]-tri[:,0], tri[:,2]-tri[:,0])
            norm = np.linalg.norm(normals, axis=1)
            normals /= np.maximum(norm[:,None],1e-15)
            shade = .55+.45*np.abs(normals@light)
            rgb = np.array(matplotlib.colors.to_rgb(colors[category(n)]))
            facecolors = np.clip(shade[:,None]*rgb,0,1)
            collection = Poly3DCollection(tri, facecolors=facecolors, edgecolors='none', linewidths=0, rasterized=True)
            ax.add_collection3d(collection)
        if index < 2:
            center = (low+high)/2
            span = high-low
            ax.set_xlim(center[0]-.48,center[0]+.48)
            ax.set_ylim(center[1]-.48,center[1]+.48)
            ax.set_zlim(low[2]-.03,high[2]+.03)
            ax.set_box_aspect((.96,.96,span[2]+.06))
            ax.view_init(elev=12,azim=25 if index == 0 else 115)
        else:
            tool = profile['tools']['L']
            for bounds,color,alpha in [(tool['descriptive_envelope']['bounds_m'],'#789fa0',.12),
                (tool['descriptive_primitives'][0]['bounds_m'],'#408f95',.9),
                (tool['descriptive_primitives'][1]['bounds_m'],'#e9a23b',.65)]:
                lo,hi = np.asarray(bounds)*1000
                # Display axes u, depth, v: descriptive coordinates, NOT ROS.
                lo,hi = lo[[0,2,1]],hi[[0,2,1]]
                vertices = np.array([[lo[0],lo[1],lo[2]],[hi[0],lo[1],lo[2]],
                    [hi[0],hi[1],lo[2]],[lo[0],hi[1],lo[2]],
                    [lo[0],lo[1],hi[2]],[hi[0],lo[1],hi[2]],
                    [hi[0],hi[1],hi[2]],[lo[0],hi[1],hi[2]]])
                faces = [[vertices[i] for i in face] for face in
                         [(0,1,2,3),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]]
                ax.add_collection3d(Poly3DCollection(faces,facecolors=color,edgecolors=color,alpha=alpha,linewidths=1))
            ax.set_xlim(-60,70); ax.set_ylim(-55,115); ax.set_zlim(-75,65)
            ax.set_box_aspect((130,170,140))
            ax.view_init(elev=22,azim=-55)
        ax.set_axis_off()
    axes[0].set_title('Vista 3D frontal oblicua', fontsize=13)
    axes[1].set_title('Vista 3D lateral oblicua', fontsize=13)
    axes[2].set_title('Abrazadera: modelo nominal SEPARADO', fontsize=13)
    fig.legend(handles=[Patch(color=colors[k],label=l) for k,l in
        [('body','Cuerpo: collision URDF'),('arm','Brazos: collision URDF'),('head','Cabeza: collision URDF'),
         ('fallback','Hombro: malla visual provisional')]],
        loc='lower center',bbox_to_anchor=(.5,.105),ncol=3,frameon=False,fontsize=10)
    fig.text(.69,.25,'Envolvente total: 82 × 100 × 130 mm\nPlaca: 70 × 100 × 36 mm; patitas: +12 mm\nTransparente: soporte según contención reportada\nPosición y orientación sobre sensor: PENDIENTES',fontsize=10,color='#414c59')
    fig.text(.05,.055,'Izquierda/centro: robot en cero sintético, SIN útiles montados en el modelo; no es la configuración física completa.\nDerecha: volumen descriptivo según cotas reportadas, no CAD exacto. No se ha supuesto su transformación al sensor.',fontsize=11,color='#374453')
    fig.subplots_adjust(left=.015,right=.99,bottom=.22,top=.86,wspace=.04)
    fig.savefig(args.output_dir/'home_mallas.png',dpi=160,facecolor=fig.get_facecolor())
    fig.savefig(args.output_dir/'home_mallas.svg',facecolor=fig.get_facecolor())
    plt.close(fig)
    manifest = dict(state=q, rendered_links={n:dict(triangles=len(t),category=category(n)) for n,t in triangles.items()},
        tool_profile=profile,
        source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (URDF,ARCHIVE,Path(__file__),Path(clamp_work_model.__file__),clamp_work_model.CONTRACT)},
        note='Robot mesh triangles rendered; tool shown separately in descriptive coordinates; not physical validation',
        robot_connections=0,movement_commands=0)
    (args.output_dir/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(args.output_dir/'home_mallas.png')


if __name__ == '__main__':
    main()
