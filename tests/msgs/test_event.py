#!/usr/bin/env python

import pyipmi.msgs.event

from pyipmi.msgs import encode_message
from pyipmi.msgs import decode_message


def test_seteventreceiver_encode_lun0_req():
    m = pyipmi.msgs.event.SetEventReceiverReq()
    m.event_receiver.ipmb_i2c_slave_address = 0x10
    m.event_receiver.lun = 0
    data = encode_message(m)
    assert data == b'\x20\x00'


def test_seteventreceiver_encode_lun3_req():
    m = pyipmi.msgs.event.SetEventReceiverReq()
    m.event_receiver.ipmb_i2c_slave_address = 0x10
    m.event_receiver.lun = 3
    data = encode_message(m)
    assert data, b'\x20\x03'


def test_geteventreceiver_decode_lun0_rsp():
    m = pyipmi.msgs.event.GetEventReceiverRsp()
    decode_message(m, b'\x00\x20\x00')
    assert m.completion_code == 0x00
    assert m.event_receiver.ipmb_i2c_slave_address == 0x10
    assert m.event_receiver.lun == 0


def test_geteventreceiver_decode_lun3_rsp():
    m = pyipmi.msgs.event.GetEventReceiverRsp()
    decode_message(m, b'\x00\x20\x03')
    assert m.completion_code == 0x00
    assert m.event_receiver.ipmb_i2c_slave_address == 0x10
    assert m.event_receiver.lun == 3
