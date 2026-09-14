import hashlib
import struct
import unittest
from unittest.mock import patch

import extract_s2_compiled_limits as module


class ExtractionTests(unittest.TestCase):
    def test_overhang_is_not_nominal_violation(self):
        r=module.position_domains(-1.38,0,-2.62,.01,.017453292519943295)
        self.assertTrue(r['nominal_inside'])
        self.assertFalse(r['uncertainty_inside'])
        self.assertGreater(r['uncertainty_interval_rad'][1],.01)

    def test_nominal_violation_not_hidden(self):
        self.assertFalse(module.position_domains(-1.38,.02,-2.62,.01,.017)['nominal_inside'])

    def test_invalid_uncertainty_rejected(self):
        for error in (-.01,float('nan'),float('inf')):
            with self.assertRaises(ValueError):
                module.position_domains(0,0,-1,1,error)

    def fixture(self, flags=4):
        blob=bytearray(1024)
        blob[:6]=b'\x7fELF\x02\x01'
        struct.pack_into('<H',blob,18,62)
        struct.pack_into('<Q',blob,32,64)
        struct.pack_into('<HH',blob,54,56,1)
        struct.pack_into('<IIQQQQQQ',blob,64,1,flags,512,module.ADDRESS,0,336,336,4096)
        for i in range(7):
            struct.pack_into('<6d',blob,512+i*48,-i-1,i+1,3,4,5,6)
        return bytes(blob)

    def test_virtual_address_translation(self):
        blob=self.fixture()
        with patch.object(module,'SHA256',hashlib.sha256(blob).hexdigest()):
            rows=module.extract(blob)
        self.assertEqual(rows[6],[-7,7,3,4,5,6])

    def test_changed_binary_rejected(self):
        with self.assertRaises(ValueError):
            module.extract(self.fixture())

    def test_mutable_data_rejected(self):
        blob=self.fixture(flags=6)
        with patch.object(module,'SHA256',hashlib.sha256(blob).hexdigest()):
            with self.assertRaises(ValueError):
                module.extract(blob)


if __name__=='__main__':
    unittest.main()
