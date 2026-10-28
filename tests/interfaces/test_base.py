#!/usr/bin/env python

import logging

import pytest

import pyipmi
import pyipmi.msgs.bmc
from pyipmi.interfaces import INTERFACES
from pyipmi.interfaces.base import Interface
from pyipmi.interfaces.ipmb import (IpmbInterface, IpmbHeaderReq,
                                   encode_ipmb_msg)
from pyipmi.interfaces.router import MessageRouter, encode_ipmb_response
from pyipmi.interfaces.aardvark import Aardvark
from pyipmi.interfaces.ipmbdev import IpmbDev
from pyipmi.interfaces.openipmblink import OpenIpmbLink
from pyipmi.interfaces.kcm import Kcm


@pytest.mark.parametrize('intf', INTERFACES)
def test_interfaces_use_base_class(intf):
    assert issubclass(intf, Interface)
    assert intf.NAME is not None


@pytest.mark.parametrize('intf', [Aardvark, IpmbDev, OpenIpmbLink, Kcm])
def test_ipmb_interfaces_use_ipmb_base_class(intf):
    assert issubclass(intf, IpmbInterface)


def test_not_implemented():
    intf = Interface()
    with pytest.raises(NotImplementedError):
        intf.send_and_receive_raw(pyipmi.Target(0x20), 0, 6, b'\x01')
    with pytest.raises(NotImplementedError):
        intf.is_target_accessible(pyipmi.Target(0x20))
    with pytest.raises(NotImplementedError), \
            pytest.warns(DeprecationWarning):
        intf.is_ipmc_accessible(pyipmi.Target(0x20))


class NewNameStub(Interface):
    def is_target_accessible(self, target):
        return True


class OldNameStub(Interface):
    """An interface outside of the library with the deprecated name."""

    def is_ipmc_accessible(self, target):
        return True


def test_is_ipmc_accessible_deprecated():
    with pytest.warns(DeprecationWarning, match='use is_target_accessible'):
        assert NewNameStub().is_ipmc_accessible(pyipmi.Target(0x20))


def test_is_target_accessible_old_name_implemented():
    with pytest.warns(DeprecationWarning,
                      match='implement is_target_accessible'):
        assert OldNameStub().is_target_accessible(pyipmi.Target(0x20))


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


def request_frame(netfn, cmdid, data=b''):
    header = IpmbHeaderReq()
    header.rs_sa = 0x20
    header.rs_lun = 0
    header.rq_sa = 0x81
    header.rq_lun = 2
    header.rq_seq = 5
    header.netfn = netfn
    header.cmdid = cmdid
    return header, encode_ipmb_msg(header, data)


def test_answer_request_message_handler():
    def get_device_id(req):
        rsp = pyipmi.msgs.bmc.GetDeviceIdRsp()
        rsp.completion_code = 0
        rsp.device_id = 0x42
        return rsp

    router = MessageRouter()
    router.register_handler(6, 1, get_device_id)
    header, frame = request_frame(6, 1)

    rsp = router.answer_request(frame)

    expected = pyipmi.msgs.bmc.GetDeviceIdRsp()
    expected.completion_code = 0
    expected.device_id = 0x42
    assert rsp == encode_ipmb_response(
        header, pyipmi.msgs.encode_message(expected))
    # answered in the calling thread, no worker is started
    assert router._worker is None


def test_answer_request_raw_handler_gets_no_interface():
    calls = []

    def handler(interface, header, data):
        calls.append((interface, header.cmdid, data))
        return b'\x00\x01'

    router = MessageRouter()
    router.register_raw_handler(0x2e, 0x10, handler)
    header, frame = request_frame(0x2e, 0x10, b'\xaa\xbb')

    assert router.answer_request(frame) == encode_ipmb_response(
        header, b'\x00\x01')
    assert calls == [(None, 0x10, b'\xaa\xbb')]


def test_answer_request_unhandled():
    header, frame = request_frame(6, 1)
    assert MessageRouter().answer_request(frame) == encode_ipmb_response(
        header, b'\xc1')
    assert MessageRouter(unhandled_cc=None).answer_request(frame) is None


def test_answer_request_handler_fails():
    def handler(interface, header, data):
        raise RuntimeError('failed')

    router = MessageRouter()
    router.register_raw_handler(6, 1, handler)
    header, frame = request_frame(6, 1)
    assert router.answer_request(frame) == encode_ipmb_response(
        header, b'\xff')


def test_answer_request_handler_returns_none():
    router = MessageRouter()
    router.register_raw_handler(6, 1, lambda intf, hdr, data: None)
    assert router.answer_request(request_frame(6, 1)[1]) is None


@pytest.mark.parametrize('frame', [
    b'\x20\x18\xc8',                         # too short
    b'\x20\x18\xc8\x81\x14\x01\x00',         # wrong checksum
    encode_ipmb_response(request_frame(6, 1)[0], b'\x00'),  # a response
])
def test_answer_request_invalid(frame):
    router = MessageRouter()
    router.register_raw_handler(6, 1, lambda intf, hdr, data: b'\x00')
    assert router.answer_request(frame) is None
