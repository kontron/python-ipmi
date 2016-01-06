#!/usr/bin/env python
#-*- coding: utf-8 -*-

from nose.tools import eq_, raises

from pyipmi.bmc import *
import pyipmi.msgs.bmc
from pyipmi.msgs import encode_message
from pyipmi.msgs import decode_message

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
