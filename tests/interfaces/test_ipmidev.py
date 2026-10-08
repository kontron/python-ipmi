#!/usr/bin/env python

import ctypes
import os
import platform

import pytest
from unittest.mock import patch

import pyipmi
from pyipmi.errors import IpmiTimeoutError
from pyipmi.interfaces import create_interface
from pyipmi.interfaces import ipmidev
from pyipmi.interfaces.ipmidev import (IpmiDev, IpmiIpmbAddr, IpmiRecv,
                                       IpmiReq, IpmiSystemInterfaceAddr)

DEVICE_ID_RSP = (b'\x00\x0c\x89\x00\x00\x02\x3d\x98'
                 b'\x3a\x00\xbe\x14\x04\x00\x02\x00')


class FakeDriver:
    """Emulates the ioctls of /dev/ipmi0.

    `responder` gets the address structure, netfn, cmd and data of a request
    and returns a list of (recv_type, msgid offset, netfn, cmd, data) tuples
    to queue as received messages.
    """

    def __init__(self, responder):
        self.responder = responder
        self.requests = []
        self.queue = []

    def ioctl(self, fd, request, arg):
        if request == ipmidev.IPMICTL_SEND_COMMAND:
            assert isinstance(arg, IpmiReq)
            addr_type = ctypes.c_int.from_address(arg.addr).value
            if addr_type == ipmidev.IPMI_SYSTEM_INTERFACE_ADDR_TYPE:
                assert arg.addr_len == ctypes.sizeof(IpmiSystemInterfaceAddr)
                addr_cls = IpmiSystemInterfaceAddr
            else:
                assert arg.addr_len == ctypes.sizeof(IpmiIpmbAddr)
                addr_cls = IpmiIpmbAddr
            # copy the address, the memory is owned by the interface and is
            # freed after the request was sent
            addr = addr_cls.from_buffer_copy(
                ctypes.string_at(arg.addr, arg.addr_len))
            data = ctypes.string_at(arg.msg.data, arg.msg.data_len)
            req = (addr, arg.msg.netfn, arg.msg.cmd, data)
            self.requests.append(req)
            for recv_type, msgid_offset, netfn, cmd, rsp in \
                    self.responder(*req):
                self.queue.append((recv_type, arg.msgid + msgid_offset,
                                   netfn, cmd, rsp))
        elif request == ipmidev.IPMICTL_RECEIVE_MSG_TRUNC:
            assert isinstance(arg, IpmiRecv)
            recv_type, msgid, netfn, cmd, rsp = self.queue.pop(0)
            arg.recv_type = recv_type
            arg.msgid = msgid
            arg.msg.netfn = netfn
            arg.msg.cmd = cmd
            assert arg.msg.data_len >= len(rsp)
            ctypes.memmove(arg.msg.data, rsp, len(rsp))
            arg.msg.data_len = len(rsp)
        else:
            raise AssertionError('unexpected ioctl %x' % request)
        return 0

    def select(self, rlist, wlist, xlist, timeout):
        return (rlist if self.queue else []), [], []


def device_id_responder(addr, netfn, cmd, data):
    return [(ipmidev.IPMI_RESPONSE_RECV_TYPE, 0, netfn + 1, cmd,
             DEVICE_ID_RSP)]


@pytest.fixture
def driver_factory():
    r, w = os.pipe()
    os.close(w)

    def create(responder=device_id_responder):
        driver = FakeDriver(responder)
        patches = [
            patch('pyipmi.interfaces.ipmidev.os.open', return_value=r),
            patch('pyipmi.interfaces.ipmidev.fcntl.ioctl', new=driver.ioctl),
            patch('pyipmi.interfaces.ipmidev.select.select',
                  new=driver.select),
        ]
        for p in patches:
            p.start()
            active.append(p)
        return driver

    active = []
    yield create
    for p in active:
        p.stop()


def open_intf(**kwargs):
    intf = IpmiDev(**kwargs)
    intf.open()
    return intf


def test_create_interface():
    intf = create_interface('ipmidev', port='/dev/ipmi1')
    assert isinstance(intf, IpmiDev)
    assert intf.port == '/dev/ipmi1'


@pytest.mark.skipif(platform.machine() != 'x86_64', reason='x86_64 only')
def test_ioctl_numbers():
    assert ipmidev.IPMICTL_SEND_COMMAND == 0x8028690d
    assert ipmidev.IPMICTL_RECEIVE_MSG_TRUNC == 0xc030690b


def test_system_interface(driver_factory):
    driver = driver_factory()
    intf = open_intf()
    try:
        rsp = intf.send_and_receive_raw(pyipmi.Target(0x20), 0, 6, b'\x01')
    finally:
        intf.close()

    assert rsp == DEVICE_ID_RSP
    addr, netfn, cmd, data = driver.requests[0]
    assert isinstance(addr, IpmiSystemInterfaceAddr)
    assert addr.channel == ipmidev.IPMI_BMC_CHANNEL
    assert addr.lun == 0
    assert (netfn, cmd, data) == (6, 1, b'')


def test_system_interface_without_target_address(driver_factory):
    driver = driver_factory()
    intf = open_intf()
    try:
        intf.send_and_receive_raw(pyipmi.Target(), 2, 0x2e, b'\x01\x02\x03')
    finally:
        intf.close()

    addr, netfn, cmd, data = driver.requests[0]
    assert isinstance(addr, IpmiSystemInterfaceAddr)
    assert addr.lun == 2
    assert (netfn, cmd, data) == (0x2e, 1, b'\x02\x03')


def test_ipmb_target(driver_factory):
    driver = driver_factory()
    intf = open_intf()
    try:
        intf.send_and_receive_raw(pyipmi.Target(0x72), 0, 6, b'\x01')
    finally:
        intf.close()

    addr = driver.requests[0][0]
    assert isinstance(addr, IpmiIpmbAddr)
    assert addr.addr_type == ipmidev.IPMI_IPMB_ADDR_TYPE
    assert (addr.channel, addr.slave_addr) == (0, 0x72)


def test_routing_one_bridge(driver_factory):
    driver = driver_factory()
    intf = open_intf()
    target = pyipmi.Target(0x72, routing=[(0x20, 0x20, 7), (0x20, 0x72, None)])
    try:
        intf.send_and_receive_raw(target, 0, 6, b'\x01')
    finally:
        intf.close()

    addr = driver.requests[0][0]
    assert isinstance(addr, IpmiIpmbAddr)
    assert (addr.channel, addr.slave_addr) == (7, 0x72)


def test_routing_multiple_bridges_not_supported(driver_factory):
    driver_factory()
    intf = open_intf()
    target = pyipmi.Target(0x72, routing=[(0x20, 0x20, 0), (0x20, 0x82, 7),
                                          (0x20, 0x72, None)])
    try:
        with pytest.raises(RuntimeError):
            intf.send_and_receive_raw(target, 0, 6, b'\x01')
    finally:
        intf.close()


def test_drops_unrelated_messages(driver_factory):
    def responder(addr, netfn, cmd, data):
        return [
            (ipmidev.IPMI_RESPONSE_RECV_TYPE, -1, netfn + 1, cmd, b'\xff'),
            (2, 0, 0, 0, b'\x01\x02'),  # async event
            (ipmidev.IPMI_RESPONSE_RECV_TYPE, 0, netfn + 1, cmd,
             DEVICE_ID_RSP),
        ]

    driver_factory(responder)
    intf = open_intf()
    try:
        rsp = intf.send_and_receive_raw(pyipmi.Target(0x20), 0, 6, b'\x01')
    finally:
        intf.close()

    assert rsp == DEVICE_ID_RSP


def test_timeout(driver_factory):
    driver_factory(lambda addr, netfn, cmd, data: [])
    intf = open_intf(timeout=0.1)
    try:
        with pytest.raises(IpmiTimeoutError):
            intf.send_and_receive_raw(pyipmi.Target(0x20), 0, 6, b'\x01')
    finally:
        intf.close()


def test_get_device_id(driver_factory):
    driver_factory()
    intf = open_intf()
    ipmi = pyipmi.create_connection(intf)
    ipmi.target = pyipmi.Target(0x20)
    try:
        device_id = ipmi.get_device_id()
    finally:
        intf.close()

    assert device_id.device_id == 0x0c


def platform_event_responder(addr, netfn, cmd, data):
    return [(ipmidev.IPMI_RESPONSE_RECV_TYPE, 0, netfn + 1, cmd, b'\x00')]


@pytest.mark.parametrize('target, system_interface', [
    (pyipmi.Target(), True),
    (pyipmi.Target(0x20), True),
    (pyipmi.Target(0x72), False),
    (pyipmi.Target(0x72, routing=[(0x20, 0x20, 7), (0x20, 0x72, None)]),
     False),
])
def test_is_system_interface(target, system_interface):
    assert IpmiDev().is_system_interface(target) is system_interface


@pytest.mark.parametrize('target, data', [
    # the system interface needs the Generator ID 0x41
    (pyipmi.Target(0x20), b'\x41\x04\xf2\x01\x6f\x00'),
    # bridged to IPMB, the Generator ID is the requester address
    (pyipmi.Target(0x72), b'\x04\xf2\x01\x6f\x00'),
])
def test_send_platform_event(driver_factory, target, data):
    driver = driver_factory(platform_event_responder)
    ipmi = pyipmi.create_connection(IpmiDev())
    ipmi.target = target
    ipmi.interface.open()
    try:
        ipmi.send_platform_event(0xf2, 1, 0x6f)
    finally:
        ipmi.interface.close()

    _, netfn, cmd, req_data = driver.requests[0]
    assert (netfn, cmd) == (0x04, 0x02)
    assert req_data == data
