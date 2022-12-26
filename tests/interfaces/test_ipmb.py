#!/usr/bin/env python
# -*- coding: utf-8 -*-

from array import array

from pyipmi import Target
from pyipmi.interfaces.ipmb import (checksum, IpmbHeaderReq, IpmbHeaderRsp,
                                    encode_send_message, encode_bridged_message,
                                    encode_ipmb_msg, decode_bridged_message,
                                    rx_filter)


def test_checksum():
    assert checksum([1, 2, 3, 4, 5]) == 256-15


def test_header_req_encode():
    header = IpmbHeaderReq()
    header.rs_lun = 0
    header.rs_sa = 0x72
    header.rq_seq = 2
    header.rq_lun = 1
    header.rq_sa = 0x20
    header.netfn = 6
    header.cmdid = 1
    data = header.encode()
    assert data == b'\x72\x18\x76\x20\x09\x01'


def test_header_req_decode():
    header = IpmbHeaderReq()
    header.decode(b'\x72\x19\x76\x20\x08\x01')
    assert header.rs_sa == 0x72
    assert header.rs_lun == 1
    assert header.rq_sa == 0x20
    assert header.rq_lun == 0
    assert header.netfn == 6

    header = IpmbHeaderReq(data=b'\x72\x19\x76\x20\x08\x01')
    assert header.rs_sa == 0x72
    assert header.rs_lun == 1
    assert header.rq_sa == 0x20
    assert header.rq_lun == 0
    assert header.netfn == 6


def test_header_rsp_encode():
    header = IpmbHeaderRsp()
    header.rs_lun = 0
    header.rs_sa = 0x72
    header.rq_seq = 2
    header.rq_lun = 1
    header.rq_sa = 0x20
    header.netfn = 6
    header.cmdid = 1
    data = header.encode()
    assert data == b'\x20\x19\xc7\x72\x08\x01'


def test_header_rsp_decode():
    header = IpmbHeaderRsp()
    header.decode(b'\x72\x19\x76\x20\x08\x01')
    assert header.rq_sa == 0x72
    assert header.rq_lun == 1
    assert header.rs_sa == 0x20
    assert header.rs_lun == 0
    assert header.netfn == 6

    header = IpmbHeaderRsp(data=b'\x72\x19\x76\x20\x08\x01')
    assert header.rq_sa == 0x72
    assert header.rq_lun == 1
    assert header.rs_sa == 0x20
    assert header.rs_lun == 0
    assert header.netfn == 6


def test_encode_ipmb_msg():
    header = IpmbHeaderReq()
    header.rs_lun = 0
    header.rs_sa = 0x72
    header.rq_seq = 2
    header.rq_lun = 0
    header.rq_sa = 0x20
    header.netfn = 6
    header.cmdid = 1

    assert encode_ipmb_msg(header, b'\xaa\xbb\xcc') == \
        b'\x72\x18\x76\x20\x08\x01\xaa\xbb\xcc\xa6'


def test_encode_send_message():
    data = encode_send_message(b'\xaa\xbb', 0x12, 0x20, 7, 0x22)
    assert data == b'\x20\x18\xc8\x12\x88\x34\x47\xaa\xbb\x86'


def test_encode_bridged_message():
    payload = array('B', b'\xaa\xbb')
    t = Target(0)
    t.set_routing([(0x81, 0x20, 7), (0x20, 0x72, None)])
    header = IpmbHeaderReq()
    header.netfn = 6
    header.rs_lun = 0
    header.rq_seq = 0x11
    header.rq_lun = 0
    header.cmdid = 0xaa
    data = encode_bridged_message(t.routing, header, payload, seq=0x22)
    assert data == \
        b'\x20\x18\xc8\x81\x88\x34\x47\x72\x18\x76\x20\x44\xaa\xaa\xbb\x8d\x7c'


def test_decode_bridged_message():
    # 81 1c 63 20 14 34 00 20 1c c4 82 14 34 00 20 14 cc 74 14 22 00 ed ff 6a 36
    data = b'\x81\x1c\x63\x20\x14\x34\x00\x20\x1c\xc4\x82\x14\x34\x00\x20\x14\xcc\x74\x14\x22\x00\xed\xff\x6a\x36'
    data = decode_bridged_message(data)
    assert len(data) == 9
    assert data == b'\x20\x14\xcc\x74\x14\x22\x00\xed\xff'


def test_rx_filter():
    header_req = IpmbHeaderReq()
    header_req.rs_lun = 1
    header_req.rs_sa = 0x72
    header_req.rq_seq = 2
    header_req.rq_lun = 0
    header_req.rq_sa = 0x20
    header_req.netfn = 6
    header_req.cmdid = 1

    # requester and responder fields are twisted ... (sa and lun)
    header_rsp = IpmbHeaderReq()
    header_rsp.rs_lun = 0
    header_rsp.rs_sa = 0x20
    header_rsp.rq_seq = 2
    header_rsp.rq_lun = 1
    header_rsp.rq_sa = 0x72
    header_rsp.netfn = 6 + 1
    header_rsp.cmdid = 1

    rx_data = encode_ipmb_msg(header_rsp, b'\xaa\xbb\xcc')

    assert rx_filter(header_req, rx_data)
