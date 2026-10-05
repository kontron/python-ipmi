#!/usr/bin/env python

import logging

import pytest

import pyipmi
import pyipmi.msgs.bmc
from pyipmi.interfaces import INTERFACES
from pyipmi.interfaces.base import Interface
from pyipmi.interfaces.ipmb import IpmbInterface, IpmbHeaderReq
from pyipmi.interfaces.router import MessageRouter, encode_ipmb_response
from pyipmi.interfaces.aardvark import Aardvark
from pyipmi.interfaces.ipmbdev import IpmbDev
from pyipmi.interfaces.openipmblink import OpenIpmbLink


@pytest.mark.parametrize('intf', INTERFACES)
def test_interfaces_use_base_class(intf):
    assert issubclass(intf, Interface)
    assert intf.NAME is not None


@pytest.mark.parametrize('intf', [Aardvark, IpmbDev, OpenIpmbLink])
def test_ipmb_interfaces_use_ipmb_base_class(intf):
    assert issubclass(intf, IpmbInterface)


def test_not_implemented():
    intf = Interface()
    with pytest.raises(NotImplementedError):
        intf.send_and_receive_raw(pyipmi.Target(0x20), 0, 6, b'\x01')
    with pytest.raises(NotImplementedError):
        intf.is_ipmc_accessible(pyipmi.Target(0x20))


class RawStub(Interface):
    NAME = 'stub'

    def send_and_receive_raw(self, target, lun, netfn, raw_bytes):
        self.request = (target, lun, netfn, raw_bytes)
        return (b'\x00\x0c\x89\x00\x00\x02\x3d\x98'
                b'\x3a\x00\xbe\x14\x04\x00\x02\x00')


def test_send_and_receive_uses_raw():
    intf = RawStub()
    req = pyipmi.msgs.bmc.GetDeviceIdReq()
    req.target = pyipmi.Target(0x72)
    rsp = intf.send_and_receive(req)

    assert intf.request == (req.target, 0, 6, b'\x01')
    assert rsp.completion_code == 0
    assert rsp.device_id == 0x0c


class IpmbStub(IpmbInterface):
    """Answers each request with cc 0x00 and data 0xaa."""

    NAME = 'ipmbstub'

    def send_frame(self, frame):
        self.header = IpmbHeaderReq(data=frame)
        self.raw_bytes = frame[6:-1]
        self._receive_frame(encode_ipmb_response(self.header, b'\x00\xaa'))


def test_ipmb_send_and_receive_raw():
    intf = IpmbStub(slave_address=0x20)
    rsp = intf.send_and_receive_raw(pyipmi.Target(0x72), 0, 6, b'\x01\x02')

    assert rsp == b'\x00\xaa'
    assert intf.header.rs_sa == 0x72
    assert intf.header.rq_sa == 0x20
    assert intf.header.netfn == 6
    assert intf.header.cmdid == 1
    assert intf.header.rq_seq == 1
    assert intf.raw_bytes == b'\x02'


def test_ipmb_rx_logged_by_interface_module(caplog):
    intf = IpmbStub(slave_address=0x20)
    with caplog.at_level(logging.DEBUG, logger='pyipmi'), \
            caplog.at_level(logging.DEBUG, logger=__name__):
        intf.send_and_receive_raw(pyipmi.Target(0x72), 0, 6, b'\x01')

    rx = [r for r in caplog.records if r.getMessage().startswith('IPMB RX')]
    assert [r.name for r in rx] == [__name__]


def test_ipmb_default_router():
    intf = IpmbStub()
    assert isinstance(intf.router, MessageRouter)
    assert intf.router.unhandled_cc is None

    router = MessageRouter()
    intf.router = router
    assert intf.router is router
    intf.router = None
    assert intf.router is intf._default_router


def test_ipmb_inc_sequence_number():
    intf = IpmbStub()
    intf.next_sequence_number = 63
    intf._inc_sequence_number()
    assert intf.next_sequence_number == 0
