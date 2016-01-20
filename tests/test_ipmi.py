#!/usr/bin/env python
#-*- coding: utf-8 -*-

from nose.tools import eq_, ok_, raises
from mock import MagicMock, call

from pyipmi import interfaces, create_connection
from pyipmi.msgs.bmc import GetDeviceIdReq, GetDeviceIdRsp
from pyipmi.msgs.sensor import GetSensorReadingReq, GetSensorReadingRsp

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
