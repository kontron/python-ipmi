#!/usr/bin/env python

import collections
import threading
import time
import types

import pytest
from unittest.mock import patch

import pyipmi
from pyipmi.interfaces.aardvark import Aardvark
from pyipmi.interfaces.router import MessageRouter, encode_ipmb_response
from pyipmi.interfaces.ipmb import IpmbHeaderReq, encode_ipmb_msg

POLL_I2C_READ = 0x01


class FakeAardvarkDevice:
    """Simulates the Aardvark adapter, enabled as I2C slave.

    Messages written as master are passed to the responder, which returns
    a list of complete IPMB messages to receive as slave.
    """

    def __init__(self):
        self.responder = None
        self.slave_address = None
        self.written = []
        self.rx = collections.deque()
        self.lock = threading.Lock()
        self.closed = False

    def enable_i2c_slave(self, address):
        self.slave_address = address

    def i2c_master_write(self, i2c_addr, data):
        frame = bytes(((i2c_addr << 1),)) + bytes(data)
        self.written.append(frame)
        for rx_frame in (self.responder(frame) if self.responder else []):
            self.inject(rx_frame)

    def inject(self, frame):
        """Receive a complete IPMB message as slave."""
        # the adapter returns the slave address and the data without it
        with self.lock:
            self.rx.append((frame[0] >> 1, frame[1:]))

    def poll(self, timeout_ms):
        with self.lock:
            if self.rx:
                return [POLL_I2C_READ]
        time.sleep(timeout_ms / 1000)
        return []

    def i2c_slave_read(self):
        with self.lock:
            return self.rx.popleft()

    def close(self):
        self.closed = True


@pytest.fixture
def device():
    device = FakeAardvarkDevice()
    module = types.SimpleNamespace(open=lambda port, serial_number: device,
                                   POLL_I2C_READ=POLL_I2C_READ)
    with patch('pyipmi.interfaces.aardvark.pyaardvark', module):
        yield device


def test_open_close(device):
    intf = Aardvark(slave_address=0x24)
    intf.open()
    assert device.slave_address == 0x12
    intf.close()
    assert device.closed


def test_requester(device):
    device.responder = lambda frame: [
        encode_ipmb_response(IpmbHeaderReq(data=frame), b'\x00\x11')]
    intf = Aardvark(slave_address=0x20)
    intf.open()
    try:
        rsp = intf.send_and_receive_raw(pyipmi.Target(0x72), 0, 6, b'\x01')
    finally:
        intf.close()

    assert rsp == b'\x00\x11'
    header = IpmbHeaderReq(data=device.written[0])
    assert header.rs_sa == 0x72
    assert header.rq_sa == 0x20


def test_responder(device):
    router = MessageRouter()
    router.register_raw_handler(6, 1, lambda intf, hdr, data: b'\x00\x42')
    intf = Aardvark(slave_address=0x20, router=router)
    intf.open()
    try:
        # incoming Get Device ID request from 0x24
        header = IpmbHeaderReq()
        header.rs_sa = 0x20
        header.netfn = 6
        header.rs_lun = 0
        header.rq_sa = 0x24
        header.rq_seq = 5
        header.rq_lun = 0
        header.cmdid = 1
        device.inject(encode_ipmb_msg(header, None))

        deadline = time.monotonic() + 1.0
        while not device.written:
            assert time.monotonic() < deadline
            time.sleep(0.01)
    finally:
        intf.close()
        router.close()

    assert device.written[0] == encode_ipmb_response(header, b'\x00\x42')
