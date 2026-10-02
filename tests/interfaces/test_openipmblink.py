#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json

import pytest
from unittest.mock import patch

import pyipmi
import pyipmi.msgs.bmc
from pyipmi.errors import IpmiTimeoutError
from pyipmi.interfaces import create_interface
from pyipmi.interfaces.ipmb import IpmbHeaderReq, checksum
from pyipmi.interfaces.openipmblink import OpenIpmbLink, OpenIpmbLinkError


def build_rsp(req, data, seq_offset=0):
    """Build the IPMB response for a request frame."""
    hdr = bytes((req[3], (req[1] | 4) & 0xfc | req[4] & 3))
    body = bytes((req[0], ((req[4] >> 2) + seq_offset) % 64 << 2 | req[1] & 3,
                  req[5])) + bytes(data)
    return hdr + bytes((checksum(hdr),)) + body + bytes((checksum(body),))


class FakeBridge:
    """Simulates the bridge on the serial data port."""

    def __init__(self, version=3, responder=None):
        self.version = version
        self.responder = responder
        self.written = []
        self.out = bytearray()
        self.closed = False

    @property
    def in_waiting(self):
        return len(self.out)

    def _reply(self, packet):
        self.out += json.dumps(packet).encode() + b'\r\n'

    def write(self, data):
        for line in data.split(b'\n'):
            if not line:
                continue
            cmd = json.loads(line)
            self.written.append(cmd)
            if cmd['cmd'] == 'ping':
                self._reply({'rsp': 'ping', 'version': self.version,
                             'board': 'fake',
                             'buses': [{'addr': 0x22, 'dropped': 0}] * 2})
            elif cmd['cmd'] == 'set_addr':
                self._reply({'rsp': 'set_addr', 'status': 'ok'})
            elif cmd['cmd'] == 'send':
                req = bytes.fromhex(cmd['msg'])
                rx = self.responder(cmd['bus'], req) if self.responder else []
                status = 'ok'
                if rx is None:
                    status, rx = 'bus_error', []
                self._reply({'rsp': 'send', 'status': status})
                for bus, frame in rx:
                    self._reply({'evt': 'rx', 'bus': bus, 'ts': 1,
                                 'msg': frame.hex()})

    def read(self, size=1):
        data = bytes(self.out[:size])
        del self.out[:size]
        return data

    def close(self):
        self.closed = True


def open_intf(bridge, **kwargs):
    with patch('pyipmi.interfaces.openipmblink.serial') as serial_mock:
        serial_mock.Serial.return_value = bridge
        intf = OpenIpmbLink(**kwargs)
        intf.open()
    return intf


def test_create_interface():
    intf = create_interface('openipmblink', port='/dev/null', bus=1)
    assert isinstance(intf, OpenIpmbLink)
    assert intf.port == '/dev/null'
    assert intf.bus == 1


def test_open_sets_address():
    bridge = FakeBridge()
    intf = open_intf(bridge, slave_address=0x24, bus=1)
    assert bridge.written[0] == {'cmd': 'ping'}
    assert bridge.written[1] == {'cmd': 'set_addr', 'bus': 1, 'addr': 0x24}
    intf.close()
    assert bridge.closed


def test_open_wrong_version():
    with pytest.raises(OpenIpmbLinkError):
        open_intf(FakeBridge(version=2))


def test_send_and_receive_raw():
    def responder(bus, req):
        return [(bus, build_rsp(req, b'\x00\x11\x22'))]

    bridge = FakeBridge(responder=responder)
    intf = open_intf(bridge)
    target = pyipmi.Target(0x72)
    rsp = intf.send_and_receive_raw(target, 0, 6, b'\x01')
    assert rsp == b'\x00\x11\x22'

    send = bridge.written[-1]
    assert send['cmd'] == 'send'
    assert send['bus'] == 0
    req = bytes.fromhex(send['msg'])
    header = IpmbHeaderReq(data=req)
    assert header.rs_sa == 0x72
    assert header.rq_sa == 0x20
    assert header.netfn == 6
    assert header.cmdid == 1
    assert checksum(req[0:3]) == 0
    assert checksum(req[3:]) == 0


def test_send_and_receive_ignores_unrelated():
    def responder(bus, req):
        return [
            (1, build_rsp(req, b'\x00\xaa')),  # other bus
            (bus, build_rsp(req, b'\x00\xbb', seq_offset=1)),  # wrong seq
            (bus, b'\x20\x18'),  # short frame
            (bus, build_rsp(req, b'\x00\xcc')),
        ]

    intf = open_intf(FakeBridge(responder=responder))
    rsp = intf.send_and_receive_raw(pyipmi.Target(0x72), 0, 6, b'\x01')
    assert rsp == b'\x00\xcc'


def test_send_and_receive_message():
    def responder(bus, req):
        data = (b'\x00\x0c\x89\x00\x00\x02\x3d\x98'
                b'\x3a\x00\xbe\x14\x04\x00\x02\x00')
        return [(bus, build_rsp(req, data))]

    intf = open_intf(FakeBridge(responder=responder))
    req = pyipmi.msgs.bmc.GetDeviceIdReq()
    req.target = pyipmi.Target(0x72)
    rsp = intf.send_and_receive(req)
    assert rsp.completion_code == 0
    assert rsp.device_id == 0x0c
    assert rsp.manufacturer_id == 0x003a98


def test_send_retries_on_bus_error():
    calls = []

    def responder(bus, req):
        calls.append(req)
        if len(calls) == 1:
            return None
        return [(bus, build_rsp(req, b'\x00'))]

    intf = open_intf(FakeBridge(responder=responder))
    with patch('pyipmi.interfaces.openipmblink.time.sleep'):
        rsp = intf.send_and_receive_raw(pyipmi.Target(0x72), 0, 6, b'\x01')
    assert rsp == b'\x00'
    assert len(calls) == 2


def test_timeout():
    intf = open_intf(FakeBridge())
    intf.timeout = 0.01
    with patch('pyipmi.interfaces.openipmblink.time.sleep'):
        with pytest.raises(IpmiTimeoutError):
            intf.send_and_receive_raw(pyipmi.Target(0x72), 0, 6, b'\x01')
