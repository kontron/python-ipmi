#!/usr/bin/env python

import unittest
from array import array

import pyipmi.msgs.fru

from pyipmi.errors import DecodingError, EncodingError
from pyipmi.msgs import encode_message
from pyipmi.msgs import decode_message


class TestWriteFruData(unittest.TestCase):
    def test_decode_valid_req(self):
        m = pyipmi.msgs.fru.WriteFruDataReq()
        decode_message(m, '\x01\x02\x03\x04\x05')
        self.assertEqual(m.fru_id, 1)
        self.assertEqual(m.offset, 0x302)
        self.assertEqual(m.data, array('B', '\x04\x05'))

    def test_encode_valid_req(self):
        m = pyipmi.msgs.fru.WriteFruDataReq()
        m.fru_id = 1
        m.offset = 0x302
        m.data = array('B', '\x04\x05')
        data = encode_message(m)
        self.assertEqual(data, '\x01\x02\x03\x04\x05')

    def test_decode_valid_req_wo_data(self):
        m = pyipmi.msgs.fru.WriteFruDataReq()
        decode_message(m, '\x01\x02\x03')
        self.assertEqual(m.fru_id, 1)
        self.assertEqual(m.offset, 0x302)
        self.assertEqual(m.data, array('B'))

    def test_encode_valid_req_wo_data(self):
        m = pyipmi.msgs.fru.WriteFruDataReq()
        m.fru_id = 1
        m.offset = 0x302
        m.data = array('B')
        data = encode_message(m)
        self.assertEqual(data, '\x01\x02\x03')

    def test_decode_invalid_req(self):
        m = pyipmi.msgs.fru.WriteFruDataReq()
        self.assertRaises(DecodingError, decode_message, m, '\x01\x02')


class TestReadFruData(unittest.TestCase):
    def test_decode_valid_req(self):
        m = pyipmi.msgs.fru.ReadFruDataReq()
        decode_message(m, '\x01\x02\x03\x04')
        self.assertEqual(m.fru_id, 1)
        self.assertEqual(m.offset, 0x302)
        self.assertEqual(m.count, 4)

    def test_decode_short_req(self):
        m = pyipmi.msgs.fru.ReadFruDataReq()
        self.assertRaises(DecodingError, decode_message, m, '\x01\x02\x03')

    def test_decode_long_req(self):
        m = pyipmi.msgs.fru.ReadFruDataReq()
        self.assertRaises(DecodingError, decode_message, m,
                '\x01\x02\x03\04\x05')

    def test_encode_valid_req(self):
        m = pyipmi.msgs.fru.ReadFruDataReq()
        m.fru_id = 1
        m.offset = 0x302
        m.count = 4
        data = encode_message(m)
        self.assertEqual(data, '\x01\x02\x03\x04')

    def test_decode_valid_rsp(self):
        m = pyipmi.msgs.fru.ReadFruDataRsp()
        decode_message(m, '\x00\x05\x01\x02\x03\x04\x05')
        self.assertEqual(m.completion_code, 0)
        self.assertEqual(m.count, 5)
        self.assertEqual(m.data, array('B', '\x01\x02\x03\x04\x05'))

    def test_decode_rsp_with_cc(self):
        m = pyipmi.msgs.fru.ReadFruDataRsp()
        decode_message(m, '\xc0')
        self.assertEqual(m.completion_code, 0xc0)

    def test_decode_invalid_rsp(self):
        m = pyipmi.msgs.fru.ReadFruDataRsp()
        self.assertRaises(DecodingError, decode_message, m, '\x00\x01\x01\x02')

    def test_encode_valid_rsp(self):
        m = pyipmi.msgs.fru.ReadFruDataRsp()
        m.completion_code = 0
        m.count = 5
        m.data = array('B', '\x01\x02\x03\x04\x05')
        data = encode_message(m)
        self.assertEqual(data, '\x00\x05\x01\x02\x03\x04\x05')

#    def test_encode_rsp_with_cc(self):
#        m = pyipmi.msgs.fru.ReadFruDataRsp()
#        m.completion_code = 0xc0
#        data = encode_message(m)
#        self.assertEqual(data, '\xc0')

    def test_encode_invalid_rsp(self):
        m = pyipmi.msgs.fru.ReadFruDataRsp()
        m.completion_code = 0
        m.count = 1
        m.data = array('B', '\x01\x02')
        self.assertRaises(EncodingError, encode_message, m)


if __name__ == '__main__':
    unittest.main()
