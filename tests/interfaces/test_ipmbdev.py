#!/usr/bin/env python

import socket
import threading

import pytest
from unittest.mock import patch

import pyipmi
from pyipmi.interfaces.ipmbdev import IpmbDev
from pyipmi.interfaces.router import MessageRouter, encode_ipmb_response
from pyipmi.interfaces.ipmb import IpmbHeaderReq, encode_ipmb_msg


@pytest.fixture
def driver():
    """Socket pair as /dev/ipmb-0: the test is the ipmb-dev-int side.

    Like the driver, a SEQPACKET socket returns one message per read.
    """
    intf_end, driver_end = socket.socketpair(type=socket.SOCK_SEQPACKET)
    driver_end.settimeout(1.0)
    with patch('pyipmi.interfaces.ipmbdev.os.open',
               return_value=intf_end.fileno()):
        yield driver_end
    driver_end.close()
    intf_end.detach()  # closed by the interface


def driver_read(driver):
    """Read a message the interface wrote, without the length byte."""
    data = driver.recv(256)
    assert data[0] == len(data) - 1
    return data[1:]


def driver_write(driver, frame):
    driver.sendall(bytes((len(frame),)) + frame)


def test_requester(driver):
    def respond():
        request = driver_read(driver)
        driver_write(driver, encode_ipmb_response(IpmbHeaderReq(data=request),
                                                  b'\x00\x11'))

    responder = threading.Thread(target=respond)
    responder.start()
    intf = IpmbDev(slave_address=0x20)
    intf.open()
    try:
        rsp = intf.send_and_receive_raw(pyipmi.Target(0x72), 0, 6, b'\x01')
    finally:
        intf.close()
        responder.join()

    assert rsp == b'\x00\x11'


def test_responder(driver):
    router = MessageRouter()
    router.register_raw_handler(6, 1, lambda intf, hdr, data: b'\x00\x42')
    intf = IpmbDev(slave_address=0x20, router=router)
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
        driver_write(driver, encode_ipmb_msg(header, None))

        assert driver_read(driver) == encode_ipmb_response(header,
                                                           b'\x00\x42')
    finally:
        intf.close()
        router.close()


def test_bad_length_is_ignored(driver):
    router = MessageRouter()
    intf = IpmbDev(slave_address=0x20, router=router)
    intf.open()
    try:
        driver.sendall(b'\x05\x01\x02')  # length byte doesn't match
        header = IpmbHeaderReq()
        header.rs_sa = 0x20
        header.netfn = 6
        header.rs_lun = 0
        header.rq_sa = 0x24
        header.rq_seq = 1
        header.rq_lun = 0
        header.cmdid = 1
        driver_write(driver, encode_ipmb_msg(header, None))

        # unhandled request: invalid command
        assert driver_read(driver) == encode_ipmb_response(header, b'\xc1')
    finally:
        intf.close()
        router.close()
