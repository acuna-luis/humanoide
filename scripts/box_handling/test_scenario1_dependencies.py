"""Offline batch dependency checks; local temporary fixtures only, no robot."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.box_handling.scenario1_dependencies import (
    HOME_META_PATH, HOME_PATH, VISION_PATH, collect_request, collector_source,
    plan_files, validate_reports,
)


VISION_XML = '<root><BehaviorTree ID="MainTree"><Sequence><Action ID="MetaLook" start_vision_mode="transport_vision" /></Sequence></BehaviorTree></root>\n'


def sha(value):
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def payload():
    return dict(bundle=dict(manifest=dict(id='0123456789abcdef',
                    sources={'front_sps_contract.py': sha('contract'), 'front_sps_native.py': sha('adapter')},
                    robot_files={'/opt/walker/task.xml': sha('task'), '/opt/walker/grasp.yaml': sha('yaml')},
                    native_binaries={'/opt/walker/libmeta_clamp.so': sha('binary')})),
                extra_hashes={'/opt/walker/deposit.yaml': sha('deposit')},
                home_pins=dict(accepted=[sha('direct'), sha('bodyfirst')],
                               direct=sha('direct'), meta=sha('meta_move')))


def reports(data=None, direct=False, vision=VISION_XML):
    data = payload() if data is None else data
    plan = plan_files(data)
    native = dict(plan['native'])
    native[HOME_PATH] = sha('direct' if direct else 'bodyfirst')
    native[VISION_PATH] = sha(vision)
    if not direct:
        native[HOME_META_PATH] = sha('meta_move')
    return dict(hashes=native, vision_xml=vision), dict(hashes=dict(plan['ros2']))


class DependencyContractTest(unittest.TestCase):
    def test_plan_preserves_all_original_files_in_both_containers(self):
        data = payload()
        plan = plan_files(data)
        package_root = '/opt/cruzr-front-box/0123456789abcdef/'
        self.assertEqual(plan['ros2'], {package_root+k: v for k, v in data['bundle']['manifest']['sources'].items()})
        expected = {**plan['ros2'], **data['bundle']['manifest']['robot_files'],
                    **data['bundle']['manifest']['native_binaries'], **data['extra_hashes']}
        self.assertEqual(plan['native'], expected)
        requests = [collect_request(data, native=True), collect_request(data, native=False)]
        self.assertEqual(len(requests), 2)
        self.assertEqual(set(requests[0]['paths']), set(expected) | {HOME_PATH, VISION_PATH})
        self.assertEqual(set(requests[1]['paths']), set(plan['ros2']))
        self.assertNotIn(HOME_META_PATH, requests[0]['paths'])
        self.assertEqual(requests[0]['home_meta_path'], HOME_META_PATH)

    def test_identity_matches_the_previous_runtime_shape(self):
        data = payload(); native, ros = reports(data)
        original = copy.deepcopy((data, native, ros))
        identity = validate_reports(data, native, ros)
        self.assertEqual(identity, dict(sps_package='0123456789abcdef', home_sha256=sha('bodyfirst'),
                                        vision_sha256=sha(VISION_XML), extra=data['extra_hashes']))
        identity['extra']['arbitrary'] = 'local change'
        self.assertEqual((data, native, ros), original)

    def test_every_binary_yaml_task_source_and_extra_change_is_rejected(self):
        data = payload(); base_native, base_ros = reports(data)
        for path in plan_files(data)['native']:
            native = copy.deepcopy(base_native); native['hashes'][path] = sha('changed')
            with self.subTest(container='native', path=path), self.assertRaises(ValueError):
                validate_reports(data, native, base_ros)
        for path in plan_files(data)['ros2']:
            ros = copy.deepcopy(base_ros); ros['hashes'][path] = sha('changed')
            with self.subTest(container='ros2', path=path), self.assertRaises(ValueError):
                validate_reports(data, base_native, ros)

    def test_missing_extra_or_duplicate_role_paths_do_not_pass(self):
        data = payload(); native, ros = reports(data)
        for container in ('native', 'ros2'):
            for mutation in ('missing', 'extra'):
                n, r = copy.deepcopy(native), copy.deepcopy(ros)
                hashes = n['hashes'] if container == 'native' else r['hashes']
                if mutation == 'missing': hashes.pop(next(iter(hashes)))
                else: hashes['/opt/unexpected'] = sha('unexpected')
                with self.subTest(container=container, mutation=mutation), self.assertRaises(ValueError):
                    validate_reports(data, n, r)

    def test_home_variants_and_conditional_library_are_enforced(self):
        data = payload()
        native, ros = reports(data, direct=True)
        self.assertEqual(validate_reports(data, native, ros)['home_sha256'], sha('direct'))
        native['hashes'][HOME_META_PATH] = sha('unexpected-meta')
        with self.assertRaises(ValueError):
            validate_reports(data, native, ros)
        for path, value in ((HOME_PATH, sha('unknown-home')), (HOME_META_PATH, sha('unknown-meta'))):
            native, ros = reports(data); native['hashes'][path] = value
            with self.subTest(path=path), self.assertRaises(ValueError):
                validate_reports(data, native, ros)
        native, ros = reports(data); del native['hashes'][HOME_META_PATH]
        with self.assertRaises(ValueError):
            validate_reports(data, native, ros)

    def test_direct_home_still_checks_meta_if_it_is_an_original_required_dependency(self):
        data = payload(); data['extra_hashes'][HOME_META_PATH] = sha('meta_move')
        native, ros = reports(data, direct=True)
        self.assertEqual(validate_reports(data, native, ros)['home_sha256'], sha('direct'))
        native['hashes'][HOME_META_PATH] = sha('changed')
        with self.assertRaises(ValueError):
            validate_reports(data, native, ros)

    def test_changed_xml_semantics_or_text_hash_mismatch_is_rejected(self):
        bad_xml = [VISION_XML.replace('transport_vision', 'sps_vision'),
                   VISION_XML.replace(' />', ' extra="true" />'),
                   '<root/>', VISION_XML.replace('</Sequence>', '<Action ID="MetaMove" /></Sequence>'),
                   '<root>']
        for xml in bad_xml:
            native, ros = reports(vision=xml)
            with self.subTest(xml=xml), self.assertRaises(ValueError):
                validate_reports(payload(), native, ros)
        native, ros = reports(); native['vision_xml'] += ' '
        with self.assertRaisesRegex(ValueError, 'full-read hash'):
            validate_reports(payload(), native, ros)

    def test_semantically_equal_changed_xml_changes_identity_for_runtime_pin(self):
        native, ros = reports()
        first = validate_reports(payload(), native, ros)
        native, ros = reports(vision=VISION_XML+'\n')
        second = validate_reports(payload(), native, ros)
        self.assertNotEqual(first, second)

    def test_malformed_manifest_hashes_paths_or_reports_reject(self):
        variants = []
        item = payload(); item['bundle']['manifest']['id'] = '../other'; variants.append(item)
        item = payload(); item['bundle']['manifest']['sources']['../outside.py'] = sha('x'); variants.append(item)
        item = payload(); item['extra_hashes']['/opt/test'] = 'bad'; variants.append(item)
        item = payload(); item['extra_hashes']['/opt/walker/grasp.yaml'] = sha('conflicting'); variants.append(item)
        for data in variants:
            with self.subTest(payload=data), self.assertRaises(ValueError):
                collect_request(data, True)
        native, ros = reports()
        for report in ({}, {'hashes': native['hashes']}, dict(native, cached=True)):
            with self.subTest(report=report), self.assertRaises(ValueError):
                validate_reports(payload(), report, ros)


class CollectorTest(unittest.TestCase):
    def collect(self, request):
        result = subprocess.run([sys.executable, '-B', '-c', collector_source(), json.dumps(request)],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_native_collector_hashes_whole_large_binary_and_preserves_exact_xml_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            binary = root/'large.bin'; contents = b'abcd' * 600_000; binary.write_bytes(contents)
            home = root/'home.xml'; home.write_text('bodyfirst')
            library = root/'libmeta_move.so'; library.write_bytes(b'meta_move')
            vision = root/'vision.xml'; xml = VISION_XML.replace('\n', '\r\n'); vision.write_bytes(xml.encode())
            request = dict(paths=list(map(str, [binary, home, vision])), text_paths=[str(vision)],
                           home_path=str(home), home_direct=sha('direct'), home_meta_path=str(library))
            result = self.collect(request)
            self.assertEqual(result['hashes'], {str(binary): sha(contents), str(home): sha('bodyfirst'),
                                               str(vision): sha(xml), str(library): sha('meta_move')})
            self.assertEqual(result['vision_xml'], xml)

    def test_direct_collector_does_not_require_absent_meta_library(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root/'home.xml'; home.write_text('direct')
            vision = root/'vision.xml'; vision.write_text(VISION_XML)
            request = dict(paths=[str(home), str(vision)], text_paths=[str(vision)],
                           home_path=str(home), home_direct=sha('direct'), home_meta_path=str(root/'missing.so'))
            result = self.collect(request)
            self.assertEqual(set(result['hashes']), {str(home), str(vision)})

    def test_repeated_collection_rereads_changed_same_size_files_without_cache(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'source.py'; path.write_text('first')
            request = dict(paths=[str(path)], text_paths=[])
            first = self.collect(request)
            path.write_text('other')
            second = self.collect(request)
            self.assertEqual(set(first), {'hashes'})
            self.assertEqual(first['hashes'][str(path)], sha('first'))
            self.assertEqual(second['hashes'][str(path)], sha('other'))
            self.assertNotEqual(first, second)

    def test_missing_file_or_non_direct_missing_library_fails_without_partial_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root/'home.xml'; home.write_text('bodyfirst')
            vision = root/'vision.xml'; vision.write_text(VISION_XML)
            requests = [dict(paths=[str(root/'missing')], text_paths=[]),
                        dict(paths=[str(home), str(vision)], text_paths=[str(vision)],
                             home_path=str(home), home_direct=sha('direct'), home_meta_path=str(root/'missing.so'))]
            for request in requests:
                result = subprocess.run([sys.executable, '-B', '-c', collector_source(), json.dumps(request)],
                                        capture_output=True, text=True, timeout=5)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
