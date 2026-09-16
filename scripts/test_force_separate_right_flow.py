"""Pruebas offline del orden y abortos; no conecta ni mueve el robot."""
import http.server
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest


FAKE_ROSA = r'''#!/usr/bin/env python3
import json, os, sys
goal = json.loads(sys.argv[-1])
name = goal.get('task_name', goal.get('command'))
from pathlib import Path
log = Path(os.environ['CALL_LOG'])
previous = [json.loads(x).get('command') for x in log.read_text().splitlines()] if log.exists() else []
with open(os.environ['CALL_LOG'], 'a') as f:
    f.write(json.dumps(goal) + '\n')
if name == os.environ.get('TIMEOUT_AT'):
    raise SystemExit(124)
result = {'state': {'desc': 'SUCCEED', 'state': 1101001}}
status = 4
if name == 'get_map_name':
    result['result_json'] = json.dumps({'map_name': 'utars_nav_map' if 'map_set' in previous else os.environ.get('TEST_MAP', 'utars_nav_map')})
elif name == 'check_state':
    result['dmsg'] = '当前FSM: ' + ('FSM_WAITNAVIGATE' if 'relocation_start' in previous and not os.environ.get('STILL_UNLOCALIZED') else os.environ.get('TEST_STATE', 'FSM_WAITNAVIGATE'))
elif name == 'navigation_start':
    assert json.loads(goal['arg_json'])['target_point'] == {
        'map_name': 'utars_nav_map', 'mode': 'logo_nav', 'id': json.loads(goal['arg_json'])['target_point']['id']}
    assert json.loads(goal['arg_json'])['target_point']['id'] in ('get1','put1')
    result['dmsg'] = 'navigation_start SUCCEEDED'
if name == os.environ.get('FAIL_AT'):
    result['state']['desc'] = 'VSLAM_MAP_DIR_ERROR' if name == 'navigation_start' else 'ClampJointTrackingError'
    status = 4 if name == 'navigation_start' else 6
print('Goal accepted with ID: offline-test')
print(f'Result: result={result!r}, status={status}')
'''


class FlowTest(unittest.TestCase):
    def run_flow(self, *, point=True, mode='run', **overrides):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path != '/map/get/utars_nav_map':
                    self.send_error(404)
                    return
                self.rfile.read(int(self.headers['Content-Length']))
                points = [{'id': 'put1', 'mode': 'logo_nav', 'point_x': 1.0,
                           'point_y': 2.0, 'point_yaw': 0.5},
                          {'id': 'get1', 'mode':'logo_nav', 'point_x':0.0, 'point_y':0.0,'point_yaw':0.0}] if point else []
                body = json.dumps({'code': 200, 'message': json.dumps(
                    {'umap': {'target_points': points}})}).encode()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                fake = root / 'rosa'
                fake.write_text(FAKE_ROSA)
                fake.chmod(0o755)
                source = Path(__file__).with_name('force_separate_right_cruzr.sh').read_text()
                inner = source.split("<<'INNER'\n", 1)[1].split('\nINNER\n', 1)[0]
                inner = inner.replace('source /opt/walker/setup.bash', ': # offline setup')
                inner = inner.replace('http://192.168.11.3:30023',
                                      f'http://127.0.0.1:{server.server_port}')
                log = root / 'calls.jsonl'
                env = dict(os.environ, PATH=f'{root}:' + os.environ['PATH'],
                           CALL_LOG=str(log), **overrides)
                result = subprocess.run(['bash', '-s', '--', mode], input=inner,
                                        text=True, capture_output=True, env=env, timeout=15)
                calls = [json.loads(line) for line in log.read_text().splitlines()]
                return result, [x.get('task_name', x.get('command')) for x in calls]
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_complete_order(self):
        result, calls = self.run_flow()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ['get_map_name', 'check_state', 'get_map_name', 'check_state', 'navigation_start',
            'vision/enable_transport_vision_switch', 'Singapore/separate_right_cruzr',
            'cruzr/mobot_back_20', 'navigation_start',
            'wrc_cruzr/put_cruzr_wrc_low', 'cruzr/home'])

    def test_missing_destination_before_grasp(self):
        result, calls = self.run_flow(point=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, ['get_map_name', 'check_state'])

    def test_check_does_not_move(self):
        result, calls = self.run_flow(mode='check')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ['get_map_name', 'check_state'])

    def test_wrong_map_does_not_move(self):
        result, calls = self.run_flow(mode='check', TEST_MAP='otro')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, ['get_map_name', 'check_state'])

    def test_wrong_map_prepared_before_navigation(self):
        result, calls = self.run_flow(TEST_MAP='otro')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(calls[:7], ['get_map_name','check_state','map_set','relocation_start','get_map_name','check_state','navigation_start'])

    def test_same_map_unlocalized_only_relocalizes(self):
        result, calls = self.run_flow(TEST_STATE='FSM_WAITRELOCATE')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertNotIn('map_set',calls)
        self.assertEqual(calls.count('relocation_start'),1)

    def test_failed_preparation_never_moves(self):
        for failure in ('map_set','relocation_start'):
            result,calls=self.run_flow(TEST_MAP='otro', FAIL_AT=failure)
            self.assertNotEqual(result.returncode,0)
            self.assertNotIn('navigation_start',calls)
            self.assertNotIn('Singapore/separate_right_cruzr',calls)

    def test_relocation_timeout_never_moves(self):
        result,calls=self.run_flow(TEST_STATE='FSM_WAITRELOCATE',TIMEOUT_AT='relocation_start')
        self.assertNotEqual(result.returncode,0)
        self.assertNotIn('navigation_start',calls)
        self.assertEqual(calls.count('relocation_start'),1)

    def test_unconfirmed_localization_never_moves(self):
        result,calls=self.run_flow(TEST_STATE='FSM_WAITRELOCATE',STILL_UNLOCALIZED='1')
        self.assertNotEqual(result.returncode,0)
        self.assertNotIn('navigation_start',calls)

    def test_busy_state_not_overridden(self):
        result,calls=self.run_flow(TEST_STATE='FSM_NAVIGATING',TEST_MAP='otro')
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(calls,['get_map_name','check_state'])

    def test_grasp_failure_stops_sequence(self):
        result, calls = self.run_flow(FAIL_AT='Singapore/separate_right_cruzr')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls[-1], 'Singapore/separate_right_cruzr')

    def test_navigation_error_even_with_status_four_stops(self):
        result, calls = self.run_flow(FAIL_AT='navigation_start')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls[-2:], ['navigation_start', 'navigation_stop'])
        self.assertNotIn('wrc_cruzr/put_cruzr_wrc_low', calls)

    def test_navigation_timeout_requests_stop(self):
        result, calls = self.run_flow(TIMEOUT_AT='navigation_start')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls[-2:], ['navigation_start', 'navigation_stop'])

    def test_deposit_failure_never_sends_home(self):
        result, calls = self.run_flow(FAIL_AT='wrc_cruzr/put_cruzr_wrc_low')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls[-1], 'wrc_cruzr/put_cruzr_wrc_low')
        self.assertNotIn('cruzr/home', calls)


if __name__ == '__main__':
    unittest.main()
