import unittest
from array import array

import pyipmi.msgs.fru
from pyipmi.errors import DecodingError, EncodingError

class TestReadFruData(unittest.TestCase):
    def test_decode_valid_req(self):
        m = pyipmi.msgs.fru.ReadFruData()
        m.req.decode('\x01\x02\x03\x04')
        self.assertEqual(m.req.fru_id, 1)
        self.assertEqual(m.req.offset, 0x302)
        self.assertEqual(m.req.count, 4)

    def test_decode_short_req(self):
        m = pyipmi.msgs.fru.ReadFruData()
        self.assertRaises(DecodingError, m.req.decode, '\x01\x02\x03')

    def test_decode_long_req(self):
        m = pyipmi.msgs.fru.ReadFruData()
        self.assertRaises(DecodingError, m.req.decode, '\x01\x02\x03\04\x05')

    def test_encode_valid_req(self):
        m = pyipmi.msgs.fru.ReadFruData()
        m.req.fru_id = 1
        m.req.offset = 0x302
        m.req.count = 4
        data = m.req.encode()
        self.assertEqual(data, '\x01\x02\x03\x04')

    def test_decode_valid_rsp(self):
        m = pyipmi.msgs.fru.ReadFruData()
        m.rsp.decode('\x00\x05\x01\x02\x03\x04\x05')
        self.assertEqual(m.rsp.completion_code, 0)
        self.assertEqual(m.rsp.count, 5)
        self.assertEqual(m.rsp.data, array('c', '\x01\x02\x03\x04\x05'))

    def test_decode_rsp_with_cc(self):
        m = pyipmi.msgs.fru.ReadFruData()
        m.rsp.decode('\xc0')
        self.assertEqual(m.rsp.completion_code, 0xc0)

    def test_decode_invalid_rsp(self):
        m = pyipmi.msgs.fru.ReadFruData()
        self.assertRaises(DecodingError, m.rsp.decode, '\x00\x01\x01\x02')

    def test_encode_valid_rsp(self):
        m = pyipmi.msgs.fru.ReadFruData()
        m.rsp.completion_code = 0
        m.rsp.count = 5
        m.rsp.data = array('c', '\x01\x02\x03\x04\x05')
        data = m.rsp.encode()
        self.assertEqual(data, '\x00\x05\x01\x02\x03\x04\x05')

    def test_encode_rsp_with_cc(self):
        m = pyipmi.msgs.fru.ReadFruData()
        m.rsp.completion_code = 0xc0
        data = m.rsp.encode()
        self.assertEqual(data, '\xc0')

    def test_encode_invalid_rsp(self):
        m = pyipmi.msgs.fru.ReadFruData()
        m.rsp.completion_code = 0
        m.rsp.count = 1
        m.rsp.data = array('c', '\x01\x02')
        self.assertRaises(EncodingError, m.rsp.encode)

if __name__ == '__main__':
    unittest.main()
