#!/usr/bin/env python

from array import array

from nose.tools import eq_, raises

import pyipmi.msgs.bmc
import pyipmi.msgs.sel
import pyipmi.msgs.event
import pyipmi.msgs.hpm
import pyipmi.msgs.sensor

from pyipmi.errors import DecodingError, EncodingError
from pyipmi.msgs import encode_message
from pyipmi.msgs import decode_message


def test_get_address_info_picmg_2_9_rsp():
    m = pyipmi.msgs.picmg.GetAddressInfoRsp()
    decode_message(m, '\x00\x00\x01\x02\x03')
    eq_(m.completion_code, 0x00)
    eq_(m.picmg_identifier, 0x00)
    eq_(m.hardware_address, 0x01)
    eq_(m.ipmb_0_address, 0x02)
    eq_(m.ipmb_1_address, 0x03)
    eq_(m.fru_id, None)
    eq_(m.site_id, None)
    eq_(m.site_type, None)
    eq_(m.carrier_number, None)

def test_get_address_info_picmg_3_0_rsp():
    m = pyipmi.msgs.picmg.GetAddressInfoRsp()
    decode_message(m, '\x00\x00\x01\x02\xff\x04\x05\x06')
    eq_(m.completion_code, 0x00)
    eq_(m.picmg_identifier, 0x00)
    eq_(m.hardware_address, 0x01)
    eq_(m.ipmb_0_address, 0x02)
    eq_(m.ipmb_1_address, 0xff)
    eq_(m.fru_id, 0x04)
    eq_(m.site_id, 0x05)
    eq_(m.site_type, 0x06)
    eq_(m.carrier_number, None)

def test_get_address_info_mtca_rsp():
    m = pyipmi.msgs.picmg.GetAddressInfoRsp()
    decode_message(m, '\x00\x00\x01\x02\x03\x04\x05\x06\x07')
    eq_(m.completion_code, 0x00)
    eq_(m.picmg_identifier, 0x00)
    eq_(m.hardware_address, 0x01)
    eq_(m.ipmb_0_address, 0x02)
    eq_(m.ipmb_1_address, 0x03)
    eq_(m.fru_id, 0x04)
    eq_(m.site_id, 0x05)
    eq_(m.site_type, 0x06)
    eq_(m.carrier_number, 0x07)

def test_get_shelf_address_info_rsp():
    m = pyipmi.msgs.picmg.GetShelfAddressInfoRsp()
    decode_message(m, '\x00\x00\x01\x02')
    eq_(m.completion_code, 0x00)
    eq_(m.picmg_identifier, 0x00)
    eq_(m.shelf_address[0], 0x01)
    eq_(m.shelf_address[1], 0x02)

def test_clear_activation_lock_req():
    m = pyipmi.msgs.picmg.SetFruActivationPolicyReq()
    m.fru_id = 1
    m.mask.activation_locked = 1
    m.set.activation_locked = 0
    data = encode_message(m)
    eq_(data, '\x00\x01\x01\x00')

def test_set_activation_lock_req():
    m = pyipmi.msgs.picmg.SetFruActivationPolicyReq()
    m.fru_id = 1
    m.mask.activation_locked = 1
    m.set.activation_locked = 1
    data = encode_message(m)
    eq_(data, '\x00\x01\x01\x01')

def test_clear_deactivation_lock_req():
    m = pyipmi.msgs.picmg.SetFruActivationPolicyReq()
    m.fru_id = 1
    m.mask.deactivation_locked = 1
    m.set.deactivation_locked = 0
    data = encode_message(m)
    eq_(data, '\x00\x01\x02\x00')

def test_set_deactivation_lock_req():
    m = pyipmi.msgs.picmg.SetFruActivationPolicyReq()
    m.fru_id = 1
    m.mask.deactivation_locked = 1
    m.set.deactivation_locked = 1
    data = encode_message(m)
    eq_(data, '\x00\x01\x02\x02')

def test_decode_rsp_local_control_state():
    m = pyipmi.msgs.picmg.GetFruLedStateRsp()
    decode_message(m, '\x00\x00\x01\xff\x00\x02')
    eq_(m.completion_code, 0x00)
    eq_(m.led_states.local_avail, 1)
    eq_(m.local_function, 0xff)
    eq_(m.local_on_duration, 0)
    eq_(m.local_color, 2)

def test_decode_rsp_override_mode():
    m = pyipmi.msgs.picmg.GetFruLedStateRsp()
    decode_message(m, '\x00\x00\x03\xff\x00\x03\xff\x00\x03')
    eq_(m.completion_code, 0x00)
    eq_(m.led_states.local_avail, 1)
    eq_(m.local_function, 0xff)
    eq_(m.local_on_duration, 0)
    eq_(m.local_color, 3)
    eq_(m.led_states.override_en, 1)
    eq_(m.override_function, 0xff)
    eq_(m.override_on_duration, 0)
    eq_(m.override_color, 3)
    eq_(m.led_states.lamp_test_en, 0)

def test_decode_rsp_lamp_test_and_override_mode():
    m = pyipmi.msgs.picmg.GetFruLedStateRsp()
    decode_message(m, '\x00\x00\x07\xff\x00\x02\xff\x00\x02\x7f')
    eq_(m.completion_code, 0x00)
    eq_(m.led_states.local_avail, 1)
    eq_(m.local_function, 0xff)
    eq_(m.local_on_duration, 0)
    eq_(m.local_color, 2)
    eq_(m.led_states.override_en, 1)
    eq_(m.override_function, 0xff)
    eq_(m.override_on_duration, 0)
    eq_(m.override_color, 2)
    eq_(m.led_states.lamp_test_en, 1)
    eq_(m.lamp_test_duration, 0x7f)

def test_decode_rsp_only_lamp_test_mode():
    m = pyipmi.msgs.picmg.GetFruLedStateRsp()
    decode_message(m, '\x00\x00\x04\xff\x00\x02\xff\x00\x02\x7f')
    eq_(m.completion_code, 0x00)
    eq_(m.led_states.local_avail, 0)
    eq_(m.local_function, 0xff)
    eq_(m.local_on_duration, 0)
    eq_(m.local_color, 2)
    eq_(m.led_states.override_en, 0)
    eq_(m.override_function, 0xff)
    eq_(m.override_on_duration, 0)
    eq_(m.override_color, 2)
    eq_(m.led_states.lamp_test_en, 1)
    eq_(m.lamp_test_duration, 0x7f)
