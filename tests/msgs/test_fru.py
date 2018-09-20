#!/usr/bin/env python

from array import array

from nose.tools import eq_, raises

import pyipmi.msgs.fru

from pyipmi.errors import DecodingError, EncodingError
from pyipmi.msgs import encode_message
from pyipmi.msgs import decode_message


def test_fruinventoryareainfo_decode_valid_rsp():
    m = pyipmi.msgs.fru.GetFruInventoryAreaInfoRsp()
    decode_message(m, '\x00\x01\x02\x01')
    eq_(m.completion_code, 0x00)
    eq_(m.area_size, 0x0201)
    eq_(m.area_info.access, 1)

def test_writefrudatareq_decode_valid_req():
    m = pyipmi.msgs.fru.WriteFruDataReq()
    decode_message(m, '\x01\x02\x03\x04\x05')
    eq_(m.fru_id, 1)
    eq_(m.offset, 0x302)
    eq_(m.data, array('B', b'\x04\x05'))

def test_writefrudatareq_encode_valid_req():
    m = pyipmi.msgs.fru.WriteFruDataReq()
    m.fru_id = 1
    m.offset = 0x302
    m.data = array('B', b'\x04\x05')
    data = encode_message(m)
    eq_(data, '\x01\x02\x03\x04\x05')

def test_writefrudatareq_decode_valid_req_wo_data():
    m = pyipmi.msgs.fru.WriteFruDataReq()
    decode_message(m, '\x01\x02\x03')
    eq_(m.fru_id, 1)
    eq_(m.offset, 0x302)
    eq_(m.data, array('B'))

def test_writefrudatareq_encode_valid_req_wo_data():
    m = pyipmi.msgs.fru.WriteFruDataReq()
    m.fru_id = 1
    m.offset = 0x302
    m.data = array('B')
    data = encode_message(m)
    eq_(data, '\x01\x02\x03')

@raises(DecodingError)
def test_writefrudatareq_decode_invalid_req():
    m = pyipmi.msgs.fru.WriteFruDataReq()
    decode_message(m, '\x01\x02')

def test_readfrudatareq_decode_valid_req():
    m = pyipmi.msgs.fru.ReadFruDataReq()
    decode_message(m, '\x01\x02\x03\x04')
    eq_(m.fru_id, 1)
    eq_(m.offset, 0x302)
    eq_(m.count, 4)

@raises(DecodingError)
def test_readfrudatareq_decode_short_req():
    m = pyipmi.msgs.fru.ReadFruDataReq()
    decode_message(m, '\x01\x02\x03')

@raises(DecodingError)
def test_readfrudatareq_decode_long_req():
    m = pyipmi.msgs.fru.ReadFruDataReq()
    decode_message(m, '\x01\x02\x03\04\x05')

def test_readfrudatareq_encode_valid_req():
    m = pyipmi.msgs.fru.ReadFruDataReq()
    m.fru_id = 1
    m.offset = 0x302
    m.count = 4
    data = encode_message(m)
    eq_(data, '\x01\x02\x03\x04')

def test_readfrudatarsp_decode_valid_rsp():
    m = pyipmi.msgs.fru.ReadFruDataRsp()
    decode_message(m, '\x00\x05\x01\x02\x03\x04\x05')
    eq_(m.completion_code, 0)
    eq_(m.count, 5)
    eq_(m.data, array('B', b'\x01\x02\x03\x04\x05'))

def test_readfrudatarsp_decode_rsp_with_cc():
    m = pyipmi.msgs.fru.ReadFruDataRsp()
    decode_message(m, '\xc0')
    eq_(m.completion_code, 0xc0)

@raises(DecodingError)
def test_readfrudatarsp_decode_invalid_rsp():
    m = pyipmi.msgs.fru.ReadFruDataRsp()
    decode_message(m, '\x00\x01\x01\x02')

def test_readfrudatarsp_encode_valid_rsp():
    m = pyipmi.msgs.fru.ReadFruDataRsp()
    m.completion_code = 0
    m.count = 5
    m.data = array('B', b'\x01\x02\x03\x04\x05')
    data = encode_message(m)
    eq_(data, '\x00\x05\x01\x02\x03\x04\x05')

@raises(EncodingError)
def test_readfrudatarsp_encode_invalid_rsp():
    m = pyipmi.msgs.fru.ReadFruDataRsp()
    m.completion_code = 0
    m.count = 1
    m.data = array('B', b'\x01\x02')
    encode_message(m)
