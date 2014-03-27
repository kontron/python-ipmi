#!/usr/bin/env python

import unittest
from array import array

import pyipmi.msgs.bmc
import pyipmi.msgs.sel
import pyipmi.msgs.event
import pyipmi.msgs.hpm
import pyipmi.msgs.sensor

from pyipmi.errors import DecodingError, EncodingError
from pyipmi.msgs import encode_message
from pyipmi.msgs import decode_message


class TestFruActivationPolicy(unittest.TestCase):
    def test_clear_activation_lock_req(self):
        m = pyipmi.msgs.picmg.SetFruActivationPolicyReq()
        m.fru_id = 1
        m.mask.activation_locked = 1
        m.set.activation_locked = 0
        data = encode_message(m)
        self.assertEqual(data, '\x00\x01\x01\x00')

    def test_set_activation_lock_req(self):
        m = pyipmi.msgs.picmg.SetFruActivationPolicyReq()
        m.fru_id = 1
        m.mask.activation_locked = 1
        m.set.activation_locked = 1
        data = encode_message(m)
        self.assertEqual(data, '\x00\x01\x01\x01')

    def test_clear_deactivation_lock_req(self):
        m = pyipmi.msgs.picmg.SetFruActivationPolicyReq()
        m.fru_id = 1
        m.mask.deactivation_locked = 1
        m.set.deactivation_locked = 0
        data = encode_message(m)
        self.assertEqual(data, '\x00\x01\x02\x00')

    def test_set_deactivation_lock_req(self):
        m = pyipmi.msgs.picmg.SetFruActivationPolicyReq()
        m.fru_id = 1
        m.mask.deactivation_locked = 1
        m.set.deactivation_locked = 1
        data = encode_message(m)
        self.assertEqual(data, '\x00\x01\x02\x02')


class TestGetFruLedState(unittest.TestCase):
    def test_decode_rsp_local_control_state(self):
        m = pyipmi.msgs.picmg.GetFruLedStateRsp()
        decode_message(m, '\x00\x00\x01\xff\x00\x02')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.led_states.local_avail, 1)
        self.assertEqual(m.local_function, 0xff)
        self.assertEqual(m.local_on_duration, 0)
        self.assertEqual(m.local_color, 2)

    def test_decode_rsp_override_mode(self):
        m = pyipmi.msgs.picmg.GetFruLedStateRsp()
        decode_message(m, '\x00\x00\x03\xff\x00\x03\xff\x00\x03')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.led_states.local_avail, 1)
        self.assertEqual(m.local_function, 0xff)
        self.assertEqual(m.local_on_duration, 0)
        self.assertEqual(m.local_color, 3)
        self.assertEqual(m.led_states.override_en, 1)
        self.assertEqual(m.override_function, 0xff)
        self.assertEqual(m.override_on_duration, 0)
        self.assertEqual(m.override_color, 3)
        self.assertEqual(m.led_states.lamp_test_en, 0)

    def test_decode_rsp_lamp_test_and_override_mode(self):
        m = pyipmi.msgs.picmg.GetFruLedStateRsp()
        decode_message(m, '\x00\x00\x07\xff\x00\x02\xff\x00\x02\x7f')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.led_states.local_avail, 1)
        self.assertEqual(m.local_function, 0xff)
        self.assertEqual(m.local_on_duration, 0)
        self.assertEqual(m.local_color, 2)
        self.assertEqual(m.led_states.override_en, 1)
        self.assertEqual(m.override_function, 0xff)
        self.assertEqual(m.override_on_duration, 0)
        self.assertEqual(m.override_color, 2)
        self.assertEqual(m.led_states.lamp_test_en, 1)
        self.assertEqual(m.lamp_test_duration, 0x7f)

    def test_decode_rsp_only_lamp_test_mode(self):
        m = pyipmi.msgs.picmg.GetFruLedStateRsp()
        decode_message(m, '\x00\x00\x04\xff\x00\x02\xff\x00\x02\x7f')
        self.assertEqual(m.completion_code, 0x00)
        self.assertEqual(m.led_states.local_avail, 0)
        self.assertEqual(m.local_function, 0xff)
        self.assertEqual(m.local_on_duration, 0)
        self.assertEqual(m.local_color, 2)
        self.assertEqual(m.led_states.override_en, 0)
        self.assertEqual(m.override_function, 0xff)
        self.assertEqual(m.override_on_duration, 0)
        self.assertEqual(m.override_color, 2)
        self.assertEqual(m.led_states.lamp_test_en, 1)
        self.assertEqual(m.lamp_test_duration, 0x7f)


if __name__ == '__main__':
    unittest.main()
