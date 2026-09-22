"""Contract/packaging regressions. These tests never contact the robot."""
import copy
import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch
import threading
import time
from types import SimpleNamespace
import xml.etree.ElementTree as ET

from scripts.box_handling.front_sps_contract import SelectionTransaction, validate_goal, wait_terminal_result
from scripts.box_handling.front_box_integration import build_bundle, META_ROOT, TASK_ROOT, SNAPSHOT
from scripts.box_handling import front_sps_session as session


class DiscoveryTest(unittest.TestCase):
    graph = ('/mc/manipulation/action : mc_task_msgs/action/ArmTask\n'
             '/cv/task/transport_action : cv_task_msgs/action/VisionActionTask\n')
    endpoints = ('/cv/task/sps_pose_action', '/cv/task/sps_select_action')

    def query(self, graph=None, info='\n', rc=0, stderr=''):
        def run(command):
            if command == 'action list --no-daemon -t':
                return subprocess.CompletedProcess(command, 0, self.graph if graph is None else graph, '')
            return subprocess.CompletedProcess(command, rc, info, stderr)
        return Mock(side_effect=run)

    def test_unused_sps_empty_info_with_populated_graph(self):
        # Captured on Motion 2026-09-22: rc=0, stdout='\n', stderr=''.
        query = self.query()
        self.assertEqual(session.check_sps_discovery(query), dict.fromkeys(self.endpoints, 'absent'))
        self.assertEqual(query.call_count, 3)

    def test_no_shm_notice_is_not_a_discovery_result(self):
        notice = ('I2026-09-22 14:57:56.776324 [1925.680208] 2848 '
                  '[context_options.cpp:97:operator()]: Shared memory mode is turned off.\n')
        query = self.query(notice+self.graph, notice+'\n')
        self.assertEqual(session.check_sps_discovery(query), dict.fromkeys(self.endpoints, 'absent'))
        # The notice alone cannot stand in for a healthy graph; other logs fail.
        for graph in (notice, notice+self.graph+'Shared memory mode is turned on.\n'):
            with self.assertRaises(RuntimeError):
                session.check_sps_discovery(self.query(graph))

    def test_initialized_clients_without_server(self):
        graph = self.graph + ''.join(e+' : cv_task_msgs/action/VisionActionTask\n' for e in self.endpoints)
        result = session.check_sps_discovery(self.query(graph, 'Action client count: 1\nAction server count: 0\n'))
        self.assertEqual(result, dict.fromkeys(self.endpoints, 'servers=0'))

    def test_real_server_rejected_even_if_appearing_after_list(self):
        for count in (1, 2):
            with self.subTest(count=count), self.assertRaisesRegex(RuntimeError, 'server already exists'):
                session.check_sps_discovery(self.query(info='Action server count: '+str(count)+'\n'))

    def test_failed_queries_never_mean_absent(self):
        for rc, stderr in ((124, ''), (1, 'transport unavailable'), (0, 'discovery error')):
            with self.subTest(rc=rc, stderr=stderr), self.assertRaisesRegex(RuntimeError, 'discovery failed'):
                session.check_sps_discovery(self.query(rc=rc, stderr=stderr))
        with self.assertRaisesRegex(RuntimeError, 'rc=124'):
            session.check_sps_discovery(lambda cmd: subprocess.CompletedProcess(cmd, 124, '', ''))

    def test_empty_partial_malformed_or_duplicate_graph_rejected(self):
        for graph in ('', self.graph.splitlines()[0], self.graph+'unexpected\n', self.graph+self.graph):
            with self.subTest(graph=graph), self.assertRaises(RuntimeError):
                session.check_sps_discovery(self.query(graph))

    def test_listed_endpoint_with_empty_info_is_inconsistent(self):
        graph = self.graph+self.endpoints[0]+' : cv_task_msgs/action/VisionActionTask\n'
        with self.assertRaisesRegex(RuntimeError, 'inconsistent'):
            session.check_sps_discovery(self.query(graph))

    def test_wrong_sps_type_rejected(self):
        graph = self.graph+self.endpoints[0]+' : wrong/action/Type\n'
        with self.assertRaisesRegex(RuntimeError, 'Unexpected SPS action type'):
            session.check_sps_discovery(self.query(graph, 'Action server count: 0\n'))

    def test_unknown_output_or_ambiguous_counts_rejected(self):
        for info in ('unknown action', 'Action server count: -1\n',
                     'Action server count: 0\nAction server count: 1\n'):
            with self.subTest(info=info), self.assertRaisesRegex(RuntimeError, 'inconsistent'):
                session.check_sps_discovery(self.query(info=info))

    def test_check_runtime_returns_before_adapter_or_task_start(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root/'manifest.json').write_text(json.dumps(dict(id='fixture', sources={}, robot_files={}, native_binaries={})))
            controllers = [dict(name=name, state=state) for name, state in (
                ('manipulation_controller', 'running'), ('vla_sdk_controller', 'initialized'),
                ('sdk_controller', 'initialized'))]
            def run(cmd, **kwargs):
                shell = cmd[5]
                if cmd[2] == session.NATIVE:
                    self.assertIn('ROSA_USE_SHM=OFF', shell)
                if 'rosa action list' in shell: output = self.graph
                elif 'rosa action info' in shell: output = '\n'
                elif 'ros2 topic echo' in shell: output = 'status_list: []\n'
                elif 'rosa service call' in shell: output = 'Response(controller='+repr(controllers)+')\n'
                else: self.fail('Unexpected command: '+str(cmd))
                return subprocess.CompletedProcess(cmd, 0, output, '')
            with patch('sys.argv', ['front_sps_session', '--package', str(root), '--check-runtime']), \
                    patch.object(session.fcntl, 'flock'), \
                    patch.object(session.subprocess, 'check_output', return_value='true\n'), \
                    patch.object(session.subprocess, 'run', side_effect=run), \
                    patch.object(session.subprocess, 'Popen', side_effect=AssertionError('No processes')), \
                    patch.object(session.tempfile, 'mkdtemp', side_effect=AssertionError('No session')), \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(session.main(), 0)
            self.assertIn('CHECK_SPS_RUNTIME_OK', output.getvalue())


def report():
    def pose(x,y,z):
        return dict(position=dict(x=x,y=y,z=z),orientation=dict(x=0.,y=0.,z=0.,w=1.))
    header=dict(frame_id='stereo_left_rectified_optical_frame',stamp=dict(sec=100,nanosec=0))
    return dict(status=4,request_ns=99_900_000_000,goal_id='raw-goal',
        vision_result=dict(ok=True,trans_outputs=dict(camera_name='head',object_name='workbin',
            box_pose=dict(header=header,poses=[pose(1.,.7,1.3),pose(1.,.02,.4)]))),
        tf_at_detection=dict(header=dict(frame_id='base_link',stamp=copy.deepcopy(header['stamp'])),
            child_frame_id=header['frame_id'],transform=dict(translation=dict(x=.2,y=0.,z=0.),
            rotation=dict(x=0.,y=0.,z=0.,w=1.))))


class ContractTest(unittest.TestCase):
    def test_stack_selection_returns_original_camera_pose_of_top(self):
        r=report()
        top=r['vision_result']['trans_outputs']['box_pose']['poses'][1]
        support=copy.deepcopy(top)
        support['position']['z']-=.22
        r['vision_result']['trans_outputs']['box_pose']['poses'].append(support)
        tx=SelectionTransaction()
        result=tx.detect(r,100_100_000_000)
        self.assertEqual(result['sps_outputs']['poses'],[top])
        selected,pending=tx.select(100_200_000_000)
        self.assertEqual(selected['sps_outputs']['poses'],[top])
        self.assertNotEqual(top['position']['x'],pending['selection']['selected_pose']['position']['x'])

    def test_get_result_waits_for_terminal_state(self):
        results={'goal':SimpleNamespace(status=2)};lock=threading.Lock()
        def complete():
            time.sleep(.03)
            with lock:results['goal']=SimpleNamespace(status=4,result='actual-pose')
        thread=threading.Thread(target=complete);thread.start()
        result=wait_terminal_result(results,lock,'goal',timeout=.3)
        thread.join()
        self.assertEqual(result.result,'actual-pose')
        self.assertEqual(result.status,4)
        with self.assertRaises(TimeoutError):wait_terminal_result({},lock,'unknown',timeout=.01)

    def test_original_camera_pose_and_same_transaction(self):
        tx=SelectionTransaction();r=report();before=copy.deepcopy(r)
        approx=tx.detect(r,100_100_000_000)
        selected,evidence=tx.select(100_200_000_000)
        self.assertEqual(approx,selected)
        self.assertEqual(selected['sps_outputs']['poses'],[r['vision_result']['trans_outputs']['box_pose']['poses'][1]])
        self.assertEqual(evidence['selection']['selected_index'],1)
        self.assertAlmostEqual(evidence['selection']['selected_pose']['position']['x'],1.2)
        self.assertEqual(r,before)

    def test_no_cached_selection_without_detection(self):
        tx=SelectionTransaction()
        with self.assertRaises(ValueError):tx.select(100_200_000_000)
        self.assertTrue(tx.failed)
        with self.assertRaises(ValueError):tx.detect(report(),100_100_000_000)

    def test_single_use(self):
        tx=SelectionTransaction();tx.detect(report(),100_100_000_000);tx.select(100_200_000_000)
        with self.assertRaises(ValueError):tx.select(100_300_000_000)

    def test_overlap_invalidates_instead_of_replacing(self):
        tx=SelectionTransaction();tx.detect(report(),100_100_000_000)
        with self.assertRaises(ValueError):tx.detect(report(),100_200_000_000)
        self.assertIsNone(tx.pending)

    def test_expiration_future_and_cancel_reject(self):
        for now in (99_000_000_000,102_000_000_001):
            tx=SelectionTransaction();tx.detect(report(),100_100_000_000)
            with self.assertRaises(ValueError):tx.select(now)
        tx=SelectionTransaction();tx.detect(report(),100_100_000_000);tx.invalidate()
        with self.assertRaises(ValueError):tx.select(100_200_000_000)

    def test_wrong_tf_time_and_frames_rejected(self):
        for key,value in [('child_frame_id','other')]:
            r=report();r['tf_at_detection'][key]=value
            with self.assertRaises(ValueError):SelectionTransaction().detect(r,100_100_000_000)
        r=report();r['tf_at_detection']['header']['stamp']['nanosec']=1
        with self.assertRaises(ValueError):SelectionTransaction().detect(r,100_100_000_000)

    def test_no_empty_or_ambiguous_success(self):
        for poses in ([],[dict(position=dict(x=1.,y=0.,z=z),orientation=dict(x=0.,y=0.,z=0.,w=1.)) for z in (.4,1.3)]):
            r=report();r['vision_result']['trans_outputs']['box_pose']['poses']=poses
            with self.assertRaises(ValueError):SelectionTransaction().detect(r,100_100_000_000)

    def test_only_expected_native_request(self):
        goal=dict(task_type='SPS',sps_inputs=dict(object_name='box',select_id=0))
        validate_goal(goal)
        for field,value in [('object_name','ti_box'),('select_id',1),('need_pcd',True),('need_mask',True),('tracking_mode',1),('box_size',dict(x=.6))]:
            changed=copy.deepcopy(goal);changed['sps_inputs'][field]=value
            with self.assertRaises(ValueError):validate_goal(changed)
        goal['task_type']='transport'
        with self.assertRaises(ValueError):validate_goal(goal)


class PackageTest(unittest.TestCase):
    def test_yaml_preserves_all_trajectory_and_limit_bytes(self):
        bundle=build_bundle()
        yaml=bundle['tasks'][META_ROOT+'local_front_box/separate_right_cruzr.yaml']
        self.assertEqual(yaml.replace('  special_box_name: box\n',''),
                         (SNAPSHOT/'meta_clamp/wrc/separate_right_cruzr.yaml').read_text())

    def test_pure_native_check_cannot_move(self):
        root=ET.fromstring(build_bundle()['tasks'][TASK_ROOT+'local_front_box/detect_only.xml'])
        self.assertEqual([n.get('ID') for n in root.iter('Action')],['MetaLook','MetaLook'])
        self.assertEqual(list(root.iter('Action'))[1].get('object_name'),'box')

    def test_grasp_only_adds_sps_and_changes_config_reference(self):
        root=ET.fromstring(build_bundle()['tasks'][TASK_ROOT+'local_front_box/separate_right_cruzr.xml'])
        sequence=root.find('./BehaviorTree/Sequence');sequence.remove(sequence[0])
        for action in root.iter('Action'):
            if action.get('name')=='local_front_box/separate_right_cruzr':action.set('name','wrc/separate_right_cruzr')
        original=ET.fromstring((SNAPSHOT/'tasks/Singapore/separate_right_cruzr.xml').read_text())
        def elements(tree):return [(node.tag,node.attrib) for node in tree.iter()]
        self.assertEqual(elements(root),elements(original))


if __name__=='__main__':unittest.main()
