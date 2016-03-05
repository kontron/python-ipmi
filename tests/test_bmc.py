#!/usr/bin/env python
#-*- coding: utf-8 -*-

from nose.tools import eq_, raises

from pyipmi.bmc import *
import pyipmi.msgs.bmc
from pyipmi.msgs import encode_message
from pyipmi.msgs import decode_message

def test_watchdog_object():
    m = pyipmi.msgs.bmc.GetWatchdogTimerRsp()
    decode_message(m, '\x00\x41\x42\x33\x44\x55\x66\x77\x88')

    w = Watchdog(m)
    eq_(w.timer_use, 1)
    eq_(w.is_running, 1)
    eq_(w.dont_log, 0)
    eq_(w.timeout_action, 2)
    eq_(w.pre_timeout_interrupt, 4)
    eq_(w.pre_timeout_interval, 0x33)

    eq_(w.timer_use_expiration_flags, 0x44)
    eq_(w.initial_countdown, 0x6655)
    eq_(w.present_countdown, 0x8877)

def test_deviceid_object():
    m = pyipmi.msgs.bmc.GetDeviceIdRsp()
    decode_message(m, '\x00\x12\x84\x05\x67\x51\x55\x12\x34\x56\x44\x55')

    d = DeviceId(m)
    eq_(d.device_id, 18)
    eq_(d.revision, 4)
    eq_(d.provides_sdrs, True)
    eq_(str(d.fw_revision), '5.67')
    eq_(str(d.ipmi_version), '1.5')
    eq_(d.manufacturer_id, 5649426)
    eq_(d.product_id, 21828)

    eq_(d.aux, None)

def test_deviceid_object_with_aux():
    m = pyipmi.msgs.bmc.GetDeviceIdRsp()
    decode_message(m,
    '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04')

    d = DeviceId(m)
    eq_(d.aux, [1,2,3,4])
