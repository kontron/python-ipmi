#!/usr/bin/env python

from array import array

import pytest

import pyipmi.msgs.sensor

from pyipmi.msgs import encode_message
from pyipmi.msgs import decode_message


def test_getdevicesdrinfo_encode_req():
    m = pyipmi.msgs.sensor.GetDeviceSdrInfoReq()
    data = encode_message(m)
    assert data == b''


def test_getdevicesdrinfo_encode_req_operation():
    m = pyipmi.msgs.sensor.GetDeviceSdrInfoReq()
    m.operation = 1
    assert encode_message(m) == b'\x01'


def test_getdevicesdrinfo_encode_rsp():
    m = pyipmi.msgs.sensor.GetDeviceSdrInfoRsp()
    decode_message(m, b'\x00\x03\x05')
    assert m.completion_code == 0x00
    assert m.number_of_sensors == 3
    assert m.flags.lun0_has_sensors == 1
    assert m.flags.lun1_has_sensors == 0
    assert m.flags.lun2_has_sensors == 1
    assert m.flags.lun3_has_sensors == 0
    assert m.flags.dynamic_population == 0


def test_getdevicesdrinfo_encode_rsp_with_timestamp():
    m = pyipmi.msgs.sensor.GetDeviceSdrInfoRsp()
    decode_message(m, b'\x00\x12\x01\xaa\xbb\xcc\xdd')
    assert m.completion_code == 0x00
    assert m.number_of_sensors == 0x12
    assert m.flags.lun0_has_sensors == 1
    assert m.flags.lun1_has_sensors == 0
    assert m.flags.lun2_has_sensors == 0
    assert m.flags.lun3_has_sensors == 0
    assert m.flags.dynamic_population == 0
    assert m.sensor_population_change == 0xddccbbaa


def test_getdevicesdr_encode_req():
    m = pyipmi.msgs.sensor.GetDeviceSdrReq()
    m.reservation_id = 0x0123
    m.record_id = 0x4567
    m.offset = 0x89
    m.bytes_to_read = 0xab
    data = encode_message(m)
    assert data == b'\x23\x01\x67\x45\x89\xab'


def test_getdevicesdr_decode_rsp():
    m = pyipmi.msgs.sensor.GetDeviceSdrRsp()
    decode_message(m, b'\x00\x01\x23\xaa\xbb')
    assert m.completion_code == 0x00
    assert m.next_record_id == 0x2301
    assert m.record_data == array('B', [0xaa, 0xbb])


def test_setsensorhysteresis_encode_req():
    m = pyipmi.msgs.sensor.SetSensorHysteresisReq()
    m.sensor_number = 0xab
    m.positive_going_hysteresis = 0xaa
    m.negative_going_hysteresis = 0xbb
    data = encode_message(m)
    assert data == b'\xab\xff\xaa\xbb'


def test_getsensorhysteresis_encode_req():
    m = pyipmi.msgs.sensor.GetSensorHysteresisReq()
    m.sensor_number = 0xab
    data = encode_message(m)
    assert data == b'\xab\xff'


def test_getsensorhysteresis_decode_rsp():
    m = pyipmi.msgs.sensor.GetSensorHysteresisRsp()
    decode_message(m, b'\x00\xaa\xbb')
    assert m.completion_code == 0x00
    assert m.positive_going_hysteresis == 0xaa
    assert m.negative_going_hysteresis == 0xbb


def test_setsensorthresholds_encode_req_set_unr():
    m = pyipmi.msgs.sensor.SetSensorThresholdsReq()
    m.sensor_number = 0x55
    m.set_mask.unr = 1
    m.threshold.unr = 0xaa
    data = encode_message(m)
    assert data == b'\x55\x20\x00\x00\x00\x00\x00\xaa'


def test_setsensorthresholds_encode_req_set_ucr():
    m = pyipmi.msgs.sensor.SetSensorThresholdsReq()
    m.sensor_number = 0x55
    m.set_mask.ucr = 1
    m.threshold.ucr = 0xaa
    data = encode_message(m)
    assert data == b'\x55\x10\x00\x00\x00\x00\xaa\x00'


def test_setsensorthresholds_encode_req_set_unc():
    m = pyipmi.msgs.sensor.SetSensorThresholdsReq()
    m.sensor_number = 0x55
    m.set_mask.unc = 1
    m.threshold.unc = 0xaa
    data = encode_message(m)
    assert data == b'\x55\x08\x00\x00\x00\xaa\x00\x00'


def test_setsensorthresholds_encode_req_set_lnr():
    m = pyipmi.msgs.sensor.SetSensorThresholdsReq()
    m.sensor_number = 0x55
    m.set_mask.lnr = 1
    m.threshold.lnr = 0xaa
    data = encode_message(m)
    assert data == b'\x55\x04\x00\x00\xaa\x00\x00\x00'


def test_setsensorthresholds_encode_req_set_lcr():
    m = pyipmi.msgs.sensor.SetSensorThresholdsReq()
    m.sensor_number = 0x55
    m.set_mask.lcr = 1
    m.threshold.lcr = 0xaa
    data = encode_message(m)
    assert data == b'\x55\x02\x00\xaa\x00\x00\x00\x00'


def test_setsensorthresholds_encode_req_set_lnc():
    m = pyipmi.msgs.sensor.SetSensorThresholdsReq()
    m.sensor_number = 0x55
    m.set_mask.lnc = 1
    m.threshold.lnc = 0xaa
    data = encode_message(m)
    assert data == b'\x55\x01\xaa\x00\x00\x00\x00\x00'


def test_setsensoreventenable_encode_req():
    m = pyipmi.msgs.sensor.SetSensorEventEnableReq()
    m.sensor_number = 0xab
    m.enable.config = 0
    m.enable.event_message = 0
    m.enable.sensor_scanning = 0
    data = encode_message(m)
    assert data == b'\xab\x00'


def test_setsensoreventenable_encode_cfg_req():
    m = pyipmi.msgs.sensor.SetSensorEventEnableReq()
    m.sensor_number = 0xab
    m.enable.config = 2
    m.enable.event_message = 0
    m.enable.sensor_scanning = 0
    data = encode_message(m)
    assert data == b'\xab\x20'


def test_setsensoreventenable_encode_scanning_enabled_req():
    m = pyipmi.msgs.sensor.SetSensorEventEnableReq()
    m.sensor_number = 0xab
    m.enable.config = 0
    m.enable.event_message = 0
    m.enable.sensor_scanning = 1
    data = encode_message(m)
    assert data == b'\xab\x40'


def test_setsensoreventenable_encode_event_enabled_req():
    m = pyipmi.msgs.sensor.SetSensorEventEnableReq()
    m.sensor_number = 0xab
    m.enable.config = 0
    m.enable.event_message = 1
    m.enable.sensor_scanning = 0
    data = encode_message(m)
    assert data == b'\xab\x80'


def test_setsensoreventenable_encode_byte3_req():
    m = pyipmi.msgs.sensor.SetSensorEventEnableReq()
    m.sensor_number = 0xab
    m.enable.config = 0
    m.enable.event_message = 0
    m.enable.sensor_scanning = 0
    m.byte3 = 0xaa
    data = encode_message(m)
    assert data == b'\xab\x00\xaa'


def test_setsensoreventenable_encode_byte34_req():
    m = pyipmi.msgs.sensor.SetSensorEventEnableReq()
    m.sensor_number = 0xab
    m.enable.config = 0
    m.enable.event_message = 0
    m.enable.sensor_scanning = 0
    m.byte3 = 0xaa
    m.byte4 = 0xbb
    data = encode_message(m)
    assert data == b'\xab\x00\xaa\xbb'


def test_getsensoreventenable_encode_req():
    m = pyipmi.msgs.sensor.GetSensorEventEnableReq()
    m.sensor_number = 0xab
    data = encode_message(m)
    assert data == b'\xab'


def test_getsensoreventenable_decode_event_enabled_rsp():
    m = pyipmi.msgs.sensor.GetSensorEventEnableRsp()
    decode_message(m, b'\x00\x80')
    assert m.completion_code == 0x00
    assert m.enabled.event_message == 1
    assert m.enabled.sensor_scanning == 0


def test_getsensoreventenable_decode_scanning_enabled_rsp():
    m = pyipmi.msgs.sensor.GetSensorEventEnableRsp()
    decode_message(m, b'\x00\x40')
    assert m.completion_code == 0x00
    assert m.enabled.event_message == 0
    assert m.enabled.sensor_scanning == 1


def test_getsensoreventenable_decode_byte3_rsp():
    m = pyipmi.msgs.sensor.GetSensorEventEnableRsp()
    decode_message(m, b'\x00\xc0\xaa')
    assert m.completion_code == 0x00
    assert m.enabled.event_message == 1
    assert m.byte3 == 0xaa


def test_getsensoreventenable_decode_byte34_rsp():
    m = pyipmi.msgs.sensor.GetSensorEventEnableRsp()
    decode_message(m, b'\x00\xc0\xaa\xbb')
    assert m.completion_code == 0x00
    assert m.enabled.event_message == 1
    assert m.byte3 == 0xaa
    assert m.byte4 == 0xbb


def test_getsensoreventenable_decode_byte3456_rsp():
    m = pyipmi.msgs.sensor.GetSensorEventEnableRsp()
    decode_message(m, b'\x00\xc0\xaa\xbb\xcc\xdd')
    assert m.completion_code == 0x00
    assert m.enabled.event_message == 1
    assert m.byte3 == 0xaa
    assert m.byte4 == 0xbb
    assert m.byte5 == 0xcc
    assert m.byte6 == 0xdd


def test_rearmsensorevents_encode_req():
    m = pyipmi.msgs.sensor.RearmSensorEventsReq()
    m.sensor_number = 0xab
    data = encode_message(m)
    assert data == b'\xab\x00\x00\x00\x00\x00'


def test_rearmsensorevents_decode_rsp():
    m = pyipmi.msgs.sensor.RearmSensorEventsRsp()
    decode_message(m, b'\x00')
    assert m.completion_code == 0x00


def test_platform_event_encode_req():
    m = pyipmi.msgs.sensor.PlatformEventReq()
    m.sensor_type = 0xf2
    m.sensor_number = 0xab
    m.event_type.type = 0x6f
    m.event_type.dir = 0x0
    m.event_data = [0x1, 0xff, 0xff]
    data = encode_message(m)
    assert data == b'\x04\xf2\xab\x6f\x01\xff\xff'


def test_platform_event_encode_req_generator_id():
    # over the system interface the request starts with the Generator ID
    m = pyipmi.msgs.sensor.PlatformEventReq()
    assert m.generator_id is None
    m.generator_id = 0x41
    m.sensor_type = 0xf2
    m.sensor_number = 0xab
    m.event_type.type = 0x6f
    m.event_data = [0x1, 0xff, 0xff]
    data = encode_message(m)
    assert data == b'\x41\x04\xf2\xab\x6f\x01\xff\xff'


def test_platform_event_decode_req():
    m = pyipmi.msgs.sensor.PlatformEventReq()
    decode_message(m, b'\x04\xf2\xab\x6f\x01\xff\xff')
    assert m.generator_id is None
    assert m.event_message_rev == 4
    assert m.sensor_type == 0xf2
    assert m.sensor_number == 0xab
    assert m.event_data == array('B', [0x1, 0xff, 0xff])


def test_platform_event_decode_rsp():
    m = pyipmi.msgs.sensor.PlatformEventRsp()
    decode_message(m, b'\x00')
    assert m.completion_code == 0x00


def test_getsensorreadingfactors_encode_req():
    m = pyipmi.msgs.sensor.GetSensorReadingFactorsReq()
    m.sensor_number = 0x10
    m.reading = 0x80
    assert m.__netfn__ == 0x04
    assert m.__cmdid__ == 0x23
    assert encode_message(m) == b'\x10\x80'


def test_getsensorreadingfactors_decode_rsp():
    m = pyipmi.msgs.sensor.GetSensorReadingFactorsRsp()
    decode_message(m, b'\x00\x90\xfe\xc5\x64\x05\x18\xd2')
    assert m.completion_code == 0x00
    assert m.next_reading == 0x90
    assert bytes(m.factors) == b'\xfe\xc5\x64\x05\x18\xd2'


@pytest.mark.parametrize('data, asserted_low, deasserted_high', [
    (b'\x00\xc0\x05\x01\x00\x02', 0x05, 0x02),
    # without the event bytes
    (b'\x00\xe0', None, None),
])
def test_getsensoreventstatus_decode_rsp(data, asserted_low,
                                         deasserted_high):
    m = pyipmi.msgs.sensor.GetSensorEventStatusRsp()
    decode_message(m, data)
    assert m.__cmdid__ == 0x2b
    assert m.status.event_messages_enabled == 1
    assert m.status.sensor_scanning_enabled == 1
    assert m.status.reading_unavailable == (data[1] >> 5) & 1
    assert m.assertion_events_low == asserted_low
    assert m.deassertion_events_high == deasserted_high


def test_setsensortype_encode_req():
    m = pyipmi.msgs.sensor.SetSensorTypeReq()
    m.sensor_number = 0x10
    m.sensor_type = 0x01
    m.event_reading_type.code = 0x6f
    assert m.__cmdid__ == 0x2e
    assert encode_message(m) == b'\x10\x01\x6f'


def test_getsensortype_decode_rsp():
    m = pyipmi.msgs.sensor.GetSensorTypeRsp()
    decode_message(m, b'\x00\x21\x6f')
    assert m.__cmdid__ == 0x2f
    assert m.sensor_type == 0x21
    assert m.event_reading_type.code == 0x6f


def test_setsensorreadingandeventstatus_encode_req():
    m = pyipmi.msgs.sensor.SetSensorReadingAndEventStatusReq()
    m.sensor_number = 0x10
    m.operation.reading = 1
    m.sensor_reading = 0x42
    assert m.__cmdid__ == 0x30
    # only the bytes up to the reading
    assert encode_message(m) == b'\x10\x01\x42'
    m.operation.assertion_bits = 3
    m.operation.event_data = 2
    m.assertion_mask = 0x0102
    m.deassertion_mask = 0x0000
    m.event_data = array('B', [0x01, 0xff, 0xff])
    assert encode_message(m) == \
        b'\x10\xb1\x42\x02\x01\x00\x00\x01\xff\xff'
