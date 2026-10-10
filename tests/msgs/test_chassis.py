#!/usr/bin/env python

from array import array

import pytest

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


def test_chassisreset_encode_valid_req():
    m = pyipmi.msgs.chassis.ChassisResetReq()
    data = encode_message(m)
    assert m.__netfn__ == 0
    assert m.__cmdid__ == 3
    assert data == b''


def test_chassisreset_decode_valid_rsp():
    m = pyipmi.msgs.chassis.ChassisResetRsp()
    decode_message(m, b'\x00')
    assert m.completion_code == 0x00


def test_chassisidentify_encode_valid_req():
    m = pyipmi.msgs.chassis.ChassisIdentifyReq()
    assert m.__netfn__ == 0
    assert m.__cmdid__ == 4
    # both bytes are optional
    assert encode_message(m) == b''
    m.interval = 30
    assert encode_message(m) == b'\x1e'
    m.force_on = 1
    assert encode_message(m) == b'\x1e\x01'


@pytest.mark.parametrize('data, interval, force_on', [
    (b'', None, None),
    (b'\x1e', 30, None),
    (b'\x00\x01', 0, 1),
])
def test_chassisidentify_decode_valid_req(data, interval, force_on):
    m = pyipmi.msgs.chassis.ChassisIdentifyReq()
    decode_message(m, data)
    assert m.interval == interval
    assert m.force_on == force_on


def test_chassisidentify_decode_valid_rsp():
    m = pyipmi.msgs.chassis.ChassisIdentifyRsp()
    decode_message(m, b'\x00')
    assert m.completion_code == 0x00


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


def test_setchassiscapabilities_encode_valid_req():
    m = pyipmi.msgs.chassis.SetChassisCapabilitiesReq()
    m.capabilities_flags.intrusion_sensor = 1
    m.capabilities_flags.frontpanel_lockout = 1
    m.fru_info_device_address = 0x20
    m.sdr_device_address = 0x22
    m.sel_device_address = 0x24
    m.system_management_device_address = 0x26
    assert m.__netfn__ == 0
    assert m.__cmdid__ == 5
    assert encode_message(m) == b'\x03\x20\x22\x24\x26'
    m.bridge_device_address = 0x28
    assert encode_message(m) == b'\x03\x20\x22\x24\x26\x28'


def test_setpowerrestorepolicy_encode_valid_req():
    m = pyipmi.msgs.chassis.SetPowerRestorePolicyReq()
    m.power_restore_policy.policy = 2
    assert m.__netfn__ == 0
    assert m.__cmdid__ == 6
    assert encode_message(m) == b'\x02'


def test_setpowerrestorepolicy_decode_valid_rsp():
    m = pyipmi.msgs.chassis.SetPowerRestorePolicyRsp()
    decode_message(m, b'\x00\x05')
    assert m.completion_code == 0x00
    assert m.power_restore_policy_support.always_off == 1
    assert m.power_restore_policy_support.restore_previous == 0
    assert m.power_restore_policy_support.always_on == 1


def test_getsystemrestartcause_encode_valid_req():
    m = pyipmi.msgs.chassis.GetSystemRestartCauseReq()
    assert m.__netfn__ == 0
    assert m.__cmdid__ == 7
    assert encode_message(m) == b''


@pytest.mark.parametrize('data, cause, channel_number', [
    (b'\x00\x01\x01', 0x1, 1),
    (b'\x00\x0b\x00', 0xb, 0),
    # without the channel number
    (b'\x00\x04', 0x4, None),
])
def test_getsystemrestartcause_decode_valid_rsp(data, cause, channel_number):
    m = pyipmi.msgs.chassis.GetSystemRestartCauseRsp()
    decode_message(m, data)
    assert m.completion_code == 0x00
    assert m.restart_cause.cause == cause
    assert m.channel_number == channel_number


def test_setfrontpanelbuttonenables_encode_valid_req():
    m = pyipmi.msgs.chassis.SetFrontPanelButtonEnablesReq()
    m.disable.power_off_button = 1
    m.disable.reset_button = 0
    m.disable.diagnostic_interrupt_button = 1
    m.disable.standby_button = 0
    assert m.__netfn__ == 0
    assert m.__cmdid__ == 0x0a
    assert encode_message(m) == b'\x05'


def test_setpowercycleinterval_encode_valid_req():
    m = pyipmi.msgs.chassis.SetPowerCycleIntervalReq()
    m.interval = 10
    assert m.__netfn__ == 0
    assert m.__cmdid__ == 0x0b
    assert encode_message(m) == b'\x0a'
