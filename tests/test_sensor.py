#!/usr/bin/env python
# -*- coding: utf-8 -*-

from mock import MagicMock

from pyipmi import interfaces, create_connection
from pyipmi.msgs.sensor import SetSensorThresholdsRsp, PlatformEventRsp
from pyipmi.sensor import (EVENT_READING_TYPE_SENSOR_SPECIFIC,
                           SENSOR_TYPE_MODULE_HOT_SWAP)


def test_set_sensor_thresholds():

    rsp = SetSensorThresholdsRsp()
    rsp.completion_code = 0

    mock_send_recv = MagicMock()
    mock_send_recv.return_value = rsp

    interface = interfaces.create_interface('mock')
    ipmi = create_connection(interface)
    ipmi.send_message = mock_send_recv

    ipmi.set_sensor_thresholds(sensor_number=5, lun=1)
    args, _ = mock_send_recv.call_args
    req = args[0]
    assert req.lun == 1
    assert req.sensor_number == 5

    ipmi.set_sensor_thresholds(sensor_number=0, unr=10)
    args, _ = mock_send_recv.call_args
    req = args[0]
    assert req.set_mask.unr == 1
    assert req.threshold.unr == 10
    assert req.set_mask.ucr == 0
    assert req.threshold.ucr == 0
    assert req.set_mask.unc == 0
    assert req.threshold.unc == 0
    assert req.set_mask.lnc == 0
    assert req.threshold.lnc == 0
    assert req.set_mask.lcr == 0
    assert req.threshold.lcr == 0
    assert req.set_mask.lnr == 0
    assert req.threshold.lnr == 0

    ipmi.set_sensor_thresholds(sensor_number=5, ucr=11)
    args, _ = mock_send_recv.call_args
    req = args[0]
    assert req.lun == 0
    assert req.set_mask.unr == 0
    assert req.threshold.unr == 0
    assert req.set_mask.ucr == 1
    assert req.threshold.ucr == 11
    assert req.set_mask.unc == 0
    assert req.threshold.unc == 0
    assert req.set_mask.lnc == 0
    assert req.threshold.lnc == 0
    assert req.set_mask.lcr == 0
    assert req.threshold.lcr == 0
    assert req.set_mask.lnr == 0
    assert req.threshold.lnr == 0


def test_send_platform_event():

    rsp = PlatformEventRsp()
    rsp.completion_code = 0

    mock_send_recv = MagicMock()
    mock_send_recv.return_value = rsp

    interface = interfaces.create_interface('mock')
    ipmi = create_connection(interface)
    ipmi.send_message = mock_send_recv

    # Module handle closed event
    ipmi.send_platform_event(SENSOR_TYPE_MODULE_HOT_SWAP, 1,
                             EVENT_READING_TYPE_SENSOR_SPECIFIC, asserted=True,
                             event_data=[0, 0xff, 0xff])
    args, _ = mock_send_recv.call_args
    req = args[0]
    assert req.event_message_rev == 4
    assert req.sensor_type == 0xf2
    assert req.sensor_number == 1
    assert req.event_type.type == 0x6f
    assert req.event_type.dir == 0
    assert req.event_data == [0, 0xff, 0xff]
