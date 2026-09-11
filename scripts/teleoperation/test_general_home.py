"""Offline functional tests: collision solids, swept edges, search and input gates."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
from general_home.geometry import RobotGeometry, Shape, solid_distance, finite_vector
from general_home.inputs import load_state, load_json
from general_home.planner import Validator, plan, segment_seconds, retime, BudgetExceeded
from cruzr_pico_to_home_owner_gate import JOINT_ORDER
from general_home.native_spline import NativeSplineEmulator, cubic_hermite


class DiskWorld:
    """Independent 2D distance oracle, for testing search/certification behavior."""
    def __init__(self, center=(.5, 0.), radius=.18):
        self.lower = np.array([-1., -1.])
        self.upper = np.array([1.5, 1.])
        self.center = np.array(center)
        self.radius = radius
        self.labels = [['moving_point', 'disk']]
        # Coordinate-wise |dx|+|dy| bounds Cartesian point travel.
        self.weights = np.ones((1, 2))

    def distances(self, q):
        return np.array([max(0., np.linalg.norm(q-self.center)-self.radius)])


def state_document():
    return dict(schema='cruzr-general-home-state-v1',
        captured_at=datetime.now(timezone.utc).isoformat(), source='unit_test_synthetic',
        empty_clamps=True, actuators_healthy=True, controller_idle=True,
        joint_state=dict(name=JOINT_ORDER[:], position=[0.]*20, velocity=[0.]*20))


class SolidTests(unittest.TestCase):
    def shape(self, size, location=(0,0,0), name='box'):
        mesh = trimesh.creation.box(extents=size)
        shape = Shape.from_mesh(name, name, mesh)
        transform = np.eye(4); transform[:3,3] = location
        shape.place(transform)
        return shape

    def test_mesh_solid_containment_is_collision_without_surface_intersection(self):
        outer, inner = self.shape([2,2,2]), self.shape([.1,.1,.1])
        self.assertEqual(solid_distance(outer, inner), 0.)
        self.assertEqual(solid_distance(inner, outer), 0.)

    def test_mesh_distance_and_surface_intersection(self):
        a = self.shape([1,1,1])
        self.assertAlmostEqual(solid_distance(a, self.shape([1,1,1], [1.3,0,0])), .3)
        self.assertEqual(solid_distance(a, self.shape([1,1,1], [.9,0,0])), 0.)

    def test_union_containment_does_not_treat_overlapping_shells_as_empty(self):
        a = trimesh.creation.box(extents=[2,2,2])
        b = a.copy(); b.apply_translation([.1,0,0])
        union = Shape.from_mesh('union','union',trimesh.util.concatenate([a,b]))
        inner = self.shape([.02,.02,.02], [.25,.25,.25])
        self.assertEqual(solid_distance(union, inner), 0.)

    def test_open_mesh_retains_full_enclosure(self):
        mesh = trimesh.creation.box(extents=[2,2,2])
        mesh.update_faces(np.arange(len(mesh.faces)-1))
        shell = Shape.from_mesh('open','open',mesh)
        self.assertTrue(shell.convex)
        self.assertEqual(solid_distance(shell, self.shape([.1,.1,.1])), 0.)

    def test_closed_parts_sharing_edge_do_not_become_one_convex_hull(self):
        first=trimesh.creation.box(extents=[1,1,1])
        second=first.copy();second.apply_translation([1,1,0])
        source=trimesh.util.concatenate([first,second]);source.merge_vertices()
        self.assertFalse(source.is_watertight)
        fixed=Shape.from_mesh('assembly','assembly',source)
        self.assertEqual(fixed.representation,'closed_component_union_exact_triangles')
        self.assertEqual(len(source.faces),len(fixed.mesh.faces))
        # The hull would fill this empty corner. Both original solids remain.
        self.assertGreater(solid_distance(fixed,self.shape([.1,.1,.1],[1,0,0])),.4)
        self.assertEqual(solid_distance(fixed,self.shape([.1,.1,.1],[1,1,0])),0.)

    def test_numeric_seam_preserves_triangles_and_charges_error_to_distance(self):
        mesh=trimesh.creation.box(extents=[1,1,1]); mesh.unmerge_vertices()
        mesh.vertices[0,0] += 5e-9
        fixed=Shape.from_mesh('seam','seam',mesh)
        self.assertEqual(fixed.representation,'closed_component_union_bounded_numeric_weld')
        self.assertEqual(len(fixed.mesh.faces),len(mesh.faces))
        self.assertGreater(fixed.geometry_error_m,0)
        self.assertLessEqual(fixed.geometry_error_m,1e-8)
        other=self.shape([1,1,1],[1.1,0,0])
        with_error=solid_distance(fixed,other)
        error=fixed.geometry_error_m; fixed.geometry_error_m=0
        self.assertAlmostEqual(solid_distance(fixed,other)-with_error,error,places=12)

    def test_larger_crack_is_not_repaired_as_a_numeric_seam(self):
        mesh=trimesh.creation.box(extents=[1,1,1]); mesh.unmerge_vertices()
        mesh.vertices[0,0] += 5e-5
        fixed=Shape.from_mesh('crack','crack',mesh)
        self.assertTrue(fixed.convex)
        self.assertEqual(fixed.geometry_error_m,0)


class NativeMathTests(unittest.TestCase):
    def test_cubic_rest_is_monotonic_and_uses_common_progress(self):
        a=np.array([-1.,.5]);b=np.array([2.,-.2]);zero=np.zeros(2)
        path=np.array([cubic_hermite(a,b,zero,zero,4.,t) for t in np.linspace(0,4,1001)])
        np.testing.assert_allclose(path[0],a);np.testing.assert_allclose(path[-1],b)
        progress=(path-a)/(b-a)
        self.assertTrue((np.diff(progress,axis=0)>=-1e-12).all())
        np.testing.assert_allclose(progress[:,0],progress[:,1],atol=1e-14)
        np.testing.assert_allclose(cubic_hermite([0],[1],[0],[0],4.,1.),[.15625])

    def test_nonzero_boundary_velocity_can_leave_the_endpoint_segment(self):
        self.assertAlmostEqual(cubic_hermite([0],[0],[1],[-1],1.,.5)[0],.25)

    def test_unreviewed_binary_is_rejected_before_emulation(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'changed.so';path.write_bytes(b'not the pinned vendor function')
            with self.assertRaisesRegex(ValueError,'hash'):NativeSplineEmulator(path)

    def test_invalid_vectors_and_time_reject(self):
        for args in [([0],[1,2],[0],[0],1,.5),([0],[1],[0],[0],0,0),
                     ([0],[1],[0],[0],1,1.01),([float('nan')],[1],[0],[0],1,0)]:
            with self.assertRaises(ValueError):cubic_hermite(*args)

    def test_cubic_timing_obeys_velocity_acceleration_without_claiming_bounded_jerk(self):
        path=[np.zeros(20),np.linspace(-1,1,20),np.zeros(20)]
        for step in retime(path,law='cubic-rest'):
            self.assertLessEqual(max(step['peak_velocity_rad_s']),.3)
            self.assertLessEqual(max(step['peak_acceleration_rad_s2']),.35)
            self.assertIsNone(step['peak_jerk_rad_s3'])
            self.assertFalse(step['jerk_bound_including_waypoints'])
        with self.assertRaises(ValueError):retime(path,law='linear')

    def test_cubic_plan_preserves_geometric_gate_and_physical_rejection(self):
        result=plan(DiskWorld(center=(.5,3)),[1.,0.],timing_law='cubic-rest')
        self.assertEqual(result['status'],'GEOMETRIC_CANDIDATE')
        self.assertEqual(result['timing_law'],'cubic-rest')
        self.assertFalse(result['native_group_execution_verified'])
        self.assertFalse(result['physical_approval'])
        self.assertTrue(all(s['timing_law']=='cubic-rest' for s in result['steps']))


class ValidatorTests(unittest.TestCase):
    def test_asynchronous_progress_can_collide_despite_safe_diagonal(self):
        validator=Validator(DiskWorld(center=(.25,.75),radius=.04),clearance=.01)
        a,b=np.array([0.,0.]),np.array([1.,1.])
        self.assertTrue(validator.edge(a,b))
        self.assertFalse(validator.independent_progress(a,b))

    def test_independent_joint_box_can_be_certified(self):
        validator=Validator(DiskWorld(center=(.5,3.)),clearance=.01)
        self.assertTrue(validator.independent_progress([0.,0.],[1.,1.]))

    def test_independent_box_finds_small_off_diagonal_obstacle(self):
        validator=Validator(DiskWorld(center=(.37,.71),radius=.0002),clearance=0)
        self.assertFalse(validator.independent_progress([0.,0.],[1.,1.]))

    def test_independent_box_rejects_outside_limits_and_insufficient_resolution(self):
        validator=Validator(DiskWorld(center=(.37,.71),radius=.0002),clearance=0,max_depth=1)
        self.assertFalse(validator.independent_progress([0.,0.],[1.,1.]))
        self.assertGreater(validator.unresolved_edges,0)
        self.assertFalse(validator.independent_progress([0.,0.],[2.,1.]))

    def test_free_endpoints_do_not_hide_midsegment_obstacle(self):
        validator = Validator(DiskWorld(), clearance=.01)
        a,b = np.array([0.,0.]), np.array([1.,0.])
        self.assertTrue(validator.state(a)); self.assertTrue(validator.state(b))
        self.assertFalse(validator.edge(a,b))

    def test_off_midpoint_thin_obstacle_is_not_skipped(self):
        validator = Validator(DiskWorld(center=(.371,0),radius=.0002), clearance=0)
        self.assertFalse(validator.edge(np.array([0.,0.]),np.array([1.,0.])))

    def test_subdivision_proves_safe_segment(self):
        validator = Validator(DiskWorld(), clearance=.01)
        self.assertTrue(validator.edge(np.array([0.,.3]),np.array([1.,.3])))
        self.assertGreater(validator.state_queries, 3)

    def test_subdivision_exhaustion_rejects_instead_of_certifying(self):
        validator = Validator(DiskWorld(center=(.371,0),radius=.0002), clearance=0, max_depth=1)
        self.assertFalse(validator.edge(np.array([0.,0.]),np.array([1.,0.])))
        self.assertEqual(validator.unresolved_edges,1)

    def test_extra_error_budget_can_reject_nominal_clearance(self):
        q=np.array([.5,.2])
        self.assertTrue(Validator(DiskWorld(), clearance=.01).state(q))
        self.assertFalse(Validator(DiskWorld(), clearance=.01,extra_margin=[.02]).state(q))

    def test_deadline_is_enforced(self):
        validator=Validator(DiskWorld(),deadline=time.monotonic()-1)
        with self.assertRaises(BudgetExceeded): validator.state(np.zeros(2))


class PlannerTests(unittest.TestCase):
    def test_direct_short_route_and_home_noop(self):
        world=DiskWorld(center=(0,3))
        result=plan(world,[.05,.02])
        self.assertEqual(result['status'],'GEOMETRIC_CANDIDATE')
        self.assertEqual(result['method'],'direct')
        self.assertEqual(len(result['steps']),1)
        self.assertFalse(result['installable'])
        self.assertEqual(plan(world,[0,0])['status'],'ALREADY_HOME_NUMERIC')

    def test_rrt_goes_around_obstacle_and_every_edge_passes(self):
        world=DiskWorld()
        result=plan(world,[1.,0.],timeout=5,seed=11)
        self.assertEqual(result['status'],'GEOMETRIC_CANDIDATE', result)
        self.assertEqual(result['method'],'rrt_connect')
        path=[np.array(q) for q in result['waypoints_rad']]
        self.assertGreater(len(path),2)
        validator=Validator(world)
        self.assertTrue(all(validator.edge(a,b) for a,b in zip(path,path[1:])))
        np.testing.assert_array_equal(path[0],[1.,0.]);np.testing.assert_array_equal(path[-1],[0.,0.])
        for a,b in zip(path,path[1:]):
            dense=a+(b-a)*np.linspace(0,1,10001)[:,None]
            self.assertGreater(float(np.linalg.norm(dense-world.center,axis=1).min()),world.radius+.002)

    def test_start_and_goal_conflicts_not_ignored(self):
        self.assertEqual(plan(DiskWorld(),[.5,0])['status'],'START_GEOMETRY_REJECTED')
        self.assertEqual(plan(DiskWorld(center=(0,0)),[1,0])['status'],'HOME_GEOMETRY_REJECTED')
        self.assertEqual(plan(DiskWorld(),[8,0])['status'],'START_OUTSIDE_LIMITS')

    def test_search_exhaustion_is_not_a_route_or_proof_of_impossibility(self):
        result=plan(DiskWorld(radius=.8),[-.8,0],max_iterations=1)
        # HOME is inside this obstacle, so reject before spending a search budget.
        self.assertEqual(result['status'],'HOME_GEOMETRY_REJECTED')
        class Barrier(DiskWorld):
            def distances(self,q):return np.array([max(0.,abs(q[0]-.5)-.1)])
        result=plan(Barrier(),[1.,0.],max_iterations=1,seed=8)
        self.assertEqual(result['status'],'SEARCH_EXHAUSTED')
        self.assertEqual(result['steps'],[])

    def test_retiming_caps_and_continuity(self):
        path=[np.zeros(20),np.linspace(-1,1,20),np.zeros(20)]
        steps=retime(path)
        np.testing.assert_array_equal(steps[0]['end_rad'],steps[1]['start_rad'])
        for step in steps:
            self.assertLessEqual(max(step['peak_velocity_rad_s']),.3)
            self.assertLessEqual(max(step['peak_acceleration_rad_s2']),.35)
            self.assertLessEqual(max(step['peak_jerk_rad_s3']),1.5)
        self.assertEqual(segment_seconds(path[0],path[0]),0.)
        with self.assertRaises(ValueError):segment_seconds(path[0],path[1],caps=(0,1,1))


class InputTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.file=Path(self.tmp.name)/'state.json'

    def load(self,data):
        self.file.write_text(json.dumps(data));return load_state(self.file)

    def test_named_joint_reordering_and_archive_provenance(self):
        data=state_document()
        data['joint_state']['position'][2]=.1
        for key in ('name','position','velocity'):data['joint_state'][key].reverse()
        q,info,_=self.load(data)
        self.assertAlmostEqual(q[2],.1)
        self.assertFalse(info['live_authorization'])

    def test_missing_duplicate_unknown_or_nonnumeric_joint_rejected(self):
        for mutation in ('missing','duplicate','unknown','bool','nan','moving'):
            with self.subTest(mutation=mutation):
                data=state_document();raw=data['joint_state']
                if mutation=='missing':raw['position'].pop()
                if mutation=='duplicate':raw['name'][1]=raw['name'][0]
                if mutation=='unknown':raw['name'][0]='unknown'
                if mutation=='bool':raw['position'][0]=True
                if mutation=='nan':raw['position'][0]=float('nan')
                if mutation=='moving':raw['velocity'][0]=.003
                with self.assertRaises(ValueError):self.load(data)

    def test_cargo_fault_active_controller_or_time_missing_rejected(self):
        for key,value in [('empty_clamps',False),('actuators_healthy',False),('controller_idle',False),
                          ('captured_at','2026-01-01T00:00:00'),('captured_at',None),
                          ('captured_at',(datetime.now(timezone.utc)+timedelta(days=1)).isoformat())]:
            data=state_document();data[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):self.load(data)

    def test_duplicate_json_keys_rejected(self):
        self.file.write_text('{"empty_clamps":false,"empty_clamps":true}')
        with self.assertRaises(ValueError):load_json(self.file)

    def test_cli_never_accepts_run_install_reload(self):
        script=Path(__file__).with_name('cruzr_plan_home.py')
        for flag in ('--run','--install','--reload'):
            p=subprocess.run([sys.executable,str(script),flag],capture_output=True,text=True,timeout=5)
            self.assertNotEqual(p.returncode,0)


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        # A 20D URDF with one independently moving tip and a fixed reference
        # body; the other 19 joints have empty frames, explicitly diagnosed.
        pieces=['<robot name="fixture"><link name="base_link"/>',
                '<link name="tip"><collision><origin xyz="1 0 0"/>'
                '<geometry><box size=".05 .05 .05"/></geometry></collision></link>',
                '<joint name="'+JOINT_ORDER[0]+'" type="revolute"><parent link="base_link"/>'
                '<child link="tip"/><axis xyz="0 0 1"/><limit lower="-3" upper="3" velocity="1"/></joint>']
        for index,name in enumerate(JOINT_ORDER[1:],1):
            pieces.extend([f'<link name="empty{index}"/>',
                f'<joint name="{name}" type="revolute"><parent link="base_link"/><child link="empty{index}"/>'
                '<axis xyz="0 0 1"/><limit lower="-3" upper="3" velocity="1"/></joint>'])
        pieces.append('</robot>')
        self.urdf=self.root/'fixture.urdf';self.urdf.write_text(''.join(pieces))
        self.scene=dict(frame_id='base_link',complete=True,objects=[])

    def test_model_scene_collision_and_arc_certificate(self):
        self.scene['objects']=[dict(id='wall',type='box',size_m=[.05,.05,.05],center_m=[1,0,0],rpy_rad=[0,0,0])]
        model=RobotGeometry(self.urdf,self.root,self.scene)
        validator=Validator(model)
        a=np.zeros(20);b=a.copy();a[0]=-.3;b[0]=.3
        self.assertTrue(validator.state(a));self.assertTrue(validator.state(b))
        self.assertFalse(validator.edge(a,b))
        self.assertTrue(model.source_files_unchanged())
        self.urdf.write_text(self.urdf.read_text()+'\n')
        self.assertFalse(model.source_files_unchanged())

    def test_empty_pair_set_is_valid_but_missing_geometry_is_reported(self):
        model=RobotGeometry(self.urdf,self.root,self.scene)
        self.assertEqual(model.weights.shape,(0,20))
        self.assertTrue(model.diagnostics['links_without_geometry'])
        result=plan(model,np.full(20,.01))
        self.assertEqual(result['status'],'GEOMETRIC_CANDIDATE')
        self.assertFalse(result['physical_approval'])

    def test_asymmetric_20d_start_is_preserved_without_copying_pico(self):
        model=RobotGeometry(self.urdf,self.root,self.scene)
        q=np.zeros(20);q[0]=-.4;q[7]=-.1;q[12]=.2
        result=plan(model,q)
        self.assertEqual(result['status'],'GEOMETRIC_CANDIDATE')
        np.testing.assert_array_equal(result['steps'][0]['start_rad'],q)
        np.testing.assert_array_equal(result['steps'][-1]['end_rad'],np.zeros(20))

    def test_only_fixed_assembly_pairs_are_omitted(self):
        text=self.urdf.read_text()
        part='<collision><origin xyz="1 0 0"/><geometry><box size=".05 .05 .05"/></geometry></collision>'
        extra=f'<link name="fixed_tip">{part}</link><joint name="mate" type="fixed"><parent link="tip"/><child link="fixed_tip"/></joint>'
        text=text.replace('</robot>',extra+'</robot>')
        text=text.replace('<link name="empty1"/>',f'<link name="empty1">{part}</link>')
        self.urdf.write_text(text)
        model=RobotGeometry(self.urdf,self.root,self.scene)
        self.assertIn(['tip#0','fixed_tip#0'],model.diagnostics['rigid_internal_pairs'])
        self.assertIn(['tip#0','empty1#0'],model.labels)
        self.assertEqual(plan(model,np.zeros(20))['status'],'START_GEOMETRY_REJECTED')

    def test_missing_mesh_is_an_error_not_missing_obstacle(self):
        text=self.urdf.read_text().replace('<box size=".05 .05 .05"/>',
            '<mesh filename="package://cruzr_s2_description/absent.stl"/>')
        self.urdf.write_text(text)
        with self.assertRaises(OSError):RobotGeometry(self.urdf,self.root,self.scene)

    def test_mimic_unknown_links_and_zero_axes_are_rejected(self):
        original=self.urdf.read_text()
        for changed in (original.replace('</joint>','<mimic joint="coupled"/></joint>',1),
                        original.replace('child link="tip"','child link="absent"',1),
                        original.replace('axis xyz="0 0 1"','axis xyz="0 0 0"',1)):
            self.urdf.write_text(changed)
            with self.assertRaises(ValueError):RobotGeometry(self.urdf,self.root,self.scene)

    def test_cli_fixture_plan_and_no_overwrite(self):
        data=state_document();data['joint_state']['position'][0]=-.1
        state=self.root/'state.json';state.write_text(json.dumps(data))
        scene=self.root/'scene.json';scene.write_text(json.dumps(dict(self.scene,
            schema='cruzr-general-home-scene-v1',captured_at=data['captured_at'],source='unit_test')))
        output=self.root/'plan.json'
        cmd=[sys.executable,str(Path(__file__).with_name('cruzr_plan_home.py')),'--plan',
            '--state',str(state),'--scene',str(scene),'--urdf',str(self.urdf),
            '--package-root',str(self.root),'--output',str(output)]
        run=subprocess.run(cmd,capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stderr)
        report=json.loads(output.read_text())
        self.assertEqual(report['status'],'GEOMETRIC_CANDIDATE')
        self.assertFalse(report['physical_approval'])
        self.assertTrue(report['independent_joint_progress']['separated'])
        self.assertFalse(report['independent_joint_progress']['physical_execution_verified'])
        self.assertIn('motion_trajectory_adapter_not_qualified',report['activation_blockers'])
        original=output.read_bytes()
        run=subprocess.run(cmd,capture_output=True,text=True,timeout=10)
        self.assertNotEqual(run.returncode,0)
        self.assertEqual(output.read_bytes(),original)

    def test_bad_frame_incomplete_scene_and_negative_size_rejected(self):
        for change in ({'frame_id':'map'},{'complete':False},{'objects':[dict(id='bad',type='box',size_m=[-1,1,1],center_m=[0,0,0],rpy_rad=[0,0,0])]}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                RobotGeometry(self.urdf,self.root,dict(self.scene,**change))


if __name__=='__main__':
    unittest.main()
