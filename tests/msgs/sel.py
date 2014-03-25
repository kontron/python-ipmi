#!/usr/bin/env python

import unittest
from array import array

import pyipmi.msgs.sel

from pyipmi.errors import DecodingError, EncodingError
from pyipmi.msgs import encode_message
from pyipmi.msgs import decode_message


class TestGetSelEntry(unittest.TestCase):
    def test_decode_rsp_with_cc(self):
        m = pyipmi.msgs.sel.GetSelEntryRsp()
        decode_message(m, '\xc0')
        self.assertEqual(m.completion_code, 0xc0)

    def test_decode_invalid_rsp(self):
        m = pyipmi.msgs.sel.GetSelEntryRsp()
        self.assertRaises(DecodingError, decode_message, m, '\x00\x01')

    def test_encode_valid_rsp(self):
        m = pyipmi.msgs.sel.GetSelEntryRsp()
        decode_message(m, '\x00\x02\x01\x01\x02\x03\x04')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.next_record_id, 0x0102)
        self.assertEqual(m.record_data, '\x01\x02\x03\x04')

    def test_encode_valid_rsp(self):
        m = pyipmi.msgs.sel.GetSelEntryRsp()
        m.completion_code = 0
        m.next_record_id = 0x0102
        m.record_data = array('B', '\x01\x02\x03\x04')
        data = encode_message(m)
        self.assertEqual(data, '\x00\x02\x01\x01\x02\x03\x04')


if __name__ == '__main__':
    unittest.main()
