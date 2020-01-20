#!/usr/bin/env python
# -*- coding: utf-8 -*-

import array

from mock import MagicMock
from nose.tools import eq_
from pyipmi import Target

from pyipmi.session import Session
from pyipmi.interfaces.rmcp import (AsfMsg, AsfPing, AsfPong, IpmiMsg,
                                    Rmcp, RmcpMsg)
from pyipmi.utils import py3_array_tobytes


class TestRmcpMsg:
    def test_rmcpmsg_pack(self):
        m = RmcpMsg(0x7)
        pdu = m.pack(None, 0xff)
        eq_(pdu, b'\x06\x00\xff\x07')

        m = RmcpMsg(0x7)
        pdu = m.pack(b'\x11\x22\x33\x44', 0xff)
        eq_(pdu, b'\x06\x00\xff\x07\x11\x22\x33\x44')

    def test_rmcpmsg_unpack(self):
        pdu = b'\x06\x00\xee\x07\x44\x33\x22\x11'
        m = RmcpMsg()
        sdu = m.unpack(pdu)
        eq_(m.version, 6)
        eq_(m.seq_number, 0xee)
        eq_(m.class_of_msg, 0x7)
        eq_(sdu, b'\x44\x33\x22\x11')


class TestAsfMsg:
    def test_pack(self):
        m = AsfMsg()
        pdu = m.pack()
        eq_(pdu, b'\x00\x00\x11\xbe\x00\x00\x00\x00')

    def test_unpack(self):
        pdu = b'\x00\x00\x11\xbe\x00\x00\x00\x00'
        msg = AsfMsg()
        msg.unpack(pdu)

    def test_tostr(self):
        m = AsfMsg()
        m.data = b'\xaa\xbb\xcc'
        eq_(str(m), 'aa bb cc')


class TestAsfPing():
    def test_pack(self):
        m = AsfPing()
        pdu = m.pack()
        eq_(pdu, b'\x00\x00\x11\xbe\x80\x00\x00\x00')


class TestAsfPong():
    def test_unpack(self):
        pdu = b'\x00\x00\x11\xbe\x40\x00\x00\x10\x00\x00\x11\xbe\x00\x00\x00\x00\x81\x00\x00\x00\x00\x00\x00\x00'
        m = AsfPong()
        m.unpack(pdu)


class TestIpmiMsg:
    def test_ipmimsg_pack(self):
        m = IpmiMsg()
        pdu = m.pack(None)
        eq_(pdu, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')

    def test_ipmimsg_pack_password(self):
        s = Session()
        s.set_auth_type_user('admin', 'admin')
        m = IpmiMsg(session=s)
        psw = m._padd_password()
        eq_(psw, b'admin\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')

        s = Session()
        s.set_auth_type_user(b'admin', b'admin')
        m = IpmiMsg(session=s)
        psw = m._padd_password()
        eq_(psw, b'admin\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')

    def test_ipmimsg_pack_with_data(self):
        data = py3_array_tobytes(array.array('B', (1, 2, 3, 4)))
        m = IpmiMsg()
        pdu = m.pack(data)
        eq_(pdu, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\x01\x02\x03\x04')

    def test_ipmimsg_pack_with_session(self):
        s = Session()
        s.set_auth_type_user('admin', 'admin')
        s.sequence_number = 0x14131211
        s.sid = 0x18171615
        m = IpmiMsg(session=s)
        pdu = m.pack(None)
        eq_(pdu, b'\x04\x11\x12\x13\x14\x15\x16\x17\x18admin\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')

    def test_ipmimsg_pack_auth_md5(self):
        s = Session()
        s.set_auth_type_user('admin', 'admin')
        s.sid = 0x02f99b85
        m = IpmiMsg(session=s)
        sdu = b'\x20\x18\xc8\x81\x0c\x3a\x02\x04\xe1\x2c\xb4\xd3\x17\xdc\x40\xdf\xe9\x78\x1e\x6d\x8e\x10\xad\xeb\x2c\xe8\x5c\xa0\x5b'
        auth = m._pack_auth_code_md5(sdu)
        eq_(auth, b'\x40\x46\xb1\x51\x4c\x89\x7f\x73\xc2\xfb\xa7\x4d\xf8\x03\x73\x8c')

    def test_ipmimsg_unpack(self):
        pdu = b'\x00\x11\x22\x33\x44\x55\x66\x77\x88\x00'
        m = IpmiMsg()
        m.unpack(pdu)

        eq_(m.auth_type, 0)
        eq_(m.sequence_number, 0x11223344)
        eq_(m.session_id, 0x55667788)

    def test_ipmimsg_unpack_auth(self):
        pdu = b'\x01\x11\x22\x33\x44\x55\x66\x77\x88\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x00'
        m = IpmiMsg()
        m.unpack(pdu)

        eq_(m.auth_type, 1)
        eq_(m.sequence_number, 0x11223344)
        eq_(m.session_id, 0x55667788)
        eq_(m.auth_code,  [1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
                           11, 12, 13, 14, 15, 16])


class TestRmcp:
#    def test_send_and_receive_raw(self):
#        mock_send = MagicMock()
#        mock_recv = MagicMock()
#        mock_recv.return_value = (b'\x06\x00\xee\x07\x00\x00\x00\x00\x00\x00'
#                                  b'\x00\x00\x00\x06'
#                                  b'\x01\x02\x03\x04\x05\x06', 0)
#
#        target = Target()
#        target.ipmb_address = 0x20
#        rmcp = Rmcp()
#        rmcp.host = '10.10.10.10'
#        rmcp.port = 637
#
#        rmcp._sock.sendto = mock_send
#        rmcp._sock.recvfrom = mock_recv
#
#        rmcp.send_and_receive_raw(target, 0, 0, b'\x00')
#        rmcp._send_ipmi_msg.assert_called_with(1)

    def test_send_and_receive(self):
        pass
