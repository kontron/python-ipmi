#!/usr/bin/env python
#-*- coding: utf-8 -*-

from nose.tools import eq_, raises
from mock import MagicMock, call

from pyipmi.sensor import *
from pyipmi import interfaces, create_connection
from pyipmi.msgs.sensor import SetSensorThresholdsRsp

def test_set_sensor_thresholds():

    rsp = SetSensorThresholdsRsp()
    rsp.completion_code = 0

    mock_send_recv = MagicMock()
    mock_send_recv.return_value = rsp

    interface = interfaces.create_interface('mock')
    ipmi = create_connection(interface)
    ipmi.send_message = mock_send_recv

    ipmi.set_sensor_thresholds(sensor_number=5, lun=1)
    args, kwargs = mock_send_recv.call_args
    req = args[0]
    eq_(req.lun, 1)
    eq_(req.sensor_number, 5)

    ipmi.set_sensor_thresholds(sensor_number=0, unr=10)
    args, kwargs = mock_send_recv.call_args
    req = args[0]
    eq_(req.set_mask.unr, 1)
    eq_(req.threshold.unr, 10)
    eq_(req.set_mask.ucr, 0)
    eq_(req.threshold.ucr, 0)
    eq_(req.set_mask.unc, 0)
    eq_(req.threshold.unc, 0)
    eq_(req.set_mask.lnc, 0)
    eq_(req.threshold.lnc, 0)
    eq_(req.set_mask.lcr, 0)
    eq_(req.threshold.lcr, 0)
    eq_(req.set_mask.lnr, 0)
    eq_(req.threshold.lnr, 0)

    ipmi.set_sensor_thresholds(sensor_number=5, ucr=11)
    args, kwargs = mock_send_recv.call_args
    req = args[0]
    eq_(req.lun, 0)
    eq_(req.set_mask.unr, 0)
    eq_(req.threshold.unr, 0)
    eq_(req.set_mask.ucr, 1)
    eq_(req.threshold.ucr, 11)
    eq_(req.set_mask.unc, 0)
    eq_(req.threshold.unc, 0)
    eq_(req.set_mask.lnc, 0)
    eq_(req.threshold.lnc, 0)
    eq_(req.set_mask.lcr, 0)
    eq_(req.threshold.lcr, 0)
    eq_(req.set_mask.lnr, 0)
    eq_(req.threshold.lnr, 0)
