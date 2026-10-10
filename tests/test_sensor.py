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
                           sensor_type_from_string,
                           SENSOR_TYPE_MODULE_HOT_SWAP, SENSOR_TYPE_VOLTAGE,
                           EVENT_BITS_SET, EVENT_BITS_CLEAR, EVENT_BITS_WRITE)
from pyipmi.errors import CompletionCodeError, DecodingError, NotSupportedError
from pyipmi.sdr import SdrCommon

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


def test_get_sensor_reading_factors():
    # M = -2, tolerance 5, B = 100, accuracy 0x45, accuracy exponent 2,
    # K2 = -3, K1 = 2
    ipmi = create_ipmi(b'\x00\x90\xfe\xc5\x64\x05\x18\xd2')
    factors = ipmi.get_sensor_reading_factors(0x10, 0x80, lun=1)
    assert ipmi.requests == [('GetSensorReadingFactorsReq', b'\x10\x80')]
    assert factors.next_reading == 0x90
    assert factors.m == -2
    assert factors.tolerance == 5
    assert factors.b == 100
    assert factors.accuracy == 0x45
    assert factors.accuracy_exp == 2
    assert factors.k2 == -3
    assert factors.k1 == 2


def test_set_sensor_hysteresis():
    ipmi = create_ipmi(b'\x00')
    ipmi.set_sensor_hysteresis(0x10, 2, 3)
    assert ipmi.requests == [('SetSensorHysteresisReq',
                              b'\x10\xff\x02\x03')]


def test_get_sensor_hysteresis():
    ipmi = create_ipmi(b'\x00\x02\x03')
    assert ipmi.get_sensor_hysteresis(0x10) == (2, 3)
    assert ipmi.requests == [('GetSensorHysteresisReq', b'\x10\xff')]


@pytest.mark.parametrize('kwargs, data', [
    # only the global enables
    ({}, b'\x10\xc0'),
    ({'event_messages': False}, b'\x10\x40'),
    ({'sensor_scanning': False}, b'\x10\x80'),
    # enable or disable selected events
    ({'assertion_mask': 0x0201}, b'\x10\xd0\x01\x02\x00\x00'),
    ({'deassertion_mask': 0x4080, 'enable': False},
     b'\x10\xe0\x00\x00\x80\x40'),
])
def test_set_sensor_event_enable(kwargs, data):
    ipmi = create_ipmi(b'\x00')
    ipmi.set_sensor_event_enable(0x10, **kwargs)
    assert ipmi.requests == [('SetSensorEventEnableReq', data)]


@pytest.mark.parametrize('rsp, messages, scanning, assertion, deassertion', [
    (b'\x00\xc0\x01\x02\x80\x40', True, True, 0x0201, 0x4080),
    (b'\x00\x40', False, True, None, None),
])
def test_get_sensor_event_enable(rsp, messages, scanning, assertion,
                                 deassertion):
    ipmi = create_ipmi(rsp)
    enable = ipmi.get_sensor_event_enable(0x10)
    assert ipmi.requests == [('GetSensorEventEnableReq', b'\x10')]
    assert enable.event_messages == messages
    assert enable.sensor_scanning == scanning
    assert enable.assertion_mask == assertion
    assert enable.deassertion_mask == deassertion


@pytest.mark.parametrize('rsp, unavailable, asserted, deasserted', [
    (b'\x00\xc0\x05\x01\x00\x02', False, 0x0105, 0x0200),
    (b'\x00\xe0', True, None, None),
])
def test_get_sensor_event_status(rsp, unavailable, asserted, deasserted):
    ipmi = create_ipmi(rsp)
    status = ipmi.get_sensor_event_status(0x10)
    assert ipmi.requests == [('GetSensorEventStatusReq', b'\x10')]
    assert status.event_messages_enabled
    assert status.sensor_scanning_enabled
    assert status.reading_unavailable == unavailable
    assert status.asserted == asserted
    assert status.deasserted == deasserted


def test_set_sensor_type():
    ipmi = create_ipmi(b'\x00')
    ipmi.set_sensor_type(0x10, 0x01, 0x6f)
    assert ipmi.requests == [('SetSensorTypeReq', b'\x10\x01\x6f')]


def test_get_sensor_type():
    ipmi = create_ipmi(b'\x00\x21\x6f')
    assert ipmi.get_sensor_type(0x10) == (0x21, 0x6f)
    assert ipmi.requests == [('GetSensorTypeReq', b'\x10')]


@pytest.mark.parametrize('kwargs, data', [
    # only the reading
    ({'reading': 0x42}, b'\x10\x01\x42'),
    # the earlier bytes are filled with 0 and "don't change"
    ({'deassertion_mask': 0x0003},
     b'\x10\x0c\x00\x00\x00\x03\x00'),
    ({'assertion_mask': 0x0101, 'mask_operation': EVENT_BITS_SET},
     b'\x10\x10\x00\x01\x01'),
    ({'assertion_mask': 0x0001, 'mask_operation': EVENT_BITS_CLEAR},
     b'\x10\x20\x00\x01\x00'),
    ({'assertion_mask': 0x0001, 'mask_operation': EVENT_BITS_WRITE},
     b'\x10\x30\x00\x01\x00'),
    # the event data with and without the offset
    ({'reading': 0x42, 'assertion_mask': 0x0002,
      'event_data': b'\x01\xff\xff', 'event_data_with_offset': True},
     b'\x10\xb1\x42\x02\x00\x00\x00\x01\xff\xff'),
    ({'event_data': b'\x01\xff\xff'},
     b'\x10\x40\x00\x00\x00\x00\x00\x01\xff\xff'),
    # nothing changed
    ({}, b'\x10\x00'),
])
def test_set_sensor_reading_and_event_status(kwargs, data):
    ipmi = create_ipmi(b'\x00')
    ipmi.set_sensor_reading_and_event_status(0x10, **kwargs)
    assert ipmi.requests == [('SetSensorReadingAndEventStatusReq', data)]


@pytest.mark.parametrize('kwargs', [
    {'mask_operation': 0},
    {'event_data': b'\x01\x02'},
])
def test_set_sensor_reading_and_event_status_invalid(kwargs):
    ipmi = create_ipmi(b'\x00')
    with pytest.raises(ValueError):
        ipmi.set_sensor_reading_and_event_status(0x10, **kwargs)
    assert ipmi.requests == []


@pytest.mark.parametrize('method, args', [
    ('get_sensor_reading_factors', (0x10, 0x80)),
    ('set_sensor_hysteresis', (0x10, 1, 1)),
    ('get_sensor_hysteresis', (0x10,)),
    ('set_sensor_event_enable', (0x10,)),
    ('get_sensor_event_enable', (0x10,)),
    ('get_sensor_event_status', (0x10,)),
    ('set_sensor_type', (0x10, 1, 1)),
    ('get_sensor_type', (0x10,)),
    ('set_sensor_reading_and_event_status', (0x10, 0x42)),
])
def test_sensor_commands_error(method, args):
    ipmi = create_ipmi(b'\xcb')
    with pytest.raises(CompletionCodeError):
        getattr(ipmi, method)(*args)


def device_id_rsp(functions):
    # the additional device support byte: bit 0 sensor, bit 1 SDR repository
    return b'\x00\x20\x81\x01\x02\x51' + bytes([functions]) + bytes(5)


def full_record(name, sensor_type=0x01, units_1=0x00, linearization=0x00):
    # threshold sensor 4 of the BMC 0x20, LUN 1, M = 1, unit degrees C
    data = bytearray([
        0x01, 0x00, 0x51, 0x01, 0x00, 0x20, 0x01, 0x04, 0x03, 0x01,
        0x7f, 0x68, sensor_type, 0x01, 0x80, 0x0a, 0x80, 0x7a, 0x38, 0x38,
        units_1, 0x01, 0x00, linearization, 0x01, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x01, 40, 80, 10, 127, 0, 100, 90, 80, 0, 0, 0, 2, 2, 0, 0,
        0, 0xc0 | len(name)])
    return SdrCommon.from_data(bytes(data) + name.encode())


# sensor-specific slot/connector sensor 0xd3
COMPACT_RECORD = SdrCommon.from_data(bytes([
    0xd3, 0x00, 0x51, 0x02, 0x28, 0x82, 0x00, 0xd3, 0xc1, 0x64,
    0x03, 0x40, 0x21, 0x6f, 0x05, 0x00, 0x01, 0x00, 0x03, 0x00,
    0xc0, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0xcd]) + b'A4:Pres SFP-1')

# a record that is no sensor: FRU device locator of FRU 0
FRU_LOCATOR = SdrCommon.from_data(bytes([
    0x10, 0x00, 0x51, 0x11, 0x00, 0x20, 0x00, 0x00, 0x00, 0x00,
    0x10, 0x00, 0x0a, 0x01, 0x00, 0xc3]) + b'FRU')


@pytest.mark.parametrize('functions, source', [
    (0x03, 'sdr_repository_entries'),
    # a satellite controller without SDR repository
    (0x01, 'device_sdr_entries'),
])
def test_sdr_entries(functions, source):
    ipmi = create_ipmi({'GetDeviceId': device_id_rsp(functions)})
    records = [COMPACT_RECORD]
    setattr(ipmi, source, lambda: iter(records))
    assert list(ipmi.sdr_entries()) == records


def test_sdr_entries_not_supported():
    ipmi = create_ipmi({'GetDeviceId': device_id_rsp(0x00)})
    with pytest.raises(NotSupportedError):
        ipmi.sdr_entries()


class TestFindSensors:
    RECORDS = [full_record('CPU Temp'), FRU_LOCATOR,
               full_record('P12V', sensor_type=SENSOR_TYPE_VOLTAGE),
               COMPACT_RECORD, full_record('CPU1 Temp')]

    def find(self, **kwargs):
        ipmi = create_ipmi({})
        ipmi.sdr_entries = lambda: iter(self.RECORDS)
        return [str(record.device_id_string)
                for record in ipmi.find_sensors(**kwargs)]

    @pytest.mark.parametrize('kwargs, names', [
        # all sensors, without the FRU locator
        ({}, ['CPU Temp', 'P12V', 'A4:Pres SFP-1', 'CPU1 Temp']),
        # the pattern matches the whole name and ignores case
        ({'name': 'cpu*'}, ['CPU Temp', 'CPU1 Temp']),
        ({'name': 'CPU?'}, []),
        ({'name': 'cpu[0-9] temp'}, ['CPU1 Temp']),
        ({'name': '*sfp*'}, ['A4:Pres SFP-1']),
        ({'name': 'P12V'}, ['P12V']),
        ({'sensor_type': 'temperature'}, ['CPU Temp', 'CPU1 Temp']),
        ({'sensor_type': SENSOR_TYPE_VOLTAGE}, ['P12V']),
        ({'sensor_type': 'slot-connector'}, ['A4:Pres SFP-1']),
        ({'name': 'cpu1*', 'sensor_type': 'temperature'}, ['CPU1 Temp']),
        ({'name': 'cpu*', 'sensor_type': 'voltage'}, []),
    ])
    def test_find_sensors(self, kwargs, names):
        assert self.find(**kwargs) == names

    def test_unknown_type(self):
        with pytest.raises(ValueError):
            self.find(sensor_type='humidity')


@pytest.mark.parametrize('name, sensor_type', [
    ('temperature', 0x01),
    ('Voltage', 0x02),
    ('power supply', 0x08),
    ('POWER-SUPPLY', 0x08),
    ('drive_slot_bay', 0x0d),
    ('Drive Slot / Bay', 0x0d),
    ('0x21', 0x21),
    ('192', 0xc0),
])
def test_sensor_type_from_string(name, sensor_type):
    assert sensor_type_from_string(name) == sensor_type


@pytest.mark.parametrize('name', ['humidity', '', '0x100', '-1'])
def test_sensor_type_from_string_invalid(name):
    with pytest.raises(ValueError):
        sensor_type_from_string(name)


class TestReadSensor:
    def test_full_record(self):
        # reading 45, upper non-critical threshold crossed
        ipmi = create_ipmi(b'\x00\x2d\xc0\x08\x00')
        reading = ipmi.read_sensor(full_record('CPU Temp'))
        # the sensor is read with its number and the LUN of its owner
        assert ipmi.requests == [('GetSensorReadingReq', b'\x04')]
        assert ipmi.interface.send_and_receive.call_args[0][0].lun == 1
        assert reading.name == 'CPU Temp'
        assert reading.raw == 45
        assert reading.value == 45.0
        assert reading.unit == 'degrees C'
        assert reading.states == 0x08
        assert reading.state_names() == ['Upper Non-critical']

    def test_initial_update_in_progress(self):
        ipmi = create_ipmi(b'\x00\x00\xe0\x00\x00')
        reading = ipmi.read_sensor(full_record('CPU Temp'))
        assert reading.raw is None
        assert reading.value is None
        assert reading.unit == 'degrees C'

    def test_non_linear(self):
        # M = -2, B = 100, K1 = 2, K2 = -3 for the reading 0x80
        ipmi = create_ipmi({
            'GetSensorReading': b'\x00\x80\xc0\x00\x00',
            'GetSensorReadingFactors': b'\x00\x90\xfe\xc5\x64\x05\x18\xd2'})
        reading = ipmi.read_sensor(full_record('Fan', linearization=0x70))
        assert ipmi.requests == [('GetSensorReadingReq', b'\x04'),
                                 ('GetSensorReadingFactorsReq', b'\x04\x80')]
        assert reading.value == pytest.approx((-2 * 0x80 + 100 * 10**2)
                                              * 10**-3)

    def test_no_numeric_reading(self):
        # analog data format 3: the sensor has no numeric reading
        ipmi = create_ipmi(b'\x00\x01\xc0\x00\x00')
        reading = ipmi.read_sensor(full_record('Status', units_1=0xc0))
        assert reading.raw == 1
        assert reading.value is None
        assert reading.unit == ''

    def test_compact_record(self):
        # the states 0 and 2 of the slot/connector sensor are asserted
        ipmi = create_ipmi(b'\x00\x00\xc0\x05\x00')
        reading = ipmi.read_sensor(COMPACT_RECORD)
        assert ipmi.requests == [('GetSensorReadingReq', b'\xd3')]
        assert reading.value is None
        assert reading.unit == ''
        assert reading.state_names() == [
            'Fault Status Asserted', 'Slot / Connector Device '
            'Installed/Attached']

    @pytest.mark.parametrize('record, rsp, states', [
        # the reserved bits 7:6 of a threshold sensor are cleared
        (full_record('CPU Temp'), b'\x00\x2d\xc0\xc8\xff', 0x08),
        # the reserved bit 15 of a discrete sensor is cleared
        (COMPACT_RECORD, b'\x00\x00\xc0\xff\xff', 0x7fff),
    ])
    def test_reserved_state_bits(self, record, rsp, states):
        reading = create_ipmi(rsp).read_sensor(record)
        assert reading.states == states

    def test_no_states(self):
        ipmi = create_ipmi(b'\x00\x2d\xc0')
        reading = ipmi.read_sensor(full_record('CPU Temp'))
        assert reading.states is None
        assert reading.state_names() == []

    def test_error(self):
        ipmi = create_ipmi(b'\xcb')
        with pytest.raises(CompletionCodeError):
            ipmi.read_sensor(full_record('CPU Temp'))


def test_convert_non_linear_without_factors():
    with pytest.raises(DecodingError):
        full_record('Fan', linearization=0x70).convert_sensor_raw_to_value(1)
