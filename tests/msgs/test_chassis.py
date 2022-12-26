#!/usr/bin/env python

from array import array

import pyipmi.msgs.chassis

from pyipmi.msgs import encode_message, decode_message


def test_getchassisstatus_encode_valid_req():
    m = pyipmi.msgs.chassis.GetChassisStatusReq()
    data = encode_message(m)
    assert m.__netfn__ == 0
    assert m.__cmdid__ == 1
    assert data == b''


def test_getchassisstatus_decode_valid_rsp():
    m = pyipmi.msgs.chassis.GetChassisStatusRsp()
    decode_message(m, b'\x00\xea\xaa\xaa')
    assert m.completion_code == 0x00
    assert m.current_power_state.power_on == 0
    assert m.current_power_state.power_overload == 1
    assert m.current_power_state.interlock == 0
    assert m.current_power_state.power_fault == 1
    assert m.current_power_state.power_control_fault == 0
    assert m.current_power_state.power_restore_policy == 3

    assert m.last_power_event.ac_failed == 0
    assert m.last_power_event.power_overload == 1
    assert m.last_power_event.power_interlock == 0
    assert m.last_power_event.power_fault == 1
    assert m.last_power_event.power_is_on_via_ipmi_command == 0

    assert m.misc_chassis_state.chassis_intrusion_active == 0
    assert m.misc_chassis_state.front_panel_lockout_active == 1
    assert m.misc_chassis_state.drive_fault == 0
    assert m.misc_chassis_state.cooling_fault_detected == 1


def test_getchassisstatus_decode_valid_optional_byte_rsp():
    m = pyipmi.msgs.chassis.GetChassisStatusRsp()
    decode_message(m, b'\x00\x00\x00\00\xaa')
    assert m.completion_code == 0x00
    assert m.front_panel_button_capabilities == 0xaa


def test_chassiscontrol_encode_valid_req():
    m = pyipmi.msgs.chassis.ChassisControlReq()
    m.control.option = 1
    data = encode_message(m)
    assert m.__netfn__ == 0
    assert m.__cmdid__ == 2
    assert data == b'\x01'


def test_getsystembootoptions_encode_valid_req():
    m = pyipmi.msgs.chassis.GetSystemBootOptionsReq()
    m.parameter_selector.boot_option_parameter_selector = 5
    data = encode_message(m)
    assert m.__netfn__ == 0
    assert m.__cmdid__ == 9
    assert data == b'\x05\x00\x00'

def test_getsystembootoptions_decode_valid_rsp():
    m = pyipmi.msgs.chassis.GetSystemBootOptionsRsp()
    decode_message(m, b'\x00\x01\x85\x00\x08\x00\x00\x00')

    assert m.completion_code == 0x00
    assert m.parameter_version.parameter_version == 1
    assert m.parameter_valid.boot_option_parameter_selector == 5
    assert m.parameter_valid.parameter_validity == 1
    assert m.data == array('B', b'\x00\x08\x00\x00\x00')

def test_setsystembootoptions_encode_valid_req():
    m = pyipmi.msgs.chassis.SetSystemBootOptionsReq()
    m.parameter_selector.boot_option_parameter_selector = 5
    m.parameter_selector.parameter_validity = 1
    m.data = array('B', b'\x70\x08\x00\x00\x00')
    data = encode_message(m)

    assert m.__netfn__ == 0
    assert m.__cmdid__ == 8
    assert data == b'\x85\x70\x08\x00\x00\x00'

def test_setsystembootoptions_decode_valid_rsp():
    m = pyipmi.msgs.chassis.SetSystemBootOptionsRsp()
    decode_message(m, b'\x00')

    assert m.completion_code == 0x00
