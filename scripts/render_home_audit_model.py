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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    joints, _, triangles = fk.load_robot(URDF, ARCHIVE)
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
    fig.suptitle('HOME NUMÉRICO · MALLAS UTILIZADAS EN LA AUDITORÍA', fontsize=20, fontweight='bold', y=.96)
    axes = [fig.add_subplot(1,3,i+1, projection='3d') for i in range(3)]
    light = np.array([.5,-.3,.8]); light /= np.linalg.norm(light)
    for index, ax in enumerate(axes):
        ax.set_facecolor('#f6f8fb')
        for n, tri in world.items():
            if index == 2 and not (n.startswith('L_') and any(k in n for k in ('elbow','wrist','sixforce','pgc','finger'))):
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
            center = poses['L_sixforce_link'][:3,3]
            u,v = np.meshgrid(np.linspace(0,2*np.pi,25),np.linspace(0,np.pi,17))
            for radius,color in ((.119411,'#d57613'),(.204411,'#c33446')):
                ax.plot_wireframe(center[0]+radius*np.cos(u)*np.sin(v),
                    center[1]+radius*np.sin(u)*np.sin(v),center[2]+radius*np.cos(v),
                    color=color,linewidth=.55,alpha=.6)
            ax.scatter(*center,color='black',s=20)
            ax.set_xlim(center[0]-.24,center[0]+.24)
            ax.set_ylim(center[1]-.24,center[1]+.24)
            ax.set_zlim(center[2]-.24,center[2]+.32)
            ax.set_box_aspect((.48,.48,.56))
            ax.view_init(elev=15,azim=30)
        ax.set_axis_off()
    axes[0].set_title('Vista 3D frontal oblicua', fontsize=13)
    axes[1].set_title('Vista 3D lateral oblicua', fontsize=13)
    axes[2].set_title('Muñeca izquierda + hipótesis esféricas', fontsize=13)
    fig.legend(handles=[Patch(color=colors[k],label=l) for k,l in
        [('body','Cuerpo: collision URDF'),('arm','Brazos: collision URDF'),('head','Cabeza: collision URDF'),
         ('fallback','Hombro: malla visual provisional'),('gripper','Pinza PGC histórica, NO abrazadera real')]],
        loc='lower center',bbox_to_anchor=(.5,.105),ncol=3,frameon=False,fontsize=10)
    fig.text(.69,.25,'Naranja: radio nominal 119,4 mm\nRojo: radio hipotético ampliado 204,4 mm\nCentro supuesto: origen sixforce del URDF',fontsize=10,color='#414c59')
    fig.text(.05,.055,'Todos los ejes = 0 (postura sintética, no captura actual). No se ha reconstruido una malla exacta de las abrazaderas.\nLas esferas son hipótesis de sensibilidad, NO piezas físicas ni cotas de seguridad verificadas. Sin mesas, vallas ni entorno.',fontsize=11,color='#374453')
    fig.subplots_adjust(left=.015,right=.99,bottom=.22,top=.86,wspace=.04)
    fig.savefig(args.output_dir/'home_mallas.png',dpi=160,facecolor=fig.get_facecolor())
    fig.savefig(args.output_dir/'home_mallas.svg',facecolor=fig.get_facecolor())
    plt.close(fig)
    manifest = dict(state=q, rendered_links={n:dict(triangles=len(t),category=category(n)) for n,t in triangles.items()},
        source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (URDF,ARCHIVE,Path(__file__))},
        note='Exact mesh triangles rendered; sphere radii rounded for illustration; not physical validation',
        robot_connections=0,movement_commands=0)
    (args.output_dir/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(args.output_dir/'home_mallas.png')


if __name__ == '__main__':
    main()
