#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nose.tools import eq_

from pyipmi.bmc import DeviceId, Watchdog
import pyipmi.msgs.bmc
from pyipmi.msgs import decode_message


def test_watchdog_object():
    msg = pyipmi.msgs.bmc.GetWatchdogTimerRsp()
    decode_message(msg, b'\x00\x41\x42\x33\x44\x55\x66\x77\x88')

    wdt = Watchdog(msg)
    eq_(wdt.timer_use, 1)
    eq_(wdt.is_running, 1)
    eq_(wdt.dont_log, 0)
    eq_(wdt.timeout_action, 2)
    eq_(wdt.pre_timeout_interrupt, 4)
    eq_(wdt.pre_timeout_interval, 0x33)

    eq_(wdt.timer_use_expiration_flags, 0x44)
    eq_(wdt.initial_countdown, 0x6655)
    eq_(wdt.present_countdown, 0x8877)


def test_deviceid_object():
    rsp = pyipmi.msgs.bmc.GetDeviceIdRsp()
    decode_message(rsp, b'\x00\x12\x84\x05\x67\x51\x55\x12\x34\x56\x44\x55')

    dev = DeviceId(rsp)
    eq_(dev.device_id, 18)
    eq_(dev.revision, 4)
    eq_(dev.provides_sdrs, True)
    eq_(str(dev.fw_revision), '5.67')
    eq_(str(dev.ipmi_version), '1.5')
    eq_(dev.manufacturer_id, 5649426)
    eq_(dev.product_id, 21828)

    eq_(dev.aux, None)


def test_deviceid_object_with_aux():
    msg = pyipmi.msgs.bmc.GetDeviceIdRsp()
    decode_message(msg,
                   b'\x00\x00\x00\x00\x00\x00\x00\x00'
                   b'\x00\x00\x00\x00\x01\x02\x03\x04')

    device_id = DeviceId(msg)
    eq_(device_id.aux, [1, 2, 3, 4])
