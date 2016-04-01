#!/usr/bin/env python

from array import array

from nose.tools import eq_

import pyipmi.msgs.chassis

from pyipmi.errors import DecodingError, EncodingError
from pyipmi.msgs import encode_message, decode_message

def test_getchassisstatus_encode_valid_req():
    m = pyipmi.msgs.chassis.GetChassisStatusReq()
    data = encode_message(m)
    eq_(m.__netfn__, 0)
    eq_(m.__cmdid__, 1)
    eq_(data, '')

def test_getchassisstatus_decode_valid_rsp():
    m = pyipmi.msgs.chassis.GetChassisStatusRsp()
    decode_message(m, '\x00\xea\xaa\xaa')
    eq_(m.completion_code, 0x00)
    eq_(m.current_power_state.power_on, 0)
    eq_(m.current_power_state.power_overload, 1)
    eq_(m.current_power_state.interlock, 0)
    eq_(m.current_power_state.power_fault, 1)
    eq_(m.current_power_state.power_control_fault, 0)
    eq_(m.current_power_state.power_restore_policy, 3)

    eq_(m.last_power_event.ac_failed, 0)
    eq_(m.last_power_event.power_overload, 1)
    eq_(m.last_power_event.power_interlock, 0)
    eq_(m.last_power_event.power_fault, 1)
    eq_(m.last_power_event.power_is_on_via_ipmi_command, 0)

    eq_(m.misc_chassis_state.chassis_intrusion_active, 0)
    eq_(m.misc_chassis_state.front_panel_lockout_active, 1)
    eq_(m.misc_chassis_state.drive_fault, 0)
    eq_(m.misc_chassis_state.cooling_fault_detected, 1)

def test_getchassisstatus_decode_valid_optional_byte_rsp():
    m = pyipmi.msgs.chassis.GetChassisStatusRsp()
    decode_message(m, '\x00\x00\x00\00\xaa')
    eq_(m.completion_code, 0x00)
    eq_(m.front_panel_button_capabilities, 0xaa)

def test_chassiscontrol_encode_valid_req():
    m = pyipmi.msgs.chassis.ChassisControlReq()
    m.control.option = 1
    data = encode_message(m)
    eq_(m.__netfn__, 0)
    eq_(m.__cmdid__, 2)
    eq_(data, '\x01')
