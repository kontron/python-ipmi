#!/usr/bin/env python

import array
import socket
import time
from unittest.mock import MagicMock
import pytest
from pyipmi.session import Session
from pyipmi.interfaces.rmcp import (AsfMsg, AsfPing, AsfPong, IpmiMsg, RmcpMsg, Rmcp)
from pyipmi.utils import py3_array_tobytes
from pyipmi.errors import DecodingError, IpmiConnectionError, RetryError
from pyipmi.interfaces.ipmb import IpmbHeaderReq, encode_ipmb_msg


class TestRmcpMsg:
    def test_rmcpmsg_pack(self):
        m = RmcpMsg(0x7)
        pdu = m.pack(None, 0xff)
        assert pdu == b'\x06\x00\xff\x07'

        m = RmcpMsg(0x7)
        pdu = m.pack(b'\x11\x22\x33\x44', 0xff)
        assert pdu == b'\x06\x00\xff\x07\x11\x22\x33\x44'

    def test_rmcpmsg_unpack(self):
        pdu = b'\x06\x00\xee\x07\x44\x33\x22\x11'
        m = RmcpMsg()
        sdu = m.unpack(pdu)
        assert m.version == 6
        assert m.seq_number == 0xee
        assert m.class_of_msg == 0x7
        assert sdu == b'\x44\x33\x22\x11'


class TestAsfMsg:
    def test_pack(self):
        m = AsfMsg()
        pdu = m.pack()
        assert pdu == b'\x00\x00\x11\xbe\x00\x00\x00\x00'

    def test_unpack(self):
        pdu = b'\x00\x00\x11\xbe\x00\x00\x00\x00'
        msg = AsfMsg()
        msg.unpack(pdu)

    def test_tostr(self):
        m = AsfMsg()
        m.data = b'\xaa\xbb\xcc'
        assert str(m) == 'aa bb cc'


class TestAsfPing:
    def test_pack(self):
        m = AsfPing()
        pdu = m.pack()
        assert pdu == b'\x00\x00\x11\xbe\x80\x00\x00\x00'


class TestAsfPong:
    def test_unpack(self):
        pdu = b'\x00\x00\x11\xbe\x40\x00\x00\x10\x00\x00\x11\xbe\x00\x00\x00\x00\x81\x00\x00\x00\x00\x00\x00\x00'
        m = AsfPong()
        m.unpack(pdu)


class TestIpmiMsg:
    def test_ipmimsg_pack(self):
        m = IpmiMsg()
        pdu = m.pack(None)
        assert pdu == b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

    def test_ipmimsg_pack_password(self):
        s = Session()
        s.set_auth_type_user('admin', 'admin')
        m = IpmiMsg(session=s)
        psw = m._padd_password()
        assert psw == b'admin\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

        s = Session()
        s.set_auth_type_user(b'admin', b'admin')
        m = IpmiMsg(session=s)
        psw = m._padd_password()
        assert psw == b'admin\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

    def test_ipmimsg_pack_with_data(self):
        data = py3_array_tobytes(array.array('B', (1, 2, 3, 4)))
        m = IpmiMsg()
        pdu = m.pack(data)
        assert pdu == b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\x01\x02\x03\x04'

    def test_ipmimsg_pack_with_session(self):
        s = Session()
        s.set_auth_type_user('admin', 'admin')
        s.sequence_number = 0x14131211
        s.sid = 0x18171615
        m = IpmiMsg(session=s)
        pdu = m.pack(None)
        assert pdu == b'\x04\x11\x12\x13\x14\x15\x16\x17\x18admin\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

    def test_ipmimsg_pack_auth_md5(self):
        s = Session()
        s.set_auth_type_user('admin', 'admin')
        s.sid = 0x02f99b85
        m = IpmiMsg(session=s)
        sdu = b'\x20\x18\xc8\x81\x0c\x3a\x02\x04\xe1\x2c\xb4\xd3\x17\xdc\x40\xdf\xe9\x78\x1e\x6d\x8e\x10\xad\xeb\x2c\xe8\x5c\xa0\x5b'
        auth = m._pack_auth_code_md5(sdu)
        assert auth == b'\x40\x46\xb1\x51\x4c\x89\x7f\x73\xc2\xfb\xa7\x4d\xf8\x03\x73\x8c'

    def test_ipmimsg_unpack(self):
        pdu = b'\x00\x11\x22\x33\x44\x55\x66\x77\x88\x00'
        m = IpmiMsg()
        m.unpack(pdu)

        assert m.auth_type == 0
        assert m.sequence_number == 0x11223344
        assert m.session_id == 0x55667788

    def test_ipmimsg_unpack_auth(self):
        pdu = b'\x01\x11\x22\x33\x44\x55\x66\x77\x88\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x00'
        m = IpmiMsg()
        m.unpack(pdu)

        assert m.auth_type == 1
        assert m.sequence_number == 0x11223344
        assert m.session_id == 0x55667788
        assert m.auth_code == [1, 2, 3, 4, 5, 6, 7, 8,
                               9, 10, 11, 12, 13, 14, 15, 16]

    def test_ipmimsg_unpack_check_sdu_length(self):
        pdu = b'\x01\x11\x22\x33\x44\x55\x66\x77\x88\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x02\x00\x00\x00'
        m = IpmiMsg()
        with pytest.raises(DecodingError):
            # data len is 2 ( byte 25 = \x02) but actual payload length is 3
            # (\x00\x00\x00) so we have len(pdu) != header_len + data_len
            m.unpack(pdu)

    def test_ipmimsg_unpack_no_check_sdu_length(self):
        pdu = b'\x01\x11\x22\x33\x44\x55\x66\x77\x88\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x02\x00\x00\x00'
        m = IpmiMsg(ignore_sdu_length=True)
        # Same PDU here, we have len(pdu) != header_len + data_len
        sdu = m.unpack(pdu)

        assert m.auth_type == 1
        assert m.sequence_number == 0x11223344
        assert m.session_id == 0x55667788
        assert m.auth_code == [1, 2, 3, 4, 5, 6, 7, 8,
                               9, 10, 11, 12, 13, 14, 15, 16]
        assert sdu == b'\x00\x00\x00'

    def tests_ipmimsg_unpack_no_check_sdu_length_empty_sdu(self):
        pdu = b'\x01\x11\x22\x33\x44\x55\x66\x77\x88\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x02'
        m = IpmiMsg(ignore_sdu_length=True)
        # We have len(pdu) != header_len + data_len
        sdu = m.unpack(pdu)

        assert m.auth_type == 1
        assert m.sequence_number == 0x11223344
        assert m.session_id == 0x55667788
        assert m.auth_code == [1, 2, 3, 4, 5, 6, 7, 8,
                               9, 10, 11, 12, 13, 14, 15, 16]
        assert sdu is None


class TestRmcp:
    def test_send_and_receive_raw(self):
        mock_socket = MagicMock(spec=socket.socket)
        expected_send = (
            b"\x06"              # RMCP Version (06h)
            b"\x00"              # RMCP Reserved
            b"\xff"              # RMCP Sequence Number (Unsequenced)
            b"\x07"              # RMCP Class (07h = IPMI)

            # --- IPMI LAN Session Wrapper ---
            b"\x00"              # Authentication Type (00h = None / v1.5)
            b"\x00\x00\x00\x00"  # Session ID (00000000h for unauthenticated/handshake)
            b"\x00\x00\x00\x00"  # Inbound Sequence Number
            b"\x07"              # Message Length (7 bytes follow)

            # --- IPMB HEADER ---
            b"\x20"              # Target Address / Requester (0x20 = BMC)
            b"\x18"              # NetFn/LUN (NetFn 6 = App Response << 2 | LUN 0) -> 0x18
            b"\xc8"              # Header Checksum (Zero-sum of preceding 2 bytes)

            b"\x81"              # Source Address / Responder (0x81 = remote proxy)
            b"\x04"              # SeqNo/LUN (Sequence Number 1 << 2 | LUN 0) -> 0x04
            b"\x00"              # Command (00h)
            b"\x7b"              # Data Checksum (Zero-sum of preceding 3 bytes)
            )
        expected_recv = (
            # --- RMCP Header ---
            b"\x06"              # RMCP Version (06h)
            b"\x00"              # RMCP Reserved
            b"\xff"              # RMCP Sequence Number (Unsequenced)
            b"\x07"              # RMCP Class (07h = IPMI)

            # --- IPMI LAN Session Wrapper ---
            b"\x00"              # Authentication Type (00h = None / v1.5)
            b"\x00\x00\x00\x00"  # Session ID (00000000h for unauthenticated/handshake)
            b"\x00\x00\x00\x00"  # Inbound Sequence Number
            b"\x08"              # Message Length (8 bytes follow)

            # --- IPMB HEADER ---
            b"\x81"              # Target Address / Requester (e.g., 0x81 for remote proxy)
            b"\x1c"              # NetFn/LUN (NetFn 7 = App Response << 2 | LUN 0) -> 0x1C
            b"\x63"              # Header Checksum (Zero-sum of preceding 2 bytes)

            b"\x20"              # Source Address / Responder (0x20 = BMC)
            b"\x04"              # SeqNo/LUN (Sequence Number 1 << 2 | LUN 0) -> 0x04
            b"\x00"              # Command (00h)
            b"\xc1"              # Completion Code (0xC1 = Invalid Command)
            b"\x1b"              # Data Checksum (Zero-sum of preceding 4 bytes)
            )

        rmcp = Rmcp()
        rmcp._sock = mock_socket
        mock_socket.recv.return_value = expected_recv
        result = rmcp.send_and_receive_raw(rmcp.host_target, 0, 6, b'\x00')
        mock_socket.send.assert_called_with(expected_send)
        assert result == b'\xc1'

    def test_send_and_receive(self):
        pass

    def test_keep_alive_skipped_while_busy(self):
        rmcp = Rmcp(keep_alive_interval=1)
        rmcp._get_device_id = MagicMock()

        # a request was sent during the last interval
        rmcp._last_request_time = time.monotonic() - 0.5
        rmcp._keep_alive()
        rmcp._get_device_id.assert_not_called()

        # idle for the whole interval
        rmcp._last_request_time = time.monotonic() - 1.0
        rmcp._keep_alive()
        rmcp._get_device_id.assert_called_once()

    def test_send_and_receive_updates_last_request_time(self):
        rmcp = Rmcp()
        rmcp._sock = MagicMock(spec=socket.socket)
        rmcp._sock.recv.return_value = (
            b'\x06\x00\xff\x07\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08'
            b'\x81\x1c\x63\x20\x04\x00\xc1\x1b')
        before = time.monotonic()
        rmcp.send_and_receive_raw(rmcp.host_target, 0, 6, b'\x00')
        assert rmcp._last_request_time >= before

    @pytest.mark.parametrize('exc, msg', [
        (TimeoutError, 'no response to RMCP ping from 10.0.0.1:623'),
        (ConnectionRefusedError, 'connection to 10.0.0.1:623 refused'),
    ])
    def test_ping_error(self, exc, msg):
        rmcp = Rmcp()
        rmcp.host = '10.0.0.1'
        rmcp.port = 623
        rmcp._sock = MagicMock(spec=socket.socket)
        rmcp._sock.recv.side_effect = exc
        with pytest.raises(IpmiConnectionError, match=msg):
            rmcp.ping()


def _rmcp_rsp(seq, data=b'\x00\xaa'):
    """Return an unauthenticated RMCP packet with a Get Device ID response."""
    header = IpmbHeaderReq()
    header.netfn = 7
    header.rs_lun = 0
    header.rs_sa = 0x81
    header.rq_seq = seq
    header.rq_lun = 0
    header.rq_sa = 0x20
    header.cmdid = 1
    msg = encode_ipmb_msg(header, data)
    return (b'\x06\x00\xff\x07\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            + bytes([len(msg)]) + msg)


class TestRmcpLateResponse:
    """A late response of an earlier request must not break later ones."""

    def _rmcp(self, max_retries=0):
        rmcp = Rmcp(max_retries=max_retries)
        rmcp._sock = MagicMock(spec=socket.socket)
        rmcp._timeout = 2.0
        rmcp.host = 'test'
        return rmcp

    def _next_seq(self, rmcp):
        return (rmcp.next_sequence_number + 1) % 64

    def test_late_response_is_discarded(self):
        rmcp = self._rmcp()
        seq = self._next_seq(rmcp)
        rmcp._sock.recv.side_effect = [_rmcp_rsp(seq - 1, b'\x00\x11'),
                                       _rmcp_rsp(seq, b'\x00\x22')]
        assert rmcp.send_and_receive_raw(rmcp.host_target, 0, 6,
                                         b'\x01') == b'\x00\x22'

    def test_next_request_after_late_response(self):
        rmcp = self._rmcp()
        seq = self._next_seq(rmcp)
        rmcp._sock.recv.side_effect = [_rmcp_rsp(seq - 1),
                                       _rmcp_rsp(seq, b'\x00\x22'),
                                       _rmcp_rsp(seq + 1, b'\x00\x33')]
        rmcp.send_and_receive_raw(rmcp.host_target, 0, 6, b'\x01')
        assert rmcp.send_and_receive_raw(rmcp.host_target, 0, 6,
                                         b'\x01') == b'\x00\x33'

    def test_socket_timeout(self):
        rmcp = self._rmcp(max_retries=1)
        rmcp._sock.recv.side_effect = TimeoutError()
        with pytest.raises(RetryError):
            rmcp.send_and_receive_raw(rmcp.host_target, 0, 6, b'\x01')
        # the request is sent again for each retry
        assert rmcp._sock.send.call_count == 2

    def test_only_unrelated_messages_times_out(self):
        rmcp = self._rmcp()
        rmcp._timeout = 0.05
        seq = self._next_seq(rmcp)
        rmcp._sock.recv.side_effect = lambda size: _rmcp_rsp(seq - 1)
        with pytest.raises(RetryError):
            rmcp.send_and_receive_raw(rmcp.host_target, 0, 6, b'\x01')


class TestAsfPongPack:
    def test_pack_unpack(self):
        pong = AsfPong()
        pong.tag = 0x12
        pong.supported_entities = 0x81
        pdu = pong.pack()
        # ASF header followed by 16 bytes of pong data
        assert pdu[:8] == b'\x00\x00\x11\xbe\x40\x12\x00\x10'
        assert len(pdu) == 8 + 16

        m = AsfPong()
        m.unpack(pdu)
        assert m.tag == 0x12
        assert m.supported_entities == 0x81


class TestRmcpCloseSession:
    def test_close_without_session(self):
        rmcp = Rmcp(keep_alive_interval=0)
        rmcp._sock = MagicMock(spec=socket.socket)
        # establishing the session failed, close must not raise
        rmcp.close_session()
        rmcp._sock.send.assert_not_called()
