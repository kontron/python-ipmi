#!/usr/bin/env python

import hashlib
import hmac
import struct
from collections import deque

import pytest

import pyipmi
from pyipmi.errors import (AuthenticationError, DecodingError,
                           MessageStatusCodeError, NotSupportedError)
from pyipmi.interfaces.ipmb import checksum
from pyipmi.interfaces.rmcpplus import (CIPHER_SUITES, PAYLOAD_TYPE_IPMI,
                                        RmcpPlus, SessionKeys, aes_available,
                                        pack_rmcpplus, unpack_rmcpplus)
from pyipmi.ipmitool import parse_interface_options

needs_aes = pytest.mark.skipif(not aes_available(),
                               reason='cryptography package not installed')

SUITE_PARAMS = [
    1, 2, pytest.param(3, marks=needs_aes),
    15, 16, pytest.param(17, marks=needs_aes),
]

SIK = bytes(range(20))


class TestFraming:
    def test_unauthenticated(self):
        pdu = pack_rmcpplus(0x10, b'\x01\x02\x03')
        assert pdu == (b'\x06\x10' + b'\x00' * 8 + b'\x03\x00'
                       + b'\x01\x02\x03')
        assert unpack_rmcpplus(pdu) == (0x10, 0, 0, b'\x01\x02\x03')

    def test_unauthenticated_extra_bytes(self):
        pdu = pack_rmcpplus(0x10, b'\x01') + b'\x00'
        with pytest.raises(DecodingError):
            unpack_rmcpplus(pdu)

    def test_invalid_auth_type(self):
        with pytest.raises(DecodingError):
            unpack_rmcpplus(b'\x00' * 12)

    @pytest.mark.parametrize('suite', [2, 16])
    @pytest.mark.parametrize('length', range(9))
    def test_integrity(self, suite, length):
        keys = SessionKeys(CIPHER_SUITES[suite], SIK)
        payload = bytes(range(length))
        pdu = pack_rmcpplus(PAYLOAD_TYPE_IPMI, payload, 0x11223344, 5, keys)
        assert pdu[1] == 0x40
        # AuthType up to Next Header is a multiple of 4
        assert (len(pdu) - keys.auth_code_length) % 4 == 0
        assert pdu[-keys.auth_code_length - 1] == 0x07
        assert unpack_rmcpplus(pdu, keys) == (PAYLOAD_TYPE_IPMI, 0x11223344,
                                              5, payload)

    def test_integrity_tampered(self):
        keys = SessionKeys(CIPHER_SUITES[2], SIK)
        pdu = bytearray(pack_rmcpplus(PAYLOAD_TYPE_IPMI, b'\x01\x02', 1, 1,
                                      keys))
        pdu[13] ^= 0xff
        with pytest.raises(AuthenticationError):
            unpack_rmcpplus(bytes(pdu), keys)

    def test_integrity_missing(self):
        keys = SessionKeys(CIPHER_SUITES[2], SIK)
        with pytest.raises(AuthenticationError):
            unpack_rmcpplus(pack_rmcpplus(PAYLOAD_TYPE_IPMI, b'\x01'), keys)

    @needs_aes
    @pytest.mark.parametrize('suite', [3, 17])
    @pytest.mark.parametrize('length', range(34))
    def test_confidentiality(self, suite, length):
        keys = SessionKeys(CIPHER_SUITES[suite], SIK)
        payload = bytes(range(length))
        pdu = pack_rmcpplus(PAYLOAD_TYPE_IPMI, payload, 1, 1, keys)
        assert pdu[1] == 0xc0
        (data_len,) = struct.unpack('<H', pdu[10:12])
        assert data_len % 16 == 0
        assert unpack_rmcpplus(pdu, keys)[3] == payload

    @pytest.mark.parametrize('suite,digest', [(3, hashlib.sha1),
                                              (17, hashlib.sha256)])
    def test_key_derivation(self, suite, digest):
        keys = SessionKeys(CIPHER_SUITES[suite], SIK)
        n = digest().digest_size
        assert keys.k1 == hmac.new(SIK, b'\x01' * n, digest).digest()
        assert keys.k2 == hmac.new(SIK, b'\x02' * n, digest).digest()


def ipmb_response(req, data):
    (rs_sa, netfn_lun, _, rq_sa, seq_lun, cmdid) = req[:6]
    header = bytes([rq_sa, (((netfn_lun >> 2) | 1) << 2) | (seq_lun & 3)])
    header += bytes([checksum(header)])
    body = bytes([rs_sa, (seq_lun & 0xfc) | (netfn_lun & 3), cmdid]) + data
    return header + body + bytes([checksum(body)])


class FakeBmc:
    """A BMC speaking RMCP+, implemented as socket replacement.

    The RAKP calculations follow IPMI v2.0, section 13.31.
    """

    GUID = bytes(range(0x40, 0x50))
    MANAGED_SID = 0x11223344

    def __init__(self, username='admin', password='secret',
                 suites=(1, 2, 3, 15, 16, 17), ipmi_2_0=True,
                 truncated_errors=False):
        self.username = username.encode()
        self.password = password.encode()
        self.suites = suites
        self.ipmi_2_0 = ipmi_2_0
        self.truncated_errors = truncated_errors
        self.rx = deque()
        self.keys = None
        self.suite = None
        self.console_sid = None
        self.inbound_seq = 0
        self.outbound_seq = 0
        self.commands = []

    # socket interface
    def connect(self, address):
        pass

    def settimeout(self, timeout):
        pass

    def recv(self, size):
        if not self.rx:
            raise TimeoutError()
        return self.rx.popleft()

    def send(self, pdu):
        if pdu[3] == 0x06:
            # ASF presence pong
            self.rx.append(b'\x06\x00\xff\x06'
                           + struct.pack('!IBBxB', 4542, 0x40, 0, 16)
                           + struct.pack('!IIBB6x', 4542, 0, 0x81, 0))
        elif pdu[4] == 0x00:
            self._handle_ipmi15(pdu[4:])
        else:
            self._handle_rmcpplus(pdu[4:])

    def _reply(self, payload_type, payload):
        if self.keys is not None:
            self.outbound_seq += 1
            pdu = pack_rmcpplus(payload_type, payload, self.console_sid,
                                self.outbound_seq, self.keys)
        else:
            pdu = pack_rmcpplus(payload_type, payload)
        self.rx.append(b'\x06\x00\xff\x07' + pdu)

    def _error(self, payload_type, tag, status):
        payload = struct.pack('<BBxxI', tag, status, self.console_sid)
        if self.truncated_errors:
            payload = payload[:7]
        self._reply(payload_type, payload)

    def _handle_ipmi15(self, pdu):
        req = pdu[10:]
        assert req[5] == 0x38  # Get Channel Authentication Capabilities
        self.commands.append(req[5])
        if self.ipmi_2_0:
            assert req[6] & 0x80, 'IPMI v2.0 extended data not requested'
            data = b'\x00\x01\x96\x04\x03\x00\x00\x00\x00'
        else:
            data = b'\x00\x01\x16\x04\x00\x00\x00\x00\x00'
        rsp = ipmb_response(req, data)
        self.rx.append(b'\x06\x00\xff\x07'
                       + struct.pack('!BIIB', 0, 0, 0, len(rsp)) + rsp)

    def _handle_rmcpplus(self, pdu):
        (payload_type, session_id, seq, payload) = \
            unpack_rmcpplus(pdu, self.keys)
        handler = {
            0x10: self._open_session,
            0x12: self._rakp1,
            0x14: self._rakp3,
            0x00: self._ipmi,
        }[payload_type]
        if payload_type == PAYLOAD_TYPE_IPMI:
            assert session_id == self.MANAGED_SID
            assert seq > self.inbound_seq
            self.inbound_seq = seq
        handler(payload)

    def _open_session(self, req):
        (tag, self.console_sid) = struct.unpack('<BxxxI', req[:8])
        algorithms = (req[12], req[20], req[28])
        for suite_id in self.suites:
            suite = CIPHER_SUITES[suite_id]
            if algorithms == (suite.authentication, suite.integrity,
                              suite.confidentiality):
                self.suite = suite
                break
        else:
            self._error(0x11, tag, 0x11)
            return
        self._reply(0x11, struct.pack('<BBBxII', tag, 0, 4, self.console_sid,
                                      self.MANAGED_SID) + req[8:])

    def _digest(self):
        return {1: hashlib.sha1, 3: hashlib.sha256}[self.suite.authentication]

    def _rakp1(self, req):
        (tag, sid, self.rm, role, ulen) = \
            struct.unpack('<BxxxI16sBxxB', req[:28])
        uname = req[28:28 + ulen]
        assert sid == self.MANAGED_SID
        if uname != self.username:
            self._error(0x13, tag, 0x0d)
            return
        self.role = bytes([role, ulen]) + uname
        self.rc = bytes(range(16))
        sid_m = struct.pack('<I', self.console_sid)
        sid_c = struct.pack('<I', self.MANAGED_SID)
        code = hmac.new(self.password, sid_m + sid_c + self.rm + self.rc
                        + self.GUID + self.role, self._digest()).digest()
        self._reply(0x13, struct.pack('<BBxxI', tag, 0, self.console_sid)
                    + self.rc + self.GUID + code)

    def _rakp3(self, req):
        (tag, status) = req[:2]
        if status != 0:
            return
        sid_m = struct.pack('<I', self.console_sid)
        sid_c = struct.pack('<I', self.MANAGED_SID)
        expected = hmac.new(self.password, self.rc + sid_m + self.role,
                            self._digest()).digest()
        assert req[8:] == expected
        sik = hmac.new(self.password, self.rm + self.rc + self.role,
                       self._digest()).digest()
        icv_len = {1: 12, 3: 16}[self.suite.authentication]
        icv = hmac.new(sik, self.rm + sid_c + self.GUID,
                       self._digest()).digest()[:icv_len]
        self._reply(0x15, struct.pack('<BBxxI', tag, 0, self.console_sid)
                    + icv)
        self.keys = SessionKeys(self.suite, sik)

    def _ipmi(self, req):
        cmdid = req[5]
        self.commands.append(cmdid)
        data = {
            0x01: b'\x00\x20\x01\x04\x00\x02\xbf\x7c\x2a\x00\x69\x09',
            0x3b: b'\x00\x04',
            0x3c: b'\x00',
        }[cmdid]
        self._reply(PAYLOAD_TYPE_IPMI, ipmb_response(req, data))


def create_ipmi(bmc, username='admin', password='secret', **kwargs):
    intf = RmcpPlus(keep_alive_interval=0, **kwargs)
    intf.open = lambda: None
    intf._sock = bmc
    ipmi = pyipmi.create_connection(intf)
    ipmi.session.set_session_type_rmcp('10.0.0.1', 623)
    ipmi.session.set_auth_type_user(username, password)
    ipmi.target = pyipmi.Target(0x20)
    return ipmi


class TestRmcpPlus:
    @pytest.mark.parametrize('suite', SUITE_PARAMS)
    def test_session(self, suite):
        bmc = FakeBmc()
        ipmi = create_ipmi(bmc, cipher_suite=suite)
        ipmi.open()
        assert bmc.suite.id == suite
        device_id = ipmi.get_device_id()
        assert device_id.device_id == 0x20
        assert device_id.manufacturer_id == 10876
        assert device_id.product_id == 2409
        ipmi.close()
        # Get Channel Auth Cap, Set Session Priv, Get Device ID, Close
        assert bmc.commands == [0x38, 0x3b, 0x01, 0x3c]
        assert ipmi.interface._keys is None

    @needs_aes
    @pytest.mark.parametrize('truncated', [False, True])
    def test_cipher_suite_fallback(self, truncated):
        bmc = FakeBmc(suites=(3,), truncated_errors=truncated)
        ipmi = create_ipmi(bmc)
        ipmi.open()
        assert bmc.suite.id == 3

    @needs_aes
    def test_explicit_cipher_suite_rejected(self):
        bmc = FakeBmc(suites=(3,))
        ipmi = create_ipmi(bmc, cipher_suite=17)
        with pytest.raises(MessageStatusCodeError) as e:
            ipmi.open()
        assert e.value.msc == 0x11

    def test_wrong_password(self):
        ipmi = create_ipmi(FakeBmc(), password='wrong', cipher_suite=2)
        with pytest.raises(AuthenticationError):
            ipmi.open()

    def test_wrong_user(self):
        ipmi = create_ipmi(FakeBmc(), username='nobody', cipher_suite=2)
        with pytest.raises(MessageStatusCodeError) as e:
            ipmi.open()
        assert e.value.msc == 0x0d

    def test_no_ipmi_2_0(self):
        ipmi = create_ipmi(FakeBmc(ipmi_2_0=False))
        with pytest.raises(NotSupportedError):
            ipmi.open()

    def test_aes_not_available(self, monkeypatch):
        monkeypatch.setattr('pyipmi.interfaces.rmcpplus.aes_available',
                            lambda: False)
        ipmi = create_ipmi(FakeBmc())
        with pytest.raises(NotSupportedError):
            ipmi.open()

    def test_aes_not_available_unencrypted_suite(self, monkeypatch):
        monkeypatch.setattr('pyipmi.interfaces.rmcpplus.aes_available',
                            lambda: False)
        bmc = FakeBmc()
        ipmi = create_ipmi(bmc, cipher_suite=2)
        ipmi.open()
        assert bmc.suite.id == 2

    def test_invalid_cipher_suite(self):
        with pytest.raises(NotSupportedError):
            RmcpPlus(cipher_suite=0)

    def test_create_interface(self):
        intf = pyipmi.interfaces.create_interface('rmcpplus', cipher_suite=3)
        assert isinstance(intf, RmcpPlus)
        assert intf.cipher_suites == (3,)

    def test_ipmitool_options(self):
        options = parse_interface_options('rmcpplus', 'cipher=17,kg=0102')
        assert options == {'cipher_suite': 17, 'kg': b'\x01\x02'}
