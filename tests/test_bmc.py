#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pyipmi.bmc import DeviceId, Watchdog
import pyipmi.msgs.bmc
from pyipmi.msgs import decode_message


def test_watchdog_object():
    msg = pyipmi.msgs.bmc.GetWatchdogTimerRsp()
    decode_message(msg, b'\x00\x41\x42\x33\x44\x55\x66\x77\x88')

    wdt = Watchdog(msg)
    assert wdt.timer_use == 1
    assert wdt.is_running == 1
    assert wdt.dont_log == 0
    assert wdt.timeout_action == 2
    assert wdt.pre_timeout_interrupt == 4
    assert wdt.pre_timeout_interval == 0x33

    assert wdt.timer_use_expiration_flags == 0x44
    assert wdt.initial_countdown == 0x6655
    assert wdt.present_countdown == 0x8877


def test_deviceid_object():
    rsp = pyipmi.msgs.bmc.GetDeviceIdRsp()
    decode_message(rsp, b'\x00\x12\x84\x05\x67\x51\x55\x12\x34\x56\x44\x55')

    dev = DeviceId(rsp)
    assert dev.device_id == 18
    assert dev.revision == 4
    assert dev.provides_sdrs
    assert str(dev.fw_revision) == '5.67'
    assert str(dev.ipmi_version) == '1.5'
    assert dev.manufacturer_id == 5649426
    assert dev.product_id == 21828

    assert dev.aux is None


def test_deviceid_object_with_aux():
    msg = pyipmi.msgs.bmc.GetDeviceIdRsp()
    decode_message(msg,
                   b'\x00\x00\x00\x00\x00\x00\x00\x00'
                   b'\x00\x00\x00\x00\x01\x02\x03\x04')

    device_id = DeviceId(msg)
    assert device_id.aux == [1, 2, 3, 4]
