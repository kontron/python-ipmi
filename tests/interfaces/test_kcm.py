#!/usr/bin/env python

import struct
import threading
import time

import pytest
from unittest.mock import patch

import pyipmi
import pyipmi.msgs.bmc
from pyipmi.errors import IpmiTimeoutError
from pyipmi.interfaces import create_interface
from pyipmi.interfaces.kcm import (Kcm, KcmDevice, KcmError, crc8,
                                   decode_frame, encode_frame)
from pyipmi.interfaces.ipmb import IpmbHeaderReq, checksum
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


class FakeKcm:
    """Simulates the KCM on the serial port.

    Both channels are wired together: a message sent on one channel is
    received on the other channel if it is addressed to that channel. Other
    messages are passed to the responder, which returns a list of
    (channel, frame) to receive or None for a NACK.
    """

    def __init__(self, version=0x0106, responder=None):
        self.version = version
        self.responder = responder
        self.addrs = [0x22, 0x22]
        self.configure_success = 1
        self.written = []
        self.out = bytearray()
        self.lock = threading.Lock()
        self.closed = False
        self.evt_seq = 0

    @property
    def in_waiting(self):
        with self.lock:
            return len(self.out)

    def _reply(self, cmd, seq, data):
        with self.lock:
            self.out += encode_frame(cmd, struct.pack('<H', seq) + data)

    def write(self, data):
        assert data[0] == 0x02 and data[-1] == 0x03
        cmd, payload = decode_frame(data[1:-1])
        (seq,) = struct.unpack_from('<H', payload)
        data = payload[2:]
        self.written.append((cmd, data))
        if cmd == 0:
            info = struct.pack('<H', self.version)
            for chan, addr in enumerate(self.addrs):
                info += struct.pack('<BBI', chan, addr, 100000)
            self._reply(4, seq, info)
        elif cmd == 2:
            chan, addr, _ = struct.unpack('<BBI', data)
            if self.configure_success:
                self.addrs[chan] = addr
            self._reply(5, seq, bytes((self.configure_success, 0)))
        elif cmd == 1:
            self._send(seq, data[0], data[1:])

    def _send(self, seq, chan, frame):
        other = 1 - chan
        if frame[0] == self.addrs[other]:
            rx = [(other, frame)]
        elif self.responder:
            rx = self.responder(chan, frame)
        else:
            rx = []
        if rx is None:
            self._reply(5, seq, b'\x00\x01')  # NACK, error code of firmware 1.6
            return
        self._reply(5, seq, b'\x01\x00')
        for rx_chan, rx_frame in rx:
            self.evt_seq += 1
            self._reply(6, self.evt_seq, bytes((rx_chan,)) + rx_frame)

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
def kcm():
    kcm = FakeKcm()
    with patch('pyipmi.interfaces.kcm.serial') as serial_mock:
        serial_mock.serial_for_url.return_value = kcm
        yield kcm
    assert KcmDevice._devices == {}


@pytest.fixture
def interfaces():
    opened = []

    def open_intf(**kwargs):
        intf = Kcm(**kwargs)
        intf.open()
        opened.append(intf)
        return intf

    yield open_intf
    for intf in opened:
        intf.close()


def test_crc8():
    # polynomial 0x97, init 0xff, no reflection, no final XOR
    assert crc8(b'') == 0xff
    assert crc8(b'\x00') == 0x3c
    assert crc8(b'123456789') == 0x64


# frames captured from a KCM with firmware 1.6
@pytest.mark.parametrize('cmd, payload, frame', [
    # Get Bridge Info
    (0, '0100', b'00010054'),
    (4, '0100 0601 0020a0860100 0121a0860100',
     b'04010006010020A08601000121A08601002F'),
    # Configure I2C Channel 0, address 0x20, 100 kHz and its status
    (2, '3412 00 20 a0860100', b'0234120020A086010032'),
    (5, '3412 01 00', b'053412010033'),
    # Send Message, Get Device ID to the absent 0xee, and its error status
    (1, '5634 00 ee18fa200401db', b'01563400EE18FA200401DB4C'),
    (5, '5634 00 01', b'055634000155'),
])
def test_captured_frames(cmd, payload, frame):
    payload = bytes.fromhex(payload)
    assert decode_frame(frame) == (cmd, payload)
    assert encode_frame(cmd, payload) == b'\x02' + frame + b'\x03'


def test_encode_decode_frame():
    frame = encode_frame(1, b'\x34\x12\x00\xab')
    assert frame[0] == 0x02
    assert frame[-1] == 0x03
    assert frame[1:-1] == frame[1:-1].upper()
    assert decode_frame(frame[1:-1]) == (1, b'\x34\x12\x00\xab')
    # both cases are accepted
    assert decode_frame(frame[1:-1].lower()) == (1, b'\x34\x12\x00\xab')


@pytest.mark.parametrize('body', [b'', b'zz', b'0102', b'010203'])
def test_decode_invalid_frame(body):
    assert decode_frame(body) is None


def test_create_interface(kcm):
    intf = create_interface('kcm', port='/dev/null', channel=1)
    assert isinstance(intf, Kcm)
    assert intf.port == '/dev/null'
    assert intf.channel == 1


def test_open_configures_channel(kcm, interfaces):
    interfaces(slave_address=0x24, channel=1)
    assert kcm.written[0] == (0, b'')
    assert kcm.written[1] == (2, struct.pack('<BBI', 1, 0x24, 100000))


def test_close(kcm):
    intf = Kcm()
    intf.open()
    intf.close()
    assert kcm.closed


def test_open_old_firmware(kcm):
    kcm.version = 0x0105
    with pytest.raises(KcmError):
        Kcm().open()
    assert kcm.closed


def test_channels_share_device(kcm, interfaces):
    intf0 = interfaces(channel=0)
    intf1 = interfaces(channel=1)
    assert intf0._device is intf1._device
    assert [cmd for cmd, _ in kcm.written].count(0) == 1


def test_channel_in_use(kcm, interfaces):
    intf = interfaces(slave_address=0x24, channel=0)
    with pytest.raises(KcmError):
        Kcm(slave_address=0x26, channel=0).open()
    assert kcm.addrs[0] == 0x24
    assert intf._device.has_listener(0)


def test_open_configure_fails(kcm, interfaces):
    kcm.configure_success = 0
    with pytest.raises(KcmError):
        Kcm(channel=0).open()
    assert kcm.closed
    # the channel is free again
    kcm.configure_success = 1
    interfaces(channel=0)


def test_frame_too_long(kcm, interfaces):
    intf = interfaces()
    with pytest.raises(KcmError, match='too long'):
        intf.send_frame(bytes(123))


def test_receive_split_and_garbage(kcm):
    """Frames are found in a stream with garbage and restarted frames."""
    device = KcmDevice('/dev/null')
    device._ser = kcm
    frame = encode_frame(6, b'\x01\x00\x00\xaa')
    kcm.out += b'xy\x02' + b'0102' + frame + b'\x02zz\x03' + frame[:5]
    assert device._read_frame() == (6, b'\x01\x00\x00\xaa')
    # the invalid frame is skipped, the next one is not complete yet
    assert device._read_frame() is None
    kcm.out += frame[5:]
    assert device._read_frame() == (6, b'\x01\x00\x00\xaa')


def test_send_and_receive_raw(kcm, interfaces):
    kcm.responder = lambda chan, req: [(chan, build_rsp(req, b'\x00\x11'))]
    intf = interfaces()
    rsp = intf.send_and_receive_raw(pyipmi.Target(0x72), 0, 6, b'\x01')
    assert rsp == b'\x00\x11'

    cmd, data = kcm.written[-1]
    assert cmd == 1
    assert data[0] == 0  # channel
    req = data[1:]
    header = IpmbHeaderReq(data=req)
    assert header.rs_sa == 0x72
    assert header.rq_sa == 0x20
    assert header.netfn == 6
    assert header.cmdid == 1
    assert checksum(req[0:3]) == 0
    assert checksum(req[3:]) == 0


def test_send_and_receive_ignores_unrelated(kcm, interfaces):
    def responder(chan, req):
        bad_checksum = bytearray(build_rsp(req, b'\x00\xdd'))
        bad_checksum[-1] ^= 1
        return [
            (1, build_rsp(req, b'\x00\xaa')),  # other channel
            (chan, build_rsp(req, b'\x00\xbb', seq_offset=1)),  # wrong seq
            (chan, b'\x20\x18'),  # short frame
            (chan, bytes(bad_checksum)),
            (chan, build_rsp(req, b'\x00\xcc')),
        ]

    kcm.responder = responder
    intf = interfaces()
    rsp = intf.send_and_receive_raw(pyipmi.Target(0x72), 0, 6, b'\x01')
    assert rsp == b'\x00\xcc'


def test_send_and_receive_message(kcm, interfaces):
    kcm.responder = lambda chan, req: [(chan, build_rsp(req, DEVICE_ID_RSP))]
    intf = interfaces()
    req = pyipmi.msgs.bmc.GetDeviceIdReq()
    req.target = pyipmi.Target(0x72)
    rsp = intf.send_and_receive(req)
    assert rsp.completion_code == 0
    assert rsp.device_id == 0x0c
    assert rsp.manufacturer_id == 0x003a98


def test_send_retries_on_nack(kcm, interfaces):
    calls = []

    def responder(chan, req):
        calls.append(req)
        if len(calls) == 1:
            return None
        return [(chan, build_rsp(req, b'\x00'))]

    kcm.responder = responder
    intf = interfaces()
    with patch('pyipmi.interfaces.ipmb.time.sleep'):
        rsp = intf.send_and_receive_raw(pyipmi.Target(0x72), 0, 6, b'\x01')
    assert rsp == b'\x00'
    assert len(calls) == 2


def test_timeout(kcm, interfaces):
    intf = interfaces()
    intf.timeout = 0.01
    with patch('pyipmi.interfaces.ipmb.time.sleep'):
        with pytest.raises(IpmiTimeoutError):
            intf.send_and_receive_raw(pyipmi.Target(0x72), 0, 6, b'\x01')


def test_responder_message_handler(kcm, interfaces):
    """Channel 1 sends a request, channel 0 answers it."""
    def handler(req):
        assert isinstance(req, pyipmi.msgs.bmc.GetDeviceIdReq)
        rsp = pyipmi.msgs.bmc.GetDeviceIdRsp()
        pyipmi.msgs.decode_message(rsp, DEVICE_ID_RSP)
        return rsp

    router = MessageRouter()
    router.register_handler(constants.NETFN_APP, constants.CMDID_GET_DEVICE_ID,
                            handler)
    interfaces(slave_address=0x20, channel=0, router=router)
    requester = interfaces(slave_address=0x24, channel=1)

    req = pyipmi.msgs.bmc.GetDeviceIdReq()
    req.target = pyipmi.Target(0x20)
    rsp = requester.send_and_receive(req)
    assert rsp.device_id == 0x0c
    assert rsp.manufacturer_id == 0x003a98
    router.close()
