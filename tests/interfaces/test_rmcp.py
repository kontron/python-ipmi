#!/usr/bin/env python
#-*- coding: utf-8 -*-

import nose
import array

from mock import MagicMock
from nose.tools import eq_, raises

from pyipmi.errors import TimeoutError
from pyipmi.interfaces.rmcp import AsfMsg, IpmiMsg


class TestAsfMsg:

    def test_asfmsg(self):
        a = AsfMsg()
        sdu = a.pack()
        eq_(sdu, '\x00\x00\x11\xbe\x00\x00\x00\x00')

    def test_ipmimsg_pack(self):
        a = IpmiMsg()
        a.authentication_type = 0
        a.sequence_number = 0x11223344
        a.session_id = 0x55667788
        sdu = a.pack()
        eq_(sdu, '\x00\x11\x22\x33\x44\x55\x66\x77\x88\x00')

    def test_ipmimsg_pack_with_data(self):
        data = array.array('B', (1,2,3,4)).tostring()
        a = IpmiMsg(data=data)
        a.authentication_type = 0
        a.sequence_number = 0
        a.session_id = 0
        sdu = a.pack()
        eq_(sdu, '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\x01\x02\x03\x04')

    def test_ipmimsg_pack_auth(self):
        a = IpmiMsg()
        a.authentication_type = 1
        a.sequence_number = 0x11223344
        a.session_id = 0x55667788
        a.authentication_code = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16]
        sdu = a.pack()
        eq_(sdu,
        '\x01\x11\x22\x33\x44\x55\x66\x77\x88\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x00')

    def test_ipmimsg_unpack(self):
        pdu = '\x00\x11\x22\x33\x44\x55\x66\x77\x88\x00'
        a = IpmiMsg()
        a.unpack(pdu)

        eq_(a.authentication_type, 0)
        eq_(a.sequence_number, 0x11223344)
        eq_(a.session_id, 0x55667788)

    def test_ipmimsg_unpack_auth(self):
        pdu =\
        '\x01\x11\x22\x33\x44\x55\x66\x77\x88\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x00'
        a = IpmiMsg()
        a.unpack(pdu)

        eq_(a.authentication_type, 1)
        eq_(a.sequence_number, 0x11223344)
        eq_(a.session_id, 0x55667788)
        eq_(a.authentication_code,  [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16])
