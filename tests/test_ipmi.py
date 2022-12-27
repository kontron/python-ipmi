#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest
from mock import MagicMock

from pyipmi import interfaces, create_connection, Target, Routing
from pyipmi.errors import CompletionCodeError, RetryError
from pyipmi.msgs.bmc import GetDeviceIdReq, GetDeviceIdRsp
from pyipmi.msgs.sensor import GetSensorReadingReq, GetSensorReadingRsp
from pyipmi.msgs.constants import CC_NODE_BUSY


def test_target():
    target = Target()
    assert target.ipmb_address is None
    assert target.routing is None

    target = Target(0xa0)
    assert target.ipmb_address == 0xa0
    assert target.routing is None

    target = Target(ipmb_address=0xb0)
    assert target.ipmb_address == 0xb0
    assert target.routing is None


def test_target_routing():
    target = Target(routing=[(0x82, 0x20, 0)])
    assert len(target.routing) == 1
    assert target.routing[0].rq_sa == 0x82
    assert target.routing[0].rs_sa == 0x20
    assert target.routing[0].channel == 0

    target = Target(routing=[(0x82, 0x20, 0), (0x20, 0x82, 7)])
    assert len(target.routing) == 2
    assert target.routing[0].rq_sa == 0x82
    assert target.routing[0].rs_sa == 0x20
    assert target.routing[0].channel == 0
    assert target.routing[1].rq_sa == 0x20
    assert target.routing[1].rs_sa == 0x82
    assert target.routing[1].channel == 7


def test_routing():
    routing = Routing(0x82, 0x20, 7)
    assert routing.rq_sa == 0x82
    assert routing.rs_sa == 0x20
    assert routing.channel == 7


def test_target_set_routing():
    target = Target()

    target.set_routing([(0x11, 0x12, 0x13)])
    assert len(target.routing) == 1
    assert target.routing[0].rq_sa == 0x11
    assert target.routing[0].rs_sa == 0x12
    assert target.routing[0].channel == 0x13

    target.set_routing([(0x11, 0x12, 0x13), (0x21, 0x22, 0x23)])
    assert len(target.routing) == 2
    assert target.routing[0].rq_sa == 0x11
    assert target.routing[0].rs_sa == 0x12
    assert target.routing[0].channel == 0x13
    assert target.routing[1].rq_sa == 0x21
    assert target.routing[1].rs_sa == 0x22
    assert target.routing[1].channel == 0x23


def test_target_set_routing_from_string():
    target = Target()

    target.set_routing('[(0x11, 0x12, 0x13)]')
    assert len(target.routing) == 1
    assert target.routing[0].rq_sa == 0x11
    assert target.routing[0].rs_sa == 0x12
    assert target.routing[0].channel == 0x13

    target.set_routing('[(0x11, 0x12, 0x13), (0x21, 0x22, 0x23)]')
    assert len(target.routing) == 2
    assert target.routing[0].rq_sa == 0x11
    assert target.routing[0].rs_sa == 0x12
    assert target.routing[0].channel == 0x13
    assert target.routing[1].rq_sa == 0x21
    assert target.routing[1].rs_sa == 0x22
    assert target.routing[1].channel == 0x23


def test_ipmi_send_message_retry():
    req = GetDeviceIdReq()
    rsp = GetDeviceIdRsp()

    interface = interfaces.create_interface('mock')
    cc = CompletionCodeError(CC_NODE_BUSY)
    mock = MagicMock(side_effect=(cc, 0))
    mock.return_value = rsp
    interface.send_and_receive = mock
    ipmi = create_connection(interface)
    ipmi.target = None
    ipmi.send_message(req)
    assert mock.call_count == 2


def test_ipmi_send_message_retry_error():
    req = GetDeviceIdReq()
    rsp = GetDeviceIdRsp()

    with pytest.raises(RetryError):
        interface = interfaces.create_interface('mock')
        cc = CompletionCodeError(CC_NODE_BUSY)
        mock = MagicMock(side_effect=(cc, cc, cc))
        mock.return_value = rsp
        interface.send_and_receive = mock
        ipmi = create_connection(interface)
        ipmi.target = None
        ipmi.send_message(req)


def test_ipmi_send_message_with_name():

    rsp = GetDeviceIdRsp()
    rsp.completion_code = 0

    mock_send_message = MagicMock()
    mock_send_message.return_value = rsp

    interface = interfaces.create_interface('mock')
    ipmi = create_connection(interface)
    ipmi.send_message = mock_send_message

    ipmi.send_message_with_name('GetDeviceId')
    args, kwargs = mock_send_message.call_args
    req = args[0]
    assert isinstance(req, GetDeviceIdReq)


def test_ipmi_send_message_with_name_and_kwargs():

    rsp = GetSensorReadingRsp()
    rsp.completion_code = 0

    mock_send_message = MagicMock()
    mock_send_message.return_value = rsp

    interface = interfaces.create_interface('mock')
    ipmi = create_connection(interface)
    ipmi.send_message = mock_send_message

    ipmi.send_message_with_name('GetSensorReading', sensor_number=5, lun=2)
    args, kwargs = mock_send_message.call_args
    req = args[0]
    assert isinstance(req, GetSensorReadingReq)
    assert req.sensor_number == 5
    assert req.lun == 2
