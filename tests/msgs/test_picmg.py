#!/usr/bin/env python

import pyipmi.msgs.bmc
import pyipmi.msgs.sel
import pyipmi.msgs.event
import pyipmi.msgs.hpm
import pyipmi.msgs.sensor

from pyipmi.msgs import constants, decode_message, encode_message
from pyipmi.msgs.picmg import PICMG_IDENTIFIER


def test_get_picmg_properties_req():
    msg = pyipmi.msgs.picmg.GetPicmgPropertiesReq()
    assert msg.cmdid == constants.CMDID_GET_PICMG_PROPERTIES
    assert msg.netfn == constants.NETFN_GROUP_EXTENSION
    assert msg.group_extension == PICMG_IDENTIFIER


def test_get_address_info_picmg_2_9_rsp():
    m = pyipmi.msgs.picmg.GetAddressInfoRsp()
    decode_message(m, b'\x00\x00\x01\x02\x03')
    assert m.completion_code == 0x00
    assert m.picmg_identifier == 0x00
    assert m.hardware_address == 0x01
    assert m.ipmb_0_address == 0x02
    assert m.ipmb_1_address == 0x03
    assert m.fru_id is None
    assert m.site_id is None
    assert m.site_type is None
    assert m.carrier_number is None


def test_get_address_info_picmg_3_0_rsp():
    m = pyipmi.msgs.picmg.GetAddressInfoRsp()
    decode_message(m, b'\x00\x00\x01\x02\xff\x04\x05\x06')
    assert m.completion_code == 0x00
    assert m.picmg_identifier == 0x00
    assert m.hardware_address == 0x01
    assert m.ipmb_0_address == 0x02
    assert m.ipmb_1_address == 0xff
    assert m.fru_id == 0x04
    assert m.site_id == 0x05
    assert m.site_type == 0x06
    assert m.carrier_number is None


def test_get_address_info_mtca_rsp():
    m = pyipmi.msgs.picmg.GetAddressInfoRsp()
    decode_message(m, b'\x00\x00\x01\x02\x03\x04\x05\x06\x07')
    assert m.completion_code == 0x00
    assert m.picmg_identifier == 0x00
    assert m.hardware_address == 0x01
    assert m.ipmb_0_address == 0x02
    assert m.ipmb_1_address == 0x03
    assert m.fru_id == 0x04
    assert m.site_id == 0x05
    assert m.site_type == 0x06
    assert m.carrier_number == 0x07


def test_get_shelf_address_info_rsp():
    m = pyipmi.msgs.picmg.GetShelfAddressInfoRsp()
    decode_message(m, b'\x00\x00\x01\x02')
    assert m.completion_code == 0x00
    assert m.picmg_identifier == 0x00
    assert m.shelf_address[0] == 0x01
    assert m.shelf_address[1] == 0x02


def test_encode_fru_control_req():
    m = pyipmi.msgs.picmg.FruControlReq()
    m.fru_id = 1
    m.option = 2
    data = encode_message(m)
    assert data == b'\x00\x01\x02'


def test_decode_fru_control_rsp():
    m = pyipmi.msgs.picmg.FruControlRsp()
    decode_message(m, b'\x00\x00\xaa')
    assert m.rsp_data[0] == 0xaa


def test_clear_activation_lock_req():
    m = pyipmi.msgs.picmg.SetFruActivationPolicyReq()
    m.fru_id = 1
    m.mask.activation_locked = 1
    m.set.activation_locked = 0
    data = encode_message(m)
    assert data == b'\x00\x01\x01\x00'


def test_set_activation_lock_req():
    m = pyipmi.msgs.picmg.SetFruActivationPolicyReq()
    m.fru_id = 1
    m.mask.activation_locked = 1
    m.set.activation_locked = 1
    data = encode_message(m)
    assert data == b'\x00\x01\x01\x01'


def test_clear_deactivation_lock_req():
    m = pyipmi.msgs.picmg.SetFruActivationPolicyReq()
    m.fru_id = 1
    m.mask.deactivation_locked = 1
    m.set.deactivation_locked = 0
    data = encode_message(m)
    assert data == b'\x00\x01\x02\x00'


def test_set_deactivation_lock_req():
    m = pyipmi.msgs.picmg.SetFruActivationPolicyReq()
    m.fru_id = 1
    m.mask.deactivation_locked = 1
    m.set.deactivation_locked = 1
    data = encode_message(m)
    assert data == b'\x00\x01\x02\x02'


def test_decode_rsp_local_control_state():
    m = pyipmi.msgs.picmg.GetFruLedStateRsp()
    decode_message(m, b'\x00\x00\x01\xff\x00\x02')
    assert m.completion_code == 0x00
    assert m.led_states.local_avail == 1
    assert m.local_function == 0xff
    assert m.local_on_duration == 0
    assert m.local_color == 2


def test_decode_rsp_override_mode():
    m = pyipmi.msgs.picmg.GetFruLedStateRsp()
    decode_message(m, b'\x00\x00\x03\xff\x00\x03\xff\x00\x03')
    assert m.completion_code == 0x00
    assert m.led_states.local_avail == 1
    assert m.local_function == 0xff
    assert m.local_on_duration == 0
    assert m.local_color == 3
    assert m.led_states.override_en == 1
    assert m.override_function == 0xff
    assert m.override_on_duration == 0
    assert m.override_color == 3
    assert m.led_states.lamp_test_en == 0


def test_decode_rsp_lamp_test_and_override_mode():
    m = pyipmi.msgs.picmg.GetFruLedStateRsp()
    decode_message(m, b'\x00\x00\x07\xff\x00\x02\xff\x00\x02\x7f')
    assert m.completion_code == 0x00
    assert m.led_states.local_avail == 1
    assert m.local_function == 0xff
    assert m.local_on_duration == 0
    assert m.local_color == 2
    assert m.led_states.override_en == 1
    assert m.override_function == 0xff
    assert m.override_on_duration == 0
    assert m.override_color == 2
    assert m.led_states.lamp_test_en == 1
    assert m.lamp_test_duration == 0x7f


def test_decode_rsp_only_lamp_test_mode():
    m = pyipmi.msgs.picmg.GetFruLedStateRsp()
    decode_message(m, b'\x00\x00\x04\xff\x00\x02\xff\x00\x02\x7f')
    assert m.completion_code == 0x00
    assert m.led_states.local_avail == 0
    assert m.local_function == 0xff
    assert m.local_on_duration == 0
    assert m.local_color == 2
    assert m.led_states.override_en == 0
    assert m.override_function == 0xff
    assert m.override_on_duration == 0
    assert m.override_color == 2
    assert m.led_states.lamp_test_en == 1
    assert m.lamp_test_duration == 0x7f


def test_encode_req_pm_heartbeat():
    m = pyipmi.msgs.picmg.SendPmHeartbeatReq()
    m.timeout = 10
    m.ps1.mch_1 = 1
    data = encode_message(m)
    assert data == b'\x00\n\x01'

    m = pyipmi.msgs.picmg.SendPmHeartbeatReq()
    m.timeout = 10
    m.ps1.mch_2 = 1
    data = encode_message(m)
    assert data == b'\x00\n\x02'


def test_decode_rsp_pm_heartbeat():
    m = pyipmi.msgs.picmg.SendPmHeartbeatRsp()
    decode_message(m, b'\x00\x00')
    assert m.completion_code == 0x00
    assert m.picmg_identifier == 0x00
