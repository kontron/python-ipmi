#!/usr/bin/env python

import pytest

from array import array

import pyipmi.msgs.sel

from pyipmi.errors import DecodingError
from pyipmi.msgs import encode_message
from pyipmi.msgs import decode_message


def test_getselentry_decode_rsp_with_cc():
    m = pyipmi.msgs.sel.GetSelEntryRsp()
    decode_message(m, b'\xc0')
    assert m.completion_code == 0xc0


def test_getselentry_decode_invalid_rsp():
    m = pyipmi.msgs.sel.GetSelEntryRsp()
    with pytest.raises(DecodingError):
        decode_message(m, b'\x00\x01')


def test_getselentry_decode_valid_rsp():
    m = pyipmi.msgs.sel.GetSelEntryRsp()
    decode_message(m, b'\x00\x02\x01\x01\x02\x03\x04')
    assert m.completion_code == 0x00
    assert m.next_record_id == 0x0102
    assert m.record_data == array('B', [1, 2, 3, 4])


def test_getselentry_encode_valid_rsp():
    m = pyipmi.msgs.sel.GetSelEntryRsp()
    m.completion_code = 0
    m.next_record_id = 0x0102
    m.record_data = array('B', b'\x01\x02\x03\x04')
    data = encode_message(m)
    assert data == b'\x00\x02\x01\x01\x02\x03\x04'


def test_setseltime_encode_req():
    m = pyipmi.msgs.sel.SetSelTimeReq()
    m.timestamp = 0x01020304
    assert encode_message(m) == b'\x04\x03\x02\x01'


def test_setseltime_decode_rsp():
    m = pyipmi.msgs.sel.SetSelTimeRsp()
    decode_message(m, b'\x00')
    assert m.completion_code == 0x00


def test_addselentry_encode_req():
    m = pyipmi.msgs.sel.AddSelEntryReq()
    m.record_data = array('B', range(16))
    assert encode_message(m) == bytes(range(16))
