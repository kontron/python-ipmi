#!/usr/bin/env python
#-*- coding: utf-8 -*-

from nose.tools import eq_, ok_, raises
from mock import MagicMock

from pyipmi import interfaces, create_connection
from pyipmi.errors import CompletionCodeError, RetryError
from pyipmi.msgs.bmc import GetDeviceIdReq, GetDeviceIdRsp
from pyipmi.msgs.sensor import GetSensorReadingReq, GetSensorReadingRsp
from pyipmi.msgs.constants import CC_NODE_BUSY


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
