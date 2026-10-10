#!/usr/bin/env python

from types import SimpleNamespace

import pytest

from pyipmi.errors import DecodingError
from pyipmi.sdr import (SdrCommon, SdrFullSensorRecord, SdrCompactSensorRecord,
                        SdrEventOnlySensorRecord, SdrFruDeviceLocator,
                        SdrManagementControllerDeviceLocator,
                        SdrManagementControllerConfirmationRecord,
                        SdrOEMSensorRecord, SdrUnknownSensorRecord,
                        entity_id_to_string, sdr_type_to_string,
                        units_to_string)

from .ipmi_helper import create_ipmi


class TestSdrFullSensorRecord:
    def test_convert_complement(self):
        assert SdrFullSensorRecord()._convert_complement(0x8, 4) == -8
        assert SdrFullSensorRecord()._convert_complement(0x80, 8) == -128
        assert SdrFullSensorRecord()._convert_complement(0x8000, 16) == -32768

    def test_decode_capabilities(self):
        record = SdrFullSensorRecord()

        record._decode_capabilities(0)
        assert 'ignore_sensor' not in record.capabilities
        assert 'auto_rearm' not in record.capabilities
        assert 'hysteresis_not_supported' in record.capabilities
        assert 'threshold_not_supported' in record.capabilities

        record._decode_capabilities(0x80)
        assert 'ignore_sensor' in record.capabilities
        assert 'auto_rearm' not in record.capabilities
        assert 'hysteresis_not_supported' in record.capabilities
        assert 'threshold_not_supported' in record.capabilities

        record._decode_capabilities(0x40)
        assert 'ignore_sensor' not in record.capabilities
        assert 'auto_rearm' in record.capabilities
        assert 'hysteresis_not_supported' in record.capabilities
        assert 'threshold_not_supported' in record.capabilities

        record._decode_capabilities(0x30)
        assert 'ignore_sensor' not in record.capabilities
        assert 'auto_rearm' not in record.capabilities
        assert 'hysteresis_fixed' in record.capabilities
        assert 'threshold_not_supported' in record.capabilities

        record._decode_capabilities(0x0c)
        assert 'ignore_sensor' not in record.capabilities
        assert 'auto_rearm' not in record.capabilities
        assert 'hysteresis_not_supported' in record.capabilities
        assert 'threshold_fixed' in record.capabilities

    def test_invalid_length(self):
        with pytest.raises(DecodingError):
            data = (0, 0, 0, 0, 0)
            SdrFullSensorRecord(data)

    def test_linearization_key_error(self):
        with pytest.raises(DecodingError):
            sdr = SdrFullSensorRecord(None)
            sdr.linearization = 12
            sdr.lin(1)

    def test_linearization(self):
        sdr = SdrFullSensorRecord(None)

        # linear
        sdr.linearization = 0
        assert sdr.lin(1) == 1
        assert sdr.lin(10) == 10

        # ln
        sdr.linearization = 1
        assert sdr.lin(1) == 0

        # log
        sdr.linearization = 2
        assert sdr.lin(10) == 1
        assert sdr.lin(100) == 2

        # log
        sdr.linearization = 3
        assert sdr.lin(8) == 3
        assert sdr.lin(16) == 4

        # e
        sdr.linearization = 4
        assert sdr.lin(1) == 2.718281828459045

        # exp10
        sdr.linearization = 5
        assert sdr.lin(1) == 10
        assert sdr.lin(2) == 100

        # exp2
        sdr.linearization = 6
        assert sdr.lin(3) == 8
        assert sdr.lin(4) == 16

        # 1/x
        sdr.linearization = 7
        assert sdr.lin(2) == 0.5
        assert sdr.lin(4) == 0.25

        # sqr
        sdr.linearization = 8
        assert sdr.lin(2) == 4

        # cube
        sdr.linearization = 9
        assert sdr.lin(2) == 8
        assert sdr.lin(3) == 27

        # sqrt
        sdr.linearization = 10
        assert sdr.lin(16) == 4

        # cubert
        sdr.linearization = 11
        assert sdr.lin(8) == 2
        assert sdr.lin(27) == 3

    def test_convert_sensor_raw_to_value(self):
        sdr = SdrFullSensorRecord()
        assert sdr.convert_sensor_raw_to_value(None) is None

        sdr.analog_data_format = sdr.DATA_FMT_UNSIGNED
        sdr.m = 1
        sdr.b = 0
        sdr.k1 = 0
        sdr.k2 = 0
        sdr.linearization = 0
        assert sdr.convert_sensor_raw_to_value(1) == 1
        assert sdr.convert_sensor_raw_to_value(255) == 255

        sdr.analog_data_format = sdr.DATA_FMT_UNSIGNED
        sdr.m = 10
        sdr.b = 0
        sdr.k1 = 0
        sdr.k2 = 0
        sdr.linearization = 0
        assert sdr.convert_sensor_raw_to_value(1) == 10
        assert sdr.convert_sensor_raw_to_value(255) == 2550

        sdr.analog_data_format = sdr.DATA_FMT_1S_COMPLEMENT
        sdr.m = 1
        sdr.b = 0
        sdr.k1 = 0
        sdr.k2 = 0
        sdr.linearization = 0
        assert sdr.convert_sensor_raw_to_value(1) == 1
        assert sdr.convert_sensor_raw_to_value(128) == -127
        assert sdr.convert_sensor_raw_to_value(255) == 0

        sdr.analog_data_format = sdr.DATA_FMT_2S_COMPLEMENT
        sdr.m = 1
        sdr.b = 0
        sdr.k1 = 0
        sdr.k2 = 0
        sdr.linearization = 0
        assert sdr.convert_sensor_raw_to_value(1) == 1
        assert sdr.convert_sensor_raw_to_value(128) == -128
        assert sdr.convert_sensor_raw_to_value(255) == -1

    def test_convert_sensor_value_to_raw(self):
        sdr = SdrFullSensorRecord()

        sdr.analog_data_format = sdr.DATA_FMT_UNSIGNED
        sdr.m = 1
        sdr.b = 0
        sdr.k1 = 0
        sdr.k2 = 0
        sdr.linearization = 0
        assert sdr.convert_sensor_value_to_raw(1) == 1
        assert sdr.convert_sensor_value_to_raw(255) == 255

        sdr.analog_data_format = sdr.DATA_FMT_UNSIGNED
        sdr.m = 10
        sdr.b = 0
        sdr.k1 = 0
        sdr.k2 = 0
        sdr.linearization = 0
        assert sdr.convert_sensor_value_to_raw(10) == 1
        assert sdr.convert_sensor_value_to_raw(2550) == 255

        sdr.analog_data_format = sdr.DATA_FMT_1S_COMPLEMENT
        sdr.m = 1
        sdr.b = 0
        sdr.k1 = 0
        sdr.k2 = 0
        sdr.linearization = 0
        assert sdr.convert_sensor_value_to_raw(1) == 1
        assert sdr.convert_sensor_value_to_raw(-1) == 254
        assert sdr.convert_sensor_value_to_raw(-127) == 128

        sdr.analog_data_format = sdr.DATA_FMT_2S_COMPLEMENT
        sdr.m = 1
        sdr.b = 0
        sdr.k1 = 0
        sdr.k2 = 0
        sdr.linearization = 0
        assert sdr.convert_sensor_value_to_raw(1) == 1
        assert sdr.convert_sensor_value_to_raw(-1) == 255
        assert sdr.convert_sensor_value_to_raw(-127) == 129

    @pytest.mark.parametrize('fmt, lowest, highest', [
        (SdrFullSensorRecord.DATA_FMT_UNSIGNED, (0, 0x00), (255, 0xff)),
        (SdrFullSensorRecord.DATA_FMT_1S_COMPLEMENT, (-127, 0x80), (127, 0x7f)),
        (SdrFullSensorRecord.DATA_FMT_2S_COMPLEMENT, (-128, 0x80), (127, 0x7f)),
    ])
    def test_convert_sensor_value_to_raw_out_of_range(self, fmt, lowest,
                                                      highest):
        sdr = SdrFullSensorRecord()
        sdr.analog_data_format = fmt
        sdr.m = 1
        sdr.b = 0
        sdr.k1 = 0
        sdr.k2 = 0
        sdr.linearization = 0

        # the limits are still converted
        for (value, raw) in (lowest, highest):
            assert sdr.convert_sensor_value_to_raw(value) == raw
            assert sdr.convert_sensor_raw_to_value(raw) == value

        # one beyond the limits must not wrap around to another raw value
        with pytest.raises(ValueError):
            sdr.convert_sensor_value_to_raw(lowest[0] - 1)
        with pytest.raises(ValueError):
            sdr.convert_sensor_value_to_raw(highest[0] + 1)

    @pytest.mark.parametrize('fmt', [
        SdrFullSensorRecord.DATA_FMT_1S_COMPLEMENT,
        SdrFullSensorRecord.DATA_FMT_2S_COMPLEMENT,
    ])
    def test_convert_sensor_value_to_raw_signed_out_of_range(self, fmt):
        sdr = SdrFullSensorRecord()
        sdr.analog_data_format = fmt
        sdr.m = 1
        sdr.b = 0
        sdr.k1 = 0
        sdr.k2 = 0
        sdr.linearization = 0

        # these were encoded as negative raw values before
        for value in (128, 200, 255, -129, -200, -255):
            with pytest.raises(ValueError):
                sdr.convert_sensor_value_to_raw(value)

    def test_convert_sensor_value_to_raw_with_offset(self):
        # 3.3VSB voltage sensor (see issue #124)
        sdr = SdrFullSensorRecord()
        sdr.analog_data_format = sdr.DATA_FMT_UNSIGNED
        sdr.m = 16
        sdr.b = 163
        sdr.k1 = 0
        sdr.k2 = -3
        sdr.linearization = 0

        assert sdr.convert_sensor_value_to_raw(3.843) == 230
        assert sdr.convert_sensor_value_to_raw(2.739) == 161
        for raw in (0, 1, 161, 196, 230, 255):
            value = sdr.convert_sensor_raw_to_value(raw)
            assert sdr.convert_sensor_value_to_raw(value) == raw

        with pytest.raises(ValueError):
            sdr.convert_sensor_value_to_raw(0.1)
        with pytest.raises(ValueError):
            sdr.convert_sensor_value_to_raw(5.0)

    def test_convert_sensor_value_to_raw_with_offset_signed(self):
        sdr = SdrFullSensorRecord()
        sdr.m = 1
        sdr.b = 10
        sdr.k1 = 0
        sdr.k2 = 0
        sdr.linearization = 0

        sdr.analog_data_format = sdr.DATA_FMT_2S_COMPLEMENT
        assert sdr.convert_sensor_value_to_raw(5) == 0xfb
        for raw in range(256):
            value = sdr.convert_sensor_raw_to_value(raw)
            assert sdr.convert_sensor_value_to_raw(value) == raw

        sdr.analog_data_format = sdr.DATA_FMT_1S_COMPLEMENT
        assert sdr.convert_sensor_value_to_raw(5) == 0xfa
        # 0x00 and 0xff both encode zero in 1's complement
        for raw in range(255):
            value = sdr.convert_sensor_raw_to_value(raw)
            assert sdr.convert_sensor_value_to_raw(value) == raw

    def test_decocde(self):
        data = [0x17, 0x00, 0x51, 0x01, 0x35, 0x17, 0x00, 0x51,
                0x01, 0x35, 0x17, 0x00, 0x51, 0x01, 0x35, 0x32,
                0x85, 0x32, 0x1b, 0x1b, 0x00, 0x04, 0x00, 0x00,
                0x3b, 0x01, 0x00, 0x01, 0x00, 0xd0, 0x07, 0xcc,
                0xf4, 0xa6, 0xff, 0x00, 0x00, 0xfe, 0xf5, 0x00,
                0x8e, 0xa5, 0x04, 0x04, 0x00, 0x00, 0x00, 0xca,
                0x41, 0x32, 0x3a, 0x56, 0x63, 0x63, 0x20, 0x31,
                0x32, 0x56]
        sdr = SdrCommon.from_data(data)
        assert isinstance(sdr, SdrFullSensorRecord)
        assert str(sdr) == '["A2:Vcc 12V"] [1:53] [17 00 51 01 35 17 00 ' \
                           '51 01 35 17 00 51 01 35 32 85 32 1b 1b 00 04 00 00 ' \
                           '3b 01 00 01 00 d0 07 cc f4 a6 ff 00 00 fe f5 00 8e ' \
                           'a5 04 04 00 00 00 ca 41 32 3a 56 63 63 20 31 32 56]'
        assert sdr.device_id_string == 'A2:Vcc 12V'


class TestSdrCommon:
    def test_invalid_data_length(self):
        with pytest.raises(DecodingError):
            data = (0x00, 0x01, 0x02, 0x03)
            SdrCommon(data)

    def test_object(self):
        data = (0x00, 0x01, 0x02, 0x03, 0x04)
        sdr = SdrCommon(data)
        assert sdr.id == 0x0100
        assert sdr.version == 0x02
        assert sdr.type == 0x03
        assert sdr.length == 0x04


class TestSdrCompactSensorRecord:

    def test_invalid_length(self):
        with pytest.raises(DecodingError):
            data = (0, 0, 0, 0, 0)
            SdrCompactSensorRecord(data)

    def test_decode(self):
        data = [0xd3, 0x00, 0x51, 0x02, 0x28, 0x82, 0x00, 0xd3,
                0xc1, 0x64, 0x03, 0x40, 0x21, 0x6f, 0x00, 0x00,
                0x00, 0x00, 0x03, 0x00, 0xc0, 0x00, 0x00, 0x01,
                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xcd,
                0x41, 0x34, 0x3a, 0x50, 0x72, 0x65, 0x73, 0x20,
                0x53, 0x46, 0x50, 0x2d, 0x31]
        sdr = SdrCommon.from_data(data)
        assert isinstance(sdr, SdrCompactSensorRecord)
        assert str(sdr) == '["A4:Pres SFP-1"] [d3 00 51 02 28 82 00 d3 c1 64 ' \
                           '03 40 21 6f 00 00 00 00 03 00 c0 00 00 01 00 00 00 ' \
                           '00 00 00 00 cd 41 34 3a 50 72 65 73 20 53 46 50 2d 31]'


def test_sdreventonlysensorrecord():
    with pytest.raises(DecodingError):
        data = (0, 0, 0, 0, 0)
        SdrEventOnlySensorRecord(data)


class TestSdrFruDeviceLocatorRecord:

    def test_invalid_length(self):
        with pytest.raises(DecodingError):
            data = (0, 0, 0, 0, 0)
            SdrFruDeviceLocator(data)

    def test_decode(self):
        data = [0x02, 0x00, 0x51, 0x11, 0x17, 0x82, 0x03, 0x80,
                0x00, 0x00, 0x10, 0x02, 0xc2, 0x61, 0x00, 0xcc,
                0x4b, 0x6f, 0x6e, 0x74, 0x72, 0x6f, 0x6e, 0x20,
                0x4d, 0x43, 0x4d, 0x43]
        sdr = SdrCommon.from_data(data)
        assert isinstance(sdr, SdrFruDeviceLocator)
        assert str(sdr) == '["Kontron MCMC"] [02 00 51 11 17 82 03 80 00 00 ' \
                           '10 02 c2 61 00 cc 4b 6f 6e 74 72 6f 6e 20 4d 43 4d 43]'


class TestSdrManagementControllerDeviceRecord:

    def test_invalid_length(self):
        with pytest.raises(DecodingError):
            data = (0, 0, 0, 0, 0)
            SdrManagementControllerDeviceLocator(data)

    def test_decode(self):
        data = [0x00, 0x01, 0x51, 0x12, 0x19, 0x00, 0x01, 0x51,
                0x12, 0x1b, 0x00, 0x01, 0x51, 0x12, 0x1b, 0xc9,
                0x41, 0x32, 0x3a, 0x41, 0x4d, 0x34, 0x32, 0x32,
                0x30]
        sdr = SdrCommon.from_data(data)
        assert isinstance(sdr, SdrManagementControllerDeviceLocator)
        assert str(sdr) == '["A2:AM4220"] [00 01 51 12 19 00 01 51 12 1b ' \
                           '00 01 51 12 1b c9 41 32 3a 41 4d 34 32 32 30]'
        assert sdr.device_id_string == 'A2:AM4220'


class TestSdrManagementControllerConfirmationRecord:

    def test_decode(self):
        data = [0x45, 0x00, 0x51, 0x13, 0x1b, 0x20, 0x00, 0x01,
                0x02, 0x01, 0x51, 0x4a, 0xc1, 0x62, 0x06, 0x80,
                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        sdr = SdrCommon.from_data(data)
        assert isinstance(sdr, SdrManagementControllerConfirmationRecord)
        assert str(sdr) == '[45 00 51 13 1b 20 00 01 02 01 51 4a c1 62 06 80 00 ' \
                           '00 00 00 00 00 00 00 00 00 00 00 00 00 00 00]'
        assert sdr.device_slave_address == 0x10
        assert sdr.device_id == 0x00
        assert sdr.channel_number == 0
        assert sdr.device_revision == 1
        assert sdr.firmware_revision_1 == 0x02
        assert sdr.firmware_revision_2 == 0x01
        assert sdr.ipmi_version == 0x51
        assert sdr.manufacturer_id == 0x2c14a
        assert sdr.product_id == 0x8006


def test_unknown_record_type():
    data = [0x01, 0x0, 0x51, 0x0a, 0x0]
    sdr = SdrCommon.from_data(data, 0xffff)
    assert isinstance(sdr, SdrUnknownSensorRecord)


# Full Sensor Record "A2:Vcc 12V" of TestSdrFullSensorRecord.test_decocde
FULL_SENSOR_RECORD = [
    0x17, 0x00, 0x51, 0x01, 0x35, 0x17, 0x00, 0x51,
    0x01, 0x35, 0x17, 0x00, 0x51, 0x01, 0x35, 0x32,
    0x85, 0x32, 0x1b, 0x1b, 0x00, 0x04, 0x00, 0x00,
    0x3b, 0x01, 0x00, 0x01, 0x00, 0xd0, 0x07, 0xcc,
    0xf4, 0xa6, 0xff, 0x00, 0x00, 0xfe, 0xf5, 0x00,
    0x8e, 0xa5, 0x04, 0x04, 0x00, 0x00, 0x00, 0xca,
    0x41, 0x32, 0x3a, 0x56, 0x63, 0x63, 0x20, 0x31,
    0x32, 0x56]


def test_full_sensor_record_bit_fields():
    data = list(FULL_SENSOR_RECORD)
    # the indexes are the byte numbers of the IPMI specification minus 1
    data[20] = 0b00101111      # units 1: rate unit 5, modifier unit 3, %
    data[27] = 0x3f            # accuracy bits 5:0, B bits 9:8 = 0
    data[28] = 0xf4            # accuracy bits 9:6, accuracy exponent 1
    data[47] = 0xca            # ID string type 3 (8-bit ASCII), 10 bytes
    sdr = SdrFullSensorRecord(data)
    assert sdr.analog_data_format == 0
    assert sdr.rate_unit == 5
    assert sdr.modifier_unit == 3
    assert sdr.percentage == 1
    assert sdr.accuracy == 0x3ff
    assert sdr.accuracy_exp == 1
    assert sdr.device_id_string_type == 3
    assert sdr.device_id_string == 'A2:Vcc 12V'


@pytest.mark.parametrize('capabilities, expected', [
    (0x00, ['hysteresis_not_supported', 'threshold_not_supported']),
    (0x14, ['hysteresis_readable', 'threshold_readable']),
    (0x28, ['hysteresis_read_and_setable', 'threshold_read_and_setable']),
    (0x3c, ['hysteresis_fixed', 'threshold_fixed']),
])
def test_full_sensor_record_threshold_access(capabilities, expected):
    record = SdrFullSensorRecord()
    record._decode_capabilities(capabilities)
    assert record.capabilities == expected


def test_delete_sdr_reserves_the_sdr_repository():
    ipmi = create_ipmi({'ReserveSdrRepository': b'\x00\x34\x12',
                        'DeleteSdr': b'\x00\x05\x00'})
    assert ipmi.delete_sdr(5) == 5
    assert ipmi.requests == [('ReserveSdrRepositoryReq', b''),
                             ('DeleteSdrReq', b'\x34\x12\x05\x00')]


def test_get_repository_sdr_canceled_reservation(monkeypatch):
    monkeypatch.setattr('pyipmi.helper.time', SimpleNamespace(sleep=lambda s: None))
    # OEM record 0x0001 with the manufacturer ID 0x070020, the last record
    header = b'\x01\x00\x51\xc0\x03'
    ipmi = create_ipmi({
        'ReserveSdrRepository': [b'\x00\x01\x00', b'\x00\x02\x00'],
        'GetSdr': [
            b'\x00\xff\xff' + header,
            # the reservation is canceled, e.g. by an added record
            b'\xc5',
            # the record is read again from the start
            b'\x00\xff\xff' + header,
            b'\x00\xff\xff' + b'\x20\x00\x07',
        ],
    })
    sdr = ipmi.get_repository_sdr(1)
    assert sdr.id == 1
    assert sdr.manufacturer_id == 0x070020
    names = [name for (name, _) in ipmi.requests]
    assert names == ['ReserveSdrRepositoryReq', 'GetSdrReq', 'GetSdrReq',
                     'ReserveSdrRepositoryReq', 'GetSdrReq', 'GetSdrReq']
    # the new reservation ID 2 is used for the reads after the cancel
    reservations = [data[:2] for (name, data) in ipmi.requests
                    if name == 'GetSdrReq']
    assert reservations == [b'\x01\x00', b'\x01\x00', b'\x02\x00',
                            b'\x02\x00']


def test_sdr_repository_entries_canceled_reservation(monkeypatch):
    monkeypatch.setattr('pyipmi.helper.time',
                        SimpleNamespace(sleep=lambda s: None))
    # two OEM records with only the manufacturer ID
    record_1 = b'\x01\x00\x51\xc0\x03' + b'\x20\x00\x07'
    record_2 = b'\x02\x00\x51\xc0\x03' + b'\x20\x00\x08'
    ipmi = create_ipmi({
        'ReserveSdrRepository': [b'\x00\x01\x00', b'\x00\x02\x00'],
        'GetSdr': [
            b'\x00\x02\x00' + record_1[:5],
            # the reservation is canceled, e.g. by an added record
            b'\xc5',
            b'\x00\x02\x00' + record_1[:5],
            b'\x00\x02\x00' + record_1[5:],
            b'\x00\xff\xff' + record_2[:5],
            b'\x00\xff\xff' + record_2[5:],
        ],
    })
    records = list(ipmi.sdr_repository_entries())
    assert [r.manufacturer_id for r in records] == [0x070020, 0x080020]
    # the next record is read with the new reservation right away, the
    # repository is reserved only once again
    names = [name for (name, _) in ipmi.requests]
    assert names.count('ReserveSdrRepositoryReq') == 2
    reservations = [data[:2] for (name, data) in ipmi.requests
                    if name == 'GetSdrReq']
    assert reservations[2:] == [b'\x02\x00'] * 4


def test_oem_record():
    # IPMI 2.0 section 43.12: no record key, the manufacturer ID (here PICMG
    # 0x00315a) is followed by the OEM data
    data = [0x05, 0x00, 0x51, 0xc0, 0x06, 0x5a, 0x31, 0x00, 0x01, 0x02, 0x03]
    record = SdrCommon.from_data(data)
    assert isinstance(record, SdrOEMSensorRecord)
    assert record.id == 5
    assert record.manufacturer_id == 0x315a
    assert record.manufacturer_name == 'PICMG'
    assert record.oem_data == b'\x01\x02\x03'
    assert not hasattr(record, 'number')


def test_oem_record_too_short():
    # a record without the complete manufacturer ID is still decoded
    record = SdrCommon.from_data([0x05, 0x00, 0x51, 0xc0, 0x02, 0x5a, 0x31])
    assert isinstance(record, SdrOEMSensorRecord)
    assert record.manufacturer_id is None
    assert record.oem_data == b'\x5a\x31'


@pytest.mark.parametrize('sdr_type, string', [
    (0x01, 'Full Sensor Record'),
    (0x11, 'FRU Device Locator Record'),
    (0x0a, 'Unknown Record'),
])
def test_sdr_type_to_string(sdr_type, string):
    assert sdr_type_to_string(sdr_type) == string


@pytest.mark.parametrize('entity_id, string', [
    (0x03, 'Processor'),
    (0x07, 'System Board'),
    (0xa0, 'PICMG Front Board'),
    (0x90, 'Chassis-specific'),
    (0xb0, 'Board-set specific'),
    (0xd0, 'OEM'),
    (0x50, 'Unknown'),
])
def test_entity_id_to_string(entity_id, string):
    assert entity_id_to_string(entity_id) == string


@pytest.mark.parametrize('units, string', [
    ((0x00, 0x00, 0x00), ''),
    ((0x00, 0x01, 0x00), 'degrees C'),
    ((0x80, 0x04, 0x00), 'Volts'),
    ((0x01, 0x12, 0x00), '% RPM'),
    ((0x01, 0x00, 0x00), '%'),
    ((0x02, 0x06, 0x05), 'Watts/Amps'),
    ((0x04, 0x06, 0x18), 'Watts*hour'),
    ((0x20, 0x55, 0x00), 'packets per minute'),
    ((0x00, 0xff, 0x00), 'unit 0xff'),
])
def test_units_to_string(units, string):
    assert units_to_string(*units) == string


def test_partial_add_sdr_sends_the_data():
    ipmi = create_ipmi(b'\x00\x05\x00')
    assert ipmi.partial_add_sdr(0x1234, 0, 0, 1, b'\x01\x02\x03') == 5
    assert ipmi.requests == [
        ('PartialAddSdrReq', b'\x34\x12\x00\x00\x00\x01\x01\x02\x03')]
