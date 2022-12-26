#!/usr/bin/env python

from array import array

import pyipmi.msgs.sdr

from pyipmi.msgs import encode_message
from pyipmi.msgs import decode_message


def test_getsdrrepositoryinfo_encode_req():
    m = pyipmi.msgs.sdr.GetSdrRepositoryInfoReq()
    data = encode_message(m)
    assert data == b''


def test_getsdrrepositoryinfo_decode_rsp():
    m = pyipmi.msgs.sdr.GetSdrRepositoryInfoRsp()
    decode_message(m, b'\x00\x51\x00\x11\x55\xaa\x11\x22\x33\x44\x55\x66\x77\x88\xaa')
    assert m.completion_code ==  0x00
    assert m.sdr_version ==  0x51
    assert m.record_count ==  0x1100
    assert m.free_space ==  0xaa55
    assert m.most_recent_addition == 0x44332211
    assert m.most_recent_erase == 0x88776655
    assert m.support.get_allocation_info == 0
    assert m.support.reserve == 1
    assert m.support.partial_add == 0
    assert m.support.delete == 1
    assert m.support.update_type == 1
    assert m.support.overflow_flag == 1


def test_getsdrrepositoryallocationinfo_encode_req():
    m = pyipmi.msgs.sdr.GetSdrRepositoryAllocationInfoReq()
    data = encode_message(m)
    assert data == b''


def test_getsdrrepositoryallocationinfo_decode_rsp():
    m = pyipmi.msgs.sdr.GetSdrRepositoryAllocationInfoRsp()
    decode_message(m, b'\x00\x11\x22\x33\x44\x55\x66\x77\x88\xaa')
    assert m.completion_code == 0x00
    assert m.number_of_units == 0x2211
    assert m.unit_size == 0x4433
    assert m.free_units == 0x6655
    assert m.largest_free_block == 0x8877
    assert m.maximum_record_size == 0xaa


def test_reservesdrrepository_encode_req():
    m = pyipmi.msgs.sdr.ReserveSdrRepositoryReq()
    data = encode_message(m)
    assert data == b''


def test_reservesdrrepository_decode_rsp():
    m = pyipmi.msgs.sdr.ReserveSdrRepositoryRsp()
    decode_message(m, b'\x00\x11\x22')
    assert m.completion_code == 0x00
    assert m.reservation_id == 0x2211


def test_getsdr_encode_req():
    m = pyipmi.msgs.sdr.GetSdrReq()
    m.reservation_id = 0x1122
    m.record_id = 0x3344
    m.offset = 0xaa
    m.bytes_to_read = 0x55
    data = encode_message(m)
    assert data == b'\x22\x11\x44\x33\xaa\x55'


def test_getsdr_decode_rsp():
    m = pyipmi.msgs.sdr.GetSdrRsp()
    decode_message(m, b'\x00\x11\x22\x33\x44\x55\x66')
    assert m.completion_code == 0x00
    assert m.next_record_id == 0x2211
    assert m.record_data == array('B', [0x33, 0x44, 0x55, 0x66])


def test_addsdr_encode_req():
    m = pyipmi.msgs.sdr.AddSdrReq()
    m.record_data = array('B', [0x55, 0x44])
    data = encode_message(m)
    assert data == b'\x55\x44'


def test_addsdr_decode_rsp():
    m = pyipmi.msgs.sdr.AddSdrRsp()
    decode_message(m, b'\x00\x11\x22')
    assert m.completion_code == 0x00
    assert m.record_id == 0x2211


def test_partialaddsdr_encode_req():
    m = pyipmi.msgs.sdr.PartialAddSdrReq()
    m.reservation_id = 0x2211
    m.record_id = 0x4433
    m.offset = 0xaa
    m.status.in_progress = 0xaa
    m.record_data = array('B', [0x55, 0x44])
    data = encode_message(m)
    assert data == b'\x11\x22\x33\x44\xaa\x0a\x55\x44'


def test_partialaddsdr_decode_rsp():
    m = pyipmi.msgs.sdr.PartialAddSdrRsp()
    decode_message(m, b'\x00\x11\x22')
    assert m.completion_code == 0x00
    assert m.record_id == 0x2211


def test_deletesdr_encode_req():
    m = pyipmi.msgs.sdr.DeleteSdrReq()
    m.reservation_id = 0x2211
    m.record_id = 0x4433
    data = encode_message(m)
    assert data == b'\x11\x22\x33\x44'


def test_deletesdr_decode_rsp():
    m = pyipmi.msgs.sdr.DeleteSdrRsp()
    decode_message(m, b'\x00\x11\x22')
    assert m.completion_code == 0x00
    assert m.record_id == 0x2211


def test_clearsdrrepository_encode_req():
    m = pyipmi.msgs.sdr.ClearSdrRepositoryReq()
    m.reservation_id = 0x2211
    m.cmd = 1
    data = encode_message(m)
    assert data == b'\x11"CLR\x01'


def test_clearsdrrepository_decode_rsp():
    m = pyipmi.msgs.sdr.ClearSdrRepositoryRsp()
    decode_message(m, b'\x00\x11')
    assert m.completion_code == 0x00
    assert m.status.erase_in_progress == 0x1
