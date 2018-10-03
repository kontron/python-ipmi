#!/usr/bin/env python

from nose.tools import eq_

import pyipmi.msgs.event

from pyipmi.msgs import encode_message
from pyipmi.msgs import decode_message


def test_seteventreceiver_encode_lun0_req():
    m = pyipmi.msgs.event.SetEventReceiverReq()
    m.event_receiver.ipmb_i2c_slave_address = 0x10
    m.event_receiver.lun = 0
    data = encode_message(m)
    eq_(data, b'\x20\x00')


def test_seteventreceiver_encode_lun3_req():
    m = pyipmi.msgs.event.SetEventReceiverReq()
    m.event_receiver.ipmb_i2c_slave_address = 0x10
    m.event_receiver.lun = 3
    data = encode_message(m)
    eq_(data, b'\x20\x03')


def test_geteventreceiver_decode_lun0_rsp():
    m = pyipmi.msgs.event.GetEventReceiverRsp()
    decode_message(m, b'\x00\x20\x00')
    eq_(m.completion_code, 0x00)
    eq_(m.event_receiver.ipmb_i2c_slave_address, 0x10)
    eq_(m.event_receiver.lun, 0)


def test_geteventreceiver_decode_lun3_rsp():
    m = pyipmi.msgs.event.GetEventReceiverRsp()
    decode_message(m, b'\x00\x20\x03')
    eq_(m.completion_code, 0x00)
    eq_(m.event_receiver.ipmb_i2c_slave_address, 0x10)
    eq_(m.event_receiver.lun, 3)
