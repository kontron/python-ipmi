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


def test_partialaddselentry_encode_req():
    m = pyipmi.msgs.sel.PartialAddSelEntryReq()
    m.reservation_id = 0x1234
    m.record_id = 0x0005
    m.offset = 8
    m.progress.in_progress = 1
    m.record_data = array('B', [1, 2, 3, 4])
    assert m.__netfn__ == 0x0a
    assert m.__cmdid__ == 0x45
    assert encode_message(m) == b'\x34\x12\x05\x00\x08\x01\x01\x02\x03\x04'


def test_partialaddselentry_decode_rsp():
    m = pyipmi.msgs.sel.PartialAddSelEntryRsp()
    decode_message(m, b'\x00\x05\x00')
    assert m.completion_code == 0x00
    assert m.record_id == 5


def test_getauxiliarylogstatus_encode_req():
    m = pyipmi.msgs.sel.GetAuxiliaryLogStatusReq()
    m.log.type = 1
    assert m.__netfn__ == 0x0a
    assert m.__cmdid__ == 0x5a
    assert encode_message(m) == b'\x01'


def test_getauxiliarylogstatus_decode_rsp():
    m = pyipmi.msgs.sel.GetAuxiliaryLogStatusRsp()
    decode_message(m, b'\x00\x11\x22\x33\x44\x02\x00\x00\x00')
    assert m.completion_code == 0x00
    assert bytes(m.log_data) == b'\x11\x22\x33\x44\x02\x00\x00\x00'


def test_setauxiliarylogstatus_encode_req():
    m = pyipmi.msgs.sel.SetAuxiliaryLogStatusReq()
    m.log.type = 0
    m.log_data = array('B', [0x11, 0x22])
    assert m.__netfn__ == 0x0a
    assert m.__cmdid__ == 0x5b
    assert encode_message(m) == b'\x00\x11\x22'


def test_getseltimeutcoffset_decode_rsp():
    m = pyipmi.msgs.sel.GetSelTimeUtcOffsetRsp()
    decode_message(m, b'\x00\xc4\xff')
    assert m.__cmdid__ == 0x5c
    assert m.completion_code == 0x00
    assert m.offset == 0xffc4


def test_setseltimeutcoffset_encode_req():
    m = pyipmi.msgs.sel.SetSelTimeUtcOffsetReq()
    m.offset = 0x003c
    assert m.__netfn__ == 0x0a
    assert m.__cmdid__ == 0x5d
    assert encode_message(m) == b'\x3c\x00'
