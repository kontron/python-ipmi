#!/usr/bin/env python

from array import array

from nose.tools import eq_, raises

import pyipmi.msgs.sdr

from pyipmi.errors import DecodingError, EncodingError
from pyipmi.msgs import encode_message
from pyipmi.msgs import decode_message


def test_getsdrrepositoryinfo_encode_req():
    m = pyipmi.msgs.sdr.GetSdrRepositoryInfoReq()
    data = encode_message(m)
    eq_(data, '')

def test_getsdrrepositoryinfo_decode_rsp():
    m = pyipmi.msgs.sdr.GetSdrRepositoryInfoRsp()
    decode_message(m,'\x00\x51\x00\x11\x55\xaa\x11\x22\x33\x44\x55\x66\x77\x88\xaa')
    eq_(m.completion_code,  0x00)
    eq_(m.sdr_version,  0x51)
    eq_(m.record_count,  0x1100)
    eq_(m.free_space,  0xaa55)
    eq_(m.most_recent_addition, 0x44332211)
    eq_(m.most_recent_erase, 0x88776655)
    eq_(m.support.get_allocation_info, 0)
    eq_(m.support.reserve, 1)
    eq_(m.support.partial_add, 0)
    eq_(m.support.delete, 1)
    eq_(m.support.update_type, 1)
    eq_(m.support.overflow_flag, 1)

def test_getsdrrepositoryallocationinfo_encode_req():
    m = pyipmi.msgs.sdr.GetSdrRepositoryAllocationInfoReq()
    data = encode_message(m)
    eq_(data, '')

def test_getsdrrepositoryallocationinfo_decode_rsp():
    m = pyipmi.msgs.sdr.GetSdrRepositoryAllocationInfoRsp()
    decode_message(m,'\x00\x11\x22\x33\x44\x55\x66\x77\x88\xaa')
    eq_(m.completion_code, 0x00)
    eq_(m.number_of_units, 0x2211)
    eq_(m.unit_size, 0x4433)
    eq_(m.free_units, 0x6655)
    eq_(m.largest_free_block, 0x8877)
    eq_(m.maximum_record_size, 0xaa)

def test_reservesdrrepository_encode_req():
    m = pyipmi.msgs.sdr.ReserveSdrRepositoryReq()
    data = encode_message(m)
    eq_(data, '')

def test_reservesdrrepository_decode_rsp():
    m = pyipmi.msgs.sdr.ReserveSdrRepositoryRsp()
    decode_message(m,'\x00\x11\x22')
    eq_(m.completion_code, 0x00)
    eq_(m.reservation_id, 0x2211)

def test_getsdr_encode_req():
    m = pyipmi.msgs.sdr.GetSdrReq()
    m.reservation_id = 0x1122
    m.record_id = 0x3344
    m.offset = 0xaa
    m.bytes_to_read = 0x55
    data = encode_message(m)
    eq_(data, '\x22\x11\x44\x33\xaa\x55')

def test_getsdr_decode_rsp():
    m = pyipmi.msgs.sdr.GetSdrRsp()
    decode_message(m,'\x00\x11\x22\x33\x44\x55\x66')
    eq_(m.completion_code, 0x00)
    eq_(m.next_record_id, 0x2211)
    eq_(m.record_data, array('B', [0x33, 0x44, 0x55, 0x66]))

def test_addsdr_encode_req():
    m = pyipmi.msgs.sdr.AddSdrReq()
    m.record_data = array('B', [0x55, 0x44])
    data = encode_message(m)
    eq_(data, '\x55\x44')

def test_addsdr_decode_rsp():
    m = pyipmi.msgs.sdr.AddSdrRsp()
    decode_message(m,'\x00\x11\x22')
    eq_(m.completion_code, 0x00)
    eq_(m.record_id, 0x2211)

def test_partialaddsdr_encode_req():
    m = pyipmi.msgs.sdr.PartialAddSdrReq()
    m.reservation_id = 0x2211
    m.record_id = 0x4433
    m.offset = 0xaa
    m.status.in_progress = 0xaa
    m.record_data = array('B', [0x55, 0x44])
    data = encode_message(m)
    eq_(data, '\x11\x22\x33\x44\xaa\x0a\x55\x44')

def test_partialaddsdr_decode_rsp():
    m = pyipmi.msgs.sdr.PartialAddSdrRsp()
    decode_message(m,'\x00\x11\x22')
    eq_(m.completion_code, 0x00)
    eq_(m.record_id, 0x2211)

def test_deletesdr_encode_req():
    m = pyipmi.msgs.sdr.DeleteSdrReq()
    m.reservation_id = 0x2211
    m.record_id = 0x4433
    data = encode_message(m)
    eq_(data, '\x11\x22\x33\x44')

def test_deletesdr_decode_rsp():
    m = pyipmi.msgs.sdr.DeleteSdrRsp()
    decode_message(m,'\x00\x11\x22')
    eq_(m.completion_code, 0x00)
    eq_(m.record_id, 0x2211)

def test_clearsdrrepository_encode_req():
    m = pyipmi.msgs.sdr.ClearSdrRepositoryReq()
    m.reservation_id = 0x2211
    m.cmd = 1
    data = encode_message(m)
    eq_(data, '\x11"CLR\x01')

def test_clearsdrrepository_decode_rsp():
    m = pyipmi.msgs.sdr.ClearSdrRepositoryRsp()
    decode_message(m,'\x00\x11')
    eq_(m.completion_code, 0x00)
    eq_(m.status.erase_in_progress, 0x1)
