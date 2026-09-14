"""Exact relative URDF chain for repeated offline CAD distance queries."""
import numpy as np


class RelativeChain:
    def __init__(self, joints, first_link, second_link, fk):
        self.fk=fk
        by_child={j['child']:j for j in joints}
        def chain(link):
            result=[];visited=set()
            while link in by_child:
                if link in visited:raise ValueError('Cyclic kinematic chain')
                visited.add(link);j=by_child[link];result.append(j);link=j['parent']
            return link,result[::-1]
        root_a,a=chain(first_link);root_b,b=chain(second_link)
        if root_a!=root_b:raise ValueError('Disconnected kinematic chains')
        while a and b and a[0]['name']==b[0]['name']:a=a[1:];b=b[1:]
        if any(j['type'] not in ('fixed','revolute','continuous') for j in a+b):
            raise ValueError('Unsupported relative joint type')
        self.a,self.b=a,b

    def evaluate(self,state):
        def product(chain):
            result=np.eye(4)
            for joint in chain:
                result=result@joint['origin']
                if joint['type']!='fixed':
                    angle=float(state.get(joint['name'],0.))
                    if not np.isfinite(angle):raise ValueError('Nonfinite joint angle')
                    rotation=self.fk.rotation_axis(joint['axis'],angle)
                    result[:3,:3]=result[:3,:3]@rotation
            return result
        a,b=product(self.a),product(self.b)
        if not self.a:return b
        inverse=np.eye(4);inverse[:3,:3]=a[:3,:3].T
        inverse[:3,3]=-a[:3,:3].T@a[:3,3]
        return inverse@b
