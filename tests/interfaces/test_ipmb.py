#!/usr/bin/env python
#-*- coding: utf-8 -*-

from array import array

import nose
from nose.tools import eq_, ok_, raises

from pyipmi import Target
from pyipmi.interfaces.ipmb import checksum, IpmbHeader, encode_ipmb_msg, \
        encode_send_message, encode_bridged_message, rx_filter

def test_checksum():
    eq_(checksum([1,2,3,4,5]), 256-15)

def test_encode():
    header = IpmbHeader()
    header.rs_lun = 0
    header.rs_sa = 0x72
    header.rq_seq = 2
    header.rq_lun = 0
    header.rq_sa = 0x20
    header.netfn = 6
    header.cmd_id = 1
    data = header.encode()
    eq_(data, array('B', [0x72, 0x18, 0x76, 0x20, 0x08, 0x01]))

def test_encode_ipmb_msg():
    header = IpmbHeader()
    header.rs_lun = 0
    header.rs_sa = 0x72
    header.rq_seq = 2
    header.rq_lun = 0
    header.rq_sa = 0x20
    header.netfn = 6
    header.cmd_id = 1

    eq_(encode_ipmb_msg(header, [0xaa,0xbb,0xcc]),
            '\x72\x18\x76\x20\x08\x01\xaa\xbb\xcc\xa6')

    eq_(encode_ipmb_msg(header, '\xaa\xbb\xcc'),
            '\x72\x18\x76\x20\x08\x01\xaa\xbb\xcc\xa6')

def test_encode_send_message():
    data = encode_send_message('\xaa\xbb', 0x12, 0x20, 7, 0x22)
    eq_(data, '\x20\x18\xc8\x12\x88\x34\x47\xaa\xbb\x86')

def test_encode_bridge_message():
    payload = '\xaa\xbb'
    t = Target(0)
    t.set_routing([(0x81,0x20,7),(0x20,0x72,None)])
    header = IpmbHeader()
    header.netfn = 6
    header.rs_lun = 0
    header.rq_seq = 0x11
    header.rq_lun = 0
    header.cmd_id = 0xaa
    tx_data = encode_bridged_message(t.routing, header, payload, 0x22)
    eq_(tx_data,
        '\x20\x18\xc8\x81\x88\x34\x47\x72\x18\x76\x20\x44\xaa\xaa\xbb\x8d\x7c')
