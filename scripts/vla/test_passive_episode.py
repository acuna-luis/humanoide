"""Offline capture contract checks. No ROS, SSH, robot, or third party modules."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

from . import passive_episode_remote as remote
from . import passive_episode_quality as quality

NAMES = ['joint_'+str(i)+'_joint' for i in range(20)]
START = 10**12


class Pixels(unittest.TestCase):
    def test_bgr_padding_decoded_to_actual_rgb_png(self):
        data = remote.png_bytes(2, 1, 8, 'bgr8', bytes([0,0,255,0,255,0,99,99]))
        self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
        chunks, offset = {}, 8
        while offset < len(data):
            size = struct.unpack('!I',data[offset:offset+4])[0]
            kind = data[offset+4:offset+8];payload=data[offset+8:offset+8+size]
            crc=struct.unpack('!I',data[offset+8+size:offset+12+size])[0]
            self.assertEqual(crc,zlib.crc32(kind+payload)&0xffffffff)
            chunks[kind]=payload;offset+=size+12
        self.assertEqual(zlib.decompress(chunks[b'IDAT']),bytes([0,255,0,0,0,255,0]))

    def test_bad_encoding_dimensions_or_truncation_rejected(self):
        for args in ((1,1,3,'uyvy',b'abc'),(0,1,3,'rgb8',b'abc'),(1,2,3,'rgb8',b'abc')):
            with self.subTest(args=args),self.assertRaises(ValueError):remote.png_bytes(*args)


class CaptureQuality(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.directory=Path(self.temp.name);(self.directory/'rgb').mkdir()
        self.manifest=dict(joint_names=NAMES,task='test',transport=dict(returncode=0),requested_seconds=.1,fps_limit=5)
        self.rows=[]
        for index in range(2):
            stamp=START+index*100_000_000
            png=remote.png_bytes(1,1,3,'rgb8',bytes([index,20,30]))
            path=f'rgb/{index:06d}.png';(self.directory/path).write_bytes(png)
            for kind in quality.REQUIRED:
                row=dict(kind=kind,source_ns=stamp,received_ns=stamp+10_000_000,
                         received_monotonic_ns=stamp-500_000_000_000)
                if kind=='rgb':row.update(png_file=path,png_sha256=hashlib.sha256(png).hexdigest(),pixels_sha256=str(index))
                elif kind=='joints':row['message']=dict(name=NAMES,position=[.01]*20)
                elif kind=='actuators':row['message']=dict(act_item=[dict(name=n[:-6]+'_motor',cmd_pos=.02) for n in NAMES])
                else:row['message']=dict(wrench={f:dict(x=0.,y=0.,z=0.) for f in ('force','torque')})
                self.rows.append(row)
        self.rows.append(dict(kind='end',errors=[],stopped=False,counts={k:2 for k in quality.REQUIRED}))

    def run_report(self):
        (self.directory/'manifest.json').write_text(json.dumps(self.manifest))
        (self.directory/'samples.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in self.rows))
        return quality.analyze(self.directory)

    def test_actual_vectors_are_separate_and_training_not_claimed(self):
        report=self.run_report();self.assertTrue(report['capture_checks_passed']);self.assertFalse(report['training_ready'])
        pair=json.loads((self.directory/'aligned.jsonl').read_text().splitlines()[0])
        self.assertEqual(pair['state20'],[.01]*20);self.assertEqual(pair['actuator_cmd_pos20'],[.02]*20)

    def test_missing_force_cannot_pass(self):
        self.rows=[r for r in self.rows if r.get('kind')!='force_left']
        self.assertFalse(self.run_report()['capture_checks_passed'])

    def test_source_clock_skew_is_not_repaired(self):
        for row in self.rows:
            if row.get('kind')=='joints':row['source_ns']+=10**9
        report=self.run_report();self.assertFalse(report['capture_checks_passed']);self.assertTrue(report['clock_warnings'])

    def test_reception_skew_rejects_even_matching_source_stamps(self):
        for row in self.rows:
            if row.get('kind')=='joints':row['received_monotonic_ns']+=600_000_000
        report=self.run_report();self.assertFalse(report['capture_checks_passed']);self.assertEqual(report['matched_frames'],0)

    def test_duplicates_fail_without_renewing_measurement(self):
        self.rows.insert(5,copy.deepcopy(self.rows[1]))
        report=self.run_report();self.assertFalse(report['capture_checks_passed']);self.assertTrue(report['invalid'])

    def test_truncated_transport_and_interruption_cannot_pass(self):
        for state in ('missing_end','transport_error','stopped'):
            with self.subTest(state=state):
                old=copy.deepcopy(self.rows);manifest=copy.deepcopy(self.manifest)
                if state=='missing_end':self.rows.pop()
                elif state=='transport_error':self.manifest['transport']['error']='timeout'
                else:self.rows[-1]['stopped']=True
                self.assertFalse(self.run_report()['capture_checks_passed'])
                self.rows=old;self.manifest=manifest

    def test_corrupt_png_fails(self):
        (self.directory/'rgb/000000.png').write_bytes(b'broken')
        self.assertFalse(self.run_report()['capture_checks_passed'])

    def test_short_source_span_cannot_pass_a_long_requested_capture(self):
        self.manifest['requested_seconds']=300
        report=self.run_report();self.assertFalse(report['capture_checks_passed'])
        self.assertFalse(report['source_span_checks_passed'])

    def test_dropped_stream_records_cannot_pass_declared_end_counts(self):
        self.rows[-1]['counts']['joints']=3
        report=self.run_report();self.assertFalse(report['capture_checks_passed'])
        self.assertFalse(report['sample_counts_match'])

    def test_no_reordering_or_missing_joint_substitution(self):
        message=dict(name=list(reversed(NAMES)),position=list(range(20)))
        self.assertEqual(quality.vector(message,NAMES),list(reversed(range(20))))
        message['name'][0]=message['name'][1]
        with self.assertRaises(ValueError):quality.vector(message,NAMES)


class ReadOnlyContract(unittest.TestCase):
    def test_existing_episode_cannot_be_overwritten(self):
        import importlib.util
        from types import SimpleNamespace
        p=Path(remote.__file__).with_name('capture_passive_episode.py')
        spec=importlib.util.spec_from_file_location('capture_passive_under_test',p)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp);sentinel=target/'sentinel';sentinel.write_text('keep')
            with self.assertRaises(FileExistsError):module.capture(SimpleNamespace(output_dir=target))
            self.assertEqual(sentinel.read_text(),'keep')

    def test_remote_contains_no_control_or_file_writing_api(self):
        tree=ast.parse(Path(remote.__file__).read_text())
        names={n.attr for n in ast.walk(tree) if isinstance(n,ast.Attribute)}
        self.assertFalse(names & {'create_publisher','create_client','send_goal','publish','call_async','write_text','write_bytes'})


class OptionalHands(unittest.TestCase):
    setUp = CaptureQuality.setUp
    run_report = CaptureQuality.run_report

    def discovery(self, left=False, right=False):
        topics = {}
        for side, subscribed in (('left', left), ('right', right)):
            for prefix, suffix in (('hand_', 'joint_states'), ('hand_command_', 'command')):
                kind = prefix + side
                topics[kind] = dict(topic=f'/mc/{side}_hand/{suffix}',
                    expected_type='sensor_msgs/msg/JointState' if prefix == 'hand_' else 'mc_task_msgs/msg/JointCommand',
                    observed_types=(['sensor_msgs/msg/JointState'] if prefix == 'hand_' else ['mc_task_msgs/msg/JointCommand']) if subscribed else [],
                    subscribed=subscribed)
        self.rows.insert(0, dict(kind='hand_discovery', topics=topics))

    def add_hand(self, side, *, offset_ns=0, only_one=False):
        kind = 'hand_'+side
        for index in range(1 if only_one else 2):
            stamp = START+index*100_000_000+offset_ns
            self.rows.insert(-1, dict(kind=kind, source_ns=stamp,
                received_ns=stamp+10_000_000,
                received_monotonic_ns=stamp-500_000_000_000,
                message=dict(name=[side+'_'+suffix for suffix in quality.HAND_SUFFIXES],
                             position=[.1, .2, .3, .4, .5, .6, .7])))
        self.rows[-1]['counts'][kind] = 1 if only_one else 2

    def test_no_hand_streams_preserve_base_success(self):
        self.discovery()
        report = self.run_report()
        self.assertTrue(report['capture_checks_passed'])
        for side in ('left', 'right'):
            hand = report['hands']['hand_'+side]
            self.assertEqual(hand['status'], 'not_detected_at_discovery')
            self.assertIsNone(hand['capture_checks_passed'])
        pair = json.loads((self.directory/'aligned.jsonl').read_text().splitlines()[0])
        self.assertNotIn('hand_left', pair)
        self.assertNotIn('hand_right', pair)

    def test_old_episode_has_no_discovery(self):
        report = self.run_report()
        self.assertTrue(report['capture_checks_passed'])
        self.assertEqual(report['hands']['hand_left']['status'], 'not_recorded_by_version')

    def test_one_hand_is_optional_and_reports_other_absent(self):
        self.discovery(left=True)
        self.add_hand('left')
        report = self.run_report()
        self.assertTrue(report['capture_checks_passed'])
        self.assertTrue(report['hands']['hand_left']['capture_checks_passed'])
        self.assertEqual(report['hands']['hand_right']['status'], 'not_detected_at_discovery')
        pair = json.loads((self.directory/'aligned.jsonl').read_text().splitlines()[0])
        self.assertEqual(pair['hand_left'], dict(name=['left_'+suffix for suffix in quality.HAND_SUFFIXES],
                                                position=[.1, .2, .3, .4, .5, .6, .7]))
        self.assertNotIn('hand_right', pair)
        self.assertIn('hand_left', pair['source_lines'])
        self.assertEqual(pair['source_delta_ms']['hand_left'], 0)

    def test_two_hand_streams_are_reported_and_aligned(self):
        self.discovery(left=True, right=True)
        self.add_hand('left'); self.add_hand('right')
        report = self.run_report()
        self.assertTrue(report['capture_checks_passed'])
        self.assertTrue(report['hands']['hand_left']['capture_checks_passed'])
        self.assertTrue(report['hands']['hand_right']['capture_checks_passed'])
        self.assertEqual(report['hands']['hand_right']['matched_frames'], 2)
        pair = json.loads((self.directory/'aligned.jsonl').read_text().splitlines()[0])
        self.assertEqual(pair['hand_right']['name'], ['right_'+suffix for suffix in quality.HAND_SUFFIXES])

    def test_missing_malformed_or_short_hand_never_masquerades_as_complete(self):
        for scenario in ('no_samples', 'bad_names', 'nonfinite', 'short', 'remote_error'):
            with self.subTest(scenario=scenario):
                old = copy.deepcopy(self.rows)
                self.discovery(left=True)
                if scenario not in ('no_samples', 'remote_error'):
                    self.add_hand('left', only_one=scenario == 'short')
                    if scenario == 'bad_names':
                        next(row for row in self.rows if row.get('kind') == 'hand_left')['message']['name'] = ['dup', 'dup']
                    elif scenario == 'nonfinite':
                        next(row for row in self.rows if row.get('kind') == 'hand_left')['message']['position'][0] = float('nan')
                elif scenario == 'remote_error':
                    self.rows.insert(-1, dict(kind='hand_error', stream='hand_left', error='serialization failed'))
                report = self.run_report()
                self.assertTrue(report['capture_checks_passed'])
                self.assertFalse(report['hands']['hand_left']['capture_checks_passed'])
                self.rows = old

    def test_hand_misalignment_does_not_invalidate_base_or_forge_pair(self):
        self.discovery(left=True)
        self.add_hand('left')
        for row in self.rows:
            if row.get('kind') == 'hand_left':
                row['received_monotonic_ns'] += 600_000_000
        report = self.run_report()
        self.assertTrue(report['capture_checks_passed'])
        self.assertFalse(report['hands']['hand_left']['capture_checks_passed'])
        self.assertEqual(report['hands']['hand_left']['unmatched_frames'], 2)
        pair = json.loads((self.directory/'aligned.jsonl').read_text().splitlines()[0])
        self.assertNotIn('hand_left', pair)

    def test_hand_coverage_or_counts_failure_is_separate_from_base(self):
        self.discovery(left=True)
        self.add_hand('left')
        self.rows[-1]['counts']['hand_left'] = 3
        report = self.run_report()
        self.assertTrue(report['capture_checks_passed'])
        self.assertFalse(report['hands']['hand_left']['capture_checks_passed'])
        self.assertFalse(report['hands']['hand_left']['sample_counts_match'])

    def test_hand_regressing_timestamp_cannot_pass(self):
        self.discovery(left=True)
        self.add_hand('left')
        rows = [row for row in self.rows if row.get('kind') == 'hand_left']
        rows[1]['source_ns'] = rows[0]['source_ns']
        report = self.run_report()
        self.assertTrue(report['capture_checks_passed'])
        self.assertEqual(report['hands']['hand_left']['status'], 'invalid')
        self.assertTrue(report['hands']['hand_left']['invalid'])

    def test_hand_insufficient_coverage_cannot_pass(self):
        self.discovery(left=True)
        self.add_hand('left')
        # Base duration remains valid; hand only covers the first 40 ms.
        hand = [row for row in self.rows if row.get('kind') == 'hand_left'][1]
        hand['source_ns'] -= 60_000_000
        hand['received_ns'] -= 60_000_000
        hand['received_monotonic_ns'] -= 60_000_000
        report = self.run_report()
        self.assertTrue(report['capture_checks_passed'])
        self.assertFalse(report['hands']['hand_left']['capture_checks_passed'])
        self.assertEqual(report['hands']['hand_left']['status'], 'partial')

    def test_hand_type_mismatch_is_not_described_as_absent_hardware(self):
        self.discovery()
        discovery = next(row for row in self.rows if row.get('kind') == 'hand_discovery')
        discovery['topics']['hand_left']['observed_types'] = ['other/msg/Type']
        report = self.run_report()
        self.assertTrue(report['capture_checks_passed'])
        self.assertEqual(report['hands']['hand_left']['status'], 'type_mismatch_or_unsubscribed')
        self.assertIsNone(report['hands']['hand_left']['capture_checks_passed'])

    def test_missing_or_unexpected_v4_joint_preserves_raw_but_fails_hand_check(self):
        for scenario in ('missing', 'unexpected'):
            with self.subTest(scenario=scenario):
                old = copy.deepcopy(self.rows)
                self.discovery(left=True)
                self.add_hand('left')
                hand = next(row for row in self.rows if row.get('kind') == 'hand_left')
                if scenario == 'missing':
                    hand['message']['name'].pop()
                    hand['message']['position'].pop()
                else:
                    hand['message']['name'][-1] = 'left_unknown'
                report = self.run_report()
                self.assertTrue(report['capture_checks_passed'])
                self.assertFalse(report['hands']['hand_left']['capture_checks_passed'])
                self.assertEqual(report['hands']['hand_left']['status'], 'incomplete_or_unknown_joints')
                raw = [json.loads(line) for line in (self.directory/'samples.jsonl').read_text().splitlines()]
                self.assertIn(hand, raw)
                pair = json.loads((self.directory/'aligned.jsonl').read_text().splitlines()[0])
                self.assertNotIn('hand_left', pair)
                self.rows = old

    def test_hand_command_is_preserved_as_raw_event_without_training_claim(self):
        self.discovery(left=True)
        self.add_hand('left')
        self.rows.insert(-1, dict(kind='hand_command_left', message={'joint_cmd': [{'name': 'left_thumb', 'mode': 3}]}))
        self.rows[-1]['counts']['hand_command_left'] = 1
        report = self.run_report()
        self.assertEqual(report['hand_commands']['hand_command_left']['raw_samples'], 1)
        self.assertTrue(report['hand_commands']['hand_command_left']['sample_counts_match'])
        self.assertFalse(report['training_ready'])


if __name__=='__main__':unittest.main()
