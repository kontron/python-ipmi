#!/usr/bin/env python
#-*- coding: utf-8 -*-

import nose
import array

from mock import MagicMock
from nose.tools import eq_, raises

from pyipmi import Session
from pyipmi.errors import TimeoutError
from pyipmi.interfaces.rmcp import RmcpMsg, AsfMsg, IpmiMsg


class TestRmcpMsg:
    def test_rmcpmsg_pack(self):
        m = RmcpMsg(0x7)
        pdu = m.pack(None, 0xff)
        eq_(pdu, '\x06\x00\xff\x07')

        m = RmcpMsg(0x7)
        pdu = m.pack('\x11\x22\x33\x44', 0xff)
        eq_(pdu, '\x06\x00\xff\x07\x11\x22\x33\x44')

    def test_rmcpmsg_pack(self):
        pdu = '\x06\x00\xee\x07\x44\x33\x22\x11'
        m = RmcpMsg()
        sdu = m.unpack(pdu)
        eq_(m.version, 6)
        eq_(m.seq_number, 0xee)
        eq_(m.class_of_msg, 0x7)
        eq_(sdu, '\x44\x33\x22\x11')


class TestAsfMsg:

    def test_asfmsg(self):
        m = AsfMsg()
        pdu = m.pack()
        eq_(pdu, '\x00\x00\x11\xbe\x00\x00\x00\x00')


class TestIpmiMsg:
    def test_ipmimsg_pack(self):
        m = IpmiMsg()
        m.sequence_number = 0x11223344
        m.session_id = 0x55667788
        pdu = m.pack(None)
        eq_(pdu, '\x00\x11\x22\x33\x44\x55\x66\x77\x88\x00')

    def test_ipmimsg_pack_with_data(self):
        data = array.array('B', (1,2,3,4)).tostring()
        m = IpmiMsg()
        m.auth_type = 0
        m.sequence_number = 0
        m.session_id = 0
        pdu = m.pack(data)
        eq_(pdu, '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\x01\x02\x03\x04')

    def test_ipmimsg_pack_auth(self):
        m = IpmiMsg()
        m.auth_type = 1
        m.sequence_number = 0x11223344
        m.session_id = 0x55667788
        m.auth_code = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16]
        pdu = m.pack(None)
        eq_(pdu,
        '\x01\x11\x22\x33\x44\x55\x66\x77\x88\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x00')

    def test_ipmimsg_with_session(self):
        s = Session()
        s.set_auth_type_user('abcdefghijklmnop', 'secret')
        m = IpmiMsg(session=s)
        pdu = m.pack(None)
        eq_(pdu,
        '\x04\x00\x00\x00\x00\x00\x00\x00\x00abcdefghijklmnop\x00')

    def test_ipmimsg_unpack(self):
        pdu = '\x00\x11\x22\x33\x44\x55\x66\x77\x88\x00'
        m = IpmiMsg()
        m.unpack(pdu)

        eq_(m.auth_type, 0)
        eq_(m.sequence_number, 0x11223344)
        eq_(m.session_id, 0x55667788)

    def test_ipmimsg_unpack_auth(self):
        pdu =\
        '\x01\x11\x22\x33\x44\x55\x66\x77\x88\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x00'
        m = IpmiMsg()
        m.unpack(pdu)

        eq_(m.auth_type, 1)
        eq_(m.sequence_number, 0x11223344)
        eq_(m.session_id, 0x55667788)
        eq_(m.auth_code,  [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16])
