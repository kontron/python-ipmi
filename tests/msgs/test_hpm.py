#!/usr/bin/env python

import unittest
from array import array

import pyipmi.msgs.hpm

from pyipmi.errors import DecodingError, EncodingError
from pyipmi.msgs import encode_message
from pyipmi.msgs import decode_message


class TestActivateFirmware(unittest.TestCase):
    def test_decode_valid_req(self):
        m = pyipmi.msgs.hpm.ActivateFirmwareReq()
        decode_message(m, '\x00\x01')
        self.assertEqual(m.picmg_identifier, 0)
        self.assertEqual(m.rollback_override_policy, 1)

    def test_encode_valid_req(self):
        m = pyipmi.msgs.hpm.ActivateFirmwareReq()
        m.picmg_identifier = 0
        m.rollback_override_policy = 0x1
        data = encode_message(m)
        self.assertEqual(data, '\x00\x01')

    def test_decode_valid_req_wo_optional(self):
        m = pyipmi.msgs.hpm.ActivateFirmwareReq()
        decode_message(m, '\x00')
        self.assertEqual(m.picmg_identifier, 0)
        self.assertEqual(m.rollback_override_policy, None)

    def test_encode_valid_req_wo_optional(self):
        m = pyipmi.msgs.hpm.ActivateFirmwareReq()
        m.picmg_identifier = 0
        m.rollback_override_policy = None
        data = encode_message(m)
        self.assertEqual(data, '\x00')


if __name__ == '__main__':
    unittest.main()
