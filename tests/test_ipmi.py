#!/usr/bin/env python
#-*- coding: utf-8 -*-

from nose.tools import eq_, ok_, raises
from mock import MagicMock

from pyipmi import interfaces, create_connection, Target, Routing
from pyipmi.errors import CompletionCodeError, RetryError
from pyipmi.msgs.bmc import GetDeviceIdReq, GetDeviceIdRsp
from pyipmi.msgs.sensor import GetSensorReadingReq, GetSensorReadingRsp
from pyipmi.msgs.constants import CC_NODE_BUSY


def test_target():
    target = Target()
    eq_(target.ipmb_address, None)
    eq_(target.routing, None)

    target = Target(0xa0)
    eq_(target.ipmb_address, 0xa0)
    eq_(target.routing, None)

    target = Target(ipmb_address=0xb0)
    eq_(target.ipmb_address, 0xb0)
    eq_(target.routing, None)


def test_target_routing():
    target = Target(routing=[(0x82, 0x20, 0)])
    eq_(len(target.routing), 1)
    eq_(target.routing[0].rq_sa, 0x82)
    eq_(target.routing[0].rs_sa, 0x20)
    eq_(target.routing[0].channel, 0)

    target = Target(routing=[(0x82, 0x20, 0), (0x20, 0x82, 7)])
    eq_(len(target.routing), 2)
    eq_(target.routing[0].rq_sa, 0x82)
    eq_(target.routing[0].rs_sa, 0x20)
    eq_(target.routing[0].channel, 0)
    eq_(target.routing[1].rq_sa, 0x20)
    eq_(target.routing[1].rs_sa, 0x82)
    eq_(target.routing[1].channel, 7)


def test_routing():
    routing = Routing(0x82, 0x20, 7)
    eq_(routing.rq_sa, 0x82)
    eq_(routing.rs_sa, 0x20)
    eq_(routing.channel, 7)


def test_target_set_routing():
    target = Target()

    target.set_routing([(0x11, 0x12, 0x13)])
    eq_(len(target.routing), 1)
    eq_(target.routing[0].rq_sa, 0x11)
    eq_(target.routing[0].rs_sa, 0x12)
    eq_(target.routing[0].channel, 0x13)

    target.set_routing([(0x11, 0x12, 0x13), (0x21, 0x22, 0x23)])
    eq_(len(target.routing), 2)
    eq_(target.routing[0].rq_sa, 0x11)
    eq_(target.routing[0].rs_sa, 0x12)
    eq_(target.routing[0].channel, 0x13)
    eq_(target.routing[1].rq_sa, 0x21)
    eq_(target.routing[1].rs_sa, 0x22)
    eq_(target.routing[1].channel, 0x23)


def test_target_set_routing_from_string():
    target = Target()

    target.set_routing('[(0x11, 0x12, 0x13)]')
    eq_(len(target.routing), 1)
    eq_(target.routing[0].rq_sa, 0x11)
    eq_(target.routing[0].rs_sa, 0x12)
    eq_(target.routing[0].channel, 0x13)

    target.set_routing('[(0x11, 0x12, 0x13), (0x21, 0x22, 0x23)]')
    eq_(len(target.routing), 2)
    eq_(target.routing[0].rq_sa, 0x11)
    eq_(target.routing[0].rs_sa, 0x12)
    eq_(target.routing[0].channel, 0x13)
    eq_(target.routing[1].rq_sa, 0x21)
    eq_(target.routing[1].rs_sa, 0x22)
    eq_(target.routing[1].channel, 0x23)


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
    eq_(mock.call_count, 2)


@raises(RetryError)
def test_ipmi_send_message_retry_error():
    req = GetDeviceIdReq()
    rsp = GetDeviceIdRsp()

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
    ok_(isinstance(req, GetDeviceIdReq))


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
    ok_(isinstance(req, GetSensorReadingReq))
    eq_(req.sensor_number, 5)
    eq_(req.lun, 2)
