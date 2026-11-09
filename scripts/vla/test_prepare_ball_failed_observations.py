import hashlib
from pathlib import Path
import tempfile
import unittest

from prepare_ball_failed_observations import verify_alignment, verify_reception, verify_time


class TestProvenance(unittest.TestCase):
    def test_source_aligned_row_image_and_checksum_must_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'rgb').mkdir();path=root/'rgb/000001.png';path.write_bytes(b'png')
            sha=hashlib.sha256(b'png').hexdigest()
            source={'png_file':'rgb/000001.png','image_source_ns':123}
            row={'png_file':'rgb/000001.png','png_sha256':sha,'observations':source.copy()}
            verify_alignment(row,source,root,{'rgb/000001.png':sha})
            row['observations']['image_source_ns']=124
            with self.assertRaises(ValueError): verify_alignment(row,source,root,{'rgb/000001.png':sha})
            row['observations']=source.copy();path.write_bytes(b'tamper')
            with self.assertRaises(ValueError): verify_alignment(row,source,root,{'rgb/000001.png':sha})

    def test_future_stale_and_false_delta_rejected(self):
        obs={'image_source_ns':100_000_000,'source_delta_ms':{'joints':-1.0,'hand_right':-2.0}}
        joint={'source_ns':99_000_000};hand={'source_ns':98_000_000}
        verify_time(obs,joint,hand)
        for invalid in (100_000_001,19_999_999,97_000_000):
            with self.assertRaises(ValueError): verify_time(obs,{'source_ns':invalid},hand)

    def test_reception_future_and_stale_rejected(self):
        image={'received_monotonic_ns':1_000_000_000}
        good={'received_monotonic_ns':900_000_000}
        verify_reception(image,good,good)
        for stamp in (1_000_000_001,499_999_999):
            with self.assertRaises(ValueError):
                verify_reception(image,{'received_monotonic_ns':stamp},good)


if __name__=='__main__': unittest.main()
