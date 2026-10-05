#!/usr/bin/env python

import pytest

from array import array

from pyipmi.chassis import (ChassisStatus, data_to_boot_device,
                            data_to_boot_mode, data_to_boot_persistency,
                            boot_options_to_data, BootDevice)
import pyipmi.msgs.chassis
from pyipmi.msgs import decode_message

from .ipmi_helper import create_ipmi


def test_chassisstatus_object():
    msg = pyipmi.msgs.chassis.GetChassisStatusRsp()
    decode_message(msg, b'\x00\xff\xff\xff')

    status = ChassisStatus(msg)

    assert status.power_on
    assert status.overload
    assert status.interlock
    assert status.fault
    assert status.control_fault
    assert status.restore_policy == 3

    assert 'ac_failed' in status.last_event
    assert 'overload' in status.last_event
    assert 'interlock' in status.last_event
    assert 'fault' in status.last_event
    assert 'power_on_via_ipmi' in status.last_event

    assert 'intrusion' in status.chassis_state
    assert 'front_panel_lockout' in status.chassis_state
    assert 'drive_fault' in status.chassis_state
    assert 'cooling_fault' in status.chassis_state


def test_datatobootmode():
    assert data_to_boot_mode(array('B', [0, 0, 0, 0, 0])) == "legacy"
    assert data_to_boot_mode(array('B', [0b10100000, 0, 0, 0, 0])) == "efi"


def test_datatobootpersistency():
    assert data_to_boot_persistency(array('B', [0b11000000, 0, 0, 0, 0]))
    assert not data_to_boot_persistency(array('B', [0b10000000, 0, 0, 0, 0]))


def test_datatobootdevice():
    assert data_to_boot_device(array('B', [0b11000000, 0b00001000, 0, 0, 0])) == BootDevice.DEFAULT_HDD
    assert data_to_boot_device(array('B', [0b11000000, 0b00000100, 0, 0, 0])) == BootDevice.PXE


def test_bootoptionstodata():
    assert boot_options_to_data("bios setup", "efi", True).array == array('B', [0b11100000, 0b00011000, 0, 0, 0])


def test_bootoptionstodata_raise_typeerror():
    with pytest.raises(TypeError):
        boot_options_to_data("pxe", "efi", 1)


def test_bootoptionstodata_raise_valueerror_bootmode():
    with pytest.raises(ValueError):
        boot_options_to_data("pxe", "wrong boot mode", True)


def test_bootoptionstodata_raise_valueerror_bootdevice():
    with pytest.raises(ValueError):
        boot_options_to_data("wrong boot device", "efi", True)


def test_chassisstatus_objects_are_independent():
    msg = pyipmi.msgs.chassis.GetChassisStatusRsp()
    decode_message(msg, b'\x00\xff\xff\xff')
    ChassisStatus(msg)

    msg = pyipmi.msgs.chassis.GetChassisStatusRsp()
    decode_message(msg, b'\x00\x00\x00\x00')
    status = ChassisStatus(msg)
    assert status.last_event == []
    assert status.chassis_state == []


def test_get_chassis_status():
    ipmi = create_ipmi(b'\x00\x01\x00\x00\x0f')
    status = ipmi.get_chassis_status()
    assert ipmi.requests == [('GetChassisStatusReq', b'')]
    assert status.power_on
    assert not status.fault
    assert status.front_panel_button_capabilities == 0x0f


@pytest.mark.parametrize('method, option', [
    ('chassis_control_power_down', 0),
    ('chassis_control_power_up', 1),
    ('chassis_control_power_cycle', 2),
    ('chassis_control_hard_reset', 3),
    ('chassis_control_diagnostic_interrupt', 4),
    ('chassis_control_soft_shutdown', 5),
])
def test_chassis_control(method, option):
    ipmi = create_ipmi(b'\x00')
    getattr(ipmi, method)()
    assert ipmi.requests == [('ChassisControlReq', bytes([option]))]


# boot flags: valid, persistent, EFI; boot device: PXE
BOOT_OPTIONS_RSP = b'\x00\x01\x05\xe0\x04\x00\x00\x00'


def test_get_system_boot_options():
    ipmi = create_ipmi(BOOT_OPTIONS_RSP)
    data = ipmi.get_system_boot_options(5)
    assert ipmi.requests == [('GetSystemBootOptionsReq', b'\x05\x00\x00')]
    assert list(data) == [0xe0, 0x04, 0, 0, 0]


def test_get_boot_options():
    ipmi = create_ipmi(BOOT_OPTIONS_RSP)
    assert ipmi.get_boot_mode() == 'efi'
    assert ipmi.get_boot_persistency() is True
    assert ipmi.get_boot_device() == BootDevice.PXE


def test_set_boot_options():
    ipmi = create_ipmi(b'\x00')
    ipmi.set_boot_options(BootDevice.PXE, 'efi', True)
    assert ipmi.requests == [
        ('SetSystemBootOptionsReq', b'\x05\xe0\x04\x00\x00\x00')]
