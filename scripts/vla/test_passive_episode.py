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


if __name__=='__main__':unittest.main()
