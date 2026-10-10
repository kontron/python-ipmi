#!/usr/bin/env python

from unittest.mock import MagicMock

import pytest

from pyipmi import interfaces, create_connection
from pyipmi.msgs.sensor import (SetSensorThresholdsRsp, GetSensorThresholdsRsp,
                                GetSensorReadingRsp, PlatformEventRsp)
from pyipmi.sensor import (EVENT_READING_TYPE_SENSOR_SPECIFIC, GENERATOR_ID_SMS,
                           event_offset_to_string,
                           event_reading_type_to_string,
                           sensor_type_to_string,
                           SENSOR_TYPE_MODULE_HOT_SWAP)

from .ipmi_helper import create_ipmi


class TestSensor:

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

    def test_send_platform_event_without_generator_id(self):
        # the Generator ID is taken from the requester address
        self.mock_send_recv.return_value = PlatformEventRsp()
        self.ipmi.send_platform_event(SENSOR_TYPE_MODULE_HOT_SWAP, 1,
                                      EVENT_READING_TYPE_SENSOR_SPECIFIC)
        req = self.mock_send_recv.call_args[0][0]
        assert req.generator_id is None

    @pytest.mark.parametrize('kwargs, generator_id', [
        ({}, GENERATOR_ID_SMS),
        ({'generator_id': 0x21}, 0x21),
    ])
    def test_send_platform_event_system_interface(self, kwargs,
                                                  generator_id):
        self.ipmi.interface.is_system_interface = lambda target: True
        self.mock_send_recv.return_value = PlatformEventRsp()
        self.ipmi.send_platform_event(SENSOR_TYPE_MODULE_HOT_SWAP, 1,
                                      EVENT_READING_TYPE_SENSOR_SPECIFIC,
                                      **kwargs)
        req = self.mock_send_recv.call_args[0][0]
        assert req.generator_id == generator_id

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


@pytest.mark.parametrize('sensor_type, string', [
    (0x01, 'Temperature'),
    (0xf0, 'FRU Hot Swap'),
    (0xc5, 'OEM (0xc5)'),
    (0x00, 'Unknown (0x00)'),
])
def test_sensor_type_to_string(sensor_type, string):
    assert sensor_type_to_string(sensor_type) == string


@pytest.mark.parametrize('event_reading_type, string', [
    (0x01, 'Threshold'),
    (0x03, 'Generic Discrete'),
    (0x0c, 'Generic Discrete'),
    (0x6f, 'Sensor-specific'),
    (0x70, 'OEM'),
    (0x00, 'Unspecified'),
])
def test_event_reading_type_to_string(event_reading_type, string):
    assert event_reading_type_to_string(event_reading_type) == string


@pytest.mark.parametrize('event_reading_type, sensor_type, offset, string', [
    (0x01, 0x01, 0x09, 'Upper Critical going high'),
    (0x08, 0x25, 0x01, 'Device Present'),
    (0x6f, 0x08, 0x01, 'Power Supply Failure Detected'),
    (0x6f, 0x23, 0x08, 'Timer Interrupt'),
    # reserved and unknown offsets
    (0x6f, 0x23, 0x04, None),
    (0x01, 0x01, 0x0c, None),
    (0x6f, 0xc0, 0x00, None),
    (0x70, 0x01, 0x00, None),
])
def test_event_offset_to_string(event_reading_type, sensor_type, offset,
                                string):
    assert event_offset_to_string(event_reading_type, sensor_type,
                                  offset) == string


@pytest.mark.parametrize('sdr_count, data', [(False, b''), (True, b'\x01')])
def test_get_device_sdr_info(sdr_count, data):
    # 3 sensors on LUN 0 and 2, dynamic population with the change time
    ipmi = create_ipmi(b'\x00\x03\x85\x00\x10\x20\x68')
    info = ipmi.get_device_sdr_info(sdr_count=sdr_count)
    assert ipmi.requests == [('GetDeviceSdrInfoReq', data)]
    assert info.count == 3
    assert info.luns_with_sensors == [0, 2]
    assert info.dynamic_population
    assert info.sensor_population_change == 0x68201000


def test_get_device_sdr_info_static():
    ipmi = create_ipmi(b'\x00\x05\x01')
    info = ipmi.get_device_sdr_info()
    assert info.count == 5
    assert info.luns_with_sensors == [0]
    assert not info.dynamic_population
    assert info.sensor_population_change is None
