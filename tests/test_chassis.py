#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nose.tools import eq_, ok_, raises
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

    eq_(status.power_on, True)
    eq_(status.overload, True)
    eq_(status.interlock, True)
    eq_(status.fault, True)
    eq_(status.control_fault, True)
    eq_(status.restore_policy, 3)

    ok_('ac_failed' in status.last_event)
    ok_('overload' in status.last_event)
    ok_('interlock' in status.last_event)
    ok_('fault' in status.last_event)
    ok_('power_on_via_ipmi' in status.last_event)

    ok_('intrusion', status.chassis_state)
    ok_('front_panel_lockout', status.chassis_state)
    ok_('drive_fault', status.chassis_state)
    ok_('cooling_fault', status.chassis_state)

def test_datatobootmode():
    eq_(data_to_boot_mode(array('B', [0, 0, 0, 0, 0])), "legacy")
    eq_(data_to_boot_mode(array('B', [0b10100000, 0, 0, 0, 0])), "efi")

def test_datatobootpersistency():
    ok_(data_to_boot_persistency(array('B', [0b11000000, 0, 0, 0, 0])))
    ok_(not data_to_boot_persistency(array('B', [0b10000000, 0, 0, 0, 0])))

def test_datatobootdevice():
    eq_(data_to_boot_device(array('B', [0b11000000, 0b00001000, 0, 0, 0])), BootDevice.DEFAULT_HDD)
    eq_(data_to_boot_device(array('B', [0b11000000, 0b00000100, 0, 0, 0])), BootDevice.PXE)

def test_bootoptionstodata():
    eq_(boot_options_to_data("bios setup", "efi", True).array, array('B', [0b11100000, 0b00011000, 0, 0, 0]))

@raises(TypeError)
def test_bootoptionstodata_raise_typeerror():
    boot_options_to_data("pxe", "efi", 1)

@raises(ValueError)
def test_bootoptionstodata_raise_valueerror_bootmode():
    boot_options_to_data("pxe", "wrong boot mode", True)

@raises(ValueError)
def test_bootoptionstodata_raise_valueerror_bootdevice():
    boot_options_to_data("wrong boot device", "efi", True)
