"""Outward-rounded interval FK boxes; model-space enclosure, no robot commands."""
import math
import numpy as np


def down(x): return np.nextafter(x, -np.inf)
def up(x): return np.nextafter(x, np.inf)


def multiply(a, b):
    al,ah=a;bl,bh=b
    lo=np.zeros((al.shape[0],bl.shape[1]));hi=lo.copy()
    for k in range(al.shape[1]):
        terms=np.stack([al[:,k,None]*bl[k,None,:],al[:,k,None]*bh[k,None,:],
                        ah[:,k,None]*bl[k,None,:],ah[:,k,None]*bh[k,None,:]])
        lo=down(lo+down(terms.min(axis=0)));hi=up(hi+up(terms.max(axis=0)))
    return lo,hi


def trig_range(lo, hi, cosine=False):
    if not math.isfinite(lo+hi) or hi<lo:raise ValueError('Invalid angular interval')
    if hi-lo>=2*math.pi:return -1.,1.
    offset=0. if cosine else math.pi/2
    fn=math.cos if cosine else math.sin
    values=[fn(lo),fn(hi)]
    for k in range(math.ceil((lo-offset)/math.pi),math.floor((hi-offset)/math.pi)+1):
        values.append(1. if k%2==0 else -1.)
    return float(down(min(values))),float(up(max(values)))


def rotation_interval(axis, lo, hi):
    axis=np.asarray(axis,float)
    if axis.shape!=(3,) or not np.isfinite(axis).all() or np.linalg.norm(axis)<=0:
        raise ValueError('Invalid interval rotation axis')
    axis=axis/np.linalg.norm(axis)
    outer=np.outer(axis,axis);coeff=np.eye(3)-outer
    x,y,z=axis;skew=np.array([[0,-z,y],[z,0,-x],[-y,x,0.]])
    sl,sh=trig_range(lo,hi);cl,ch=trig_range(lo,hi,True)
    low=down(down(outer+down(np.minimum(coeff*cl,coeff*ch)))+down(np.minimum(skew*sl,skew*sh)))
    high=up(up(outer+up(np.maximum(coeff*cl,coeff*ch)))+up(np.maximum(skew*sl,skew*sh)))
    a=np.eye(4);b=a.copy();a[:3,:3]=low;b[:3,:3]=high
    return a,b


def poses_interval(joints, nominal, half_widths):
    poses={'base_link':(np.eye(4),np.eye(4))}
    pending=list(joints)
    while pending:
        progress=False
        for joint in list(pending):
            if joint['parent'] not in poses:continue
            name=joint['name'];q=nominal.get(name,0.);h=half_widths.get(name,0.)
            if not math.isfinite(q+h) or h<0:raise ValueError('Invalid joint interval')
            motion=(np.eye(4),np.eye(4))
            if joint['type'] in ('revolute','continuous'):
                motion=rotation_interval(joint['axis'],float(down(q-h)),float(up(q+h)))
            elif joint['type']=='prismatic':
                a=np.eye(4);b=a.copy();values=np.stack([joint['axis']*(q-h),joint['axis']*(q+h)])
                a[:3,3]=down(values.min(axis=0));b[:3,3]=up(values.max(axis=0));motion=a,b
            elif joint['type']!='fixed':raise ValueError('Unsupported joint kind')
            origin=(joint['origin'],joint['origin'])
            poses[joint['child']]=multiply(multiply(poses[joint['parent']],origin),motion)
            pending.remove(joint);progress=True
        if not progress:raise ValueError('Disconnected interval model')
    return poses


def scene_separations(geometry, common, order, q, half_widths, indices):
    result=np.zeros(len(indices))
    scene_indices=[(k,i) for k,i in enumerate(indices) if geometry.pairs[i][1]>=geometry.robot_count]
    if not scene_indices:return result
    poses=poses_interval(geometry.joints,dict(geometry.auxiliary,**dict(zip(order,q))),dict(zip(order,half_widths)))
    boxes={}
    for k,i in scene_indices:
        a,b=geometry.pairs[i]
        if a not in boxes:
            shape=geometry.shapes[a]
            bounds=shape.mesh.bounds+np.array([[-1],[1]])*shape.geometry_error_m
            corners=common.fk.corners(*bounds)
            points=np.column_stack((corners,np.ones(len(corners)))).T
            low,high=multiply(poses[shape.link],(points,points))
            boxes[a]=(low[:3].min(axis=1),high[:3].max(axis=1))
        low_a,high_a=boxes[a]
        scene=geometry.shapes[b]
        if not np.array_equal(scene.pose,np.eye(4)):
            raise ValueError('Scene transform must be baked into fixed mesh')
        low_b,high_b=scene.mesh.bounds+np.array([[-1],[1]])*scene.geometry_error_m
        # A single separating coordinate suffices. max does not require
        # combining nominal distances or assuming correlated errors.
        result[k]=max(0.,float(np.maximum(down(low_a-high_b),down(low_b-high_a)).max()))
    return result
