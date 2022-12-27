#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest

from array import array

from pyipmi.chassis import (ChassisStatus, data_to_boot_device,
                            data_to_boot_mode, data_to_boot_persistency,
                            boot_options_to_data, BootDevice)
import pyipmi.msgs.chassis
from pyipmi.msgs import decode_message


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

    assert 'intrusion', status.chassis_state
    assert 'front_panel_lockout', status.chassis_state
    assert 'drive_fault', status.chassis_state
    assert 'cooling_fault', status.chassis_state


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
