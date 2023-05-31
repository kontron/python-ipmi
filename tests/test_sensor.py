#!/usr/bin/env python
# -*- coding: utf-8 -*-

from mock import MagicMock

from pyipmi import interfaces, create_connection
from pyipmi.msgs.sensor import (SetSensorThresholdsRsp, GetSensorThresholdsRsp,
                                GetSensorReadingRsp, PlatformEventRsp)
from pyipmi.sensor import (EVENT_READING_TYPE_SENSOR_SPECIFIC,
                           SENSOR_TYPE_MODULE_HOT_SWAP)


class TestSensor(object):

    def setup_method(self):
        self.mock_send_recv = MagicMock()

        interface = interfaces.create_interface('mock')
        self.ipmi = create_connection(interface)
        self.ipmi.send_message = self.mock_send_recv

    def test_set_sensor_thresholds(self):

        rsp = SetSensorThresholdsRsp()
        rsp.completion_code = 0
        self.mock_send_recv.return_value = rsp

        self.ipmi.set_sensor_thresholds(sensor_number=5, lun=1)
        args, _ = self.mock_send_recv.call_args
        req = args[0]
        assert req.lun == 1
        assert req.sensor_number == 5

        self.ipmi.set_sensor_thresholds(sensor_number=0, unr=10)
        args, _ = self.mock_send_recv.call_args
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

        self.ipmi.set_sensor_thresholds(sensor_number=5, ucr=11)
        args, _ = self.mock_send_recv.call_args
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

    def test_send_platform_event(self):

        rsp = PlatformEventRsp()
        rsp.completion_code = 0
        self.mock_send_recv.return_value = rsp

        # Module handle closed event
        self.ipmi.send_platform_event(SENSOR_TYPE_MODULE_HOT_SWAP, 1,
                                      EVENT_READING_TYPE_SENSOR_SPECIFIC,
                                      asserted=True,
                                      event_data=[0, 0xff, 0xff])
        args, _ = self.mock_send_recv.call_args
        req = args[0]
        assert req.event_message_rev == 4
        assert req.sensor_type == 0xf2
        assert req.sensor_number == 1
        assert req.event_type.type == 0x6f
        assert req.event_type.dir == 0
        assert req.event_data == [0, 0xff, 0xff]

    def test_get_sensor_thresholds(self):

        rsp = GetSensorThresholdsRsp()
        rsp.readable_mask.lnc = 1
        rsp.readable_mask.lcr = 1
        rsp.readable_mask.lnr = 1
        rsp.readable_mask.unc = 1
        rsp.readable_mask.ucr = 1
        rsp.readable_mask.unr = 1
        rsp.threshold.lnc = 1
        rsp.threshold.lcr = 2
        rsp.threshold.lnr = 3
        rsp.threshold.unc = 4
        rsp.threshold.ucr = 5
        rsp.threshold.unr = 6
        rsp.completion_code = 0
        self.mock_send_recv.return_value = rsp

        thresholds = self.ipmi.get_sensor_thresholds(0)
        assert thresholds['unr'] == 6
        assert thresholds['ucr'] == 5
        assert thresholds['unc'] == 4
        assert thresholds['lnc'] == 1
        assert thresholds['lcr'] == 2
        assert thresholds['lnr'] == 3

    def test_get_sensor_reading(self):

        # in progress
        rsp = GetSensorReadingRsp()
        rsp.sensor_reading = 0
        rsp.config.initial_update_in_progress = 1
        self.mock_send_recv.return_value = rsp

        (reading, states) = self.ipmi.get_sensor_reading(0)
        assert reading is None
        assert states is None

        # no states
        rsp = GetSensorReadingRsp()
        rsp.sensor_reading = 0x55
        rsp.config.initial_update_in_progress = 0
        self.mock_send_recv.return_value = rsp

        (reading, states) = self.ipmi.get_sensor_reading(0)
        assert reading == 0x55
        assert states is None

        # with states
        rsp = GetSensorReadingRsp()
        rsp.sensor_reading = 0
        rsp.states1 = 0x55
        rsp.states2 = 0x55
        rsp.config.initial_update_in_progress = 0
        self.mock_send_recv.return_value = rsp

        (reading, states) = self.ipmi.get_sensor_reading(0)
        assert reading == 0
        assert states == 0x5555
