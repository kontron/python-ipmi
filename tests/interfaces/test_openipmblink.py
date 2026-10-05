#!/usr/bin/env python

import json
import threading
import time

import pytest
from unittest.mock import patch

import pyipmi
import pyipmi.msgs.bmc
from pyipmi.errors import IpmiTimeoutError
from pyipmi.interfaces import create_interface
from pyipmi.interfaces.ipmb import IpmbHeaderReq, checksum
from pyipmi.interfaces.openipmblink import (OpenIpmbLink, OpenIpmbLinkDevice,
                                            OpenIpmbLinkError)
from pyipmi.interfaces.router import MessageRouter
from pyipmi.msgs import constants

DEVICE_ID_RSP = (b'\x00\x0c\x89\x00\x00\x02\x3d\x98'
                 b'\x3a\x00\xbe\x14\x04\x00\x02\x00')


def build_rsp(req, data, seq_offset=0):
    """Build the IPMB response for a request frame."""
    hdr = bytes((req[3], (req[1] | 4) & 0xfc | req[4] & 3))
    body = bytes((req[0], ((req[4] >> 2) + seq_offset) % 64 << 2 | req[1] & 3,
                  req[5])) + bytes(data)
    return hdr + bytes((checksum(hdr),)) + body + bytes((checksum(body),))


class FakeBridge:
    """Simulates the bridge on the serial data port.

    Both buses are wired together like in the bridge self-test: a message
    sent on one bus is received on the other bus if it is addressed to that
    bus. Other messages are passed to the responder, which returns a list of
    (bus, frame) to receive or None for a bus error.
    """

    def __init__(self, version=3, responder=None):
        self.version = version
        self.responder = responder
        self.addrs = [0x22, 0x22]
        self.written = []
        self.out = bytearray()
        self.lock = threading.Lock()
        self.closed = False

    @property
    def in_waiting(self):
        with self.lock:
            return len(self.out)

    def _reply(self, packet):
        with self.lock:
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
                             'buses': [{'addr': a, 'dropped': 0}
                                       for a in self.addrs]})
            elif cmd['cmd'] == 'set_addr':
                self.addrs[cmd['bus']] = cmd['addr']
                self._reply({'rsp': 'set_addr', 'status': 'ok'})
            elif cmd['cmd'] == 'send':
                self._send(cmd['bus'], bytes.fromhex(cmd['msg']))

    def _send(self, bus, frame):
        other = 1 - bus
        if frame[0] == self.addrs[other]:
            rx = [(other, frame)]
        elif self.responder:
            rx = self.responder(bus, frame)
        else:
            rx = []
        status = 'ok'
        if rx is None:
            status, rx = 'bus_error', []
        self._reply({'rsp': 'send', 'status': status})
        for rx_bus, rx_frame in rx:
            self._reply({'evt': 'rx', 'bus': rx_bus, 'ts': 1,
                         'msg': rx_frame.hex()})

    def read(self, size=1):
        with self.lock:
            data = bytes(self.out[:size])
            del self.out[:size]
        if not data:
            time.sleep(0.001)
        return data

    def close(self):
        self.closed = True


@pytest.fixture
def bridge():
    bridge = FakeBridge()
    with patch('pyipmi.interfaces.openipmblink.serial') as serial_mock:
        serial_mock.serial_for_url.return_value = bridge
        yield bridge
    assert OpenIpmbLinkDevice._devices == {}


@pytest.fixture
def interfaces():
    opened = []

    def open_intf(**kwargs):
        intf = OpenIpmbLink(**kwargs)
        intf.open()
        opened.append(intf)
        return intf

    yield open_intf
    for intf in opened:
        intf.close()


def test_create_interface(bridge):
    intf = create_interface('openipmblink', port='/dev/null', bus=1)
    assert isinstance(intf, OpenIpmbLink)
    assert intf.port == '/dev/null'
    assert intf.bus == 1


def test_open_sets_address(bridge, interfaces):
    interfaces(slave_address=0x24, bus=1)
    assert bridge.written[0] == {'cmd': 'ping'}
    assert bridge.written[1] == {'cmd': 'set_addr', 'bus': 1, 'addr': 0x24}


def test_close(bridge):
    intf = OpenIpmbLink()
    intf.open()
    intf.close()
    assert bridge.closed


def test_open_wrong_version(bridge):
    bridge.version = 2
    with pytest.raises(OpenIpmbLinkError):
        OpenIpmbLink().open()
    assert bridge.closed


def test_buses_share_device(bridge, interfaces):
    intf0 = interfaces(bus=0)
    intf1 = interfaces(bus=1)
    assert intf0._device is intf1._device
    assert bridge.written.count({'cmd': 'ping'}) == 1


def test_bus_in_use(bridge, interfaces):
    interfaces(bus=0)
    with pytest.raises(OpenIpmbLinkError):
        OpenIpmbLink(bus=0).open()


def test_send_and_receive_raw(bridge, interfaces):
    bridge.responder = lambda bus, req: [(bus, build_rsp(req, b'\x00\x11'))]
    intf = interfaces()
    rsp = intf.send_and_receive_raw(pyipmi.Target(0x72), 0, 6, b'\x01')
    assert rsp == b'\x00\x11'

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


def test_send_and_receive_ignores_unrelated(bridge, interfaces):
    def responder(bus, req):
        bad_checksum = bytearray(build_rsp(req, b'\x00\xdd'))
        bad_checksum[-1] ^= 1
        return [
            (1, build_rsp(req, b'\x00\xaa')),  # other bus
            (bus, build_rsp(req, b'\x00\xbb', seq_offset=1)),  # wrong seq
            (bus, b'\x20\x18'),  # short frame
            (bus, bytes(bad_checksum)),
            (bus, build_rsp(req, b'\x00\xcc')),
        ]

    bridge.responder = responder
    intf = interfaces()
    rsp = intf.send_and_receive_raw(pyipmi.Target(0x72), 0, 6, b'\x01')
    assert rsp == b'\x00\xcc'


def test_send_and_receive_message(bridge, interfaces):
    bridge.responder = lambda bus, req: [(bus, build_rsp(req, DEVICE_ID_RSP))]
    intf = interfaces()
    req = pyipmi.msgs.bmc.GetDeviceIdReq()
    req.target = pyipmi.Target(0x72)
    rsp = intf.send_and_receive(req)
    assert rsp.completion_code == 0
    assert rsp.device_id == 0x0c
    assert rsp.manufacturer_id == 0x003a98


def test_send_retries_on_bus_error(bridge, interfaces):
    calls = []

    def responder(bus, req):
        calls.append(req)
        if len(calls) == 1:
            return None
        return [(bus, build_rsp(req, b'\x00'))]

    bridge.responder = responder
    intf = interfaces()
    with patch('pyipmi.interfaces.ipmb.time.sleep'):
        rsp = intf.send_and_receive_raw(pyipmi.Target(0x72), 0, 6, b'\x01')
    assert rsp == b'\x00'
    assert len(calls) == 2


def test_timeout(bridge, interfaces):
    intf = interfaces()
    intf.timeout = 0.01
    with patch('pyipmi.interfaces.ipmb.time.sleep'):
        with pytest.raises(IpmiTimeoutError):
            intf.send_and_receive_raw(pyipmi.Target(0x72), 0, 6, b'\x01')


def test_incoming_request_ignored_by_default(bridge, interfaces):
    interfaces(slave_address=0x20, bus=0)
    requester = interfaces(slave_address=0x24, bus=1)
    requester.timeout = 0.05
    with patch('pyipmi.interfaces.ipmb.time.sleep'):
        with pytest.raises(IpmiTimeoutError):
            requester.send_and_receive_raw(pyipmi.Target(0x20), 0, 6,
                                           b'\x01')


def test_responder_raw_handler(bridge, interfaces):
    """Self-test setup: bus 1 sends a request, bus 0 answers it."""
    requests = []

    def handler(interface, header, data):
        requests.append((interface, header, data))
        return b'\x00' + data

    router = MessageRouter()
    router.register_raw_handler(0x30, 0x42, handler)
    responder = interfaces(slave_address=0x20, bus=0, router=router)
    requester = interfaces(slave_address=0x24, bus=1)

    rsp = requester.send_and_receive_raw(pyipmi.Target(0x20), 0, 0x30,
                                         b'\x42\x01\x02')
    assert rsp == b'\x00\x01\x02'

    interface, header, data = requests[0]
    assert interface is responder
    assert header.rq_sa == 0x24
    assert header.rs_sa == 0x20
    assert data == b'\x01\x02'
    router.close()


def test_responder_message_handler(bridge, interfaces):
    def handler(req):
        assert isinstance(req, pyipmi.msgs.bmc.GetDeviceIdReq)
        rsp = pyipmi.msgs.bmc.GetDeviceIdRsp()
        pyipmi.msgs.decode_message(rsp, DEVICE_ID_RSP)
        return rsp

    router = MessageRouter()
    router.register_handler(constants.NETFN_APP, constants.CMDID_GET_DEVICE_ID,
                            handler)
    interfaces(slave_address=0x20, bus=0, router=router)
    requester = interfaces(slave_address=0x24, bus=1)

    req = pyipmi.msgs.bmc.GetDeviceIdReq()
    req.target = pyipmi.Target(0x20)
    rsp = requester.send_and_receive(req)
    assert rsp.device_id == 0x0c
    assert rsp.manufacturer_id == 0x003a98
    router.close()


def test_responder_unhandled_request(bridge, interfaces):
    router = MessageRouter()
    interfaces(slave_address=0x20, bus=0, router=router)
    requester = interfaces(slave_address=0x24, bus=1)

    rsp = requester.send_and_receive_raw(pyipmi.Target(0x20), 0, 6, b'\x01')
    assert rsp == bytes((constants.CC_INV_CMD,))
    router.close()


def test_responder_handler_error(bridge, interfaces):
    def handler(interface, header, data):
        raise ValueError('broken handler')

    router = MessageRouter()
    router.register_raw_handler(6, 1, handler)
    interfaces(slave_address=0x20, bus=0, router=router)
    requester = interfaces(slave_address=0x24, bus=1)

    rsp = requester.send_and_receive_raw(pyipmi.Target(0x20), 0, 6, b'\x01')
    assert rsp == bytes((constants.CC_UNSPECIFIED_ERROR,))
    router.close()


def test_handler_forwards_request(bridge, interfaces):
    """A handler can send a request itself while handling one."""
    bridge.responder = lambda bus, req: [(bus, build_rsp(req, b'\x00\x99'))]
    router = MessageRouter()

    def handler(interface, header, data):
        return interface.send_and_receive_raw(pyipmi.Target(0x72), 0, 6,
                                              b'\x01')

    router.register_raw_handler(0x30, 0x01, handler)
    interfaces(slave_address=0x20, bus=0, router=router)
    requester = interfaces(slave_address=0x24, bus=1)
    requester.timeout = 1.0

    rsp = requester.send_and_receive_raw(pyipmi.Target(0x20), 0, 0x30,
                                         b'\x01')
    assert rsp == b'\x00\x99'
    router.close()
