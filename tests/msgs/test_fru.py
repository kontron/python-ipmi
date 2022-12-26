#!/usr/bin/env python

import pytest

from array import array

import pyipmi
from pyipmi.errors import DecodingError, EncodingError
from pyipmi.msgs import encode_message, decode_message


def test_fruinventoryareainfo_decode_valid_rsp():
    m = pyipmi.msgs.fru.GetFruInventoryAreaInfoRsp()
    decode_message(m, b'\x00\x01\x02\x01')
    assert m.completion_code == 0x00
    assert m.area_size == 0x0201
    assert m.area_info.access == 1


def test_writefrudatareq_decode_valid_req():
    m = pyipmi.msgs.fru.WriteFruDataReq()
    decode_message(m, b'\x01\x02\x03\x04\x05')
    assert m.fru_id == 1
    assert m.offset == 0x302
    assert m.data == array('B', b'\x04\x05')


def test_writefrudatareq_encode_valid_req():
    m = pyipmi.msgs.fru.WriteFruDataReq()
    m.fru_id = 1
    m.offset = 0x302
    m.data = array('B', b'\x04\x05')
    data = encode_message(m)
    assert data == b'\x01\x02\x03\x04\x05'


def test_writefrudatareq_decode_valid_req_wo_data():
    m = pyipmi.msgs.fru.WriteFruDataReq()
    decode_message(m, b'\x01\x02\x03')
    assert m.fru_id == 1
    assert m.offset == 0x302
    assert m.data == array('B')


def test_writefrudatareq_encode_valid_req_wo_data():
    m = pyipmi.msgs.fru.WriteFruDataReq()
    m.fru_id = 1
    m.offset = 0x302
    m.data = array('B')
    data = encode_message(m)
    assert data == b'\x01\x02\x03'


def test_writefrudatareq_decode_invalid_req():
    m = pyipmi.msgs.fru.WriteFruDataReq()
    with pytest.raises(DecodingError):
        decode_message(m, b'\x01\x02')


def test_readfrudatareq_decode_valid_req():
    m = pyipmi.msgs.fru.ReadFruDataReq()
    decode_message(m, b'\x01\x02\x03\x04')
    assert m.fru_id == 1
    assert m.offset == 0x302
    assert m.count == 4


def test_readfrudatareq_decode_short_req():
    m = pyipmi.msgs.fru.ReadFruDataReq()
    with pytest.raises(DecodingError):
        decode_message(m, b'\x01\x02\x03')


def test_readfrudatareq_decode_long_req():
    m = pyipmi.msgs.fru.ReadFruDataReq()
    with pytest.raises(DecodingError):
        decode_message(m, b'\x01\x02\x03\04\x05')


def test_readfrudatareq_encode_valid_req():
    m = pyipmi.msgs.fru.ReadFruDataReq()
    m.fru_id = 1
    m.offset = 0x302
    m.count = 4
    data = encode_message(m)
    assert data == b'\x01\x02\x03\x04'


def test_readfrudatarsp_decode_valid_rsp():
    m = pyipmi.msgs.fru.ReadFruDataRsp()
    decode_message(m, b'\x00\x05\x01\x02\x03\x04\x05')
    assert m.completion_code == 0
    assert m.count == 5
    assert m.data == array('B', b'\x01\x02\x03\x04\x05')


def test_readfrudatarsp_decode_rsp_with_cc():
    m = pyipmi.msgs.fru.ReadFruDataRsp()
    decode_message(m, b'\xc0')
    assert m.completion_code == 0xc0


def test_readfrudatarsp_decode_invalid_rsp():
    m = pyipmi.msgs.fru.ReadFruDataRsp()
    with pytest.raises(DecodingError):
        decode_message(m, b'\x00\x01\x01\x02')


def test_readfrudatarsp_encode_valid_rsp():
    m = pyipmi.msgs.fru.ReadFruDataRsp()
    m.completion_code = 0
    m.count = 5
    m.data = array('B', b'\x01\x02\x03\x04\x05')
    data = encode_message(m)
    assert data == b'\x00\x05\x01\x02\x03\x04\x05'


def test_readfrudatarsp_encode_invalid_rsp():
    m = pyipmi.msgs.fru.ReadFruDataRsp()
    m.completion_code = 0
    m.count = 1
    m.data = array('B', b'\x01\x02')
    with pytest.raises(EncodingError):
        encode_message(m)
